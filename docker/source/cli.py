#!/usr/bin/env python3

#Command line interface

PrintDebug = True #Enable debugging

import sys, os, pathlib, sqlite3
import pethubpacket as p
import paho.mqtt.client as mqtt
from configparser import ConfigParser
from box import Box

#Load PetHubLocal database
def dict_factory(cursor, row): #Return results as a Box/dict key value pair
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return Box(d)
conn=sqlite3.connect("pethublocal.db")
conn.row_factory = dict_factory
curs=conn.cursor()

if len(sys.argv) > 1:

    if "hub" in sys.argv[1]:
        print("len ",len(sys.argv))
        curs.execute('select mac_address from devices where product_id = "1"')
        device = curs.fetchone()
        operations = p.generatemessage(device.mac_address, 'operations','')
        if device and len(sys.argv) <= 2:
            print("Hub Supported operations:")
            for key in operations:
                print ('Hub: {:<15s}{:>3s}'.format(key, operations[key].desc))
        elif device and len(sys.argv) == 3:
            if sys.argv[2] in operations:
                print("Op Good")
        elif not device:
            print('Device not found')
        else:
            if PrintDebug:
                print(device)
            print('Send a Hub message')
            setvalue = p.generatemessage(device.mac_address, sys.argv[2],'')
            print(setvalue)

    elif "petdoor" in sys.argv[1]:
        setvalue = p.generatemessage("xpetdoormacaddyx", sys.argv[2],sys.argv[3])
        print(setvalue)

    elif "feeder" in sys.argv[1]:
        setvalue = p.generatemessage("xfeedermacaddyxx", sys.argv[2],sys.argv[3])
        print(setvalue)

    else:
        curs.execute('select product_id from devices where mac_address = "' + sys.argv[1] + '"')
        device = curs.fetchone()
        if device:
            print("arg length",len(sys.argv))
            if len(sys.argv) > 3:
                status = sys.argv[3]
            else:
                status = ""
            setvalue = p.generatemessage(sys.argv[1], sys.argv[2],status)
            print(setvalue)

    if setvalue:
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
            print("HAMQTTIP not set in config.ini, exiting")
            exit(1)

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

        mc = mqtt.Client()
        mc.connect(mqtthost, mqttport, 30)

        ret=mc.publish(setvalue.topic,setvalue.msg,qos=1)
   
