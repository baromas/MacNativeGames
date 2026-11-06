/* Synthetic API integration: production codec, real AV1 backend, fake guest events. No game files/window. */
#include "../../runtime/ns2_codec.c"
#include "synthetic_av1.h"
#include <assert.h>
#include <sys/mman.h>

typedef struct { uint32_t signalled, alive; } event;
static unsigned bound, destroyed, prepared;
static void event_clear(void *p) { event *e=p;assert(e->alive==0x45564e54);e->signalled=0; }
static void event_destroy(void *p) { event *e=p;assert(e->alive==0x45564e54);e->alive=0;destroyed++; }
static void holder_init(void *p,void *e) { *(void **)p=e; }
_Noreturn void runtime_fail(const char *s) { fprintf(stderr,"FAIL %s\n",s);exit(2); }
void *runtime_symbol(const char *s) {
    if(strstr(s,"ClearSystemEvent"))return event_clear;
    if(strstr(s,"DestroySystemEvent"))return event_destroy;
    if(strstr(s,"InitializeMultiWaitHolder"))return holder_init;
    runtime_fail("unexpected guest symbol");
}
void hle_bind_system_event(void *p,int automatic) { assert(!automatic);event *e=p;memset(p,0,0x30);e->alive=0x45564e54;bound++; }
void hle_signal_system_event(void *p) { event *e=p;assert(e->alive==0x45564e54);e->signalled=1; }
void dm_guest_write_prepare(void *p,size_t n) { assert(p&&n);prepared++; }

static void *resolve(const char *s) { void *p=runtime_ns2_codec_override(s);assert(p);return p; }
typedef Result (*transfer_fn)(void *,void *,uint64_t,uint64_t,uint64_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t);
typedef Result (*remote_fn)(void *,uint64_t,uint64_t,uint64_t,uint32_t,uint32_t,uint32_t,uint32_t);
typedef Result (*legacy_fn)(void *,void *,uint64_t,uint64_t,uint64_t,uint64_t,uint32_t,uint32_t,uint64_t);

static void run(unsigned w,unsigned h,const uint8_t *packet,size_t bytes,int form) {
    unsigned before_bound=bound,before_destroyed=destroyed;
    _Alignas(16) uint8_t decoder[0x400]={0},pool[0x20]={0},completion[0x58]={0};
    cv_pref pref;
    if(form) {
        typedef cv_pref (*pref_fn)(uint64_t,uint64_t,uint32_t,uint32_t);
        pref=((pref_fn)resolve("_ZN2nn5codec25MakeDecodeImagePreferenceEttNS0_24VideoDecoderOutputFormatENS0_15ImageTilingModeE"))(w,h,3,1);
    }else pref=cv_preference((uint16_t)w,(uint16_t)h,3,1);
    uint64_t size=0,alignment=0;assert(!cv_pool_size(&size,&alignment,&pref,2));
    size_t mapped=(size+0x3fff)&~(size_t)0x3fff;
    uint8_t *memory=mmap(NULL,mapped,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(memory!=MAP_FAILED);memset(memory,0x5a,mapped);
    if(form) {
        typedef Result (*pool_fn)(void *,void *,uint64_t,const cv_pref *,uint32_t);
        pool_fn init=resolve("_ZN2nn5codec26InitializeDecoderImagePoolEPNS0_25VideoDecoderImagePoolTypeEPvmRKNS0_27VideoDecoderImagePreferenceEj");
        assert(init(pool,memory+1,size,&pref,2)==CV_R(2004));assert(!init(pool,memory,size,&pref,2));
    }else assert(!cv_pool_init(pool,memory,size,&pref,2,0));
    uint64_t wide_w=UINT64_C(0xabcd000000000000)|w,wide_h=UINT64_C(0xdcba000000000000)|h;
    if(form==1) {
        transfer_fn init=resolve("_ZN2nn5codec36InitializeAv1DecoderByTransferMemoryEPNS0_14Av1DecoderTypeEPvmmttjNS0_23VideoDecoderInputFormatENS0_24VideoDecoderOutputFormatENS0_22VideoDecoderOutputModeE");
        assert(!init(decoder,NULL,4096,4096,wide_w,wide_h,4,0,3,0));
    }else if(form==2) {
        remote_fn init=resolve("_ZN2nn5codec34InitializeAv1DecoderByRemoteMemoryEPNS0_14Av1DecoderTypeEmttjNS0_23VideoDecoderInputFormatENS0_24VideoDecoderOutputFormatENS0_22VideoDecoderOutputModeE");
        assert(!init(decoder,4096,wide_w,wide_h,4,0,3,0));
    }else {
        legacy_fn init=resolve("_ZN2nn5codec20InitializeAv1DecoderEPNS0_14Av1DecoderTypeEPvmmttjNS0_23VideoDecoderInputFormatENS0_24VideoDecoderOutputFormatE");
        assert(!init(decoder,NULL,4096,4096,wide_w,wide_h,4,0,3));
    }
    typedef void *(*event_fn)(void *);
    void *ready=((event_fn)resolve("_ZN2nn5codec33GetAv1DecoderSubmissionReadyEventEPNS0_14Av1DecoderTypeE"))(decoder);
    assert(ready==decoder+CV_EVENT_OFF&&((event *)ready)->signalled);
    assert(!cv_dec_reg(decoder,0,pool,0));
    uint32_t index;cv_sync sync;assert(!cv_dec_acq(&index,&sync,decoder)&&index==0);cv_dec_rel(decoder,index,sync);
    assert(!cv_dec_acq(&index,&sync,decoder));assert(!sync_reached(&sync));
    assert(!spt_create(completion));assert(!spt_request(completion,&sync));assert(!((event *)completion)->signalled);
    uint64_t submitted=0;assert(!cv_dec_submit(&submitted,decoder,packet,bytes,123456789,0)&&submitted==1);
    assert(((event *)completion)->signalled&&sync_reached(&sync));spt_cancel(completion);spt_destroy(completion);
    uint16_t pw,ph,cw,ch;int64_t time;bool end;
    assert(!cv_dec_props(&pw,&ph,&cw,&ch,&time,&end,decoder,index)&&pw==w&&ph==h&&cw==w&&ch==h&&time==123456789&&!end);
    uint8_t *y=malloc((size_t)w*h),*uv=malloc((size_t)w*h/2),*rgba=malloc((size_t)w*h*4);assert(y&&uv&&rgba);
    assert(!cv_read_nv12(pool,0,0,0,(uint16_t)w,(uint16_t)h,y,w,(uint64_t)w*h,uv,w,(uint64_t)w*h/2));
    for(size_t i=0;i<(size_t)w*h;i++)assert(y[i]==81);
    for(size_t i=0;i<(size_t)w*h/2;i++)assert(uv[i]==(i%2?240:90));
    assert(!cv_read_rgba(pool,0,0,0,(uint16_t)w,(uint16_t)h,rgba,w*4,(uint64_t)w*h*4));
    for(size_t i=0;i<(size_t)w*h;i++)assert(rgba[i*4]>=250&&rgba[i*4+1]<=3&&rgba[i*4+2]<=3&&rgba[i*4+3]==255);
    uint32_t handle=cv_native(pool,0);assert(!cv_native(pool,2));
    if(form) {
        uint8_t *surface;uint64_t total;uint32_t sw,sh,stride;
        assert(handle&&handle==cv_native(pool,0));assert(runtime_ns2_native_image(handle,&surface,&total,&sw,&sh,&stride));
        assert(surface==memory&&sw==w&&sh==h&&stride==native_stride(w)&&total==native_size(w,h));
        for(unsigned row=0;row<h;row++) {
            assert(!memcmp(surface+(size_t)row*stride,rgba+(size_t)row*w*4,(size_t)w*4));
            for(unsigned x=w*4;x<stride;x++)assert(surface[(size_t)row*stride+x]==0x5a);
        }
        for(uint64_t i=(uint64_t)stride*h;i<total;i++)assert(memory[i]==0x5a);
        assert(prepared);
    }else assert(!handle); /* Legacy pool sizing remains CPU-only, rather than exposing an unwritten GPU surface. */
    cv_dec_rel(decoder,index,sync);assert(!cv_dec_reset(decoder));assert(!cv_dec_acq(&index,&sync,decoder));
    assert(!cv_dec_submit(&submitted,decoder,packet,bytes,222222222,1)&&submitted==2);
    assert(!cv_dec_props(&pw,&ph,&cw,&ch,&time,&end,decoder,index)&&time==222222222&&end);
    cv_pool_fin(pool);
    if(handle){uint8_t *p;uint64_t n;uint32_t a,b,c;assert(!runtime_ns2_native_image(handle,&p,&n,&a,&b,&c));}
    assert(!cv_dec_fin(decoder));assert(!*(void **)decoder&&!*(void **)pool);
    assert(bound-before_bound==2&&destroyed-before_destroyed==2);
    free(y);free(uv);free(rgba);assert(!munmap(memory,mapped));
}

int main(void) {
    for(int form=0;form<3;form++){run(64,64,red_64_64,sizeof red_64_64,form);run(66,48,red_66_48,sizeof red_66_48,form);}
    printf("{\"status\":\"pass\",\"cases\":6,\"forms\":3,\"events_destroyed\":%u,\"native_writes\":%u}\n",destroyed,prepared);
}
