"""Reusable external library build recipes.

The package contains build descriptions and license material, not vendor source.
"""

__version__ = "0.1.0"

from .inputs import recipe_input_files
from .sdk import make_aria_recipe, make_mira_recipe, make_sdk_config, make_curl_recipe


def get_recipe(name):
    """Return one shared recipe, including every external identity input."""
    from .catalog import RECIPES
    from .inputs import with_inputs
    from .protocols import get_protocol_recipe
    for dependency in RECIPES:
        if dependency.name == name:
            return with_inputs(dependency)
    return get_protocol_recipe(name)


def cmake_dir():
    """Directory containing the preserved Aria OpenSSL CMake recipe assets."""
    from pathlib import Path
    return Path(__file__).resolve().with_name("cmake")
