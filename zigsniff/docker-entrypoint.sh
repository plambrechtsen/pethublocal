#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /data/zigsniff

#!/bin/bash

d=$(date +%Y%m%d-%H%M%S)

cd /data/zigsniff

[[ -f pethublocal.db ]] && echo "Pethublocal.db exists" || sqlite3 pethublocal.db < /data/pethublocal.sql

# The below is designed to be modular and capture traces at each step using tee, first it creates a pcap from whsniff, then the .txt from wireshark and then the parsed payload using zigparse.

exec /data/whsniff -c 15 | tee $d.pcap | tshark -r - --disable-protocol lwm -Y "wpan.dst_pan == 0x3421" -T fields -e frame.time_epoch -e wpan.src64 -e wpan.dst64 -e data -l | unbuffer -p tee $d.txt | grep --line-buffered -P "\t01" | python3 -u /data/zigparse.py | unbuffer -p tee $d.update.txt
