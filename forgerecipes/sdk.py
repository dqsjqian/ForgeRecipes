"""Feature-selected SDK recipes; versions still come from the consumer lock."""

from dataclasses import replace
from .catalog import RECIPES
from .inputs import with_inputs


def _variant(name, settings, requires):
    dep = next(item for item in RECIPES if item.name == name)
    options = tuple(option for option in dep.options
                    if option.removeprefix("-D").split("=", 1)[0] not in settings)
    options += tuple("-D" + key + "=" + ("ON" if value else "OFF") for key, value in settings.items())
    return with_inputs(replace(dep, options=options, requires=tuple(requires)))


def make_aria_recipe(*, http=False, tls=False, qt=False, jni=False, appkit=False, uikit=False, shared=True):
    """Select an installed Aria SDK; Qt/NDK/Apple SDK inputs remain explicit."""
    if tls and not http:
        raise ValueError("Aria TLS requires the HTTP feature")
    required = ["json", "mira"] if http else []
    if tls:
        required.append("openssl")
    return _variant("aria", {"ARIA_BUILD_HTTP": http, "ARIA_HTTP_ENABLE_TLS": tls,
        "ARIA_BUILD_QT6": qt, "ARIA_BUILD_JNI": jni, "ARIA_BUILD_APPKIT": appkit,
        "ARIA_BUILD_UIKIT": uikit, "ARIA_BUILD_SHARED": shared}, required)


def make_mira_recipe(*, tls=False, websocket=False, http2=False, http3=False, dnssec=False):
    """Select an installed Mira SDK and its actual external artifact graph."""
    required = []
    if tls or websocket or http3 or dnssec:
        required.append("openssl")
    if websocket:
        required.append("zlib")
    if http2:
        required.append("nghttp2")
    if http3:
        required.extend(("nghttp3", "ngtcp2"))
    return _variant("mira", {"MIRA_ENABLE_TLS": tls, "MIRA_ENABLE_WEBSOCKET": websocket,
        "MIRA_ENABLE_HTTP2": http2, "MIRA_ENABLE_HTTP3": http3, "MIRA_ENABLE_DNSSEC": dnssec}, required)


def make_sdk_config(*, aria_options=(), extra_packages=(), **features):
    """Return the complete shared Aria SDK graph for make_aria_recipe features."""
    from pathlib import Path
    from forgedeps import ProjectConfig
    from . import get_recipe
    from .configuration import PATCH_VERSIONS, PROVIDERS
    from .bindings import build_curl, build_ngtcp2
    from .openssl import build_openssl
    from .resolve import resolve_recipe
    selected = make_aria_recipe(**features)
    if any(not item.startswith("-D") for item in aria_options):
        raise ValueError("aria_options must contain CMake definitions")
    selected = replace(selected, options=(*selected.options, *aria_options))
    recipes = {"aria": selected, "mira": make_mira_recipe(tls=features.get("tls", False))}
    result, seen = [], set()
    def visit(name):
        if name in seen:
            return
        dependency = recipes.get(name) or get_recipe(name)
        for required in dependency.requires:
            visit(required)
        seen.add(name)
        result.append(dependency)
    visit("aria")
    for name in extra_packages:
        visit(name)
    return ProjectConfig(name="aria-sdk", recipes=tuple(result),
        builders={"openssl": build_openssl, "curl": build_curl, "ngtcp2": build_ngtcp2},
        resolve_recipe=resolve_recipe, patches_dir=Path(__file__).with_name("patches"),
        patch_versions=PATCH_VERSIONS, providers=PROVIDERS)


def make_curl_recipe(*, cli=False, http2=False, http3=False):
    """Build curl with explicit protocol artifacts and an optional test CLI."""
    required = ['zlib', 'openssl']
    if http2:
        required.append('nghttp2')
    if http3:
        required.extend(('nghttp3', 'ngtcp2'))
    return _variant('curl', {'BUILD_CURL_EXE': cli, 'BUILD_STATIC_CURL': cli,
        'BUILD_SHARED_LIBS': False, 'BUILD_STATIC_LIBS': True,
        'USE_NGHTTP2': http2, 'USE_NGTCP2': http3}, required)
