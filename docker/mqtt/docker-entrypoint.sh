#!/bin/ash

# Create conf directory if it doesn't exist 
mkdir -p /mosquitto/conf
mkdir -p /mosquitto/db
mkdir -p /mosquitto/logs
[[ ! -f /mosquitto/conf/mosquitto.conf ]] && cp /default/* /mosquitto/conf

if grep "HAMQTTIP" /mosquitto/conf/mosquitto.conf>/dev/null; then
   sed -i "s/HAMQTTIP/$HAMQTTIP/" /mosquitto/conf/mosquitto.conf
fi

if [ "$HAMQTTUSERNAME" != "" ]; then
	if grep remote_username /mosquitto/conf/mosquitto.conf>/dev/null; then
		echo "Existing remote username"
	else
		echo remote_username $HAMQTTUSERNAME >> /mosquitto/conf/mosquitto.conf
	fi
fi

if [ "$HAMQTTPASSWORD" != "" ]; then
	if grep remote_username /mosquitto/conf/mosquitto.conf>/dev/null; then
		echo "Existing remote password"
	else
		echo remote_password $HAMQTTPASSWORD >> /mosquitto/conf/mosquitto.conf
	fi
fi

exec /usr/sbin/mosquitto -c /mosquitto/conf/mosquitto.conf
