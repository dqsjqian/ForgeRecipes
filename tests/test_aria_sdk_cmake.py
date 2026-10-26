import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SDK = Path(__file__).resolve().parents[1] / "forgerecipes/cmake/AriaSdk.cmake"

# Stand-in for ForgeDeps.cmake that applies the same argument contract as the
# real forgedeps_environment and prints what it received.
STUB = """
function(forgedeps_environment)
    cmake_parse_arguments(DEP "OFFLINE" "FILE;PROJECT_CONFIG;ONLY;CONFIGURATION;PREFIXES"
        "SOURCE_OVERRIDES" ${ARGN})
    if(DEP_KEYWORDS_MISSING_VALUES OR DEP_UNPARSED_ARGUMENTS)
        message(FATAL_ERROR "rejected: missing=[${DEP_KEYWORDS_MISSING_VALUES}] unparsed=[${DEP_UNPARSED_ARGUMENTS}]")
    endif()
    message(STATUS "received sources=[${DEP_SOURCE_OVERRIDES}] only=[${DEP_ONLY}]")
    set(${DEP_PREFIXES} "" PARENT_SCOPE)
endfunction()
"""


@unittest.skipUnless(shutil.which("cmake"), "cmake is required")
class AriaSdkArgumentTests(unittest.TestCase):
    def run_sdk(self, arguments):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "stub").mkdir()
        (root / "stub/ForgeDeps.cmake").write_text(STUB, encoding="utf-8")
        package = root / "python/forgedeps"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(
            f"print({(root / 'stub').as_posix()!r})\n", encoding="utf-8")
        driver = root / "driver.cmake"
        driver.write_text(
            f'set(ForgeDeps_PYTHON_EXECUTABLE [=[{sys.executable}]=])\n'
            f'include("{SDK.as_posix()}")\n'
            f'forgerecipes_sdk(FILE deps.json HTTP ON TLS OFF QT OFF JNI OFF APPKIT OFF UIKIT OFF '
            f'SHARED OFF {arguments})\n',
            encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(root / "python"))
        return subprocess.run(["cmake", "-P", str(driver)], cwd=root, env=env,
                              capture_output=True, text=True)

    def test_no_source_override_omits_the_keyword(self):
        result = self.run_sdk("")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("received sources=[] only=[aria]", result.stdout + result.stderr)

    def test_source_override_is_forwarded(self):
        result = self.run_sdk("SOURCE /src/aria EXTRA_PACKAGES mira")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("received sources=[aria=/src/aria] only=[aria,mira]",
                      result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
