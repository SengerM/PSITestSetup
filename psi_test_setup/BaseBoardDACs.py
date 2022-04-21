import pandas
from pathlib import Path
from smbus2 import SMBus
from .ImmutableButNonEfficientDataFrame import ImmutableButNonEfficientDataFrame

class DAC:
	"""This class is designed such that each object controls a single
	DAC chip. In my base board I have four `MAX5825BAUP+` chips.
	"""
	# You should not use this class, I designed it for internal use.
	def __init__(self, dac_i2c_address, i2c_bus=1):
		self.i2c_bus = SMBus(i2c_bus)
		self.dac_i2c_address = dac_i2c_address
	
	def reset(self):
		"""Reset the DAC using the command `SW_RESET` in table 4, p. 23 
		of [the datasheet](https://www.mouser.ch/datasheet/2/256/MAX5823-MAX5825-1515715.pdf).
		"""
		self.i2c_bus.write_i2c_block_data(
			i2c_addr = self.dac_i2c_address, 
			register = 0b00110101, 
			data = [0b10010110, 0b00110000],
		)
	
	def set_output(self, channel: int, mV: int):
		"""Set the output voltage of one of the channels using the command
		`CODEn_LOADn` in table 4, p. 23 of [the datasheet](https://www.mouser.ch/datasheet/2/256/MAX5823-MAX5825-1515715.pdf).
		Parameters
		----------
		channel: int
			Number of channel to which to set the voltage.
		mV: int
			Value in millivolts to set to the output. 
		"""
		if not isinstance(mV, int):
			raise TypeError(f'`mV` must be an integer number, received object of type {type(mV)}.')
		if not isinstance(channel, int):
			raise TypeError(f'`channel` must be an integer number, received object of type {type(channel)}.')
		if not 0 <= channel <= 7:
			raise ValueError(f'`channel` must be in {{0, 1, ..., 7}}, received {channel}. ')
		if not 0 <= mV <= 2047:
			raise ValueError(f'`mV` must be between 0 and 2047, received {mV}.')
		self.i2c_bus.write_i2c_block_data(
			i2c_addr = self.dac_i2c_address,
			register = 0b10110000 | channel,
			data = [(2*mV & 0xFF0) >> 4, (2*mV & 0x0F) << 4],
		)

BASE_BOARD_DAC_CHIPS = ImmutableButNonEfficientDataFrame(
	pandas.read_csv(Path(__file__).parent.resolve()/Path('base_board_data/DAC_chips.csv'), comment='#')
)
BASE_BOARD_DAC_SIGNALS = ImmutableButNonEfficientDataFrame(
	pandas.read_csv(Path(__file__).parent.resolve()/Path('base_board_data/DAC_signals.csv'), comment='#')
)

class BaseBoardDACs:
	"""Class to wrap all the DACs in the base board, providing access 
	to each signal according to the names given in the "Mezzaine connectors",
	e.g. `UC1`, `UC2`, ...
	"""
	def __init__(self):
		# Open connection with each DAC.
		dacs_df = BASE_BOARD_DAC_CHIPS.df
		dacs_df = dacs_df.set_index(["I2C slave address MSB","I2C slave address LSB"])
		for MSB,LSB in dacs_df.index:
			i2c_address = int(MSB+LSB[2:], 2)
			dacs_df.loc[(MSB,LSB),'DAC'] = DAC(dac_i2c_address = i2c_address)
		
		# Put everything together in a single data frame.
		df = BASE_BOARD_DAC_SIGNALS.df
		df = df.set_index('DAC chip reference in schematic')
		dacs_df = dacs_df.set_index('DAC chip reference in schematic')
		for col in dacs_df.columns:
			df[col] = dacs_df[col]
		df = df.reset_index()
		
		self._dacs_df = df
		
	def set_voltage(self, V:float, base_board_signal_name:str):
		"""Set the output voltage of one of the DACs.
		Parameters
		----------
		V: float
			Voltage value.
		base_board_signal_name: str
			Name of the signal that you want to set the voltage to, e.g.
			"UC1".
		"""
		if base_board_signal_name not in list(BASE_BOARD_DAC_SIGNALS.df['base board signal name']):
			raise ValueError(f"`base_board_signal_name` must be one of {sorted(BASE_BOARD_DAC_SIGNALS.df['base board signal name'])}, received {repr(base_board_signal_name)}.")
		dacs_df = self._dacs_df
		dac = list(dacs_df.loc[dacs_df['base board signal name']==base_board_signal_name,'DAC'])[0]
		channel = list(dacs_df.loc[dacs_df['base board signal name']==base_board_signal_name,'channel within DAC chip'])[0]
		dac.set_output(channel = int(channel), mV = int(V*1000))
