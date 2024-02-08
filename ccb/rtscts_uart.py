#!/usr/bin/env python3
import serial

def sync():
    while serPort.cts == True:
        pass

# Serial port configuration:
serPort = serial.Serial("/dev/ttyUSB0", 12000000, timeout=None, rtscts=True, dsrdtr=False)
print('Serial Port Open!')
firstTime = True
with open('./test.png', 'rb') as img_file:
    print('Reading File...')
    img_data = img_file.read()

print('Begin Data Transfer...')
sync()
serPort.write(img_data)
print('Transfer Complete!')

serPort.flush()
serPort.close()
print('Serial Port Closed.')
print('Done!')