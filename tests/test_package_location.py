import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "forgerecipes/cmake/PackageLocation.cmake"


@unittest.skipUnless(shutil.which("cmake"), "cmake is required")
class PackageLocationTests(unittest.TestCase):
    def test_library_layout_and_cache(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        prefix = root / "one"
        (prefix / "lib/cmake/aria").mkdir(parents=True)
        (prefix / "lib/cmake/aria/ariaConfig.cmake").write_text("", encoding="utf-8")
        (root / "two").mkdir()
        driver = root / "driver.cmake"
        driver.write_text(
            f'include("{MODULE.as_posix()}")\n'
            f'forgerecipes_locate_package(PREFIXES "{root.as_posix()}/one" "{root.as_posix()}/two" '
            "PACKAGE aria OUT config PREFIX_OUT owner)\n"
            f'if(NOT config STREQUAL "{(prefix / "lib/cmake/aria").as_posix()}")\n'
            '  message(FATAL_ERROR "wrong config directory: ${config}")\n'
            "endif()\n"
            f'if(NOT owner STREQUAL "{prefix.as_posix()}")\n'
            '  message(FATAL_ERROR "wrong owning prefix: ${owner}")\n'
            "endif()\n"
            f'if(NOT aria_DIR STREQUAL "{(prefix / "lib/cmake/aria").as_posix()}")\n'
            '  message(FATAL_ERROR "cache entry was not set: ${aria_DIR}")\n'
            "endif()\n", encoding="utf-8")
        result = subprocess.run(["cmake", "-P", str(driver)], cwd=root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_header_layout_is_found(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        prefix = root / "json-headers"
        (prefix / "share/cmake/nlohmann_json").mkdir(parents=True)
        (prefix / "share/cmake/nlohmann_json/nlohmann_jsonConfig.cmake").write_text(
            "", encoding="utf-8")
        driver = root / "driver.cmake"
        driver.write_text(
            f'include("{MODULE.as_posix()}")\n'
            f'forgerecipes_locate_package(PREFIXES "{prefix.as_posix()}" PACKAGE nlohmann_json OUT config)\n'
            f'if(NOT config STREQUAL "{(prefix / "share/cmake/nlohmann_json").as_posix()}")\n'
            '  message(FATAL_ERROR "header-only layout was not found: ${config}")\n'
            "endif()\n", encoding="utf-8")
        result = subprocess.run(["cmake", "-P", str(driver)], cwd=root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_package_leaves_outputs_empty(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "empty").mkdir()
        driver = root / "driver.cmake"
        driver.write_text(
            f'include("{MODULE.as_posix()}")\n'
            f'forgerecipes_locate_package(PREFIXES "{root.as_posix()}/empty" PACKAGE aria OUT config PREFIX_OUT owner)\n'
            "if(config OR owner)\n"
            '  message(FATAL_ERROR "unexpected success: ${config} ${owner}")\n'
            "endif()\n", encoding="utf-8")
        result = subprocess.run(["cmake", "-P", str(driver)], cwd=root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
