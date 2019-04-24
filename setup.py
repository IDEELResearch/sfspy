#! /usr/bin/env python3

from setuptools import setup

setup(
	name = "sfspy",
	version = "0.1.0",
	description = "A Python interface for manipulating site frequency spectra (SFS)",
	url = "http://github.com/IDEELResearch/sfspy",
	author = "Andrew Parker Morgan",
	author_email='andrew.parker.morgan@gmail.com',
	license= "MIT",
	packages = ["sfspy"],
	scripts=["bin/sfspy"],
	install_requires = [
		"numpy",
		"scipy"
	],
	zip_safe = False
)
