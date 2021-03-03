import setuptools

setuptools.setup(
	name = "psi_test_setup",
	version = "0.0.0",
	author = "Matias H. Senger",
	author_email = "m.senger@hotmail.com",
	description = "Control the PSI test setup from Python.",
	packages = setuptools.find_packages(),
	classifiers = [
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: Raspberry Pi",
	],
)
