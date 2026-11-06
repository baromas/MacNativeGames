"""An unverified driver field is rejected by default; the OoT-only experiment is exact and opt-in."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='darwin','Foundation/Metal headers required')
class OotDriverZero(unittest.TestCase):
    def test_exact_opt_in_leaves_other_variants_and_unknown_fields_rejected(self):
        env={k:v for k,v in os.environ.items() if not k.startswith(('TOTK_','DM_'))}
        with tempfile.TemporaryDirectory() as d:
            for variant,flags in [('base',[]),('dkb',['-DGAME_DKB=1','-DGAME_NS2=1']),('oot',['-DGAME_OOT=1','-DGAME_NS2=1'])]:
                program=Path(d)/variant
                built=subprocess.run(['xcrun','clang','-fobjc-arc','-Wall','-Wextra','-Werror',*flags,str(ROOT/'tests/oot_driver_zero_probe.m'),'-framework','Foundation','-framework','Metal','-o',str(program)],capture_output=True,text=True,timeout=60)
                self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                for switch,field,stage in [(None,'c0+0x640','vs'),('0','c0+0x640','vs'),('yes','c0+0x640','vs'),('1','c0+0x640','vs'),('1','c0+0x644','vs'),('1','c0+0x640,c0+0x644','vs'),('1','c0+0x640','ps'),('1','c0+0x640','cs')]:
                    with self.subTest(variant=variant,switch=switch,field=field,stage=stage):
                        ran=subprocess.run([str(program),field,stage],env=env|({} if switch is None else {'TOTK_OOT_C0_640_ZERO':switch}),capture_output=True,text=True,timeout=5)
                        self.assertEqual(ran.returncode,0,ran.stderr)
                        allowed=variant=='oot' and switch=='1' and field=='c0+0x640' and stage=='vs'
                        self.assertEqual(ran.stdout.strip(),f'{0 if allowed else 1} 1')
                        self.assertEqual('EXPERIMENT' in ran.stderr,allowed)
