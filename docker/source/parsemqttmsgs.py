#!/usr/bin/env python3

# Reparse mqtt messages

import sys, re, os, pathlib
import paho.mqtt.client as mqtt
from time import sleep
from configparser import ConfigParser

PrintDebug = True # Enable debugging

if len(sys.argv) >= 2:
    parser = ConfigParser()
    if pathlib.Path("../config.ini").exists():
        with open("../config.ini") as stream:
            parser.read_string("[top]\n" + stream.read())

    if os.environ.get('HAMQTTIP') is not None:
        print("HAMQTTIP from environment")
        hamqttip = os.environ.get('HAMQTTIP')
    elif 'top' in parser and 'HAMQTTIP' in parser['top']:
        print("HAMQTTIP from config.ini")
        hamqttip = parser['top']['HAMQTTIP']
    else:
        print("HAMQTTIP from local file")
        hamqttip = "192.168.1.250"

    print("Connecting to "+hamqttip)
    if ':' in hamqttip:
        hamqttipsplit = hamqttip.split(':')
        mqtthost = hamqttipsplit[0]
        mqttport = int(hamqttipsplit[1])
    else:
        mqtthost = hamqttip
        mqttport = 1883

    if PrintDebug:
        print("HAMQTT Host: "+mqtthost)
        print("HAMQTT Port: "+str(mqttport))

    client = mqtt.Client()
    client.connect(mqtthost, mqttport)
    client.loop_start()

    print("MQTT File to replay :"+sys.argv[1])
    file1 = open(sys.argv[1], 'r') 
    Lines = file1.readlines()

    for line in Lines:
        newline=line.replace(' ',"\t",4)
        splitline = newline.split("\t")
        topic = re.sub("^.*/messages","pethublocal/messages",splitline[3])
        message = splitline[4].replace("\n","")
        if PrintDebug:
            print(topic,splitline[4])
        client.publish(topic,message,qos=1)
        sleep(0.14)

else:
    print("Command line argument for MQTT logfile to replay missing\n\nUsage python parsemqttmsgs.py ../output/msgs/mqtt.yyyy-mm-dd.log")
    exit(1)

