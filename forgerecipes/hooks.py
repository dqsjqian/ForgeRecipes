"""Shared library attribution and static-library installation hooks."""

import hashlib
import shutil
import sys
from pathlib import Path
from forgedeps import Dependency

def normalize_zlib_static(prefix: Path) -> None:
    """Keep zlib's exports intact and supply names understood by FindZLIB.

    zlib 1.3.2 names Windows static libraries zs.lib/libzs.a. Older CMake
    FindZLIB modules do not search these names, so retain the original export
    location and add a byte-identical static-library compatibility name.
    """
    # zlib sets CMAKE_DEBUG_POSTFIX "d" unconditionally on Windows, so a Debug
    # build installs zsd.lib/libzsd.a. Each artifact prefix holds one
    # configuration, so either spelling supplies the same compatibility names.
    pairs = []
    for stem in ('zs', 'zsd'):
        pairs += [(stem + '.lib', 'zlibstatic.lib'), (stem + '.lib', 'z.lib'), ('lib' + stem + '.a', 'libz.a')]
    present = {name for name, _ in pairs if (prefix / 'lib' / name).is_file()}
    if {'zs.lib', 'zsd.lib'} <= present or {'libzs.a', 'libzsd.a'} <= present:
        raise ValueError(f'Release and Debug zlib archives share one prefix: {prefix}')
    for original, compatible in pairs:
        source, target = prefix / 'lib' / original, prefix / 'lib' / compatible
        if source.is_file():
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file() or hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest():
                    raise ValueError(f'Conflicting zlib static library preserved: {target}')
            else:
                shutil.copy2(source, target)


def json_attributions(prefix: Path, source: Path, dep: Dependency) -> list[str]:
    notices = set()
    for header in (source / 'include/nlohmann').rglob('*.hpp'):
        for line in header.read_text(encoding='utf-8').splitlines():
            if 'SPDX-FileCopyrightText:' in line or 'SPDX-License-Identifier:' in line:
                notices.add(line)
    if not notices:
        raise ValueError('JSON embedded copyright notices are missing')
    target = prefix / "share/licenses" / dep.name / 'ATTRIBUTIONS.txt'
    target.write_text('\n'.join(sorted(notices)) + '\n', encoding='utf-8')
    return ['ATTRIBUTIONS.txt']


def sqlite3_dedication(prefix: Path, source: Path, dep: Dependency) -> list[str]:
    # The official amalgamation carries a public-domain dedication, not a LICENSE.
    header = (source / 'sqlite3.h').read_text(encoding='utf-8')
    dedication, separator, _ = header.partition('*************************************************************************')
    if not separator or 'author disclaims copyright' not in dedication:
        raise ValueError('SQLite public-domain dedication needs review')
    target = prefix / "share/licenses" / dep.name / 'PUBLIC-DOMAIN.txt'
    target.write_text(dedication, encoding='utf-8')
    return ['PUBLIC-DOMAIN.txt']


def zlib_windows_fixup(prefix: Path, source: Path, dep: Dependency) -> None:
    if sys.platform != 'win32':
        return
    normalize_zlib_static(prefix)
    for junk in ('lib/zlib.lib', 'lib/zlib.dll', 'lib/zlib1.dll',
                 'lib/libzlib.dll.a', 'bin/zlib.dll', 'bin/zlib1.dll', 'bin/libzlib.dll'):
        (prefix / junk).unlink(missing_ok=True)


