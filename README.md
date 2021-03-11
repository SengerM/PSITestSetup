# psi_test_setup

Package to control the test setup from Python.

## Instalation

Clone the repository wherever you like in your Raspberry Pi and then run

```
pip3 install -e .
```

Otherwise just run
```
pip3 install git+https://github.com/SengerM/PSITestSetup
```

## Usage example

```Python
import psi_test_setup
import time

with psi_test_setup.DigitalTDCTestSetup() as setup:
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
