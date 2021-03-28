#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /mqtt/msgs

cd /mqtt

exec /usr/bin/mosquitto_sub -h local_mqtt -p 1883 -v -t "pethublocal/#" | ts | tee /mqtt/msgs/mqtt."$(date +%Y-%m-%d)".log 
#exec /usr/bin/mosquitto_sub -h local_mqtt -p 1883 -v -t "pethublocal/#" | ts > | tee /mqtt/msgs/mqtt."$(date +%Y-%m-%d)".log 
#| python /mqtt/mqttsub.py $(date +%Y-%m-%d)
