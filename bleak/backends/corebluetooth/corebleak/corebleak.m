//
//  corebleak.m
//  corebleak
//
//  Created by Kevin Davis on 6/29/19.
//  Copyright © 2019 Kevin Davis. All rights reserved.
//

#import <Foundation/Foundation.h>
#import <CoreBluetooth/CoreBluetooth.h>
#include "CoreBleak.h"

@implementation CoreBleak : NSObject

+ (void) assignPeripheralDelegate:(id)delegate toPeripheral:(CBPeripheral*)peripheral
{
    peripheral.delegate = delegate;
}

@end
