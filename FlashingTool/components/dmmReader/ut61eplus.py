import binascii
import logging
import hid # https://github.com/trezor/cython-hidapi https://trezor.github.io/cython-hidapi/api.html
import decimal
import time # add 20241004 soo, need it to handle timeout for hid library
import select # add 20241004 soo, need it to handle timeout for hid library

log = logging.getLogger(__name__)

print(hid.__file__)

"""
protocol of UT61+

parts from an USB trace, parts from experimenting myself, parts from https://github.com/gulux/Uni-T-CP2110
and many 'inspirations' form the decompiled bluetooth app

example response in mV AC

ab . => header
cd . => header
10   => number of bytes that follow including 'checksum'
01   => mode
30 0 => range (character starting at '0')
20   => digit MSB (can be ' ' or '-') ! number can also be ' OL.  '
20   => digit
35 5 => digit
33 3 => digit
2e . => digit
35 5 => digit
34 4 => digit LSB
01   => progress1
00   => progress2 => progress = progress1*10 + progress2 - meaning is not clear yet
30 0 => Bitmask: Max,Min,Hold,Rel
34 4 => Bitmask: !Auto,Battery,HvWarning
30 0 => Bitmask: !DC,PeakMax,PeakMin,BarPol
03   => sum over all - MSB - sum from 0xab to 0x30
8d . => sum over all - LSB

"""


class Measurement:

    # decoded modes
    _MODE = ['ACV', 'ACmV', 'DCV', 'DCmV', 'Hz', '%', 'OHM', 'CONT', 'DIDOE', 'CAP', '°C', '°F', 'DCuA', 'ACuA', 'DCmA', 'ACmA',
             'DCA', 'ACA', 'HFE', 'Live', 'NCV', 'LozV', 'ACA', 'DCA', 'LPF', 'AC/DC', 'LPF', 'AC+DC', 'LPF', 'AC+DC2', 'INRUSH']

    # units based on mode and range
    _UNITS = {'%': {'0': '%'},
              'AC+DC': {'1': 'A'},
              'AC+DC2': {'1': 'A'},
              'AC/DC': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'ACA': {'1': 'A'},
              'ACV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'ACmA': {'0': 'mA', '1': 'mA'},
              'ACmV': {'0': 'mV'},
              'ACuA': {'0': 'uA', '1': 'uA'},
              'CAP': {'0': 'nF',
                      '1': 'nF',
                      '2': 'uF',
                      '3': 'uF',
                      '4': 'uF',
                      '5': 'mF',
                      '6': 'mF',
                      '7': 'mF'},
              'CONT': {'0': 'Ω'},
              'DCA': {'1': 'A'},
              'DCV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'DCmA': {'0': 'mA', '1': 'mA'},
              'DCmV': {'0': 'mV'},
              'DCuA': {'0': 'uA', '1': 'uA'},
              'DIDOE': {'0': 'V'},
              'Hz': {'0': 'Hz',
                     '1': 'Hz',
                     '2': 'kHz',
                     '3': 'kHz',
                     '4': 'kHz',
                     '5': 'MHz',
                     '6': 'MHz',
                     '7': 'MHz'},
              'LPF': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'LozV': {'0': 'V', '1': 'V', '2': 'V', '3': 'V'},
              'OHM': {'0': 'Ω',
                      '1': 'kΩ',
                      '2': 'kΩ',
                      '3': 'kΩ',
                      '4': 'MΩ',
                      '5': 'MΩ',
                      '6': 'MΩ'},
              '°C': {'0': '°C', '1': '°C'},
              '°F': {'0': '°F', '1': '°F'},
              'HFE': {'0': 'B'},
              'NCV': {'0': 'NCV'}}

    # strings that could mean overload - taken from android app
    _OVERLOAD = set(['.OL', 'O.L', 'OL.', 'OL', '-.OL', '-O.L', '-OL.', '-OL'])
    
    # strings that Indicate level of voltage detected >=50Vrms (50-60Hz)
    _NCV = set(['EF','-','--','---','----','-----'])
    
    # unit exponents
    _EXPONENTS = {
        'M':  6, # mega
        'k':  3, # kilo
        'm': -3, # milli
        'u': -6, # mirco
        'n': -9,  # nano
    }

    @property
    def binary(self)->bytes:
        """ original binary data from DMM """
        return self._data['binary']

    @property
    def mode(self)->str:
        """ mode """
        return self._data['mode']

    @property
    def range(self)->str:
        """ range - internal to device """
        return self._data['range']

    @property
    def display(self)->str:
        """displayed number as string """
        return self._data['display']

    @property
    def overload(self)->bool:
        """ device is in overload condition - like measuring resistance on open leads """
        return self._data['overload']

    @property
    def display_decimal(self)->decimal:
        """ displayed number as decimal - may be decimal.Overflow() in overload condition """
        return self._data['display_decimal']

    @property
    def display_unit(self)->str:
        """ displayed unit including exponent - e.g. mV """
        return self._data['display_unit']

    @property
    def unit(self)->str:
        """ physical unit of the measurement - e.g. V """
        return self._data['display_unit']

    @property
    def value(self)->decimal:
        """ decimal representation - e.g. 200mV => 0.2V """
        return self._data['decimal']
    
    @property
    def progress(self)->int:
        """ some progress indicator - unknown meaning """
        return self._data['progres']

    @property
    def isMax(self)->bool:
        """ value is max value """
        return self._data['max']

    @property
    def isMin(self)->bool:
        """ value is max value """
        return self._data['min']

    @property
    def isHold(self)->bool:
        """ DMM is in hold mode """
        return self._data['hold']

    @property
    def isRel(self)->bool:
        """ DMM is in REL mode """
        return self._data['rel']

    @property
    def isAuto(self)->bool:
        """ auto ranging active """
        return self._data['auto']

    @property
    def hasBatteryWarning(self)->bool:
        """ battery warning """
        return self._data['battery']

    @property
    def hasHVWarning(self)->bool:
        """ high voltage warning - > 30 V """
        return self._data['hvwarning']

    @property
    def isDC(self)->bool:
        """ displayed value is DC """
        return self._data['dc']

    @property
    def isMaxPeak(self)->bool:
        """ value is max peak """
        return self._data['peak_max']

    @property
    def isMinPeak(self)->bool:
        """ value is min peak """
        return self._data['peak_min']

    @property
    def isBarPol(self)->bool:
        """ unknown """
        return self._data['']


    def __init__(self, b: bytes):
        self._data = {}
        self._data['binary'] = b
        self._data['mode'] = self._MODE[b[0]]
        self._data['range'] = b[1:2].decode('ASCII')
        self._data['display'] = b[2:9].decode('ASCII').replace(' ', '')
        self._data['overload'] = self._data['display'] in self._OVERLOAD
        self._data['ncv'] = self._data['display'] in self._NCV
        if self._data['overload']:
            self._data['display_decimal'] = decimal.Overflow()
        elif self._data['ncv']:
            switch={
                'EF': 0,
                '-': 1,
                '--': 2,
                '---': 3,
                '----': 4,
                '-----': 5
            }
            self._data['display_decimal'] = switch.get(self._data['display'],-1)
        else:
            self._data['display_decimal'] = decimal.Decimal(self.display)
            
        self._data['display_unit'] = self._UNITS[ self._data['mode'] ].get(self._data['range'])
        
        self._data['unit'] = self._data['display_unit']

        self._data['decimal'] = self.display_decimal
        if self._data['unit'][0] in self._EXPONENTS and not self._data['overload']:
            self._data['decimal'] = self._data['decimal'].rotate(self._EXPONENTS[self.unit[0]])
            self._data['unit'] = self._data['unit'][1:] # remove first char

        self._data['progres'] = b[9] * 10 + b[10]
        self._data['max'] = b[11] & 8 > 0
        self._data['min'] = b[11] & 4 > 0
        self._data['hold'] = b[11] & 2 > 0
        self._data['rel'] = b[11] & 1 > 0
        self._data['auto'] = b[12] & 4 == 0
        self._data['battery'] = b[12] & 2 > 0
        self._data['hvwarning'] = b[12] & 1 > 0
        self._data['dc'] = b[13] & 8 > 0
        self._data['peak_max'] = b[13] & 4 > 0
        self._data['peak_min'] = b[13] & 2 > 0
        self._data['bar_pol'] = b[13] & 1 > 0  # meaning not clear

    def __str__(self):
        res = '\n'
        res += f'mode={self.mode}\n'
        res += f'range={self.range}\n'
        res += f'display={self.display}\n'
        res += f'display_decimal={self.display_decimal}\n'
        res += f'display_unit={self.display_unit}\n'
        res += f'overload={self.overload}\n'
        res += f'value={self.value}\n'
        res += f'unit={self.unit}\n'
        res += f'isMax={self.isMax}\n'
        res += f'ismin={self.isMin}\n'
        res += f'isHold={self.isHold}\n'
        res += f'isRel={self.isRel}\n'
        res += f'isAuto={self.isAuto}\n'
        res += f'hasBatteryWarning={self.hasBatteryWarning}\n'
        res += f'hashasHVWarning={self.hasHVWarning}\n'
        res += f'isDC={self.isDC}\n'
        res += f'isMaxPeak={self.isMaxPeak}\n'
        res += f'isMinPeak={self.isMinPeak}\n'
        return res

        # pylint: disable=unreachable
        for b in self.binary:
            l = '{:02x} {}\n'.format(b, chr(b))
            res += l
        return res


class UT61EPLUS:

    CP2110_VID = 0x10c4
    CP2110_PID = 0xea80

    QinHeng_VID = 0x1a86
    QinHeng_PID = 0xe429
    
    path = "/dev/hidraw5"

    _SEQUENCE_GET_NAME = bytes.fromhex('AB CD 03 5F 01 DA')
    _SEQUENCE_SEND_DATA = bytes.fromhex('AB CD 03 5E 01 D9')
    _SEQUENCE_SEND_CMD = bytes.fromhex('AB CD 03')

    _COMMANDS = {
        'min_max': 65,
        'not_min_max': 66,
        'range': 70, 
        'auto': 71,
        'rel': 72, 
        'select2': 73, # Hz/USB
        'hold': 74,
        'lamp': 75,
        'select1': 76, # orange
        'p_min_max': 77,
        'not_peak': 78,
    }

    selected_device = None

    def __init__(self, device_number=None):

        multimeters = []

        """Find and open the UT61E+ device"""

        print("Find and open the UT61E+ device")
        devices = hid.enumerate(self.CP2110_VID, self.CP2110_PID)

        # bar 20241004 soo, add support for other usb dongle type

        # if not devices: 
        #     raise Exception("No UT61E+ device found.")
        
        # for i, device in enumerate(devices):
        #     devices = hid.enumerate(self.CP2110_VID, self.CP2110_PID)
        #     if not devices:
        #         raise Exception("No UT61E+ device found.")

        #     if device_number == 0:
        #         self.selected_device = devices[0]
        #     elif device_number == 1:
        #         self.selected_device = devices[1]
        #     else:
        #         print(f"Selected device number: {device_number}")
        #         raise ValueError(f"Invalid device number: {device_number}")

        # bar 20241004 soo, add support for other usb dongle type
            
        #add 20241004 soo, add support for other usb dongle type
        for device in devices:
            multimeters.append(device)
        devices = hid.enumerate(self.QinHeng_VID, self.QinHeng_PID) 
        for device in devices:
            multimeters.append(device)

        print("")
        print("")
        print("Connected Multimeter Info Array")
        print("")
        print("")
        print(multimeters)
        print("")
        print("")

        if device_number > len(multimeters):
            raise Exception("Invalid multimeter")
        else:
            self.selected_device = multimeters[device_number]
        #add 20241004 soo, add support for other usb dongle type

        # Open the selected device
        self.dev = hid.Device(self.selected_device['vendor_id'], self.selected_device['product_id'], self.selected_device['serial_number'])

        # self.dev.set_nonblocking(True)

        self.dev.send_feature_report(bytes([0x41, 0x01]))  # enable uart
        self.dev.send_feature_report(bytes([0x50, 0x00, 0x00, 0x25, 0x80, 0x00, 0x00, 0x03, 0x00, 0x00]))  # 9600 8N1 - from USB trace
        self.dev.send_feature_report(bytes([0x43, 0x02]))  # purge both fifos
        log.debug('feature requests sent')
        print('feature requests sent')
        if self.dev is None:
            raise Exception("No UT61E+ device found.")
        else:
            print("UT61E+ device found")
            print("UT61E+ device opened")
        
    def _write(self, b: bytes):
        buf = []
        buf.append(len(b))
        buf += b
        self.dev.write(bytes(buf))

    # def _readResponse(self) -> bytes:
    #     # pylint: disable=unsupported-assignment-operation,unsubscriptable-object
    #     state = 0  # 0=init 1=0xAB received 2=0xCD received 3=we have length
    #     buf: bytes = None
    #     index: int = None
    #     sum: int = 0

    #     print("_readResponse")
    #     timeout = 5 # in seconds
    #     start_time = time.time() # add 20241004 soo, need it to handle timeout for hid library
    #     while True:
    #     # while time.time() - start_time < timeout:
    #         x = self.dev.read(64)
    #         # x = self.dev.read(64,3000) # add 20241004 soo, need it to handle timeout for hid library,3 seconds timeout
    #         b: int
    #         for b in x[1:]:  # skip first byte - length from HID

    #             if state < 3 or index + 2 < len(buf):  # sum all bytes except last 2
    #                 sum += b

    #             if state == 0 and b == 0xAB:
    #                 state = 1
    #             elif state == 1 and b == 0xCD:
    #                 state = 2
    #             elif state == 2:
    #                 buf = bytearray(b)
    #                 index = 0
    #                 state = 3
    #             elif state == 3:
    #                 buf[index] = b
    #                 index += 1
    #                 if index == len(buf):
    #                     recevied_sum = (buf[-2] << 8) + buf[-1]
    #                     log.debug('calculated sum=%04x expected sum=%04x', sum, recevied_sum)
    #                     print('calculated sum=%04x expected sum=%04x', sum, recevied_sum)
    #                     if sum != recevied_sum:
    #                         log.warning('checksum mismatch')
    #                         print('checksum mismatch')
    #                         return None
    #                     return buf[:-2]  # drop last 2 bytes at end with checksum
    #             else:
    #                 log.warning('unexpected byte %02x in state %i', b, state)
    #                 print('unexpected byte %02x in state %i', b, state)
            
    #         time.sleep(0.01) # add 20241004 soo, need it to handle timeout for hid library

    #     self.dev.close()
        
    # Test new flow
    def _readResponse(self) -> bytes:
        # pylint: disable=unsupported-assignment-operation,unsubscriptable-object
        state = 0  # 0=init 1=0xAB received 2=0xCD received 3=we have length
        buf: bytearray = bytearray()
        index: int = 0
        checksum: int = 0

        print("_readResponse")
        timeout = 1  # Timeout in seconds
        start_time = time.time()  # Track start time
        # print("start_time: ", str(start_time))

        while True:
            if time.time() - start_time > timeout:
                print("Timeout reached, no response.")
                return None
            
            # Read data from the device
            # print("self.dev.read(64)")
            data = self.dev.read(64, timeout)
            # print("Received:", data)
            
            if not data:
                print("No response received, exiting.")
            
            for b in data[1:]:  # Skip first byte - length from HID
                if state < 3 or index + 2 < len(buf):  # Sum all bytes except last 2
                    checksum += b

                if state == 0 and b == 0xAB:
                    state = 1
                elif state == 1 and b == 0xCD:
                    state = 2
                elif state == 2:
                    buf = bytearray(b)
                    index = 0
                    state = 3
                elif state == 3:
                    buf[index] = b
                    index += 1
                    if index == len(buf):
                        if len(buf) < 2:
                            print("Insufficient data received for checksum validation.")
                            return None
                        received_sum = (buf[-2] << 8) + buf[-1]
                        log.debug('calculated sum=%04x expected sum=%04x', checksum, received_sum)
                        print('calculated sum=%04x expected sum=%04x', checksum, received_sum)
                        if checksum != received_sum:
                            log.warning('checksum mismatch')
                            print('checksum mismatch')
                            return None
                        return buf[:-2]  # Drop last 2 bytes at end with checksum
                else:
                    log.warning('unexpected byte %02x in state %i', b, state)
                    print('unexpected byte %02x in state %i', b, state)

            time.sleep(0.01)  # Short sleep to avoid high CPU usage

        print("End of _readResponse")  # This is now reachable if timeout occurs

    def getName(self):
        # pylint: disable=unused-variable
        """get name of multimeter"""
        self._write(self._SEQUENCE_GET_NAME)
        unknown = self._readResponse()
        name = self._readResponse()
        return name.decode('ASCII')

    def takeMeasurement(self):
        """read measurement from screen"""
        self._write(self._SEQUENCE_SEND_DATA)
        b = self._readResponse()
        if b is None:
            return None
        return Measurement(b)

    def sendCommand(self, cmd)->None:
        """send command to device"""
        if cmd in self._COMMANDS:
            cmd = self._COMMANDS[cmd]
        if not type(cmd) is int:
            raise Exception(f'bad argument {cmd}')

        seq = self._SEQUENCE_SEND_CMD
        cmd_bytes = bytearray(3)
        cmd_bytes[0] = cmd & 0xff
        cmd = cmd + 379 # don't ask it's from the java source
        cmd_bytes[1] = cmd >> 8
        cmd_bytes[2] = cmd & 0xff
        seq += cmd_bytes
        self._write(seq)
        # pylint: disable=unused-variable
        unknown = self._readResponse()
        print(f'Command {cmd} sent')
        print(f"Response: {unknown}")

    def _test(self):
        self._write(self._SEQUENCE_GET_NAME)

        while True:
            x = self.dev.read(64)
            for i in range(1, len(x)):  # skip first byte - length
                hex: str = binascii.hexlify(x[i:i+1]).decode('ASCII')
                c: str = x[i:i+1].decode(encoding='ASCII', errors='ignore')
                if c.isprintable and len(c) == 1:
                    pass
                else:
                    c = '.'
                print(f'{hex} {c}')

    def writeMeasurementToFile(self, filename=None):
        measurement = self.takeMeasurement()

        if measurement is not None:
            with open(filename, 'w') as file:
                file.write(str(measurement))


