#!/usr/bin/env python3

import argparse
import subprocess
from collections import namedtuple

import antlr_fuzzer

arg_parser = argparse.ArgumentParser(description='Run ANTLR grammar fuzzer')

arg_parser.add_argument('grammar_file', type=str, help='ANTLR grammar file to be used for fuzzing')
arg_parser.add_argument('entry_rule', type=str, help='ANTLR rule to use as initial rule')
arg_parser.add_argument('fuzz_command', type=str, help='command to run with generated input as STDIN')

arg_parser.add_argument('--iterations', type=str, default=100, help='number of iterations')
arg_parser.add_argument('--max_depth', type=str, default=500, help='max depth in grammar to generate')

args = arg_parser.parse_args()

FuzzError = namedtuple('FuzzError', ['stdin', 'stdout', 'stderr', 'returncode'])

fuzz_errors = []

for fuzz_input in antlr_fuzzer.generate(args.grammar_file, args.entry_rule, args.iterations, args.max_depth):
	p = subprocess.Popen(args.fuzz_command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = p.communicate(input=fuzz_input.encode())

	if p.returncode != 0:
		fuzz_errors.append(FuzzError(fuzz_input, stdout.decode('utf-8'), stderr.decode('utf-8'), p.returncode))
		print('ERROR Command exited with nonzero status code', p.returncode)

		print('STDIN:')
		print(fuzz_input)
		print('STDOUT:')
		print(stdout.decode('utf-8'))
		print('STDERR:')
		print(stderr.decode('utf-8'))

		print()
		print()

# print(fuzz_errors)

# p = subprocess.Popen(['rev'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

# stdout_data = p.communicate(input='data_to_write'.encode())[0]

# print(stdout_data)

# stdout_data = p.communicate(input='data_to_write'.encode())[0]

# print(stdout_data)