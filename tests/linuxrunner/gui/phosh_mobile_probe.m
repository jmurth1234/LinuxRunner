// Host acceptance test. Require visible search text after real pointer and key input.
#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>
#import "app/LinuxRunner/RFBClient.h"
static CGImageRef frameImage(NSData *data, unsigned width, unsigned height) {
    CGDataProviderRef provider=CGDataProviderCreateWithCFData((__bridge CFDataRef)data);
    CGColorSpaceRef color=CGColorSpaceCreateDeviceRGB();
    CGImageRef image=CGImageCreate(width,height,8,32,width*4,color,kCGBitmapByteOrder32Little|kCGImageAlphaNoneSkipFirst,provider,NULL,false,kCGRenderingIntentDefault);
    CGDataProviderRelease(provider);CGColorSpaceRelease(color);return image;
}
int main(int argc,char **argv) {@autoreleasepool {
    if(argc!=5)return 2;
    NSString *out=@(argv[3]);NSLock *lock=[NSLock new];
    __block NSData *pixels;__block uint16_t width=0,height=0;__block uint64_t frames=0;
    LRRFBClient *client=[[LRRFBClient alloc]initWithPort:atoi(argv[1]) password:[NSString stringWithContentsOfFile:@(argv[2]) encoding:NSUTF8StringEncoding error:nil]];
    client.frameHandler=^(NSData *data,uint16_t w,uint16_t h,uint64_t n,uint64_t bytes){[lock lock];pixels=data;width=w;height=h;frames=n;[lock unlock];};
    __block BOOL ended=NO;
    client.statusHandler=^(NSString *s){fprintf(stderr,"%s\n",s.UTF8String);if([s hasPrefix:@"Linux display ended"]||[s hasPrefix:@"Display error:"])dispatch_async(dispatch_get_main_queue(),^{ended=YES;});};
    [client start];
    NSDate *start=NSDate.date;BOOL opened=NO,typed=NO,passed=NO;uint64_t observed=0;
    while(!ended&&-start.timeIntervalSinceNow<120) {
        [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:1]];
        [lock lock];NSData *data=pixels;uint16_t w=width,h=height;uint64_t n=frames;[lock unlock];
        if(!data)continue;
        if(!opened&&!typed&&-start.timeIntervalSinceNow>30){[client key:0xffeb down:YES];[client key:0xffeb down:NO];opened=YES;}
        if(n==observed)continue;observed=n;
        CGImageRef image=frameImage(data,w,h);
        CGImageDestinationRef destination=CGImageDestinationCreateWithURL((__bridge CFURLRef)[NSURL fileURLWithPath:[out stringByAppendingPathComponent:@"phosh.png"]],CFSTR("public.png"),1,NULL);
        CGImageDestinationAddImage(destination,image,NULL);CGImageDestinationFinalize(destination);CFRelease(destination);
        VNRecognizeTextRequest *request=[VNRecognizeTextRequest new];request.recognitionLevel=VNRequestTextRecognitionLevelAccurate;
        VNImageRequestHandler *handler=[[VNImageRequestHandler alloc]initWithCGImage:image options:@{}];[handler performRequests:@[request] error:nil];CGImageRelease(image);
        NSMutableString *text=[NSMutableString new];CGRect search=CGRectZero;
        for(VNRecognizedTextObservation *line in request.results){NSString *value=[line topCandidates:1].firstObject.string;[text appendFormat:@"%@\n",value];if([value.lowercaseString containsString:@"search apps"])search=line.boundingBox;}
        fprintf(stderr,"PHOSH_FRAME %llu %ux%u %s\n",n,w,h,text.UTF8String);
        [text writeToFile:[out stringByAppendingPathComponent:@"phosh-ocr.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
        if([text.lowercaseString containsString:@"123456789"]){passed=YES;break;}
        if(!typed&&!CGRectIsEmpty(search)) {
            uint16_t x=CGRectGetMidX(search)*w,y=(1-CGRectGetMidY(search))*h;
            [client pointerX:x y:y buttons:1];[client pointerX:x y:y buttons:0];
            [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.5]];
            for(const char *c="123456789";*c;c++){[client key:*c down:YES];[client key:*c down:NO];}
            typed=YES;
        }
    }
    [client stop];
    NSDictionary *result=@{@"environment":@"macOS interpreter with RFB; no iOS UI verification", @"search_input_rendered":@(passed), @"width":@(width), @"height":@(height), @"frames":@(frames)};
    [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[out stringByAppendingPathComponent:@"phosh-result.json"] atomically:YES];
    return passed?0:1;
}}
