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

![image](https://github.com/rolfnbl/tp8236/assets/118851141/54e49083-eca2-4375-afbb-2138639f3320)


