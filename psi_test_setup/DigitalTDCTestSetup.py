from .FPGA import FPGA
from .DAC import DAC
import time

_COMMANDS = {
	# See https://drive.switch.ch/index.php/s/u4TGjVyMPjTvswf in /Adapter_TPIX/FPGA/doc/spi2.txt
	'enable':	'1001 0000 1001 0001',
	'disable':	'1001 0000 1001 0000',
	'dummy':	'0000 0000 0000 0000',
	'SeqReset':	'0100 0000 0000 0000',
	'SeqInit':	'0100 1000 0000 0000',
}

DAC_OUTPUT_NUMBERS = {
	# Beat sent me this in an email on 10.mar.2021.
	'FINEA': 6,
	'FINEB': 2,
}

class DigitalTDCTestSetup:
	def __enter__(self):
		self.test_setup = _DigitalTDCTestSetup()
		self.test_setup.enable()
		self.test_setup._dac.reset()
		return self.test_setup
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.test_setup.disable()

class _DigitalTDCTestSetup:
	def __init__(self):
		self._fpga = FPGA()
		self._dac = DAC()
	
	def enable(self):
		self._fpga.send_and_receive(_COMMANDS['enable'])
	
	def disable(self):
		self._fpga.send_and_receive(_COMMANDS['disable'])
	
	def set_FTUNE(self, delay_chip: str, FTUNE_V: float):
		# FTUNE_V is in Volt.
		# Set the "F_TUNE" voltage for <delay_chip> A or B.
		# See https://ww1.microchip.com/downloads/en/DeviceDoc/sy89296u.pdf#page=10 for more information on F_TUNE.
		if delay_chip not in ['A','B']:
			raise ValueError(f'<delay_chip> must be either "A" or "B", received {delay_chip}.')
		try:
			FTUNE_V = float(FTUNE_V)
		except:
			raise TypeError(f'<FTUNE_V> must be a float number, received {FTUNE_V} of type {type(FTUNE_V)}.')
		if not 0 <= FTUNE_V <= 1.5:
			raise ValueError(f'<FTUNE_V> must be between 0 and 1.25 V (see https://ww1.microchip.com/downloads/en/DeviceDoc/sy89296u.pdf#page=9), received {FTUNE_V}.')
		self._dac.set_output(
			channel = DAC_OUTPUT_NUMBERS[f'FINE{delay_chip}'],
			mV = int(FTUNE_V*1e3),
		)
	
	def set_D(self, delay_chip: str, D: int):
		# Set the "D[9:0]" bits to <delay_chip> A or B.
		# See https://ww1.microchip.com/downloads/en/DeviceDoc/sy89296u.pdf#page=10 for more information on D[9:0].
		if delay_chip not in ['A','B']:
			raise ValueError(f'<delay_chip> must be either "A" or "B", received {delay_chip}.')
		try:
			D = int(D)
		except:
			raise TypeError(f'<D> must be an integer, received {D} of type {type(D)}.')
		if not 0 <= D <= 0b111111111:
			raise ValueError(f'<D> must be between 0 and {0b111111111}, received {D}.')
		command = '0010' if delay_chip == 'A' else '0011'
		command += f'{int(D):0>12b}'
		self._fpga.send_and_receive(command)
	
	def run_measure_sequence(self):
		self._fpga.send_and_receive(_COMMANDS['SeqReset'])
		time.sleep(10e-3)
		self._fpga.send_and_receive(_COMMANDS['SeqInit'])
		time.sleep(10e-3)
