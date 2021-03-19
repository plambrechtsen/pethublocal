BEGIN TRANSACTION;
DROP TABLE devices;
CREATE TABLE devices(devicemac STRING PRIMARY KEY, devicename STRING, deviceid NUMERIC, devicetype NUMERIC, uptime NUMERIC);
INSERT INTO devices VALUES('messages','Hub',33,1,0);

DROP TABLE animals;
CREATE TABLE animals(petid NUMERIC PRIMARY KEY, microchip TEXT, name STRING, inorout STRING, inoutdate STRING, lastfeddate STRING, laststatedate STRING );

DROP TABLE doorpetmapping;
CREATE TABLE doorpetmapping(devicepetid STRING PRIMARY KEY, petid NUMERIC, device STRING, doorpetid NUMERIC );
COMMIT;

