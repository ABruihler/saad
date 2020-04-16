import json
import logging
import os
import re
import shlex
import subprocess
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path


# Replace curly-brace surrounded variables with
# the corresponding value in values
# Example: insert_named_valued("Hello {name}", {'name': "'Bob"})
# -> "Hello Bob"
# Variables with no corresponding value are left as is (i.e. "{variable}")
def insert_named_values(string, values):
    return re.sub(r'{([a-zA-Z0-9_~]+)}', lambda m: swap_named_value(m, values), str(string))


def swap_named_value(match, values):
    """
    Replace regex matches with variables.
    :param match: regex match group
    :param values: values dictionary
    :return: String to use in place of the variable
    """
    if match.group(1) in values:
        return values.get(match.group(1))
    else:
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
    pathlist = Path(dir_path).glob("**/*.json")
    for path in pathlist:
        parsed = parse_json_file(str(path))
        yield parsed


class Scope:
    def __init__(self, bindings):
        self.bindings = {}
        self.bind_vars(bindings)

    def bind_vars(self, bindings):
        for binding in bindings.keys():
            self.bindings[binding] = bindings[binding]

    def __str__(self):
        return str(self.bindings)


class Probe:
    def __init__(self, data, scope):
        global running_probes
        self.module = modules[data['type']]
        self.headers = {}
        for key, value in data.items():
            if key == 'config':
                self.inputs = value
            else:
                self.headers[key] = value
        self.scope = scope
        self.status = "Waiting"
        self.pid = None

    def run(self):
        global running_probes

        populated_config = {k: insert_named_values(v, self.scope.bindings) for k, v in self.inputs.items()}
        quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}

        populated_command = insert_named_values(self.module.config['command'], quoted_config)
        populated_command = insert_named_values(populated_command, self.scope.bindings)

        self.script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        self.pid = self.script.pid
        running_probes[self.pid] = self
        timeout = self.inputs.get("timeout", self.module.config.get("timeout", modules.get("defaultTimeout").config))
        assert timeout > 0
        try:
            output, error = self.script.communicate(timeout=timeout)
            self.log()
            # Note: this doesn't seem to really work as intended, because we have shell=True in the Popen() call
            # From what I can tell the terminate()/kill() call is called on the opened shell, not on the started commands
            # TODO figure out a way to handle this properly and terminate the actual commands that run
        except subprocess.TimeoutExpired:
            terminate_t = time.time()
            logging.warning("Script %s timed out after %ds, attempting to terminate", self.module.name, timeout)
            self.script.terminate()
            output, error = self.script.communicate()
            logging.warning("Script %s timed out, finished terminating (took %ds)", self.module.name,
                            time.time() - terminate_t)
            self.log()

        output = output.decode('utf-8')
        error = error.decode('utf-8')

        # TODO: handle errors and return values better
        if error != '':
            print(error)
            return False
        else:
            print(output)
            return output

    def log(self):
        return None

    def kill(self):
        return None

    def evaluate_condition(self):
        try:
            condition = self.inputs['condition']
        except KeyError:
            return True

        populated_condition = insert_named_values(condition, self.scope.bindings)
        return eval(populated_condition)

    def __str__(self):
        return str({'headers': self.headers, 'inputs': self.inputs})


class Module:
    def __init__(self, name, config):
        self.name = name
        self.config = config  # equivalent to modules[name]

    def run_probe(self, probe_inputs, scope):
        p = Probe(probe_inputs, scope)
        return p.run()

    def __str__(self):
        return str(self.config)


def load_modules():
    modules = {}

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "module_configs")
    for config in all_json_in_dir(path):
        for key, value in config.items():
            if key in modules:
                # Module of same type was already defined somewhere else
                raise ValueError("Duplicate module")
            modules[key] = Module(key, value)

    return modules


def iterate_over_configs(current_commit_dir, previous_commit_dir):
    path = os.path.join(current_commit_dir, 'probe_configs')

    # Default variables that can be accessed in module/monitoring configs
    default_variables = {
        "HEAD": current_commit_dir,
        "HEAD~1": previous_commit_dir
    }

    # Loop over all files
    for configs in all_json_in_dir(path):
        scope = Scope(default_variables)
        for probe_config in configs:
            probe = Probe(probe_config, scope)
            if probe.evaluate_condition():
                result = probe.run()
                if 'name' in probe.headers:
                    scope.bind_vars({probe.headers['name']: result})


def iterate_over_configs_parallel(current_commit_dir, previous_commit_dir):
    raise NotImplementedError  # TODO fix after refactor
    logging.info("Running parallel version of iterate_over_configs")
    path = os.path.join(current_commit_dir, "probe_configs")

    # Default variables that can be accessed in module/monitoring configs
    # TODO address multiple probes working in same directory at same time?
    default_variables = {
        "HEAD": current_commit_dir,
        "HEAD~1": previous_commit_dir
    }

    with ThreadPoolExecutor() as executor:
        for config in all_json_in_dir(path):
            logging.debug("Submitting a config to the thread pool")
            executor.submit(handle_config, config, default_variables)
        logging.info("All configs submitted to thread pool")

    logging.info("All config threads finished")


modules = load_modules()
running_probes = {}


if __name__ == "__main__":
    iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))
