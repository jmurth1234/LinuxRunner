#import <Foundation/Foundation.h>
#import "app/LinuxRunner/DiagnosticLogTail.h"
#include <assert.h>

static BOOL awaitText(NSURL *url, NSString *expected) {
    NSDate *deadline=[NSDate dateWithTimeIntervalSinceNow:3];
    do {
        if([LRCachedDiagnosticTail(url,64) isEqual:expected])return YES;
        [NSThread sleepForTimeInterval:0.01];
    }while([deadline timeIntervalSinceNow]>0);
    return NO;
}

int main(void) {
    @autoreleasepool {
        NSString *directory=[NSTemporaryDirectory() stringByAppendingPathComponent:NSUUID.UUID.UUIDString];
        assert([NSFileManager.defaultManager createDirectoryAtPath:directory withIntermediateDirectories:NO attributes:nil error:nil]);
        NSURL *url=[NSURL fileURLWithPath:[directory stringByAppendingPathComponent:@"session.log"]];
        int fd=open(url.fileSystemRepresentation,O_CREAT|O_RDWR,0600);assert(fd>=0);
        off_t size=100*1024*1024;
        assert(ftruncate(fd,size)==0);
        assert(pwrite(fd,"finished",8,size-8)==8);close(fd);
        NSData *tail=LRReadDiagnosticTail(url,8);
        assert(tail.length==8);assert([LRDiagnosticTailString(tail) isEqual:@"finished"]);
        NSURL *link=[NSURL fileURLWithPath:[directory stringByAppendingPathComponent:@"link"]];
        assert(symlink(url.fileSystemRepresentation,link.fileSystemRepresentation)==0);
        assert(LRReadDiagnosticTail(link,64)==nil);
        assert(LRReadDiagnosticTail([NSURL fileURLWithPath:directory],64)==nil);
        NSURL *pipe=[NSURL fileURLWithPath:[directory stringByAppendingPathComponent:@"pipe"]];
        assert(mkfifo(pipe.fileSystemRepresentation,0600)==0);
        assert(LRReadDiagnosticTail(pipe,64)==nil);
        unsigned char utf8[]={0x80,'o','k'};
        assert([LRDiagnosticTailString([NSData dataWithBytes:utf8 length:3]) isEqual:@"ok"]);
        assert([@"first" writeToURL:url atomically:YES encoding:NSUTF8StringEncoding error:nil]);
        assert(awaitText(url,@"first"));
        assert([@"second" writeToURL:url atomically:YES encoding:NSUTF8StringEncoding error:nil]);
        assert(awaitText(url,@"second"));
        assert([NSFileManager.defaultManager removeItemAtURL:url error:nil]);
        assert(awaitText(url,@""));
        assert([NSFileManager.defaultManager removeItemAtPath:directory error:nil]);
        puts("PASS: bounded reads, link and FIFO refusal, UTF-8 recovery, async refresh and deletion");
    }
}
