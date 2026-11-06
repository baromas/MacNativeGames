#import <Foundation/Foundation.h>
#include "../games/totk/third_party/d2r_gfx/gfx/nvn/nvn_refl.m"
int main(void){@autoreleasepool {
 for(int i=0;i<3;i++){
 int bank=i==0?24:i==1?0:2;
 NSDictionary *j=@{@"route":@"B",@"bindings":@[@{@"kind":@"drvcb",@"bank":@(bank),@"arg_id":@0}],@"drv_unfillable":@[]};
 nvn_refl r;char e[200];if(nvn_refl_from_json(j,&r,e,sizeof e))return 2;
 if(r.nb!=1||r.b[0].kind!=(i==0?NVN_RB_CBUF:i==1?NVN_RB_DRV0:NVN_RB_DRV2)||(i==0&&r.b[0].reg!=24))return 3;
 }return 0;
}}
