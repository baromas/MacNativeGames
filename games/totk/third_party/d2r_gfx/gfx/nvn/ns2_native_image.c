/* Native decoded movie images, adapted from seedds/nxnative 865cc35f dm/gfx/nvn/hle_nvn.c (MIT).
 * See ../../../licenses/nxnative.txt. No game/scene decisions: a codec-owned RGBA surface becomes a linear texture. */
#ifdef GAME_NS2
#include "../../host/hle.h"
#include "nvn_impl.h"
#include <string.h>

void *nvn_slot_fn(const char *name);
#define CALL(name) ((NVNT_##name)nvn_slot_fn(#name))
__attribute__((weak)) int runtime_ns2_native_image(uint32_t handle, uint8_t **mem, uint64_t *size, uint32_t *w, uint32_t *h, uint32_t *stride) {
    (void)handle; (void)mem; (void)size; (void)w; (void)h; (void)stride; return 0;
}
typedef struct { NVNdevice *dev; uint32_t handle; NVNformat format; } native_builder;
typedef struct { NVNdevice *dev; uint32_t handle; NVNformat format; uint32_t has_pool; NVNmemoryPool pool; } native_image;
_Static_assert(sizeof(native_builder) <= 0x100, "native image builder storage");
_Static_assert(sizeof(native_image) <= 0x200, "native image storage");

NVN_EXTRA(nvnNativeImageBuilderSetDefaults, void, native_builder *b) { NVNdevice *dev=b->dev;memset(b,0,sizeof *b);b->dev=dev; }
NVN_EXTRA(nvnNativeImageBuilderSetDevice, void, native_builder *b, NVNdevice *dev) { b->dev=dev; }
NVN_EXTRA(nvnNativeImageBuilderSetNativeImageHandle, void, native_builder *b, uint32_t handle) { b->handle=handle; }
NVN_EXTRA(nvnNativeImageBuilderSetMemoryPermission, void, native_builder *b, int permission) { (void)b;(void)permission; }
NVN_EXTRA(nvnNativeImageBuilderSetFormat, void, native_builder *b, NVNformat format) { b->format=format; }
NVN_EXTRA(nvnNativeImageInitialize, NVNboolean, native_image *i, const native_builder *b) {
    i->dev=b->dev;i->handle=b->handle;i->format=b->format;i->has_pool=0;return 1;
}
NVN_EXTRA(nvnNativeImageFinalize, void, native_image *i) {
    if(i->has_pool)CALL(nvnMemoryPoolFinalize)(&i->pool);i->has_pool=0;
}
NVN_EXTRA(nvnTextureInitializeFromNativeImage, NVNboolean, NVNtexture *texture, native_image *i) {
    if(i->format!=NVN_FORMAT_RGBA8&&i->format!=NVN_FORMAT_RGBA8_SRGB)return 0;
    uint8_t *mem;uint64_t size;uint32_t w,h,stride;
    if(!runtime_ns2_native_image(i->handle,&mem,&size,&w,&h,&stride))return 0;
    if(getenv("TOTK_CODEC_LOG")){static unsigned count;if(count++<4)LOG("[native-movie] handle=%#x size=%ux%u stride=%u format=%u",i->handle,w,h,stride,(unsigned)i->format);}
    if(!i->has_pool){
        NVNmemoryPoolBuilder pb;CALL(nvnMemoryPoolBuilderSetDefaults)(&pb);CALL(nvnMemoryPoolBuilderSetDevice)(&pb,i->dev);
        CALL(nvnMemoryPoolBuilderSetStorage)(&pb,mem,(size_t)size);
        CALL(nvnMemoryPoolBuilderSetFlags)(&pb,NVN_MEMORY_POOL_FLAGS_CPU_UNCACHED|NVN_MEMORY_POOL_FLAGS_GPU_CACHED);
        if(!CALL(nvnMemoryPoolInitialize)(&i->pool,&pb))return 0;i->has_pool=1;
    }
    NVNtextureBuilder tb;CALL(nvnTextureBuilderSetDefaults)(&tb);CALL(nvnTextureBuilderSetDevice)(&tb,i->dev);
    CALL(nvnTextureBuilderSetTarget)(&tb,NVN_TEXTURE_TARGET_2D);CALL(nvnTextureBuilderSetFormat)(&tb,i->format);
    CALL(nvnTextureBuilderSetSize2D)(&tb,(int)w,(int)h);CALL(nvnTextureBuilderSetLevels)(&tb,1);
    CALL(nvnTextureBuilderSetFlags)(&tb,NVN_TEXTURE_FLAGS_LINEAR);CALL(nvnTextureBuilderSetStride)(&tb,(ptrdiff_t)stride);
    CALL(nvnTextureBuilderSetStorage)(&tb,&i->pool,0);return CALL(nvnTextureInitialize)(texture,&tb);
}

void *nvn_native_image_override(const char *name) {
    static const struct {const char *name;void *fn;} entries[]={
        {"_Z32nvnNativeImageBuilderSetDefaultsP21NVNnativeImageBuilder",x_nvnNativeImageBuilderSetDefaults},
        {"_Z30nvnNativeImageBuilderSetDeviceP21NVNnativeImageBuilderP9NVNdevice",x_nvnNativeImageBuilderSetDevice},
        {"_Z41nvnNativeImageBuilderSetNativeImageHandleP21NVNnativeImageBuilderN2nn2gs17NativeImageHandleE",x_nvnNativeImageBuilderSetNativeImageHandle},
        {"_Z40nvnNativeImageBuilderSetMemoryPermissionP21NVNnativeImageBuilder30NVNnativeImageMemoryPermission",x_nvnNativeImageBuilderSetMemoryPermission},
        {"_Z30nvnNativeImageBuilderSetFormatP21NVNnativeImageBuilder9NVNformat",x_nvnNativeImageBuilderSetFormat},
        {"_Z24nvnNativeImageInitializeP14NVNnativeImagePK21NVNnativeImageBuilder",x_nvnNativeImageInitialize},
        {"_Z22nvnNativeImageFinalizeP14NVNnativeImage",x_nvnNativeImageFinalize},
        {"_Z35nvnTextureInitializeFromNativeImageP10NVNtextureP14NVNnativeImage",x_nvnTextureInitializeFromNativeImage},
    };
    for(size_t k=0;k<sizeof entries/sizeof entries[0];k++)if(!strcmp(name,entries[k].name))return entries[k].fn;
    return NULL;
}
#endif
