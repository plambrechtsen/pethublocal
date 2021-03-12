import sys,binascii,array
import surepetpacket as spp

PrintZigline = False

for line in sys.stdin:
    inline=line.split('\t')
    if len(inline) > 1:
        hexbyte=bytes.fromhex(inline[3])
        if PrintZigline:
            print("ZigLine: ",inline[0],inline[1],inline[2]," ".join(["{:02x}".format(x) for x in bytearray(hexbyte)]), sep='\t')
        if len(inline[3])>2:
            print(spp.decodemiwi(inline[0],inline[1],inline[2],inline[3]))

