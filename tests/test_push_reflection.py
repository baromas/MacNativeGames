import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(sys.platform=="darwin","Metal headers required")
class PushReflection(unittest.TestCase):
 def test_reserved_bank_and_existing_driver_banks(self):
  with tempfile.TemporaryDirectory() as d:
   for flags in ([],["-DGAME_NS2=1","-DGAME_OOT=1"]):
    with self.subTest(flags=flags):
     p=Path(d)/"probe"
     r=subprocess.run(["xcrun","clang","-fobjc-arc",*flags,str(ROOT/"tests/push_reflection_probe.m"),"-framework","Foundation","-framework","Metal","-o",str(p)],capture_output=True,text=True)
     self.assertEqual(r.returncode,0,r.stderr)
     self.assertEqual(subprocess.run([str(p)]).returncode,0)
