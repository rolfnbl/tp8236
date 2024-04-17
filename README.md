# tp8236
This provides a class interface used to collect data from a TekPower TP8236 datalogging Digital Multimeter.  The TP8236 is an inexpensive DMM with a USB interface and obviously a display used to provide measurement data.  The class model chosen started out as a string with measurements and statuses, which will then morph into a ictionary.

Data is stored as a dictionary.  With available measurements stored there.  If the measurement is unavailable, the value returned will be simply None.

Lets talk units.  The measurements available are:

AC or DC Volts ('VDC', 'mVDC', 'uVDC', 'VAC', 'mVAC', 'uVAC')
AC or DC Amps ('VDC', 'mVDC', 'uVDC', 'VAC', 'mVAC', 'uVAC')
Ohms ('megaohms', 'kiloohms' | 'kohms', 'ohms', 'milliohms', 'microohms')
... more to be added

The class can be threaded or on-demand.  Threaded measurements are continuous, and will store up to 1000 or a defined number of measurements sampled at a specified interval.

![image](https://github.com/rolfnbl/tp8236/assets/118851141/d5ef13af-234f-4249-b03e-e603b944ecc1)


The TP8236 reports it's LCD status eery 250mSec.  The data is organized into 22 bytes, with bitmapping impirically detemined as follows:

    Byte 0: Synchronization Byte (0xaa)
    Byte 1: Synchronization Byte (0xaa)
    Byte 2: Undetermined but constant byte - potentially synchronization (0x52)
    Byte 3: Undetermined but constant byte - potentially synchronization (0x52)
    Byte 4: Undetermined but constant byte - potentially synchronization (0x52)
    Byte 5: Undetermined but constant byte - potentially synchronization (0x52)
    Byte 6: LCD 4th Digit (LSB) map, with preceding decimal point mapped as follows:
    	Bit 7: Preceding (3rd) decimal point
    	Bit 6: 4th Digit (LSB), LCD Segment E
    	Bit 5: 4th Digit (LSB), LCD Segment G
    	Bit 4: 4th Digit (LSB), LCD Segment F
    	Bit 3: 4th Digit (LSB), LCD Segment D
    	Bit 2: 4th Digit (LSB), LCD Segment C
    	Bit 1: 4th Digit (LSB), LCD Segment B
    	Bit 0: 4th Digit (LSB), LCD Segment A
    Byte 7: LCD 3rd Digit (LSB) map, with preceding decimal point mapped as follows:
    	Bit 7: Preceding (2nd) decimal point
    	Bit 6: 3rd Digit, LCD Segment E
    	Bit 5: 3rd Digit, LCD Segment G
    	Bit 4: 3rd Digit, LCD Segment F
    	Bit 3: 3rd Digit, LCD Segment D
    	Bit 2: 3rd Digit, LCD Segment C
    	Bit 1: 3rd Digit, LCD Segment B
    	Bit 0: 3rd Digit, LCD Segment A
    Byte 8: LCD 2nd Digit (LSB) map, with preceding decimal point mapped as follows:
    	Bit 7: Preceding (1st) decimal point
    	Bit 6: 2nd Digit, LCD Segment E
    	Bit 5: 2nd Digit, LCD Segment G
    	Bit 4: 2nd Digit, LCD Segment F
    	Bit 3: 2nd Digit, LCD Segment D
    	Bit 2: 2nd Digit, LCD Segment C
    	Bit 1: 2nd Digit, LCD Segment B
    	Bit 0: 2nd Digit, LCD Segment A
    Byte 9: LCD 1st Digit (LSB) map, with preceding decimal point mapped as follows:
    	Bit 7: 0 (not used)
    	Bit 6: 1st Digit, LCD Segment E
    	Bit 5: 1st Digit, LCD Segment G
    	Bit 4: 1st Digit, LCD Segment F
    	Bit 3: 1st Digit, LCD Segment D
    	Bit 2: 1st Digit, LCD Segment C
    	Bit 1: 1st Digit, LCD Segment B
    	Bit 0: 1st Digit, LCD Segment A
    Byte 10:
    	Bit 7: Battery Icon
    	Bit 6: ignored - possibly the Buzz Icon?
    	Bit 5: Ignored - possibly the Buzz Dot Icon?
    	Bit 4: 0 (not used)
    	Bit 3: Display sign or negative icon
    	Bit 2: DC Icon
    	Bit 1: AC icon
    	Bit 0: ignored - possibly the Diode icon?
    Byte 11:
    	Bit 0...7: Maps to range bars 1...8 
    Byte 12:
    	Bit 0...7: Maps to range bars 9...16 
    Byte 13:
    	Bit 0...7: Maps to range bars 17...24 
    Byte 14:
    	Bit 0...7: Maps to range bars 25...32 
    Byte 15:
    	Bit 0...7: Maps to range bars 33...40 
    Byte 16:
    	Bit 0...7: Maps to range bars 41...48
    Byte 17:
    	Bit 0...7: Maps to range bars 49...56
    Byte 18:
    	Bit 7: 0 (not used)
    	Bit 6: 0 (not used)
    	Bit 5: Auto Icon
    	Bit 4: 0 (not used)
    	Bit 0...3: Maps to range bars 57...60
    Byte 19:
    	Bit 7: 0 (not used)
    	Bit 6: hfe icon
    	Bit 5: Percent icon
    	Bit 4: 0 (not used)
    	Bit 3: MIN icon in "MAX-MIN"
    	Bit 2: dash icon in "MAX-MIN"
    	Bit 1: MAX icon in "MAX-MIN"
    	Bit 0: ignored - possibly the USB icon?
    Byte 20:
    	Bit 7: Farad icon in "munF"
    	Bit 6: nano icon in "munF"
    	Bit 5: micro icon in "munF"
    	Bit 4: milli icon in "munF"
    	Bit 3: 0 (not used)
    	Bit 2: 0 (not used)
    	Bit 1: Deg F icon
    	Bit 0: Deg C icon
    Byte 21:
    	Bit 7: Hz icon in "MkΩHz"
    	Bit 6: Ohm icon in "MkΩHz"
    	Bit 5: kilo icon in icon in "MkΩHz"
    	Bit 4: Mega icon in "MkΩHz"
    	Bit 3: V icon in "umAV"
    	Bit 2: A icon in "umAV"
    	Bit 1: m icon in "umAV"
    	Bit 0: u icon in "umAV"
    	

