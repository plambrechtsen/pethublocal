#!/bin/bash

#You need to update the output/web/Hxxx serial number back from original over the top.
#You also need a new DNS entry for the below DNS domain a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com to point internally and then add the real IP to your local hosts
#The Serial Number and MAC Address are written on the underside of the hub, mac address is the hardware mac, but has 4 leading 0000, but that is correct on the label.

serialnumber=H0xx-0xxxxxx
macaddress=0000xxxxxxxxxxxx
certpassword=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Firmware version is currently 2.43
fw=2.43

if [[ $certpassword == *"xxx"* ]]; then
  echo 'Certificate password has not been updated, you need to edit this script and update the variables before running'
  exit 1
fi

#If you manually want to download the credentials from sure pet directly rather than using the frontend
if test -f "../docker/output/web/$serialnumber-$macaddress-$fw.original.bin"; then
  cp ../docker/output/web/$serialnumber-$macaddress-$fw.original.bin .
else
  curl -v -k -d "serial_number=$serialnumber&mac_address=$macaddress&product_id=1&firmware_version=$fw" -H "curl/7.22.0 (x86_64-pc-linux-gnu) libcurl/7.22.0 OpenSSL/1.0.1 zlib/1.2.3.4 libidn/1.23 librtmp/2.3" -H "Content-Type: application/x-www-form-urlencoded" -X POST -o $serialnumber-$macaddress-$fw.original.bin https://hub.api.surehub.io/api/credentials
fi    

#Take the 9th value from the credentials file which is the PKCS12 certificate, and base64 decode it into the serial number.p12 PKCS12 binary file, for openssl and polarproxy to be able to open with the certpassword.
awk -F":" '{print $9}' $serialnumber-$macaddress-$fw.original.bin | base64 -d > $serialnumber.p12

#Check to make sure we can open the PKCS12 with the password
openssl pkcs12 -nodes -passin pass:$certpassword -in $serialnumber.p12 -out $serialnumber.pem
if [ $? -ne 0 ]; then
   echo "Password for PKCS12 is incorrect, you will need to fix this as there is no point in proceeding"
   exit 1
else
   echo "Decrypted Certificate"
   cat $serialnumber.pem
   echo "Certificate Information"
   openssl x509 -in $serialnumber.pem -text
fi

#Generate self signed iot files and convert to pkcs12 file with a password of password but not with a CA Constraint
openssl req -config <(printf "[req]\ndistinguished_name=dn\n[dn]") -x509 -newkey rsa:2048 -nodes -keyout iot.key -out iot.pem -sha256 -addext "subjectAltName = DNS:iot.us-east-1.amazonaws.com, DNS:*.iot.us-east-1.amazonaws.com" -days 3650 -subj '/CN=*.iot.us-east-1.amazonaws.com'
openssl pkcs12 -in iot.pem -inkey iot.key -password pass:password -export -out iot.p12

mkdir mqtt

#x64 download : curl https://www.netresec.com/?download=PolarProxy | tar -xzf -
#arm 32 bit   : curl https://www.netresec.com/?download=PolarProxy_linux-arm | tar -xzf -
#arm 64 bit   : curl https://www.netresec.com/?download=PolarProxy_linux-arm64 | tar -xzf -

./PolarProxy -v -p 8883,1883 --autoflush 10 -o mqtt --insecure --clientcert a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com:$serialnumber.p12:$certpassword --servercert a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com:iot.p12:password --nosni a5kzy4c0c0226-ats.iot.us-east-1.amazonaws.com

