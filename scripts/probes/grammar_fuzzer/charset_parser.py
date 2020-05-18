from unicode_range import maximum_unicode_codepoint

escaped_values = {
	# See https://github.com/antlr/antlr4/blob/8c50731894e045be3e19799b84b39e9a60e2ab61/tool/src/org/antlr/v4/misc/CharSupport.java#L26
	'n': '\n',
	'r': '\r',
	'b': '\b',
	't': '\t',
	'f': '\f',
	'\\': '\\',
	# The following can be escaped in charset
	# See https://github.com/antlr/antlr4/blob/8c50731894e045be3e19799b84b39e9a60e2ab61/tool/src/org/antlr/v4/misc/EscapeSequenceParsing.java#L159
	'-': '-',
	']': ']'
}

class EscapeParseError(Exception):
	pass


# Adapted from https://github.com/antlr/antlr4/blob/8c50731894e045be3e19799b84b39e9a60e2ab61/tool/src/org/antlr/v4/misc/EscapeSequenceParsing.java#L83
def parse_escape(s, start_offset):
	# Original Java code has to handle unicode codepoints which consist of more than one character,
	# however in Python 3.3+, we don't have to worry about this: https://stackoverflow.com/a/42262842

	offset = start_offset

	if offset + 2 > len(s) or s[offset] != '\\':
		raise EscapeParseError('Escape must have at least two characters starting with \\')

	offset += 1  # Move past backslash
	escaped = s[offset]
	offset += 1  # Move past escaped character

	if escaped == 'u':
		if offset + 3 > len(s):
			# \u{1} is the shortest we support
			raise EscapeParseError('Shortest unicode escape is \\u{0}')

		hex_start_offset = None
		hex_end_offset = None  # Exclusive

		if s[offset] == '{':
			# \u{...}
			hex_start_offset = offset + 1

			try:
				hex_end_offset = s.index('}', hex_start_offset)
			except ValueError:
				raise EscapeParseError('Missing closing bracket for unicode escape')

			offset = hex_end_offset + 1
		else:
			# \uXXXX
			if offset + 4 > len(s):
				raise EscapeParseError('Non-bracketed unicode escape must be of form \\uXXXX')

			hex_start_offset = offset
			hex_end_offset = hex_start_offset + 4
			offset = hex_end_offset

		try:
			codepoint = int(s[hex_start_offset:hex_end_offset], 16)
		except ValueError:
			raise EscapeParseError('Invalid hex value')

		if codepoint < 0 or codepoint > maximum_unicode_codepoint:
			raise EscapeParseError('Invalid unicode codepoint')

		return (codepoint, offset)

	if escaped in ('p', 'P'):
		raise EscapeParseError('Unicode properties (\\p{...}) are not supported')

	if escaped in escaped_values:
		return (ord(escaped_values[escaped]), offset)

	raise EscapeParseError('Invalid escaped value')


# Adapted from https://github.com/antlr/antlr4/blob/8c50731894e045be3e19799b84b39e9a60e2ab61/tool/src/org/antlr/v4/automata/LexerATNFactory.java#L439
def lexer_charset_interval(s):
	assert len(s) > 0, 'Charset cannot be empty'

	ranges = []
	in_range = False

	i = 0
	while i < len(s):
		char = s[i]
		offset = i + 1  # Offset functions differently than in original function

		if char == '-' and not in_range and i != 0 and i != len(s) - 1:
			in_range = True
		else:
			codepoint = None

			if char == '\\':
				codepoint, offset = parse_escape(s, i)
			else:
				codepoint = ord(char)

			if in_range:
				in_range = False
				ranges[-1] = (ranges[-1][0], codepoint + 1)
			else:
				ranges.append((codepoint, codepoint + 1))

		i = offset

	return ranges
