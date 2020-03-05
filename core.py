import json
import logging
import os
import re
import shlex
import subprocess
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path


# Replace curly-brace surrounded variables with
# the corresponding value in 'values'
# Example: insert_named_valued('Hello {name}', {'name': 'Bob'})
# -> 'Hello Bob'
# Variables with no corresponding value are left as is (i.e. "{variable}")
def insert_named_values(string, values):
    return re.sub(r'{([a-zA-Z0-9_~]+)}', lambda m: swap_named_value(m, values), string)


def swap_named_value(match, values):
    """
    Replace regex matches with variables.
    :param match: regex match group
    :param values: values dictionary
    :return: String to use in place of the variable
    """
    if match.group(1) in values:
        return values.get(match.group(1))
    else:g
        logging.debug("Leaving variable as-is because it has no matching value: %s", match.group(0))
        return match.group(0)


def merge_two_dicts(x, y):
    z = x.copy()  # Start with x's keys and values
    z.update(y)  # Modifies z with y's keys and values & returns None
    return z


def parse_json_file(file_path):
    with open(file_path, 'r') as probe_config_file:
        probe_file_contents = probe_config_file.read()

    return json.loads(probe_file_contents)


# Easy way to recursively iterate over all json files in a directory
# Usage: for parsed_json in all_json_in_dir(path):
def all_json_in_dir(dir_path):
    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(dir_path).glob('**/*.json')
    for path in pathlist:
        parsed = parse_json_file(str(path))
        yield parsed


def load_modules():
    modules = {}

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'module_configs')
    for config in all_json_in_dir(path):
        for key, value in config.items():
            if key in modules:
                # Module of same type was already defined somewhere else
                raise ValueError('Duplicate module')

            modules[key] = value

    return modules


modules = load_modules()


def run_module(module_type, config, bound_values):
    module = modules[module_type]

    populated_config = {k: insert_named_values(v, bound_values) for k, v in config.items()}
    quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}

    populated_command = insert_named_values(module['command'], quoted_config)

    script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = script.communicate()

    output = output.decode('utf-8')
    error = error.decode('utf-8')

    # TODO: handle errors and return values better
    if error != '':
        print(error)
        return False
    else:
        print(output)
        return output


def handle_config(config, default_variables):
    bound_values = default_variables.copy()

    for module in config:
        module_config = merge_two_dicts(default_variables, module['config'])
        if evaluate_condition(module_config, bound_values):
            output = run_module(module['type'], module_config, bound_values)
            if 'name' in module:
                bound_values[module['name']] = output


def evaluate_condition(module_config, bound_values):
    try:
        condition = module_config['condition']
    except KeyError:
        return True

    populated_condition = insert_named_values(condition, bound_values)
    return eval(populated_condition)


def iterate_over_configs(current_commit_dir, previous_commit_dir):
    path = os.path.join(current_commit_dir, 'probe_configs')

    # Default variables that can be accessed in module/monitoring configs
    default_variables = {
        'HEAD': current_commit_dir,
        'HEAD~1': previous_commit_dir
    }

    for config in all_json_in_dir(path):
        handle_config(config, default_variables)


def iterate_over_configs_parallel(current_commit_dir, previous_commit_dir):
    logging.info("Running parallel version of iterate_over_configs")
    path = os.path.join(current_commit_dir, 'probe_configs')

    # Default variables that can be accessed in module/monitoring configs
    # TODO address multiple probes working in same directory at same time?
    default_variables = {
        'HEAD': current_commit_dir,
        'HEAD~1': previous_commit_dir
    }

    with ThreadPoolExecutor() as executor:
        for config in all_json_in_dir(path):
            logging.debug("Submitting a config to the thread pool")
            executor.submit(handle_config, config, default_variables)
        logging.info("All configs submitted to thread pool")

    logging.info("All config threads finished")


if __name__ == "__main__":
    iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))
