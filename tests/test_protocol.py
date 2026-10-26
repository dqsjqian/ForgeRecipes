from pathlib import Path
import tempfile
import unittest

from forgerecipes.protocol_support import install_compile_pdbs, install_dependency_licenses


class ProtocolTests(unittest.TestCase):
    def test_pdb_is_installed_and_ambiguity_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build, prefix = root / "build", root / "prefix"
            build.mkdir()
            (prefix / "lib").mkdir(parents=True)
            (prefix / "lib/nghttp2_static.lib").write_bytes(b"archive")
            (build / "nghttp2_static.pdb").write_bytes(b"symbols")
            install_compile_pdbs(build, prefix)
            self.assertEqual((prefix / "lib/nghttp2_static.pdb").read_bytes(), b"symbols")
            (build / "second").mkdir()
            (build / "second/nghttp2_static.pdb").write_bytes(b"ambiguous")
            with self.assertRaisesRegex(ValueError, "Ambiguous compiler PDB"):
                install_compile_pdbs(build, prefix)

    def test_runtime_notices_and_external_terms_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, prefix = Path(temporary) / "source", Path(temporary) / "prefix"
            (source / "lib").mkdir(parents=True)
            (source / "COPYING").write_text("upstream MIT terms")
            notice = "/* Copyright 2026 Example Author. Original complete terms. */"
            (source / "lib/runtime.c").write_text("int runtime;\n" + notice)
            install_dependency_licenses(source, prefix, "ngtcp2")
            target = prefix / "share/licenses/ngtcp2"
            self.assertIn(notice, (target / "SOURCE-NOTICES.txt").read_text())
            for name in ("COPYING", "quiche-LICENSE", "pcg-LICENSE-MIT.txt", "SOURCES.md"):
                self.assertTrue((target / name).is_file())


if __name__ == "__main__":
    unittest.main()
