/* Diagnostic only: isolate decoded movie output from NDVE reconstruction.
   Based on the matching/lifetime strategy in nxnative PR #1331, 76c20edba480db753ce7092cd2677f6c4a8daa15
   (MIT, third_party/licenses/nxnative.txt). This renderer uses an ordered compute scale instead of a render copy.
   No intermediate dispatch is skipped. This changes reconstruction quality, not a production correctness fix. */
static const char oot_movie_convert_key[] = "49dff010b9832251bb18e000c71a1ace470fd79dcf444a581132dd9f347becf7";
static const char oot_movie_final_key[] = "4f41ccf24f163e0dd5f7347190607a892a42575928fa6441245c43b7302d1440";
static int oot_movie_enabled(void) {
#if defined(GAME_OOT)
    static int enabled = -1;
    if (enabled < 0) { const char *e = getenv("TOTK_OOT_MOVIE_DIRECT"); enabled = e && !strcmp(e, "1"); }
    return enabled;
#else
    return 0;
#endif
}
static int oot_movie_role(const char *key) {
    if (strlen(key) < 64 || (key[64] && key[64] != '-')) return 0;
    if (!strncmp(key, oot_movie_convert_key, 64)) return 1;
    if (!strncmp(key, oot_movie_final_key, 64)) return 2;
    return 0;
}
static id<MTLTexture> oot_movie_image(NvShader *cs, unsigned slot, uint64_t *serial, int write) {
    int binding = 0;
    for (int i = 0; i < cs->rf.nb; i++) {
        const nvn_rbind *b = &cs->rf.b[i];
        if (b->kind == NVN_RB_IMG && b->reg == slot && b->rw && b->dtt == MTLTextureType2D) binding = 1;
    }
    if (!binding) return nil;
    int tid = (int)(S.img[5][slot] & 0xfffff);
    id<MTLTexture> t = nil;
    registry_lock();
    if (tid > 0 && tid < g_ntreg && g_treg[tid].ok) {
        void *p = NULL; (void)tex_image_rid(tid, &p, write); t = (__bridge id<MTLTexture>)p;
        if (serial) *serial = g_treg[tid].t.serial;
    }
    registry_unlock();
    if (t.textureType != MTLTextureType2D || t.sampleCount != 1 ||
        (t.pixelFormat != MTLPixelFormatRGBA8Unorm && t.pixelFormat != MTLPixelFormatRGBA8Unorm_sRGB) ||
        !swizzle_eq(t.swizzle, MTLTextureSwizzleChannelsDefault)) return nil;
    return t;
}
static int oot_movie_scale(id<MTLTexture> in, id<MTLTexture> out) {
    if (in.width != 1920 || in.height != 1080 || out.width != 2560 || out.height != 1440 || in == out ||
        in.textureType != MTLTextureType2D || out.textureType != MTLTextureType2D ||
        in.pixelFormat != MTLPixelFormatRGBA8Unorm ||
        (out.pixelFormat != MTLPixelFormatRGBA8Unorm && out.pixelFormat != MTLPixelFormatRGBA8Unorm_sRGB) ||
        !(in.usage & MTLTextureUsageShaderRead) || !(out.usage & MTLTextureUsageShaderWrite)) return 0;
    static id<MTLComputePipelineState> ps;
    static id<MTL4ArgumentTable> table;
    if (!ps || !table) {
        NSError *error = nil;
        NSString *source = @"#include <metal_stdlib>\nusing namespace metal;\n"
            "kernel void scale_movie(texture2d<float> src [[texture(0)]], texture2d<float,access::write> dst [[texture(1)]], uint2 p [[thread_position_in_grid]]) {"
            " if(p.x>=dst.get_width()||p.y>=dst.get_height()) return;"
            " constexpr sampler s(coord::normalized,address::clamp_to_edge,filter::linear);"
            " float2 uv=(float2(p)+0.5)/float2(dst.get_width(),dst.get_height()); dst.write(src.sample(s,uv,level(0)),p); }";
        id<MTLLibrary> lib = [g_dev newLibraryWithSource:source options:nil error:&error];
        id<MTLFunction> fn = lib ? [lib newFunctionWithName:@"scale_movie"] : nil;
        ps = fn ? [g_dev newComputePipelineStateWithFunction:fn error:&error] : nil;
        MTL4ArgumentTableDescriptor *ad = [MTL4ArgumentTableDescriptor new]; ad.maxTextureBindCount = 2;
        table = [g_dev newArgumentTableWithDescriptor:ad error:&error];
        if (!ps || !table) { MLOG("[oot-movie] diagnostic preparation failed: %s", error.localizedDescription.UTF8String); return 0; }
    }
    rp_end(); blit_close();
    id<MTL4ComputeCommandEncoder> ce = (id<MTL4ComputeCommandEncoder>)enc_c_begin(NULL);
    [ce setArgumentTable:table]; [table setTexture:in.gpuResourceID atIndex:0]; [table setTexture:out.gpuResourceID atIndex:1];
    enc_c_pso(ce, ps); enc_c_dispatch(ce, MTLSizeMake(320, 180, 1), MTLSizeMake(8, 8, 1)); enc_c_end(ce);
    args_dirty_all(); return 1;
}
static void oot_movie_remember(NvShader *cs) {
    g_oot_movie_decoded = oot_movie_image(cs, 0, NULL, 0);
    if (g_oot_movie_decoded.width != 1920 || g_oot_movie_decoded.height != 1080 ||
        g_oot_movie_decoded.pixelFormat != MTLPixelFormatRGBA8Unorm) g_oot_movie_decoded = nil;
    g_oot_movie_sub = g_sub_serial;
}
static int oot_movie_replace(NvShader *cs) {
    id<MTLTexture> in = g_oot_movie_decoded; g_oot_movie_decoded = nil;
    if (!in || g_oot_movie_sub != g_sub_serial) return 0;
    rp_end(); uint64_t serial = 0;
    id<MTLTexture> out = oot_movie_image(cs, 1, &serial, 1);
    if (!oot_movie_scale(in, out)) return 0;
    gpu_owned_mark(serial); zskip_del(serial);
    static unsigned count;
    if (++count <= 3 || count % 600 == 0)
        MLOG("[oot-movie] EXPERIMENT: direct bilinear 1920x1080 -> 2560x1440; replaced %u final dispatches, output serial %llu", count, (unsigned long long)serial);
    return 1;
}
