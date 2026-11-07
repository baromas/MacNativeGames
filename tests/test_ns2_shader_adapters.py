"""Production C# adapters on constructed MSL/control headers, never game shaders."""
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import unittest
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
CS=ROOT/'games/totk/tools/totk_xlate'
DOTNET=shutil.which('dotnet') or '/usr/local/share/dotnet/dotnet'
@unittest.skipUnless(platform.system()=='Darwin' and Path(DOTNET).is_file(),'native .NET/Metal toolchain required')
class Ns2ShaderAdapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.work=Path(cls.temp.name)
        files=[CS/n for n in ('BaseInstance.cs','Pools.cs','MeshStage.cs')]+[ROOT/'tests/ns2_shader_adapter_probe.cs']
        project='<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup>'+''.join('<Compile Include="'+escape(str(f))+'"/>' for f in files)+'</ItemGroup></Project>'
        (cls.work/'probe.csproj').write_text(project)
        p=subprocess.run([DOTNET,'build',str(cls.work/'probe.csproj'),'-c','Release','-o',str(cls.work/'out')],capture_output=True,text=True,timeout=120)
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def run_adapter(self,op,source,ok=True):
        p=subprocess.run([DOTNET,str(self.work/'out/probe.dll'),op],input=source,text=True,capture_output=True,cwd=self.work,timeout=20)
        self.assertEqual(p.returncode,0 if ok else 1,p.stdout+p.stderr)
        return p.stdout if ok else p.stderr
    def compile_metal(self,source):
        (self.work/'synthetic.metal').write_text(source)
        p=subprocess.run(['xcrun','-sdk','macosx','metal','-std=metal3.2','-c',str(self.work/'synthetic.metal'),'-o',str(self.work/'synthetic.air')],capture_output=True,text=True,timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_base_instance_lowering_and_unestablished_lanes(self):
        head='#include <metal_stdlib>\nusing namespace metal;\nstruct Driver { float4 _m0[101]; };\nstruct Args { constant Driver* vp_c0 [[id(0)]]; };\n'
        vertex='vertex float4 main0(constant Args& spvDescriptorSet0 [[buffer(0)]])\n{\nreturn float4(as_type<uint>((*spvDescriptorSet0.vp_c0)._m0[100].y));\n}\n'
        original=head+vertex
        lowered=self.run_adapter('base',original)
        self.assertIn('[[base_instance]]',lowered);self.assertNotIn('_m0[100].y',lowered)
        self.compile_metal(lowered)
        self.assertEqual(self.run_adapter('base',lowered),lowered)
        existing=original.replace('[[buffer(0)]])','[[buffer(0)]], uint gl_BaseInstance [[base_instance]])')
        lowered_existing=self.run_adapter('base',existing)
        self.assertIn('as_type<float>(int(gl_BaseInstance))',lowered_existing)
        self.assertEqual(lowered_existing.count('[[base_instance]]'),1)
        self.assertNotIn('_m0[100].y',lowered_existing)
        self.compile_metal(lowered_existing)
        for bad in (original.replace('[100].y','[100].x'),original.replace('vertex ','fragment '),original.replace('return float4','return float4((*spvDescriptorSet0.vp_c0)._m0[100].x) + float4')):
            self.assertEqual(self.run_adapter('base',bad),bad)
    def test_pool_tables_renumber_ids_and_preserve_small_arrays(self):
        src='struct spvDescriptorSetBuffer0\n{\n    array<texture2d<float>, 8192> cp_t_cb0_40000000 [[id(3)]];\n    array<sampler, 4096> cp_s_cb0_40000000 [[id(8195)]];\n    array<texture2d<float>, 4> fixed_tex [[id(12291)]];\n};\nfloat4 a = args.cp_t_cb0_40000000[t[idx[2]]].read(uint2(0));\n'
        out=self.run_adapter('pool',src)
        self.assertIn('constant spvPool_cp_t_cb0_40000000*',out)
        self.assertIn('fixed_tex [[id(2)]]',out)
        self.assertIn('min(uint(t[idx[2]]), args.cp_t_cb0_40000000->n)',out)
        self.assertEqual(self.run_adapter('pool',out),out)
    def mesh_request(self,mp=126,kind='ms'):
        ctl=bytearray(0xc0);struct.pack_into('<II',ctl,0,0x98761234,0xc9)
        struct.pack_into('<I',ctl,0x38,0x90);struct.pack_into('<II',ctl,0x40,0x90,0x90)
        ctl[0x56]=6 if kind=='ts' else 7;struct.pack_into('<H',ctl,0x58,128)
        struct.pack_into('<HH',ctl,0x60,128,mp)
        area=bytearray(0x90);area[0x35]=0xf0
        code=self.work/'area.bin';code.write_bytes(area)
        return dict(variant='constructed',stage=kind,arch='sm86',mesh_control=ctl.hex(),code=str(code))
    def test_mesh_padding_indices_fit_in_allocated_stage_memory(self):
        for mp in (1,31,32,33,63,64,126,127,128,255,256):
            rq=self.mesh_request(mp)
            out=json.loads(self.run_adapter('prepare',json.dumps(rq)))
            prim=out['mesh_layout'][3]
            # Zero-output meshlets write every lane, including the final block's padding.
            last=prim+4+3*((mp+31)//32)*32-1
            self.assertLess(last,out['shared']);self.assertLessEqual(out['shared'],32768)
        old_33=prim=2304+4*4*128
        self.assertGreaterEqual(prim+4+3*64-1,((old_33+4+3*33+15)//4+4)*4)
    def test_object_and_mesh_wrappers_compile(self):
        for kind in ('ts','ms'):
            prepared=json.loads(self.run_adapter('prepare',json.dumps(self.mesh_request(kind=kind))))
            words=prepared['shared']//4
            source='#include <metal_stdlib>\nusing namespace metal;\ntemplate<typename T, size_t N> struct spvUnsafeArray { T e[N]; threadgroup T& operator[](size_t i) threadgroup { return e[i]; } };\n'
            source+=f'kernel void main0(uint lane [[thread_position_in_threadgroup]])\n{{\n    threadgroup spvUnsafeArray<uint, {words}> stage_data;\n    stage_data[lane] = lane;\n}}\n'
            wrapped=self.run_adapter('wrap',json.dumps(dict(source=source,info=prepared['mesh_stage'])))
            self.assertIn('threadgroup_barrier(mem_flags::mem_threadgroup)',wrapped)
            self.compile_metal(wrapped)
    def test_malformed_control_is_rejected(self):
        rq=self.mesh_request();rq['mesh_control']='00'*0xc0
        self.assertIn('control section',self.run_adapter('prepare',json.dumps(rq),False))

    def test_mesh_vertex_and_primitive_attribute_blocks_are_separate(self):
        for verts,topology in ((1,'point'),(2,'line'),(3,'triangle')):
            with self.subTest(topology=topology):
                rq=self.mesh_request(mp=64)
                ctl=bytearray.fromhex(rq['mesh_control'])
                ctl[0x5f]=verts
                ctl[0x68]=0x80
                struct.pack_into('<I',ctl,0x64,0x90)
                struct.pack_into('<II',ctl,0x40,0x110,0x110)
                code=Path(rq['code'])
                area=bytearray(code.read_bytes())+bytearray(0x80)
                area[0x35]=0xf8         # point size, then four position components
                area[0x36]=0x10         # vertex attribute 1, x only
                area[0x90+0x36]=0x0f    # four per-primitive attribute 0 components
                code.write_bytes(area)
                rq['mesh_control']=ctl.hex()
                prepared=json.loads(self.run_adapter('prepare',json.dumps(rq)))
                self.assertEqual(prepared['mesh_layout'],[0,64,2304,6400])
                words=prepared['shared']//4
                source='#include <metal_stdlib>\nusing namespace metal;\ntemplate<typename T, size_t N> struct spvUnsafeArray { T e[N]; threadgroup T& operator[](size_t i) threadgroup { return e[i]; } };\n'
                source+=f'kernel void main0(uint lane [[thread_position_in_threadgroup]])\n{{\n    threadgroup spvUnsafeArray<uint, {words}> stage_data;\n    stage_data[lane] = lane;\n}}\n'
                wrapped=self.run_adapter('wrap',json.dumps(dict(source=source,info=prepared['mesh_stage'])))
                self.assertIn(f'metal::topology::{topology}',wrapped)
                self.assertIn(f'np * {verts}u',wrapped)
                self.assertIn('576u + (v / 32u) * 192u',wrapped)
                self.assertIn('1344u + (p / 32u) * 128u',wrapped)
                self.assertEqual('[[point_size]]' in wrapped,verts==1)
                self.assertIn('o.position = float4(as_type<float>(stage_data[b + 32u])',wrapped)
                self.compile_metal(wrapped)
    def test_constructed_stage_store_through_production_native_service(self):
        xlate=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
        for kind in ('ts','ms'):
            rq=self.mesh_request(kind=kind)
            ctl=bytearray.fromhex(rq['mesh_control'])
            # Construct MOV R0,1; stage store [RZ+offset],R0; EXIT, using ISA fields.
            offset,mode=(4,0xb8) if kind=='ts' else (3,0x88)
            code=b''.join(struct.pack('<QQ',lo,hi) for lo,hi in [
                ((1<<32)|0x7802,0x000fc60000000f00),
                ((offset<<40)|(255<<24)|0x7927,0x000fe80000000000|(mode<<8)),
                (0x794d,0x000fea0003800000)])
            area=bytearray(0x80)+code;area[0x35]=0xf0
            Path(rq['code']).write_bytes(area)
            struct.pack_into('<I',ctl,0x38,len(area));struct.pack_into('<II',ctl,0x40,len(area),len(area))
            rq.update(mesh_control=ctl.hex(),tex={},img={},attr={},fout={},debug=True,variant='constructed_'+kind)
            p=subprocess.run([str(xlate),'--service','--spirv-cross','(linked in)','--out',str(self.work),'--chain','synthetic-mesh-test'],input=json.dumps(rq)+'\n',capture_output=True,text=True,timeout=90)
            self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['ok'],p.stdout+p.stderr)
            reflection=json.loads((self.work/(rq['variant']+'_b.json')).read_text())
            self.assertEqual(reflection['mesh_stage']['kind'],kind)
            self.assertEqual(reflection['drv_unfillable'],[])
            shader=(self.work/(rq['variant']+'_b.metal')).read_text()
            if kind=='ms':
                self.assertRegex(shader,r'\(\(threadgroup uchar\*\)&\w+\[0\]\)')
                self.assertNotIn('atomic_compare_exchange',shader)
            self.compile_metal(shader)

    def test_ampere_global_address_and_atomic_forms(self):
        # Adapted from nxnative's constructed SM86 fixtures, MIT. A memory
        # descriptor must not enter the address. INC and CAS must still write.
        xlate=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
        def lower(*operations):
            init=[(0x000e260000002100,0x7919|(r<<16)) for r in (9,19,20,21,22)]
            store=(0x000fe8000000c800,0x0000080609008388)
            body=[(hi|(0x3f<<52),lo) for hi,lo in (*operations,store)]
            code=self.work/'atomics.code'
            code.write_bytes(b''.join(struct.pack('<QQ',lo,hi) for hi,lo in (*init,*body,(0x000fea0003800000,0x794d))))
            rq=dict(variant='atomics',stage='cs',arch='sm86',code=str(code),tex={},img={},attr={},fout={},local=[32,1,1],debug=True,shared=4096,nvn2_cs=[0,0,3,0x40,0])
            p=subprocess.run([str(xlate),'--service','--spirv-cross','(linked in)','--out',str(self.work),'--chain','synthetic-atomic-test'],input=json.dumps(rq)+'\n',capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(json.loads(p.stdout)['ok'],p.stdout+p.stderr)
            return (self.work/'atomics_b.metal').read_text()
        set_descriptor=(0x000fe200000e0000,0x00000000130473c2)
        self.assertEqual(lower(set_descriptor,(0x000fe2200c1e1900,0x0000000414067981)),
                         lower(set_descriptor,(0x000fe2200c1e1900,0x0000003f14067981)))
        for op in ((0x000fe200001ee116,0x00000013140673a9),
                   (0x000fe200019ee100,0x00000013140673a8),
                   (0x000fe20001800000,0x000000141306738c)):
            shader=lower(op)
            self.assertIn('atomic_compare_exchange',shader)
            self.compile_metal(shader)

    def test_ampere_depth_follows_enabled_render_target_blocks(self):
        xlate=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
        for mask,depth in ((0,r'0[.]125'),(0xf,r'0[.]5'),(0x10f,r'0[.]75'),(0x80000001,r'0[.]75')):
            with self.subTest(mask=hex(mask)):
                header=bytearray(0x80)
                struct.pack_into('<I',header,0,0x000c5482)
                struct.pack_into('<I',header,0x14,0xb0000000)
                struct.pack_into('<II',header,0x48,mask,2)   # fragment outputs, depth written
                # MOV Rn, immediate; each possible depth register gets a
                # distinct value. EXIT emits the depth from the selected register.
                body=b''.join(struct.pack('<QQ',(value<<32)|(reg<<16)|0x7802,0x000fe20000000f00)
                              for reg,value in ((1,0x3e000000),(3,0x3e800000),(5,0x3f000000),(6,0x3e800000),(9,0x3f400000)))
                code=self.work/'depth.code'
                code.write_bytes(header+body+struct.pack('<QQ',0x794d,0x000fea0003800000))
                rq=dict(variant='depth',stage='ps',arch='sm86',code=str(code),tex={},img={},attr={},fout={})
                p=subprocess.run([str(xlate),'--service','--spirv-cross','(linked in)','--out',str(self.work),'--chain','synthetic-depth-test'],
                                 input=json.dumps(rq)+'\n',capture_output=True,text=True,timeout=30)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertTrue(json.loads(p.stdout)['ok'],p.stdout+p.stderr)
                shader=(self.work/'depth_b.metal').read_text()
                self.assertRegex(shader,rf'gl_FragDepth = {depth}\b')
                self.compile_metal(shader)

    def test_ampere_shared_half_word_store(self):
        xlate=Path(os.environ.get('MNG_TEST_XLATE',ROOT/'games/totk/prebuilt/macos-arm64/totk_xlate'))
        code=self.work/'shared_half.code'
        # MOV R0,0xbeef; STS.U16 [RZ+2],R0; EXIT.
        code.write_bytes(b''.join(struct.pack('<QQ',lo,hi) for lo,hi in (
            ((0xbeef<<32)|0x7802,0x000fe20000000f00),
            ((2<<40)|(255<<24)|0x7388,0x000fe80000000400),
            (0x794d,0x000fea0003800000))))
        rq=dict(variant='shared_half',stage='cs',arch='sm86',code=str(code),tex={},img={},attr={},fout={},
                local=[32,1,1],shared=4096,nvn2_cs=[0,0,3,0x40,0])
        p=subprocess.run([str(xlate),'--service','--spirv-cross','(linked in)','--out',str(self.work),'--chain','synthetic-store-test'],
                         input=json.dumps(rq)+'\n',capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['ok'],p.stdout+p.stderr)
        shader=(self.work/'shared_half_b.metal').read_text()
        self.assertIn('typedef ushort __attribute__((may_alias)) dm_ushort_alias;',shader)
        self.assertRegex(shader,r'\(\(threadgroup dm_ushort_alias\*\)&\w+\[0\]\)\[uint\(\w+\) >> 1u\]')
        self.assertNotIn('atomic_compare_exchange',shader)
        self.compile_metal(shader)
