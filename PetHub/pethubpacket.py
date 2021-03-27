#!/usr/bin/env python

"""
   Decode Sure Pet Packet

   Copyright (c) 2021, Peter Lambrechtsen (peter@crypt.nz)

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software Foundation,
   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
"""

import binascii, struct, time, sys, sqlite3, json
#import paho.mqtt.client as mqtt

from datetime import datetime
from operator import xor
from pathlib import Path

#Debugging mesages
PrintFrame = False #Print the before and after xor frame
PrintFrameDbg = False #Print the frame headers
Print126Frame = False #Debug the 2A / 126 feeder frame
Print127Frame = False #Debug the 2D / 127 feeder frame
Print132Frame = False #Debug the 3C / 132 hub and door frame
Print2Frame = False   #Debug the 2 frame

#Feeder static values
fStateArr={0:"Animal_open", 1:"Animal_shut", 4:"Manual_open", 5: "Manual_shut", 5: "ManualZeroScales", 6:"ZeroBoth", 7:"ZeroLeft", 8:"ZeroRight" } # Feeder State either open or closed
fCloseDelayArr={0:"Fast", 4000:"Normal", 20000:"Slow"}                          # Feeder Close Delay speed
fBowls={1:"Single", 2:"Double"}                                                 # Feeder number of bowls
dDirection={0x61:"out-61", 0x62:"out-62" } # Direction
pDLockState={0:"Unlocked", 1:"Keep pets in", 2:"Keep pets out", 3:"Lock both ways", 4:"Curfew Enabled lock" } # Pet Door Lock state
pDKeepPetsOutState={2:"Allow pets in", 3:"Keep Pets outs" } # Pet Door Keep Pets Out state
pDCurfewState={1:"Disabled",2:"Enabled "}

#Import xor key from pethubpacket.xorkey and make sure it is sane.
xorfile=Path('pethubpacket.xorkey').read_text()
if len(xorfile) > 20 and len(xorfile) % 2 == 0:
    xorkey=bytearray.fromhex(xorfile)
else:
    sys.exit("Corrupted pethubpacket.xorkey file, make sure the length is an even set of bytes")

#Load PetHubLocal database
conn=sqlite3.connect('pethublocal.db')
curs=conn.cursor()
conn.row_factory = sqlite3.Row

def feederchiptohex(chip):
    chiphex = ""
    if len(chip) == 10:
        #HDX Chip - Chip type seems to be always 03 and needs a 00 to pad it to the right length.
        chiphex = chip+'0003'
    else:
        #FDX-B Chip - Append 01 for chip type.
        chipsplit=chip.split(".")
        chipbin=format(int(chipsplit[0]),'b').zfill(10)+format(int(chipsplit[1]),'b').zfill(38)
        chipint=int(chipbin,2)
        chiphex=hex(int.from_bytes(chipint.to_bytes(6,'little'),'big'))[2:]
        chiphex = chiphex+'01'
        #print("Feeder Chip to Hex : " + chip + " " + chiphex)
    return chiphex

def feederhextochip(chiphex):
    chipbytes = bytes.fromhex(chiphex)
    chip = ""
    if len(chiphex) == 10:
        chip=chiphex
    elif chipbytes[5] == 0:
        #HDX
        chip=chiphex[:10]
    else:
        #FDX-B
        chipval = "{0:48b}".format(int.from_bytes(chipbytes[:6], byteorder='little'))
        chip=str(int(chipval[:10],2)) + "." + str(int(chipval[10:],2)).zfill(12)
        #print("Feeder Hex to Chip : " + chiphex + " " + chip)
    return chip

def doorchiptohex(chip):
    chipsplit=chip.split(".")
    chipbin=format(int(chipsplit[0]),'b').zfill(10)+format(int(chipsplit[1]),'b').zfill(38)
    #print(chipbin)
    chiphex=hex(int(chipbin[::-1],2))[2:]
    #print("Door   Chip to Hex : " + chip + " " + chiphex)
    return chiphex

def doorhextochip(chiphex):
    chipbin = "{0:48b}".format(int.from_bytes(bytes.fromhex(chiphex), byteorder='big'))[::-1]
    #print(chipbin)
    chip=str(int(chipbin[:10],2)) + "." + str(int(chipbin[10:],2)).zfill(12)
    #print("Door   Hex to Chip : " + chiphex + " " + chip)
    return chip

#Conversion of byte arrays into integers
def b2ih(b2ihvalue):
    #Divide int by 100 to give two decimal places for weights
    return str(int(b2is(b2ihvalue))/100)

def b2iu(b2ivalue):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='little', signed=False))

def b2is(b2ivalue):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='little', signed=True))

def b2ib(b2ivalue):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='big', signed=True))

def macconv(macaddress):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='big', signed=True))

def tohex(ba):
    return ''.join(format(x, '02x') for x in ba)

#Convert a int to hex
def hb(hexbyte):
    return format(hexbyte,'02x')
    
def petmovement(mac_address, deviceindex):
    curs.execute('select tag from tagmap where mac_address=(?) and deviceindex=(?)', (mac_address, deviceindex))
    tagval = curs.fetchone()
    if (tagval):
        tag=str(tagval[0])
        curs.execute('select name from pets where tag=(?)', ([tag]))
        petval = curs.fetchone()
        if (petval):
            petname=petval[0]
        else:
            petname="Unknown"
    else:
        petname="Unknown"
    return petname

#126 Frames aka 0x7E (126) or 0x2A (Wire value with TBC XOR) can have multiple messages, so need to loop until you get to the end
def parsemultiframe(device, payload):
    response = []
    operation = []
    multimsg = ""
    count=0
    while len(payload) > 2:
        if count>0:
            multimsg += ","
        multilen=payload[0]+1
        curmessage=payload[1:multilen]
        respmsg = parseframe(device, curmessage)
        op=respmsg[0]
        operation.append(op['OP'])
        respmsg.remove(op)
        response.append(respmsg)
        #Remove the parsed payload and loop again
        del payload[0:multilen]
        count += 1
    response.append({"OP":operation})
    return response

#Parse Feeder Frame 
#127 Frame aka 0x7F (127) or 0x2D (Wire value with TBC XOR) are a single payload vs 126 need parsemultiframe as they have multiple messages in a single frame
def parseframe(device, value):
    response = []
    msg=""
#   print("Parse : " + ''.join(format(x, '02x') for x in value))
    if value[0] == 0x00:
        #Send Acknowledge for data type
        response.append({"OP":"ACK"})
        response.append({"FF-00":"ACK-" + hb(value[8])})
        msg = "FF-00: Acknowledge data type " + hb(value[8])
        if Print126Frame:
            print(msg)
        return response
    elif value[0] == 0x01:
        #Send query for data type
        response.append({"OP":"Query"})
        response.append("FF-01:QRY-" + hb(value[8]))
        msg = "FF-01: Query data type " + hb(value[8])
        if Print126Frame:
            print(msg)
        return response
    elif value[0] == 0x07:
        #Send query for data type
        response.append({"OP":"MSG07"})
        response.append("FF-07:???-" + tohex(value[8:13]))
        msg = "FF-07: **TODO** data type " + tohex(value[8:13])
        if Print126Frame:
            print(msg)
        return response
    elif value[0]==0x09:
        response.append({"OP":"UpdateState"})
        if Print126Frame:
            print("FF-09: Update settings - ", hb(value[8]))
        msg="FF-09: Update settings-"
        submessagevalue = b2is(value[9:12])
        submessagevalueh = b2ih(value[9:12])
        if value[8]==0x05:
            msg += "TrainingMode=" + submessagevalue
            response.append("FF-09:TRN-" + submessagevalue)
        elif value[8]==0x0a:
            msg += "SetLeftWeight=" + submessagevalueh
            response.append("FF-09:SLW-" + submessagevalueh)
        elif value[8]==0x0b:
            msg += "SetRightWeight=" + submessagevalueh
            response.append("FF-09:SRW-" + submessagevalueh)
        elif value[8]==0x0c:
            msg += "SetFeederBowls=" + fBowls[int(submessagevalue)]
            response.append("FF-09:SBC-" + fBowls[int(submessagevalue)])
        elif value[8]==0x0d:
            msg += "CloseDelay=" + fCloseDelayArr[int(submessagevalue)]
            response.append("FF-09:CLD-" + fCloseDelayArr[int(submessagevalue)])
        elif value[8]==0x12:
            msg += "**TODO** 12=" + tohex(value[9:12])
            response.append("FF-09:?12=" + tohex(value[9:12]))
        elif value[8]==0x17:
            msg += "ZeroLeft=" + submessagevalueh
            response.append("FF-09:ZLW=" + submessagevalueh)
        elif value[8]==0x18:
            msg += "ZeroRight=" + submessagevalueh
            response.append("FF-09:ZRW=" + submessagevalueh)
        elif value[8]==0x19:
            msg += "**TODO** 19=" + tohex(value[9:12])
            response.append("FF-09:?19=" + tohex(value[9:12]))
        else:
            msg += "**TODO** Unknown-" + tohex(value)
            response.append("FF-09:???=" + tohex(value))
        if Print126Frame:
            print(msg)
        return response
    elif value[0] == 0x0b:
        response.append({"OP":"Boot"})
        msg = "FF-0b: **TODO** Boot 0b " + tohex(value[3:])
        response.append("FF-0B:" + tohex(value[3:]))
        if Print126Frame:
            print(msg)
        return response
    elif value[0] == 0x0c:
        response.append({"OP":"Boot"})
        msg = "FF-0c: **TODO** Boot 0c " + tohex(value[3:])
        response.append("FF-0C:" + tohex(value[3:]))
        if Print126Frame:
            print(msg)
        return response
    elif value[0] == 0x10:
        response.append({"OP":"Boot"})
        msg = "FF-10: **TODO** Boot 10 " + tohex(value[3:])
        response.append("FF-10:" + tohex(value[3:]))
        if Print126Frame:
          print(msg)
        return response
    elif value[0] == 0x11:
        response.append({"OP":"Boot"})
        msg = "FF-11: **TODO** Msg 11 " + tohex(value[3:])
        response.append("FF-11:" + tohex(value[3:]))
        if Print126Frame:
          print(msg)
        return response
    elif value[0] == 0x16:
        response.append({"OP":"MSG16"})
        msg = "FF-16: **TODO** Msg 16 " + tohex(value[3:])
        response.append("FF-16:" + tohex(value[3:]))
        if Print126Frame:
          print(msg)
        return response
    elif value[0] == 0x18:
        response.append({"OP":"Feed"})
        #Hard code feeder states
        if value[15] in fStateArr:
            msgval = {}
            if value[15] in range(4, 8):
                tag="Manual"
                msgval["Animal"]="Manual"
            else:
                tag = feederhextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    msgval["Animal"]=petval[0]
                else:
                    msgval["Animal"]=tag
            action=fStateArr[value[15]]
            feederopenseconds=b2iu(value[16:17])
            scaleleftfrom=b2ih(value[19:23])
            scaleleftto=b2ih(value[23:27])
            scalerightfrom=b2ih(value[27:31])
            scalerightto=b2ih(value[31:35])
            msgval["FA"]=action
            msgval["FOS"]=feederopenseconds
            msgval["SLF"]=scaleleftfrom #Or if single bowl
            msgval["SLT"]=scaleleftto
            msgval["SRF"]=scalerightfrom
            msgval["SRT"]=scalerightto

            #Return bowl count
            curs.execute('select bowltype from feeders where mac_address=(?)', ([device]))
            bowlval = curs.fetchone()
            if (bowlval):
                msgval["BC"]=bowlval[0]
            else:
                msgval["BC"]=1
            response.append(msgval)
            print("FF-18: Feeder door change - chip="+tag+",action="+fStateArr[value[15]]+',feederopenseconds='+ b2iu(value[16:17])+',scaleleftfrom='+b2ih(value[19:23])+',scaleleftto='+b2ih(value[23:27])+',scalerightfrom='+b2ih(value[27:31])+',scalerightto='+b2ih(value[31:35]))
            return response
        else:
            print("FF-18: Feeder door change - **TODO** unknown state " + hb(value[15]))
            response.append("FF-18:Unknown" + hb(value[15]))
            return respone
    else:
        response.append("FF-??:"+tohex(value))
        msg = "FF-**TODO** Unknown - " + tohex(value)
        print(msg)
        return response

#Parse Pet Door Frames aka 132's sent to the pet door
def parsedataframe(operation,device,offset,value):
    response = []
    operation = []

    message=bytearray.fromhex(value)
    if PrintFrameDbg:
        print("Operation: " + operation + " -offset- " + str(offset) + " -value- " + value)
    logmsg=""
    if offset == 34: #Set local time for Pet Door 34 = HH in hex and 35 = MM
        logmsg += device + " " + operation + "-Time    : "+ int(message[1]) +":"+ int(message[2])
        msgval = {}
        msgval['Time']=int(message[1]) +":"+ int(message[2])
        operation.append("SetTime")
        response.append(msgval)
        if int(message[0]) > 2:
            logmsg += "Addional bytes:"+tohex(message[3:])
    if offset == 36: #Lock state
        logmsg += device + " " + operation + "-Lockstate       : "+ pDLockState[int(message[1])]
        msgval = {}
        msgval['Lock']=pDLockState[int(message[1])]
        operation.append("LockState")
        response.append(msgval)
        if int(message[0]) > 1:
            logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset == 40: #Keep pets out allow incoming state
        logmsg += device + " " + operation + "-Keep pets out   : "+pDKeepPetsOutState[int(message[1])]
        msgval = {}
        msgval['PetsOut']=pDKeepPetsOutState[int(message[1])]
        operation.append("KeepPetsOut")
        response.append(msgval)
        if int(message[0]) > 1:
            logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset == 59: #Provisioned Chip Count
        logmsg += device + " " + operation + "-Prov Chip #     : "+(message[1])
        msgval = {}
        msgval['ChipCount']=message[1]
        operation.append("ProvChipCount")
        response.append(msgval)
        if int(message[0]) > 1:
            logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset >= 91 and offset <= 308: #Provisioned chips
        pet=round((int(offset)-84)/7) #Calculate the pet number
        chip=doorhextochip(value[4:]) #Calculate chip Number
        msgval = {}
        msgval['Chip']=chip
        msgval['PetOffset']=pet
        operation.append("ProvChip")
        response.append(msgval)
        logmsg += device + " " + operation + "-Prov Chip ID   "+ str(pet) + " : Chip number " + chip
    elif offset == 519: #Curfew
        logmsg += device + " " + operation + "-Curfew          : "+pDCurfewState[message[1]] + " Lock: "+str(message[2]).zfill(2)+":"+str(message[3]).zfill(2) + " Unlock: "+str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        msgval = {}
        msgval['CurfewState']=pDCurfewState[message[1]]
        msgval['CurfewOn']=str(message[2]).zfill(2)+":"+str(message[3]).zfill(2)
        msgval['CurfewOff']=str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        operation.append("Curfew")
        response.append(msgval)
    elif offset >= 525 and offset <= 618: #Pet movement in or out
        pet=round((int(offset)-522)/3)-1 #Calculate the pet number
        petname = petmovement(device, pet)
        if message[3] in dDirection:
            direction = dDirection[message[3]]
        else:
            direction = "Other " + hb(message[3])
        msgval = {}
        msgval['PetOffset']=pet
        msgval['Animal']=petmovement(device, pet)
        msgval['Direction']=direction
        operation.append("PetMovement")
        response.append(msgval)
        #logmsg += device + " " + operation + "-Pet Movement    : " + petname + " went " + direction
 #       print("Pet " + str(pet) + " went " + message[3])
    elif offset == 621: #Unknown pet went outside
        msgval = {}
        msgval['PetOffset']="621"
        msgval['Animal']="Unknown Pet"
        msgval['Direction']="Outside"
        operation.append("PetMovement")
        response.append(msgval)
        logmsg += device + " " + operation + "-Pet Movement    : Unknown pet went outside " + value
    else:
        logmsg += device + " " + operation + "-Other offset    : " + str(offset) + " len " + str(int(message[0])) + " msg " + tohex(message[1:])
        #print("other offset" + logmsg)

    response.append({"OP":operation})
    return response

def decodehubmqtt(topic,message):
    response = dict();
    msgsplit=message.split()
    topicsplit=topic.split('/')
    device=topicsplit[-1:][0]

    #Decode device name
    if device=="messages":
        response['device'] = "hub"
    else:
        curs.execute('select name from devices where mac_address=(?)', ([device]))
        devicename = curs.fetchone()
        if devicename:
            response['device'] = str(devicename[0])
        else:
            response['device'] = str(device)
    response['message'] = msgsplit
    
    response['timestamp'] = msgsplit[0]
    
    if msgsplit[1] == "1000":
        operation = "Command"
    else:
        operation = "Status"
    response['operation'] = operation


    print(message)
    #Device message
    if msgsplit[2] == "127": #Feeder frame sent/control message
        #ba = bytearray([0x7F])
        print("message 127")
        ba = bytearray.fromhex("".join(msgsplit[3:]))
        respmsg = parseframe(device,ba)
        operation = []
        op=respmsg[0]
        operation.append(op['OP'])
        respmsg.remove(op)
        resp = []
        resp.append(respmsg)
        resp.append({"OP":operation})
        response['message'] = resp
    elif msgsplit[2] == "126": #Feeder frame status message
        #ba = bytearray([0x7E])
        ba = bytearray.fromhex("".join(msgsplit[3:]))
        response['message'] = parsemultiframe(device,ba)

    elif msgsplit[2] == "132": #Pet Door Status
        #Status message has a counter at offset 4 we can ignore:
        if Print132Frame:
            print("132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        response['message'] = parsedataframe(operation,device, int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "2": #Action message setting value to Pet Door
        #Action message doesn't have a counter
        if Print2Frame:
            print("2 Message : "+message)
        msgsplit[4] = hb(int(msgsplit[4])) #Convert length at offset 4 which is decimal into hex byte so we pass it as a hex string to parsedoorframe
        response['message'] = parsedataframe(operation,device, int(msgsplit[3]),"".join(msgsplit[4:]))
    return response

def decodemiwi(timestamp,source,destination,framestr):
    framexor=bytearray.fromhex(framestr)
    #Convert MAC addresses into reverse byte format.
    sourcemac=''.join(list(reversed(source.split(":")))).upper()
    destinationmac=''.join(list(reversed(destination.split(":")))).upper()

    #Dexor the frame
    frame = list(map(xor, framexor, xorkey))

    if PrintFrame:
        print("Received frame at: " + timestamp + " from: " + sourcemac + " to: " + destinationmac)
        print("Packet:" + tohex(framexor))
        print("Dexor :" + tohex(frame))
    if len(frame) > 8:
        if PrintFrameDbg:
            print("Frame Type       :", hb(frame[2]))
            print("Frame Length     :", len(frame))
            print("Frame Length Val :", frame[4])
        payload=frame[6:]
        logmsg=""
        if frame[2] == 0x2a: #126 Message Feeder to Hub Message
            logmsg="2A: "
            if Print126Frame:
                print("FF-126 Request: " + tohex(payload))
            resmessage=parsemultiframe(payload)
            if len(resmessage) > 0 and Print127Frame:
                print("126 Resp :", resmessage)
        elif frame[2] == 0x2d: #127 Message Hub to Feeder control message
            logmsg="2D: "
            if Print127Frame:
                print("FF-127 Request: " + tohex(payload))
            resmessage=parseframe(payload)
            logmsg += resmessage
            if len(resmessage) > 0 and Print127Frame:
                print("Frame 2D message :", resmessage)
        elif frame[2] == 0x3c: #Pet door frame
            logmsg="132: " + tohex(payload)
            if Print132Frame:
                print("DF-132 Request: " + tohex(payload))
            print(parsedataframe('Status',source,int(b2ib(payload[0:2])),tohex(payload[2:-1])))
                
    else:
        logmsg = "Corrupt Frame " + tohex(frame)
    return "Received frame at: " + timestamp + " from: " + sourcemac + " to: " + destinationmac + " " + logmsg

def buildmqtt(type,value):
#  ts = str(binascii.hexlify(struct.pack('>I', round(datetime.utcnow().timestamp()))),'ascii')
  ts = hex(round(datetime.utcnow().timestamp()))[2:]
  return ts + " 1000 "+type+" " + " ".join(value[i:i+2] for i in range(0, len(value), 2))

#Generate message
def generatemessage(msgtype,msg):
    if type=="hub":
        print("TBC")
    elif type=="feeder":
        if operation == "ackfeederstatedoor":
        #Acknowledge the 18 door state.
            msgstr = "0000ZZ00TTTTTTTT180000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "ackfeederstate16":
            #Acknowledge the 16 state.
            msgstr = "0000ZZ00TTTTTTTT160000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "ackfeederstate09":
            #Acknowledge the 09 settings update state.
            msgstr = "0000ZZ00TTTTTTTT090000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "getcurrentstate0b":
        #Request boot message state 0b
            msgstr = "0100ZZ00TTTTTTTT0b00"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "getbootstate0c":
            #Request boot message state 0c
            msgstr = "0100ZZ00TTTTTTTT0c00"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "getbootstate10":
        #Request boot message state 10
            msgstr = "0100ZZ00TTTTTTTT1000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "getprovisionedchipsstate":
            #This tells the feeder to dump all provisioned chips
            msgstr = "0100ZZ00TTTTTTTT1100ff"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "getbootstate17":
            #Request boot message state 17
            msgstr = "0100ZZ00TTTTTTTT170000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "lidclosedelayfast":
            #Update lid close delay to fast = 0
            msgstr = "0900ZZ00TTTTTTTT0d00000000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "lidclosedelaynormal":
            #Update lid close delay to normal = 4000 (0fa0) - 4 seconds(?)
            msgstr = "0900ZZ00TTTTTTTT0da00f0000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "lidclosedelayslow":
            #Update lid close delay to slow = 20000 (4e20) - 20 seconds(?)
            msgstr = "0900ZZ00TTTTTTTT0d204e0000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "setleftscaleweight":
            #Set left or single bowl scale weight
            msgstr = "0900ZZ00TTTTTTTT0aWWWWWWWW"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WWWWWWWW", weight)
            return msgstr
        elif operation == "setrightscaleweight":
            #Set right scale weight
            msgstr = "0900ZZ00TTTTTTTT0bWWWWWWWW"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WWWWWWWW", weight)
            return msgstr
        elif operation == "setbowlcount":
            #Set bowl count either 01 for one bowl or 02 for two.
            msgstr = "0900ZZ00TTTTTTTT0cWW000000"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            msgstr = msgstr.replace("WW", format(opval,'02x'))
            return msgstr
        elif operation == "set12message":
            #Not sure what caused this but it happened around setting the scales - 12f4010000
            msgstr = "0900ZZ00TTTTTTTT12WWWWWWWW"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            weight= str(binascii.hexlify(struct.pack('<I', opvalue)),'ascii')
            msgstr = msgstr.replace("WWWWWWWW", weight)
            return msgstr
        elif operation == "zeroleftscale":
            #Zero the left scale, first need to check feeder is open via Message 18 state 
            msgstr = "0d00ZZ00TTTTTTTT001900000003000000000101"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "zerorightscale":
            #Zero the right scale, first need to check feeder is open via Message 18 state 
            msgstr = "0d00ZZ00TTTTTTTT001900000003000000000102"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            msgstr = msgstr.replace('TTTTTTTT', timestamp) # Timestamp
            return msgstr
        elif operation == "zerobothscales":
            #Zero the both scales, first need to check feeder is open via Message 18 state 
            msgstr = "0d00ZZ002601e354001900000003000000000103"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
            return msgstr
        else:
            print("Unknown message")
    elif type=="petdoor":
        if operation == "settime":
            #Set the time, packet 34 or 22 in hex
            msgstr = "022202HHMM"
            msgstr = msgstr.replace('HHMM', time)
            return msgstr
        if operation == "enablecurfew":
            #Set the time, packet 36 or 24 in hex
            msgstr = "02240104"
            return msgstr

    else:
        print("Unknown type")





'''
        #else:
        #    print("?? Request: " + tohex(payload))
        #    return "?? Request: " + tohex(payload)
#            devid = sourcemac + '-' + b2ib(payload[0:2])
#            pbdc = conn.cursor()
#            pbdc.execute('select name from doorpetmapping left join animals using (petid) where devicepetid=(?)', ([devid]))
#            pbd = pbdc.fetchone()
#            if (pbd):
    #            #I'm not sure if this is right or not, but there are very weird values sometimes for in / out
    #            direction=list(hb(payload[6]))
#                msg = pbd[0] + " went " + hb(payload[6])
    #            msg = pbd[0] + " went " + fDirection[int(direction[1])] + " in " + direction[0] + " seconds " + hb(payload[6])
#                logmsg += msg
#                if Print132Frame:
#                    print(msg)
#            else:
#                logmsg += tohex(payload)
    #                return pbd[0]
    #            else:
    #                pbdc.execute("INSERT OR IGNORE INTO doorpetmapping values((?), (?), (?)) ", ("0", device, int(id)))
    #                conn.commit()
    #                return "Unknown"
'''
