#Pass pcap file into something that can be read, and filter only mqtt data frames to reduce the noise.
tshark -r $1.pcap -Y "mqtt.msgtype == 3" -T fields -e frame.time_epoch -e ip.src -e ip.dst -e mqtt.topic -e mqtt.msg | python3 mqttpcapparse.py $1.txt
