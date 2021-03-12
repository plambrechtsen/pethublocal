
# ZIGSNIFF

This container wraps up a single line script to sniff the zigbee traffic using a CC2531.

AliExpress: https://www.aliexpress.com/item/1005001863093680.html (standalone)
or https://www.aliexpress.com/item/1005001973568180.html (with debugger / flasher)
Be sure to get the CC2531 as the CC2540 is for Bluetooth not Zigbee. And if you don't already have the debugger / flasher you need the second one. There will no doubt be others on Ali but I liked this one as it had a case.

Using these two documents you need to flash the **sniffer_fw_cc2531.hex** file onto the CC2531 on linux, if you're using windows then you need to flash the firmware zboss wants.

https://www.zigbee2mqtt.io/how_tos/how_to_sniff_zigbee_traffic.html
https://www.zigbee2mqtt.io/information/flashing_the_cc2531.html

Then the zigsniff_up.sh has two things you may want to modify.

Firstly it detects the USB port the CC2531 is connected to and connects them as a device in docker, I assume there is only one CC2531 connected and otherwise you should modify the device field accordingly.

Secondly I map the /data/zigsniff folder in the container to /data/surepet/zigsniff, this may need to change.

Then the pcap is created, as is a .txt and the .update.txt is the dexored version of the payload.

You will see lines like:
```
ZigLine:  Feb  8, 2021 23:20:46.846118000 NZDT 70:b3:d5:f9:c0:02:2e:16 01 97 2a 58 b1 6c 73 69 ba 13 33 77 14 fc 4e 1e 2c c0 e7 83 2a a9 9f da 98 80 f1 a1 0d 9b b8 bc e0 54 27 cf 4a b0 c5 b7 1a 01 e9 47 56 ed 12 48 b1
Output :  Feb  8, 2021 23:20:46.846118000 NZDT 70:b3:d5:f9:c0:02:2e:16 01 97 2a 58 2b 7e 29 18 00 85 00 8f d3 00 00 b1 e2 5e 05 80 e9 01 01 3e 00 02 da 01 00 00 7f 01 00 00 f2 12 00 00 ee 11 00 00 13 00 2c 01 00 00
MQTT - Feb 08 23:20:47 surepetlocal/messages/162E02C0F9D5B370 60211080 02c0          126 29 18 00 85 00 8f d3 00 00 b1 e2 5e 05 80 e9 01 01 3e 00 02 da 01 00 00 7f 01 00 00 f2 12 00 00 ee 11 00 00 13 00 2c 01 00 00
```
This is the before and after dexoring the file.
The xor key I used I figured out by comparing the MQTT payload and doing a dexor using http://xor.pw/ against the message.
The last byte in the packet is a checksum (I assume) so if you take the payload from MQTT and make sure the lengths are right then you should be able to calculate the xor key.

The key I have figured out is in the parsezig.py and it is:

xorkey=bytes.fromhex('000000009a125a71ba9633f8c7fc4eafce9ee203c3a89ee498822ba00d9bc7bde054d5dd4ab02ba61a01fa477aec124811273f59ee848b9303903b3acd74678f8305d5ef33df79d5d56e00')

I am confident it is correct from byte 7.

Useful documents I found are:
[http://ww1.microchip.com/downloads/en/DeviceDoc/MiWi-Software-Design-Guide-User-Guide-DS50002851B.pdf](http://ww1.microchip.com/downloads/en/DeviceDoc/MiWi-Software-Design-Guide-User-Guide-DS50002851B.pdf)  
[http://ww1.microchip.com/downloads/en/Appnotes/00001283B.pdf](http://ww1.microchip.com/downloads/en/Appnotes/00001283B.pdf)  
[https://ww1.microchip.com/downloads/en/DeviceDoc/00001204C.pdf](https://ww1.microchip.com/downloads/en/DeviceDoc/00001204C.pdf)  
[http://ww1.microchip.com/downloads/en/appnotes/an1066%20-%20miwi%20app%20note.pdf](http://ww1.microchip.com/downloads/en/appnotes/an1066%20-%20miwi%20app%20note.pdf)  
[https://microchipdeveloper.com/led:miwi-protocol](https://microchipdeveloper.com/led:miwi-protocol)

| Offset | Message |
|-|-|
|01| Frame Control - 01 is a Data, otherwise 8 is a beacon as per the first doc on page 8
|02| Sequence number - Single byte hex counter that goes up every request.
|03| Assumed xored packet type value.
|04| Typically same value so assumed 00 and the xor value.
|05| Assumed xored packet length value, still haven't figured it out.
|06| Typically same value so assumed 00 and the xor value.
|07+| Main payload that matches to the MQTT message after being dexored.


## Finding the XOR Key

For this you need the hub pointing to the local docker MQTT stack **AND** a CC2531 able to sniff the zig packets. Ideally use a feeder as they are easy to move and send larger packets. 

The messages from mqtt will be in: docker/surepet/msgs
And the zig packets will be wherever you are running the whsniff docker container mapping the /data/zigsniff volume locally.

So below are two frames from MQTT and Zigsniff. Ideally a packet 29 from the feeder when the door opens / closes works the best. And the close you know is the last packet sent so go for that.

```
MQTT: Feb 09 23:08:34 surepetlocal/messages/162E02C0F9D5B370 60225f22 02b0 126 29 18 00 0d 00 c8 04 42 00 b1 e2 5e 05 80 e9 01 01 46 01 02 38 ff ff ff 01 fa ff ff 8e fe ff ff 60 fa ff ff 02 00 2c 01 00 00
ZIG: Feb  9, 2021 23:08:32.513476000 NZDT    70:b3:d5:f9:c0:02:2e:16 d9:8d:e8:fe:ff:12:1f:80 01f22a58b16c7369ba9b3330c3be4e1e2cc0e7832aa99fa29980135ff264c6471fab5b23b54f4b5ce5fef84756ed1248ef
```

So you can see the above two have around the same  timestamp and they are the last packet in a flow.
If you take after the "126" and start with the 29 and remove all spaces you end up with:
```
2918000d00c8044200b1e25e0580e9010146010238ffffff01faffff8efeffff60faffff02002c010000
```
Then from the 7th byte in on the Zig packet and removing the last byte as that is a check value you get
```
7369ba9b3330c3be4e1e2cc0e7832aa99fa29980135ff264c6471fab5b23b54f4b5ce5fef84756ed1248ef
```

Put them side by side:
```
2918000d00c8044200b1e25e0580e9010146010238ffffff01faffff8efeffff60faffff02002c010000
7369ba9b3330c3be4e1e2cc0e7832aa99fa29980135ff264c6471fab5b23b54f4b5ce5fef84756ed1248
```
And they are the same length.....
Now put the two values into:
http://xor.pw/#

and I get:
```
5a71ba9633f8c7fc4eafce9ee203c3a89ee498822ba00d9bc7bde054d5dd4ab02ba61a01fa477aec1248
```
So that is my XOR key from offset 07. Update `zigsniff.py` with that value at byte 7 in the file where it starts 5a, as yours will be different but at the same offset.

Then you can re-parse the air traffic using

```
grep -P "\t01 dddddd-tttttt.txt | python3 zigsniff.py 
```

And you should now have dexored zigsniff and output packets that should match the mqtt msgs folder.