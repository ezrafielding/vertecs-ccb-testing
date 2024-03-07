file_name = './test.bin'

with open(file_name, 'rb') as f:
    packetData = f.read().split(b'\x1A\xCF\xFC\x1D')[1:]

mpduPackets = []
print('Number of Packets: ', len(packetData))
for packet in packetData:
    mpduPackets.append(packet[28:])

imgData = bytes()
i = 0
for packet in mpduPackets:
    if packet[:2] == b'\x55\x40':
        i += 1
        imgData += packet[28:-160]
    elif packet[:2] == b'\x51\xFF':
        pass
    else:
        print(packet)

imgData = imgData.rstrip(b'\x00')
print('Total Image Packets: ', i)
print('Total bytes: ',len(imgData))
with open('test_receive.png', 'wb') as f:
    f.write(imgData)