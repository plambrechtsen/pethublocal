tshark -r $1.pcap -Y "mqtt.msgtype == 3" -T fields -e frame.time -e ip.src -e ip.dst -e mqtt.topic -e mqtt.msg | python3 mqttpcapparse.py $1.txt
