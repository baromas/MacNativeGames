#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <math.h>
int main(int argc,char **argv){@autoreleasepool{
 if(argc!=2)return 2;NSError *e=nil;NSString *s=[NSString stringWithContentsOfFile:@(argv[1]) encoding:NSUTF8StringEncoding error:&e];
 id<MTLDevice>d=MTLCreateSystemDefaultDevice();id<MTLLibrary>l=[d newLibraryWithSource:s options:nil error:&e];
 if(!l){fprintf(stderr,"%s\n",e.localizedDescription.UTF8String);return 3;}
 id<MTLComputePipelineState>p=[d newComputePipelineStateWithFunction:[l newFunctionWithName:@"probe"] error:&e];if(!p)return 4;
 id<MTLCommandQueue>q=[d newCommandQueue];unsigned checked=0;
 for(unsigned groups=1;groups<=4;groups*=2){
 id<MTLBuffer>b=[d newBufferWithLength:groups*128*sizeof(float) options:MTLResourceStorageModeShared];
 id<MTLCommandBuffer>c=[q commandBuffer];id<MTLComputeCommandEncoder>ce=[c computeCommandEncoder];[ce setComputePipelineState:p];[ce setBuffer:b offset:0 atIndex:0];[ce dispatchThreadgroups:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(groups*32,1,1)];[ce endEncoding];[c commit];[c waitUntilCompleted];if(c.error){fprintf(stderr,"%s\n",c.error.localizedDescription.UTF8String);return 5;}
 const float *v=b.contents;
 for(unsigned g=0;g<groups;g++)for(unsigned r=0;r<16;r++)for(unsigned n=0;n<8;n++){
 int sum=0;for(unsigned k=0;k<16;k++)sum+=((int)((r*3+k+g)%5)-2)*((int)((k*2+n+g)%5)-2);
 float want=2*sum+(int)((r+n+g)%3)-1,got=v[g*128+r*8+n];if(got!=want){fprintf(stderr,"group%u r%u n%u got%g want%g\n",g,r,n,got,want);return 6;}checked++;
 }
 }
 printf("HMMA: %u numeric outputs passed (1/2/4 SIMD groups, two accumulations)\n",checked);return 0;
}}
