#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /mqtt/msgs

cd /mqtt

#Change timestamp to epoch time to make parsing it easier and the same as the pcap files
exec /usr/bin/mosquitto_sub -h mqtt -p 1883 -F '%U\t%t\t%p' -t "pethublocal/#" | tee /mqtt/msgs/mqtt."$(date +%Y-%m-%d)".log 
