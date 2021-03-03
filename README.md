# psi_test_setup

Package to control the test setup from Python.

## Instalation

Clone the repository wherever you like in your Raspberry Pi and then run

```
pip3 install -e .
```

## Usage example

```Python
import psi_test_setup
import time

with psi_test_setup.DigitalTDCTestSetup() as setup:
	for k in range(555):
		print(k)
		setup.set_delay(
			chip_number = 1,
			delay_10ps = k,
		)
		setup.run_measure_sequence()
		time.sleep(55e-3)
```
