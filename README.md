# ForgeRecipes

Development candidate for ForgeDeps 0.4. The package supplies reusable library
build recipes; ForgeDeps supplies source acquisition, content identities,
artifact storage, locking and environment receipts. No third-party source
archives or installed libraries are bundled.

The catalog contains zlib, OpenSSL, curl, JSON, SQLite, Gumbo, QuickJS,
sqlite_modern_cpp, doctest, Aria, Mira, nghttp2, nghttp3 and ngtcp2. Applications
keep their version locks and feature-selection policy in their own repositories.

```python
from forgerecipes import get_recipe, recipe_input_files, make_sdk_config
from forgerecipes.configuration import make_config

json_recipe = get_recipe("json")
config = make_config(("nghttp2", "nghttp3", "ngtcp2"))
# The ngtcp2 graph includes the same locked OpenSSL artifact used by consumers.
sdk = make_sdk_config(http=True, tls=True, shared=False)
```

`make_config(names)` assembles the requested recipe graph and its public
ForgeDeps callbacks. `make_aria_recipe`, `make_mira_recipe`, and
`make_curl_recipe` select library features without changing the consumer's lock.
The QuickJS resolver substitutes its locked release date. Patch support is
restricted to reviewed versions. SQLite and QuickJS providers verify official
release information and the available source digests.

`forgerecipes.openssl.build_openssl(ctx)` uses the exact compiler, configuration,
SDK and toolchain in ForgeDeps' `BuildContext`. The CMake driver retains the
upstream integration's Android, iOS, macOS, Linux, MSVC and MinGW branches.
Native macOS Release and Debug builds have been exercised; retained branches
and command-construction tests alone do not establish a new platform result.
OpenSSL, curl and ngtcp2 discover linked libraries through their recorded
artifact dependencies. Recipe builders never silently switch Clang to GCC.

`cmake_dir()/AriaSdk.cmake` exposes `forgerecipes_sdk(FILE lock ...)` for installed
Aria SDK consumers. Feature values and editable source overrides are explicit.
Qt libraries and headers are content hashed; the resulting SDK identity affects
only the Aria recipe, not unrelated libraries in the graph.

`recipe_input_files(name)` records package-relative implementation, patch,
shim and license inputs. Options and actual compiler/SDK identities also enter
the build fingerprint. JSON is header-only. Compiled recipes retain target and
configuration identities. Moving the Python package does not change a recipe's
content identity.

For local development, with the matching candidate checkout:

```sh
python -m pip install -e ../ForgeDeps -e .
python -m unittest discover -s tests -v
```

See [NOTICE.md](NOTICE.md) for extraction provenance and retained license texts.
Release tags and published installation instructions will follow acceptance.
