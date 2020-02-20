import json
from pathlib import Path
import subprocess
import shlex
import os
import re

def parse_json_file(file_path):
    with open(file_path, 'r') as probe_config_file:
        probe_file_contents = probe_config_file.read()

    return json.loads(probe_file_contents)

def load_modules():
    modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')

    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(modules_dir).glob('**/*.json')

    modules = {}

    for path in pathlist:
        parsed = parse_json_file(str(path))
        for key, value in parsed.items():
            if key in modules:
                raise ValueError('Duplicate module')

            modules[key] = value

    return modules

modules = load_modules()

def split_for_format(command):
    symbol = '%'
    output = ['']

    preceded_by_symbol = False
    for char in command:
        if char == symbol:
            if preceded_by_symbol:
                preceded_by_symbol = False
                output[-1] += symbol
            else:
                preceded_by_symbol = True
        else:
            if preceded_by_symbol:
                preceded_by_symbol = False
                output.append('')
            output[-1] += char

    if preceded_by_symbol:
        output.append('')

    return output

def insert_values(command, values):
    split_command = split_for_format(command)

    if len(split_command) != len(values) + 1:
        raise ValueError('Invalid number of values for command')

    output = split_command[0]

    for value, rest in zip(values, split_command[1:]):
        output += shlex.quote(value) + rest

    return output

def insert_named_values(string, values):
    return re.sub(r'{([a-zA-Z0-9_]+)}', lambda m: values[m.group(1)], string)

def populate_command(command, inputs, config, bound_values):
    values = list(map(lambda key: config[key], inputs))
    return insert_values(command, values)

def run_module(module_type, config, bound_values):
    module = modules[module_type]

    populated_config = {k: insert_named_values(v, bound_values) for k, v in config.items()}
    quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}

    populated_command = insert_named_values(module['command'], quoted_config)

    script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = script.communicate()

    output = output.decode('utf-8')
    error = error.decode('utf-8')

    if error != '':
        print(error)
        return False
    else:
        print(output)
        return output

def handle_config(file_path, current_commit_dir, previous_commit_dir):
    print('Handling ', file_path)
    config = parse_json_file(file_path)
    bound_values = {}

    for module in config:
        output = run_module(module['type'], module['config'], bound_values)
        if 'name' in module:
            bound_values[module['name']] = output

def iterate_over_configs(current_commit_dir, previous_commit_dir):
    probes_dir = os.path.join(current_commit_dir, 'monitoring')

    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(probes_dir).glob('**/*.json')

    for path in pathlist:
        path_str = str(path)
        handle_config(path_str, current_commit_dir, previous_commit_dir)

print(split_for_format('echo'))
print(split_for_format('echo %'))
print(split_for_format('echo %%'))
print(split_for_format('echo %%%'))
print(split_for_format('echo %%%%'))
print(split_for_format('echo % %'))

print(insert_values('echo', []))
print(insert_values('echo %', ['test string']))
print(shlex.split(insert_values('echo % % % %', ['test string', 'rm -rf', "'", '; "blah"; rm -rf'])))

iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))