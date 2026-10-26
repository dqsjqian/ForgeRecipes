"""OpenSSL builder using the preserved platform-aware CMake recipe.

The public BuildContext supplies actual compiler/SDK/configuration identities.
Build output stays in the private build tree and the canonical artifact prefix.
"""

from pathlib import Path
import os
import shlex
import subprocess


# Match the static libraries previously consumed by AriaRead and Mira. Building
# build_libs/install_dev avoids linking optional legacy modules against another
# toolchain's libcrypto; it does not silently substitute GCC for selected Clang.
CONFIGURE_OPTIONS = ("no-shared", "no-tests", "no-winstore", "no-docs", "no-apps", "no-asm")


def _literal(value):
    text = str(value)
    if "]====]" in text:
        raise ValueError("Unsupported CMake bracket delimiter in recipe path")
    return "[====[" + text + "]====]"


def build_openssl(ctx):
    """Build static OpenSSL for the probed target, including native Debug builds."""
    selected = ctx.target.get("c", {})
    if not selected.get("path"):
        raise ValueError("OpenSSL requires a probed target.c compiler identity")
    if ctx.configuration not in ("Release", "Debug", "RelWithDebInfo", "MinSizeRel"):
        raise ValueError("Unsupported OpenSSL configuration: " + ctx.configuration)
    settings = ctx.target.get("cmake", {})
    options = list(ctx.options.get("cmake_options", ctx.target.get("cmake_options", ())))
    for option in options:
        name = option.removeprefix("-D").split("=", 1)[0].split(":", 1)[0]
        if name in ("CMAKE_INSTALL_PREFIX", "CMAKE_PREFIX_PATH") or name.startswith("ARIA_OPENSSL_"):
            raise ValueError(name + " is controlled by the shared OpenSSL recipe")
        # OpenSSL's generated Makefile does not use a CMake compiler launcher.
        if name == "CMAKE_C_COMPILER_LAUNCHER" and option.split("=", 1)[-1]:
            raise ValueError("OpenSSL cannot apply CMAKE_C_COMPILER_LAUNCHER")
    if selected.get("launcher"):
        raise ValueError("OpenSSL cannot apply CMAKE_C_COMPILER_LAUNCHER")
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    driver = ctx.build_dir / "recipe-driver"
    driver.mkdir()
    (driver / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\nproject(ForgeRecipesOpenSSL C)\n"
        "function(aria_fetch_pinned_archive)\n"
        "  set(ARIA_PINNED_OPENSSL_SOURCE_DIR " + _literal(ctx.source_snapshot.as_posix()) + " PARENT_SCOPE)\n"
        "endfunction()\n"
        "include(" + _literal((Path(__file__).with_name("cmake") / "BuildOpenSSL.cmake").as_posix()) + ")\n",
        encoding="utf-8")
    command = ["cmake", "-S", str(driver), "-B", str(ctx.build_dir / "driver-build")]
    generator = settings.get("CMAKE_GENERATOR")
    if generator:
        command += ["-G", generator]
    for key, flag in (("CMAKE_GENERATOR_PLATFORM", "-A"), ("CMAKE_GENERATOR_TOOLSET", "-T")):
        if settings.get(key):
            command += [flag, settings[key]]
    command += options
    command += ["-DCMAKE_C_COMPILER=" + selected["path"]]
    if selected.get("arguments"):
        quote = subprocess.list2cmdline if os.name == "nt" else shlex.join
        command += ["-DCMAKE_C_COMPILER_ARG1=" + quote(selected["arguments"])]
    if settings.get("CMAKE_TOOLCHAIN_FILE"):
        command += ["-DCMAKE_TOOLCHAIN_FILE=" + settings["CMAKE_TOOLCHAIN_FILE"]]
    command += ["-DCMAKE_BUILD_TYPE=" + ctx.configuration,
                "-DARIA_OPENSSL_INSTALL_PREFIX=" + Path(ctx.prefix).as_posix(),
                "-DARIA_OPENSSL_JOBS=" + str(ctx.jobs),
                "-DARIA_OPENSSL_CONFIGURE_OPTIONS=" + ";".join(CONFIGURE_OPTIONS)]
    ctx.run(command)
    ctx.run(["cmake", "--build", ctx.build_dir / "driver-build", "--config", ctx.configuration,
             "--target", "aria_openssl_external", "--parallel", str(ctx.jobs)])
