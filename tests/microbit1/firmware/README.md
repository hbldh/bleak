# Overview


testservice.hex advertises by service UUID.  The service and UUID are described here: https://github.com/bsiever/microbit-ble-testservice

testservice_B.hex advertises by name and include TX power of -100, but is essentially the same service as above (https://github.com/bsiever/microbit-ble-testservice2)

Use a BBC:microbit as a test device. 

See: https://github.com/bsiever/microbit-ble-testservice to build

The firmware needs to be copied to the micro:bit (should be completed by the test fixtures)

The micro:bit will advertise the custom service UUID: 1d93af38-9239-11ea-bb37-0242ac130002

## Advertising

TODO: Review

* BREDR not supported
* General Discoverable
* Connectable, Undirected
* Incomplete list of 128 bit UUIDs: 1d93af38-9239-11ea-bb37-0242ac130002

## GAP Settings

TODO: Review

* No Security (Just Works)
* Device Name: `Test MB ` + micro:bit specific name generated from device serial number.  It'll be in the format `[XXXXX]`, where each `X` is a letter. (See: https://support.microbit.org/support/solutions/articles/19000067679-can-i-rename-my-micro-bit-) 
* Preferred connection parameters:
  * Min Connection Interval: 10ms
  * Max Connection Interval: 16ms
  * Slave Latency: 0
* Advertising interval of 200ms; no timeout
* Packets can hold 23 bytes of data (TODO: Confirm)

## Services

### Device information service

Service UUID: 0x180A

| Props | Short desc | UUID | Long Description |
|-------|------------|------|------------------|

TODO!

   MICROBIT_BLE_MANUFACTURER, 
   MICROBIT_BLE_MODEL, 
   serialNumber.toCharArray(), 
   MICROBIT_BLE_HARDWARE_VERSION, 
   MICROBIT_BLE_FIRMWARE_VERSION, 
   MICROBIT_BLE_SOFTWARE_VERSION

### Custom Testing Service

Service UUID: 1d93af38-9239-11ea-bb37-0242ac130002

| Props | Short desc | UUID | Long Description |
|-------|------------|------|------------------|
| R     |  Data Short    | 1d93b2f8-9239-11ea-bb37-0242ac130002 |  Contains ASCII digits 0-9: "0123456789"  (10 bytes) | 
| R     |  Data Packet   | 1d93b488-9239-11ea-bb37-0242ac130002 | Contains 20 bytes:"abcdefghijklmnopqrst" (full BLE packet) |
| R     |  Data Long     | 1d93b56e-9239-11ea-bb37-0242ac130002 | Contains 62 bytes: "abcdefghijklmnopqrstuvwzyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" (multiple packets) |
| RWn    | Short R/Wn Data  | 1d93b636-9239-11ea-bb37-0242ac130002 | For testing writes up to 20 bytes (readback to confirm)|
| RWr    | Short R/W Data  | 1d93b942-9239-11ea-bb37-0242ac130002 | For testing writes up to 80 bytes (readback to confirm) |
| RWr    | Short R/W Data (identical ids)  | 1d93c374-9239-11ea-bb37-0242ac130002 | For testing writes up to 4 bytes (readback to confirm) |
| RWr    | Short R/W Data (identical ids) | 1d93c374-9239-11ea-bb37-0242ac130002 | For testing writes up to 4 bytes (readback to confirm) |
| RWr | Client Disconnect | 1d93c1e4-9239-11ea-bb37-0242ac130002 | Time (in ms) until client will disconnect intentionally |
| RWr | Client Reset (hard disconnect) | 1d93c2c0-9239-11ea-bb37-0242ac130002| Time (in ms) until client will disconnect intentionally |
| RW | Auth Permissions | 1d93b7c6-9239-11ea-bb37-0242ac130002 | 4 ASCII bytes; including an "R" allows Read and "W" allows write |
| RaWa | Auth Data | 1d93b884-9239-11ea-bb37-0242ac130002 | Data for authorization test (8 bytes) |
| RWr | Notifiable counter1 period | 1d93b6fe-9239-11ea-bb37-0242ac130002 | 4 byte value in ms indicating the period of updated to the notifications of counter 1; 500ms initially|
| N | Notifiable counter1 | 1d93bb2c-9239-11ea-bb37-0242ac130002| 4 byte counter; Starts at 1 on enable and counts up |
| RWr | Notifiable counter2 period | 1d93bbea-9239-11ea-bb37-0242ac130002 | 4 byte value in ms indicating the period of updated to the notifications of counter 1; 500ms initially|
| N | Notifiable counter2 | 1d93bc9e-9239-11ea-bb37-0242ac130002| 4 byte counter; Starts at 1 on enable and counts up |
| RWr | Indicatable counter1 period | 1d93bd52-9239-11ea-bb37-0242ac130002 | 4 byte value in ms indicating the period of updated to the notifications of counter 1; 500ms initially|
| N | Indicatable counter1 | 1d93be06-9239-11ea-bb37-0242ac130002| 4 byte counter; Starts at 1 on enable and counts up |
| RWr | Indicatable counter2 period | 1d93bec4-9239-11ea-bb37-0242ac130002 | 4 byte value in ms indicating the period of updated to the notifications of counter 1; 500ms initially|
| N | Indicatable counter2 | 1d93bf82-9239-11ea-bb37-0242ac130002| 4 byte counter; Starts at 1 on enable and counts up |

