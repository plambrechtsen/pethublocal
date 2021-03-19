docker stop zigsniff
docker container rm zigsniff
cp ../../PetHub/* .
docker build -t zigsniff .
device=`lsusb -d 0451: | sed 's/://' | awk '{print "/dev/bus/usb/"$2"/"$4}'`
echo "TI CC2531 Device $device"
docker run -d --name="zigsniff" -v /data/pethublocal/zigsniff:/data/zigsniff -v /etc/localtime:/etc/localtime:ro --device $device zigsniff
docker update --restart unless-stopped zigsniff
