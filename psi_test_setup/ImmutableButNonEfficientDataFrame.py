class ImmutableButNonEfficientDataFrame:
	"""To store small data frames that should be immutable.
	"""
	def __init__(self, df):
		self._df = df

	@property
	def df(self):
		return self._df.copy()
