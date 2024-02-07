import serial
ser = serial.Serial('/dev/ttyUSB0', 57600)  # open serial port
print(ser.name) # check which port was really used
ser.write(b'hello test') # write a string
ser.close()
