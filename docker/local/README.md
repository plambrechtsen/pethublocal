# Docker Compose

This is a fully self contained docker compose script which builds a web server, mqtt and listener to mqtt. If you have not downloaded the credentials then the app will download it and save it locally.

For this to work you need to update your local DNS server to respond with a different IP address for:

```
hub.api.surehub.io
```
Many routers support having local DNS entries or if you are running OpenWRT it is easy, however ISP suppled routers do not support this feature.

If you can't update your DNS then there is no point proceeding from here and you need to buy a new router or add a second router running OpenWRT to replace the DNS entry to point locally.

Then when the hub boots I re-write the creds to point to the same DNS name for the MQTT endpoint. Have a look in the output/web creds file, the original file is stored there too.

Edit the docker-compose.yml, and adjust the IP addresses if you want to bind to a second IP address rather than all IPs, as you will need a listener on port 443 for the hub and 8883 for MQTT.

```
    ports:
      - "192.168.20.241:1884:1883"
      - "192.168.20.241:8883:8883"
```
Adjust or remove the IP if needed, then start it.

```
docker-compose up --build
```

If you use tmux (like screen but better) then you can have it running in the background.

Now you should get console messages of it starting

```
Creating local_mqtt ... done
Creating local_web  ... done
Creating local_msgs ... done
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
```

web - is where the creds get downloaded and cached
mqtt - the logs from the mqtt server
msgs - A log of the messages
