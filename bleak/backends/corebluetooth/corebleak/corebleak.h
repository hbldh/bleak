//
//  corebleak.h
//  corebleak
//
//  Created by Kevin Davis on 6/29/19.
//  Copyright © 2019 Kevin Davis. All rights reserved.
//

#import <Foundation/Foundation.h>
#import <CoreBluetooth/CoreBluetooth.h>

//! Project version number for corebleak.
FOUNDATION_EXPORT double corebleakVersionNumber;

//! Project version string for corebleak.
FOUNDATION_EXPORT const unsigned char corebleakVersionString[];

// In this header, you should import all the public headers of your framework using statements like #import <corebleak/PublicHeader.h>

@interface CoreBleak : NSObject

+ (void) assignPeripheralDelegate:(id)delegate toPeripheral:(CBPeripheral*)peripheral;

@end
