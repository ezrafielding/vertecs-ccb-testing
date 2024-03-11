#!/usr/bin/env python3
import serial
from time import sleep
import ftdi1 as ftdi

import atexit
import logging
import math
import os
import subprocess
import sys
import time
from ctypes import c_uint16, c_ubyte, byref
import timeit

import ftdi1 as ftdi


logger = logging.getLogger(__name__)

FT232H_VID = 0x0403   # Default FTDI FT232H vendor ID
FT232H_PID = 0x6014   # Default FTDI FT232H product ID

MSBFIRST = 0
LSBFIRST = 1
CTS_MASK = 1 << 4

_REPEAT_DELAY = 4


def _check_running_as_root():
    # NOTE: Checking for root with user ID 0 isn't very portable, perhaps
    # there's a better alternative?
    if os.geteuid() != 0:
        raise RuntimeError('Expected to be run by root user! Try running with sudo.')

def disable_FTDI_driver():
    """Disable the FTDI drivers for the current platform.  This is necessary
    because they will conflict with libftdi and accessing the FT232H.  Note you
    can enable the FTDI drivers again by calling enable_FTDI_driver.
    """
    logger.debug('Disabling FTDI driver.')
    if sys.platform == 'darwin':
        logger.debug('Detected Mac OSX')
        # Mac OS commands to disable FTDI driver.
        _check_running_as_root()
        subprocess.call('kextunload -b com.apple.driver.AppleUSBFTDI', shell=True)
        subprocess.call('kextunload /System/Library/Extensions/FTDIUSBSerialDriver.kext', shell=True)
    elif sys.platform.startswith('linux'):
        logger.debug('Detected Linux')
        # Linux commands to disable FTDI driver.
        _check_running_as_root()
        subprocess.call('modprobe -r -q ftdi_sio', shell=True)
        subprocess.call('modprobe -r -q usbserial', shell=True)
    # Note there is no need to disable FTDI drivers on Windows!

def enable_FTDI_driver():
    """Re-enable the FTDI drivers for the current platform."""
    logger.debug('Enabling FTDI driver.')
    if sys.platform == 'darwin':
        logger.debug('Detected Mac OSX')
        # Mac OS commands to enable FTDI driver.
        _check_running_as_root()
        subprocess.check_call('kextload -b com.apple.driver.AppleUSBFTDI', shell=True)
        subprocess.check_call('kextload /System/Library/Extensions/FTDIUSBSerialDriver.kext', shell=True)
    elif sys.platform.startswith('linux'):
        logger.debug('Detected Linux')
        # Linux commands to enable FTDI driver.
        _check_running_as_root()
        subprocess.check_call('modprobe -q ftdi_sio', shell=True)
        subprocess.check_call('modprobe -q usbserial', shell=True)

def use_FT232H():
    """Disable any built in FTDI drivers which will conflict and cause problems
    with libftdi (which is used to communicate with the FT232H).  Will register
    an exit function so the drivers are re-enabled on program exit.
    """
    disable_FTDI_driver()
    atexit.register(enable_FTDI_driver)

def enumerate_device_serials(vid=FT232H_VID, pid=FT232H_PID):
    """Return a list of all FT232H device serial numbers connected to the
    machine.  You can use these serial numbers to open a specific FT232H device
    by passing it to the FT232H initializer's serial parameter.
    """
    try:
        # Create a libftdi context.
        ctx = None
        ctx = ftdi.new()
        # Enumerate FTDI devices.
        device_list = None
        count, device_list = ftdi.usb_find_all(ctx, vid, pid)
        if count < 0:
            raise RuntimeError('ftdi_usb_find_all returned error {0}: {1}'.format(count, ftdi.get_error_string(self._ctx)))
        # Walk through list of devices and assemble list of serial numbers.
        devices = []
        while device_list is not None:
            # Get USB device strings and add serial to list of devices.
            ret, manufacturer, description, serial = ftdi.usb_get_strings(ctx, device_list.dev, 256, 256, 256)
            if serial is not None:
                devices.append(serial)
            device_list = device_list.next
        return devices
    finally:
        # Make sure to clean up list and context when done.
        if device_list is not None:
            ftdi.list_free(device_list)
        if ctx is not None:
            ftdi.free(ctx)


class FT232H():

    def __init__(self, baudrate=12000000,vid=FT232H_VID, pid=FT232H_PID, serial=None):
        """Create a FT232H object.  Will search for the first available FT232H
        device with the specified USB vendor ID and product ID (defaults to
        FT232H default VID & PID).  Can also specify an optional serial number
        string to open an explicit FT232H device given its serial number.  See
        the FT232H.enumerate_device_serials() function to see how to list all
        connected device serial numbers.
        """
        # Initialize FTDI device connection.
        self._ctx = ftdi.new()
        if self._ctx == 0:
            raise RuntimeError('ftdi_new failed! Is libftdi1 installed?')
        # Register handler to close and cleanup FTDI context on program exit.
        atexit.register(self.close)
        if serial is None:
            # Open USB connection for specified VID and PID if no serial is specified.
            self._check(ftdi.usb_open, vid, pid)
        else:
            # Open USB connection for VID, PID, serial.
            self._check(ftdi.usb_open_string, 's:{0}:{1}:{2}'.format(vid, pid, serial))
        # Reset device.
        self._check(ftdi.usb_reset)
        # Enable flow control.
        self._check(ftdi.setflowctrl, ftdi.SIO_RTS_CTS_HS)
        # Change write buffer to maximum size, 1115 bytes.
        self._check(ftdi.write_data_set_chunksize, 1115)
        # Set baudrate
        self._check(ftdi.set_baudrate, baudrate)
        # Clear pending read data & write buffers.
        self._check(ftdi.usb_purge_buffers)


    def close(self):
        """Close the FTDI device.  Will be automatically called when the program ends."""
        if self._ctx is not None:
            ftdi.free(self._ctx)
        self._ctx = None

    def write(self, buf):
        """Helper function to call write_data on the provided FTDI device and
        verify it succeeds.
        """
        ret = ftdi.write_data(self._ctx, buf)
        while self.cts:
            pass

    def _check(self, command, *args):
        """Helper function to call the provided command on the FTDI device and
        verify the response matches the expected value.
        """
        ret = command(self._ctx, *args)
        logger.debug('Called ftdi_{0} and got response {1}.'.format(command.__name__, ret))
        if ret != 0:
            raise RuntimeError('ftdi_{0} failed with error {1}: {2}'.format(command.__name__, ret, ftdi.get_error_string(self._ctx)))
        
    @property
    def cts(self):
        """
        get the state of CTS
        """
        status = c_uint16()
        _,status = ftdi.poll_modem_status(self._ctx)
        return bool(status.value & CTS_MASK)

def sync():
    while xbandData.cts:
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
        current = (c_ubyte * len(current)).from_buffer_copy(current)
        vcduPackets.append(current)
    
    return vcduPackets

# Serial port configuration:
# serPort = serial.Serial("/dev/ttyUSB0", 12000000, timeout=None, rtscts=True, dsrdtr=False)
xbandData = FT232H()
# serPort.flush()
xbandConfig = serial.Serial("/dev/ttyAMA3", 19200)
xbandConfig.write(b'B0A\r')
print('Serial Port Open! ', xbandData)
with open('../examples/small_test.jpg', 'rb') as img_file:
    print('Reading File...')
    img_data = img_file.read()

print('Total Image Bytes: ', len(img_data))

mdpu = packMDPU(img_data, 1, 27, 'JG6YBW', 'JG6YNH')
vcdu = packVCDU(mdpu)
print('Total Packets: ', len(mdpu))
print('Begin Data Transfer...')
xbandConfig.write(b'B64\r')
sync()
for packet in vcdu:
    xbandData.write(packet)
print('Transfer Complete!')

# serPort.flush()
# serPort.close()
xbandConfig.write(b'B0A\r')
xbandData.close()
xbandConfig.close()
print('Serial Port Closed.')
print('Done!')