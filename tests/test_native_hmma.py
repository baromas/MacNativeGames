"""Constructed Ampere instructions exercise the shipped translator and final Metal compilation."""
import json,os,platform,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
XLATE=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
def inst(lo,hi):return struct.pack('<QQ',lo,hi)
def program():
    code=b''.join(inst((0x3c003c00<<32)|(r<<16)|0x7802,0x000fc60000000f00) for r in range(6))
    code+=b''.join(inst((r<<16)|0x7802,0x000fc60000000f00) for r in (6,7))
    code+=inst((4<<32)|(0<<24)|(20<<16)|0x723c,0x000fe20000000806)
    code+=inst((0x20<<40)|(20<<32)|(255<<24)|0x7388,0x000fe80000000800)
    return code+inst(0x794d,0x000fea0003800000)
@unittest.skipUnless(platform.system()=='Darwin' and platform.machine()=='arm64','native Mac translator required')
class NativeHmma(unittest.TestCase):
    def test_ampere_helper_is_lowered_to_native_matrices(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'code.bin').write_bytes(program());(p/'jobs.json').write_text(json.dumps([dict(key='synthetic',stage='cs',arch='sm86',code=str(p/'code.bin'),tex={},img={},attr={},fout={},local=[32,1,1],debug=True,shared=0x400,nvn2_cs=[0,0,0,0x40,0])]))
            job=json.loads((p/'jobs.json').read_text())[0];job['variant']='synthetic'
            r=subprocess.run([str(XLATE),'--service','--spirv-cross','(linked in)','--out',td,'--chain','synthetic-test'],input=json.dumps(job)+'\n',capture_output=True,text=True,timeout=90)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            self.assertTrue(json.loads(r.stdout)['ok'],r.stdout+r.stderr)
            source=p/'synthetic_b.metal';s=source.read_text()
            self.assertIn('simdgroup_multiply_accumulate(',s)
            self.assertNotIn('%(',s)
            r=subprocess.run(['xcrun','-sdk','macosx','metal','-c',str(source),'-o',str(p/'out.air')],capture_output=True,text=True,timeout=90)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
