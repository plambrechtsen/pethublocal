#!/usr/bin/env python3

# Build pethublocal.db sqlite database from API calls to surepet cloud service or using a local copy of it via command line.

import json, sqlite3, os, sys, asyncio, pathlib
import surepy.client as spc
import surepy.const as spco
from datetime import datetime
from box import Box

from sqlite3 import Error

#Debugging mesages
PrintDebug = True #Print debugging messages

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def sqlcmd(conn, sql_cmd):
    try:
        c = conn.cursor()
        c.execute(sql_cmd)
        conn.commit()
    except Error as e:
        print(e)

def sqlcmdvar(conn, sql_cmd, values):
    try:
        c = conn.cursor()
        c.execute(sql_cmd, values)
        conn.commit()
    except Error as e:
        print(e)

def makedb(data):
    if PrintDebug:
        print("Dump of full Start API Message payload")
        print(data)
        #Don't write the log file if we have loaded it via command line
        if len(sys.argv) < 2:
            sttime = datetime.now().strftime('%Y%m%d_%H%M%S')
            f = open("start-"+sttime+".json", "w")
            f.write(json.dumps(data))
            f.close()
    # Create pet hub local tables
    conn = create_connection('pethublocal.db')

    #Import pethublocal.sql file to database
    if conn is not None:
        cursor = conn.cursor()
        pethublocal_file = open("pethublocal.sql")
        cursor.executescript(pethublocal_file.read())
    else:
        print("Error! cannot create the database connection.")
        exit(1)

    #If someone decides to save and pass the full "start.json" message there is a data top level element that isn't expected.
    if 'data' in data:
        data = data.data

    if {'tags','devices','pets'} <= set(data):
    
        tags = data.tags
        devices = data.devices
        pets = data.pets

        for pet in pets:
            if PrintDebug:
                print("Adding Pets")
            tagid = pet.tag_id
            name = pet.name
            if 'species_id' in pet:
                species = pet.species_id
            else:
                species = 0
            tag = [x for x in tags if x["id"]==tagid][0].tag
            if PrintDebug:
                print('Pets: Tag = {0}, Name = {1}, Species={2}'.format(tag, name, species))
            sqlcmdvar(conn, "INSERT INTO pets values((?), (?), (?));", (tag, name, species))

            if 'status' in pet:
                if 'activity' in pet.status:
                    timestamp = pet.status.activity.since
                    if 'device_id' in pet.status.activity:
                        device_id = pet.status.activity.device_id
                        mac_address = [x for x in devices if x["id"]==device_id][0].mac_address
                    else:
                        device_id = ''
                        mac_address = ''
                    state = pet.status.activity.where
                    if PrintDebug:
                        print('PetState for Doors: Tag = {0}, mac_address = {1}, timestamp={2}, state={3}'.format(tag, mac_address, timestamp, state))
                    sqlcmdvar(conn, "INSERT INTO petstate values((?), (?), (?), (?));", (tag, mac_address, timestamp, state))

                #Feeders
                if 'feeding' in pet.status:
                    timestamp = pet.status.feeding.at
                    if 'device_id' in pet.status.feeding:
                        device_id = pet.status.feeding.device_id
                        mac_address = [x for x in devices if x["id"]==device_id][0].mac_address
                    else:
                        device_id = ''
                        mac_address = ''
                    state = json.dumps(pet.status.feeding.change)

                    if PrintDebug:
                        print('PetState for Feeders: Tag = {0}, mac_address = {1}, timestamp={2}, state={3}'.format(tag, mac_address, timestamp, state))
                    sqlcmdvar(conn, "INSERT INTO petstate values((?), (?), (?), (?));", (tag, mac_address, timestamp, state))

                #Felaqua
                if 'drinking' in pet.status:
                    timestamp = pet.status.drinking.at
                    if 'device_id' in pet.status.drinking:
                        device_id = pet.status.drinking.device_id
                        mac_address = [x for x in devices if x["id"]==device_id][0].mac_address
                    else:
                        device_id = ''
                        mac_address = ''
                    state = json.dumps(pet.status.feeding.change)

                    if PrintDebug:
                        print('PetState for drinking: Tag = {0}, mac_address = {1}, timestamp={2}, state={3}'.format(tag, mac_address, timestamp, state))
                    sqlcmdvar(conn, "INSERT INTO petstate values((?), (?), (?), (?));", (tag, mac_address, timestamp, state))

        for device in data.devices:
            if PrintDebug:
                print("Adding Devices")

            deviceid = device.id
            product_id = device.product_id
            if 'name' in device:
                name = device.name
            elif 'serial_number' in device:
                name = device.serial_number
            else:
                name = device.mac_address
            if 'serial_number' in device:
                serial_number = device.serial_number
            else:
                serial_number = ""
            mac_address = device.mac_address
            if 'battery' in device.status:
                battery = device.status.battery
            else:
                battery = ""
            if 'signal' in device.status:
                device_rssi = str(device.status.signal.device_rssi)
                hub_rssi = str(device.status.signal.hub_rssi)
            else:
                device_rssi = ""
                hub_rssi = ""
            version = json.dumps(device.status.version)
            if PrintDebug:
                print('Devices: mac_address = {0}, product_id={1}, name={2}, serial_number={3}, battery={4}, device_rssi={5}, hub_rssi={6}, version={7}'.format(mac_address, product_id, name, serial_number, battery, device_rssi, hub_rssi, version))
            sqlcmdvar(conn, "INSERT INTO devices values((?), (?), (?), (?), (?), (?), (?), (?));", (mac_address, product_id, name, serial_number, battery, device_rssi, hub_rssi, version))

            if product_id == 1: #Hub
                if 'led_mode' in device.control:
                    led_mode = device.control.led_mode
                    pairing_mode = device.control.pairing_mode
                else:
                    led_mode = 0
                    pairing_mode = 0
                if 'online' in device.status:
                    state = device.status.online
                else:
                    state = 0
                print("State ",state)
                if PrintDebug:
                    print('Hubs: mac_address = {0}, led_mode={1}, pairing_mode={2}, state={3}, uptime=0'.format(mac_address, led_mode, pairing_mode, state))
                sqlcmdvar(conn, "INSERT INTO hubs values((?), (?), (?), (?), 0);", (mac_address, led_mode, pairing_mode, state))

            if product_id == 3: #Pet Door
                #Curfew mode
                if 'enabled' in device.control.curfew:
                    curfewenabled = device.control.curfew.enabled
                    curfews = device.control.curfew.lock_time + "-" + device.control.curfew.unlock_time
                else:
                    curfewenabled = False
                    curfews = ""

                #Locking mode
                if 'locking' in device.control:
                    lockingmode = device.control.locking
                else:
                    if 'locking' in device.status:
                        lockingmode = device.status.locking.mode
                    else:
                        lockingmode = 0
                if PrintDebug:
                    print('Pet Doors: mac_address = {0}, lockingmode={1}, curfewenabled={2}, curfews={3} '.format(mac_address, lockingmode, curfewenabled, curfews ))
                sqlcmdvar(conn, "INSERT INTO doors values((?), (?), (?), (?), '000000');", (mac_address,lockingmode, curfewenabled, curfews ))

            if product_id == 4: #Feeder
                bowltype = device.control.bowls.type
                if bowltype == 4:
                    #Two bowls
                    bowltarget1 = device.control.bowls.settings[0].target
                    bowltarget2 = device.control.bowls.settings[1].target
                    bowltype = 2
                elif bowltype == 1:
                    #One bowl
                    bowltarget1 = device.control.bowls.settings[0].target
                    bowltarget2 = 0
                    bowltype = 1
                else:
                    #Unknown value
                    bowltarget1 = 0
                    bowltarget2 = 0
                    bowltype = 0
                close_delay = device.control.lid.close_delay
                if PrintDebug:
                    print('Feeders: mac_address = {0}, bowltype={1}, bowl1=, bowl2=, bowltarget1={2}, bowltarget2={3}, close_delay={4}'.format(mac_address, bowltype, bowltarget1, bowltarget2, close_delay))
                sqlcmdvar(conn, "INSERT INTO feeders values((?), (?), 0, 0, (?), (?), (?));", (mac_address, bowltype, bowltarget1, bowltarget2, close_delay))
                sqlcmdvar(conn, "INSERT INTO devicecounter values((?), 0, 0);", [mac_address])

            if product_id == 6: #Cat Door
                #Curfew mode
                curfews = ""
                if len(device.control.curfew) > 0:
                    curfewenabled = True
                    #Loop through all the curfews and create a single string "hh:mm-hh:mm,hh:mm-hh:mm" for each enabled curfew where the start end is - deimited and each curfew is comma separated
                    for curfew in device.control.curfew:
                        if curfew.enabled:
                            curfews += curfew.lock_time + "-" + curfew.unlock_time
                            #Add a comma delimiter unless it's the last entry
                            if curfew != device.control.curfew[-1]:
                                curfews += ","
                else:
                    curfewenabled = False

                #Locking mode
                if 'locking' in device.control:
                    lockingmode = device.control.locking
                else:
                    if 'locking' in device.status:
                        lockingmode = device.status.locking.mode
                    else:
                        lockingmode = 0
                if PrintDebug:
                    print('Pet Doors: mac_address = {0}, lockingmode={1}, curfewenabled={2}, curfews={3} '.format(mac_address, lockingmode, curfewenabled, curfews ))
                sqlcmdvar(conn, "INSERT INTO doors values((?), (?), (?), (?), '000000');", (mac_address,lockingmode, curfewenabled, curfews ))
                sqlcmdvar(conn, "INSERT INTO devicecounter values((?), 0, 0);", [mac_address])

            if product_id == 8: #Water bowl - Felaqua
                #Not sure if this is even useful, but it seems to be the only value that comes in the device outside the standard ones.
                if 'tare' in device.control:
                    bowltarget1 = device.control.tare
                else:
                    bowltarget1 = 0
                if PrintDebug:
                    print('Felaqua: mac_address = {0}, bowltarget1={1}'.format(mac_address, bowltarget1))
                sqlcmdvar(conn, "INSERT INTO feeders values((?), 0, 0, 0, (?), 0, 0);", (mac_address, bowltarget1))
                sqlcmdvar(conn, "INSERT INTO devicecounter values((?), 0, 0);", [mac_address])

            if 'tags' in device:
                for tag in device.tags:
                    tagindex = tag.index
                    tagid = tag.id
                    #Cat flap and feeders have a profile, On cat flap profile = 3 = inside only
                    if 'profile' in tag:
                        profile=tag.profile
                    else:
                        profile=0
                    tag = str([x for x in tags if x["id"]==tagid][0].tag)
                    if PrintDebug:
                        print('Tagmap: mac_address = {0}, tagindex={1}, tag={2} profile={3}'.format(mac_address, tagindex, tag, profile))
                    sqlcmdvar(conn, "INSERT INTO tagmap values((?), (?), (?), (?));", (mac_address, tagindex, tag, profile))
        print("pethublocal.db created/updated")
    else:
        print("Corrupted input file, have you removed the top level data: element?")

async def petlocaldb():
    if os.environ.get('CLOUDUSERNAME') is not None:
        user=os.environ.get('CLOUDUSERNAME')
    else:
        user="**Update email address for cloud here**"
    if "**" in user:
        print("Username has not been set, either set CLOUDUSERNAME environment or update file")
        exit(1)
    if os.environ.get('CLOUDPASSWORD') is not None:
        password=os.environ.get('CLOUDPASSWORD')
    else:
        password="**securelongpassword**"
    if "**" in password:
        print("Password has not been set, either set CLOUDPASSWORD environment or update file")
        exit(1)
    sp = spc.SureAPIClient(email=user, password=password)
    await sp.call(method="GET", resource=spco.MESTART_RESOURCE)
    data = Box(sp.resources[spco.MESTART_RESOURCE].get("data", {}))
    if data.devices:
        makedb(data)
        #Dump response
#    await sp.close_session()

#Check if a command line parameter was passed, and then it's a json file we need to load rather than talking to the cloud.
if len(sys.argv) >= 2:
    if pathlib.Path(sys.argv[1]).exists():
        makedb(Box.from_json(filename=sys.argv[1]))
else:
    asyncio.run(petlocaldb())

