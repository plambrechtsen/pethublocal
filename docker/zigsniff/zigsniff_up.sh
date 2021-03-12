docker stop surepet_zigsniff
docker container rm surepet_zigsniff
docker build -t surepet_zigsniff .
device=`lsusb -d 0451: | sed 's/://' | awk '{print "/dev/bus/usb/"$2"/"$4}'`
echo "TI CC2531 Device $device"
docker run -d --name="surepet_zigsniff" -v /data/surepet/zigsniff:/data/zigsniff -v /etc/localtime:/etc/localtime:ro --device $device surepet_zigsniff
docker update --restart unless-stopped surepet_zigsniff
