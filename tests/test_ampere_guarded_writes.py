"""MIT nxnative 9507c221 regression, adapted to the production NativeAOT service.
Constructed instruction sequence models a guarded deferred write followed by an inverted-guard write.
"""
import json,os,platform,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
XLATE=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','native Mac translator required')
class GuardedWrites(unittest.TestCase):
    def test_false_issue_guard_does_not_commit_a_stale_shadow(self):
        # MOV R5 from uniform; P0 compare; EX2.P0 R17 with barrier 3; MUL.!P0 R17;
        # wait, MUL R17; an image atomic retains the computed value; EXIT.
        instructions=[(0x000fe20000000f00,0x0100000000057a02),(0x000fda0003f06070,0x00c0060005007a0c),
                      (0x000ee20000000800,0x0000002000170308),(0x000fe20000410000,0x0000001d1d178220),
                      (0x008fe20000410000,0x0000001724177220),(0x002ea200001ee000,0x00000c17030c7593),
                      (0x000fea0003800000,0x794d)]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'code.bin').write_bytes(b''.join(struct.pack('<QQ',lo,hi) for hi,lo in instructions))
            rq=dict(variant='guarded',stage='cs',arch='sm86',code=str(p/'code.bin'),tex={},img={},attr={},fout={},local=[32,1,1],debug=True,nvn2_cs=[0,0,3,0x40,0])
            r=subprocess.run([str(XLATE),'--service','--spirv-cross','(linked in)','--out',td,'--chain','guard-test'],input=json.dumps(rq)+'\n',capture_output=True,text=True,timeout=90)
            self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(json.loads(r.stdout)['ok'],r.stdout+r.stderr)
            source=(p/'guarded_b.metal').read_text()
            self.assertRegex(source,r'\? 1065353216 : 0;','issue guard must be captured as a stable, non-denormal word')
            self.assertRegex(source,r'bool \w+ = \w+ != 0;\s+float \w+ = \w+;\s+if \(\w+\)','the deferred commit must obey the captured guard')
