#Parse pcap file and print to console, log file or send it to pethublocal or to mqtt to be processed

import sys
import re
import time
import os
import datetime
import json
import paho.mqtt.client as mqtt

#Send the messages to MQTT
hamqttip = "127.0.0.1"

PrintMQTTline = True
WriteMQTTtext = True
WritePetHubText = True
SendToMQTT = False

if WriteMQTTtext == True:
    if sys.argv[1]:
        file = open(sys.argv[1], "a")
    else:
        file = open("mqttpcaptext.txt", "a")

if WritePetHubText == True:
    import pethubpacket as phlp
    if sys.argv[1]:
        pethubfile = open("pethub-"+sys.argv[1], "a")
    else:
        pethubfile = open("pethub-mqttpcaptext.txt", "a")

def on_publish(client,userdata,result):
    pass

if SendToMQTT:
    print("Connecting to "+hamqttip)
    mc = mqtt.Client('SendPetHub')
    if ':' in hamqttip:
        hamqttipsplit = hamqttip.split(':')
        mqtthost = hamqttipsplit[0]
        mqttport = int(hamqttipsplit[1])
    else:
        mqtthost = hamqttip
        mqttport = 1883

    print("HAMQTT Host: "+mqtthost)
    print("HAMQTT Port: "+str(mqttport))
    #mc.username_pw_set(username=os.environ.get('HAMQTTUSERNAME'), password=os.environ.get('HAMQTTPASSWORD'))
    mc.on_publish = on_publish
    mc.connect(mqtthost, mqttport, 30)
    mc.loop_start()

for line in sys.stdin:
    #print(line)
    if len(line) > 1:
        inline=line.split('\t')
        if len(inline) > 1:
            #Sometimes the cloud service sends two MQTT messages in a single packet, so with wireshark they are comma delmited so split them out and make two lines in the log
            topic=inline[3].split(',')
            message=inline[4].split(',')
            for ziptopic,zipmessage in zip(topic,message):
                timestamp = datetime.datetime.utcfromtimestamp(float(inline[0])).strftime('%Y-%m-%d %H:%M:%S')
                pethublocaltopic = re.sub(r".*messages", "pethublocal/messages", ziptopic)
                #Some versions of tshark decode pcap files as a hex string, others decode it as ascii, so this handles if it is a hex string and decodes it.
                if len(zipmessage.split(' ')) == 1:
                    zipmessage=bytes.fromhex(zipmessage).decode("ASCII")
                if SendToMQTT:
                    pethublocalmessage = re.sub(r"\n", "", zipmessage)
                    #print(pethublocaltopic, pethublocalmessage)
                    ret=mc.publish(pethublocaltopic, pethublocalmessage, qos=1, retain=False)
                    #print(ret)
                    time.sleep(.35)
                if PrintMQTTline:
                    print("MQTT: ",timestamp,inline[1],inline[2],pethublocaltopic, zipmessage)
                if "\n" not in zipmessage:
                    zipmessage +="\n"
                if WriteMQTTtext:
                    file.write("{}\t{}\t{}\t{}\t{}".format(inline[0],inline[1],inline[2],pethublocaltopic,zipmessage))
                if WritePetHubText:
                    msg = phlp.decodehubmqtt(pethublocaltopic, zipmessage)
                    pethubfile.write(json.dumps(msg)+"\n")
                    #print(msg)

if WriteMQTTtext:
    file.close()

if WritePetHubText:
    pethubfile.close()

if SendToMQTT:
    mc.loop_stop()
    mc.disconnect()
