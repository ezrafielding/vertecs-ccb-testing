#!/usr/bin/env python3
import serial
import time

def sync():
    while serPort.cts == True:
        pass

def packMDPU(data, data_type: int, data_id, dest_callsign, src_callsign, max_data_size=1087):
    npackets = -(len(data) // -max_data_size)
    header = b'\x00\x00'
    trans_info = dest_callsign.encode('ascii') + b'\x00' + src_callsign.encode('ascii') + b'\x00'
    header += trans_info
    header += data_type.to_bytes(1, 'big')
    header += npackets.to_bytes(3, 'big')
    header += data_id.to_bytes(2, 'big') # check max number of images for mission or aat least roll over
    pad_size = len(data) + (max_data_size - len(data) % max_data_size)
    data = data.ljust(pad_size, b'\0')

    mdpuPackets = []
    for i in range(0, len(data), max_data_size):
        current = header + data[i:i+max_data_size]
        mdpuPackets.append(current)
    
    return mdpuPackets

def packVCDU(mdpuPackets, spacecraft_id=0x55, vcid=0, version=1):
    header = ((version << 14) + (spacecraft_id << 6) + vcid).to_bytes(2, 'big')

    vcduPackets = []
    for i, packet in enumerate(mdpuPackets):
        current = header + i.to_bytes(3, 'big') + b'\x00' + packet
        vcduPackets.append(current)
    
    return vcduPackets

# Serial port configuration:
serPort = serial.Serial("/dev/ttyUSB0", 12000000, timeout=None, rtscts=True, dsrdtr=False)
serPort.flush()
xbandConfig = serial.Serial("/dev/ttyAMA3", 19200)
# xbandConfig.write(b'B0A\r')
print('Serial Port Open!')

with open('../examples/small_test.jpg', 'rb') as img_file:
    print('Reading File...')
    img_data = img_file.read()

print('Total Image Bytes: ', len(img_data))

mdpu = packMDPU(img_data, 1, 27, 'JG6YBW', 'JG6YNH')
vcdu = packVCDU(mdpu)
print('Total Packets: ', len(mdpu))
print('Begin Data Transfer...')
start = time.time()
# xbandConfig.write(b'B64\r')
sync()
for packet in vcdu:
    serPort.write(packet)
    sync()
end = time.time()
print('Transfer Complete!')
print('Total transfer time: ', end-start)
# xbandConfig.write(b'B0A\r')

serPort.flush()
serPort.close()
print('Serial Port Closed.')
print('Done!')