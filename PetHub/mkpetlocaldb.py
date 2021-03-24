import json, sqlite3
from sqlite3 import Error

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

conn = create_connection('pethublocal.db')

# Create pet hub local tables
if conn is not None:
    sqlcmd(conn, "DROP TABLE devices;")
    sqlcmd(conn, "DROP TABLE doors;")
    sqlcmd(conn, "DROP TABLE feeders;")
    sqlcmd(conn, "DROP TABLE tagmap;")
    sqlcmd(conn, "DROP TABLE pets;")
    sqlcmd(conn, "DROP TABLE petstate;")
#    sqlcmd(conn, "CREATE TABLE devices(deviceid INTEGER, product_id INTEGER, name TEXT, serial_number TEXT, mac_address TEXT, battery INTEGER, device_rssi INTEGER, hub_rssi INTEGER, version BLOB);")
    sqlcmd(conn, "CREATE TABLE devices(mac_address TEXT, product_id INTEGER, name TEXT, serial_number TEXT, battery TEXT, device_rssi TEXT, hub_rssi TEXT, version BLOB);")
#    sqlcmd(conn, "CREATE TABLE doors(deviceid INTEGER, curfewenabled INTEGER, lock_time TEXT, unlock_time TEXT, lockingmode INTEGER );")
    sqlcmd(conn, "CREATE TABLE doors(mac_address TEXT, curfewenabled INTEGER, lock_time TEXT, unlock_time TEXT, lockingmode INTEGER );")
#    sqlcmd(conn, "CREATE TABLE feeders(deviceid INTEGER, bowltarget1 INTEGER, bowltarget2 INTEGER, close_delay INTEGER );")
    sqlcmd(conn, "CREATE TABLE feeders(mac_address TEXT, bowltarget1 INTEGER, bowltarget2 INTEGER, close_delay INTEGER );")
#    sqlcmd(conn, "CREATE TABLE tagmap(deviceid INTEGER, deviceindex INTEGER, tagid INTEGER, UNIQUE (deviceid, deviceindex) ON CONFLICT REPLACE );")
    sqlcmd(conn, "CREATE TABLE tagmap(mac_address TEXT, deviceindex INTEGER, tag TEXT, UNIQUE (mac_address, deviceindex) ON CONFLICT REPLACE );")
#    sqlcmd(conn, "CREATE TABLE pets(tagid INTEGER, name TEXT, tag TEXT );")
    sqlcmd(conn, "CREATE TABLE pets(tag TEXT, name TEXT );")
#    sqlcmd(conn, "CREATE TABLE petstate(tagid INTEGER, deviceid INTEGER, state TEXT, timestamp TEXT );")
    sqlcmd(conn, "CREATE TABLE petstate(tag TEXT, mac_address TEXT, timestamp TEXT, state BLOB );")
    sqlcmd(conn, "CREATE TABLE devicestate(mac_address TEXT, offset INTEGER, data BLOB, UNIQUE (mac_address, offset) ON CONFLICT REPLACE );")
else:
    print("Error! cannot create the database connection.")

with open('start.json') as json_file:
    data = json.load(json_file)

    tags = data['data']['tags']
    devices = data['data']['devices']
#    print(tags)

    c = conn.cursor()

    for pets in data['data']['pets']:
        tagid = pets['tag_id']
        name = pets['name']
        tag = [x for x in tags if x["id"]==tagid][0]['tag']

#        c.execute("INSERT INTO pets values((?), (?), (?));", (tagid, name, tag))
        c.execute("INSERT INTO pets values((?), (?) );", (tag, name))
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

    for device in data['data']['devices']:
#        print(device)

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

#        c.execute("INSERT INTO devices values((?), (?), (?), (?), (?), (?), (?), (?), (?));", (deviceid, product_id, name, serial_number, mac_address, battery, device_rssi, hub_rssi, version))
        c.execute("INSERT INTO devices values((?), (?), (?), (?), (?), (?), (?), (?));", (mac_address, product_id, name, serial_number, battery, device_rssi, hub_rssi, version))
        conn.commit()

        if product_id == 3: #Pet Door
            if 'enabled' in device['control']['curfew']:
                curfewenabled = device['control']['curfew']['enabled']
                lock_time = device['control']['curfew']['lock_time']
                unlock_time = device['control']['curfew']['unlock_time']
            else:
                curfewenabled = 0
                lock_time = ""
                unlock_time = ""

            lockingmode = device['control']['locking']
#            c.execute("INSERT INTO doors values((?), (?), (?), (?), (?));", (deviceid, curfewenabled, lock_time, unlock_time, lockingmode))
            c.execute("INSERT INTO doors values((?), (?), (?), (?), (?));", (mac_address, curfewenabled, lock_time, unlock_time, lockingmode))
            conn.commit()

        if product_id == 4: #Feeder
            bowltarget1 = device['control']['bowls']['settings'][0]['target']
            if device['control']['bowls']['type'] == 4:
                #Two bowls
                bowltarget2 = device['control']['bowls']['settings'][1]['target']
            elif device['control']['bowls']['type'] == 1:
                #One bowls
                bowltarget2 = 0
            else:
                #Unknown value
                bowltarget2 = 0
            close_delay = device['control']['lid']['close_delay']
#            c.execute("INSERT INTO feeders values((?), (?), (?), (?));", (deviceid, bowltarget1, bowltarget2, close_delay))
            c.execute("INSERT INTO feeders values((?), (?), (?), (?));", (mac_address, bowltarget1, bowltarget2, close_delay))
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
            lockingmode = device['control']['locking']
#            c.execute("INSERT INTO doors values((?), (?), (?), (?), (?));", (deviceid, curfewenabled, lock_time, unlock_time, lockingmode))
            c.execute("INSERT INTO doors values((?), (?), (?), (?), (?));", (mac_address, curfewenabled, lock_time, unlock_time, lockingmode))
            conn.commit()

        if 'tags' in device:
            for tag in device['tags']:
                tagindex = tag['index']
                tagid = tag['id']
                tag = str([x for x in tags if x["id"]==tagid][0]['tag'])

#                c.execute("INSERT INTO tagmap values((?), (?), (?) );", (deviceid, tagindex, tagid))
                c.execute("INSERT INTO tagmap values((?), (?), (?) );", (mac_address, tagindex, tag))
                conn.commit()

print("pethublocal.db created/updated")
