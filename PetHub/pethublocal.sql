BEGIN TRANSACTION;
DROP TABLE devices;
CREATE TABLE devices(mac_address TEXT, product_id INTEGER, name TEXT, serial_number TEXT, battery TEXT, device_rssi TEXT, hub_rssi TEXT, version BLOB);
INSERT INTO devices VALUES('MACADDRESS',1,'Home','SN','','','','');
INSERT INTO devices VALUES('MACADDRESS',4,'Feeder','SN','','','','');
INSERT INTO devices VALUES('MACADDRESS',3,'PetDoor','','','','','');

DROP TABLE doors;
CREATE TABLE doors(mac_address TEXT, curfewenabled INTEGER, lock_time TEXT, unlock_time TEXT, lockingmode INTEGER );
INSERT INTO doors VALUES('DOORMAC',0,'22:','07:00',0);

DROP TABLE feeders;
CREATE TABLE feeders(mac_address TEXT, bowltarget1 INTEGER, bowltarget2 INTEGER, close_delay INTEGER );
INSERT INTO feeders VALUES('FEEDERMAC',30,30,0);

DROP TABLE tagmap;
CREATE TABLE tagmap(mac_address TEXT, deviceindex INTEGER, tag TEXT, UNIQUE (mac_address, deviceindex) ON CONFLICT REPLACE );
INSERT INTO tagmap VALUES('DOORMAC',0,'TAG1');
INSERT INTO tagmap VALUES('DOORMAC',1,'TAG2');

DROP TABLE pets;
CREATE TABLE pets(tag TEXT, name TEXT );
INSERT INTO pets VALUES('TAG1','NAME');
INSERT INTO pets VALUES('TAG2','NAME');

DROP TABLE petstate;
CREATE TABLE petstate(tag TEXT, mac_address TEXT, timestamp TEXT, state BLOB );

DROP TABLE devicestate;
CREATE TABLE devicestate(mac_address TEXT, offset INTEGER, data BLOB, UNIQUE (mac_address, offset) ON CONFLICT REPLACE );

COMMIT;

