# Recipe provenance

The Python recipes, CMake templates, support hooks and patches were extracted
from the existing MIT-licensed AriaRead, Mira and ForgeDeps implementations.
Copyright (c) 2026 dqsjqian is retained in LICENSE. Extraction used these
checkouts and their in-progress dependency migration changes:

- AriaRead base: `93690776861be8d9b779777430d995e4803752b4`
- Mira base: `3f89424c157ed46dffae9b6e463f1cfa3886aec6`
- ForgeDeps base: `d97d94712f1ebc3aabd2a87cd6ae6e85272e802d`

This package does not bundle dependency source archives or installed libraries.
Patches and the QuickJS portability shim retain their source comments.
Runtime license installation retains each upstream license and embedded notices.
The additional ngtcp2 license texts and exact upstream hashes are documented in
`forgerecipes/licenses/SOURCES.md`. Those texts retain their original terms.
