from smbus2 import SMBus

class DAC:
	# This class is intented to control a MAX5825BAUP+.
	# This is probably not the best implementation for the DACs, 
	# but I just need something that works and this works.
	
	def __init__(self, i2c_bus=1, dac_i2c_address=0b00010011):
		self.i2c_bus = SMBus(i2c_bus)
		self.dac_i2c_address = dac_i2c_address
	
	def reset(self):
		# Command "SW_RESET" in table 4, p. 23 here https://www.mouser.ch/datasheet/2/256/MAX5823-MAX5825-1515715.pdf
		self.i2c_bus.write_i2c_block_data(
			i2c_addr = self.dac_i2c_address, 
			register = 0b00110101, 
			data = [0b10010110, 0b00110000],
		)
	
	def set_output(self, channel: int, mV: int):
		# "CODEn_LOADn" in table 4, p. 23 here https://www.mouser.ch/datasheet/2/256/MAX5823-MAX5825-1515715.pdf
		if not isinstance(mV, int):
			raise TypeError(f'<mV> must be an integer number, received {mV} of type {type(mV)}.')
		if not isinstance(channel, int):
			raise TypeError(f'<channel> must be an integer number, received {channel} of type {type(channel)}.')
		if not 0 <= channel <= 7:
			raise ValueError(f'<channel> must be in {{0, 1, ..., 7}}. Received {channel}. ')
		if not 0 <= mV <= 2047:
			raise ValueError(f'<mV> must be between 0 and 2047, received {mV}.')
		self.i2c_bus.write_i2c_block_data(
			i2c_addr = self.dac_i2c_address,
			register = 0b10110000 | channel,
			data = [(2*mV & 0xFF0) >> 4, (2*mV & 0x0F) << 4],
		)
