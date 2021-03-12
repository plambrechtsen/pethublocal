# Feeder messages - 126 - 2A/2D

The feeder is slightly different as it can send two messages in a single payload where the message length indicates how long the message is and sometimes there is a second message.
The feeder message is always 126 if it is to do with the feeder itself. This is a 2A message over the air. 
If the hub is sending a message to configure the feeder that is a 2D, and the feeder responds with a 2A.

The message is formatted as: - length - type - payload 

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|LEN| Length of the message in hex including the LEN payload such as 29 for a 41 byte feeder open / close message
|MSG| Message Type described below. 
|01| Always 00
|02| Hex based counter that goes from 00 - FF for the event number off the device itself. When the device is rebooted from a power cycle the number resets to 00. 

## 09 - Learning mode, scales reset, change bowls and boot message

Below are the messages with the operation in field 07 from the pet training (05) modes 1-4 and finishing up, feeder close delay (0d) ,  pressing the scales reset with nothing on the left hand scale (17) and an empty bowl on the right (18) also there is a 19 on boot.

|LEN|MSG|00|01|02|03|04|05|06|07-OP|08|09|10|11|Comment|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
0d|09|00|c0|04|1c|01|24|00|05|01|00|00|00|Train mode 1
0d|09|00|c3|04|25|01|24|00|05|02|00|00|00|Train mode 2
0d|09|00|c6|04|2b|01|24|00|05|03|00|00|00|Train mode 3
0d|09|00|c9|04|31|01|24|00|05|04|00|00|00|Train mode 4
0d|09|00|cc|04|38|01|24|00|05|00|00|00|00|Train mode finished
0d|09|00|cc|04|38|01|24|00|0a|94|11|00|00|Single bowl left weight
0d|09|00|cc|04|38|01|24|00|0b|00|00|00|00|Single bowl right weight
0d|09|00|cc|04|38|01|24|00|0a|a0|0f|00|00|Dual bowl left weight
0d|09|00|cc|04|38|01|24|00|0b|88|13|00|00|Dual bowl right weight
0d|09|00|cc|04|38|01|24|00|0c|01|00|00|00|Single bowl
0d|09|00|cc|04|38|01|24|00|0c|02|00|00|00|Dual bowl
0d|09|00|cc|04|38|01|24|00|0d|20|4e|00|00|Feeder delay slow
0d|09|00|cc|04|38|01|24|00|0d|a0|0f|00|00|Feeder delay normal
0d|09|00|cc|04|38|01|24|00|0d|00|00|00|00|Feeder delay fast
0d|09|00|66|00|d7|8d|00|00|17|6a|f7|ff|ff|Left side weight after zero
0d|09|00|67|00|d7|8d|00|00|18|d8|0c|00|00|Right side weight after zero 
0d|09|00|00|00|00|00|42|00|19|ab|b6|23|00|Weight at boot

Message information
| Offset | Message |
|-|-|
|02-06| ??? |
|07| Operation: 05 for learning mode, 0a left hand required weight or if one bowl total weight, 0b right hand weight, 0c single or dual bowl, 0d feeder close delay, absolute weight 17 (left) & 18 (right) when scales are zeroed and 19 boot weight.

### Operations
Always little endian so least significant bit first.

|07-OP|08-11|Comments|
|--|--|--|
|05|00-04| Learning mode - In offset 8 it is either 00 for returning out of learning mode or 01 to 04 depending on the learning mode.|
|0a|Left bowl weight| If it is a single bowl then the left weight is set and right weight is zeroed. Otherwise the desired weight to light up the leds on the feeder using the standard weight calculation
|0b|Right bowl weight| As above 0 for single bowl or right desired weight 
|0c|Bowl Count| Set single bowl = 01, dual bowl = 02
|0d|Delay| Feeder close delay, in milliseconds(?), so  204e = 20000 = Slow, a00f = 4000 = Normal or 0 = fast.
|17|Weight| User initiated scales reset - left hand scale
|18|Weight| User initiated scales reset - right hand scale
|19|Weight| Weight on boot

## 0B - Check feeder door state

If you are trying to remotely zero the feeder you need to make sure the door is open. So the hub sends:

|MSG|00|01|02|03|04|05|06|07-OP|08|09|10|Comment|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--
0b|00|00|0e|00|86|42|00|00|0d|00|00|Is door open?

Response:
You get a user initiated zero left 0d, and the state that the door was manually opened 29 message.
|LEN|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
0d|09|00|24|00|88|42|00|00|17|08|17|00|00|
29|18|00|25|00|88|42|00|00|01|02|03|04|05|06|07|07|00|00|02|00|00|00|00|01|00|00|00|07|16|00|00|00|00|00|00|02|00|28|01|00|00



## 18 - Feeder open / close action including open and close bowl weight

When the feeder is opened and closed using a microchip then you get two messages. The close weight is always zeros on an open, and if you don't re-zero the feeder when you close the first and second open weight should be the same.
When the button is pressed two 16 messages in a single message precede the 18 on its own. Unsure what the 16 messages mean so far. When the microchip is used to open the feeder then you don't get the 16 messages only a 18 on open and close. You can also get a 16 & 18 message in the same frame if you press the button quickly.

The below shows the feeder being manually opened so including the two 16 messages then the 18 message where a approximate 20 gram AA battery added to the left feeder and two AA batteries added to the right.
Then manually closing the feeder with two more 16 messages and then the 18 where the close weights are shown with the weight changing left -5.64 -> 17.87 and right -28.99 -> 11.44
Then using HDX chip 0113C870F2 to open the feeder and  remove the two batteries and weights go left  17.65 -> -5.62 and 9.68 -> -29.03

|LEN|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|30|31|32|33|34|35|36|37|38|39|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
12|16|00|13|00|f9|83|00|00|00|01|03|d0|c2|01|d8|07|02|00|12|16|00|14|00|f9|83|00|00|00|00|a1|d0|c2|01|9e|00|00|00
29|18|00|15|00|fb|83|00|00|01|02|03|04|05|06|07|04|00|00|02|cc|fd|ff|ff|00|00|00|00|ad|f4|ff|ff|00|00|00|00|05|00|24|01|00|00
12|16|00|16|00|06|84|00|00|00|01|84|f2|c2|01|e3|21|00|00|12|16|00|17|00|06|84|00|00|00|00|cf|f2|c2|01|4b|00|00|00
29|18|00|18|00|06|84|00|00|01|02|03|04|05|06|07|05|07|00|02|cc|fd|ff|ff|fb|06|00|00|ad|f4|ff|ff|78|04|00|00|06|00|24|01|00|00
29|18|00|19|00|18|84|00|00|01|13|f0|5d|2e|00|03|00|00|00|02|e5|06|00|00|00|00|00|00|c8|03|00|00|00|00|00|00|06|00|24|01|00|00
29|18|00|1a|00|20|84|00|00|01|13|f0|5d|2e|00|03|01|07|00|02|e5|06|00|00|ce|fd|ff|ff|c8|03|00|00|a9|f4|ff|ff|07|00|24|01|00|00


Message information
| Offset | Message |
|-|-|
|02-06| ??? |
|07-13| Chip Number FDX-B or HDX with calculation below.
|13| Chip type, 00 for HDX otherwise FDX-B.
|14 | Feed state - 00 Animal closed to Open , 01 Animal open to closed, 04 Manual open, 05 Manual closed, 06 scales zeroed while manually opened and zero button pressed on the back of feeder |
|15-16| Number of seconds the feeder was open for in little endian word |
|17| ?? Perhaps bowl or scales count if 1 or 2 as always 02 |
|18-21| Left hand open weight hex little endian signed with two decimal places. See weight calculation below.
|22-25| Left hand close weight same calculation as above.
|26-29| Right hand open weight same calculation as above.
|30-33| Right hand open weight same calculation as above.

# Unknown messages

## Boot payload
As shown below it includes a 0c and 10 messages then a 0b and then a further 0c and 10 messages. The 0b, 0c or 10 messages have not been observed any other time other than when the feeder boots.

|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0d|09|00|00|00|00|00|42|00|19|ab|b6|23|00|Boot weight
|18|0c|00|01|00|00|00|00|00|e7|13|00|00|ca|0c|00|00|26|01|00|00|00|00|00|00
|18|10|00|02|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00
|43|0b|00|03|00|0f|00|00|00|09|00|00|00|96|01|00|00|b5|01|00|00|c5|c4|95|b1|4b|4e|1a|9e|00|00|00|00|1f|00|00|00|33|38|51|0c|31|35|38|37|11|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|00|04|00|00
|18|0c|00|04|00|0f|00|00|00|e7|13|00|00|ca|0c|00|00|26|01|00|00|00|00|00|00
|18|10|00|05|00|0f|00|00|00|00|00|00|00|00|00|00|00|00|00|01|00|7b|00|b4|02

## 16 - no idea

Below showing multiple times opening and closing the feeder using the button. Perhaps this is the battery level and RSSI rather than the 132 messages which happen every hour as documented in the Hub.

|LEN|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
12|16|00|96|03|fa|1c|22|00|00|01|84|96|51|57|3a|b4|86|00
12|16|00|97|03|fb|1c|22|00|00|00|02|97|51|57|7e|00|00|00
12|16|00|99|03|0c|1d|22|00|00|01|de|cb|51|57|dc|34|00|00
12|16|00|9a|03|0c|1d|22|00|00|00|7a|cc|51|57|9c|00|00|00
12|16|00|9c|03|84|1d|22|00|00|01|8e|7e|53|57|14|b2|01|00
12|16|00|9d|03|84|1d|22|00|00|00|ff|7e|53|57|71|00|00|00
12|16|00|9f|03|93|1d|22|00|00|01|cf|b7|53|57|d0|38|00|00
12|16|00|a0|03|93|1d|22|00|00|00|52|b8|53|57|83|00|00|00
12|16|00|a2|03|cd|1d|22|00|00|01|14|8b|54|57|c2|d2|00|00
12|16|00|a3|03|cd|1d|22|00|00|00|79|8b|54|57|65|00|00|00
12|16|00|a5|03|f3|1d|22|00|00|01|5f|1f|55|57|e6|93|00|00
12|16|00|a6|03|f3|1d|22|00|00|00|e2|1f|55|57|83|00|00|00
12|16|00|a8|03|37|1e|22|00|00|01|bf|16|56|57|dd|f6|00|00
12|16|00|a9|03|37|1e|22|00|00|00|3e|17|56|57|7f|00|00|00
12|16|00|ab|03|96|1e|22|00|00|01|d4|69|57|57|96|52|01|00
12|16|00|ac|03|96|1e|22|00|00|00|51|6a|57|57|7d|00|00|00
12|16|00|ae|03|a4|1e|22|00|00|01|39|a2|57|57|e8|37|00|00
12|16|00|af|03|a4|1e|22|00|00|00|bf|a2|57|57|86|00|00|00
12|16|00|b1|03|b9|1e|22|00|00|01|cc|f2|57|57|0d|50|00|00
12|16|00|b2|03|b9|1e|22|00|00|00|49|f3|57|57|7d|00|00|00

Message information
| Offset | Message |
|-|-|
|02-06| Same / similar values as the message 18's when the feeder is opened and closed manually so perhaps a timestamp |
|07| Always 00 |
|08| Only 01 or 00 |
|09-16| ??? |


# Calculations

Below are python snippets to perform the required calculations on the relevant fields.

## Weight calculation

Signed reverse/little endian 4 byte with two decimal places for weight using the same calculation in the message  When zeroing scales it reports the absolute measured weight where it starts at 6df7ffff or -21.95 grams with nothing on the scale and goes up from there to be 0 with nothing in the bowl.

Python code to convert:
```
def convertweight(hexweightvalue):
  #Take little endian hex byte array and convert it into a int then divide by 100
  return int.from_bytes(b2ivalue, byteorder='little', signed=True)/100
```

## Microchip number

Using this site as a reference : https://www.priority1design.com.au/fdx-b_animal_identification_protocol.html
These are the chips that are inserted into animals and are documented in ISO 11784 & 11785. Typically all animals will have a FDX-B chip inserted in them.
Another important note about the chip number if you add two chips to be able to open the feeder. Then use chip 1 to open it, add chip 2, then remove chip one and then lastly remove chip 2 the last chip to leave is reported on the close event rather than the first chip used to open the feeder

### FDX-B
A reverse/little endian 7 byte / 48 bit using calculation for FDX-B chips which are the chips injected into your animal in the format 3 + 17 numbers ie 934.000090104497 maps to b1e25e0580e9. The first 10 bits of the 48 bit array is the country code, and the remaining 38 bits is the number.

### HDX
The door and feeders include two HDX chip that you could to attach to the animals collar if they hadn't been chipped with a HDX-B chip and the direct hex value is sent with an appended 03 where the number written on the chip is 0113C870F2 you get 0113c870f200

### Manual feeder operation
When you manually open the feeder using the button you get the chip id  01020304050607 

Python code to convert chip:
```
def convertchip(chipvalue):
  if chipvalue[6] == 0:
    #HDX
    return tohex(chipvalue)
  else
    #FDX-B - Take number and split into bits
    chipval = "{0:48b}".format(int.from_bytes(chipvalue, byteorder='little'))
    # Take first 10 bits for the country code, remaining bits for chip value.
    chip=str(int(chipval[:10],2)) + "." + str(int(chipval[10:],2)).zfill(12)
```
