/* CPU-only native-image adapter test. Production adapter, mock NVN resource functions, no game or GPU. */
#include "../../third_party/d2r_gfx/gfx/nvn/nvn_impl.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void *nvn_native_image_override(const char *);
static uint8_t pixels[16384];
static unsigned pools,textures,finalized;
typedef struct {NVNdevice *dev;void *memory;size_t size;int flags;} pool_data;
typedef struct {NVNdevice *dev;NVNmemoryPool *pool;ptrdiff_t offset,stride;int target,format,w,h,levels,flags;} texture_data;
static texture_data observed;
int runtime_ns2_native_image(uint32_t handle,uint8_t **mem,uint64_t *size,uint32_t *w,uint32_t *h,uint32_t *stride) {
    if(handle!=42)return 0;*mem=pixels;*size=sizeof pixels;*w=66;*h=48;*stride=320;return 1;
}
static void pb_defaults(NVNmemoryPoolBuilder *p){memset(p,0,sizeof *p);}
static void pb_device(NVNmemoryPoolBuilder *p,NVNdevice *d){((pool_data *)p)->dev=d;}
static void pb_storage(NVNmemoryPoolBuilder *p,void *v,size_t n){((pool_data *)p)->memory=v;((pool_data *)p)->size=n;}
static void pb_flags(NVNmemoryPoolBuilder *p,int f){((pool_data *)p)->flags=f;}
static NVNboolean pool_init(NVNmemoryPool *p,const NVNmemoryPoolBuilder *b){
    const pool_data *d=(const pool_data *)b;assert(d->memory==pixels&&d->size==sizeof pixels);
    assert(d->flags==(NVN_MEMORY_POOL_FLAGS_CPU_UNCACHED|NVN_MEMORY_POOL_FLAGS_GPU_CACHED));memcpy(p,d,sizeof *d);pools++;return 1;
}
static void pool_fin(NVNmemoryPool *p){(void)p;finalized++;}
static void tb_defaults(NVNtextureBuilder *p){memset(p,0,sizeof *p);}
static void tb_device(NVNtextureBuilder *p,NVNdevice *v){((texture_data *)p)->dev=v;}
static void tb_target(NVNtextureBuilder *p,NVNtextureTarget v){((texture_data *)p)->target=v;}
static void tb_format(NVNtextureBuilder *p,NVNformat v){((texture_data *)p)->format=v;}
static void tb_size(NVNtextureBuilder *p,int w,int h){((texture_data *)p)->w=w;((texture_data *)p)->h=h;}
static void tb_levels(NVNtextureBuilder *p,int v){((texture_data *)p)->levels=v;}
static void tb_flags(NVNtextureBuilder *p,int v){((texture_data *)p)->flags=v;}
static void tb_stride(NVNtextureBuilder *p,ptrdiff_t v){((texture_data *)p)->stride=v;}
static void tb_storage(NVNtextureBuilder *p,NVNmemoryPool *v,ptrdiff_t offset){((texture_data *)p)->pool=v;((texture_data *)p)->offset=offset;}
static NVNboolean texture_init(NVNtexture *p,const NVNtextureBuilder *b){(void)p;observed=*(const texture_data *)b;textures++;return 1;}
void *nvn_slot_fn(const char *s){
#define SLOT(name,fn) if(!strcmp(s,#name))return fn
    SLOT(nvnMemoryPoolBuilderSetDefaults,pb_defaults);SLOT(nvnMemoryPoolBuilderSetDevice,pb_device);
    SLOT(nvnMemoryPoolBuilderSetStorage,pb_storage);SLOT(nvnMemoryPoolBuilderSetFlags,pb_flags);
    SLOT(nvnMemoryPoolInitialize,pool_init);SLOT(nvnMemoryPoolFinalize,pool_fin);
    SLOT(nvnTextureBuilderSetDefaults,tb_defaults);SLOT(nvnTextureBuilderSetDevice,tb_device);
    SLOT(nvnTextureBuilderSetTarget,tb_target);SLOT(nvnTextureBuilderSetFormat,tb_format);
    SLOT(nvnTextureBuilderSetSize2D,tb_size);SLOT(nvnTextureBuilderSetLevels,tb_levels);
    SLOT(nvnTextureBuilderSetFlags,tb_flags);SLOT(nvnTextureBuilderSetStride,tb_stride);
    SLOT(nvnTextureBuilderSetStorage,tb_storage);SLOT(nvnTextureInitialize,texture_init);
#undef SLOT
    assert(!"unexpected NVN slot");return NULL;
}
static void *resolve(const char *s){void *p=nvn_native_image_override(s);assert(p);return p;}
int main(void){
    _Alignas(16) uint8_t builder[0x100]={0},image[0x200]={0};NVNtexture texture={0};NVNdevice dev={0};
    void (*device)(void *,NVNdevice *)=resolve("_Z30nvnNativeImageBuilderSetDeviceP21NVNnativeImageBuilderP9NVNdevice");
    void (*defaults)(void *)=resolve("_Z32nvnNativeImageBuilderSetDefaultsP21NVNnativeImageBuilder");
    void (*handle)(void *,uint32_t)=resolve("_Z41nvnNativeImageBuilderSetNativeImageHandleP21NVNnativeImageBuilderN2nn2gs17NativeImageHandleE");
    void (*format)(void *,NVNformat)=resolve("_Z30nvnNativeImageBuilderSetFormatP21NVNnativeImageBuilder9NVNformat");
    NVNboolean (*init)(void *,const void *)=resolve("_Z24nvnNativeImageInitializeP14NVNnativeImagePK21NVNnativeImageBuilder");
    NVNboolean (*tex)(NVNtexture *,void *)=resolve("_Z35nvnTextureInitializeFromNativeImageP10NVNtextureP14NVNnativeImage");
    void (*fin)(void *)=resolve("_Z22nvnNativeImageFinalizeP14NVNnativeImage");
    assert(!nvn_native_image_override("not-a-native-image-function"));
    device(builder,&dev);defaults(builder);format(builder,NVN_FORMAT_RGBA8);handle(builder,0);assert(init(image,builder));
    assert(!tex(&texture,image)&&!pools&&!textures);
    handle(builder,42);format(builder,NVN_FORMAT_RGBA16F);assert(init(image,builder));assert(!tex(&texture,image)&&!pools);
    format(builder,NVN_FORMAT_RGBA8);assert(init(image,builder));assert(tex(&texture,image));assert(pools==1&&textures==1);
    assert(observed.dev==&dev&&observed.w==66&&observed.h==48&&observed.stride==320&&observed.offset==0);
    assert(observed.format==NVN_FORMAT_RGBA8&&observed.target==NVN_TEXTURE_TARGET_2D&&observed.levels==1&&observed.flags==NVN_TEXTURE_FLAGS_LINEAR);
    assert(tex(&texture,image)&&pools==1&&textures==2);fin(image);assert(finalized==1);fin(image);assert(finalized==1);
    puts("{\"status\":\"pass\",\"native_image_bridge\":true,\"invalid_handles_and_formats\":true,\"pool_reuse_and_teardown\":true}");
}
