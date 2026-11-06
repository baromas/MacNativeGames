"""Run production SDK 22 adapters with generated packets, independent of game data."""
import importlib.util
import os
import platform
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ns2_codec_probe', ROOT / 'games/totk/tests/ns2_codec/run.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
PREFIX = Path(os.environ.get('MNG_DAV1D_PREFIX', ROOT / 'games/totk/build/dav1d/install'))


@unittest.skipUnless(sys.platform == 'darwin' and platform.machine() == 'arm64', 'requires Apple silicon SDK')
class NS2Codec(unittest.TestCase):
    def test_native_image_resource_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            result = probe.native_image(Path(directory))
        self.assertEqual(result['status'], 'pass')
        self.assertTrue(result['invalid_handles_and_formats'])
        self.assertTrue(result['pool_reuse_and_teardown'])

    @unittest.skipUnless((PREFIX / 'lib/libdav1d.a').is_file() and
                         Path('/opt/homebrew/opt/libvpx/lib/libvpx.a').is_file(),
                         'build pinned dav1d first, or set MNG_DAV1D_PREFIX to its install directory')
    def test_sdk22_av1_and_native_pools(self):
        with tempfile.TemporaryDirectory() as directory:
            results = probe.codec(Path(directory), PREFIX)
        for backend, result in results.items():
            with self.subTest(backend=backend):
                self.assertEqual(result['status'], 'pass')
                self.assertEqual(result['cases'], 6)
                self.assertEqual(result['events_destroyed'], 12)
                self.assertEqual(result['native_writes'], 8)
                self.assertGreaterEqual(result['movie_clock_checks'], 90)
