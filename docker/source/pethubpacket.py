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

import binascii, struct, time, sys, sqlite3, json, glob, logging, pathlib, pytz, re
import os

from datetime import datetime
from operator import xor
from pathlib import Path
from enum import IntEnum
from datetime import datetime, date
from pethubconst import *
from box import Box
from configparser import ConfigParser

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
DebugResponse = False    #Returning MSG payload in json response

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

#Load the database
if os.path.isfile('pethubtest.db'): #If we have a pethubtest then use it as it is for regression testing
    pethubdb = "pethubtest.db"
elif os.path.isfile('pethublocal.db'):
    pethubdb = 'pethublocal.db'
else:
    #Database doesn't exist, so creating dummy one.
    pethubdb = "pethublocal.db"
    #print('Creating Pet Hub Local DB ' + pethubdb)
    connection = sqlite3.connect(pethubdb)
    cursor = connection.cursor()
    pethublocal_file = open("pethublocal.sql")
    cursor.executescript(pethublocal_file.read())
    connection.close()

conn=sqlite3.connect(pethubdb)
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
    return ts

def devicetimestampfromnow():
    now = datetime.utcnow() # Current timestamp in UTC
    bintime = int2bit(now.strftime("%y"),6)+int2bit(now.month,4)+int2bit(now.day,5)+int2bit(now.hour,5)+int2bit(now.minute,6)+int2bit(now.second,6)
    return int(bintime,2).to_bytes(4,'little').hex() #Return as a hex string

def devicetimestampfromstring(tsstring):
    tsarray=re.split('-| |:',tsstring)
    #Take only the last two digits of the year if it is longer
    bintime = int2bit(tsarray[0][-2:],6)+int2bit(tsarray[1],4)+int2bit(tsarray[2],5)+int2bit(tsarray[3],5)+int2bit(tsarray[4],6)+int2bit(tsarray[5],6)
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
        chip = "Null" #**TODO Need to figure out how to calculate this
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
#126 Frames aka can have multiple messages, so need to loop until you get to the end
def parsemultiframe(device, payload):
    response = []
    operation = []
    while len(payload) > 2:
        subframelength=payload[0]+1
        currentframe=payload[1:subframelength]
        frameresponse = parseframe(device, currentframe)
        response.append(frameresponse)
        #Append the operation to a separate array we attach at the end.
        operation.append(frameresponse.Operation)
        #Remove the parsed payload and loop again
        del payload[0:subframelength]
    response.append({"Operation":operation})
    return response

#Parse Feeder, Cat Flap and Felaqua Frame
#Single frame payload to be parsed, can be called by 126 Multi data frame or 127 Single command frame
def parseframe(device, value):
    frameresponse = Box()

    #Frame timestamp value
    frameresponse.frametimestamp = devicetimestamptostring(value[4:8])
    #    print("Timestampts:",frameresponse.framets)

    if DebugResponse:
        frameresponse.Message = tohex(value)

    #Return the message type and counter which is two bytes as they are needed for acknowledgement of the message back
    frameresponse.data=Box({'msg':hb(value[0]),'counter':b2iu(value[2:4])})

    if value[0] in [0x0b, 0x10, 0x16]: #Unknown messages
        op=hb(value[0])
        frameresponse.Operation="Msg"+op
        frameresponse.Message=tohex(value[3:])
    elif value[0] == 0x00: #Send Acknowledge for message type
        frameresponse.Operation="Ack"
        frameresponse.Message=hb(value[8])
        if Print126Frame:
            print("FF-00:ACK-" + hb(value[8]))
    elif value[0] == 0x01: #Send query for data type
        frameresponse.Operation="Query"
        frameresponse.Type=hb(value[8])
        frameresponse.SubData=tohex(value[9:])
        if Print126Frame:
            print("FF-01:QRY-" + hb(value[8]))
    elif value[0] == 0x07: #Set Time
        frameresponse.Operation="Settime"
        frameresponse.Type=tohex(value[8:])
    elif value[0] == 0x09: #Update state messages with subtypes depending on device type
        frameresponse.Operation="UpdateState"
        submessagevalue = b2is(value[9:12])
        if value[8]==0x05: # Training mode
            frameresponse.SubOperation="Training"
            frameresponse.Mode=submessagevalue
        elif value[8]==0x0a: #Set Left Weight
            frameresponse.SubOperation="SetLeftScale"
            frameresponse.Weight=str(round(int(submessagevalue)/100))
        elif value[8]==0x0b: #Set Right Weight
            frameresponse.SubOperation="SetRightScale"
            frameresponse.Weight=str(round(int(submessagevalue)/100))
        elif value[8]==0x0c: #Set Bowl Count either 1 or 2
            frameresponse.SubOperation="SetBowlCount"
            frameresponse.Bowls=FeederBowls(int(submessagevalue)).name
        elif value[8]==0x0d: #Set Feeder Close Delay
            frameresponse.SubOperation="SetCloseDelay"
            frameresponse.Delay=FeederCloseDelay(int(submessagevalue)).name
        elif value[8]==0x12: # **TODO - Always seems to be the same value, either 500, or 5000
            frameresponse.SubOperation="Set12"
            frameresponse.Value = submessagevalue
            frameresponse.MSG=tohex(value[9:])
        elif value[8] == 0x14:  # Custom Mode
            frameresponse.SubOperation = "Custom"
            frameresponse.MODE = submessagevalue
            frameresponse.MSG = tohex(value[9:])
        elif value[8]==0x17: #Set ZeroLeftWeight
            frameresponse.SubOperation="ZeroLeft"
            frameresponse.WEIGHT=submessagevalue
        elif value[8]==0x18: #Set ZeroRightWeight
            frameresponse.SubOperation="ZeroRight"
            frameresponse.WEIGHT=submessagevalue
        elif value[8]==0x19: #SetTODO 19
            frameresponse.SubOperation="SetTODO"
            frameresponse.MSG=tohex(value[9:])
        else:
            frameresponse.SubOperation="SetTODO"
            frameresponse.MSG=tohex(value[9:12])
    elif value[0] == 0x0c: #Battery state for four bytes
        frameresponse.Operation="Battery"
        battery = str(int(b2is(value[8:12]))/1000)
        frameresponse.Battery=battery
        upd = "UPDATE devices SET battery=" + battery + ' WHERE mac_address = "' + device + '"'
        curs.execute(upd)
        conn.commit()
        frameresponse.Value2 = str(int(b2is(value[12:16]))) #**TODO Not sure what this value is.
        frameresponse.Value3 = str(int(b2is(value[16:20]))) #**TODO Or this one
        frameresponse.BatteryTime = devicetimestamptostring(value[20:24]) #**TODO Last time the feeders time was set?
    elif value[0] == 0x0d: #Lock state of Cat Flap and zeroing scales
        print("Message 0d " , len(value))
        if len(value) == 20: #Zeroing Scales
            frameresponse.Operation="ZeroScales"
            frameresponse.Scale = FeederZeroScales(int(value[19])).name
        else:
            frameresponse.Operation="CurfewLockState"
            frameresponse.MSG = tohex(value)
            frameresponse.LockState = CatFlapLockState(int(value[29])).name
            frameresponse.LockStateNumber = str(PetDoorLockState[frameresponse.LockState].value)

    elif value[0] == 0x11: #Provision chip to device and set lock states on cat flap.
        curs.execute('select product_id from devices where mac_address=(?)', ([device]))
        devtype = curs.fetchone()
        #if devtype.product_id == 4:
        if value[14] in [0x01,0x03]: #Provisioning HDX (1) or FDX-B (3) chip
            tag = hextochip(tohex(value[8:15]))
            curs.execute('select name from pets where tag=(?)', ([tag]))
            petval = curs.fetchone()
            if petval:
                frameresponse.Animal=petval.name
            else:
                frameresponse.Animal=tag
            frameresponse.Operation="TagProvision"
            #Setting Lock State on the Animal rather than the Door
            frameresponse.LockState=CatFlapLockState(int(value[15])).name
#            frameresponse.LockStateNumber=str(PetDoorLockState[frameresponse.LockState].value)
            frameresponse.Offset=value[16]
            frameresponse.ChipState=ProvChipState(value[17]).name
        elif value[14] == 0x07: #Set Cat Flap Lock State
            frameresponse.Operation="LockState"
            frameresponse.LockState=CatFlapLockState(int(value[15])).name
            frameresponse.LockStateNumber=str(PetDoorLockState[frameresponse.LockState].value)
            #Update sqlite with lock state integer value
            sqlcmd('UPDATE doors SET lockingmode=' + frameresponse.LockStateNumber + ' WHERE mac_address = "' + device + '"')
        else:
            frameresponse.Operation="Unknown"
            frameresponse.MSG=tohex(value)
    elif value[0] == 0x12: #Curfew
        frameresponse.Operation="Curfew"
        frameresponse.Curfew=[]
        curfewentries = value[16:]
        curfewcount = 0
        while len(curfewentries) > 4:
            if CatFlapCurfewState(curfewentries[8]).name == 'On':
                curfewentry = Box({"State":curfewentries[8],"Start":devicetimestamptostring(curfewentries[0:4]),"End":devicetimestamptostring(curfewentries[4:8])})
                #print("Curfew Val ",curfewentries[8])
                #print("Curfew Entry ",curfewentry)
                frameresponse.Curfew.append(curfewentry)
            curfewcount += 1
            del curfewentries[0:9]
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
            frameresponse.Operation="PetMovement"
        else:
            frameresponse.Operation="PetMovementStatus"
        frameresponse.MSG=tohex(value)
    elif value[0] == 0x18:
        frameresponse.Operation="Feed"
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
            frameresponse.Action=action
            frameresponse.Time=feederopenseconds
            frameresponse.LeftFrom=scaleleftfrom #Or if single bowl
            frameresponse.LeftTo=scaleleftto
            frameresponse.LeftDelta=scaleleftdiff
            frameresponse.RightFrom=scalerightfrom
            frameresponse.RightTo=scalerightto
            frameresponse.RightDelta=scalerightdiff
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
                frameresponse.BowlCount=bowlval.bowltype
            else:
                frameresponse.BowlCount=1
        else:
            frameresponse.Operation="Unknown"
            frameresponse.MSG=tohex(value)
    elif value[0] == 0x1B: #Felaqua Drinking frame, similar to a feeder frame but slightly different
        frameresponse.Operation="Drinking"
        #Different operation values I assume
        drinkaction=hb(value[8])     #Action performed
        drinktime=b2iu(value[9:11])  #Time spent
        drinkfrom=b2ih(value[12:16]) #Weight From
        drinkto=b2ih(value[16:20])   #Weight To
        drinkdiff=str(float(drinkto)-float(drinkfrom))
        frameresponse.Action=drinkaction
        frameresponse.Time=drinktime
        frameresponse.From=drinkfrom
        frameresponse.To=drinkto
        frameresponse.Diff=drinkdiff
        frameresponse.MSG=tohex(value)
        #Update current weight value in database
        upd = "UPDATE feeders SET bowl1=" + drinkto + ' WHERE mac_address = "' + device + '"'
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
        frameresponse.Operation="Unknown"
        frameresponse.MSG=tohex(value)
    return frameresponse

#Parse Hub Frames aka 132's sent to the hub
def parsehubframe(mac_address,offset,value):
    response = []
    frameresponse = Box()
    message=bytearray.fromhex(value)
    frameresponse.Offset = offset
    frameresponse.MSG = value[2:]
    if PrintHubFrame:
        print("Hub Frame: MAC Address: " + mac_address + " offset " + str(offset) + " -value- " + str(value))
    if offset == 15: #Adoption Mode
        opvalue = str(int(message[1]))
        operation="Adopt"
        frameresponse.Operation=operation
        frameresponse[operation]=HubAdoption(int(opvalue)).name 
        #sqlcmd('UPDATE hubs SET pairing_mode=' + opvalue + ' WHERE mac_address = "' + mac_address + '"')
    elif offset == 18: #LED Mode
        opvalue = str(int(message[1]))
        operation="LED"
        frameresponse.Operation=operation
        frameresponse[operation]=HubLeds(int(opvalue)).name 
        sqlcmd('UPDATE hubs SET led_mode=' + opvalue + ' WHERE mac_address = "' + mac_address + '"')
    else:
        if message[0] >= 4: #This is a register dump message
            curs.execute("INSERT OR REPLACE INTO devicestate values((?), (?), (?), (?));", (mac_address, offset, message[0], value[2:]))
            conn.commit()
            operation="Boot"
        else:
            operation="Other"
        frameresponse.Operation=operation
        #frameresponse[operation]=operation
    response.append(frameresponse)
    response.append({"Operation":operation})
    return response

def parse132frame(mac_address,offset,value):
    #Feeder and Cat Flap sends a 132 Status messages and most probably Felaqua sends one too but they only have a 33 type for the time and battery. I think these 132 frames are calcuated by the Hub as part of the RSSI frame.
    response = []
    frameresponse = Box();
    message=bytearray.fromhex(value)
    if offset == 33: #Battery and Door Time
        operation="Data132Battery"
        frameresponse.Operation=operation
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
        frameresponse.Operation=operation
        frameresponse.MSG=tohex(value)
        frameresponse[operation]=operation
    response.append(frameresponse)
    response.append({"Operation":[operation]})
    return response

#Parse Pet Door Frames aka 132's sent to the pet door
def parsedoorframe(mac_address,offset,value):
    response = []
    operation = []
    frameresponse = Box()
    message=bytearray.fromhex(value)
    frameresponse.MSG = value
    if PrintFrameDbg:
        print("Operation: " + str(operation) + " mac_address " + str(mac_address) + " offset " + str(offset) + " -value- " + str(value))
    logmsg=""
    if offset == 33: #Battery and Door Time
        op="Battery"
        frameresponse.Operation=op
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
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.Time=converttime(message[1:3])
    elif offset == 36: #Lock state
        op="LockState"
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.LockState=PetDoorLockState(int(message[1])).name
        frameresponse.LockStateNumber=message[1]
        sqlcmd('UPDATE doors SET lockingmode='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset == 40: #Keep pets out to allow pets to come in state
        op="LockedOutState"
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.LockedOut=PetDoorLockedOutState(int(message[1])).name
    elif offset == 59: #Provisioned Chip Count
        op="PrivChipCount"
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.ChipCount=message[1]
    elif offset >= 91 and offset <= 308: #Provisioned chips
        op="ProvChip"
        frameresponse.Operation=op
        operation.append(op)
        pet=round((int(offset)-84)/7) #Calculate the pet number
        chip=doorhextochip(value[4:]) #Calculate chip Number
        frameresponse.PetOffset=pet
        frameresponse.Chip=chip
    elif offset == 519: #Curfew
        op="Curfew"
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.CurfewState=CurfewState(message[1]).name
        frameresponse.CurfewStateNumber=message[1]
        frameresponse.CurfewOn=str(message[2]).zfill(2)+":"+str(message[3]).zfill(2)
        frameresponse.CurfewOff=str(message[4]).zfill(2)+":"+str(message[5]).zfill(2)
        sqlcmd('UPDATE doors SET curfewenabled='+ str(message[1]) +' WHERE mac_address = "' + mac_address + '"')
    elif offset >= 525 and offset <= 618: #Pet movement state in or out
        op="PetMovement"
        frameresponse.Operation=op
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
        frameresponse.Operation=op
        operation.append(op)
        frameresponse.PetOffset="621"
        frameresponse.Animal="Unknown Pet"
        frameresponse.Direction="Outside"
        frameresponse.State="OFF"
    else:
        op="Other"
        frameresponse.Operation=op
        operation.append(op)
    response.append(frameresponse)
    response.append({"Operation":operation})
    return response

def inithubmqtt():
    response = Box();
    #Devices
    curs.execute('select name,product_id,devices.mac_address,serial_number,uptime,version,state,battery,led_mode,pairing_mode,lockingmode,curfewenabled,curfews,bowl1,bowl2,bowltarget1,bowltarget2,bowltype,close_delay from devices left outer join hubs on devices.mac_address=hubs.mac_address left outer join doors on devices.mac_address=doors.mac_address left outer join feeders on devices.mac_address=feeders.mac_address;')
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
        frameresponse.Operation=op
        frameresponse.MSG=message
        frameresponse[op]='Offline'
        resp.append(frameresponse)
        resp.append({"Operation":[op]})
        #Update state in database
        sqlcmd('UPDATE hubs SET state=0 WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "Hub": #Hub online message
        op="State"
        frameresponse.Operation=op
        frameresponse.MSG=message
        frameresponse[op]='Online'
        resp.append(frameresponse)
        resp.append({"Operation":[op]})
        #Update state in database
        sqlcmd('UPDATE hubs SET state=1 WHERE mac_address = "' + mac_address + '"')
        response.message = resp
    elif msgsplit[2] == "10": #Hub Uptime
        op="Uptime"
        uptime = str(int(msgsplit[3]))
        frameresponse.Operation=op
        frameresponse[op]=uptime
        frameresponse.TS=msgsplit[4]+"-"+':'.join(format(int(x), '02d') for x in msgsplit[5:8])
        frameresponse.Reconnect=msgsplit[9]
        resp.append(frameresponse)
        resp.append({"Operation":[op]})
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
        singleframeop=singleframeresponse.Operation
        singleresponse.append({"Operation":[singleframeop]})
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
        resp.append({"Operation":["8"]})
        response.message = resp
    elif msgsplit[2] == "3": # Boot message - dump memory
        resp.append({"Msg":"Dump to " + msgsplit[4]})
        resp.append({"Operation":["Dump"]})
        response.message = resp
    else:
        resp.append({"Msg":message})
        resp.append({"Operation":["ERROR"]})
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
            op=singleframeresponse.Operation
            response.append({"Operation":[Operation]})
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
            "DumpState"    : { "msg" : "3 0 205",    "desc" : "Dump current configuration" },                    #Dump all memory registers from 0 to 205
            "EarsOff"      : { "msg" : "2 18 1 00",  "desc" : "Ears off" },                                      #Ears off state
            "EarsOn"       : { "msg" : "2 18 1 01",  "desc" : "Ears on" },                                       #Ears on state
            "EarsDimmed"   : { "msg" : "2 18 1 04",  "desc" : "Ears dimmed" },                                   #Ears dimmed state
            "FlashEarsOff" : { "msg" : "2 18 1 80",  "desc" : "Flash ears 3 times and return to ears off" },     #Flash the ears 3 times, return to off state
            "FlashEarsOn"  : { "msg" : "2 18 1 81",  "desc" : "Flash ears 3 times and return to ears on" },      #Flash the ears 3 times, return to on state
            "FlashEarsDim" : { "msg" : "2 18 1 84",  "desc" : "Flash ears 3 times and return to ears dimmed" },  #Flash the ears 3 times, return to dimmed state
            "AdoptEnable"  : { "msg" : "2 15 1 02",  "desc" : "Enable adoption mode to adopt devices." },        #Enable adoption mode to adopt new devices
            "AdoptDisable" : { "msg" : "2 15 1 00",  "desc" : "Disable adoption mode" },                         #Disable adoption mode
            "AdoptButton"  : { "msg" : "2 15 1 82",  "desc" : "Enable adoption using reset button." },           #Enable adoption mode as if you pressed the button under the hub
            "RemoveDev0"   : { "msg" : "2 22 1 00",  "desc" : "Remove Provisioned device 0" },                   #Remove Provisioned device 0
            "RemoveDev1"   : { "msg" : "2 22 1 01",  "desc" : "Remove Provisioned device 1" },                   #Remove Provisioned device 1
            "RemoveDev2"   : { "msg" : "2 22 1 02",  "desc" : "Remove Provisioned device 2" },                   #Remove Provisioned device 2
            "RemoveDev3"   : { "msg" : "2 22 1 03",  "desc" : "Remove Provisioned device 3" },                   #Remove Provisioned device 3
            "RemoveDev4"   : { "msg" : "2 22 1 04",  "desc" : "Remove Provisioned device 4" }                    #Remove Provisioned device 4
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
            "DumpState"    : { "msg" : "3 0 630",                   "desc" : "Dump current registers" },                #Dump all memory registers from 0 to 630
            "SetTime"      : { "msg" : "2 34 2 HH MM",              "desc" : "Set the time" },                          #Set the time on the pet door HH MM in hex
            "CustomMode"   : { "msg" : "2 61 3 00 00 00",           "desc" : "Set Custom mode" },                       #Set custom mode as a bit operator
            "Unlocked"     : { "msg" : "2 36 1 00",                 "desc" : "Unlocked" },                              #Unlocked
            "LockKeepIn"   : { "msg" : "2 36 1 01",                 "desc" : "Keep pets in" },                          #Keep Pets in
            "LockKeepOut"  : { "msg" : "2 36 1 02",                 "desc" : "Keep pets out" },                         #Keep Pets out
            "Locked"       : { "msg" : "2 36 1 03",                 "desc" : "Locked both way" },                       #Locked both ways
            "CurfewMode"   : { "msg" : "2 36 1 04",                 "desc" : "Curfew enabled" },                        #Curfew mode enabled
            "LockState39"  : { "msg" : "2 39 1 01",                 "desc" : "Lock State 39" },                         #Not sure if this is needed, but it was set once during set locking state.
            "CurfewState"  : { "msg" : "2 519 6 SS FF FF TT TT 00", "desc" : "Set Curfew time From / To" },             #Enable curfew time from database
        })
        if operation in operations:
            message = operations[operation].msg
            #Set the time
            now = datetime.now() # Current timestamp
            message = message.replace('HH MM', hb(now.hour)+" "+hb(now.minute)) #Set the time in hex
        elif operation == "KeepIn" or operation == "KeepOut":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lmresp = curs.fetchone()
            lm = lmresp.lockingmode
            if PrintDebug:
                print("Locking mode in database: ", lm)
            if (operation == "KeepIn" and state == "OFF" and lm == 1) or (operation == "KeepOut" and state == "OFF" and lm == 2):  #Going to Lock State 0 - Unlocked
                message = operations["Unlocked"].msg
            elif (operation == "KeepIn" and state == "ON" and lm == 0) or (operation == "KeepOut" and state == "OFF" and lm == 3): #Going to Lock State 1 - Keep pets in
                message = operations["LockKeepIn"].msg
            elif (operation == "KeepIn" and state == "OFF" and lm == 3) or (operation == "KeepOut" and state == "ON" and lm == 0): #Going to Lock State 2 - Keep pets out
                message = operations["LockKeepOut"].msg
            elif (operation == "KeepIn" and state == "ON" and lm == 2) or (operation == "KeepOut" and state == "ON" and lm == 1):  #Going to Lock State 3 - Lock both ways
                message = operations["Locked"].msg
            else:
                message = operations["Unlocked"].msg
        elif operation == "CurfewLock":
            if (state == "ON"): #Curfew lock state 4
                message = operations["CurfewMode"].msg
            else: #Going to Lock State 0 - Unlocked
                message = operations["Unlocked"].msg
        elif operation == "SetCurfewState": #Curfew, EE = Enable State, FF = From HH:MM, TT = To HH:MM
            message = operations['CurfewState'].msg
            curs.execute('select curfewenabled,curfews from doors where mac_address = (?)', ([mac_address]))
            curfew = curs.fetchone()
            #print("Current curfew mode: ", curfew.curfewenabled)
            curfewsstartstop = curfew.curfews.split('-')
            message = message.replace('FF FF TT TT', converttimetohex(curfewsstartstop[0]) + " " + converttimetohex(curfewsstartstop[1])) #Set the curfew time
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
            "Boot9"     : "09", #Boot message 09
            "Unknown0b" : "0b", #Unknown 0b message
            "Battery"   : "0c", #Battery state change
            "Boot10"    : "10", #Boot message 10
            "Tags"      : "11", #Tag provisioning
            "Status16"  : "16", #Status 16 message, happens each time feeder manually opened
            "Boot17"    : "17", #Boot message 17
            "Feeder"    : "18", #Feeder state change
        })
        getdatatype = Box({
            "Boot9"     : "09 00 ff",  #Boot message 09
            "Unknown0b" : "0b 00",     #Unknown 0b
            "Battery"   : "0c 00",     #Battery state
            "Boot10"    : "10 00",     #Boot message 10
            "Tags"      : "11 00 ff",  #Tag provisioned
            "Boot17"    : "17 00 00",  #Boot message  17
        })
        bowlcount = Box({
            "One"   : "01", #One bowl
            "Two"   : "02"  #Two bowls
        })
        lidclosedelay = Box({
            "Fast"   : "00 00 00 00", #0 Seconds
            "Normal" : "a0 0f 00 00", #4 Seconds "0fa0" = 4000
            "Slow"   : "20 4e 00 00"  #20 Seconds "4e20" = 20000
        })
        zeroscale = Box({
            "Left"   : "01", #Zero left scale
            "Right"  : "02", #Zero right scale
            "Both"   : "03"  #Zero both scale
        })
        chipstate = Box({
            "disable"  : "00", #Disable chip
            "enable"   : "01"  #Enable / Provision chip
        })
        #All messages detected sending to the feeder, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "Ack"            : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                             "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type
            "Get"            : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                                   "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "SetTime"        : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 07",                       "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "SetLeftScale"   : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0a WW WW WW WW",                       "desc" : "Set the left or single scale target weight" },              #Set left or single scale weight in grams to 2 decimal places
            "SetRightScale"  : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0b WW WW WW WW",                       "desc" : "Set the right scale target weight" },                       #Set right scale weight in grams to 2 decimal places
            "SetBowlCount"   : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0c SS 00 00 00",                       "desc" : "Set the bowl count", "validate": bowlcount },               #Set bowl count either 01 for one bowl or 02 for two.
            "SetCloseDelay"  : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 0d LL LL LL LL",                       "desc" : "Set the lid close delay", "validate": lidclosedelay },      #Set lid close delay, 0 (fast) , 4 seconds (normal), 20 seconds (slow)
            "Set12"          : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 12 f4 01 00 00",                       "desc" : "Set the 12 message" },                                      #Not sure what caused this but it happened around setting the scales
            "Custom"         : { "msg" : "127 09 00 ZZ ZZ TT TT TT TT 14 00 01 00 00",                       "desc" : "Set Custom Mode - Intruder" },                              #Custom mode - Intruder - This closes the feeder when non-provisioned tags are detected
            "ZeroScale"      : { "msg" : "127 0d 00 ZZ ZZ TT TT TT TT 00 19 00 00 00 03 00 00 00 00 01 SS",  "desc" : "Zero the scales left/right/both", "validate": zeroscale },  #Zero left right or both scales
            "TagProvision"   : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 II SS",        "desc" : "Provision/enable or disable chip" }                         #Provision or enable or disable chip
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

            #Lid Close Delay speed
            if "LL LL LL LL" in message:
                if state in lidclosedelay:
                    message = message.replace("LL LL LL LL", lidclosedelay[state])
                else:
                    return Box({"error":"No valid lid close delay passed"})

            #Chip Provisioning
            if "CC CC CC CC CC CC CC" in message:
                statesplit = state.split('-')
                if len(statesplit) == 3:
                    if statesplit[0] in chipstate:
                        message = message.replace("SS", chipstate[statesplit[0]])
                        message = message.replace("II", hb(int(statesplit[1])))
                        chiphex = chiptohex(statesplit[2])
                        message = message.replace("CC CC CC CC CC CC CC", splitbyte(chiphex))
                    else:
                        return Box({"error":"Invalid state passed"})
                else:
                    return Box({"error":"Invalid values passed, needs to be enable-offset-tagnumber"})

            #print("Operation to do: " + operation + " State " + state + " Message " + message)
            return Box({"topic":"pethublocal/messages/"+mac_address, "msg":buildmqttsendmessage(message)})
        else:
            return Box({"error":"Unknown message"})

    elif EntityType(int(device.product_id)).name == "CATFLAP": #Cat Flap
        ackdatatype = Box({
            "Noot9"       : "09", #Boot message 09
            "Noot10"      : "10", #Boot message 10
            "Tags"        : "11", #Tag provisioning
            "Curfew"      : "12", #Curfew
            "PetMovement" : "13", #Pet movement in / out cat flap
            "Boot17"      : "17", #Boot message 17
            "Unknown0b"   : "0b", #Unknown 0b message
            "Battery"     : "0c"  #Battery state change
        })
        getdatatype = Box({
            "Boot9"     : "09 00 ff", #Boot message 09
            "Boot10"    : "10 00",    #Boot message 10
            "Tags"      : "11 00 ff", #Tag provisioned
            "Boot17"    : "17 00 00", #Boot message  17
            "Unknown0b" : "0b 00",    #Unknown 0b
            "Battery"   : "0c 00"     #Battery state
        })
        chipstate = Box({
            "Disable"  : "00", #Disable chip
            "Enable"   : "01", #Enable / Provision chip
            "Normal"   : "02", #Normal mode in and out
            "KeepIn"   : "03"  #Set KeepIn for the animal
        })

        #All messages detected sending to the feeder, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "Ack"             : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                         "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type
            "Get"             : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                               "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "SetTime"         : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 05",                   "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "Unlocked"        : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 06 00 02",    "desc" : "Unlocked" },                                                 #Unlocked
            "LockKeepIn"      : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 03 00 02",    "desc" : "Keep pets in" },                                            #Keep Pets in
            "LockKeepOut"     : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 05 00 02",    "desc" : "Keep pets out" },                                           #Keep Pets out
            "Locked"          : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 04 00 02",    "desc" : "Locked both way" },                                         #Locked both ways
            "TagKeepIn"       : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC SS II 02",    "desc" : "Set tag KeepIn or normal state" },                          #Cat Flap feature to KeepIn or normal
            "TagProvision"    : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 II SS",    "desc" : "Provision/enable or disable chip" },                        #Provision or enable or disable chip
            "Curfew"          : { "msg" : "127 12 00 ZZ ZZ TT TT TT TT 00 00 00 00 00 00 07 00 AA",       "desc" : "Set Curfew" }                                               #Set Curfews
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
                    #print(chiphex)
                    message = message.replace("CC CC CC CC CC CC CC", splitbyte(chiphex))
                    message = message.replace("SS", chipstate[statesplit[0]])

            #Set Curfew - There can be 4 curfew times, and if they are unset then the second for loop applies.
            if "AA" in message:
                curfewcount = 0
                curfewmessage = ""
                if len(state) > 1:
                    statesplit = state.split(',')
                    for cur in statesplit:
                        startendsplit = cur.split('-')
                        start = datetime.strptime(startendsplit[0], '%H:%M').time()
                        end = datetime.strptime(startendsplit[1], '%H:%M').time()
                        #Time is in UTC using the Cat Flap timestamp format with 00 seconds.
                        startdatetime = datetime.combine(date.today(), start).astimezone(pytz.utc)
                        enddatetime = datetime.combine(date.today(), end).astimezone(pytz.utc)
                        curfewmessage += splitbyte(devicetimestampfromstring(startdatetime.strftime("%y %m %d %H %M 00"))) + " "
                        curfewmessage += splitbyte(devicetimestampfromstring(enddatetime.strftime("%y %m %d %H %M 00"))) + " 03" #03 for enabled after the two times.
                        if curfewcount < 3:
                            curfewmessage += " "
                        curfewcount += 1
                for i in range(curfewcount, 4): #Set the remaining curfews to disabled.
                    curfewmessage += "00 00 42 00 00 00 42 00 06"
                    if i < 3:
                        curfewmessage += " "
                message = message.replace("AA", curfewmessage) #Update the payload with the curfew message

        elif operation == "KeepIn" or operation == "KeepOut":
            curs.execute('select lockingmode from doors where mac_address = (?)', ([mac_address]))
            lmresp = curs.fetchone()
            lm = lmresp.lockingmode
            #print("Current locking mode: ", lm)
            if (operation == "KeepIn" and state == "OFF" and lm == 1) or (operation == "KeepOut" and state == "OFF" and lm == 2):  #Going to Lock State 0 - Unlocked
                message = operations["Unlocked"].msg
            elif (operation == "KeepIn" and state == "ON" and lm == 0) or (operation == "KeepOut" and state == "OFF" and lm == 3): #Going to Lock State 1 - Keep pets in
                message = operations["LockKeepIn"].msg
            elif (operation == "KeepIn" and state == "OFF" and lm == 3) or (operation == "KeepOut" and state == "ON" and lm == 0): #Going to Lock State 2 - Keep pets out
                message = operations["LockKeepOut"].msg
            elif (operation == "KeepIn" and state == "ON" and lm == 2) or (operation == "KeepOut" and state == "ON" and lm == 1):  #Going to Lock State 3 - Lock both ways
                message = operations["Locked"].msg
            else:
                message = operations["Unlocked"].msg
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
            "Boot9"     : "09", #Boot message 09
            "Unknown0b" : "0b", #Unknown 0b message
            "Battery"   : "0c", #Battery state change
            "Boot10"    : "10", #Boot message 10
            "Tags"      : "11", #Tag provisioning
            "Status16"  : "16", #Status 16 message
            "Boot17"    : "17", #Boot message 17
            "Drinking"  : "1b"  #Drinking message
        })
        getdatatype = Box({
            "Boot9"     : "09 00 ff", #Boot message 09
            "Boot10"    : "10 00",    #Boot message 10
            "Tags"      : "11 00 ff", #Tag provisioned
            "Boot17"    : "17 00 00", #Boot message 17
            "Unknown0b" : "0b 00",    #Unknown 0b
            "Battery"   : "0c 00"     #Battery state
        })
        chipstate = Box({
            "Disable"  : "00", #Disable chip
            "Enable"   : "01"  #Enable / Provision chip
        })
        #All messages detected sending to the felaqua, if the fields have validation then they have a validate date referencing the above dictionary key value pairs
        operations = Box({
            "Ack"             : { "msg" : "127 00 00 ZZ ZZ TT TT TT TT SS 00 00",                             "desc" : "Send acknowledge to data type", "validate": ackdatatype },  #Send acknowledge to data type
            "Get"             : { "msg" : "127 01 00 ZZ ZZ TT TT TT TT SS",                                   "desc" : "Get current state of data type", "validate": getdatatype }, #Get data type state
            "SetTime"         : { "msg" : "127 07 00 ZZ ZZ TT TT TT TT 00 00 00 00 06",                       "desc" : "Set the device time" },                                     #Set device time, seems like the last byte = 04 sets time when going forward, 05 sets time, 06 sets time on boot
            "TagProvision"    : { "msg" : "127 11 00 ZZ ZZ TT TT TT TT CC CC CC CC CC CC CC 02 00 SS",        "desc" : "Provision/enable or disable chip" }                         #Provision or enable or disable chip
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
