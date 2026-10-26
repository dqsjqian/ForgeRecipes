"""Content identity for external Qt SDK inputs used by installed SDK recipes."""
import hashlib
from pathlib import Path
import sys


def content_identity(paths):
    digest = hashlib.sha256(b'forgerecipes-qt-sdk-v1\0')
    for index, raw in enumerate(paths):
        path = Path(raw)
        if not path.exists():
            raise ValueError('Qt SDK input is missing: ' + str(path))
        files = sorted(item for item in path.rglob('*') if item.is_file()) if path.is_dir() else [path]
        for item in files:
            label = item.relative_to(path).as_posix() if path.is_dir() else item.name
            digest.update(f'{index}/{label}\0'.encode())
            with item.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
    return digest.hexdigest()


if __name__ == '__main__':
    print(content_identity(sys.argv[1:]))
