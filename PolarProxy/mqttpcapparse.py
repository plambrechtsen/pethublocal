import sys,binascii,array
#import pethubpacket as phlp

PrintMQTTline = True
WriteMQTTtext = True

if WriteMQTTtext == True:
    if sys.argv[1]:
        file = open(sys.argv[1], "a")
    else:
        file = open("mqttpcaptext.txt", "a")

for line in sys.stdin:
    #print(line)
    if len(line) > 1:
        inline=line.split('\t')
        if len(inline) > 1:
            #Sometimes the cloud service sends two MQTT messages in a single packet, so with wireshark they are comma delmited so split them out and make two lines in the log
            topic=inline[3].split(',')
            message=inline[4].split(',')
            for ziptopic,zipmessage in zip(topic,message):
                timestamp = inline[0].replace('\t',' ')
                if "\n" not in zipmessage:
                    zipmessage +="\n"
                mqttframe=bytes.fromhex(zipmessage).decode("ASCII")
                if PrintMQTTline == True:
                    print("MQTT: ",timestamp,inline[1],inline[2],ziptopic, mqttframe)
                if WriteMQTTtext == True:
                    file.write("{}\t{}\t{}\t{}\t{}".format(inline[0],inline[1],inline[2],ziptopic,mqttframe+"\n"))
                #msg = phlp.decodehubmqtt(ziptopic, mqttframe)
                #print(msg)

if WriteMQTTtext == True:
    file.close()
