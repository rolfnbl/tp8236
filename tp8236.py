import sys
import time
import serial
import serial.tools.list_ports
import threading
from typing import TypedDict
import nist_scales as factors


class DmmMeasurement(TypedDict):
    """
    The Dmm Measurement Variable
        timestamp: The number of seconds since epoch that the data was recovered.  Leverages time package from
            pip install time
        rawdata: raw data string, as a list of bytes.
        display: readable actua display string excluding  icon flags.  Includes units, example: "1.234 mVAC"
        floating: value of the display as a float, scaled into absolutes
        units: measured units as a string, such as VAC, IDC, Ohms, etc.  Valid units are available as a dictionary in
            class.
        flags: any set flags on the screen.  This can include range, battery status, etc.

    """
    timestamp: float | None
    rawdata: list[int] | None
    display: str | None
    value: float | None
    units: str | None
    flags: dict | None
    name: str | None


__tp8236_checkdata__ = [0xaa, 0x55, 0x52, 0x24, 0x01, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
__tp8236_lcdmap__ = {0x5F: '0',
                     0x06: '1',
                     0x6B: '2',
                     0x2F: '3',
                     0x36: '4',
                     0x3D: '5',
                     0x7D: '6',
                     0x07: '7',
                     0x7F: '8',
                     0x3F: '9',
                     0x00: ' ',
                     0x58: 'L'  # This is the only Alpha character used for 'O.L' indication
                     }


class DmmData(TypedDict):
    timestamp: float | None
    rawdata: list[int] | None


debug = False


def debug_print(string):
    if debug:
        print(string)
    pass


class TP8236:
    def __init__(self, port: str | None = None, name: str | None = None):
        """
        Creates a unique instance of this DMM.  Features of this class type:
            1) Multiple instances can be created and will run concurrently
            2) Every instance will come with its own serial thread.
            3) Every instance can be named, and this name will tag onto the measurement
        :param port: The serial port attached to this instance.  The serial port will be opened and a thread assigned
            to service this port.  If None, then the port is not opened.
        :param name: A readable name attached to every measurement.  Doesn't really have to be unique, and can be left
            alone or None
        """
        super().__init__()
        self.devName = name
        self.__comPort__ = None
        self.__comPortThread__ = None
        self.__measurement__: DmmData = {"timestamp": 0, "rawdata": None}  # measurement
        self.__measurements__: [DmmData] = []  # list of measurements (most recent at location 0)
        self.__depth__ = 10  # depth of history
        self.__rawdata__ = [int]  # raw data
        self.units = ["V", "A", "ohms", "F", "degC", "degF", "Hz"]
        if port is not None:
            self.open(port)

    #
    # opens port
    def open(self, port=None):
        """
        Opens Serial Port for DMM
        :param port: Port Name
        :return: None
        """
        if self.__comPort__ is not None:
            if self.__comPort__.isOpen():
                self.__comPort__.close()
                while threading.Thread.is_alive(self.__comPortThread__):
                    time.sleep(0.05)
        if port is not None:
            # Open the port here
            self.__comPort__ = serial.Serial(port.device, 2400, timeout=0)
            print(f'Opened a TP8236 at {str(port.device)} as {self.devName}')
            # create the thread to be used to catch the serial data
            self.__comPortThread__ = threading.Thread(target=self.__serial_thread__, daemon=True)
            self.__comPortThread__.start()
            # The thread shuts down when the comport closes.

    def close(self):
        """
        Closes the port
        :return: Nothing
        """
        print("closing port")
        self.__comPort__.close()

    #
    #  Measurement interpreter function used to convert measurement data to a useful set of data.  Data is initially
    #   stored as a timestamp-dataset.  This function expands the dataset to the following dictionary elements:
    #       "timestamp": Timestamp copied from the measurement collected in the serial thread
    #       "data": List of a complete frame of raw data bytes collected

    def read(self, data: None | DmmData = None) -> None | DmmMeasurement:
        """
        Provides a multi-faceted mechanism to read data from the multimeter.  The following mechanisms are supported:
           1) Read last measurement (default)
           2) Read last (n) measurements
           3) read next measurement (need to specify a timeout).
        :param data:
        :return: None if no measuremet or A measurement composed of the following elements:
            'timestamp': a classic timestamp when the data was received
            'rawdata': the raw data received
            'display': the main display, units and scaling (i.e. "1.45 mV")
            'value': raw value
            'units': units of measure
            'flags': meter dependent list of elements and indicators such as:
                'low battery'
                    'diode'
                'bar'
                etc.
        """
        if data is None:
            # if the data is None, get the most recent data, and process it.
            debug_print (f' # Measurements = {len(self.__measurements__)}')
            if len(self.__measurements__) == 0:
                return None
            while len(self.__measurements__) > 0:
                data = self.__measurements__.pop(0)
        else:
            data = DmmData(timestamp=data["timestamp"], rawdata=data["rawdata"])
        # process the bytes
        debug_print(data["timestamp"])
        # Interpret the primary digits, including sign.
        # This is the LCD primary display map, which is specific for the TP8236
        datastring = ''
        dlist = data['rawdata'].copy()
        for byte in dlist:
            if dlist != '':
                datastring = datastring + ' '
            datastring = datastring + f'0x{byte:02x}'
        display = ''
        unit = ''
        mult = 1
        flags = {}
        # Determine first character of the display - which is the sign of the measurement (only if negative)
        bitmask = 0x08
        bytenum = 10
        if dlist[bytenum] & bitmask == bitmask:
            display = display + '-'
            dlist[bytenum] = dlist[bytenum] & ~bitmask  # clear interpreted bits.  This is used as a self-check
        # 1st Digit (MSB) 7-segment (no DP)
        # i.e.   8.8.8.8
        #        ^
        if dlist[9] in __tp8236_lcdmap__.keys():
            tbyte = dlist[9] & 0x7F
            display = display + __tp8236_lcdmap__[tbyte]
            dlist[9] = dlist[9] & ~0x7F  # clear bits
        else:
            errstr = f'Unknown LCD mapping at byte [9] EGFDCBA = {dlist[9]}\n  Full string {datastring}'
            raise ValueError(errstr)
        # Byte #8
        # 2nd Digit 7-segment plus 1st DP
        # i.e.   8.8.8.8
        #         ^^
        if dlist[8] & 0x80 == 0x80:
            display = display + '.'
            dlist[8] = dlist[8] & ~0x80  # clear bits
        if dlist[8] in __tp8236_lcdmap__.keys():
            display = display + __tp8236_lcdmap__[dlist[8] & 0x7F]
            dlist[8] = dlist[8] & ~0x7F  # clear bits
        else:
            errstr = f'Unknown LCD mapping at byte [8] EGFDCBA = {dlist[8]}\n  Full string: {datastring}'
            raise ValueError(errstr)
        # Byte #7
        # 3rd digit 7-segment plus 2nd DP
        # i.e.   8.8.8.8
        #           ^^
        if dlist[7] & 0x80 == 0x80:
            display = display + '.'
            dlist[7] = dlist[7] & ~0x80  # clear bits
        if dlist[7] in __tp8236_lcdmap__.keys():
            display = display + __tp8236_lcdmap__[dlist[7] & 0x7F]
            dlist[7] = dlist[7] & ~0x7F  # clear bits
        else:
            errstr = f'Unknown LCD mapping at byte 7 EGFDCBA = {dlist[7]}\n  Full string: {datastring}'
            raise ValueError(errstr)
        # Byte # 6:
        #   4th digit (LSB) 7-segment plus 3rd DP
        #   i.e.   8.8.8.8
        #               ^^
        if dlist[6] & 0x80 == 0x80:
            display = display + '.'
            dlist[6] = dlist[6] & ~0x80  # clear bits
        if dlist[6] in __tp8236_lcdmap__.keys():
            display = display + __tp8236_lcdmap__[dlist[6] & 0x7F]
            dlist[6] = dlist[6] & ~0x7F  # clear bits
        else:
            errstr = f'Unknown LCD mapping at byte [6] EGFDCBA = {dlist[6]}\n  Full string: {datastring}'
            raise ValueError(errstr)
        try:
            value = float(display)
        except ValueError:
            value = None
        debug_print(f'Value: {value}')
        display = display + ' '  # terminate number with a space
        # add units which are in Bytes 20 and 21
        # Degrees C Icon
        bitmask = 0x01
        if dlist[20] & bitmask == bitmask:
            display = display + 'degC'
            dlist[20] = dlist[20] & ~bitmask  # clear bits
        # Degrees F Icon
        bitmask = 0x02
        if dlist[20] & bitmask == bitmask:
            display = display + 'degF'
            dlist[20] = dlist[20] & ~bitmask  # clear bits
        # m in munF
        bitmask = 0x10
        if dlist[20] & bitmask == bitmask:
            display = display + 'm'
            mult = factors.scales.get('milli')
            dlist[20] = dlist[20] & ~bitmask  # clear bits
        # u in munF
        bitmask = 0x20
        if dlist[20] & bitmask == bitmask:
            display = display + 'u'
            dlist[20] = dlist[20] & ~bitmask  # clear bits
            mult = factors.scales.get('micro')
        # n in munF
        bitmask = 0x40
        if dlist[20] & bitmask == bitmask:
            display = display + 'n'
            dlist[20] = dlist[20] & ~bitmask  # clear bits
            mult = factors.scales.get('nano')
        # F in munF (append a space)
        bitmask = 0x80
        if dlist[20] & bitmask == bitmask:
            display = display + 'F '
            dlist[20] = dlist[20] & ~bitmask  # clear bits
            unit = "F"
        # u icon in umAV string
        bitmask = 0x01
        if dlist[21] & bitmask == bitmask:
            display = display + 'u'
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            mult = factors.scales.get('micro')
        # m icon in umAV string
        bitmask = 0x02
        if dlist[21] & bitmask == bitmask:
            display = display + 'm'
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            mult = factors.scales.get('micro')
        # Amps icon in umAV string (space appended)
        bitmask = 0x04
        if dlist[21] & bitmask == bitmask:
            display = display + 'A '
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            unit = 'A'
        # Volts icon in umAV string (space appended)
        bitmask = 0x08
        if dlist[21] & bitmask == bitmask:
            display = display + 'V '
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            unit = 'V'
        # M icon in MkΩHz
        bitmask = 0x10
        if dlist[21] & bitmask == bitmask:
            display = display + 'M'
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            mult = factors.scales.get('mega')
        # k icon in MkΩHz
        bitmask = 0x20
        if dlist[21] & bitmask == bitmask:
            display = display + 'k'
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            mult = factors.scales.get('kilo')
        # Ω icon in MkΩHz (space appended)
        bitmask = 0x40
        if dlist[21] & bitmask == bitmask:
            display = display + 'Ohm '
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            unit = 'ohm'
        # Hz icon in MkΩHz (space appended)
        bitmask = 0x80
        if dlist[21] & bitmask == bitmask:
            display = display + 'Hz '  # todo check
            dlist[21] = dlist[21] & ~bitmask  # clear bits
            unit = 'Hz'
        # AC Icon (space appended)
        bitmask = 0x02
        if dlist[10] & bitmask == bitmask:
            display = display + 'AC '
            dlist[10] = dlist[10] & ~bitmask  # clear bits
            unit = unit + 'AC'
        # DC Icon (space appended)
        bitmask = 0x04
        if dlist[10] & bitmask == bitmask:
            display = display + 'DC '
            dlist[10] = dlist[10] & ~bitmask  # clear bits
            unit = unit + 'DC'
        # Percent Icon (space appended)
        bitmask = 0x40
        if dlist[19] & bitmask == bitmask:
            display = display + '% '
            dlist[19] = dlist[19] & ~bitmask  # clear bits
            unit = "%"
        # hfe Icon (space appended)
        bitmask = 0x80
        if dlist[19] & bitmask == bitmask:
            display = display + 'hfe '
            dlist[19] = dlist[19] & ~bitmask  # clear bits
            unit = "hfe"
        # The following are flags - appended space separated.

        # Diode Icon
        bitmask = 0x01
        if dlist[10] & bitmask == bitmask:
            flags['diode'] = True  # todo check
            dlist[10] = dlist[10] & ~bitmask  # clear bits
        # Buzzer Icon
        bitmask = 0x60  # combine two flags
        if dlist[10] & bitmask == bitmask:
            flags['beep'] = True  # todo check
            dlist[10] = dlist[10] & ~bitmask  # clear bits
        # Unknown (dot) Icon (space appended)
        else:
            bitmask = 0x20
            if dlist[10] & bitmask == bitmask:
                flags['D10x20'] = True  # todo unknown
                dlist[10] = dlist[10] & ~bitmask  # clear bits
        # Max-Min icon
        bitmask = 0x0E
        if dlist[19] & bitmask == bitmask:
            flags['min-max'] = True  # todo check
            dlist[19] = dlist[19] & ~bitmask  # clear bits
        else:
            # Min icon (space appended)
            bitmask = 0x02
            if dlist[19] & bitmask == bitmask:
                flags['min'] = True
                dlist[19] = dlist[19] & ~bitmask  # clear bits
            else:
                # Max icon (space appended)
                bitmask = 0x08
                if dlist[19] & bitmask == bitmask:
                    flags['max'] = True
                    dlist[19] = dlist[19] & ~bitmask  # clear bits
        # USB Icon (space appended)
        bitmask = 0x01
        if dlist[19] & bitmask == bitmask:
            flags['usb'] = True  # todo check
            dlist[19] = dlist[19] & ~bitmask  # clear bits
        # Auto Icon (space appended)
        bitmask = 0x20
        if dlist[18] & bitmask == bitmask:
            flags['auto'] = True
            dlist[18] = dlist[18] & ~bitmask  # clear bits
        # Battery Low Icon (space appended)
        bitmask = 0x80
        if dlist[10] & bitmask == bitmask:
            flags['low battery'] = True
            dlist[10] = dlist[10] & ~bitmask  # clear bits
        # deal with the bar
        bar = 0
        for idx in range(11, 19):
            if idx < 18:
                r = 8
            else:
                r = 4
            bitmask = 0x01
            for b in range(r):
                if dlist[idx] & bitmask == bitmask:
                    bar = bar + 1
                    dlist[idx] = dlist[idx] & ~bitmask
                bitmask = bitmask * 2
        flags['bar'] = bar
        # Finally, need to check the bits.  Through the program, used bits should've been cleared.  So, here is the
        #   check string:
        for idx, d in enumerate(dlist):
            if d != __tp8236_checkdata__[idx]:
                errstr = f'There are unrecognized bits in received data at byte {idx} (0x{d:02X})'
                errstr = errstr + f'\n  Full string: {datastring}'
                print(errstr)
                raise ValueError(errstr)
        if value is not None:
            value = value * mult
        return DmmMeasurement(timestamp=data['timestamp'], rawdata=data['rawdata'], display=display,
                              value=value, units=unit, flags=flags, name=self.devName)

    def __serial_thread__(self):
        """
        Thread used to run the serial port.  The serial port is queried every 100 mSec until it has been closed.
        :return: None
        """
        while self.__comPort__.isOpen():
            # READ SERIAL PORT
            new_data = self.__comPort__.read_all()
            if len(new_data) > 0:
                # append the data to the byte buffer
                # Pop the new data into the data buffer
                for b in new_data:
                    self.__rawdata__.append(b)
            # search for synchronization byte.  Likely in front but could come in asynchronous.  This is most like
            while len(self.__rawdata__) > 22:
                while len(self.__rawdata__) > 1:
                    if (self.__rawdata__[0] == __tp8236_checkdata__[0] and
                            self.__rawdata__[1] == __tp8236_checkdata__[1]):
                        break
                    self.__rawdata__.pop(0)  # not found.  Discard lead byte, keep looking!
                # new_frame holds the 22 data bytes.  This is only filled if there are 22 raw data bytes.  The first two
                #   bytes have already at this point been verified as the synchronization byte.
                while len(self.__rawdata__) >= 22:
                    new_frame = []
                    for j in range(22):
                        # Fill the new frame with exactly 22 bytes.
                        new_frame.append(self.__rawdata__.pop(0))
                    # todo get timestamp
                    timestamp = None
                    # Create the measurement structure.  The two required items are the timestamp and data.  No further
                    #   action will occur in the thread.  This will be processed in as the measurement is queried, in
                    #   the non-threaded task.
                    new_measurement = {"timestamp": timestamp, "rawdata": new_frame}
                    if len(self.__measurements__) >= self.__depth__:
                        #  Remove the oldest measurements to make room
                        self.__measurements__.pop(0)  #
                    self.__measurements__.append(new_measurement)  # add new data at the beginning of the queue.
            time.sleep(0.05)  # wait for next data


if __name__ == '__main__':
    print('Welcome to the TP8236 Remote Display')
    portDevList = []
    indexes = []
    for index, comport in enumerate(serial.tools.list_ports.comports()):
        # if any([desc in comport.description for desc in ('UART Bridge', 'USB Serial Port', 'User UART')]):
        indexes.append(str(index))
        portDevList.append(comport)
        print(f'  {index}: {portDevList[index].description}')
    inp = input('Please select from one of these ports: ')
    if len(indexes) == 0:
        dmm = TP8236(name="My Dmm")
        # must be a dummy test
    elif inp not in indexes:
        print("Invalid Selection")
        sys.exit(1)
    else:
        dmm = TP8236(portDevList[int(inp)])
    if len(indexes) > 0:
        number_of_samples = 100
        for i in range(number_of_samples):
            time.sleep(.1)
            reading = dmm.read()
            if reading is not None:
                print(f'{reading}')
        dmm.close()
