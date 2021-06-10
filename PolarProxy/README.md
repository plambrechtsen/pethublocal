# PolarProxy

PolarProxy is my tool of choice to be able to "Man in the Middle" traffic 

You need to update the gomqtt with the serial number and password for the certificate.

To find the certificate you need to open the hub and attach a TTL Serial adapter to the console port.

Details on the connection is in the Hub documentation:

https://github.com/plambrechtsen/pethublocal/tree/main/docs/Hub

Then use this script and read the top about setting up logging as the upgrade produces around 20k lines, and you can't stop the firmware update or you could brick your hub.

https://github.com/plambrechtsen/pethublocal/blob/main/docker/source/fwlogtopw.py

Also a DNS entry for a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com needs to be added internally to point to the host running polarproxy and then add onto the local hosts to point to the real AWS endpoint.

When you have a days worth of logs using mergecap will merge the whole directory into a single pcap file which makes parsing it easier:

cd mqtt
mergecap -w ../AllFiles.pcap *.pcap 

in the mqtt directory and then you have a single PCAP.

Also ideally you create the pethublocal database from the cloud and copy that long with pethublocal and const into this directory to parse the pcap into human readable messages

cp ../docker/source/pethublocal.db .
cp ../docker/source/pethubpacket.py .
cp ../docker/source/pethubconst.py .

And then in mqttpcapparse.py you can turn on what is needed.
