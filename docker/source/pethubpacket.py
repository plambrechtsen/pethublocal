#!/usr/bin/env python3

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

import binascii, struct, time, sys, sqlite3, json, glob

from datetime import datetime
from operator import xor
from pathlib import Path
from enum import IntEnum
from datetime import date, timedelta
from pethubconst import *

#Debugging mesages
PrintFrame = True #Print the before and after xor frame
PrintFrameDbg = False #Print the frame headers
Print126Frame = True #Debug the 2A / 126 feeder frame
Print127Frame = True #Debug the 2D / 127 feeder frame
Print132Frame = True #Debug the 3C / 132 hub and door frame
Print2Frame = False   #Debug the 2 frame

#Import xor key from pethubpacket.xorkey and make sure it is sane.
for file in glob.glob("pethubpacket.xorkey"):
    xorfile=Path(file).read_text()
    if len(xorfile) > 20 and len(xorfile) % 2 == 0:
        xorkey=bytearray.fromhex(xorfile)
    else:
        sys.exit("Corrupted pethubpacket.xorkey file, make sure the length is an even set of bytes")

#Load PetHubLocal database
for sqlitefile in glob.glob("pethublocal.db"):
    conn=sqlite3.connect(sqlitefile)
curs=conn.cursor()
conn.row_factory = sqlite3.Row

#Create hex timestamp
ts = hex(round(datetime.utcnow().timestamp()))[2:]

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
    if int(chiphex,16) == 0:
        chip = "Null"
    else:
        chipbin = "{0:48b}".format(int.from_bytes(bytes.fromhex(chiphex), byteorder='big'))[::-1]
        #print(chipbin)
        chip=str(int(chipbin[:10],2)) + "." + str(int(chipbin[10:],2)).zfill(12)
        #print("Door   Hex to Chip : " + chiphex + " " + chip)
    return chip

def bit2int(number,start,bitlen,fill):
     return str(int(number[start : start+bitlen],2)).zfill(fill)

def int2bit(number,fill):
     return str(bin(int(number))[2:]).zfill(fill)

def feedertimestamptostring(number):
    binstring = str(bin(number)[2:]).zfill(32)
    return '{0}-{1}-{2} {3}:{4}:{5}'.format(bit2int(binstring,0,6,2),bit2int(binstring,6,4,2),bit2int(binstring,10,5,2),bit2int(binstring,15,5,2),bit2int(binstring,20,6,2),bit2int(binstring,26,6,2))

def feedertimestampfromnow():
    now = datetime.now() # Current timestamp
    return int(int2bit(now.strftime("%y"),6)+int2bit(now.month,4)+int2bit(now.day,5)+int2bit(now.hour,5)+int2bit(now.minute,6)+int2bit(now.second,6),2).to_bytes(4,'little').hex()

def bltoi(value): #Bytes little to integer
    return int.from_bytes(value,byteorder='little')

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

def b2ibs(b2ivalue):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='big', signed=True))

def b2ibu(b2ivalue):
    #Take little endian hex byte array and convert it into a int then into a string.
    return str(int.from_bytes(b2ivalue, byteorder='big', signed=False))

def tohex(ba):
    return ''.join(format(x, '02x') for x in ba)

#Convert a int to hex
def hb(hexbyte):
    return format(hexbyte,'02x')
    
def petnamebydevice(mac_address, deviceindex):
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

#Parse Feeder and Cat Flap Multi-Frame
#126 Frames aka 0x7E (126) or 0x2A (Wire value with TBC XOR) can have multiple messages, so need to loop until you get to the end
def parsemultiframe(device, payload):
    response = []
    operation = []
    while len(payload) > 2:
        subframelength=payload[0]+1
        currentframe=payload[1:subframelength]
        frameresponse = parseframe(device, currentframe)
        response.append(frameresponse)
        #Append the operation to a separate array we attach at the end.
        op=frameresponse['OP']
        operation.append(op)
        #Remove the parsed payload and loop again
        del payload[0:subframelength]
    response.append({"OP":operation})
    return response

#Parse Feeder and Cat Flap Frame 
#127 Frame aka 0x7F (127) or 0x2D (Wire value with TBC XOR) are a single payload vs 126 need parsemultiframe as they have multiple messages in a single frame
def parseframe(device, value):
    frameresponse = {}
    msg = ""

    #Frame timestamp value
    print(tohex(value))
#    print(tohex(value[4:8]))
    frametimestamp = feedertimestamptostring(bltoi(value[4:8]))
#    print(str(frametimestamp))
    frameresponse["framets"]=frametimestamp

    if value[0] in [0x07, 0x0b, 0x0c, 0x10, 0x16]: #Unknown messages
        op=hb(value[0])
        frameresponse["OP"]="Msg"+op
        frameresponse["MSG"]=tohex(value[3:])
        if Print126Frame:
            print("FF-"+op+": **TODO** Msg " + tohex(value[3:]))
    elif value[0] == 0x00: #Send Acknowledge for data type
        frameresponse["OP"]="Ack"
        frameresponse["MSG"]=hb(value[8])
        if Print126Frame:
            print("FF-00:ACK-" + hb(value[8]))
    elif value[0] == 0x01: #Send query for data type
        frameresponse["OP"]="Query"
        frameresponse["MSG"]=hb(value[8])
        if Print126Frame:
            print("FF-01:QRY-" + hb(value[8]))
    elif value[0] == 0x09: #Update state
        frameresponse["OP"]="UpdateState"
        submessagevalue = b2is(value[9:12])
        if value[8]==0x05: # Training mode
            msg = {"MSG":"FF-09:TRN-" + submessagevalue} #Training Mode
            frameresponse["SUBOP"]="Training"
            frameresponse["MODE"]=submessagevalue
        elif value[8]==0x0a: #Set Left Weight
            msg += "FF-09:SLW-" + submessagevalue
            frameresponse["SUBOP"]="SetLeftWeight"
            frameresponse["WEIGHT"]=submessagevalue
        elif value[8]==0x0b:
            msg += "SetRightWeight=" + submessagevalue
            frameresponse["SUBOP"]="SetRightWeight"
            frameresponse["WEIGHT"]=submessagevalue
        elif value[8]==0x0c:
            msg += "FF-09:SBC-" + FeederBowls(int(submessagevalue)).name
            frameresponse["SUBOP"]="SetBowls"
            frameresponse["BOWLS"]=FeederBowls(int(submessagevalue)).name
        elif value[8]==0x0d:
            msg += "FF-09:CLD-" + FeederCloseDelay(int(submessagevalue)).name
            frameresponse["SUBOP"]="SetCloseDelay"
            frameresponse["DELAY"]=FeederCloseDelay(int(submessagevalue)).name
        elif value[8]==0x12:
            msg += "FF-09:?12=" + tohex(value[9:12])
            frameresponse["SUBOP"]="SetTODO"
            frameresponse["MSG"]=tohex(value[9:12])
        elif value[8]==0x17:
            msg += "ZeroLeftWeight=" + submessagevalue
            frameresponse["SUBOP"]="ZeroLeftWeight"
            frameresponse["WEIGHT"]=submessagevalue
        elif value[8]==0x18:
            msg += "ZeroRightWeight=" + submessagevalue
            frameresponse["SUBOP"]="ZeroRigtWeight"
            frameresponse["WEIGHT"]=submessagevalue
        elif value[8]==0x19:
            msg += "FF-09:?19=" + tohex(value[9:12])
            frameresponse["SUBOP"]="SetTODO"
            frameresponse["MSG"]=tohex(value[9:12])
        else:
            msg += "FF-09:???=" + tohex(value[9:12])
            frameresponse["SUBOP"]="SetTODO"
            frameresponse["MSG"]=tohex(value[9:12])
        if Print126Frame:
            print(msg)
    elif value[0] == 0x11: #Provision chip to device and set lock states on cat flap.
        curs.execute('select product_id from devices where mac_address=(?)', ([device]))
        devtype = curs.fetchone()
        if devtype[0] == 4:
            print("Feeder")
            if value[15] == 0x02: #Provisioned Chip on feeder
                tag = feederhextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    frameresponse["Animal"]=petval[0]
                else:
                    frameresponse["Animal"]=tag
                frameresponse["OP"]="Chip"
                frameresponse["ChipState"]=ProvChipState(value[17]).name
                frameresponse["MSG"]=tohex(value)
            if value[15] == 0x06: #Un-provisioned Chip on feeder
                frameresponse["OP"]="Chip"
                frameresponse["ChipState"]="Empty"
                frameresponse["MSG"]=tohex(value)
            else:
                frameresponse["OP"]="Unknown"
                frameresponse["MSG"]=tohex(value)
        if devtype[0] == 6:
            print("Cat Flap")
            print(tohex(value))
            print("14: ",value[14], " 15 ", value[15], " 16 ", value[16])
            if value[14] == 0x07: #Set Cat Flap Lock State
                frameresponse["OP"]="LockState"
                frameresponse['Lock']=CatFlapLockState(int(value[15])).name
                frameresponse["MSG"]=tohex(value)
            else:
                frameresponse["OP"]="Unknown"
                frameresponse["MSG"]=tohex(value)
    elif value[0] == 0x13: #Pet Movement through cat door
        tag = feederhextochip(tohex(value[18:25]))
        curs.execute('select name from pets where tag=(?)', ([tag]))
        petval = curs.fetchone()
        if (petval):
            frameresponse["Animal"]=petval[0]
        else:
            frameresponse["Animal"]=tag
        AnimalDirection=(value[16] << 8) + value[17]
        print(AnimalDirection)
        frameresponse["Direction"]=CatFlapDirection(AnimalDirection).name
        if frameresponse["Direction"] != "Status":
            frameresponse["OP"]="PetMovement"
        else:
            frameresponse["OP"]="PetMovementStatus"
        frameresponse["MSG"]=tohex(value)
    elif value[0] == 0x18:
        frameresponse["OP"]="Feed"
        #Hard code feeder states
        if FeederState.has_value(value[15]):
            if value[15] in range(4, 8):
                tag="Manual"
                frameresponse["Animal"]="Manual"
            else:
                tag = feederhextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    frameresponse["Animal"]=petval[0]
                else:
                    frameresponse["Animal"]=tag
            action=FeederState(int(value[15])).name
            feederopenseconds=b2iu(value[16:17])
            scaleleftfrom=b2ih(value[19:23])
            scaleleftto=b2ih(value[23:27])
            scalerightfrom=b2ih(value[27:31])
            scalerightto=b2ih(value[31:35])
            frameresponse["FA"]=action
            frameresponse["FOS"]=feederopenseconds
            frameresponse["SLF"]=scaleleftfrom #Or if single bowl
            frameresponse["SLT"]=scaleleftto
            frameresponse["SRF"]=scalerightfrom
            frameresponse["SRT"]=scalerightto
            #Return bowl count
            curs.execute('select bowltype from feeders where mac_address=(?)', ([device]))
            bowlval = curs.fetchone()
            if (bowlval):
                frameresponse["BC"]=bowlval[0]
            else:
                frameresponse["BC"]=1
            #response.append(frameresponse)
            if Print126Frame:
                print("FF-18: Feeder door change - chip="+tag+",action="+action+',feederopenseconds='+ b2iu(value[16:17])+',scaleleftfrom='+b2ih(value[19:23])+',scaleleftto='+b2ih(value[23:27])+',scalerightfrom='+b2ih(value[27:31])+',scalerightto='+b2ih(value[31:35]))
        else:
            frameresponse["OP"]="Unknown"
            frameresponse["MSG"]=tohex(value)
    else:
        frameresponse["OP"]="Unknown"
        frameresponse["MSG"]=tohex(value)
    return frameresponse

#Parse Hub Frames aka 132's sent to the pet door
def parsehubframe(operation,device,offset,value):
    response = []
    operation = []
    msgval = {}
    message=bytearray.fromhex(value)
    print("Hub Frame",message)
    if PrintFrameDbg:
        print("Operation: " + operation + " device " + device + " offset " + str(offset) + " -value- " + value)
    logmsg=""
    if message[0] >= 4: #This is a register dump message
        print("Insert into db")
        curs.execute("INSERT OR REPLACE INTO devicestate values((?), (?), (?), (?));", (device, offset, message[0], value[2:]))
        conn.commit()
    if offset == 33: #Battery and 
        #print("Value",message[1])
        op="BatteryandTime"
        msgval['OP']=op
        operation.append(op)
        msgval['Battery']=hb(message[1])
        msgval['Time']=converttime(message[2:4])
        response.append(msgval)
    elif offset == 34: #Set local time for Pet Door 34 = HH in hex and 35 = MM
        op="SetTime"
        msgval['OP']=op
        operation.append(op)
        msgval['Time']=converttime(message[1:3])
        response.append(msgval)
        #logmsg += device + " " + operation + "-Time    : "+ int(message[1]) +":"+ int(message[2])
        #if int(message[0]) > 2:
        #    logmsg += "Addional bytes:"+tohex(message[3:])
    elif offset == 36: #Lock state
        op="LockState"
        msgval['OP']=op
        operation.append(op)
        msgval['Lock']=LockState(int(message[1])).name
        #msgval['Lock']=message[1]
        response.append(msgval)
        #logmsg += device + " " + operation + "-Lockstate       : "+ pDLockState[int(message[1])]
        #if int(message[0]) > 1:
        #    logmsg += "Addional bytes:"+tohex(message[2:])
    else:
        op="Other"
        msgval['OP']=op
        operation.append(op)
        msgval['MSG']=value
        #print("Other ", value)
        #logmsg += device + " " + operation + "-Other offset    : " + value
        #print("other offset" + logmsg)
    response.append({"OP":operation})
    return response

def converttime(timearray):
    return ':'.join(format(x, '02d') for x in timearray)

#Parse Pet Door Frames aka 132's sent to the pet door
def parsedoorframe(operation,device,offset,value):
    response = []
    operation = []
    msgval = {}
    message=bytearray.fromhex(value)
    if PrintFrameDbg:
        print("Operation: " + operation + " device " + device + " offset " + str(offset) + " -value- " + value)
    logmsg=""
    if offset == 33: #Battery and 
        #print("Value",message[1])
        op="BatteryandTime"
        msgval['OP']=op
        operation.append(op)
        msgval['Battery']=hb(message[1])
        msgval['Time']=converttime(message[2:4])
    elif offset == 34: #Set local time for Pet Door 34 = HH in hex and 35 = MM
        op="SetTime"
        msgval['OP']=op
        operation.append(op)
        msgval['Time']=converttime(message[1:3])
        #logmsg += device + " " + operation + "-Time    : "+ int(message[1]) +":"+ int(message[2])
        #if int(message[0]) > 2:
        #    logmsg += "Addional bytes:"+tohex(message[3:])
    elif offset == 36: #Lock state
        op="LockState"
        msgval['OP']=op
        operation.append(op)
        msgval['Lock']=LockState(int(message[1])).name
        #logmsg += device + " " + operation + "-Lockstate       : "+ pDLockState[int(message[1])]
        #if int(message[0]) > 1:
        #    logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset == 40: #Keep pets out allow incoming state
        op="LockedOutState"
        msgval['OP']=op
        operation.append(op)
        msgval['LockedOut']=LockedOutState(int(message[1])).name
        #logmsg += device + " " + operation + "-Keep pets out   : "+pDKeepPetsOutState[int(message[1])]
        #if int(message[0]) > 1:
        #    logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset == 59: #Provisioned Chip Count
        op="PrivChipCount"
        msgval['OP']=op
        operation.append(op)
        msgval['ChipCount']=message[1]
        #logmsg += device + " " + operation + "-Prov Chip #     : "+(message[1])
        #if int(message[0]) > 1:
        #   logmsg += "Addional bytes:"+tohex(message[2:])
    elif offset >= 91 and offset <= 308: #Provisioned chips
        op="ProvChip"
        msgval['OP']=op
        operation.append(op)
        pet=round((int(offset)-84)/7) #Calculate the pet number
        chip=doorhextochip(value[4:]) #Calculate chip Number
        msgval['PetOffset']=pet
        msgval['Chip']=chip
        #logmsg += device + " " + operation + "-Prov Chip ID   "+ str(pet) + " : Chip number " + chip
    elif offset == 519: #Curfew
        op="Curfew"
        msgval['OP']=op
        operation.append(op)
        msgval['CurfewState']=CurfewState(message[1]).name
        msgval['CurfewOn']=str(message[2]).zfill(2)+":"+str(message[3]).zfill(2)
        msgval['CurfewOff']=str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        #logmsg += device + " " + operation + "-Curfew          : "+pDCurfewState[message[1]] + " Lock: "+str(message[2]).zfill(2)+":"+str(message[3]).zfill(2) + " Unlock: "+str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
    elif offset >= 525 and offset <= 618: #Pet movement state in or out
        op="PetMovement"
        msgval['OP']=op
        operation.append(op)
        pet=round((int(offset)-522)/3)-1 #Calculate the pet number
        if PetDoorDirection.has_value(message[3]):
            direction = PetDoorDirection(message[3]).name
        else:
            direction = "Other " + hb(message[3])
        msgval['PetOffset']=pet
        msgval['Animal']=petnamebydevice(device, pet)
        msgval['Direction']=direction
        operation.append("PetMovement")
    elif offset == 621: #Unknown pet went outside
        op="PetMovement"
        msgval['OP']=op
        operation.append(op)
        msgval['PetOffset']="621"
        msgval['Animal']="Unknown Pet"
        msgval['Direction']="Outside"
        msgval['State']="OFF"
#        logmsg += device + " " + operation + "-Pet Movement    : Unknown pet went outside " + value
    else:
        op="Other"
        msgval['OP']=op
        operation.append(op)
        msgval['MSG']=value
        #print("Other ", value)
        #logmsg += device + " " + operation + "-Other offset    : " + value
        #print("other offset" + logmsg)
    response.append(msgval)
    response.append({"OP":operation})
    return response

def inithubmqtt():
    response = dict();
    #Devices
    curs.execute('select name,product_id,devices.mac_address,led_mode,pairing_mode,curfewenabled,lock_time,unlock_time,lockingmode,bowltarget1,bowltarget2,bowltype,close_delay from devices left outer join hubs on devices.mac_address=hubs.mac_address left outer join doors on devices.mac_address=doors.mac_address left outer join feeders on devices.mac_address=feeders.mac_address;')
    devices = curs.fetchall()
    if devices:
        response['devices'] = devices
    curs.execute('select pets.name as name,species,devices.name as device,product_id,state from pets left outer join petstate on pets.tag=petstate.tag left outer join devices on petstate.mac_address=devices.mac_address;')
    pets = curs.fetchall()
    if pets:
        response['pets'] = pets
    return response

def decodehubmqtt(topic,message):
    response = dict();
    msgsplit=message.split()
    topicsplit=topic.split('/')
    device=topicsplit[-1:][0]

    #Decode device name
    if device=="messages":
        response['device'] = "hub"
        timestampstr = str(datetime.utcfromtimestamp(int(ts,16)))
    else:
        curs.execute('select name from devices where mac_address=(?)', ([device]))
        devicename = curs.fetchone()
        if devicename:
            response['device'] = str(devicename[0])
        else:
            response['device'] = str(device)
        timestampstr = str(datetime.utcfromtimestamp(int(msgsplit[0],16)))
    response['message'] = msgsplit
    response['timestamp']=timestampstr

    #Timestamp calculations

    if msgsplit[1] == "1000":
        operation = "Command"
    else:
        operation = "Status"
    response['operation'] = operation

    resp = []
    #Device message
    if msgsplit[0] == "Hub": #Hub Offline Last Will message
        resp.append({"Msg":message})
        resp.append({"OP":["Boot"]})
        response['message'] = resp
    elif msgsplit[2] == "Hub": #Hub online / boot message
        resp.append({"Msg":" ".join(msgsplit[2:])})
        resp.append({"OP":["Boot"]})
        response['message'] = resp
    elif msgsplit[2] == "10": #Hub Uptime
        msgval = {}
        msgval['Uptime']=str(int(msgsplit[3]))
        msgval['TS']=msgsplit[4]+"-"+':'.join(format(int(x,16), '02d') for x in msgsplit[5:8])
        msgval['Reconnect']=msgsplit[9]
        resp.append({"Msg":msgval})
        resp.append({"OP":["Uptime"]})
        response['message'] = resp
    elif msgsplit[2] == "127": #Feeder frame sent/control message
        #ba = bytearray([0x7F])
        singleframe = bytearray.fromhex("".join(msgsplit[3:]))
        singleresponse = []
        singleframeresponse = parseframe(device, singleframe)
        singleresponse.append(singleframeresponse)
        #Append the operation to a separate array we attach at the end.
        op=singleframeresponse['OP']
        singleresponse.append({"OP":[op]})
        response['message'] = singleresponse
    elif msgsplit[2] == "126": #Feeder frame status message
        #ba = bytearray([0x7E])
        #print("message 127")
        multiframe = bytearray.fromhex("".join(msgsplit[3:]))
        response['message'] = parsemultiframe(device,multiframe)
        #print(response['message'])
    elif msgsplit[2] == "132" and device != "messages" : #Pet Door Status
        #Status message has a counter at offset 4 we can ignore:
        if Print132Frame:
            print("132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        #print("Message :", "".join(msgsplit[5:]))
        response['message'] = parsedoorframe(operation,device, int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "132" and device == "messages": #Hub Frame
        #Status message has a counter at offset 4 we can ignore:
        if Print132Frame:
            print("132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        #print("Message :", "".join(msgsplit[5:]))
        response['message'] = parsehubframe(operation,device, int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "2" and device != "messages" : #Action message setting value to Pet Door
        #Action message doesn't have a counter
        if Print2Frame:
            print("2 Message : "+message)
        msgsplit[4] = hb(int(msgsplit[4])) #Convert length at offset 4 which is decimal into hex byte so we pass it as a hex string to parsedoorframe
        response['message'] = parsedoorframe(operation,device, int(msgsplit[3]),"".join(msgsplit[4:]))
    elif msgsplit[2] == "8": #Action message setting value to Pet Door
        resp.append({"Msg":message})
        resp.append({"OP":["8"]})
        response['message'] = resp
    elif msgsplit[2] == "3": # Boot message - dump memory
        resp.append({"Msg":"Dump to " + msgsplit[4]})
        resp.append({"OP":["Dump"]})
        response['message'] = resp
    else:
        resp.append({"Msg":message})
        resp.append({"OP":["ERROR"]})
        response['message'] = resp
    return response

def decodemiwi(timestamp,source,destination,framestr):
    framexor=bytearray.fromhex(framestr)
    #Convert MAC addresses into reverse byte format.
    sourcemac=''.join(list(reversed(source.split(":")))).upper()
    destinationmac=''.join(list(reversed(destination.split(":")))).upper()

    timesplit=timestamp.split(".")
    hextimestamp = hex(round(int(timesplit[0])))[2:]
    #print("Time " + hextimestamp)

    #Dexor the frame
    frame = list(map(xor, framexor, xorkey))

    if PrintFrame:
        print("Received frame at: " + hextimestamp + " from: " + sourcemac + " to: " + destinationmac)
        print("Packet:" + tohex(framexor))
        print("Dexor :" + tohex(frame))
    if len(frame) > 8:
        response = []
        if PrintFrameDbg:
            print("Frame Type       :", hb(frame[2]))
            print("Frame Length     :", len(frame))
            print("Frame Length Val :", frame[4])
        payload=frame[6:frame[4]+1]
        logmsg=""
        if frame[2] == 0x2a: #126 Message Feeder to Hub Message which will be a multiframe
            if Print126Frame:
                print("FF-2A Request : " + sourcemac + " " + tohex(payload))
            response=parsemultiframe(sourcemac,payload)
            if len(response) > 0 and Print127Frame:
                print("FF-2A Response: ", response)
        elif frame[2] == 0x2d: #127 Message Hub to Feeder or Cat Door control message which will be a single frame
            if Print127Frame:
                print("FF-2D Request : " + sourcemac + " " + tohex(payload))
            singleframeresponse = parseframe(sourcemac, payload)
            response.append(singleframeresponse)
            op=singleframeresponse['OP']
            response.append({"OP":[op]})
            if len(response) > 0 and Print127Frame:
                print("FF-2D Response: ", response)
        elif frame[2] == 0x3c: #Pet door frame
            if Print132Frame:
                print("DF-132 Request: " + tohex(payload))
            #print(parsedoorframe('Status',sourcemac,int(b2ibs(payload[0:2])),tohex(payload[2:-1])))
        return response
    else:
        logmsg = "Corrupt Frame " + tohex(frame)
    return "Received frame at: " + timestamp + " from: " + sourcemac + " to: " + destinationmac + " " + logmsg

def buildmqttsendmessage(value):
#  ts = str(binascii.hexlify(struct.pack('>I', round(datetime.utcnow().timestamp()))),'ascii')
  return ts + " 1000 " + value

#Generate message
def generatemessage(devicetype,device,operation,state):
    if devicetype=="hub":
        if operation == "dumpstate":      #Dump all memory registers from 0 to 205
            msgstr = "3 0 205"
        elif operation == "flashleds":    #Flash the ears 3 times
            msgstr = "2 18 1 80"
        elif operation == "flashleds2":   #Flash the ears 2 times
            msgstr = "2 18 1 81"
        elif operation == "earsoff":      #Turn ear lights off
            msgstr = "2 18 1 04"
        elif operation == "earsdimmed":   #Ears dimmed
            msgstr = "2 18 1 00"
        elif operation == "earsbright":   #Ears bright
            msgstr = "2 18 1 01"
        elif operation == "adoptdisable": #Disable adoption mode
            msgstr = "2 15 1 02"
        elif operation == "adoptdisable": #Enable adoption mode to adopt devices.
            msgstr = "2 15 1 00"
        return buildmqttsendmessage(msgstr)

    elif devicetype=="petdoor":
        if operation == "dumpstate": #Dump all memory registers from 0 to 630
            msgstr = "3 0 630"
        if operation == "setlockstateunlocked": #Lock state - unlocked
            msgstr = "2 36 1 00"
        if operation == "setlockstatein":       #Lock state - keep pets in
            msgstr = "2 36 1 01"
        if operation == "setlockstateout":      #Lock state - keep pets out
            msgstr = "2 36 1 02"
        if operation == "setlockstateboth":     #Lock state - lock both ways
            msgstr = "2 36 1 03"
        if operation == "setlockstate39":       #Lock state offset 39, was only set on first lock, probably not needed
            msgstr = "2 39 1 01"
        if operation == "setcurfew": #Curfew, EE = Enable State, FF = From HH:MM, TT = To HH:MM
            msgstr = "2 519 6 EE FF FF TT TT 00"
        if operation == "inbound" or operation == "outbound":
            curs.execute('select mac_address, lockingmode from devices join doors using (mac_address) where name like (?)', ([device]))
            lockingmode = curs.fetchone()
            #print("Current locking mode: " + lockingmode[0])
            if (operation == "outbound" and state == "OFF" and lockingmode[1] == 1) or (operation == "inbound" and state == "OFF" and lockingmode[1] == 2):
                #Going to Lock State 0 - Unlocked
                msgstr = "2 36 1 00"
            elif (operation == "outbound" and state == "ON" and lockingmode[1] == 0) or (operation == "inbound" and state == "OFF" and lockingmode[1] == 3):
                #Going to Lock State 1 - Keep pets in
                msgstr = "2 36 1 01"
            elif (operation == "outbound" and state == "OFF" and lockingmode[1] == 3) or (operation == "inbound" and state == "ON" and lockingmode[1] == 0):
                #Going to Lock State 2 - Keep pets out
                msgstr = "2 36 1 02"
            elif (operation == "outbound" and state == "ON" and lockingmode[1] == 2) or (operation == "inbound" and state == "ON" and lockingmode[1] == 1):
                #Going to Lock State 3 - Lock both ways
                msgstr = "2 36 1 03"
            else:
                msgstr = "2 36 1 00"
            return {"topic":"pethublocal/messages/"+lockingmode[0], "msg":buildmqttsendmessage(msgstr)}
        return buildmqttsendmessage(msgstr)

    elif devicetype=="feeder": #Message 127 to the feeder or cat door
        curs.execute('select mac_address, lockingmode from devices join doors using (mac_address) where name like (?)', ([device]))
        macaddy = curs.fetchone()
        if operation == "ackfeederstatedoor":
        #Acknowledge the 18 door state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 18 00 00"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
        elif operation == "ackfeederstate16":
            #Acknowledge the 16 state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 16 00 00"
            return msgstr
        elif operation == "ackfeederstate09":
            #Acknowledge the 09 settings update state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 09 00 00"
            return msgstr
        elif operation == "getcurrentstate0b":
        #Request boot message state 0b
            msgstr = "01 00 ZZ 00 TT TT TT TT 0b 00"
            return msgstr
        elif operation == "getbootstate0c":
            #Request boot message state 0c
            msgstr = "01 00 ZZ 00 TT TT TT TT 0c 00"
            return msgstr
        elif operation == "getbootstate10":
        #Request boot message state 10
            msgstr = "01 00 ZZ 00 TT TT TT TT 10 00"
            return msgstr
        elif operation == "getprovisionedchipsstate":
            #This tells the feeder to dump all provisioned chips
            msgstr = "01 00 ZZ 00 TT TT TT TT 11 00 ff"
            return msgstr
        elif operation == "getbootstate17":
            #Request boot message state 17
            msgstr = "01 00 ZZ 00 TT TT TT TT 17 00 00"
            return msgstr
        elif operation == "lidclosedelayfast":
            #Update lid close delay to fast = 0
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d 00 00 00 00"
            return msgstr
        elif operation == "lidclosedelaynormal":
            #Update lid close delay to normal = 4000 (0fa0) - 4 seconds(?)
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d a0 0f 00 00"
            return msgstr
        elif operation == "lidclosedelayslow":
            #Update lid close delay to slow = 20000 (4e20) - 20 seconds(?)
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d 20 4e 00 00"
            return msgstr
        elif operation == "setleftscaleweight":
            #Set left or single bowl scale weight
            msgstr = "09 00 ZZ 00 TT TT TT TT 0a WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
            return msgstr
        elif operation == "setrightscaleweight":
            #Set right scale weight
            msgstr = "09 00 ZZ 00 TT TT TT TT 0b WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
            return msgstr
        elif operation == "setbowlcount":
            #Set bowl count either 01 for one bowl or 02 for two.
            msgstr = "09 00 ZZ 00 TT TT TT TT 0c WW 00 00 00"
            msgstr = msgstr.replace("WW", format(opval,'02x'))
            return msgstr
        elif operation == "set12message":
            #Not sure what caused this but it happened around setting the scales - 12f4010000
            msgstr = "09 00 ZZ 00 TT TT TT TT 12 WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
            return msgstr
        elif operation == "zeroleftscale":
            #Zero the left scale, first need to check feeder is open via Message 18 state 
            msgstr = "0d 00 ZZ 00 TT TT TT TT 00 19 00 00 00 03 00 00 00 00 01 01"
            return msgstr
        elif operation == "zerorightscale":
            #Zero the right scale, first need to check feeder is open via Message 18 state 
            msgstr = "0d 00 ZZ 00 TT TT TT TT 00 19 00 00 00 03 00 00 00 00 01 02"
            return msgstr
        elif operation == "zerobothscales":
            #Zero the both scales, first need to check feeder is open via Message 18 state 
            msgstr = "0d 00 ZZ 00 TT TT TT TT 00 19 00 00 00 03 00 00 00 00 01 03"
            return msgstr
        elif operation == "chipprovision":
            #Provision chip, CCCCCCCCCCCCCC is the chip in hex format using feederhextochip and SS is state 00 = disabled, 01 = enabled.
            msgstr = "11 00 ZZ 00 TT TT TT TT CC CC CC CC CC CC CC 02 00 SS"
        else:
            print("Unknown message")

        hubts = feedertimestampfromnow()
        devcounter = devicecounter(macaddy[0],"-1","-2") #Iterate the send counter for the device
        msgstr = msgstr.replace('ZZ', hb(devcounter['send'])) # Replace device counter in the record
        msgstr = msgstr.replace('TT TT TT TT', " ".join(hubts[i:i+2] for i in range(0, len(hubts), 2))) # Timestamp
        return {"topic":"pethublocal/messages/"+macaddy[0], "msg":buildmqttsendmessage("127 "+msgstr)} #Need to prefix the message with "127 "
        return msgstr

    elif devicetype=="catflap":
        if operation == "dumpstate": #Dump all memory registers from 0 to 630
            msgstr = "TBC"
        if operation == "inbound" or operation == "outbound":
            curs.execute('select mac_address, lockingmode from devices join doors using (mac_address) where name like (?)', ([device]))
            lockingmode = curs.fetchone()
            #print("Current locking mode: " + lockingmode[0])
            if (operation == "outbound" and state == "OFF" and lockingmode[1] == 1) or (operation == "inbound" and state == "OFF" and lockingmode[1] == 2):
                #Going to Lock State 0 - Unlocked
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 06 00 02"
            elif (operation == "outbound" and state == "ON" and lockingmode[1] == 0) or (operation == "inbound" and state == "OFF" and lockingmode[1] == 3):
                #Going to Lock State 1 - Keep pets in
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 03 00 02"
            elif (operation == "outbound" and state == "OFF" and lockingmode[1] == 3) or (operation == "inbound" and state == "ON" and lockingmode[1] == 0):
                #Going to Lock State 2 - Keep pets out
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 05 00 02"
            elif (operation == "outbound" and state == "ON" and lockingmode[1] == 2) or (operation == "inbound" and state == "ON" and lockingmode[1] == 1):
                #Going to Lock State 3 - Lock both ways
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 04 00 02"
            else:
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 06 00 02"
            hubts = feedertimestampfromnow()
            devcounter = devicecounter(lockingmode[0],"-1","-2") #Iterate the send counter for the device
            msgstr = msgstr.replace('ZZ', hb(devcounter['send'])) # Replace device counter in the record
            msgstr = msgstr.replace('TT TT TT TT', " ".join(hubts[i:i+2] for i in range(0, len(hubts), 2))) # Timestamp
            return {"topic":"pethublocal/messages/"+lockingmode[0], "msg":buildmqttsendmessage("127 "+msgstr)} #Need to prefix the message with "127 "
        return buildmqttsendmessage(msgstr)

    else:
        print("Unknown type")

#Update Device Counter
def devicecounter(mac_address,send,retrieve):
    #If the send or retrieve counters are -1 we take the current value and iterate it and -2 return the current value
    curs.execute('select send,retrieve from devicecounter where mac_address=(?)', ([mac_address]))
    devcount = curs.fetchone()
    devc = {"send":-3, "retrieve":-3}
    if send == "-2":
        devc['send'] = devcount[0]
    if send == "-1":
        devc['send'] = devcount[0]+1
    if send >= "0":
        devc['send'] = send
    if retrieve == "-2":
        devc['retrieve'] = devcount[1]
    if retrieve == "-1":
        devc['retrieve'] = devcount[1]+1
    if retrieve >= "0":
        devc['retrieve'] = retrieve
    cur = conn.cursor()
    upd = 'UPDATE devicecounter SET send=' + str(devc['send']) + ', retrieve=' + str(devc['retrieve']) + ' WHERE mac_address = "' + mac_address + '"'
    cur.execute(upd)
    conn.commit()
    return devc

def updatedb(tab,dev,col,val):
    cur = conn.cursor()
    upd = 'UPDATE '+ tab + ' SET ' + col + ' = "' + str(LockState[val].value) + '" WHERE mac_address = "' + dev + '"'
    #print(upd)
    cur.execute(upd)
    #cur.execute('UPDATE doors SET ? = ? WHERE mac_address = ?', (col,val,dev))
    conn.commit()