from .BaseBoardFPGA import BaseBoardFPGA
from .BaseBoardDACs import BaseBoardDACs
import time
import pandas
from scipy import interpolate
import numpy as np

FPGA_COMMANDS_PROTOTYPES = {
	# `0` or `1`: Fixed values.
	# `X`: Don't care.
	# `_`: Data must go here.
	# ` `: Just for aesthetic purposes.
	'set_SEL': '0000 XXXX XXXX ____',
	'set_BLOCK_RESET': '0001 XXXX XXXX XXX_',
	'set_BLOCK_HOLD': '0010 XXXX XXXX XXX_',
	'set_POLARITY': '0011 XXXX XXXX XXX_',
	'set_RESET_RELEASE_TIME': '0100 XX__ ____ ____',
	'set_AOUT_RESET_RELEASE_TIME': '0101 XX__ ____ ____',
	'set_MEASURE_TIME': '0110 XX__ ____ ____',
	'CMD_ENA': '1001 XXXX XXXX XXX_',
}

MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD = {
	'DELAY': 'UC1',
	'PR_BIAS2': 'UC5',
	'PR_BIAS0': 'UC7',
	'PR2_P': 'UC8',
	'PR2_N': 'UC9',
	'PR2_CASC': 'UC10',
	'PR2_BIAS0': 'UC11',
	'INT_RP': 'UC12',
	'INT_RN': 'UC13',
	'INT_FB2': 'UC14',
	'INT_FB1': 'UC15',
	'COMP_BIAS': 'UC16',
	'AOUT_REF': 'UC20',
	'AOUT_BIAS': 'UC21',
	'Vaout': 'UC22',
	'COMP2_THR': 'UC2',
	'COMP1_THR': 'UC3',
	'PR_FB': 'UC4',
	'PR_BIAS1': 'UC6',
}

def create_command_string(command_prototype:str, data:str)->str:
	"""Given a command prototype and some data, returns the command ready
	to be sent to the FPGA.
	
	Parameters
	----------
	command_prototype: str
		The prototype of the command, e.g. `'0100 XX__ ____ ____'` where
		`0` and `1` are fixed values, `X` is "don't care" and `_` is "put
		here data" (white spaces are removed, just there for aesthetic
		reasons).
	data: str
		A string of binary data, e.g. `0110100100`.
	"""
	COMMAND_PROTOTYPE_ALLOWED_CHARS = {'0','1','X','_',' '}
	DATA_ALLOWED_CHARS = {'0','1'}
	if not isinstance(command_prototype, str):
		raise TypeError(f'`command_prototype` must be a string.')
	if not isinstance(data, str):
		raise TypeError(f'`data` must be a string.')
	if not set(command_prototype).union(COMMAND_PROTOTYPE_ALLOWED_CHARS) == COMMAND_PROTOTYPE_ALLOWED_CHARS:
		raise ValueError(f'The only allowed characters for `command_prototype` are {repr(COMMAND_PROTOTYPE_ALLOWED_CHARS)}, received {repr(command_prototype)}.')
	if not set(data).union(DATA_ALLOWED_CHARS) == DATA_ALLOWED_CHARS:
		raise ValueError(f'The only allowed characters for `data` are {repr(DATA_ALLOWED_CHARS)}, received {repr(data)}.')
	
	cmd = command_prototype.replace(' ','')
	if len(data) != cmd.count('_'):
		raise ValueError(f'Cannot fit `data={repr(data)}` in the `command_prototype={repr(command_prototype)}`.')
	cmd = cmd[:-len(data)] + data
	cmd = cmd.replace('X','0')
	return cmd

class PIX_V1_SW_28_10_19_TestSetup:
	"""Usage example:
	```
	from psi_test_setup.PIX_V1_SW_28_10_19_TestSetup import PIX_V1_SW_28_10_19_TestSetup
	from time import sleep

	VOLTAGES = {
		'DELAY': 1,
		'PR_BIAS2': 0,
		'PR_BIAS0': .5,
		'PR2_P': .2,
		'PR2_N': 1.1,
		'PR2_CASC': 1.2,
		'PR2_BIAS0': .1,
		'INT_RP': .3,
		'INT_RN': .4,
		'INT_FB2': .6,
		'INT_FB1': .7,
		'COMP_BIAS': .8,
		'AOUT_REF': .9,
		'AOUT_BIAS': .44,
		'Vaout': .11,
		'COMP2_THR': .99,
		'COMP1_THR': .05,
		'PR_FB': .66,
		'PR_BIAS1': 1.15,
	}

	setup = PIX_V1_SW_28_10_19_TestSetup()

	for signal in VOLTAGES:
		setup.set_analog_signal_voltage(signal, VOLTAGES[signal])

	with setup: # The power supply and the voltages are enabled here, otherwise they are all off.
		print(f'Now commuting output!')
		while True:
			setup.set_BLOCK_HOLD('1')
			sleep(1)
			setup.set_BLOCK_HOLD('0')
			sleep(1)
	```
	"""
	def __init__(self):
		self._DACs = BaseBoardDACs()
		self._FPGA = BaseBoardFPGA()
		self.send_command_to_FPGA('CMD_ENA', '1') # Enable FPGA communication.
		self._configured_voltages_for_the_analog_signals = {}
	
	def __enter__(self):
		# Enable power voltage ---
		for signal_name in {'Uio','US1'}:
			self._DACs.set_voltage(base_board_signal_name=signal_name, V=1.2)
		self._we_are_inside_a_with_statement = True
		# Enable analog voltages ---
		for signal_name in self._configured_voltages_for_the_analog_signals:
			self._DACs.set_voltage(
				base_board_signal_name = MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD[signal_name],
				V = self._configured_voltages_for_the_analog_signals[signal_name],
			)
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		# Disable analog voltages ---
		for signal_name in MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD:
			self._DACs.set_voltage(
				base_board_signal_name = MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD[signal_name],
				V = 0,
			)
		# Disable power voltage ---
		for signal_name in {'Uio','US1'}:
			self._DACs.set_voltage(base_board_signal_name=signal_name, V=0)
		self._we_are_inside_a_with_statement = False
	
	def send_command_to_FPGA(self, cmd_name:str, data:str=None):
		"""Send an SPI command to the FPGA.
		
		Parameters
		----------
		cmd_name: str
			The name of the command. This must be one of the options in 
			the dictionary `FPGA_COMMANDS_PROTOTYPES` defined in this file.
		data: str, optional
			A string with the binary data for the command, if required.
		
		Returns
		-------
		fpga_answer: str
			Whatever the FPGA answers.
		"""
		if cmd_name not in FPGA_COMMANDS_PROTOTYPES:
			raise ValueError(f'`cmd_name` {repr(cmd_name)} not found within the available commands {repr(set(FPGA_COMMANDS_PROTOTYPES.keys()))}.')
		cmd_string = create_command_string(FPGA_COMMANDS_PROTOTYPES[cmd_name], data)
		return self._FPGA.send_and_receive(cmd_string)
	
	def set_SEL(self, SEL:int):
		if not isinstance(SEL, int) or not 0<=SEL<=15:
			raise ValueError(f'`SEL` must be an integer number satisfying `0<=SEL<=15`, received {repr(SEL)}.')
		self.send_command_to_FPGA('set_SEL', f'{SEL:04b}')
	
	def set_BLOCK_RESET(self, BLOCK_RESET:str):
		if not BLOCK_RESET in {'0','1'}:
			raise ValueError(f'`BLOCK_RESET` must be either "0" or "1", received {repr(BLOCK_RESET)}.')
		self.send_command_to_FPGA('set_BLOCK_RESET',BLOCK_RESET)
	
	def set_BLOCK_HOLD(self, BLOCK_HOLD:str):
		if not BLOCK_HOLD in {'0','1'}:
			raise ValueError(f'`BLOCK_HOLD` must be either "0" or "1", received {repr(BLOCK_HOLD)}.')
		self.send_command_to_FPGA('set_BLOCK_HOLD',BLOCK_HOLD)
	
	def set_POLARITY(self, POLARITY:str):
		if not POLARITY in {'0','1'}:
			raise ValueError(f'`POLARITY` must be either "0" or "1", received {repr(POLARITY)}.')
		self.send_command_to_FPGA('set_POLARITY',POLARITY)
	
	def set_RESET_RELEASE_TIME(self, RESET_RELEASE_TIME:int):
		if not isinstance(RESET_RELEASE_TIME, int) or not 0<=RESET_RELEASE_TIME<2**10:
			raise ValueError(f'`RESET_RELEASE_TIME` must be an integer number satisfying `0<=RESET_RELEASE_TIME<2**10`, received {repr(RESET_RELEASE_TIME)}.')
		self.send_command_to_FPGA('set_RESET_RELEASE_TIME',f'{RESET_RELEASE_TIME:010b}')
	
	def set_AOUT_RESET_RELEASE_TIME(self, AOUT_RESET_RELEASE_TIME:int):
		if not isinstance(AOUT_RESET_RELEASE_TIME, int) or not 0<=AOUT_RESET_RELEASE_TIME<2**10:
			raise ValueError(f'`AOUT_RESET_RELEASE_TIME` must be an integer number satisfying `0<=AOUT_RESET_RELEASE_TIME<2**10`, received {repr(AOUT_RESET_RELEASE_TIME)}.')
		self.send_command_to_FPGA('set_AOUT_RESET_RELEASE_TIME',f'{AOUT_RESET_RELEASE_TIME:010b}')
	
	def set_MEASURE_TIME(self, MEASURE_TIME:int):
		if not isinstance(MEASURE_TIME, int) or not 0<=MEASURE_TIME<2**10:
			raise ValueError(f'`MEASURE_TIME` must be an integer number satisfying `0<=MEASURE_TIME<2**10`, received {repr(MEASURE_TIME)}.')
		self.send_command_to_FPGA('set_MEASURE_TIME',f'{MEASURE_TIME:010b}')
	
	def set_analog_signal_voltage(self, signal_name:str, voltage:float):
		if signal_name not in MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD:
			raise ValueError(f'The `signal_name` must be one of {sorted(MAPPING_OF_SIGNALS_FROM_THE_STRUCTURE_TO_THE_BASE_BOARD.keys())} but received {signal_name}.')
		if not isinstance(voltage, (float, int)) or not 0<=voltage<=1.2:
			raise ValueError(f'`voltage` must be a number between 0 and 1.2, but received {voltage}.')
		self._configured_voltages_for_the_analog_signals[signal_name] = voltage
