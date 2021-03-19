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
import paho.mqtt.client as mqtt

from datetime import datetime
from operator import xor
from pathlib import Path

#Debugging mesages
PrintFrame = False #Print the before and after xor frame
PrintFrameDbg = False #Print the frame headers
Print121Frame = False #Debug the 2D / 121 feeder frame
Print126Frame = False #Debug the 2A / 126 feeder frame
Print132Frame = False #Debug the 3C / 132 feeder frame

#Feeder static values
fStateArr={0:"Animal_open", 1:"Animal_shut", 4:"Manual_open", 5: "Manual_shut"} # Feeder State either open or closed
fCloseDelayArr={0:"Fast", 4000:"Normal", 20000:"Slow"}                          # Feeder Close Delay speed
fBowls={1:"Single", 2:"Double"}                                                 # Feeder number of bowls
fDirection={0:"Looked in", 1:"in", 2:"out", 3:"3", 4:"4", 5:"5", 6:"6", 7:"7" , 8:"8", 9:"9" } # Direction

#Import xor key from pethubpacket.xorkey and make sure it is sane.
xorfile=Path('/data/pethubpacket.xorkey').read_text()
if len(xorfile) > 20 and len(xorfile) % 2 == 0:
    xorkey=bytearray.fromhex(xorfile)
else:
    sys.exit("Corrupted pethubpacket.xorkey file, make sure the length is an even set of bytes")

#Load PetHubLocal database
conn=sqlite3.connect('pethublocal.db')
curs=conn.cursor()
conn.row_factory = sqlite3.Row

#Conversion of byte arrays into integers
def b2ih(b2ihvalue):
  #Divide int by 100 to give two decimal places for weights
  return str(int(b2i(b2ihvalue))/100)

def b2i(b2ivalue):
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

#Message to feeder is a 121
def parse121(value):
  if Print121Frame:
    print("Current 2D / 121 : Message " + format(value[0],'x'))
    print("Current 2D / 121 : " + tohex(value))
  if value[0]==0x09:
    fCloseDelayArr=int(batoint(value[9:11],1))
    print("Current 2D / 121 : Feeder Close Delay = " + feederCloseDelayArray[fCloseDelayArr])
  return "Success"

#Message from feeder is a 126 
def parse126(value):
#  print("Parse : " + ''.join(format(x, '02x') for x in value))
  if Print126Frame:
    print("Current 2A / 126 : Message " + format(value[0],'02x'))
    print("Current 2A / 126 : " + tohex(value))
  if value[0]==0x18:
    #Hard code feeder states
    if value[15] in fStateArr:
      if value[15] == 4 or value[15] == 5:
        chip="Manual"
      else:
        if value[13] == 0:
          #HDX
          chip=tohex(value[8:14])
        elif value[14] == 1:
          #FDX-B
          chipval = "{0:48b}".format(int.from_bytes(value[8:14], byteorder='little'))
          chip=str(int(chipval[:10],2)) + "." + str(int(chipval[10:],2)).zfill(12)
        else:
          chip="Unknown"+tohex(value[8:15])
        print(tohex(value[12:16]))
      return "Feeder chip="+chip+",action="+fStateArr[value[15]]+',secondsopen='+ b2i(value[16:17])+',scaleleftfrom='+b2ih(value[19:23])+',scaleleftto='+b2ih(value[23:27])+',scalerightfrom='+b2ih(value[27:31])+',scalerightto='+b2ih(value[31:35])
    else:
      return ""
  elif value[0]==0x09:
    if Print126Frame:
      print("Msg 09 Subtype   :", hb(value[8]))
    msg=""
    submessagevalue = b2i(value[9:12])
    submessagevalueh = b2ih(value[9:12])
    if value[8]==0x05:
      msg = "TrainingMode=" + submessagevalue
    elif value[8]==0x0a:
      msg = "SetLeftWeight=" + submessagevalueh
    elif value[8]==0x0b:
      msg = "SetRightWeight=" + submessagevalueh
    elif value[8]==0x0c:
      msg = "SetFeederBowls=" + fBowls[int(submessagevalue)]
    elif value[8]==0x0d:
      msg = "CloseDelay=" + fCloseDelayArr[int(submessagevalue)]
    elif value[8]==0x17:
      msg = "ZeroLeft=" + submessagevalueh
    elif value[8]==0x18:
      msg = "ZeroRight=" + submessagevalueh
    else:
      msg = "Unknown"
    if Print126Frame:
      print("Current 2D / 121 :", msg )
    return msg + ","
  elif value[0] == 0x16:
    msg = "Message 16 " + tohex(value[3:])
    if Print126Frame:
      print(msg)
    return msg
  elif value[0]==0x0b:
    msg = "Boot Message 0b " + tohex(value[3:])
    if Print126Frame:
      print(msg)
    return msg
  elif value[0]==0x0c:
    msg = "Boot Message 0c " + tohex(value[3:])
    if Print126Frame:
      print(msg)
    return msg
  elif value[0]==0x10:
    msg = "Boot Message 10 " + tohex(value[3:])
    if Print126Frame:
      print(msg)
    return msg
  elif value[0]==0x00:
    msg = "Message 00=" + tohex(value[3:])
    if Print126Frame:
      print(msg)
    return msg
  else:
    return "Unknown=" + format(value[0],'02x')

def decodemiwi(timestamp,source,destination,framestr):
    framexor=bytearray.fromhex(framestr)
    #Convert MAC addresses into Surepet reverse byte format.
    sourcemac=''.join(list(reversed(source.split(":")))).upper()
    destinationmac=''.join(list(reversed(destination.split(":")))).upper()

    frame = list(map(xor, framexor, xorkey))
    if PrintFrame:
        print("Received frame at: " + timestamp + " from: " + sourcemac + " to: " + destinationmac)
        print("Packet:" + tohex(framexor))
        print("Dexor :" + tohex(frame))
    if PrintFrameDbg:
        print("Frame Type       :", hb(frame[2]))
        print("Frame Length Val :", frame[4])
    payload=frame[6:]
    logmsg=""
    if frame[2] == 0x2a:
        logmsg="Feeder: "
        if Print126Frame:
            print("Frame 2A / 126   : " + tohex(payload))
        while len(payload) > 4:
            msglen=payload[0]+1
            curmessage=payload[1:msglen]
            resmessage=parse126(curmessage)
            if len(resmessage) > 0 and Print126Frame:
                print("Frame 2A message :" + resmessage)
            #Append parsed message response
            logmsg += resmessage
            #Remove the parsed payload and loop again
            del payload[0:msglen]
    if frame[2] == 0x2d:
        logmsg="Hub   : "
        if Print121Frame:
            print("Frame 2D / 121   : " + tohex(payload))
        resmessage=parse126(payload)
        logmsg += resmessage
        if len(resmessage) > 0 and Print121Frame:
            print("Frame 2D message :", resmessage)
    if frame[2] == 0x3c:
        logmsg="132: "
        if Print132Frame:
            print("Frame 3C / 132   : " + tohex(payload))
            print("Record " + devid)
        devid = sourcemac + '-' + b2ib(payload[0:2])
        pbdc = conn.cursor()
        pbdc.execute('select name from doorpetmapping left join animals using (petid) where devicepetid=(?)', ([devid]))
        pbd = pbdc.fetchone()
        if (pbd):
            #I'm not sure if this is right or not, but there are very weird values sometimes for in / out
            direction=list(hb(payload[6]))
            msg = pbd[0] + " went " + fDirection[int(direction[1])] + " in " + direction[0] + " seconds " + hb(payload[6])
            logmsg += msg
            if Print132Frame:
                print(msg)
        else:
            logmsg += tohex(payload)
#                return pbd[0]
#            else:
#                pbdc.execute("INSERT OR IGNORE INTO doorpetmapping values((?), (?), (?)) ", ("0", device, int(id)))
#                conn.commit()
#                return "Unknown"

    return "Received frame at: " + timestamp + " from: " + sourcemac + " to: " + destinationmac + " " + logmsg
