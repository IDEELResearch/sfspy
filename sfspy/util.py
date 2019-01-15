#! /usr/bin/env python3

import numpy as np

from re import match as rematch
from re import sub as resub

def sniff_dims(x):
	pattern = r"\#+dims\="
	if rematch(pattern, x):
		y = resub(pattern, "", x)
		dims = list( map(int, y.split(",")))
		return dims
	else:
		return None

def line_reader(path, comment = "#", fn = None):

	was_file = False
	if not hasattr(path, "read"):
		infile = open(path, "r")
	else:
		infile = path
		was_file = True

	seen_values = False
	dims = None

	for line in infile:
		if line.startswith(comment):
			maybe_dims = sniff_dims(line.strip())
			if maybe_dims:
				dims = maybe_dims
			continue

		pieces = line.strip().split()
		if callable(fn):
			values = list( map(fn, pieces) )
		else:
			values = pieces
		if dims and not seen_values:
			values = np.asarray(values).reshape(dims)
		seen_values = True
		yield values

	if not was_file:
		infile.close()

def lines_as_floats(infile, comment = "#"):
	return line_reader(infile, comment, float)

def lines_as_integers(infile, comment = "#"):
	return line_reader(infile, comment, int)
