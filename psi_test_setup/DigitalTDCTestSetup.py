from .FPGA import FPGA
import time

_COMMANDS = {
	# See https://drive.switch.ch/index.php/s/u4TGjVyMPjTvswf in /Adapter_TPIX/FPGA/doc/spi2.txt
	'enable':	'1001 0000 1001 0001',
	'disable':	'1001 0000 1001 0000',
	'dummy':	'0000 0000 0000 0000',
	'SeqReset':	'0100 0000 0000 0000',
	'SeqInit':	'0100 1000 0000 0000',
}

class DigitalTDCTestSetup:
	def __enter__(self):
		self.test_setup = _DigitalTDCTestSetup()
		self.test_setup.enable()
		return self.test_setup
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.test_setup.disable()

class _DigitalTDCTestSetup:
	def __init__(self):
		self._fpga = FPGA()
	
	def enable(self):
		self._fpga.send_and_receive(_COMMANDS['enable'])
	
	def disable(self):
		self._fpga.send_and_receive(_COMMANDS['disable'])
	
	def set_delay(self, chip_number: int, delay_10ps: int):
		try:
			chip_number = int(chip_number)
		except:
			raise TypeError(f'<chip_number> must be an integer, received {chip_number} of type {type(chip_number)}.')
		if chip_number not in [1,2]:
			raise ValueError(f'<chip_number> must be either 1 or 2, received {chip_number}.')
		try:
			delay_10ps = int(delay_10ps)
		except:
			raise TypeError(f'<delay_10ps> must be an integer, received {delay_10ps} of type {type(delay_10ps)}.')
		if not 0 <= delay_10ps <= 0b111111111:
			raise ValueError(f'<delay_10ps> must be between 0 and {0b111111111}, received {delay_10ps}.')
		command = '0010' if chip_number == 1 else '0011'
		command += f'{int(delay_10ps):0>12b}'
		self._fpga.send_and_receive(command)
	
	def run_measure_sequence(self):
		self._fpga.send_and_receive(_COMMANDS['SeqReset'])
		time.sleep(10e-3)
		self._fpga.send_and_receive(_COMMANDS['SeqInit'])
		time.sleep(10e-3)
