/* Constructed kernel only: JSON -> push commands -> immutable argument snapshots -> GPU. */
static int probe_push_constants(void) {
    NSError *error=nil;
    NSString *source=@"#include <metal_stdlib>\nusing namespace metal; struct A {constant uint *push [[id(0)]]; device uint *out [[id(1)]];}; kernel void probe(constant A &a [[buffer(0)]],uint i [[thread_position_in_grid]]) {a.out[i]=a.push[i];}";
    id<MTLLibrary> lib=[g_dev newLibraryWithSource:source options:nil error:&error];
    if(!lib)MDIE("push probe compile: %s",error.localizedDescription.UTF8String);
    NvShader *cs=[NvShader new];cs->fn=[lib newFunctionWithName:@"probe"];cs->stage=5;strlcpy(cs->key,"probe-push",sizeof cs->key);
    NSDictionary *json=@{@"route":@"B",@"bindings":@[@{@"kind":@"drvcb",@"bank":@24,@"arg_id":@0},@{@"kind":@"sbuf",@"reg":@0,@"rw":@YES,@"arg_id":@1}],@"drv_unfillable":@[]};
    char why[200];if(nvn_refl_from_json(json,&cs->rf,why,sizeof why))MDIE("push reflection: %s",why);
    cs->rf.tg[0]=64;cs->rf.tg[1]=cs->rf.tg[2]=1;cs->ae=[cs->fn newArgumentEncoderWithBufferIndex:0];cs->arg_len=cs->ae.encodedLength;
    const char *neg=getenv("TOTK_PROBE_NEGATIVE");if(neg&&atoi(neg)==32)cs->rf.b[0].kind=NVN_RB_DRV0;
    NvProg *pr=[NvProg new];pr->sh[5]=cs;prog_t p={.serial=0xfffff910};serial_put(p.serial,pr);
    uint32_t *mem=NULL;if(posix_memalign((void **)&mem,16384,16384))MDIE("push probe allocation");memset(mem,0,16384);mtl_pool_add(mem,16384);
    op_hdr end={OP_END,8};mtl_sub_begin();mtl_exec((const uint8_t *)&end);S.cprog=&p;
    uint32_t expected[3][64];for(unsigned i=0;i<64;i++)expected[0][i]=0x12340000+i;
    memcpy(expected[1],expected[0],256);expected[1][17]=0xaabbccdd;memcpy(expected[2],expected[1],256);
    struct {op_hdr h;uint16_t compute,offset;uint32_t size;uint32_t data[64];op_hdr end;} op={.h={OP_PUSH_CONST,272},.compute=1,.size=256,.end={OP_END,8}};
    memcpy(op.data,expected[0],256);mtl_exec((const uint8_t *)&op);
    for(unsigned round=0;round<3;round++) {
        if(round==1){op.offset=68;op.size=4;op.data[0]=expected[1][17];mtl_exec((const uint8_t *)&op);}
        if(round==2){op.compute=0;op.offset=0;op.size=256;memset(op.data,0xed,256);mtl_exec((const uint8_t *)&op);}
        S.ssbo[5][0]=(p_bind_buf){5,0,(uint64_t)(uintptr_t)(mem+round*64),256};args_dirty_all();p_dispatch dp={1,1,1,0};dispatch(&dp);
    }
    S.cprog=NULL;mtl_sub_commit();mtl_finish();
    for(unsigned r=0;r<3;r++)for(unsigned i=0;i<64;i++)if(mem[r*64+i]!=expected[r][i])MDIE("push probe round%u word%u got%#x want%#x",r,i,mem[r*64+i],expected[r][i]);
    memset(S.push,0,sizeof S.push);memset(&S.ssbo[5][0],0,sizeof S.ssbo[5][0]);mtl_prog_release(&p);mtl_pool_del(mem);mtl_finish();free(mem);return 192;
}
