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
	def __init__(self):
		self._DACs = BaseBoardDACs()
		self._FPGA = BaseBoardFPGA()
		
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
	
	def __enter__(self):
		for signal_name in {'Uio','US1'}:
			self._DACs.set_voltage(base_board_signal_name=signal_name, V=1.2)
		self.send_command_to_FPGA('CMD_ENA', '1') # Enable FPGA communication.
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		for signal_name in {'Uio','US1'}:
			self._DACs.set_voltage(base_board_signal_name=signal_name, V=0)
		self.send_command_to_FPGA('CMD_ENA', '0') # Disable FPGA communication.
