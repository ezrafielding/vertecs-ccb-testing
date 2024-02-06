#!/usr/bin/env python3
import sys
import serial

def sync():
    while serPort.cts == True:
        pass

# Serial port configuration:
serPort = serial.Serial("/dev/ttyUSB0", 12000000, timeout=None, rtscts=True, dsrdtr=False)

firstTime = True

while True:
    data = sys.stdin.buffer.read(32768)
    if (len(data) == 0):
        break
    if firstTime:
        sync()
    serPort.write(data)
    firstTime = False

serPort.flush()
serPort.close()
