#!/bin/bash

d=$(date +%Y%m%d-%H%H%S)

cp ../../PetHub/* .
whsniff -k -c 15 | tee $d.pcap | tshark -r - -T fields -e frame.time -e wpan.src64 -e wpan.dst64 -e data -l | unbuffer -p tee $d.txt | unbuffer -p grep -P "\t01" | python3 -u zigparse.py | unbuffer -p tee $d.update.txt
