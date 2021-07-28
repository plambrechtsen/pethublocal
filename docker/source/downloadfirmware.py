#!/usr/bin/env python3
"""
   Download Firmware from SurePet

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

import os
import pathlib
import logging
import requests
import sys
import re
from datetime import datetime

#Logging level
LogLevel = logging.DEBUG

#This could be useful in the future ... just saying. ;)
bootloader='1.177' #Bootloader value sent by hub during firmware update
directory=''
#directory='firmware/'
surehubio='hub.api.surehub.io' #Replace with IP address if you have pointed this locally

# Setup Logging framework to log to console without timestamps and log to file with timestamps
log = logging.getLogger('')
log.setLevel(LogLevel)
ch = logging.StreamHandler(sys.stdout)
log.addHandler(ch)
pathlib.Path("log").mkdir(exist_ok=True)
fh = logging.FileHandler(directory + 'log/downloadfirmware-{:%Y-%m-%d}.log'.format(datetime.now()))
logformat = logging.Formatter('%(asctime)s - [%(levelname)-5.5s] - %(message)s')
fh.setFormatter(logformat)
log.addHandler(fh)

def dlfirmware(serialnumber,page):
    page=str(page)
    url = 'http://'+surehubio+'/api/firmware'
    headers = {'User-Agent': 'curl/7.22.0 (x86_64-pc-linux-gnu) libcurl/7.22.0 OpenSSL/1.0.1 zlib/1.2.3.4 libidn/1.23 librtmp/2.3', 'Content-Type':'application/x-www-form-urlencoded', 'Host':'hub.api.surehub.io', 'Connection': None, 'Accept-Encoding': None }
    postdata='serial_number='+serialnumber+'&page='+page+'&bootloader_version='+bootloader
    response = requests.post(url, data = postdata, headers=headers, verify=False)
    response.raise_for_status() # ensure we notice bad responses
    payload=response.content
    filename=directory+serialnumber+'-'+bootloader+'-'+str(page).zfill(2)+'.bin'
    file = open(filename, "wb")
    file.write(payload)
    file.close()

if len(sys.argv) > 1:
    if re.match('^H[0-9]{3}-[0-9]{7}$',sys.argv[1]):
        firmware=directory+sys.argv[1]+'-'+bootloader+'-00.bin'
        if not os.path.isfile(firmware):
            #Download header firmware file
            log.info("Download first firmware record")
            dlfirmware(sys.argv[1],0)
            with open(firmware, "rb") as f:
                #Read the header
                byte = f.read(36).decode("utf-8").split()
                #Record count in hex
                recordcount=int(byte[2], 16)+6
                log.info("Count: " + str(recordcount))
                for counter in range(1,recordcount):
                    log.info("Download remaining record: " + str(counter))
                    dlfirmware(sys.argv[1],counter)
        else:
            log.info("Firmware already downloaded " + firmware)
    else:
        log.info('Invalid Serial Number passed, make sure it is H0xx-xxxxxxx')
else:
    log.info('No Serial number passed')
