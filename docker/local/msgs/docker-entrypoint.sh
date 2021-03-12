#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /mosquitto/msgs

exec /usr/bin/mosquitto_sub -h local_mqtt -p 1883 -v -t "pethublocal/#" | ts >> /mosquitto/msgs/mqtt."$(date +%Y-%m-%d)".log
