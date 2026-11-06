#!/usr/bin/env python3
"""Synthetic production AV1/API and native-image tests; never opens a game window."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

GAME = Path(__file__).resolve().parents[2]


def checked(command, *, env=None):
    result = subprocess.run([str(x) for x in command], env=env, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{command[0]} exited {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result


def flags(sanitize=False):
    result = ['xcrun', 'clang', '-std=c11', '-O1' if sanitize else '-O2', '-g', '-Wall', '-Wextra', '-Werror',
              '-Wno-deprecated-declarations', '-DGAME_NS2=1', '-I' + str(GAME / 'third_party/d2r_gfx/gfx/nvn/include')]
    if sanitize:
        result += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    return result


def native_image(work, sanitize=False):
    binary = work / 'native-image-probe'
    checked([*flags(sanitize), GAME / 'third_party/d2r_gfx/gfx/nvn/ns2_native_image.c',
             GAME / 'tests/ns2_codec/native_image_probe.c', '-o', binary])
    return json.loads(checked([binary]).stdout)


def codec(work, prefix, sanitize=False):
    binary = work / 'codec-probe'
    checked([*flags(sanitize), '-I' + str(prefix / 'include'), '-I/opt/homebrew/opt/libvpx/include',
             GAME / 'tests/ns2_codec/probe.c', GAME / 'runtime/ns2_av1.c',
             prefix / 'lib/libdav1d.a', '/opt/homebrew/opt/libvpx/lib/libvpx.a',
             '-framework', 'VideoToolbox', '-framework', 'CoreMedia', '-framework', 'CoreVideo',
             '-framework', 'CoreFoundation', '-o', binary])
    clean = {k: v for k, v in os.environ.items() if not k.startswith(('TOTK_', 'DM_'))}
    return {name: json.loads(checked([binary], env=dict(clean, DM_AV1_DAV1D=value)).stdout)
            for name, value in [('automatic', '0'), ('dav1d', '1')]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dav1d-prefix', type=Path, default=GAME / 'build/dav1d/install')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='mng-ns2-codec-') as directory:
        work = Path(directory)
        print(json.dumps({'native_image': native_image(work, args.sanitize),
                          'codec': codec(work, args.dav1d_prefix.resolve(), args.sanitize)}, indent=2))
