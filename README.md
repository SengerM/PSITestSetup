# PSI Test Setup Raspberri Pi

Package to control the test setup from Python.

## Instalation

Clone the repository wherever you like in your Raspberry Pi and then run

```
pip3 install -e .
```

Otherwise just run
```
pip3 install git+https://github.com/SengerM/PSITestSetupRaspberriPi
```
and it will automatically be cloned in a default location.

This is a pure Python package and should not interfere with anything.

## Digital TDC test setup

Up to now I have only implemented the ```DigitalTDCTestSetup``` class which is intended to be used to measure the digital TDC of Stephan Wiederkehr. This class should be easy to adapt (if not alredy working) to other "adapter board with two delay chips".

### Usage example

```Python
import psi_test_setup
import time

with psi_test_setup.DigitalTDCTestSetup() as setup: # The <with> block ensures the initialization and finalization are done automatically and properly.
	for delay_chip in ['A','B']:
		setup.set_D( # This sets the delay D[9:0].
			delay_chip = delay_chip,
			D = 0, # This is approximately in tens of picosecond.
		)
		setup.set_FTUNE( # Sets the voltage in the FTUNE pin.
			delay_chip = delay_chip,
			FTUNE_V = 0, 
		)
	for k in range(9):
		setup.run_measure_sequence()
		time.sleep(0.1)
```

### Warm up period

Note that when entering the ```with``` block there is a default warm up period of 5 minutes, I have observed that the delay is very sensitive to this warm up period. You can change this like this:

```Python
with psi_test_setup.DigitalTDCTestSetup(warm_up_seconds=0) as setup: # No warm up.
	...
```

### Calibration

The relation between the value of ```D``` and ```F_TUNE``` vs the delay that is produced can be calibrated. For this you must first measure the average delay obtained as a function of ```D``` and as a function of ```FTUNE``` voltage for each of the two delay chips ```A``` and ```B```. Then you have to produce two calibration files using this information, see examples of calibration files in [this link](https://github.com/SengerM/PSITestSetup/tree/main/doc/example_calibration_files). After this you can load the calibration files as follows:

```Python
with psi_test_setup.DigitalTDCTestSetup() as setup:
	setup.load_calibration_files(
		D_calibration_file = '/path/to/D_calibration_file.csv',
		FTUNE_calibration_file = '/path/to/FTUNE_calibration_file.csv',
	)
	setup.set_delay(100e-12) # Based on the calibration it chooses the best combination of D and FTUNE to obtain a Delta_t of 100e-12 s between start and stop signals produced by the delay chips.
```
If you place the files in ```~/calibration_files``` then you don't need to load them manually as they will automatically be loaded by the module when required. In this case you can just do

```Python
with psi_test_setup.DigitalTDCTestSetup() as setup:
	setup.set_delay(100e-12) # Calibration files are automatically loaded the first time that <set_delay> is called.
```
