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

import binascii, struct, time, sys, sqlite3, json, glob, logging

from datetime import datetime
from operator import xor
from pathlib import Path
from enum import IntEnum
from datetime import date, timedelta
from pethubconst import *
from box import Box

#Debugging mesages
PrintFrame = False       #Print the before and after xor frame
LogFrame = False         #Log the frames to a file
LogAirFrame = False      #Log the frame sent over the air as a hub mqtt packet to a file
PrintFrameDbg = False    #Print the frame headers
Print126Frame = False    #Debug the 2A / 126 feeder frame
Print127Frame = False    #Debug the 2D / 127 feeder frame
Print132Frame = False    #Debug the 3C / 132 hub and door frame
PrintHubFrame = False    #Debug the Hub frame
PrintFeederFrame = False #Debug the Hub frame
Print2Frame = False      #Debug the 2 frame
PrintDebug = False       #Debug the 2 frame

#Import xor key from pethubpacket.xorkey and make sure it is sane.
for file in glob.glob("pethubpacket.xorkey"):
    xorfile=Path(file).read_text()
    if len(xorfile) > 20 and len(xorfile) % 2 == 0:
        xorkey=bytearray.fromhex(xorfile)
    else:
        sys.exit("Corrupted pethubpacket.xorkey file, make sure the length is an even set of bytes")

#Load PetHubLocal database
def dict_factory(cursor, row): #Return results as a dict key value pair
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return Box(d)

#for sqlitefile in glob.glob("pethublocal.db"):
#    conn=sqlite3.connect(sqlitefile)
conn=sqlite3.connect("pethublocal.db")
conn.row_factory = dict_factory
curs=conn.cursor()
#conn.row_factory = sqlite3.Row

#Create hex timestamp
ts = hex(round(datetime.utcnow().timestamp()))[2:]

def sqlcmd(sql_cmd):
    try:
        curs.execute(sql_cmd)
        conn.commit()
    except Error as e:
        print(e)

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

def converttime(timearray):
    return ':'.join(format(x, '02d') for x in timearray)

def converttimetohex(timestring): #For curfew time
    time=timestring.split(':')
    return hb(int(time[0]))+" "+hb(int(time[1]))
    
def petnamebydevice(mac_address, deviceindex):
    curs.execute('select tag from tagmap where mac_address=(?) and deviceindex=(?)', (mac_address, deviceindex))
    tagval = curs.fetchone()
    if (tagval):
        curs.execute('select name from pets where tag=(?)', ([tagval.tag]))
        petval = curs.fetchone()
        if (petval):
            petname=petval.name
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
        op=frameresponse.OP
        operation.append(op)
        #Remove the parsed payload and loop again
        del payload[0:subframelength]
    response.append({"OP":operation})
    return response

#Parse Feeder, Cat Flap and Felaqua Data Frame or Multi-Frame
#127 Frame aka 0x7F (127) or 0x2D (Wire value with TBC XOR) are a single payload vs 126 need parsemultiframe as they have multiple messages in a single frame
def parseframe(device, value):
    frameresponse = Box()
    msg = ""

    #Frame timestamp value
    frameresponse.framets = feedertimestamptostring(bltoi(value[4:8]))
    #The message type and counter are needed for acking back
    frameresponse.data=Box({'msg':hb(value[0]),'counter':hb(value[2])})
#    frameresponse.msgdata=hb(value[0])+" "+hb(value[2])

    if value[0] in [0x07, 0x0b, 0x10, 0x16]: #Unknown messages
        op=hb(value[0])
        frameresponse.OP="Msg"+op
        frameresponse.MSG=tohex(value[3:])
        if Print126Frame:
            print("FF-"+op+": **TODO** Msg " + tohex(value[3:]))
    elif value[0] == 0x00: #Send Acknowledge for message type
        frameresponse.OP="Ack"
        frameresponse.MSG=hb(value[8])
        if Print126Frame:
            print("FF-00:ACK-" + hb(value[8]))
    elif value[0] == 0x01: #Send query for data type
        frameresponse.OP="Query"
        frameresponse.MSG=hb(value[8])
        if Print126Frame:
            print("FF-01:QRY-" + hb(value[8]))
    elif value[0] == 0x09: #Update state messages with subtypes depending on device type
        if value[3] == 0x06: #Status message on each provisioned chip seen on the Felaqua
            frameresponse.OP="ChipStatus"
            frameresponse.ChipOffset=hb(value[8])
            frameresponse.MSG=tohex(value[9:])
        else:
            frameresponse.OP="UpdateState"
            submessagevalue = b2is(value[9:12])
            if value[8]==0x05: # Training mode
                msg = {"MSG":"FF-09:TRN-" + submessagevalue} #Training Mode
                frameresponse.SUBOP="Training"
                frameresponse.MODE=submessagevalue
            elif value[8]==0x0a: #Set Left Weight
                msg += "FF-09:SLW-" + submessagevalue
                frameresponse.SUBOP="SetLeftWeight"
                frameresponse.WEIGHT=submessagevalue
            elif value[8]==0x0b:
                msg += "SetRightWeight=" + submessagevalue
                frameresponse.SUBOP="SetRightWeight"
                frameresponse.WEIGHT=submessagevalue
            elif value[8]==0x0c:
                msg += "FF-09:SBC-" + FeederBowls(int(submessagevalue)).name
                frameresponse.SUBOP="SetBowls"
                frameresponse.BOWLS=FeederBowls(int(submessagevalue)).name
            elif value[8]==0x0d:
                msg += "FF-09:CLD-" + FeederCloseDelay(int(submessagevalue)).name
                frameresponse.SUBOP="SetCloseDelay"
                frameresponse.DELAY=FeederCloseDelay(int(submessagevalue)).name
            elif value[8]==0x12:
                msg += "FF-09:?12=" + tohex(value[9:12])
                frameresponse.SUBOP="SetTODO"
                frameresponse.MSG=tohex(value[9:12])
            elif value[8]==0x17:
                msg += "ZeroLeftWeight=" + submessagevalue
                frameresponse.SUBOP="ZeroLeftWeight"
                frameresponse.WEIGHT=submessagevalue
            elif value[8]==0x18:
                msg += "ZeroRightWeight=" + submessagevalue
                frameresponse.SUBOP="ZeroRigtWeight"
                frameresponse.WEIGHT=submessagevalue
            elif value[8]==0x19:
                msg += "FF-09:?19=" + tohex(value[9:12])
                frameresponse.SUBOP="SetTODO"
                frameresponse.MSG=tohex(value[9:12])
            else:
                msg += "FF-09:???=" + tohex(value[9:12])
                frameresponse.SUBOP="SetTODO"
                frameresponse.MSG=tohex(value[9:12])
            if Print126Frame:
                print(msg)
    elif value[0] == 0x0c: #Battery state for two bytes
        frameresponse.OP="Battery"
        battery = str(int(b2is(value[8:10]))/1000)
        frameresponse.Battery=battery
        upd = "UPDATE devices SET battery=" + battery + ' WHERE mac_address = "' + device + '"'
        curs.execute(upd)
        conn.commit()
    elif value[0] == 0x11: #Provision chip to device and set lock states on cat flap.
        curs.execute('select product_id from devices where mac_address=(?)', ([device]))
        devtype = curs.fetchone()
        if devtype.product_id == 4:
            print("Feeder")
            if value[15] == 0x02: #Provisioned Chip on feeder
                tag = feederhextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    frameresponse.Animal=petval.name
                else:
                    frameresponse.Animal=tag
                frameresponse.OP="Chip"
                frameresponse.ChipState=ProvChipState(value[17]).name
                frameresponse.MSG=tohex(value)
            if value[15] == 0x06: #Un-provisioned Chip on feeder
                frameresponse.OP="Chip"
                frameresponse.ChipState="Empty"
                frameresponse.MSG=tohex(value)
            else:
                frameresponse.OP="Unknown"
                frameresponse.MSG=tohex(value)
        if devtype.product_id == 6:
            print("Cat Flap")
            print(tohex(value))
            print("14: ",value[14], " 15 ", value[15], " 16 ", value[16])
            if value[14] == 0x07: #Set Cat Flap Lock State
                frameresponse.OP="LockState"
                frameresponse.Lock=CatFlapLockState(int(value[15])).name
                frameresponse.MSG=tohex(value)
            else:
                frameresponse.OP="Unknown"
                frameresponse.MSG=tohex(value)
    elif value[0] == 0x13: #Pet Movement through cat door
        tag = feederhextochip(tohex(value[18:25]))
        curs.execute('select name from pets where tag=(?)', ([tag]))
        petval = curs.fetchone()
        if (petval):
            frameresponse.Animal=petval.name
        else:
            frameresponse.Animal=tag
        AnimalDirection=(value[16] << 8) + value[17]
        print(AnimalDirection)
        if CatFlapDirection.has_value(AnimalDirection):
            frameresponse.Direction=CatFlapDirection(AnimalDirection).name
        else:
            frameresponse.Direction="**UNKNOWN**"
        if frameresponse.Direction != "Status":
            frameresponse.OP="PetMovement"
        else:
            frameresponse.OP="PetMovementStatus"
        frameresponse.MSG=tohex(value)
    elif value[0] == 0x18:
        frameresponse.OP="Feed"
        #Hard code feeder states
        if FeederState.has_value(value[15]):
            if value[15] in range(4, 8):
                tag="Manual"
                frameresponse.Animal="Manual"
            else:
                tag = feederhextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    frameresponse.Animal=petval.name
                else:
                    frameresponse.Animal=tag
            action=FeederState(int(value[15])).name
            feederopenseconds=b2iu(value[16:17])
            scaleleftfrom=b2ih(value[19:23])
            scaleleftto=b2ih(value[23:27])
            scalerightfrom=b2ih(value[27:31])
            scalerightto=b2ih(value[31:35])
            frameresponse.FA=action
            frameresponse.FOS=feederopenseconds
            frameresponse.SLF=scaleleftfrom #Or if single bowl
            frameresponse.SLT=scaleleftto
            frameresponse.SRF=scalerightfrom
            frameresponse.SRT=scalerightto
            #Return bowl count
            curs.execute('select bowltype from feeders where mac_address=(?)', ([device]))
            bowlval = curs.fetchone()
            if (bowlval):
                frameresponse.BC=bowlval.bowltype
            else:
                frameresponse.BC=1
            #response.append(frameresponse)
            if Print126Frame:
                print("FF-18: Feeder door change - chip="+tag+",action="+action+',feederopenseconds='+ b2iu(value[16:17])+',scaleleftfrom='+b2ih(value[19:23])+',scaleleftto='+b2ih(value[23:27])+',scalerightfrom='+b2ih(value[27:31])+',scalerightto='+b2ih(value[31:35]))
        else:
            frameresponse.OP="Unknown"
            frameresponse.MSG=tohex(value)
    elif value[0] == 0x1B: #Felaqua Drinking frame, similar to a feeder frame but slightly different
        frameresponse.OP="Drinking"
        #Different operation values I assume
        drinkaction=hb(value[8])     #Action performed
        drinktime=b2iu(value[9:11])  #Time spent
        drinkfrom=b2ih(value[12:16]) #Weight From
        drinkto=b2ih(value[16:20])   #Weight To
        drinkdiff=str(float(drinkto)-float(drinkfrom))
        frameresponse.Action=drinkaction
        frameresponse.Time=drinktime
        frameresponse.WeightFrom=drinkfrom
        frameresponse.WeightTo=drinkto
        frameresponse.WeightDiff=drinkdiff
        frameresponse.MSG=tohex(value)
        #Update current bowl weight value in database
        upd = "UPDATE feeders SET bowl1=" + drinkdiff + ' WHERE mac_address = "' + device + '"'
        curs.execute(upd)
        conn.commit()
        if len(value) > 27:      #Includes the chip that performed the action
            tag = feederhextochip(tohex(value[27:34]))
            print("Hex tag",tohex(value[27:34]))
            curs.execute('select name from pets where tag=(?)', ([tag]))
            petval = curs.fetchone()
            if (petval):
                frameresponse.Animal=petval.name
            else:
                frameresponse.Animal=tag
        if Print126Frame:
            print("FF-1B: Felaqua action="+action+',seconds='+ drinktime+',drinkfrom='+drinkfrom+',drinkto='+drinkto)
    else:
        frameresponse.OP="Unknown"
        frameresponse.MSG=tohex(value)
    return frameresponse

#Parse Hub Frames aka 132's sent to the hub
def parsehubframe(mac_address,offset,value):
    response = []
    frameresponse = Box()
    message=bytearray.fromhex(value)
    if PrintHubFrame:
        print("Hub Frame: MAC Address: " + mac_address + " offset " + str(offset) + " -value- " + str(value))
    if offset == 15: #Adoption Mode
        opvalue = str(int(message[1]))
        operation="Adopt"
        frameresponse.OP=operation
        frameresponse[operation]=opvalue
        #sqlcmd('UPDATE hubs SET pairing_mode=' + opvalue + ' WHERE mac_address = "' + mac_address + '"')
    elif offset == 18: #LED Mode
        opvalue = str(int(message[1]))
        operation="LED"
        frameresponse.OP=operation
        frameresponse[operation]=opvalue
        sqlcmd('UPDATE hubs SET led_mode=' + opvalue + ' WHERE mac_address = "' + mac_address + '"')
    else:
        if message[0] >= 4: #This is a register dump message
            curs.execute("INSERT OR REPLACE INTO devicestate values((?), (?), (?), (?));", (mac_address, offset, message[0], value[2:]))
            conn.commit()
            operation="Boot"
        else:
            operation="Other"
        frameresponse.OP=operation
        frameresponse[operation]=operation
    response.append(frameresponse)
    response.append({"OP":operation})
    return response

def parsefeederframe(mac_address,offset,value):
    #The 132 Status messaes only have a 33 type for the time and battery, but both values are busted.
    response = []
    frameresponse = Box()
    message=bytearray.fromhex(value)
    if PrintFeederFrame:
        print("Hub Frame: MAC Address: " + mac_address + " offset " + str(offset) + " -value- " + str(value))
    if offset == 33: #Battery and Door Time
        operation="Feeder132Battery"
        frameresponse.OP=operation
        #Battery ADC Calculation, Battery full 0xbd, and dies at 0x61/0x5f.
        #ADC Start for Pet Door, not sure if this is consistent or just my door
        adcstart=2.1075
        #ADC Step value for each increment of the adc value 
        adcstep=0.0225
        battadc = (int(message[1])*adcstep)+adcstart
        frameresponse.Battery=str(battadc)
        frameresponse.Time=converttime(message[2:4])
    else:
        operation="Other"
        frameresponse.OP=operation
        frameresponse.MSG=tohex(value)
        frameresponse[operation]=operation
    response.append(frameresponse)
    response.append({"OP":[operation]})
    return response

#Parse Pet Door Frames aka 132's sent to the pet door
def parsedoorframe(mac_address,offset,value):
    response = []
    operation = []
    frameresponse = Box()
    message=bytearray.fromhex(value)
    if PrintFrameDbg:
        print("Operation: " + str(operation) + " mac_address " + str(mac_address) + " offset " + str(offset) + " -value- " + str(value))
    logmsg=""
    if offset == 33: #Battery and Door Time
        op="Battery"
        frameresponse.OP=op
        operation.append(op)
        #Battery ADC Calculation, Battery full 0xbd, and dies at 0x61/0x5f.
        #ADC Start for Pet Door, not sure if this is consistent or just my door
        adcstart=2.1075
        #ADC Step value for each increment of the adc value 
        adcstep=0.0225
        battadc = (int(message[1])*adcstep)+adcstart
        frameresponse.Battery=str(battadc)
        frameresponse.Time=converttime(message[2:4])
        sqlcmd('UPDATE devices SET battery=' + str(battadc) + ' WHERE mac_address = "' + mac_address + '"')
    elif offset == 34: #Set local time for Pet Door 34 = HH in hex and 35 = MM
        op="SetTime"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.Time=converttime(message[1:3])
    elif offset == 36: #Lock state
        op="LockState"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.Lock=LockState(int(message[1])).name
        sqlcmd('UPDATE doors SET lockingmode='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset == 40: #Keep pets out allow incoming state
        op="LockedOutState"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.LockedOut=LockedOutState(int(message[1])).name
    elif offset == 59: #Provisioned Chip Count
        op="PrivChipCount"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.ChipCount=message[1]
    elif offset >= 91 and offset <= 308: #Provisioned chips
        op="ProvChip"
        frameresponse.OP=op
        operation.append(op)
        pet=round((int(offset)-84)/7) #Calculate the pet number
        chip=doorhextochip(value[4:]) #Calculate chip Number
        frameresponse.PetOffset=pet
        frameresponse.Chip=chip
    elif offset == 519: #Curfew
        op="Curfew"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.CurfewState=CurfewState(message[1]).name
        frameresponse.CurfewOn=str(message[2]).zfill(2)+":"+str(message[3]).zfill(2)
        frameresponse.CurfewOff=str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        sqlcmd('UPDATE doors SET curfewenabled='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset >= 525 and offset <= 618: #Pet movement state in or out
        op="PetMovement"
        frameresponse.OP=op
        operation.append(op)
        pet=round((int(offset)-522)/3)-1 #Calculate the pet number
        if PetDoorDirection.has_value(message[3]):
            direction = PetDoorDirection(message[3]).name
        else:
            direction = "Other " + hb(message[3])
        frameresponse.PetOffset=pet
        frameresponse.Animal=petnamebydevice(mac_address, pet)
        frameresponse.Direction=direction
        operation.append("PetMovement")
    elif offset == 621: #Unknown pet went outside
        op="PetMovement"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.PetOffset="621"
        frameresponse.Animal="Unknown Pet"
        frameresponse.Direction="Outside"
        frameresponse.State="OFF"
    else:
        op="Other"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.MSG=value
    response.append(frameresponse)
    response.append({"OP":operation})
    return response

def inithubmqtt():
    response = Box();
    #Devices
    curs.execute('select name,product_id,devices.mac_address,serial_number,version,state,battery,led_mode,pairing_mode,curfewenabled,lock_time,unlock_time,lockingmode,bowl1,bowl2,bowltarget1,bowltarget2,bowltype,close_delay from devices left outer join hubs on devices.mac_address=hubs.mac_address left outer join doors on devices.mac_address=doors.mac_address left outer join feeders on devices.mac_address=feeders.mac_address;')
    devices = curs.fetchall()
    if devices:
        response.devices = devices
    #Pets
    curs.execute('select pets.name as name,species,devices.name as device,product_id,state from pets left outer join petstate on pets.tag=petstate.tag left outer join devices on petstate.mac_address=devices.mac_address;')
    pets = curs.fetchall()
    if pets:
        response.pets = pets
    return response

def decodehubmqtt(topic,message):
    response = Box();
    msgsplit=message.split()
    topicsplit=topic.split('/')
    mac_address=topicsplit[-1]

    #Decode device name
    if mac_address=="messages":
        curs.execute('select name,mac_address,product_id from devices where product_id=1')
        devicename = curs.fetchone()
        if devicename:
            response.device = str(devicename.name)
            response.mac_address = str(devicename.mac_address)
            mac_address = devicename.mac_address
        timestampstr = str(datetime.utcfromtimestamp(int(ts,16)))
    else:
        curs.execute('select name,mac_address,product_id from devices where mac_address=(?)', ([mac_address]))
        devicename = curs.fetchone()
        if devicename:
            response.device = str(devicename.name)
            response.mac_address = mac_address
        else:
            response.device = str(mac_address)
            response.mac_address = str(devicename.mac_address)
        timestampstr = str(datetime.utcfromtimestamp(int(msgsplit[0],16)))
    response.message = message
    response.timestamp=timestampstr

    #Determine operation
    if msgsplit[1] == "1000":
        operation = "Command"
    else:
        operation = "Status"
    response.operation = operation

    resp = []
    frameresponse = Box()
    #Device message
    if msgsplit[0] == "Hub": #Hub Offline Last Will message
        op="State"
        frameresponse.OP=op
        frameresponse.Msg=message
        frameresponse[op]='Offline'
        resp.append(frameresponse)
        resp.append({"OP":[op]})
        #Update state in database
        sqlcmd('UPDATE hubs SET state=0 WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "Hub": #Hub online message
        op="State"
        frameresponse.OP=op
        frameresponse.Msg=message
        frameresponse[op]='Online'
        resp.append(frameresponse)
        resp.append({"OP":[op]})
        #Update state in database
        sqlcmd('UPDATE hubs SET state=1 WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "10": #Hub Uptime
        op="Uptime"
        uptime = str(int(msgsplit[3]))
        frameresponse.OP=op
        frameresponse[op]=uptime
        frameresponse.TS=msgsplit[4]+"-"+':'.join(format(int(x), '02d') for x in msgsplit[5:8])
        frameresponse.Reconnect=msgsplit[9]
        resp.append(frameresponse)
        resp.append({"OP":[op]})
        #Update uptime in database
        sqlcmd('UPDATE hubs SET Uptime=' + uptime + ' WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "132" and EntityType(int(devicename.product_id)).name == "HUB": #Hub Frame
        if PrintHubFrame:
            print("Hub Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        response.message = parsehubframe(mac_address,int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "132" and EntityType(int(devicename.product_id)).name == "PETDOOR": #Pet Door Status
        #Status message has a counter at offset 4 we can ignore:
        if Print132Frame:
            print("132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        #print("Message :", "".join(msgsplit[5:]))
        response.message = parsedoorframe(mac_address, int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "132" and EntityType(int(devicename.product_id)).name == "FEEDER": #Feeder 132 Status
        #Status message has a counter at offset 4 we can ignore:
        if PrintFeederFrame:
            print("Feeder 132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        #print("Message :", "".join(msgsplit[5:]))
        response.message = parsefeederframe(mac_address, int(msgsplit[4]),"".join(msgsplit[5:]))
    elif msgsplit[2] == "127": #127 Feeder/CatDoor frame sent/control message
        singleframe = bytearray.fromhex("".join(msgsplit[3:]))
        singleresponse = []
        singleframeresponse = parseframe(mac_address, singleframe)
        singleresponse.append(singleframeresponse)
        op=singleframeresponse.OP
        singleresponse.append({"OP":[op]})
        response.message = singleresponse
    elif msgsplit[2] == "126": #126 Feeder/CatDoor multiframe status message
        multiframe = bytearray.fromhex("".join(msgsplit[3:]))
        response.message = parsemultiframe(mac_address,multiframe)
    elif msgsplit[2] == "2" and devicename.product_id == 1: #Action message setting value to Pet Door
        #Action message doesn't have a counter
        if Print2Frame:
            print("2 Message : "+message)
        msgsplit[4] = hb(int(msgsplit[4])) #Convert length at offset 4 which is decimal into hex byte so we pass it as a hex string to parsedoorframe
        response.message = parsedoorframe(mac_address, int(msgsplit[3]),"".join(msgsplit[4:]))
    elif msgsplit[2] == "8": #Action message setting value to Pet Door
        resp.append({"Msg":message})
        resp.append({"OP":["8"]})
        response.message = resp
    elif msgsplit[2] == "3": # Boot message - dump memory
        resp.append({"Msg":"Dump to " + msgsplit[4]})
        resp.append({"OP":["Dump"]})
        response.message = resp
    else:
        resp.append({"Msg":message})
        resp.append({"OP":["ERROR"]})
        response.message = resp
    return Box(response)

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
            op=singleframeresponse.OP
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
  return ts + " 1000 " + value

#Generate message
def generatemessage(mac_address,operation,state):
    if PrintDebug:
        print(mac_address,operation,state)
    curs.execute('select product_id from devices where mac_address like (?)', ([mac_address]))
    device = curs.fetchone()
    if PrintDebug:
        print(device)
    if EntityType(int(device.product_id)).name == "HUB": #Hub
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
        elif operation == "adoptenable":  #Enable adoption mode to adopt devices.
            msgstr = "2 15 1 02"
        elif operation == "adoptdisable": #Disable adoption mode
            msgstr = "2 15 1 00"
        elif operation == "removedevice0": #Remove Provisioned device 
            msgstr = "2 22 1 00" #00 for device 0, 01 for device 1 etc.
        elif operation == "removedevice1": #Remove Provisioned device 
            msgstr = "2 22 1 01" #00 for device 0, 01 for device 1 etc.
            
        return Box({"topic":"pethublocal/messages", "msg":buildmqttsendmessage(msgstr)})

    elif EntityType(int(device.product_id)).name == "PETDOOR": #Pet Door
        if operation == "dumpstate": #Dump all memory registers from 0 to 630
            msgstr = "3 0 630"
        if operation == "settime": #Set the time
            now = datetime.now() # Current timestamp
            msgstr = "2 34 2 "+hb(now.hour)+" "+hb(now.minute)
        if operation == "setcustom": #Set Custom Modes
            msgstr = "2 61 3 00 00 00"
            #bitwise operator with each custom mode a separate bit to enable/disable
            #def setBit(int_type, offset):
            #mask = 1 << offset
            #return(int_type | mask)

            #def clearBit(int_type, offset):
            #mask = ~(1 << offset)
            #return(int_type & mask)
        
        if operation == "setlockstate39":       #Lock state offset 39, was only set on first lock, probably not needed??
            msgstr = "2 39 1 01"
        if operation == "keepin" or operation == "keepout":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lmresp = curs.fetchone()
            lm = lmresp.lockingmode
            print("Current locking mode: ", lm)
            if (operation == "keepin" and state == "OFF" and lm == 1) or (operation == "keepout" and state == "OFF" and lm == 2):
                #Going to Lock State 0 - Unlocked
                msgstr = "2 36 1 00"
            elif (operation == "keepin" and state == "ON" and lm == 0) or (operation == "keepout" and state == "OFF" and lm == 3):
                #Going to Lock State 1 - Keep pets in
                msgstr = "2 36 1 01"
            elif (operation == "keepin" and state == "OFF" and lm == 3) or (operation == "keepout" and state == "ON" and lm == 0):
                #Going to Lock State 2 - Keep pets out
                msgstr = "2 36 1 02"
            elif (operation == "keepin" and state == "ON" and lm == 2) or (operation == "keepout" and state == "ON" and lm == 1):
                #Going to Lock State 3 - Lock both ways
                msgstr = "2 36 1 03"
            else:
                msgstr = "2 36 1 00"
        if operation == "curfewlock":
            if (state == "ON"):
                #Curfew lock state 4
                msgstr = "2 36 1 04"
            else:
                #Going to Lock State 0 - Unlocked
                msgstr = "2 36 1 00"

        if operation == "setcurfewstate": #Curfew, EE = Enable State, FF = From HH:MM, TT = To HH:MM
            curs.execute('select curfewenabled,lock_time,unlock_time from doors where mac_address = (?)', ([mac_address]))
            curfew = curs.fetchone()
            print("Current curfew mode: ", state)
            if state == "ON":
                stateval = "02"
            else:
                stateval = "01"
            msgstr = "2 519 6 " + stateval + " " +converttimetohex(curfew.lock_time) + " " + converttimetohex(curfew.unlock_time)  + " 00"
        return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(msgstr)})

    elif EntityType(int(device.product_id)).name == "FEEDER": #Feeder
        #curs.execute('select mac_address, lockingmode from devices join doors using (mac_address) where name like (?)', ([device]))
        #macaddy = curs.fetchone()
        if operation == "dumpstate":
        #Request message state
            msgstr = "01 00 ZZ 00 TT TT TT TT " + state
        elif operation == "sendack":
        #Acknowledge the 18 door state.
            msgstr = "00 00 ZZ 00 TT TT TT TT VV 00 00"
            msgstr = msgstr.replace('ZZ', state.counter)
            msgstr = msgstr.replace('VV', state.msg)
        elif operation == "ackfeederstatedoor":
        #Acknowledge the 18 door state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 18 00 00"
            msgstr = msgstr.replace('ZZ', format(counter,'02x'))
        elif operation == "ackfeederstate16":
            #Acknowledge the 16 state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 16 00 00"
        elif operation == "ackfeederstate09":
            #Acknowledge the 09 settings update state.
            msgstr = "00 00 ZZ 00 TT TT TT TT 09 00 00"
        elif operation == "getcurrentstate0b":
        #Request boot message state 0b
            msgstr = "01 00 ZZ 00 TT TT TT TT 0b 00"
        elif operation == "getbootstate0c":
            #Request boot message state 0c - Battery
            msgstr = "01 00 ZZ 00 TT TT TT TT 0c 00"
        elif operation == "getbootstate10":
        #Request boot message state 10
            msgstr = "01 00 ZZ 00 TT TT TT TT 10 00"
        elif operation == "getprovisionedchipsstate":
            #This tells the feeder to dump all provisioned chips
            msgstr = "01 00 ZZ 00 TT TT TT TT 11 00 ff"
        elif operation == "getbootstate17":
            #Request boot message state 17
            msgstr = "01 00 ZZ 00 TT TT TT TT 17 00 00"
        elif operation == "settime":
            #Set on the feeder
            msgstr = "07 00 ZZ 00 TT TT TT TT 00 00 00 00 05"
        elif operation == "lidclosedelayfast":
            #Update lid close delay to fast = 0
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d 00 00 00 00"
        elif operation == "lidclosedelaynormal":
            #Update lid close delay to normal = 4000 (0fa0) - 4 seconds(?)
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d a0 0f 00 00"
        elif operation == "lidclosedelayslow":
            #Update lid close delay to slow = 20000 (4e20) - 20 seconds(?)
            msgstr = "09 00 ZZ 00 TT TT TT TT 0d 20 4e 00 00"
        elif operation == "setleftscaleweight":
            #Set left or single bowl scale weight
            msgstr = "09 00 ZZ 00 TT TT TT TT 0a WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
        elif operation == "setrightscaleweight":
            #Set right scale weight
            msgstr = "09 00 ZZ 00 TT TT TT TT 0b WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue*100)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
        elif operation == "setbowlcount":
            #Set bowl count either 01 for one bowl or 02 for two.
            msgstr = "09 00 ZZ 00 TT TT TT TT 0c WW 00 00 00"
            msgstr = msgstr.replace("WW", format(opval,'02x'))
        elif operation == "set12message":
            #Not sure what caused this but it happened around setting the scales - 12f4010000
            msgstr = "09 00 ZZ 00 TT TT TT TT 12 WW WW WW WW"
            weight= str(binascii.hexlify(struct.pack('<I', opvalue)),'ascii')
            msgstr = msgstr.replace("WW WW WW WW", weight)
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
        devcounter = devicecounter(mac_address,"-1","-2") #Iterate the send counter for the device
        msgstr = msgstr.replace('ZZ', hb(devcounter.send)) # Replace device counter in the record
        msgstr = msgstr.replace('TT TT TT TT', " ".join(hubts[i:i+2] for i in range(0, len(hubts), 2))) # Timestamp
        #msgstr = msgstr.replace('TT TT TT TT', "43 13 e3 54") # Timestamp
        return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage("127 "+msgstr)}) #Need to prefix the message with "127 "

    elif EntityType(int(device.product_id)).name == "CATFLAP": #Cat Flap
        if operation == "dumpstate": #Dump all memory registers from 0 to 630
            msgstr = "TBC"
        elif operation == "settime":
            #I assume the same command that is applied to the feeder is the same as the cat flap... TBC.
            msgstr = "07 00 ZZ 00 TT TT TT TT 00 00 00 00 05"
        elif operation == "keepin" or operation == "keepout":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lockingmode = curs.fetchone()
            lm = lockingmode.lockingmode
            print("Current locking mode: ", lm)
            if (operation == "keepin" and state == "OFF" and lm == 1) or (operation == "keepout" and state == "OFF" and lm == 2):
                #Going to Lock State 0 - Unlocked
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 06 00 02"
            elif (operation == "keepin" and state == "ON" and lm == 0) or (operation == "keepout" and state == "OFF" and lm == 3):
                #Going to Lock State 1 - Keep pets in
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 03 00 02"
            elif (operation == "keepin" and state == "OFF" and lm == 3) or (operation == "keepout" and state == "ON" and lm == 0):
                #Going to Lock State 2 - Keep pets out
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 05 00 02"
            elif (operation == "keepin" and state == "ON" and lm == 2) or (operation == "keepout" and state == "ON" and lm == 1):
                #Going to Lock State 3 - Lock both ways
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 04 00 02"
            else:
                msgstr = "11 00 ZZ 00 TT TT TT TT 00 00 00 00 00 00 07 06 00 02"
        hubts = feedertimestampfromnow()
        devcounter = devicecounter(mac_address,"-1","-2") #Iterate the send counter for the device
        msgstr = msgstr.replace('ZZ', hb(devcounter.send)) # Replace device counter in the record
        msgstr = msgstr.replace('TT TT TT TT', " ".join(hubts[i:i+2] for i in range(0, len(hubts), 2))) # Timestamp
        return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage("127 "+msgstr)}) #Need to prefix the message with "127 "

    else:
        print("Unknown type")

#Update Device Counter
def devicecounter(mac_address,send,retrieve):
    #If the send or retrieve counters are -1 we take the current value and iterate it and -2 return the current value
    curs.execute('select send,retrieve from devicecounter where mac_address=(?)', ([mac_address]))
    devcount = curs.fetchone()
    devc = Box({"send":-3, "retrieve":-3})
    if send == "-2":
        devc.send = devcount.send
    if send == "-1":
        devc.send = devcount.send+1
    if send >= "0":
        devc.send = send
    if retrieve == "-2":
        devc.retrieve = devcount.retrieve
    if retrieve == "-1":
        devc.retrieve = devcount.retrieve+1
    if retrieve >= "0":
        devc.retrieve = retrieve
    cur = conn.cursor()
    upd = 'UPDATE devicecounter SET send=' + str(devc.send) + ', retrieve=' + str(devc.retrieve) + ' WHERE mac_address = "' + mac_address + '"'
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