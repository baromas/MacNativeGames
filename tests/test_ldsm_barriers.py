"""Translate a constructed Ampere shared-memory program; check actual SPIR-V ordering."""
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRANSLATOR = Path(os.environ.get('MNG_TEST_XLATE', ROOT / 'games/totk/prebuilt/macos-arm64/totk_xlate'))


def instruction(low, high):
    return struct.pack('<QQ', low, high)


def synthetic_program(transposed=True):
    # Construct MOV R3, 0x40; LDSM.16.[M/MT]88.4 R20, [R3]; STS.U32 [RZ+0x20], R20; EXIT.
    # ISA fields, not bytes from a game: the final store retains the loaded result through optimization.
    return b''.join((instruction((0x40 << 32) | (3 << 16) | 0x7802, 0x000fc60000000f00),
                     instruction((3 << 24) | (20 << 16) | 0x783b, 0x000fe20000000200 | (int(transposed) << 14)),
                     instruction((0x20 << 40) | (20 << 32) | (255 << 24) | 0x7388, 0x000fe80000000800),
                     instruction(0x794d, 0x000fea0003800000)))


def instructions(data):
    words = struct.unpack('<' + 'I' * (len(data) // 4), data)
    if words[0] != 0x07230203:
        raise ValueError('not SPIR-V')
    at = 5
    while at < len(words):
        count, opcode = words[at] >> 16, words[at] & 65535
        if not count or at + count > len(words):
            raise ValueError('invalid SPIR-V instruction')
        yield opcode, words[at + 1:at + count]
        at += count


@unittest.skipUnless(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'requires native Mac shader translator')
class LDSMBarriers(unittest.TestCase):
    def test_collective_reads_are_between_two_subgroup_memory_barriers(self):
        for transposed in (False, True):
            with self.subTest(transposed=transposed), tempfile.TemporaryDirectory() as folder:
                work = Path(folder)
                code = work / 'synthetic.bin'
                code.write_bytes(synthetic_program(transposed))
                jobs = work / 'jobs.json'
                jobs.write_text(json.dumps([dict(key='synthetic', stage='cs', arch='sm86', code=str(code),
                                                tex={}, img={}, attr={}, fout={}, local=[32, 1, 1],
                                                debug=True, shared=0x400, nvn2_cs=[0, 0, 0, 0x40, 0])]))
                command = ['dotnet', str(TRANSLATOR)] if TRANSLATOR.suffix == '.dll' else [str(TRANSLATOR)]
                ran = subprocess.run([*command, str(jobs), folder], capture_output=True, text=True, timeout=90)
                self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
                spv = work / 'synthetic.spv'
                self.assertTrue(spv.is_file(), ran.stdout + ran.stderr)
                ops = list(instructions(spv.read_bytes()))
                constants = {args[1]: args[2] for op, args in ops if op == 43 and len(args) == 3}
                barriers = [i for i, (op, _) in enumerate(ops) if op == 224]  # OpControlBarrier
                shared_pointers = {args[1] for op, args in ops if op == 59 and args[2] == 4}  # OpVariable Workgroup
                for op, args in ops:
                    if op in (65, 66) and args[2] in shared_pointers:  # Op[InBounds]AccessChain
                        shared_pointers.add(args[1])
                loads = [i for i, (op, args) in enumerate(ops) if op == 61 and args[2] in shared_pointers]
                self.assertEqual(len(barriers), 2, 'missing LDSM subgroup barriers')
                self.assertTrue(loads and barriers[0] < loads[0] and loads[-1] < barriers[1], ops)
                for i in barriers:
                    self.assertEqual(tuple(constants[x] for x in ops[i][1]), (3, 3, 0x108),
                                     'subgroup execution/memory scopes with acquire-release workgroup memory')
                cross = os.environ.get('MNG_TEST_SPIRV_CROSS')
                if cross:
                    msl = work / 'synthetic.metal'
                    converted = subprocess.run([cross, '--msl', '--msl-version', '20300', str(spv), '--output', str(msl)],
                                               capture_output=True, text=True, timeout=30)
                    self.assertEqual(converted.returncode, 0, converted.stdout + converted.stderr)
                    self.assertEqual(msl.read_text().count('simdgroup_barrier(mem_flags::mem_threadgroup)'), 2)
                    built = subprocess.run(['xcrun', '-sdk', 'macosx', 'metal', '-c', str(msl), '-o', str(work / 'synthetic.air')],
                                           capture_output=True, text=True, timeout=60)
                    self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
