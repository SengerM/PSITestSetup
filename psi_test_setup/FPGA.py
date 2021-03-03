import spidev
import time

def answer2string(answer):
	string = f'{[f"{byte:0>8b}" for byte in answer]}'
	string = string.replace('0b','').replace(',','').replace('[','').replace(']','').replace("'",'')
	return string

class FPGA:
	def __init__(self):
		self.spi = spidev.SpiDev(0,0)
		self.spi.max_speed_hz = 1200000
	
	def send_and_receive(self, msg: str):
		# <msg> is a string with the binary command, e.g. msg = '10010000 10010001'.
		if not isinstance(msg, str):
			raise TypeError(f'<msg> must be a string containing the sequence of "ones" and "zeros" that form the command in binary format, e.g. msg = "10010000 10010001". Received {msg} of type {type(msg)}.')
		msg = msg.replace(' ', '')
		if len(msg) != 16:
			raise ValueError(f'<msg> must be a string with 16 characters, one for each bit. Received {msg} which has {len(msg)} characters instead.')
		for c in msg:
			if c not in ['0', '1']:
				raise ValueError(f'<msg> must be a string containing only zeros and ones ("0", "1"). Found "{c}" within <msg>.')
		answer = self.spi.xfer2([int(msg[:8],2), int(msg[8:],2)])
		return answer2string(answer)
