"""Recipe registry assembly without application profile or TLS selection policy."""
from pathlib import Path
from forgedeps import ProjectConfig
from . import providers
from .bindings import build_curl, build_ngtcp2
from .openssl import build_openssl
from .resolve import resolve_recipe

PATCH_VERSIONS = {'gumbo': {'0.10.1'}, 'quickjs': {'2026-06-04'},
                  'doctest': {'2.5.3'}}
PROVIDERS = {'sqlite': providers.resolve_sqlite, 'quickjs': providers.resolve_quickjs}

def make_config(names):
    from . import get_recipe
    result, seen = [], set()
    def visit(name):
        if name in seen:
            return
        dependency = get_recipe(name)
        for required in dependency.requires:
            visit(required)
        seen.add(name)
        result.append(dependency)
    for name in names:
        visit(name)
    return ProjectConfig(name='catalog', recipes=tuple(result),
        builders={'openssl': build_openssl, 'curl': build_curl, 'ngtcp2': build_ngtcp2},
        resolve_recipe=resolve_recipe, patches_dir=Path(__file__).with_name('patches'),
        patch_versions=PATCH_VERSIONS, providers=PROVIDERS)
