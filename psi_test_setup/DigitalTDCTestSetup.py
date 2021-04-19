from .FPGA import FPGA
from .DAC import DAC
import time
import pandas
from scipy import interpolate
import numpy as np

_FPGA_COMMANDS = {
	# See https://drive.switch.ch/index.php/s/u4TGjVyMPjTvswf in /Adapter_TPIX/FPGA/doc/spi2.txt
	'enable': '1001 0000 1001 0001',
	'disable': '1001 0000 1001 0000',
	'dummy': '0000 0000 0000 0000',
	'run_sequencer': '0100 0000 0000 0000',
	'enter_read_mode': '1100 0000 0000 0000', # This is called "cmd_read_start" in the Verilog code.
	'read': '1101 0000 0000 0000', # This is called "cm_read" in the Verilog code.
	'exit_read_mode': '1110 0000 0000 0000', # This is called "cmd_read_last" in the Verilog code.
}

class DigitalTDCTestSetup:
	def __init__(self, warm_up_seconds=60*5):
		try:
			self.warm_up_seconds = float(warm_up_seconds)
		except: 
			raise ValueError(f'<warm_up_seconds> must be a float number, received {warm_up_seconds} of type {type(warm_up_seconds)}.')
	
	def __enter__(self):
		self.test_setup = _DigitalTDCTestSetup()
		self.test_setup.enable() # Turn on the delay chips.
		self.test_setup.set_VDD(mV=1200) # Turn on the test structure.
		time.sleep(self.warm_up_seconds)
		return self.test_setup
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.test_setup.set_VDD(mV=0) # Turn off the test structure.
		self.test_setup.disable() # Turn off the delay chips.

class _DigitalTDCTestSetup:
	def __init__(self):
		self._fpga = FPGA()
		self._dac1 = DAC(dac_i2c_address=0b00010011) # In this DAC there are FINEA and FINEB.
		self._dac2 = DAC(dac_i2c_address=0x10) # In this DAC there is VDD.
	
	def enable(self):
		self._fpga.send_and_receive(_FPGA_COMMANDS['enable'])
	
	def disable(self):
		self._fpga.send_and_receive(_FPGA_COMMANDS['disable'])
	
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
		self._dac1.set_output(
			channel = 6 if delay_chip == 'A' else 2,
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
		if not 0 <= D <= 0b1111111111:
			raise ValueError(f'<D> must be between 0 and {0b111111111}, received {D}.')
		command = '0010' if delay_chip == 'A' else '0011'
		command += f'{int(D):0>12b}'
		self._fpga.send_and_receive(command)
	
	def set_VDD(self, mV: int):
		self._dac2.set_output(
			channel = 1,
			mV = mV,
		)
	
	def run_measure_sequence(self):
		time.sleep(10e-3)
		self._fpga.send_and_receive(_FPGA_COMMANDS['run_sequencer'])
		time.sleep(10e-3)
	
	def load_calibration_files(self, D_calibration_file: str, FTUNE_calibration_file: str):
		D_data = pandas.read_csv(
			D_calibration_file,
			delimiter = ',',
			comment = '#',
		)
		self.time_to_D = {}
		for delay_chip in sorted(set(D_data['delay_chip'])):
			self.time_to_D[delay_chip] = interpolate.interp1d(
				x = D_data.loc[D_data['delay_chip']==delay_chip, 'average delay (s)'],
				y = D_data.loc[D_data['delay_chip']==delay_chip, 'D'],
			)
		FTUNE_data = pandas.read_csv(
			FTUNE_calibration_file,
			delimiter = ',',
			comment = '#',
		)
		self.time_to_FTUNE = {}
		self.FTUNE_to_time = {}
		for delay_chip in sorted(set(D_data['delay_chip'])):
			self.time_to_FTUNE[delay_chip] = interpolate.interp1d(
				x = FTUNE_data.loc[FTUNE_data['delay_chip']==delay_chip, 'average delay (s)'],
				y = FTUNE_data.loc[FTUNE_data['delay_chip']==delay_chip, 'FTUNE (V)'],
			)
			self.FTUNE_to_time[delay_chip] = interpolate.interp1d(
				y = FTUNE_data.loc[FTUNE_data['delay_chip']==delay_chip, 'average delay (s)'],
				x = FTUNE_data.loc[FTUNE_data['delay_chip']==delay_chip, 'FTUNE (V)'],
			)
		
		self.D_calibration_data = {}
		for delay_chip in sorted(set(D_data['delay_chip'])):
			self.D_calibration_data[delay_chip] = {}
			self.D_calibration_data[delay_chip]['D'] = np.array(list(D_data.loc[D_data['delay_chip']==delay_chip,'D']))
			self.D_calibration_data[delay_chip]['average delay (s)'] = np.array(list(D_data.loc[D_data['delay_chip']==delay_chip,'average delay (s)']))
	
	def set_delay(self, t: float):
		if not (hasattr(self, 'time_to_D') and hasattr(self, 'time_to_FTUNE') and hasattr(self, 'FTUNE_to_time') and hasattr(self, 'D_calibration_data')):
			try: # Try to automatically load the files in the ~/calibration_files directory.
				self.load_calibration_files(
					D_calibration_file = '~/calibration_files/D_calibration_file.csv',
					FTUNE_calibration_file = '~/calibration_files/FTUNE_calibration_file.csv',
				)
			except FileNotFoundError:
				raise RuntimeError(f'Prior to calling <set_delay> you must load calibration data using the method <load_calibration_files>. Otherwise you can manually set D and FTUNE using <set_D> and <set_FTUNE>.')
		try:
			t = float(t)
		except:
			raise ValueError(f'<delay> must be a float number specifying the delay in seconds. Received {delay} of type {type(delay)}.')
		
		chip_to_use = None
		for delay_chip in self.time_to_D:
			try:
				D = int(np.ceil(self.time_to_D[delay_chip](t)))
				chip_to_use = delay_chip
			except ValueError as e:
				continue
		if chip_to_use is None:
			raise ValueError(f'<t> is outside D calibration range. Received t = {t} s.')
		
		fine_delay_to_remove = ((t - self.D_calibration_data[chip_to_use]['average delay (s)'][self.D_calibration_data[chip_to_use]['D']==D])**2)**.5
		FTUNE_delay_at_0V = self.FTUNE_to_time[chip_to_use](0)
		FTUNE_voltage = self.time_to_FTUNE[chip_to_use](FTUNE_delay_at_0V-fine_delay_to_remove)[0]
		
		for delay_chip in ['A','B']:
			self.set_D(
				delay_chip = delay_chip, 
				D = D if delay_chip == chip_to_use else 0,
			)
			self.set_FTUNE(
				delay_chip = delay_chip, 
				FTUNE_V = FTUNE_voltage if delay_chip == chip_to_use else 0,
			)

	def read_measured_data(self):
		# This assumes that previously <self.run_measure_sequence> has been called so now there is data stored in the RAM memory within the FPGA.
		N_TDC = 4
		self._fpga.send_and_receive(_FPGA_COMMANDS['enter_read_mode'])
		try:
			first = []
			second = []
			for k in range(N_TDC): # There are 4 TDC structures in the test structure.
				first.append(self._fpga.send_and_receive(_FPGA_COMMANDS['read']))
				second.append(self._fpga.send_and_receive(_FPGA_COMMANDS['read']))
		except Exception as e:
			raise e
		finally:
			self._fpga.send_and_receive(_FPGA_COMMANDS['exit_read_mode'])
		
		data = {}
		for k in range(N_TDC):
			data[f'TDC{k+1}'] = {}
			data[f'TDC{k+1}']['counter'] = first[k].replace(' ','')[0:7][::-1]
			data[f'TDC{k+1}']['SAFF'] = f'{first[k]}{second[k]}'.replace(' ','')[-21:]
		return data


