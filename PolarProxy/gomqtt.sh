#!/bin/bash

#Convert self signed iot files to pkcs12 file with a password of password
openssl pkcs12 -in ../docker/mqtt/default/iot.pem -inkey ../docker/mqtt/default/iot.key -password pass:password -export -out iot.p12

#You need to update the output/web/Hxxx serial number back from original over the top.
#You also need a new DNS entry for the below DNS domain a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com to point internally and then add the real IP to your local hosts

serialnumber=H010-0651105
macaddress=000068271904A2F7
certpassword=9BE64CF91A6242E1ACA099ADC94A1828

awk -F":" '{print $9}' ../docker/output/web/$serialnumber-$macaddress-2.43.original.bin | base64 -d > $serialnumber.p12

openssl pkcs12 -nodes -passin pass:$certpassword -in $serialnumber.p12

mkdir mqtt

#x64 download : curl https://www.netresec.com/?download=PolarProxy | tar -xzf -
#arm 32 bit   : curl https://www.netresec.com/?download=PolarProxy_linux-arm | tar -xzf -
#arm 64 bit   : curl https://www.netresec.com/?download=PolarProxy_linux-arm64 | tar -xzf -

./PolarProxy -v -p 8883,1883 --autoflush 10 -o mqtt --insecure --clientcert a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com:$serialnumber.p12:$certpassword --servercert a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com:iot.p12:password --nosni a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com

