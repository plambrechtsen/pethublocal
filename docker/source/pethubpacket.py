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

import binascii, struct, time, sys, sqlite3, json, glob, logging, pathlib

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

'''
#Setup Logging framework to log to console without timestamps and log to file with timestamps
log = logging.getLogger('')
log.setLevel(logging.INFO)
logformat = logging.Formatter("%(asctime)s - [%(levelname)-5.5s] - %(message)s")
ch = logging.StreamHandler(sys.stdout)
log.addHandler(ch)
pathlib.Path("log").mkdir(exist_ok=True)
fh = logging.FileHandler('log/pethubpacket-{:%Y-%m-%d}.log'.format(datetime.now()))
fh.setFormatter(logformat)
log.addHandler(fh)
'''

#Import xor key from pethubpacket.xorkey and make sure it is sane.
for file in glob.glob("pethubpacket.xorkey"):
    xorfile=Path(file).read_text()
    if len(xorfile) > 20 and len(xorfile) % 2 == 0:
        xorkey=bytearray.fromhex(xorfile)
    else:
        sys.exit("Corrupted pethubpacket.xorkey file, make sure the length is an even set of bytes")

#Load PetHubLocal database
def box_factory(cursor, row): #Return results as a Box/dict key value pair
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return Box(d)

conn=sqlite3.connect("pethublocal.db")
conn.row_factory = box_factory
curs=conn.cursor()

def sqlcmd(sql_cmd):
    try:
        curs.execute(sql_cmd)
        conn.commit()
    except Error as e:
        print(e)

def bit2int(number,start,bitlen,fill):
    return str(int(number[start : start+bitlen],2)).zfill(fill)

def int2bit(number,fill):
    return str(bin(int(number))[2:]).zfill(fill)

def hextimestampfromnow(): #Create UTC hex timestamp, used for the hub timestamp values for every event
    return hex(round(datetime.utcnow().timestamp()))[2:]

def devicetimestamptostring(hexts):
#    print("Incoming ts",tohex(hexts))
    intts = int.from_bytes(hexts,byteorder='little')
    binstring = str(bin(intts)[2:]).zfill(32)
    ts="{}-{}-{} {}:{}:{}".format("20"+bit2int(binstring,0,6,2),bit2int(binstring,6,4,2),bit2int(binstring,10,5,2),bit2int(binstring,15,5,2),bit2int(binstring,20,6,2),bit2int(binstring,26,6,2))
#    print("parsed ts",ts)
    return ts
    #return str(datetime(bit2int(binstring,0,6,2)+2000,bit2int(binstring,6,4,2),bit2int(binstring,10,5,2),bit2int(binstring,15,5,2),bit2int(binstring,20,6,2),bit2int(binstring,26,6,2)))

def devicetimestampfromnow():
    now = datetime.utcnow() # Current timestamp in UTC
    bintime = int2bit(now.strftime("%y"),6)+int2bit(now.month,4)+int2bit(now.day,5)+int2bit(now.hour,5)+int2bit(now.minute,6)+int2bit(now.second,6)
    return int(bintime,2).to_bytes(4,'little').hex() #Return as a hex string

def localtimestampfromnow():
    dtnow = datetime.now()
    return dtnow.strftime("%Y-%m-%d %H:%M:%S")

def chiptohex(chip):
    chiphex = ""
    if "." in chip:
        #FDX-B Chip - Append 01 for chip type.
        chipsplit=chip.split(".")
        chipbin=format(int(chipsplit[0]),'b').zfill(10)+format(int(chipsplit[1]),'b').zfill(38)
        chipint=int(chipbin,2)
        chiphex=hex(int.from_bytes(chipint.to_bytes(6,'little'),'big'))[2:]
        chiphex = chiphex+'01'
        #print("Feeder Chip to Hex : " + chip + " " + chiphex)
    elif len(chip) == 10:
        #HDX Chip - Chip type seems to be always 03 and needs a 00 to pad it to the right length.
        chiphex = chip+'0003'
    else:
        chiphex = "Error"
    return chiphex

def hextochip(chiphex):
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
        chip=str(int(chipbin[:10],2)) + "." + str(int(chipbin[10:],2)).zfill(12)
    return chip


def splitbyte(bytestring):
    return " ".join(bytestring[i:i+2] for i in range(0, len(bytestring), 2))

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
#    if value[0] == 0x00: #Acknowledge message timestamp at a different offset, for whatever reason, and then some reason it wasn't?
#        frameresponse.framets = devicetimestamptostring(value[3:7])
#    else: #All other timestamps are at the same position.
    frameresponse.framets = devicetimestamptostring(value[4:8])

#    print("Timestamp:",tohex(value[4:8]))
#    print("Timestampts:",frameresponse.framets)

    #The counter is two bytes and is needed for acking back
    frameresponse.data=Box({'msg':hb(value[0]),'counter':b2iu(value[2:4])})

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
        #if devtype.product_id == 4:
        if value[14] == (0x03 or 0x01): #Provisioning HDX (1) or FDX-B (3) chip
            tag = hextochip(tohex(value[8:15]))
            curs.execute('select name from pets where tag=(?)', ([tag]))
            petval = curs.fetchone()
            if petval:
                frameresponse.Animal=petval.name
            else:
                frameresponse.Animal=tag
            frameresponse.OP="Chip"
            frameresponse.Lock=CatFlapLockState(int(value[15])).name
            frameresponse.Offset=value[16]
            frameresponse.ChipState=ProvChipState(value[17]).name
            frameresponse.MSG=tohex(value)
        elif value[14] == 0x07: #Set Cat Flap Lock State
            frameresponse.OP="LockState"
            frameresponse.Lock=CatFlapLockState(int(value[15])).name
            frameresponse.MSG=tohex(value)
        else:
            frameresponse.OP="Unknown"
            frameresponse.MSG=tohex(value)
    elif value[0] == 0x12: #Curfew.. TBC
        frameresponse.OP="Curfew"
        frameresponse.MSG=tohex(value)
    elif value[0] == 0x13: #Pet Movement through cat door
        tag = hextochip(tohex(value[18:25]))
        curs.execute('select name from pets where tag=(?)', ([tag]))
        petval = curs.fetchone()
        if (petval):
            frameresponse.Animal=petval.name
        else:
            frameresponse.Animal=tag
        AnimalDirection=(value[16] << 8) + value[17]
        #print(AnimalDirection)
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
            action=FeederState(int(value[15])).name
            feederopenseconds=b2iu(value[16:17])
            scaleleftfrom=b2ih(value[19:23])
            scaleleftto=b2ih(value[23:27])
            scalerightfrom=b2ih(value[27:31])
            scalerightto=b2ih(value[31:35])
            scaleleftdiff=str(round(float(scaleleftto)-float(scaleleftfrom),2))
            scalerightdiff=str(round(float(scalerightto)-float(scalerightfrom),2))
            frameresponse.FA=action
            frameresponse.FOS=feederopenseconds
            frameresponse.SLF=scaleleftfrom #Or if single bowl
            frameresponse.SLT=scaleleftto
            frameresponse.SLD=scaleleftdiff
            frameresponse.SRF=scalerightfrom
            frameresponse.SRT=scalerightto
            frameresponse.SRD=scalerightdiff
            #Return bowl count
            if value[15] in range(4, 8):
                tag="Manual"
                frameresponse.Animal="Manual"
            else:
                tag = hextochip(tohex(value[8:15]))
                curs.execute('select name from pets where tag=(?)', ([tag]))
                petval = curs.fetchone()
                if (petval):
                    frameresponse.Animal=petval.name
                    #Update weight values in database for known pet when the feeder closes
                    if value[15] == 1:
                        scalediff='['+scaleleftdiff+','+scalerightdiff+']'
                        print("Scale Diff Update: ",scalediff)
                        updatedbtag('petstate',tag,device,'state', scalediff)
                        updatedbtag('petstate',tag,device,'timestamp', localtimestampfromnow())
                else:
                    frameresponse.Animal=tag
            #Update weight values in database for feeder when the feeder closes
            if value[15] in [1,5]:
                updatedb('feeders',device,'bowl1', scaleleftto)
                updatedb('feeders',device,'bowl2', scalerightto)
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
            tag = hextochip(tohex(value[27:34]))
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
        frameresponse[operation]=HubAdoption(int(opvalue)).name 
        #sqlcmd('UPDATE hubs SET pairing_mode=' + opvalue + ' WHERE mac_address = "' + mac_address + '"')
    elif offset == 18: #LED Mode
        opvalue = str(int(message[1]))
        operation="LED"
        frameresponse.OP=operation
        frameresponse[operation]=HubLeds(int(opvalue)).name 
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

def parse132frame(mac_address,offset,value):
    #Feeder and Cat Flap sends a 132 Status messages and most probably Felaqua sends one too but they only have a 33 type for the time and battery. I think these 132 frames are calcuated by the Hub as part of the RSSI frame.
    response = []
    frameresponse = Box();
    message=bytearray.fromhex(value)
    if offset == 33: #Battery and Door Time
        operation="Data132Battery"
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
        frameresponse.LockState=PetDoorLockState(int(message[1])).name
        frameresponse.LockStateNumber=message[1]
        sqlcmd('UPDATE doors SET lockingmode='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset == 40: #Keep pets out to allow pets to come in state
        op="LockedOutState"
        frameresponse.OP=op
        operation.append(op)
        frameresponse.LockedOut=PetDoorLockedOutState(int(message[1])).name
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
        frameresponse.CurfewStateNumber=message[1]
        frameresponse.CurfewOn=str(message[2]).zfill(2)+":"+str(message[3]).zfill(2)
        frameresponse.CurfewOff=str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        sqlcmd('UPDATE doors SET curfewenabled='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset >= 525 and offset <= 618: #Pet movement state in or out
        op="PetMovement"
        frameresponse.OP=op
        operation.append(op)
        deviceindex=round((int(offset)-522)/3)-1 #Calculate the pet number
        if PetDoorDirection.has_value(message[3]):
            direction = PetDoorDirection(message[3]).name
        else:
            direction = "Other " + hb(message[3])
        frameresponse.PetOffset=deviceindex
        #Find Pet
        curs.execute('select tag from tagmap where mac_address=(?) and deviceindex=(?)', (mac_address, deviceindex))
        tagval = curs.fetchone()
        if (tagval):
            curs.execute('select name from pets where tag=(?)', ([tagval.tag]))
            petval = curs.fetchone()
            if (petval):
                petname=petval.name
                if message[3] in [0x61, 0x81]:
                    petstate = "1" #Inside
                else:
                    petstate = "0" #Otherwise Outside
                updatedbtag('petstate',tagval.tag,mac_address,'state', petstate )  # Update state as inside or outside
                updatedbtag('petstate',tagval.tag,mac_address,'timestamp', localtimestampfromnow()) #Update timestamp
            else:
                petname="Unknown"
        else:
            petname="Unknown"
        frameresponse.Animal=petname
        frameresponse.Direction=direction
        operation.append("PetMovement")
    elif offset == 621: #Unknown pet went outside, should probably do a lookup to see what animals are still inside and update who is left??
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
    curs.execute('select name,product_id,devices.mac_address,serial_number,uptime,version,state,battery,led_mode,pairing_mode,curfewenabled,lock_time,unlock_time,lockingmode,bowl1,bowl2,bowltarget1,bowltarget2,bowltype,close_delay from devices left outer join hubs on devices.mac_address=hubs.mac_address left outer join doors on devices.mac_address=doors.mac_address left outer join feeders on devices.mac_address=feeders.mac_address;')
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
        try:
            int(msgsplit[0], 16)
            timestampstr = str(datetime.utcfromtimestamp(int(msgsplit[0],16)))
        except ValueError:
            timestampstr = str(datetime.utcnow().replace(microsecond=0))
    else:
        curs.execute('select name,mac_address,product_id from devices where mac_address=(?)', ([mac_address]))
        devicename = curs.fetchone()
        if devicename:
            response.device = str(devicename.name)
            response.mac_address = mac_address
        else:
            response.device = str(mac_address)
            response.mac_address = mac_address
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
        frameresponse.MSG=message
        frameresponse[op]='Offline'
        resp.append(frameresponse)
        resp.append({"OP":[op]})
        #Update state in database
        sqlcmd('UPDATE hubs SET state=0 WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "Hub": #Hub online message
        op="State"
        frameresponse.OP=op
        frameresponse.MSG=message
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
    elif msgsplit[2] == "132": #Feeder 132 Status
        #Status message has a counter at offset 4 we can ignore:
        if PrintFeederFrame:
            print("NonHub/PetDoor 132 Message : "+message)
        msgsplit[5] = hb(int(msgsplit[5])) #Convert length at offset 5 which is decimal into hex byte so we pass it as a hex string to parsedataframe
        #print("Message :", "".join(msgsplit[5:]))
        response.message = parse132frame(mac_address, int(msgsplit[4]),"".join(msgsplit[5:]))
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
    elif msgsplit[2] == "2" and EntityType(int(devicename.product_id)).name == "HUB": #Action message setting value to Hub Pet Door
        #Action message doesn't have a counter
        if Print2Frame:
            print("2 Message : "+message)
        msgsplit[4] = hb(int(msgsplit[4])) #Convert length at offset 4 which is decimal into hex byte so we pass it as a hex string to parsedoorframe
        response.message = parsehubframe(mac_address, int(msgsplit[3]),"".join(msgsplit[4:]))
    elif msgsplit[2] == "2" and EntityType(int(devicename.product_id)).name == "PETDOOR": #Action message setting value to Hub Pet Door
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
  return hextimestampfromnow() + " 1000 " + value

#Generate message
def generatemessage(mac_address,operation,state):
    if PrintDebug:
        print("GenerateMessage: Mac={} Op={} State={}".format(mac_address,operation,state))
    curs.execute('select product_id from devices where mac_address like (?)', ([mac_address]))
    device = curs.fetchone()
    if PrintDebug:
        print("Device: ",EntityType(int(device.product_id)).name)
    if EntityType(int(device.product_id)).name == "HUB": #Hub
        operations = Box({
            "dumpstate"    : { "msg" : "3 0 205",    "desc" : "Dump current configuration" },                    #Dump all memory registers from 0 to 205
            "earsoff"      : { "msg" : "2 18 1 00",  "desc" : "Ears off" },                                      #Ears off state
            "earson"       : { "msg" : "2 18 1 01",  "desc" : "Ears on" },                                       #Ears on state
            "earsdimmed"   : { "msg" : "2 18 1 04",  "desc" : "Ears dimmed" },                                   #Ears dimmed state
            "flashearsoff" : { "msg" : "2 18 1 80",  "desc" : "Flash ears 3 times and return to ears off" },     #Flash the ears 3 times, return to off state
            "flashearson"  : { "msg" : "2 18 1 81",  "desc" : "Flash ears 3 times and return to ears on" },      #Flash the ears 3 times, return to on state
            "flashearsdim" : { "msg" : "2 18 1 84",  "desc" : "Flash ears 3 times and return to ears dimmed" },  #Flash the ears 3 times, return to dimmed state
            "adoptenable"  : { "msg" : "2 15 1 02",  "desc" : "Enable adoption mode to adopt devices." },        #Enable adoption mode to adopt new devices
            "adoptdisable" : { "msg" : "2 15 1 00",  "desc" : "Disable adoption mode" },                         #Disable adoption mode
            "adoptbutton"  : { "msg" : "2 15 1 82",  "desc" : "Enable adoption using reset button." },           #Enable adoption mode as if you pressed the button under the hub
            "removedev0"   : { "msg" : "2 22 1 00",  "desc" : "Remove Provisioned device 0" },                   #Remove Provisioned device 0
            "removedev1"   : { "msg" : "2 22 1 01",  "desc" : "Remove Provisioned device 1" },                   #Remove Provisioned device 1
            "removedev2"   : { "msg" : "2 22 1 02",  "desc" : "Remove Provisioned device 2" },                   #Remove Provisioned device 2
            "removedev3"   : { "msg" : "2 22 1 03",  "desc" : "Remove Provisioned device 3" },                   #Remove Provisioned device 3
            "removedev4"   : { "msg" : "2 22 1 04",  "desc" : "Remove Provisioned device 4" }                    #Remove Provisioned device 4
        })
        if operation == "operations":      #Dump all memory registers from 0 to 205
            return operations
        elif operation in operations:
            #print("Operation to do: " + operation)
            return Box({"topic":"pethublocal/messages", "msg":buildmqttsendmessage(operations[operation].msg)})
        else:
            return Box({"error":"Unknown message"})

    elif EntityType(int(device.product_id)).name == "PETDOOR": #Pet Door
        curfewstate = Box({
            "OFF"  : "01", #Disable Curfew State
            "ON"   : "02"  #Enable Curfew State
        })
        operations = Box({
            "dumpstate"    : { "msg" : "3 0 630",                   "desc" : "Dump current registers" },                #Dump all memory registers from 0 to 630
            "settime"      : { "msg" : "2 34 2 HH MM",              "desc" : "Set the time" },                          #Set the time on the pet door HH MM in hex
            "custommode"   : { "msg" : "2 61 3 00 00 00",           "desc" : "Set Custom mode" },                       #Set custom mode as a bit operator
            "unlocked"     : { "msg" : "2 36 1 00",                 "desc" : "Unlocked" },                              #Unlocked
            "lockkeepin"   : { "msg" : "2 36 1 01",                 "desc" : "Keep pets in" },                          #Keep Pets in
            "lockkeepout"  : { "msg" : "2 36 1 02",                 "desc" : "Keep pets out" },                         #Keep Pets out
            "locked"       : { "msg" : "2 36 1 03",                 "desc" : "Locked both way" },                       #Locked both ways
            "curfewmode"   : { "msg" : "2 36 1 04",                 "desc" : "Curfew enabled" },                        #Curfew mode enabled
            "lockstate39"  : { "msg" : "2 39 1 01",                 "desc" : "Lock State 39" },                         #Not sure if this is needed, but it was set once during set locking state.
            "curfewstate"  : { "msg" : "2 519 6 SS FF FF TT TT 00", "desc" : "Set Curfew time From / To" },             #Enable curfew time from database
        })
        if operation in operations:
            message = operations[operation].msg
            #Set the time
            now = datetime.now() # Current timestamp
            message = message.replace('HH MM', hb(now.hour)+" "+hb(now.minute)) #Set the time
        elif operation == "keepin" or operation == "keepout":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lmresp = curs.fetchone()
            lm = lmresp.lockingmode
            if PrintDebug:
                print("Locking mode in database: ", lm)
            if (operation == "keepin" and state == "OFF" and lm == 1) or (operation == "keepout" and state == "OFF" and lm == 2):  #Going to Lock State 0 - Unlocked
                message = operations["unlocked"].msg
            elif (operation == "keepin" and state == "ON" and lm == 0) or (operation == "keepout" and state == "OFF" and lm == 3): #Going to Lock State 1 - Keep pets in
                message = operations["lockkeepin"].msg
            elif (operation == "keepin" and state == "OFF" and lm == 3) or (operation == "keepout" and state == "ON" and lm == 0): #Going to Lock State 2 - Keep pets out
                message = operations["lockkeepout"].msg
            elif (operation == "keepin" and state == "ON" and lm == 2) or (operation == "keepout" and state == "ON" and lm == 1):  #Going to Lock State 3 - Lock both ways
                message = operations["locked"].msg
            else:
                message = operations["unlocked"].msg
        elif operation == "curfewlock":
            if (state == "ON"): #Curfew lock state 4
                message = operations["curfewmode"].msg
            else: #Going to Lock State 0 - Unlocked
                message = operations["unlocked"].msg
        elif operation == "setcurfewstate": #Curfew, EE = Enable State, FF = From HH:MM, TT = To HH:MM
            message = operations['curfewstate'].msg
            curs.execute('select curfewenabled,lock_time,unlock_time from doors where mac_address = (?)', ([mac_address]))
            curfew = curs.fetchone()
            #print("Current curfew mode: ", state)
            message = message.replace('FF FF TT TT', converttimetohex(curfew.lock_time) + " " + converttimetohex(curfew.unlock_time)) #Set the curfew time
            if state in curfewstate: #Has string value to map
                message = message.replace("SS", curfewstate[state])
            elif hb(int(state)) in curfewstate.values(): #Has value that exists in validation dictionary
                message = message.replace("SS", hb(int(state)))
            else:
                return Box({"error":"Unknown message"})
        else:
            return Box({"error":"Unknown message"})
        return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(message)})

    elif EntityType(int(device.product_id)).name == "FEEDER": #Feeder
        ackdatatype = Box({
            "boot9"     : "09", #Boot message 09
            "boot10"    : "10", #Boot message 10
            "tags"      : "11", #Tag provisioning
            "status16"  : "16", #Status 16 message, happens each time feeder manually opened
            "boot17"    : "17", #Boot message 17
            "feeder"    : "18", #Feeder state change
            "unknown0b" : "0b", #Unknown 0b message
            "battery"   : "0c"  #Battery state change
        })
        getdatatype = Box({
            "boot9"     : "09 00 ff", #Boot message 09
            "boot10"    : "10 00",    #Boot message 10
            "tags"      : "11 00 ff", #Tag provisioned
            "boot17"    : "17 00 00", #Boot message  17
            "unknown0b" : "0b 00",    #Unknown 0b
            "battery"   : "0c 00"     #Battery state
        })
        bowlcount = Box({
            "one"   : "01", #One bowl
            "two"   : "02"  #Two bowls
        })
        lidclosedelay = Box({
            "fast"   : "00 00 00 00", #0 Seconds
            "normal" : "a0 0f 00 00", #4 Seconds "0fa0" = 4000
            "slow"   : "20 4e 00 00"  #20 Seconds "4e20" = 20000
        })
        zeroscale = Box({
            "left"   : "01", #Zero left scale
            "right"  : "02", #Zero right scale
            "both"   : "03"  #Zero both scale
        })
        chipstate = Box({
            "disable"  : "00", #Disable chip
            "enable"   : "01"  #Enable / Provision chip
        })
        #All messages detected sending to the feeder, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "ack"             : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                             "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type 
            "get"             : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                                   "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "settime"         : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 06",                       "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "setleftscale"    : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0a WW WW WW WW",                       "desc" : "Set the left or single scale target weight" },              #Set left or single scale weight in grams to 2 decimal places
            "setrightscale"   : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0b WW WW WW WW",                       "desc" : "Set the right scale target weight" },                       #Set right scale weight in grams to 2 decimal places
            "setbowlcount"    : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0c SS 00 00 00",                       "desc" : "Set the bowl count", "validate": bowlcount },               #Set bowl count either 01 for one bowl or 02 for two.
            "lidclosedelay"   : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0d LL LL LL LL",                       "desc" : "Set the lid close delay", "validate": lidclosedelay },      #Set lid close delay, 0 (fast) , 4 seconds (normal), 20 seconds (slow)
            "set12message"    : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 12 f4 01 00 00",                       "desc" : "Set the 12 message" },                                      #Not sure what caused this but it happened around setting the scales
            "zeroscale"       : { "msg" : "127 0d 00 ZZ ZZ TT TT TT TT 00 19 00 00 00 03 00 00 00 00 01 SS",  "desc" : "Zero the scales left/right/both", "validate": zeroscale },  #Zero left right or both scales
            "chipprovision"   : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 00 SS",        "desc" : "Provision/enable or disable chip" }                         #Provision or enable or disable chip
        })
        if operation in operations:
            message = operations[operation].msg
            #Update standard values of the counter, and the timestamp
            hubts = splitbyte(devicetimestampfromnow())
            devcount = devicecounter(mac_address,"-1","-2") #Iterate the send counter for the device
            message = message.replace('ZZ ZZ', splitbyte(devcount.send.to_bytes(2,'little').hex())) #Replace device send counter in the record
            message = message.replace('TT TT TT TT', hubts) #Replace timestamp in the record
            #This operation has values we should validate
            if "validate" in operations[operation]:
                #print(operations[operation].validate)
                if state in operations[operation].validate: #Has string value to map
                    message = message.replace("SS", operations[operation].validate[state])
                elif hb(int(state,16)) in operations[operation].validate.values(): #Has value that exists in validation dictionary
                    message = message.replace("SS", hb(int(state,16)))
                else:
                    return Box({"error":"Invalid value passed, check validation", "validate": operations[operation].validate })
            #Message has a weight value we need to convert from the incoming state
            if "WW WW WW WW" in message:
                if state.isdigit():
                    weight=splitbyte((int(state)*100).to_bytes(4,'little').hex())
                    #print("Weight: "+str(state) + " AsHex " + weight)
                    message = message.replace("WW WW WW WW", weight)
                else:
                    return Box({"error":"No valid positive integer weight passed"})

            #Chip Provisioning
            if "CC CC CC CC CC CC CC" in message:
                statesplit = state.split('-')
                if statesplit[0] in chipstate:
                    chiphex = chiptohex(statesplit[1])
                    print(chiphex)
                    message = message.replace("CC CC CC CC CC CC CC", splitbyte(chiphex))
                    message = message.replace("SS", chipstate[statesplit[0]])

            #print("Operation to do: " + operation + " State " + state + " Message " + message)
            return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(message)})
        else:
            return Box({"error":"Unknown message"})

    elif EntityType(int(device.product_id)).name == "CATFLAP": #Cat Flap
        ackdatatype = Box({
            "boot9"       : "09", #Boot message 09
            "boot10"      : "10", #Boot message 10
            "tags"        : "11", #Tag provisioning
            "curfew"      : "12", #Curfew
            "petmovement" : "13", #Pet movement in / out cat flap
            "boot17"      : "17", #Boot message 17
            "unknown0b"   : "0b", #Unknown 0b message
            "battery"     : "0c"  #Battery state change
        })
        getdatatype = Box({
            "boot9"     : "09 00 ff", #Boot message 09
            "boot10"    : "10 00",    #Boot message 10
            "tags"      : "11 00 ff", #Tag provisioned
            "boot17"    : "17 00 00", #Boot message  17
            "unknown0b" : "0b 00",    #Unknown 0b
            "battery"   : "0c 00"     #Battery state
        })

        #All messages detected sending to the feeder, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "ack"             : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                       "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type 
            "get"             : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                             "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "settime"         : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 05",                 "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "unlocked"        : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 06 00 02",  "desc" : "Unlocked" },                                                 #Unlocked
            "lockkeepin"      : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 03 00 02",  "desc" : "Keep pets in" },                                            #Keep Pets in
            "lockkeepout"     : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 05 00 02",  "desc" : "Keep pets out" },                                           #Keep Pets out
            "locked"          : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 04 00 02",  "desc" : "Locked both way" },                                         #Locked both ways
            "chipprovision"   : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 00 SS",  "desc" : "Provision/enable or disable chip" }                         #Provision or enable or disable chip
        })

        if operation in operations:
            message = operations[operation].msg
            #This operation has values we should validate
            if "validate" in operations[operation]:
                #print(operations[operation].validate)
                if state in operations[operation].validate: #Has string value to map
                    message = message.replace("SS", operations[operation].validate[state])
                elif hb(int(state)) in operations[operation].validate.values(): #Has value that exists in validation dictionary
                    message = message.replace("SS", hb(int(state)))
                else:
                    return Box({"error":"Invalid value passed, check validation", "validate": operations[operation].validate })

            #Chip Provisioning
            if "CC CC CC CC CC CC CC" in message:
                statesplit = state.split('-')
                if statesplit[0] in chipstate:
                    chiphex = chiptohex(statesplit[1])
                    print(chiphex)
                    message = message.replace("CC CC CC CC CC CC CC", splitbyte(chiphex))
                    message = message.replace("SS", chipstate[statesplit[0]])

        elif operation == "keepin" or operation == "keepout":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lmresp = curs.fetchone()
            lm = lmresp.lockingmode
            #print("Current locking mode: ", lm)
            if (operation == "keepin" and state == "OFF" and lm == 1) or (operation == "keepout" and state == "OFF" and lm == 2):  #Going to Lock State 0 - Unlocked
                message = operations["unlocked"].msg
            elif (operation == "keepin" and state == "ON" and lm == 0) or (operation == "keepout" and state == "OFF" and lm == 3): #Going to Lock State 1 - Keep pets in
                message = operations["lockkeepin"].msg
            elif (operation == "keepin" and state == "OFF" and lm == 3) or (operation == "keepout" and state == "ON" and lm == 0): #Going to Lock State 2 - Keep pets out
                message = operations["lockkeepout"].msg
            elif (operation == "keepin" and state == "ON" and lm == 2) or (operation == "keepout" and state == "ON" and lm == 1):  #Going to Lock State 3 - Lock both ways
                message = operations["locked"].msg
            else:
                message = operations["unlocked"].msg
        else:
            return Box({"error":"Unknown message"})

        #Update standard values of the counter, and the timestamp
        hubts = splitbyte(devicetimestampfromnow())
        devcount = devicecounter(mac_address,"-1","-2") #Iterate the send counter for the device
        message = message.replace('ZZ ZZ', splitbyte(devcount.send.to_bytes(2,'little').hex())) #Replace device send counter in the record with two byte counter
        message = message.replace('TT TT TT TT', hubts) #Replace timestamp in the record
        return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(message)})

    elif EntityType(int(device.product_id)).name == "FELAQUA": #Felaqua
        ackdatatype = Box({
            "boot9"     : "09", #Boot message 09
            "unknown0b" : "0b", #Unknown 0b message
            "battery"   : "0c", #Battery state change
            "boot10"    : "10", #Boot message 10
            "tags"      : "11", #Tag provisioning
            "status16"  : "16", #Status 16 message
            "boot17"    : "17", #Boot message 17
            "drinking"  : "1b"  #Drinking message
        })
        getdatatype = Box({
            "boot9"     : "09 00 ff", #Boot message 09
            "boot10"    : "10 00",    #Boot message 10
            "tags"      : "11 00 ff", #Tag provisioned
            "boot17"    : "17 00 00", #Boot message  17
            "unknown0b" : "0b 00",    #Unknown 0b
            "battery"   : "0c 00"     #Battery state
        })
        zeroscale = Box({
            "left"   : "01", #Zero left scale
            "right"  : "02", #Zero right scale
            "both"   : "03"  #Zero both scale
        })
        chipstate = Box({
            "disable"  : "00", #Disable chip
            "enable"   : "01"  #Enable / Provision chip
        })
        #All messages detected sending to the felaqua, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "ack"             : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                             "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type 
            "get"             : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                                   "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "settime"         : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 06",                       "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "chipprovision"   : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 00 SS",        "desc" : "Provision/enable or disable chip" }                         #Provision or enable or disable chip
        })
        if operation in operations:
            message = operations[operation].msg
            #Update standard values of the counter, and the timestamp
            hubts = splitbyte(devicetimestampfromnow())
            devcount = devicecounter(mac_address,"-1","-2") #Iterate the send counter for the device
            message = message.replace('ZZ ZZ', splitbyte(devcount.send.to_bytes(2,'little').hex())) #Replace device send counter in the record
            message = message.replace('TT TT TT TT', hubts) #Replace timestamp in the record
            #This operation has values we should validate
            if "validate" in operations[operation]:
                #print(operations[operation].validate)
                if state in operations[operation].validate: #Has string value to map
                    message = message.replace("SS", operations[operation].validate[state])
                elif hb(int(state,16)) in operations[operation].validate.values(): #Has value that exists in validation dictionary
                    message = message.replace("SS", hb(int(state,16)))
                else:
                    return Box({"error":"Invalid value passed, check validation", "validate": operations[operation].validate })
            #Message has a weight value we need to convert from the incoming state
            if "WW WW WW WW" in message:
                if state.isdigit():
                    weight=splitbyte((int(state)*100).to_bytes(4,'little').hex())
                    #print("Weight: "+str(state) + " AsHex " + weight)
                    message = message.replace("WW WW WW WW", weight)
                else:
                    return Box({"error":"No valid positive integer weight passed"})

            #Chip Provisioning
            if "CC CC CC CC CC CC CC" in message:
                statesplit = state.split('-')
                if statesplit[0] in chipstate:
                    chiphex = chiptohex(statesplit[1])
                    print(chiphex)
                    message = message.replace("CC CC CC CC CC CC CC", splitbyte(chiphex))
                    message = message.replace("SS", chipstate[statesplit[0]])

            #print("Operation to do: " + operation + " State " + state + " Message " + message)
            return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(message)})
        else:
            return Box({"error":"Unknown message"})
    else:
        print("Unknown type")

#Update Device Counter for messages send to all devices apart from the pet door.
def devicecounter(mac_address,send,retrieve):
    #If the send or retrieve counters are -1 we take the current value and iterate it and -2 return the current value
    curs.execute('select send,retrieve from devicecounter where mac_address=(?)', ([mac_address]))
    devcount = curs.fetchone()
    devc = Box({"send":-3, "retrieve":-3})
    if send == "-2":
        devc.send = devcount.send
    if send == "-1":
        devc.send = devcount.send+1
        #Reset the counter if larger than 65535
        if devc.send > 65535:
            devc.send = 0
    if send >= "0":
        devc.send = send
    if retrieve == "-2":
        devc.retrieve = devcount.retrieve
    if retrieve == "-1":
        devc.retrieve = devcount.retrieve+1
        #Reset the counter if larger than 65535
        if devc.retrieve > 65535:
            devc.retrieve = 0
    if retrieve >= "0":
        devc.retrieve = retrieve
    cur = conn.cursor()
    upd = 'UPDATE devicecounter SET send=' + str(devc.send) + ', retrieve=' + str(devc.retrieve) + ' WHERE mac_address = "' + mac_address + '"'
    cur.execute(upd)
    conn.commit()
    return devc

def updatedb(tab,mac_address,col,val):
    cur = conn.cursor()
    upd = 'UPDATE '+ tab + ' SET ' + col + ' = "' + val + '" WHERE mac_address = "' + mac_address + '"'
    cur.execute(upd)
    conn.commit()

#Update the petstate database when 
def updatedbtag(tab,tag,mac_address,col,val):
    cur = conn.cursor()
    upd = 'UPDATE '+ tab + ' SET ' + col + ' = "' + val + '" WHERE tag = "' + tag + '" and mac_address = "' + mac_address + '"'
    cur.execute(upd)
    conn.commit()
