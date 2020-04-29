import json
import logging
import os
import re
import shlex
import subprocess
import threading
import time
import psutil

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
        self.lock = threading.Lock()
        self.lock.acquire()
        #print("Init grabbed scope lock")
        self.bindings = {}
        for binding in bindings.keys():
            self.bindings[binding] = bindings[binding]

        # List of probes in scope. Internal names are indices in this
        self.probes = []
        # Mapping from probe names to internal names
        self.probe_names = {}
        # How many probes are blocking each of those
        self.blocking_counts = {}
        # Which probes are blocked by a given probe
        self.probes_waiting_on = {}
        self.lock.release()

    def bind_vars(self, bindings):
        self.lock.acquire()
        #print("Binding grabbed scope lock")
        for binding in bindings.keys():
            self.bindings[binding] = bindings[binding]
        self.lock.release()

    def add_probe(self, probe, name=None):
        self.lock.acquire()
        #print("Adding grabbed scope lock")
        internal_name = len(self.probes)
        self.probes.append(probe)
        if name is not None:
            if name in self.probe_names:
                raise ValueError("Duplicate Probe Name")
            self.probe_names[name] = internal_name
        self.blocking_counts[internal_name] = 0
        self.probes_waiting_on[internal_name] = []
        self.lock.release()

    def register_probe_dependency(self, probe, dependency_name):

        self.lock.acquire()
        #print("Dependency grabbed scope lock")
        dependency_name = self.probe_names[dependency_name]
        if dependency_name not in self.probes_waiting_on:
            raise ValueError("Probe " + dependency_name + "not found")

        probe_name = self.probes.index(probe)
        self.probes_waiting_on[dependency_name].append(probe_name)
        self.blocking_counts[probe_name] += 1
        self.lock.release()
        #print("Released")

    def update_with_result(self, probe_name, result):
        self.lock.acquire()
        #print("Updating grabbed scope lock")
        self.bindings[probe_name] = result
        name = self.probe_names[probe_name]
        if name in self.probes_waiting_on:
            if len(self.probes_waiting_on[name]) != 0:
                for probe in self.probes_waiting_on[name]:
                    self.blocking_counts[probe] -= 1
                    if self.blocking_counts[probe] == 0:
                        thread = threading.Thread(target=self.probes[probe].run, args=())
                        thread.start()
        self.lock.release()

    def get(self, lookup):
        if lookup in self.bindings:
            return True, self.bindings[lookup]
        if lookup not in self.probe_names:
            return False, None
        return True, None

    def get_dependencies(self, string):
        matches = re.finditer(r'{([a-zA-Z0-9_~]+)}', str(string))
        dependencies = []
        for match in matches:
            bound, result = self.get(match.group(1))
            if bound and result is None:
                dependencies.append(match.group(1))
        return dependencies

    def __str__(self):
        return str(self.bindings)


class Probe:
    def __init__(self, data, scope):
        self.lock = threading.Lock()
        self.lock.acquire()
        #print("init grabbed_probe_lock")
        self.module = modules[data['type']]
        self.headers = {}
        for key, value in data.items():
            if key == 'config':
                self.inputs = value
            else:
                self.headers[key] = value
        self.scope = scope

        self.status = "Waiting"
        self.process = None
        self.name = False
        if 'name' in self.headers:
            self.name = self.headers['name']
            self.scope.add_probe(self, self.name)
        else:
            self.scope.add_probe(self)
        self.lock.release()

    def prep_input_dependencies(self):

        self.lock.acquire()
        #print("Prep grabbed probe lock")
        for item in self.inputs.values():
            dependencies = self.scope.get_dependencies(item)
            for dependency in dependencies:
                self.scope.register_probe_dependency(self, dependency)

        dependencies = self.scope.get_dependencies(self.module.config['command'])
        for dependency in dependencies:
            self.scope.register_probe_dependency(self, dependency)
        self.lock.release()

    def run(self):
        if not self.evaluate_condition():
            return
        self.lock.acquire()
        self.status = "Preparing"
        self.scope.lock.acquire()
        populated_config = {k: insert_named_values(v, self.scope.bindings) for k, v in self.inputs.items()}
        quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}
        populated_command = insert_named_values(self.module.config['command'], quoted_config)
        populated_command = insert_named_values(populated_command, self.scope.bindings)
        self.scope.lock.release()
        self.status = "Running"
        self.script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        self.pid = self.script.pid
        self.process = psutil.Process(self.pid)

        timeout = self.inputs.get("timeout", self.module.config.get("timeout", modules.get("defaultTimeout").config))

        assert timeout > 0
        try:
            output, error = self.script.communicate(timeout=timeout)
            self.log()
            # Note: this doesn't seem to really work as intended, because we have shell=True in the Popen() call
            # From what I can tell the terminate()/kill() call is called on the opened shell, not on the started commands
            # TODO figure out a way to handle this properly and terminate the actual commands that run
        except subprocess.TimeoutExpired:
            self.status = "Timed Out"
            terminate_t = time.time()
            logging.warning("Script %s timed out after %ds, attempting to terminate", self.module.name, timeout)
            output, error = self.script.communicate()
            self.kill()
            logging.warning("Script %s timed out, finished terminating (took %ds)", self.module.name,
                            time.time() - terminate_t)

        output = output.decode('utf-8')
        error = error.decode('utf-8')
        # TODO: handle errors and return values better
        if error != '':
            print(error)
            if self.name:
                self.scope.update_with_result(self.name, False)
        else:
            print(output)
            if self.name:
                self.scope.update_with_result(self.name, output)
        self.lock.release()

    def log(self):
        return None

    def kill(self):
        if self.process is not None:
            for proc in self.process.children(recursive=True):
                proc.kill()
        self.process.kill()
        self.status = "Terminated"
        self.log()
        return

    def evaluate_condition(self):
        self.lock.acquire()
        if 'condition' not in self.inputs:
            self.lock.release()
            return True
        condition = self.inputs['condition']
        self.lock.release()
        self.scope.lock.acquire()
        populated_condition = insert_named_values(condition, self.scope.bindings)
        self.scope.lock.release()

        return eval(populated_condition)

    def __str__(self):
        return str({'headers': self.headers, 'inputs': self.inputs})


class Module:
    def __init__(self, name, config):
        self.name = name
        self.config = config  # equivalent to modules[name]

    def run_probe(self, probe_inputs, scope):
        p = Probe(probe_inputs, scope)
        p.run()

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
        # Initialize Probes
        probes = []
        for probe_config in configs:
            probe = Probe(probe_config, scope)
            probes.append(probe)
        # Get the dependencies set
        for probe in probes:
            probe.prep_input_dependencies()
        # Run probes
        scope.lock.acquire()
        data = scope.blocking_counts
        for probe_name in data.keys():
            if data[probe_name] == 0:
                thread = threading.Thread(target=scope.probes[probe_name].run, args=())
                thread.start()
                #scope.probes[probe_name].run()
        scope.lock.release()


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

if __name__ == "__main__":
    iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))
