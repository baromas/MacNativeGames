"""Run the production MSL rewrite on a constructed helper, then verify actual Metal matrix arithmetic. No game data."""
import argparse,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');a=p.parse_args()
helper='''
uint dmsh_hmma16816_f16(uint lane, uint blk, uint a0, uint a1, uint a2, uint a3, uint b0, uint b1, uint acc0, uint acc1, thread uint& d1, threadgroup uint* scratch)
{
 d1=0; return 0;
}
'''
kernel='''
uint packh(half a,half b){return as_type<uint>(half2(a,b));}
half A(uint r,uint k,uint g){return half(int((r*3+k+g)%5)-2);}
half B(uint k,uint n,uint g){return half(int((k*2+n+g)%5)-2);}
half C(uint r,uint n,uint g){return half(int((r+n+g)%3)-1);}
kernel void probe(device float *out [[buffer(0)]],uint lane [[thread_index_in_simdgroup]],uint group [[simdgroup_index_in_threadgroup]]){
 threadgroup uint scratch[4*256];uint g=lane>>2,t=lane&3,d1;
 uint a0=packh(A(g,2*t,group),A(g,2*t+1,group)),a1=packh(A(g+8,2*t,group),A(g+8,2*t+1,group));
 uint a2=packh(A(g,8+2*t,group),A(g,9+2*t,group)),a3=packh(A(g+8,8+2*t,group),A(g+8,9+2*t,group));
 uint b0=packh(B(2*t,g,group),B(2*t+1,g,group)),b1=packh(B(8+2*t,g,group),B(9+2*t,g,group));
 uint c0=packh(C(g,2*t,group),C(g,2*t+1,group)),c1=packh(C(g+8,2*t,group),C(g+8,2*t+1,group));
 uint d0=dmsh_hmma16816_f16(lane,group*256,a0,a1,a2,a3,b0,b1,c0,c1,d1,scratch);
 d0=dmsh_hmma16816_f16(lane,group*256,a0,a1,a2,a3,b0,b1,d0,d1,d1,scratch);
 half2 lo=as_type<half2>(d0),hi=as_type<half2>(d1);
 out[group*128+g*8+t*2]=float(lo.x);out[group*128+g*8+t*2+1]=float(lo.y);
 out[group*128+(g+8)*8+t*2]=float(hi.x);out[group*128+(g+8)*8+t*2+1]=float(hi.y);
}
'''
with tempfile.TemporaryDirectory() as td:
 d=Path(td);(d/'Hmma.cs').write_text((ROOT/'games/totk/tools/totk_xlate/Hmma.cs').read_text())
 (d/'probe.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>')
 (d/'Program.cs').write_text('''using System; using System.IO;
class RuntimeError : Exception {public RuntimeError(string s):base(s){}}
class Program {static int Main(string[] a){string s=File.ReadAllText(a[0]); string r=Hmma.Rewrite(s);if(Hmma.Rewrite("no helper")!="no helper")return 2;try{Hmma.Rewrite("dmsh_hmma16816_f16 malformed");return 3;}catch(InvalidOperationException){} File.WriteAllText(a[1],r);return 0;}}
''')
 src='#include <metal_stdlib>\n#include <simd/simd.h>\nusing namespace metal;\n'+helper+kernel
 (d/'in.metal').write_text(src)
 subprocess.run([a.dotnet,'run','--project',str(d/'probe.csproj'),'-c','Release','--',str(d/'in.metal'),str(d/'out.metal')],check=True)
 subprocess.run(['xcrun','clang','-fobjc-arc',str(ROOT/'tests/hmma_gpu_probe.m'),'-framework','Foundation','-framework','Metal','-o',str(d/'gpu')],check=True)
 env=os.environ|{'MTL_DEBUG_LAYER':'1'}
 subprocess.run([str(d/'gpu'),str(d/'out.metal')],check=True,env=env)
 # The intentionally wrong old scalar stand-in must not accidentally satisfy the numerical test.
 negative=subprocess.run([str(d/'gpu'),str(d/'in.metal')],capture_output=True,text=True,env=env)
 if negative.returncode!=6:raise RuntimeError('negative control did not fail numeric comparison: '+negative.stderr)
 print('Unrewritten zero helper fails numerical control as expected. Signature rejection and no-helper preservation passed.')
