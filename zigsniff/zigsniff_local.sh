d=$(date +%Y%m%d-%H%M%S)

[[ -f pethublocal.db ]] && echo "Pethublocal.db exists" || cp ../../PetHub/pethublocal.db .
[[ -f pethubpacket.py ]] && echo "Pethubpacke.py exists" || cp ../../PetHub/pethubpacket.py .
[[ -f pethubpacket.xorkey ]] && echo "Pethubpacket.xorkey exists" || cp ../../PetHub/pethubpacket.xorkey .

tshark -r $1.pcap -T fields -e frame.time -e wpan.src64 -e wpan.dst64 -e data -l | unbuffer -p tee $1.txt | grep --line-buffered -P "\t01" | python3 -u zigparse.py | unbuffer -p tee $1.update.txt
