from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from forgerecipes import openssl


class OpenSSLTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def context(self, compiler="/selected/toolchain/clang", platform="Linux", arguments=()):
        return SimpleNamespace(
            source_snapshot=self.root / "source", build_dir=self.root / "build", prefix=self.root / "prefix",
            environment={"PATH": "/available/bin", "CFLAGS": "-DSELECTED=1"}, options={},
            target={"platform": platform, "machine": "x86_64", "c": {"path": compiler, "arguments": list(arguments)}},
            jobs=2, configuration="Release", run=Mock())

    def test_selected_clang_never_silently_switches_to_gcc(self):
        context = self.context(arguments=("-DARGUMENT=1",))
        openssl.build_openssl(context)
        configure = context.run.call_args_list[0].args[0]
        self.assertIn("-DCMAKE_C_COMPILER=/selected/toolchain/clang", configure)
        self.assertIn("-DCMAKE_C_COMPILER_ARG1=-DARGUMENT=1", configure)
        self.assertFalse(any("gcc" in str(value) for value in configure))
        self.assertNotIn("CC", context.environment)

    def test_selected_gcc_is_forwarded_even_if_path_has_other_compilers(self):
        context = self.context("/selected/gcc-15")
        openssl.build_openssl(context)
        self.assertIn("-DCMAKE_C_COMPILER=/selected/gcc-15", context.run.call_args_list[0].args[0])

    def test_missing_compiler_identity_is_not_guessed_from_path(self):
        context = self.context()
        context.target["c"] = {}
        with self.assertRaisesRegex(ValueError, "probed target.c"):
            openssl.build_openssl(context)
        context.run.assert_not_called()

    def test_msvc_path_is_one_unquoted_cmake_argument(self):
        context = self.context("C:/Program Files/Compiler/cl.exe", "Windows", ("/DARGUMENT=1",))
        openssl.build_openssl(context)
        configure = context.run.call_args_list[0].args[0]
        self.assertIn("-DCMAKE_C_COMPILER=C:/Program Files/Compiler/cl.exe", configure)
        self.assertIn("-DCMAKE_C_COMPILER_ARG1=/DARGUMENT=1", configure)

    def test_debug_configuration_is_forwarded_without_release_substitution(self):
        context = self.context("C:/Compiler/cl.exe", "Windows")
        context.configuration = "Debug"
        openssl.build_openssl(context)
        self.assertIn("-DCMAKE_BUILD_TYPE=Debug", context.run.call_args_list[0].args[0])
        build = context.run.call_args_list[1].args[0]
        self.assertEqual(build[build.index("--config") + 1], "Debug")

    def test_target_sdk_toolchain_and_flags_reach_platform_recipe(self):
        context = self.context()
        context.target["platform"] = "iOS"
        context.target["cmake"] = {"CMAKE_GENERATOR": "Ninja", "CMAKE_TOOLCHAIN_FILE": "/selected/ios.cmake"}
        context.options = {"cmake_options": ["-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_SYSROOT=iphonesimulator", "-DCMAKE_C_FLAGS=-DABI=1"]}
        openssl.build_openssl(context)
        configure = context.run.call_args_list[0].args[0]
        for value in context.options["cmake_options"]:
            self.assertIn(value, configure)
        self.assertIn("-DCMAKE_TOOLCHAIN_FILE=/selected/ios.cmake", configure)
        self.assertIn("Ninja", configure)

    def test_managed_install_prefix_cannot_be_overridden(self):
        for option in ("-DCMAKE_INSTALL_PREFIX=/other", "-DCMAKE_PREFIX_PATH=/other", "-DARIA_OPENSSL_INSTALL_PREFIX=/other"):
            context = self.context()
            context.options = {"cmake_options": [option]}
            with self.subTest(option=option), self.assertRaisesRegex(ValueError, "controlled"):
                openssl.build_openssl(context)
            context.run.assert_not_called()

    def test_unconsumed_compiler_launcher_fails_before_build(self):
        context = self.context()
        context.target["c"]["launcher"] = {"path": "/usr/bin/ccache"}
        with self.assertRaisesRegex(ValueError, "COMPILER_LAUNCHER"):
            openssl.build_openssl(context)
        context.run.assert_not_called()

    def test_canonical_prefix_is_used_without_copying_relocatable_exports(self):
        context = self.context()
        openssl.build_openssl(context)
        self.assertIn("-DARIA_OPENSSL_INSTALL_PREFIX=" + Path(context.prefix).as_posix(), context.run.call_args_list[0].args[0])
        driver = (context.build_dir / "recipe-driver/CMakeLists.txt").read_text()
        self.assertIn("ARIA_PINNED_OPENSSL_SOURCE_DIR", driver)
        self.assertIn(context.source_snapshot.as_posix(), driver)
        self.assertFalse(context.source_snapshot.exists())


if __name__ == "__main__":
    unittest.main()
