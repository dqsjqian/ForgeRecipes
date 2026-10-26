from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from forgerecipes import bindings
from forgerecipes.sdk_identity import content_identity

@dataclass
class Context:
    options: dict
    requires: dict
    target: dict

class BindingTests(unittest.TestCase):
    def test_ngtcp2_binds_ssl_to_required_artifact(self):
        ctx = Context({'cmake_options': ['-DOPENSSL_ROOT_DIR=/untracked', '-DKEEP=1']},
                      {'openssl': SimpleNamespace(prefix=Path('/shared/ssl'))}, {})
        with patch.object(bindings, 'build_cmake') as build:
            bindings.build_ngtcp2(ctx)
        self.assertEqual(build.call_args.args[0].options['cmake_options'],
                         ['-DKEEP=1', '-DOPENSSL_ROOT_DIR=/shared/ssl'])
        with self.assertRaisesRegex(ValueError, 'requires an artifact'):
            bindings.build_ngtcp2(Context({}, {}, {}))

    def test_sdk_identity_detects_binary_and_header_edits_and_survives_move(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second = root / 'first', root / 'second'
            first.mkdir(); second.mkdir()
            for folder in (first, second):
                (folder / 'header.hpp').write_bytes(b'header')
                (folder / 'QtCore.lib').write_bytes(b'library')
            before = content_identity([first])
            self.assertEqual(before, content_identity([second]))
            (first / 'QtCore.lib').write_bytes(b'changed library')
            self.assertNotEqual(before, content_identity([first]))
            (first / 'QtCore.lib').write_bytes(b'library')
            (first / 'header.hpp').write_bytes(b'changed header')
            self.assertNotEqual(before, content_identity([first]))

if __name__ == '__main__':
    unittest.main()
