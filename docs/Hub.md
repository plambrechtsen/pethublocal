
# Hub messages

The hub has a standard prefix format for all messages.
- Always a UTC Timestamp
- Two byte hex status or command message
	- Status messages are 0xx0 where the xx is a counter 00 - ff in lower case.
	- Command messages are always 1000 instead of the 

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|TS| Timestamp
|C| Two byte status or command

## Message type 10 - Uptime

Sends a message every hour indicating how long the hub has been up.

|MSG|00|01|02|03|04|05|06|
|--|--|--|--|--|--|--|--|
10|00009600|29|21|22|42|60147ca2|2

Standard message header offsets that don't change per message type:
| Offset | Message |
|-|-|
|10| Message Type 10
|00| 8 digit zero padded decimal counter of the number of minutes the hub has been up. So first message is always 00000060 after 1 hour.
|01| Day of month (UTC)
|02| Hour (UTC)
|03| Minute (UTC)
|04| Second (UTC)
|05| Unix time stamp, same value as TS.
|06| Reconnect count, starts at 0 and if the hub loses connection to the cloud service this iterates.


## Message type 132
The 132 messages are generate by the Feeder and the Hub. 

The boot message seems to dump a memory offset, where device 1 Mac starts at 45 (XX), device 2 at 61 (YY) which also corresponds to the topic in upper case.

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

# Command Messages

## Query Registers / Status - Type 3
| Message |
|-|
|TS 1000 3 0 205

This command from the cloud service  tells the hub to send all the registers from the Hub to the cloud similar to doing a boot. The 205 is the last register on the Hub so it must be a 3 to dump registers start at 0 and end at 205.

## Change Register - Type 2

To alter the registers the register value is sent plus the length.

### 18 - Flash ears

This register is used to enable or disable the ears, and to flash them such as when an animal comes in the door.

| Message | Type
|-|-|
|TS 1000 2 18 1 00|Ears dimmed
|TS 1000 2 18 1 01|Ears bright
|TS 1000 2 18 1 04|Ears off
|TS 1000 2 18 1 80|Flash ears 3 times
|TS 1000 2 18 1 81|Flash ears twice

### 15 - Adoption Mode

Used to adopt new devices to the hub, to do this you need to enable adoption mode on the hub first, then press the "connect" button on the device.

| Message | Type
|-|-|
|TS 1000 2 15 1 00|Enable Adoption
|TS 1000 2 15 1 02|Disable Adoption
