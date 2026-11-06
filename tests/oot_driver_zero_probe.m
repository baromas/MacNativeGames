/* Reflection policy only, synthetic JSON; no game shader or GPU work. */
#import <Foundation/Foundation.h>
#include "../games/totk/third_party/d2r_gfx/gfx/nvn/nvn_refl.m"
int main(int argc,char **argv) { @autoreleasepool {
    if(argc!=3)return 2;
    NSArray *missing=[@(argv[1]) componentsSeparatedByString:@","];
    NSDictionary *j=@{@"route":@"B",@"bindings":@[],@"stage":@(argv[2]),@"drv_reads":@{@"0":@{}},@"drv_unfillable":missing};
    nvn_refl r;char error[160]={0};int failed=nvn_refl_from_json(j,&r,error,sizeof error);
    printf("%d %d\n",failed,r.drv_read[0]);return 0;
} }
