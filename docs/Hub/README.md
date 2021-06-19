# Hub Teardown

This documents up the known pins for the hub that has the following:
| Component | Description |
| -- | -- |
| CPU |PIC32MX695F512H - PIC CPU in 64 Pin (H version) TQFP form factor |
| Radio | MRF24J40 - Microchip Zigbee / MiWi radio controller |
| Ethernet | ENC424J600 Ethernet controller |
 
## Datasheets
Below is links to the datasheets found on the Microchip site, these links may break so the PDFs are also downloaded and included here.

### PIC32MX
There are two revisions of the PIC32MX and I find the v2 better.
https://ww1.microchip.com/downloads/en/DeviceDoc/PIC32MX_Datasheet_v2_61143B.pdf
Also V1 if required (for completeness)
https://ww1.microchip.com/downloads/en/devicedoc/pic32mx_datasheet_v1_61143a.pdf
There is also a specific PIC32MX6xx/7xx series datasheet which is much the same informaiton as the above two datasheets:
https://www.microchip.com/content/dam/mchp/documents/MCU32/ProductDocuments/DataSheets/PIC32MX5XX6XX7XX_Family)Datasheet_DS60001156K.pdf
Main page: https://www.microchip.com/en-us/products/microcontrollers-and-microprocessors/32-bit-mcus/pic32-32-bit-mcus/pic32mx


### MRF24J40MA
The radio is a MRF24J40 but it is in the MA package so you will need the main datasheet for the information about the CPU and the MA datasheet for the board pin information:

MRF24J40: https://ww1.microchip.com/downloads/en/DeviceDoc/39776C.pdf
MRF24J40MA: https://ww1.microchip.com/downloads/en/DeviceDoc/MRF24J40MA-Data-Sheet-70000329C.pdf
Main page: https://www.microchip.com/mrf24j40

## Using PICKIT3

A site detailing using the PICKIT3 to connect up to a PIC32MX695 CPU to extract the firmware.

https://blog.rapid7.com/2019/04/30/extracting-firmware-from-microcontrollers-onboard-flash-memory-part-3-microchip-pic-microcontrollers/

## High resolution photos

High resolution photos of both sides of the hub:

<p style="text-align: center;">Front</p> 
<img src="./Front.jpg" height="350">
<p style="text-align: center;">Back</p>
<img src="./Back.jpg" height="350">
<p style="text-align: center;">CPU</p>
<img src="./CPU.jpg" height="350">

## Hub pins
The pads on both sides of the board connect to the other side, so the below photos show the pin connections on both sides of the boards.
This may not be 100% correct so please check this before connecting anything.

The serial port speed is 57600 8/N/1 with flow control disabled.

<p style="text-align: center;">Front with pins</p> 
<img src="./Front-WithPins.jpg" height="350">
<p style="text-align: center;">Back  with pins</p>
<img src="./Back-WithPins1.jpg" height="350">

| Pin Number | CPU Pin | Description |
| -- | -- | -- |
| 1 | 17 | PGC2 used for ICSP debugger |
| 2 | 7 | /MCLR via 100R |
| 3 | 18 | PGD2 used for ICSP debugger |
| 4 | 31 | U2RX - UART RX for the serial console |
| 5 | 32 | U2TX - UART TX for the serial console |
| 6 | 10, 26, 38 | Vdd - 3.3v power supply |
| 7 | 9,25,41 | Vss - Ground for UART and ICSP |
| 8 | - | Vin 5Vdc barrel plug |
| 9 | - | USB connector (unpopulated) USB+? |
| 10 | 36 | USB D- (unpopulated L3) |
| 11 | 37 | USB D+ (unpopulated L3) |
| 12 | 61 | PMD0/RE0 Connected to Reset Button (?) |
| 13 | 9,25,41 | Vss - Ground for UART and ICSP |
| 14 | - | NC |

Side connector pin mapping:
Just including this for ease of reading
| Connector Pin | aka Pin | CPU Pin | Description |
| -- | -- | -- | -- |
| 1 | 6 | 10, 26, 38 | Vdd - 3.3v Positive supply |
| 2 | - | NC |
| 3 | 7 | 9,25,41 | Vss - Ground |
| 4 | 1 | 17 | PGC2 used for ICSP debugger |
| 5 | 3 | 18 | PGD2 used for ICSP debugger |
| 6 | 2 | 7 | /MCLR via 100R |
| 7 | 4 | 31 | U2RX - UART RX for the Console output |
| 8 | 5 | 32 | U2TX - UART TX for the Console output |



# Console Boot Message:

The hub doesn't output too much during boot until you enable debug messages:

Standard boot message:

    SureFlap Hub 12:45:09 Jan 17 2020
    Build Number 43
    ---------------------------------
            Serial: 48 30 3x 30 2d 30 3x 3x 3x 3x 3x 3x 00
            As text: H0x0-0xxxxxx

    Stack Top: 0xa001ff88

    MAC address = xx:xx:xx:xx:xx:xx:xx:xx
    Read channel f from EEPROM
    Warning trying to change channel to f
    Set PANID to 3421
            [------------- Paired Devices ------------]
            [-----------------------------------------]

The above MAC address is the Zigbee Wireless MAC address not the ethernet MAC address

## Debug Menu
The Debug menu can be enabled if you send an upper case "A"

    A - Enable debug console
    c/r - After debug messages are enabled hitting enter gives the below debug menu.

    SureFlap Hub Debug Menu
    -----------------------
    e - Dump list of application errors
    h - dump entire hub register entry table
    p - dump pairing table
    l - Toggle Ethernet RJ45 LEDs
    s - Dump set_reg_queue
    t - Spam RF requests to test buffering
    z - disconnect and zero connection table

    Please select

    Other commands:

    miwi_channel_noise_floor addr=23

    RF Channel Register = 24
    1 - Set Channel to 15 (0f)
    2 - Set Channel to 20 (14)
    3 - Set Channel to 26 (1a)
    r - Doesn't give an error, I think it does a ping over MQTT.
    v - Unknown

    Registers 27-30, uptime in seconds.

`h` is the same output as sending a `TS 1000 3 0 205` message over MQTT.
`z` is the same as pressing the button underneath to start paring.

`p` Pairing table you get:

    [00]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [01]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [02]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [03]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [04]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [05]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [06]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [07]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [08]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]
    [09]: valid=0 online=0 type=0 last_heard=0 >>00:00:00:00:00:00:00:00<<   -]


If you enable debug when the hub first boots you get a lot more information:

    | Talking to: hub.api.surehub.io | Socket Obtained | Socket Opened | Socket Secured |
    --- Processing Response: 17 Bytes Total
    1 bytes remain, after 2 reads.Found status = 200
    0 bytes remain, after 3 reads.  | Tstate 2 |
    --- Processing Done

    --- Processing Response: 275 Bytes Total
    0 bytes remain, after 35 reads..Content Length = 3573           Start receiving non-chunked data, length=3573
            | Tstate 4 |
    --- Processing Done

    --- Processing Response: 3573 Bytes Total
    0 bytes remain, after 447 reads....     | Tstate 5 |    TCP_RESPONSE_COMPLETE
    --- Processing Done

    -------- Credentials Decoded --------
            Host:           **8th Field in Creds file**
            Client ID:      **3rd Field in Creds file**
            Base Topic:     **7th Field in Creds file**
            Version:        **1st Field in Creds file**
            ID:             xxxxxx (Serial Number which is also 2nd field ) and ClientID as a single string
            Username:       **4th Field in Creds file, should be empty**
            Password:       **5th Field in Creds file, also empty**
            Network Type:   1 **6th Field in Creds file**
            Certificate:    **9th Field in Creds file**
            
            Length:         xxx
            Cert Hash:      0x xxxxxxxx
            Key Hash:       0x xxxxxxxx

    -------- End Credentials --------

    Connected
    LED new mode a 5 Closing Socket
    Web state=3 Calling connect... Connection made!
    Connection sequence done.
    RF reset
    Web state=5 Subscribing to Hub Messages: Success!
    LED new mode 5 5 Web state=9 TCP Bytes Put: 2852, Seconds: 60
    Set LED to 0
    LED new mode 0 5 Unknown command 71
