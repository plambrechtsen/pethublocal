# Hub messages

The hub has a standard prefix format for all messages. Always a UTC Timestamp, then two byte hex counter that is 0xx0 where the xx counte from 00 - ff.

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|TS| Timestamp
|C| Two byte counter 

## Message type 10 - Uptime

Sends a message every hour indicating how long the hub has been up.

|MSG|00|01|02|03|04|05|06|
|--|--|--|--|--|--|--|--|
10|00009600|29|21|22|42|60147ca2|2

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|10| Message Type 10
|00| Decimal counter of the number of minutes the hub has been up. So first message is always 00000060 after 1 hour.
|01| Day of month (UTC)
|02| Hour (UTC)
|03| Minute (UTC)
|04| Second (UTC)
|05| Unix time stamp, same value as TS.
|06| Always 2 ??


## Message type 132
The 132 messages are generate by the Feeder and the Hub. 

The boot message seems to dump a memory offset, where device 1 Mac starts at 45 (XX), device 2 at 61 (YY) which also corosponds to the topic in upper case.

|MSG|00|01|02|03|04|05|06|07|08|09|10|11|12|
|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
132|0|0|8|01|cd|00|02|00|2b|00|03
132|1|8|3|00|01|b1
132|2|13|3|00|00|00
132|3|18|1|00
132|4|20|8|00|00|00|00|0f|00|00|00
132|5|28|8|02|03|04|00|00|00|00|00
132|6|36|8|00|00|00|00|00|00|00|0a
132|7|44|8|02|XX|XX|XX|XX|XX|XX|XX
132|8|52|8|XX|11|00|18|82|57|14|40
132|9|60|8|39|YY|YY|YY|YY|YY|YY|YY
132|10|68|8|YY|8d|ff|ff|ff|71|84|40
132|11|76|8|39|00|00|00|00|00|00|00
132|12|84|8|00|fc|ff|ff|ff|ff|ff|ff
132|13|92|8|ff|00|00|00|00|00|00|00
132|14|100|8|00|fc|ff|ff|ff|ff|ff|ff
132|15|108|8|ff|00|00|00|00|00|00|00
132|16|116|8|00|fc|ff|ff|ff|ff|ff|ff
132|17|124|8|ff|00|00|00|00|00|00|00
132|18|132|8|00|fc|ff|ff|ff|ff|ff|ff
132|19|140|8|ff|00|00|00|00|00|00|00
132|20|148|8|00|fc|ff|ff|ff|ff|ff|ff
132|21|156|8|ff|00|00|00|00|00|00|00
132|22|164|8|00|fc|ff|ff|ff|ff|ff|ff
132|23|172|8|ff|00|00|00|00|00|00|00
132|24|180|8|00|fc|ff|ff|ff|ff|ff|ff
132|25|188|8|ff|00|00|00|00|00|00|00
132|26|196|8|00|fc|ff|ff|ff|ff|ff|ff

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|27| Updates every hour with a single value.
|55 & 71 | Update from devices every time they connect. Suspect RSSI and / or battery level reporting back.
|70| Somtimes get 2 or 3 bytes reporting back on door, but dont get similar with 54 on feeder.
