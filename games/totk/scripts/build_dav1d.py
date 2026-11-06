#!/usr/bin/env python3
"""Build a pinned, static AV1 decoder without adding a Homebrew runtime dependency.

The source archive, build tools, compiler identity and resulting library hash are recorded locally. No game files
are read. Meson is prevented from downloading subprojects; its dependencies are in this folder's requirements.txt.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

VERSION = '1.5.4'
URL = f'https://code.videolan.org/videolan/dav1d/-/archive/{VERSION}/dav1d-{VERSION}.tar.bz2'
SHA256 = '2abfb0c89212e6e4733a54e0ae509ec00a5b845a6360946f918806e14aedb011'
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def build(work, jobs=2):
    work = work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    archive = work / f'dav1d-{VERSION}.tar.bz2'
    if not archive.exists() or digest(archive) != SHA256:
        partial = archive.with_suffix('.partial')
        request = urllib.request.Request(URL, headers={'User-Agent': 'MacNativeGames dependency build'})
        with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as out:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 64 * 1024 * 1024:
                    raise RuntimeError('dav1d archive unexpectedly exceeds 64 MiB')
                out.write(chunk)
        if digest(partial) != SHA256:
            raise RuntimeError('dav1d source SHA256 mismatch')
        partial.replace(archive)
    sources = work / 'src'
    source = sources / f'dav1d-{VERSION}'
    if not source.exists():
        sources.mkdir(exist_ok=True)
        with tarfile.open(archive) as package:
            package.extractall(sources, filter='data')
    target = work / 'objects'
    install = work / 'install'
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', ''))
    # A login shell may export an unrelated GCC from another project. This runtime is built with Xcode's Apple ABI.
    env['CC'] = subprocess.check_output(['xcrun', '--find', 'clang'], text=True).strip()
    env['CXX'] = subprocess.check_output(['xcrun', '--find', 'clang++'], text=True).strip()
    env['SDKROOT'] = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    meson = [sys.executable, '-m', 'mesonbuild.mesonmain']
    options = ['--buildtype=release', '--default-library=static', '--wrap-mode=nodownload',
               '--prefix=' + str(install), '--libdir=lib', '-Denable_tools=false', '-Denable_tests=false',
               '-Denable_examples=false']
    setup = [*meson, 'setup', str(target), str(source), *options]
    if (target / 'build.ninja').exists():
        setup.append('--reconfigure')
    subprocess.run(setup, env=env, check=True)
    subprocess.run([*meson, 'compile', '-C', str(target), '-j', str(jobs)], env=env, check=True)
    subprocess.run([*meson, 'install', '-C', str(target), '--no-rebuild'], env=env, check=True)
    library = install / 'lib/libdav1d.a'
    receipt = dict(version=VERSION, url=URL, source_sha256=SHA256, library_sha256=digest(library),
                   build_script_sha256=digest(Path(__file__)), sdk=env['SDKROOT'],
                   environment={key: env.get(key, '') for key in ('CC', 'CXX', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'MACOSX_DEPLOYMENT_TARGET')},
                   meson=importlib.metadata.version('meson'), ninja=importlib.metadata.version('ninja'),
                   compiler=subprocess.check_output(['xcrun', 'clang', '--version'], text=True).splitlines()[0],
                   options=options)
    (work / 'build.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return library


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'build/dav1d')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    print(build(args.work, args.jobs))
