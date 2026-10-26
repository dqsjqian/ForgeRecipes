import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "forgerecipes/cmake/RunOpenSSL.cmake.in"
NATIVE = r"D:\a\Mira\forgedeps\build\openssl\windows-x64-gcc-debug"


@unittest.skipUnless(shutil.which("cmake"), "cmake is required")
class OpenSSLRunScriptPathTests(unittest.TestCase):
    def render(self, prefix_expression):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        driver = root / "driver.cmake"
        driver.write_text(
            f'set(ARIA_OPENSSL_INSTALL_PREFIX [=[{NATIVE}]=])\n'
            f'{prefix_expression}\n'
            f'set(_OPENSSL_ROOT "{root.as_posix()}")\n'
            f'configure_file("{TEMPLATE.as_posix()}" "{(root / "run.cmake").as_posix()}" @ONLY)\n',
            encoding="utf-8")
        subprocess.run(["cmake", "-P", str(driver)], check=True, capture_output=True)
        return subprocess.run(["cmake", "-DSTEP=unknown", "-P", str(root / "run.cmake")],
                              capture_output=True, text=True)

    def test_native_windows_prefix_breaks_the_generated_script(self):
        result = self.render("")
        self.assertIn("Syntax error", result.stderr)

    def test_normalised_prefix_reaches_the_step_dispatch(self):
        result = self.render(
            "file(TO_CMAKE_PATH \"${ARIA_OPENSSL_INSTALL_PREFIX}\" ARIA_OPENSSL_INSTALL_PREFIX)")
        self.assertNotIn("Syntax error", result.stderr)
        self.assertIn("Unknown OpenSSL step", result.stderr)

    def test_recipe_normalises_caller_paths_before_rendering(self):
        text = (TEMPLATE.parent / "BuildOpenSSL.cmake").read_text(encoding="utf-8")
        normalise = text.index('file(TO_CMAKE_PATH "${ARIA_OPENSSL_INSTALL_PREFIX}"')
        render = text.index("RunOpenSSL.cmake.in")
        self.assertLess(normalise, render)


if __name__ == "__main__":
    unittest.main()
