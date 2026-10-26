"""Explicit, location-independent inputs for recipe and artifact identities."""

from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PATCHES = {
    "gumbo": ("gumbo-0.10.1-msvc.patch",),
    "quickjs": ("quickjs-msvc-2026-06-04.patch", "quickjs_msvc_shim.h"),
    "doctest": ("doctest-2.5.3-cmake-utf8-discovery.patch",),
}
_PROTOCOL = {"nghttp2", "nghttp3", "ngtcp2"}
_CATALOG = {"zlib", "openssl", "curl", "json", "sqlite3", "gumbo", "quickjs",
            "doctest", "aria", "mira"}


def recipe_input_files(name):
    """Map stable package-relative labels to all code and assets used by a recipe."""
    if name not in _PROTOCOL | _CATALOG:
        raise ValueError("Unknown shared recipe: " + name)
    names = {"inputs.py"}
    if name in ("aria", "mira", "curl"):
        names.add("sdk.py")
    if name in ("curl", "ngtcp2"):
        names.add("bindings.py")
    if name in _PROTOCOL:
        names.update(("protocols.py", "protocol_support.py"))
        if name == "ngtcp2":
            names.update("licenses/" + filename for filename in
                         ("quiche-LICENSE", "pcg-LICENSE-MIT.txt", "SOURCES.md"))
    else:
        names.add("catalog.py")
        if name in ("json", "sqlite3", "zlib"):
            names.add("hooks.py")
        if name == "openssl":
            names.add("openssl.py")
            names.update("cmake/" + filename for filename in
                         ("BuildOpenSSL.cmake", "RunOpenSSL.cmake.in", "RunOpenSSL-mingw.sh.in"))
        if name == "quickjs":
            names.add("resolve.py")
        if name in ("quickjs", "sqlite3"):
            names.add("providers.py")
        names.update("patches/" + filename for filename in _PATCHES.get(name, ()))
    result = {name: _ROOT / name for name in sorted(names)}
    for name, path in result.items():
        if not path.is_file():
            raise ValueError("Missing shared recipe input: " + name)
    return result


def with_inputs(dependency):
    """Attach the same external files to the legacy ProjectConfig recipe."""
    return replace(dependency, builder_inputs=tuple(recipe_input_files(dependency.name).values()))
