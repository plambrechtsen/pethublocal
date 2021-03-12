#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /mosquitto/conf
mkdir -p /mosquitto/db
mkdir -p /mosquitto/logs
[[ ! -f /mosquitto/conf/mosquitto.conf ]] && cp /default/* /mosquitto/conf

exec /usr/sbin/mosquitto -c /mosquitto/conf/mosquitto.conf
