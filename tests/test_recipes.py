from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from forgedeps import deps_build as deps
from forgerecipes import catalog, hooks, providers, recipe_input_files, get_recipe, make_sdk_config, make_curl_recipe
from forgerecipes.configuration import make_config
from forgerecipes.resolve import resolve_recipe


class RecipeTests(unittest.TestCase):
    def test_catalog_configs_record_all_inputs(self):
        config = make_config(tuple(item.name for item in catalog.RECIPES) + ('nghttp2', 'nghttp3', 'ngtcp2'))
        for dependency in config.recipes:
            self.assertEqual(set(dependency.builder_inputs), set(recipe_input_files(dependency.name).values()))
            self.assertTrue(all(path.is_file() for path in dependency.builder_inputs))

    def test_sdk_graph_has_only_selected_dependencies(self):
        self.assertEqual([d.name for d in make_sdk_config(shared=False).recipes], ['aria'])
        selected = {d.name: d for d in make_sdk_config(http=True, tls=True, qt=True, shared=False).recipes}
        self.assertEqual(set(selected), {'json', 'openssl', 'mira', 'aria'})
        self.assertEqual(selected['aria'].requires, ('json', 'mira', 'openssl'))
        self.assertEqual(selected['mira'].requires, ('openssl',))
        self.assertIn('-DARIA_BUILD_SHARED=OFF', selected['aria'].options)
        self.assertEqual(selected['openssl'], get_recipe('openssl'))
        with self.assertRaisesRegex(ValueError, 'TLS requires'):
            make_sdk_config(tls=True)

    def test_sdk_can_select_an_explicit_additional_library(self):
        deps = make_sdk_config(extra_packages=('json',), shared=False).recipes
        self.assertEqual([dep.name for dep in deps], ['aria', 'json'])
        self.assertEqual(deps[0].requires, ())

    def test_external_sdk_options_only_change_aria_recipe(self):
        plain = {d.name: d for d in make_sdk_config(http=True, tls=True, qt=True).recipes}
        qt = {d.name: d for d in make_sdk_config(http=True, tls=True, qt=True,
              aria_options=['-DQt6_DIR=/sdk/Qt6', '-DARIA_SDK_QT_IDENTITY=content']).recipes}
        for name in ('json', 'openssl', 'mira'):
            self.assertEqual(plain[name], qt[name])
        self.assertIn('-DARIA_SDK_QT_IDENTITY=content', qt['aria'].options)

    def test_curl_protocol_variant_records_real_dependencies(self):
        selected = make_curl_recipe(cli=True, http2=True, http3=True)
        self.assertEqual(selected.requires, ('zlib', 'openssl', 'nghttp2', 'nghttp3', 'ngtcp2'))
        self.assertIn('-DBUILD_CURL_EXE=ON', selected.options)
        self.assertIn('-DUSE_NGTCP2=ON', selected.options)
        self.assertTrue(get_recipe('json').header_only)



    def test_input_labels_and_digests_survive_package_relocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name in ("quickjs", "ngtcp2", "openssl"):
                inputs = recipe_input_files(name)
                copied = {}
                for label, path in inputs.items():
                    self.assertFalse(Path(label).is_absolute())
                    target = Path(temporary) / name / label
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
                    copied[label] = target
                self.assertEqual({k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in inputs.items()},
                                 {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in copied.items()})



    def test_quickjs_placeholder_is_external_and_only_uses_locked_version(self):
        quickjs = next(d for d in catalog.RECIPES if d.name == "quickjs")
        result = resolve_recipe(replace(quickjs, version="2026-06-04"), {"version": "2026-06-04"})
        self.assertNotIn("@QUICKJS_VERSION@", result.cmake_lists)
        self.assertIn('CONFIG_VERSION="2026-06-04"', result.cmake_lists)
        self.assertIn("@QUICKJS_VERSION@", quickjs.cmake_lists)

    def test_unreviewed_patch_version_is_rejected(self):
        config = make_config(("quickjs",))
        dep = next(d for d in config.recipes if d.name == "quickjs")
        record = {"source": {"provider": "quickjs"}, "version": "2099-01-01", "requested": "2099-01-01",
                  "url": "https://bellard.org/quickjs/quickjs-2099-01-01.tar.xz", "sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "explicitly reviewed"):
            deps.locked_recipes({"dependencies": {"quickjs": record}}, [dep], config)

    def test_json_and_sqlite_license_hooks_preserve_upstream_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, prefix = Path(temporary) / "source", Path(temporary) / "prefix"
            headers = source / "include/nlohmann"
            headers.mkdir(parents=True)
            (source / "LICENSE.MIT").write_text("MIT fixture")
            notice = "// SPDX-FileCopyrightText: 2026 Example Author"
            (headers / "json.hpp").write_text(notice + "\n// SPDX-License-Identifier: MIT\n")
            dep = next(d for d in catalog.RECIPES if d.name == "json")
            self.assertIn("ATTRIBUTIONS.txt", deps.copy_licenses(prefix, source, dep))
            self.assertIn(notice, (prefix / "share/licenses/json/ATTRIBUTIONS.txt").read_text())
            dedication = "The author disclaims copyright to this source code.\n"
            (source / "sqlite3.h").write_text(dedication + "*" * 73)
            dep = next(d for d in catalog.RECIPES if d.name == "sqlite3")
            deps.copy_licenses(prefix, source, dep)
            self.assertEqual((prefix / "share/licenses/sqlite3/PUBLIC-DOMAIN.txt").read_text(), dedication)

    def test_zlib_static_names_preserve_exports_findzlib_and_local_changes(self):
        for original, compatible in (("zs.lib", "zlibstatic.lib"), ("libzs.a", "libz.a")):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temporary:
                prefix = Path(temporary)
                (prefix / "lib").mkdir()
                (prefix / "lib" / original).write_bytes(b"compiled static library")
                hooks.normalize_zlib_static(prefix)
                self.assertEqual((prefix / "lib" / compatible).read_bytes(), b"compiled static library")
                self.assertTrue(deps.artifact_present(prefix, "lib/libz.a"))
                if original == "zs.lib":
                    self.assertEqual((prefix / "lib/z.lib").read_bytes(), b"compiled static library")
                if shutil.which("cmake"):
                    (prefix / "include").mkdir()
                    (prefix / "include/zlib.h").write_text('#define ZLIB_VERSION "1.3.2"\n')
                    (prefix / "CMakeLists.txt").write_text(
                        'cmake_minimum_required(VERSION 3.20)\nset(CMAKE_SYSTEM_NAME Windows)\n'
                        'project(FindZlibFixture NONE)\nset(CMAKE_FIND_LIBRARY_PREFIXES "" "lib")\n'
                        'set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" ".lib")\n'
                        f'set(ZLIB_ROOT "{prefix.as_posix()}")\n'
                        'set(ZLIB_USE_STATIC_LIBS ON)\nfind_package(ZLIB REQUIRED)\n'
                        f'if(NOT ZLIB_LIBRARY_RELEASE MATCHES "^{prefix.as_posix()}/lib/")\n'
                        'message(FATAL_ERROR "Selected non-recipe zlib")\nendif()\n')
                    found = subprocess.run(["cmake", "-S", str(prefix), "-B", str(prefix / "build")],
                                           capture_output=True, text=True)
                    self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
                hooks.normalize_zlib_static(prefix)
                (prefix / "lib" / compatible).write_bytes(b"local modification")
                with self.assertRaisesRegex(ValueError, "Conflicting zlib"):
                    hooks.normalize_zlib_static(prefix)
                self.assertEqual((prefix / "lib" / compatible).read_bytes(), b"local modification")


class ProviderContext:
    def __init__(self, text, data=b"release bytes"):
        self.text, self.data = text, data
        self.downloads = []
    def get_text(self, url):
        return self.text[url]
    def get_bytes(self, url):
        return self.data
    def download_digest(self, url, expected=None):
        digest = hashlib.sha256(self.data).hexdigest()
        if expected is not None and expected != digest:
            raise ValueError("SHA256 mismatch")
        self.downloads.append(url)
        return digest


class ProviderTests(unittest.TestCase):
    def test_sqlite_latest_verifies_official_sha3(self):
        digest = hashlib.sha3_256(b"release bytes").hexdigest()
        context = ProviderContext({"https://www.sqlite.org/download.html":
            f"PRODUCT,3.51.3,2026/sqlite-amalgamation-3510300.zip,123,{digest}\n"})
        self.assertEqual(providers.resolve_sqlite({}, "latest", context)["version"], "3.51.3")
        context.data = b"tampered"
        with self.assertRaisesRegex(ValueError, "official SHA3-256 mismatch"):
            providers.resolve_sqlite({}, "latest", context)

    def test_sqlite_explicit_historical_release_keeps_year(self):
        context = ProviderContext({"https://www.sqlite.org/download.html": "",
            "https://www.sqlite.org/releaselog/3_49_1.html": "SQLite Release 3.49.1 On 2025-02-18"})
        result = providers.resolve_sqlite({}, "3.49.1", context)
        self.assertEqual(result["url"], "https://www.sqlite.org/2025/sqlite-amalgamation-3490100.zip")

    def test_quickjs_latest_ignores_unofficial_names(self):
        context = ProviderContext({"https://bellard.org/quickjs/":
            '<a href="quickjs-2026-06-04.tar.xz">ok</a><a href="quickjs-2099-01-01-beta.tar.xz">beta</a>'})
        self.assertEqual(providers.resolve_quickjs({}, "latest", context)["version"], "2026-06-04")
        with self.assertRaisesRegex(ValueError, "official YYYY-MM-DD"):
            providers.resolve_quickjs({}, "main", context)


if __name__ == "__main__":
    unittest.main()
