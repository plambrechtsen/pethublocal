# Docker Compose

This is a fully self contained docker compose script which builds a web server, mqtt, listener to mqtt to log every message... and most  importantly pethub which listens to messages from the hub and then translates them into standard messages and vice versa.

This is a work in progress and I am finally tying this all together as the pethub will also support control messages sent from Home Assistant or similar and then send to the hub appropriate topic.

# How it works
Below I document how the current and altered boot process works.

## Standard Hub boot process

As per the below standard flow it is:
- Query DNS for hub.api.surehub.io
- Connect to HTTPS Cloud service to retrieve credentials and client certificate
- Connect to AWS IoT MQTT with client certificate 

![Standard-SurePet](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/plambrechtsen/pethublocal/main/docs/SurePet.iuml)

## Pet Hub Local Hub altered boot process

As per the below the altered flow is:
- Query DNS but get the response for hub.api.surehub.io to point to the local docker container or webserver
- Local Web on first connection proxies the request to the Cloud Web to retrieve the Credentials file
- Alters credentials file to point to local MQTT endpoint and have a consistent topic name rather than UUID value and saves original and new credentials file locally
- Responds to Hub with altered credentials file
- Connect to local MQTT with client certificate but it doesn't validate the certificate

![PetHubLocal](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/plambrechtsen/pethublocal/main/docs/Pethublocal.iuml)


# Setup Process
Below are the steps required to be followed to get Pet Hub Local working within your environment. It uses Home Assistant MQTT Discovery so there should be no configuration required within Home Assistant and the entities for the Hub and any attached devices should appear automagically.

## Step 1 - Update your local DNS
For pethublocal to work you need to update your local DNS server to respond with a different IP address for:
```
hub.api.surehub.io
```
Many routers support having local DNS entries or if you are running OpenWRT it is easy, however ISP suppled routers do not support this feature.

If you can't update your DNS then there is no point proceeding from here and you need to buy a new router or add a second router running OpenWRT to replace the DNS entry to point locally.

Then when the hub boots I re-write the creds to point to the same DNS name for the MQTT endpoint and update the topic path to be `pethublocal`.  Have a look in the `output/web/H0xx-xx.bin` creds file, the original file is stored there too.

## Step 2 - Create pethublocal.db database
To begin with you need to export out the results from the Start API call into the pethublocal.db sqlite database that is used to reference the devices and pets. Reusing surepy: https://github.com/benleb/surepy so you need to make sure the library is installed:
You need to be using Python 3.8 or higher to use mkpetlocaldb, i might consolidate this into a separate docker container to make this simpler.
Update the `/docker/source/mkpetlocaldb.py` with your portal credentials in the user and password. Then run it.
```
cd /docker/source
pip3 install surepy
edit mkpetlocaldb.py
python3 mkpetlocaldb.py
```
That uses surepy to make the `/me/start` api call and create a sqlite3. Check out the database using sqlite3:
```
sqlite3 pethublocal.db
```

## Step 3 - Review pethub source files 
The database, plus surepetpacket need to be in the `docker/source` directory for the docker container pethub to work. So please check and make sure the database has been created and update as required.

## Step 4 - Update the config.ini

Edit the `/docker/config.ini`, and adjust the Home Assistant IP addresses for the upstream MQTT instance you want to connect to.

 ```
#Pet Hub Local Environment Configuration File

#Sure Pet Cloud Login to download configuration
CLOUDUSERNAME=**emailaddress**
CLOUDPASSWORD=securelongpassword

#Home Assistant MQTT Upstream configuration
HAMQTTIP=192.168.1.250
#HAMQTTUSERNAME=user
#HAMQTTPASSWORD=pass

#Bind IP Address if you want to bind to a specific IP, you need to have a : at the end of the IP
#BINDIP=192.168.1.251:
```

Adjust where appropriate.

## Step 4 - Start docker compose
Now you have everything configured you should be good to start the stack.
```
cd docker
docker-compose up --build
```

If you use tmux (like screen but better) then you can have it running in the background.

Now you should get console messages of it starting

```
Creating local_mqtt ... done
Creating local_web  ... done
Creating local_msgs ... done
Creating local_pethub ... done
Attaching to local_web, local_mqtt, local_msgs
mqtt_1  | 1615575327: Warning: Mosquitto should not be run as root/administrator.
web_1   |  * Serving Flask app "app" (lazy loading)
web_1   |  * Environment: production
web_1   |    WARNING: This is a development server. Do not use it in a production deployment.
web_1   |    Use a production WSGI server instead.
web_1   |  * Debug mode: off
mqtt_1  | 1615575331: New connection from 172.24.0.3 on port 1883.
mqtt_1  | 1615575331: New client connected from 172.24.0.3 as mosq-YtRDDMDZecdyz4Wz7W (p2, c1, k60).
mqtt_1  | 1615575331: mosq-YtRDDMDZecdyz4Wz7W 0 pethublocal/#
web_1   |  * Running on https://0.0.0.0:443/ (Press CTRL+C to quit)
mqtt_1  | 1615575335: New connection from 192.168.1.129 on port 1883.
mqtt_1  | 1615575337: New client connected from 192.168.1.129 as PetHubTest (p2, c1, k15).
```
And you will see under the output subfolder there is:
```
web
mqtt
msgs
pethub
```

`web` - is where the creds get downloaded and cached
`mqtt` - the logs from the mqtt server
`msgs` - A log of the messages
`pethub` - Listens to hub topic and creates local messages.
