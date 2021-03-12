# Feeder messages - 126

Like the door the Mac address of the door in reverse order is the topic the messages are put on.
The feeder is slightly different as it can send two messages in a single payload where the message length indicates how long the message is and sometimes there is a second message.
The feeder message is always 126 if it is to do with the feeder itself.

The message is formatted as: - length - type - payload 

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|LEN| Length of the message in hex including the LEN payload such as 29 for a 41 byte feeder open / close message
|MSG| Message Type described below such as 09 or 18 etc. 
|01| Always 00
|02| Hex based counter that goes from 00 - FF for the event number off the device itself. When the device is rebooted from a power cycle the number resets to 00. 

## 09 - Learning mode, scales reset and boot message

Below are the messages from the pet training (05) modes 1-4 and finishing up, and pressing the scales reset with nothing on the left hand scale (17) and an empty bowl on the right (18) also there is a 19 on boot.

|LEN|MSG|00|01|02|03|04|05|06|07|08|09|10|11|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
0d|09|00|c0|04|1c|01|24|00|05|01|00|00|00
0d|09|00|c3|04|25|01|24|00|05|02|00|00|00
0d|09|00|c6|04|2b|01|24|00|05|03|00|00|00
0d|09|00|c9|04|31|01|24|00|05|04|00|00|00
0d|09|00|cc|04|38|01|24|00|05|00|00|00|00
0d|09|00|66|00|d7|8d|00|00|17|6a|f7|ff|ff
0d|09|00|67|00|d7|8d|00|00|18|d8|0c|00|00
0d|09|00|00|00|00|00|42|00|19|ab|b6|23|00|

Message information
| Offset | Message |
|-|-|
|02-06| ??? |
|07| 05 for learning mode, absolute weight 17 (left) & 18 (right) when scales are zeroed and  |
|08-11| When in learning mode state being 00 (learning finished) or modes 01 to 04. When zeroing scales it reports the absolute measured weight where it starts at 6df7ffff or -21.95 with nothing on the scale and goes up from there to be around 0 with nothing in the bowl.


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
|07-13| Chip Number using unknown calculation for FDX-B chips which are the chips injected into your animal in the format 3 + 17 numbers ie 934.000090104497 maps to b1e25e0580e901 then the first 4 bytes b1e25e05 reverse byte = 055ee2b1 = 90104497. Unsure how the country code 934 is calculated. If it is a HDX chip you such as the tags included with the feeder to attach to the animals collar the direct value is sent with an appended 0003 where the number written on the chip is 0113C870F2 you get 0113c870f20003 or 01020304050607 for manual open when you press the button. Also if you add two chips while the feeder is open and remove the first one first leaving the second one in place the last chip to leave is reported on the close event rather than the first chip used to open the feeder.
|14 | Feed state - 00 Animal closed to Open , 01 Animal open to closed, 04 Manual open, 05 Manual closed, 06 scales zeroed while manually opened and zero button pressed on the back of feeder |
|15-16| Number of seconds the feeder was open for in two reverse byte hex |
|17| ?? Perhaps bowl or scales count if 1 or 2 as always 02 |
|18-21| Left hand open weight hex little endian signed with two decimal places so you need to divide by 100 to get the value in grams. Positive values 28090000 -little endian reverse> 00000928 -hex to decimal> 2344 -divide by 100> 23.44grams or for the negative values c6f4ffff -> fffff4c6 -> -2874 -> -28.74 
|22-25| Left hand close weight same calculation as above.
|26-29| Right hand open weight same calculation as above.
|30-33| Right hand open weight same calculation as above.


# Unknown messages

## Boot payload
As shown below it includes a 0c and 10 messages then a 0b and then a further 0c and 10 messages. The 0b, 0c or 10 messages have not been observed any other time other than when the feeder boots.

|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26|27|28|29|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|25|26
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0d|09|00|00|00|00|00|42|00|19|ab|b6|23|00
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
