from itertools import chain

maximum_unicode_codepoint = 0x10FFFF

def printable_ranges(start, end):
	range_start = None
	ranges = []

	for x in range(start, end):
		if chr(x).isprintable():
			if range_start is None:
				range_start = x
		else:
			if range_start is not None:
				ranges.append((range_start, x))
				range_start = None

	if range_start is not None:
		ranges.append((range_start, end))

	return ranges

def tuple_range(t):
	return range(*t)

def ranges_to_list(ranges):
	return list(chain(*map(tuple_range, ranges)))

printable_unicode_ranges = printable_ranges(0, maximum_unicode_codepoint + 1)
printable_unicode_ranges_list = ranges_to_list(printable_unicode_ranges)