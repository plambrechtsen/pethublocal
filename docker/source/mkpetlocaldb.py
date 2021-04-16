import json, sqlite3, os, asyncio
import surepy.client as spc
import surepy.const as spco

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
    if data := sp.resources[spco.MESTART_RESOURCE].get("data", {}):
        #Dump response
        if PrintDebug:
            print(data)
        # Create pet hub local tables
        conn = create_connection('pethublocal.db')
        if conn is not None:
            sqlcmd(conn, "DROP TABLE devices;")
            sqlcmd(conn, "DROP TABLE hubs;")
            sqlcmd(conn, "DROP TABLE doors;")
            sqlcmd(conn, "DROP TABLE feeders;")
            sqlcmd(conn, "DROP TABLE tagmap;")
            sqlcmd(conn, "DROP TABLE pets;")
            sqlcmd(conn, "DROP TABLE petstate;")
            sqlcmd(conn, "CREATE TABLE devices(mac_address TEXT, product_id INTEGER, name TEXT, serial_number TEXT, battery TEXT, device_rssi TEXT, hub_rssi TEXT, version BLOB);")
            sqlcmd(conn, "CREATE TABLE hubs(mac_address TEXT, led_mode INTEGER, pairing_mode INTEGER );")
            sqlcmd(conn, "CREATE TABLE doors(mac_address TEXT, curfewenabled INTEGER, lock_time TEXT, unlock_time TEXT, lockingmode INTEGER, custommode TEXT);")
            sqlcmd(conn, "CREATE TABLE feeders(mac_address TEXT, bowltype INTEGER, bowl1 INTEGER, bowl2 INTEGER, bowltarget1 INTEGER, bowltarget2 INTEGER, close_delay INTEGER );")
            sqlcmd(conn, "CREATE TABLE tagmap(mac_address TEXT, deviceindex INTEGER, tag TEXT, UNIQUE (mac_address, deviceindex) ON CONFLICT REPLACE );")
            sqlcmd(conn, "CREATE TABLE pets(tag TEXT, name TEXT, species INTEGER );")
            sqlcmd(conn, "CREATE TABLE petstate(tag TEXT, mac_address TEXT, timestamp TEXT, state BLOB );")
            sqlcmd(conn, "CREATE TABLE devicestate(mac_address TEXT, offset INTEGER, length INTEGER, data TEXT, UNIQUE (mac_address, offset, length) ON CONFLICT REPLACE );")
        else:
            print("Error! cannot create the database connection.")
            exit(1)

        tags = data['tags']
        devices = data['devices']

        c = conn.cursor()

        for pets in data['pets']:
            tagid = pets['tag_id']
            name = pets['name']
            if 'species_id' in pets:
                species = pets['species_id']
            else:
                species = 0
            tag = [x for x in tags if x["id"]==tagid][0]['tag']
            c.execute("INSERT INTO pets values((?), (?), (?));", (tag, name, species))
            conn.commit()

            if 'status' in pets:
                if 'activity' in pets['status']:
                    timestamp = pets['status']['activity']['since']
                    device_id = pets['status']['activity']['device_id']
                    mac_address = [x for x in devices if x["id"]==device_id][0]['mac_address']
                    state = pets['status']['activity']['where']

                    c.execute("INSERT INTO petstate values((?), (?), (?), (?));", (tag, mac_address, timestamp, state))
                    conn.commit()

                if 'feeding' in pets['status']:
                    timestamp = pets['status']['feeding']['at']
                    device_id = pets['status']['feeding']['device_id']
                    mac_address = [x for x in devices if x["id"]==device_id][0]['mac_address']
                    state = json.dumps(pets['status']['feeding']['change'])

                    c.execute("INSERT INTO petstate values((?), (?), (?), (?));", (tag, mac_address, timestamp, state))
                    conn.commit()

        for device in data['devices']:

            deviceid = device['id']
            product_id = device['product_id']
            name = device['name']
            if 'serial_number' in device:
                serial_number = device['serial_number']
            else:
                serial_number = ""
            mac_address = device['mac_address']
            if 'battery' in device['status']:
                battery = device['status']['battery']
            else:
                battery = ""
            if 'signal' in device['status']:
                device_rssi = str(device['status']['signal']['device_rssi'])
                hub_rssi = str(device['status']['signal']['hub_rssi'])
            else:
                device_rssi = ""
                hub_rssi = ""
            version = json.dumps(device['status']['version'])
            c.execute("INSERT INTO devices values((?), (?), (?), (?), (?), (?), (?), (?));", (mac_address, product_id, name, serial_number, battery, device_rssi, hub_rssi, version))
            conn.commit()

            if product_id == 1: #Hub
                if 'led_mode' in device['control']:
                    led_mode = device['control']['led_mode']
                    pairing_mode = device['control']['pairing_mode']
                else:
                    led_mode = 0
                    pairing_mode = 0
                c.execute("INSERT INTO hubs values((?), (?), (?));", (mac_address, led_mode, pairing_mode))
                conn.commit()

            if product_id == 3: #Pet Door
                #Curfew mode
                if 'enabled' in device['control']['curfew']:
                    curfewenabled = device['control']['curfew']['enabled']
                    lock_time = device['control']['curfew']['lock_time']
                    unlock_time = device['control']['curfew']['unlock_time']
                else:
                    if 'curfew' in device['status']:
                        curfewenabled = device['status']['curfew']['enabled']
                        lock_time = device['status']['curfew']['lock_time']
                        unlock_time = device['status']['curfew']['unlock_time']
                    else:
                        curfewenabled = 0
                        lock_time = ""
                        unlock_time = ""

                #Locking mode
                if 'locking' in device['control']:
                    lockingmode = device['control']['locking']
                else:
                    if 'locking' in device['status']:
                        lockingmode = device['status']['locking']['mode']
                    else:
                        lockingmode = 0
                c.execute("INSERT INTO doors values((?), (?), (?), (?), (?), '000000');", (mac_address, curfewenabled, lock_time, unlock_time, lockingmode))
                conn.commit()

            if product_id == 4: #Feeder
                if bowltype == 4:
                    #Two bowls
                    bowltarget1 = device['control']['bowls']['settings'][0]['target']
                    bowltarget2 = device['control']['bowls']['settings'][1]['target']
                    bowltype = 2
                elif bowltype == 1:
                    #One bowl
                    bowltarget1 = device['control']['bowls']['settings'][0]['target']
                    bowltarget2 = 0
                    bowltype = 1
                else:
                    #Unknown value
                    bowltarget1 = 0
                    bowltarget2 = 0
                    bowltype = 0
                close_delay = device['control']['lid']['close_delay']
                c.execute("INSERT INTO feeders values((?), (?), 0, 0, (?), (?), (?));", (mac_address, bowltype, bowltarget1, bowltarget2, close_delay))
                conn.commit()

            if product_id == 6: #Cat Door
                if 'enabled' in device['control']['curfew']:
                    curfewenabled = device['control']['curfew']['enabled']
                    lock_time = device['control']['curfew']['lock_time']
                    unlock_time = device['control']['curfew']['unlock_time']
                else:
                    curfewenabled = 0
                    lock_time = ""
                    unlock_time = ""

                #Locking mode
                if 'locking' in device['control']:
                    lockingmode = device['control']['locking']
                else:
                    if 'locking' in device['status']:
                        lockingmode = device['status']['locking']['mode']
                    else:
                        lockingmode = 0
                c.execute("INSERT INTO doors values((?), (?), (?), (?), (?), '000000');", (mac_address, curfewenabled, lock_time, unlock_time, lockingmode))
                conn.commit()

            if 'tags' in device:
                for tag in device['tags']:
                    tagindex = tag['index']
                    tagid = tag['id']
                    tag = str([x for x in tags if x["id"]==tagid][0]['tag'])
                    c.execute("INSERT INTO tagmap values((?), (?), (?) );", (mac_address, tagindex, tag))
                    conn.commit()
        print("pethublocal.db created/updated")
    await sp.close_session()

if __name__ == '__main__':
    asyncio.run(petlocaldb())
