# Pet Hub Local

This is project aims to completely reverse engineer the cloud service for the Sure Petcare "Connect" series of internet enabled pet devices and to provide a local network backend for the Connect Hub to connect to rather than using their cloud service.
It was born out of frustration with the cloud service being unstable over Christmas 2020/January 2021 and from a privacy perspective I prefer to not to have all my animals movements being sent off to their cloud service.
End goal is to connect it to Home Assistant and equally if folks wanted to they could connect it into OpenHAB as I have kept it generic and am just sending MQTT messages to topics with the configuration and status.

All trademarks of are the rights of their respective owners and this is completely unsupported by Sure Petcare and may void agreement you have with them as I am sure what I have built is against their terms of use somewhere in the pages of agreement I was required to tick the box to agree to that no one ever reads.

I have added support for the devices I have in my home which are:

- Connect Internet Hub
- Pet Door Connect
- Feeder Connect

Working on adding support for the following devices if others in the community can assist with traces.
- Cat Flap Connect
- Felaqua Connect

## Docker

This is the main code you are looking for, it is a docker compose stack that should be self contained and able to integrate directly into home assistant.
I have built it on a Debian Buster image on both an x64 and ODroid C2 which is similar to a Raspberry Pi 4.
It is built to be modular so if you want to pick up components such as the MQTT configuration and integrate that into your existing Mosquito MQTT host it should be very straight forward.
Have a read of the readme to see the setup tasks.

### Docker/source
This is the main python code used for interpreting the Hub messages that are sent from the hub over MQTT as well as supporting decrypting the 802.14.5 / MiWi packets sent over the air from the devices to the hub and converting them into a consistent message that is more useful than a stream of hex bytes. 
This directory is used by the pethub docker image when it starts pethubmqtt.py to talk to the single MQTT broker.

## Zigsniff

Zigsniff is a docker compose that uses a Zigbee / 802.14.5 CC2531 to sniff all traffic and then log it to a wireshark pcap file then translate it using PetHub.
This is really helpful for analysis of network traffic from the hub to the remote devices.
It doesn't need to run as a docker container, and if you check out 

## Docs

Various documentation I have found along the way and of the analysis of the Hub, a feeder and pet door and photo of the internal hub including pin outs.

## WemosMRFShield

Documentation on how to build a local hub replacement using a Wemos D1 Mini either the ESP32 or ESP8266 version and a custom build hardware shield based off https://doc.riot-os.org/group__boards__esp32__mh-et-live-minikit.html

## WemosPetHub

The arduino code to run the pet hub connect on a Wemos D1 Mini ESP32 or ESP32 and MRF24J40 using the MRF shield built above. This code is partially functional and needs work, but has been abandonded due to getting the hub messages completely decoded.
