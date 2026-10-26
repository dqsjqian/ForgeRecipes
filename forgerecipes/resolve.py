"""Library-specific transformation after generic lock validation."""

from dataclasses import replace


def resolve_recipe(dependency, record):
    if dependency.name == "quickjs":
        return replace(dependency, cmake_lists=dependency.cmake_lists.replace(
            "@QUICKJS_VERSION@", record["version"]))
    return dependency
