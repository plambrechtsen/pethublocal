#!/usr/bin/env python3

'''
Convert serial output of the firmware update process on the hub to grab the password for the PKCS12 certificate in credentials.

For this you need to connect a TTL serial adapter to the correct header pins. This will void any warranty and you are responsible if you break it... With that out of the way.

Either you can download the firmware from Surepet during boot, or if you have the local docker stack setup then enable firmware support as per:

https://github.com/plambrechtsen/pethublocal/blob/main/docker/web/app.py#L9 and set 

SupportFirmware = True

Then the next time the hub reboots and connects to the docker stack then the docker stack will download the firmware and save it locally for future use.

If you read: https://github.com/plambrechtsen/pethublocal/tree/main/docs/Hub

You need to connect to pins 7(GND) and 4&5 for RX/TS.
I personally find it easier to solder to the connector so then you connect to pins 3 (GND) and 7&8.

Then connect the serial console at 57600 8/N/1

If you are using windows then I recommend Putty and you can set the line of scroll back to something larger than 2000 characters under Window -> Lines of Scrollback to something like 2000000
This is because a firmware update generates about 20k lines.

** BE AWARE YOU ARE JUST ABOUT TO FIRMWARE UPDATE YOUR HUB. ****DO NOT UNPLUG IT WHILE IT IS DOING THE UPDATE AS YOU COULD BRICK YOUR HUB JUST LEAVE IT TO COMPLETE!!!!**** **

Lastly unplug the power to the hub and then hold down the reset button underneath the hub with a pen or something then plug the power in and you will see the the firmware update process start.

Save the log to a text file and run it with this script.

'''

import sys, pathlib, re, codecs

#Debugging mesages
PrintDebug = True #Print debugging messages

#Check if a command line parameter was passed, and then it's a json file we need to load rather than talking to the cloud.
if len(sys.argv) >= 2:
    if pathlib.Path(sys.argv[1]).exists():
        with codecs.open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as firmware:
            sn=""
            haslongserial=False
            serial={}
            while True:
                line = firmware.readline()
                if not line: #EOF
                    break
                if sn == "" and (line.startswith("serial_number=") or "As text:" in line):
                    snre = re.compile('H\d+-\d+')
                    sn=snre.findall(line)[0]
                    print("Serial Number:"+sn)
                if haslongserial == True:
                    if "length=1024" in line:
                        #End of serial number.
                        haslongserial = False
                        print("Serial extracted")
                        serialnumberorder = [10,7,8,11,0,5,12,13,15,1,2,14,4,6,3,9]
                        print('Firmware XOR String for '+sn+' :',"".join(serial.values())) # list() not needed in Python 2
                        print('Certificate Password for '+sn+':',''.join(list(map(serial.get, serialnumberorder))).upper()) # list() not needed in Python 2
                        exit(0)
                    else:
                        if len(line) > 2:
                            #print("Line length",len(line))
                            if line.startswith("10 "):
                                #If we 
                                print("Corrupted file")
                                exit(1)
                            linesplit=line.split()
                            #print(linesplit)
                            serial[int(linesplit[0],16)]=linesplit[1].zfill(2) #Pad zero to make a byte if it is a single character
                if "Read 319a 1d000000 47 1d000000 1000 1" in line and haslongserial == False:
                    print("Found Serial")
                    haslongserial = True
        firmware.close()
else:
    print("Need to pass a command line argument of the console log, ideally starting with the line 'serial_number=' or at a minimum 'Read 319a 1d000000 47 1d000000 1000 1'")