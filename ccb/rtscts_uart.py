#!/usr/bin/env python3
import serial

def sync():
    while serPort.cts == True:
        pass

# Serial port configuration:
serPort = serial.Serial("/dev/ttyUSB0", 12000000, timeout=None, rtscts=True, dsrdtr=False)

firstTime = True
with open('./test.png', 'rb') as img_file:
    img_data = img_file.read()
sync()
serPort.write(img_data)

serPort.flush()
serPort.close()
