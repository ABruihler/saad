import json
import logging
import os
import re
import shlex
import subprocess
import threading
import time
import psutil
import datetime
import sqlite3
import tempfile
import configparser

from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path


def split_config_list(string):
    return [i.strip() for i in string.split(";")]


# Replace curly-brace surrounded variables with
# the corresponding value in values
# Example: insert_named_valued("Hello {name}", {'name': "'Bob"})
# -> "Hello Bob"
# Variables with no corresponding value are left as is (i.e. "{variable}")
def insert_named_values(string, values):
    """
    Replace curly-brace surrounded variables with
    the corresponding value in values
    :param string: the string to insert into
    :param values: the values to insert
    :return: The input string with all of the values replaced
    Example: insert_named_valued("Hello {name}", {'name': "'Bob"})
    -> "Hello Bob"
    Variables with no corresponding value are left as is (i.e. "{variable}")
    """
    return re.sub(r'{([a-zA-Z0-9_~]+)}', lambda m: swap_named_value(m, values), str(string))


def get_named_values(string):
    output = []
    for match in re.finditer(r'{([a-zA-Z0-9_~]+)}', str(string)):
        output.append(match.group(1))
    return output


def swap_named_value(match, values):
    """
    Replace regex matches with variables.
    :param match: regex match group
    :param values: values dictionary
    :return: String to use in place of the variable
    """
    if match.group(1) in values:
        return str(values.get(match.group(1)))
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
    """
    Easy way to recursively iterate over all json files in a directory
    :param dir_path: the directory to recursively search
    :return: a dictionary of parsed json dictionaries, one per file
    """
    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(dir_path).glob("**/*.json")
    for path in pathlist:
        parsed = parse_json_file(str(path))
        yield parsed

def connect_database(path):
    """
    Connect to the sqlite database at path
    """
    connection = None
    if path is None:
        return None
    try:
        connection = sqlite3.connect(path)
        #print("Connection to SQLite DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection


def init_user_database(db):
    """
    Initialize an sqlite database to keep track of users, if one doesn't exist. Currently unused
    """
    cursor = db.cursor()
    tables_schema['users'] = 'CREATE TABLE users(id INTEGER, hash INTEGER, PRIMARY KEY(id ASC));'
    tables_schema['repos'] = 'CREATE TABLE repos(id INTEGER, name TEXT, url TEXT, PRIMARY KEY(id ASC));'
    tables_schema['users_auth'] = 'CREATE TABLE users_auth(user_id INTEGER, repo_id INTEGER);'
    for table_name in tables_schema.keys():
        print("Checking table " + table_name)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        res = cursor.fetchone()
        if res is None:
            print("Adding table " + table_name)
            cursor.execute(tables_schema[table_name])
            db.commit()
    db.close()


def init_database(db):
    """
    Initialize an sqlite database to keep track of probes that have run, if one doesn't exist
    """
    cursor = db.cursor()
    tables_schema = {}
    tables_schema[
        'probes'] = 'CREATE TABLE probes(id INTEGER, type TEXT, name TEXT, create_time INTEGER, start_time INTEGER, end_time INTEGER, PRIMARY KEY(id ASC));'
    tables_schema['probe_inputs'] = 'CREATE TABLE probe_inputs(probe_id INTEGER, name TEXT, value TEXT);'
    tables_schema['probe_outputs'] = 'CREATE TABLE probe_outputs(probe_id INTEGER, errors TEXT, output TEXT);'
    for table_name in ['probes', 'probe_inputs', 'probe_outputs']:
        print("Checking table " + table_name)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        res = cursor.fetchone()
        if res is None:
            print("Adding table " + table_name)
            cursor.execute(tables_schema[table_name])
            db.commit()
    db.close()


class Scope:
    """
    Manages bindings and ensures that probes run after the probes they depend on
    """
    def __init__(self, bindings):
        """
        Create an instance with the given bindings
        """
        #Lock used due to multithreading
        self.lock = threading.Lock()
        self.lock.acquire()
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
        """
        Make new bindings for the given bindings
        """
        self.lock.acquire()
        for binding in bindings.keys():
            self.bindings[binding] = bindings[binding]
        self.lock.release()

    def add_probe(self, probe, name=None):
        """
        Add a Probe object to the list of probes in this scope
        """
        self.lock.acquire()
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
        """
        Set up variables such that the Probe waits for its dependency to finish
        """
        self.lock.acquire()
        dependency_name = self.probe_names[dependency_name]
        if dependency_name not in self.probes_waiting_on:
            raise ValueError("Probe " + dependency_name + "not found")

        probe_name = self.probes.index(probe)
        self.probes_waiting_on[dependency_name].append(probe_name)
        self.blocking_counts[probe_name] += 1
        self.lock.release()
        #print("Released")

    def update_with_result(self, probe_name, result):
        """
        Update the bindings with the result of a finished probe, and run any newly unblocked probes
        """
        self.lock.acquire()
        self.bindings[probe_name] = result
        name = self.probe_names[probe_name]
        if name in self.probes_waiting_on:
            if len(self.probes_waiting_on[name]) != 0:
                #Reduce the wait counts for any probes that were waiting on me
                for probe in self.probes_waiting_on[name]:
                    self.blocking_counts[probe] -= 1
                    #Start any probes that are now unblocked
                    if self.blocking_counts[probe] == 0:
                        thread = threading.Thread(target=self.probes[probe].run, args=())
                        thread.start()
        self.lock.release()

    def get(self, lookup):
        """
        Getter for bindings
        """
        if lookup in self.bindings:
            return True, self.bindings[lookup]
        if lookup not in self.probe_names:
            return False, None
        return True, None

    def get_dependencies(self, string):
        """
        Get all of the values that still have not been bound
        """
        matches = re.finditer(r'{([a-zA-Z0-9_~]+)}', str(string))
        dependencies = []
        for match in matches:
            bound, result = self.get(match.group(1))
            if bound and result is None:
                dependencies.append(match.group(1))
        return dependencies

    def __str__(self):
        return str(self.bindings)


class Repo:
    """
    Class for managing Repositories and configuration files
    """
    # Checks that a config value won't be overwritten improperly
    def __update_config_vals__(self, vals, append=True, overwrite=False):
        for key in vals:
            # If my parent hasn't set a value or isn't false, update
            if (key not in self.inherited_config) or (self.inherited_config[key] != 'False') or overwrite:
                # But check that my value isn't false first

                if (key in self.config) and self.config[key] != 'False':
                    if vals[key] == 'False':
                        continue
                    if append:
                        if self.config[key][-1] != ";" and vals[key][0] != ";":
                            self.config[key] += ";"
                        self.config[key] += vals[key]
                        continue
                    self.config[key] = vals[key]
                    continue

                self.config[key] = vals[key]

    def __init__(self, repo_path, repo_name, root_dir, parent_repo=None):
        """
        Initialize the repository and load the starting config files in.
        """
        self.repo = repo_path
        self.name = repo_name
        self.commits = {}
        self.modules = {}
        self.running_probes = []
        self.probe_lock = threading.Lock()
        self.config = {}
        self.inherited_config = {}
        self.child_repos = {}
        self.parent = parent_repo
        self.config['root_path'] = root_dir
        if self.parent:
            self.parent.child_repos[self.name] = self

            if 'Repo' in self.parent.config:
                self.__update_config_vals__(self.parent.config['Repo'], True, True)
                self.inherited_config['Repo'] = {}
                for key in self.parent.config['Repo']:
                    # Copy inherited default settings over
                    self.inherited_config[key] = self.parent.config['Repo'][key]
                    self.inherited_config['Repo'][key] = self.parent.config['Repo'][key]
            if self.name in self.parent.config:
                # Load specific config values from parent
                self.__update_config_vals__(self.parent.config[self.name], True, True)
                for key in self.parent.config[self.name]:
                    if key not in self.inherited_config:
                        self.inherited_config[key] = self.parent.config[self.name][key]
                    if self.inherited_config[key] != 'False' and self.parent.config[self.name][key] == 'False':
                        self.inherited_config[key] = 'False'
                    elif self.parent.config[self.name][key] != 'False':
                        self.inherited_config[key] = self.parent.config[self.name][key]

    def load_config_recursive(self, path, commit=None, start=False):
        """
        Loads all configs, even those defined in another config.
        """
        print("Loading config " + path)
        if not start:
            self.load_config(path, commit)
            if 'configfiles' in self.config:
                if self.config['configfiles']:
                    undone_configs = split_config_list(self.config['configfiles'])
                    i = 1
                    while i < len(undone_configs) and undone_configs[i] != path:
                        i += 1
                    if i < len(undone_configs):
                        self.load_config(undone_configs[i], commit)
        elif 'configfiles' in self.config and self.config['configfiles']:
            if len(split_config_list(self.config['configfiles'])) > 0:
                self.load_config_recursive(split_config_list(self.config['configfiles'])[0], commit, False)

    def load_config(self, path, commit=None):
        """
        Load a single config, ensuring that parent values override properly
        """
        saad_config = {}
        config_parser = configparser.ConfigParser()
        if commit is not None:
            code_dir = self.get_commit(commit)
            if os.path.isdir(code_dir):
                os.chdir(code_dir)
        if os.path.isfile(path):
            config_parser.read(path)
        else:
            print("No config for repo " + self.name + " found at " + path)
            return
        for section in config_parser:

            if section == 'Local':
                self.__update_config_vals__(config_parser['Local'], True, False)
            elif self.parent is not None:
                continue
            elif section == 'Server':
                for key in config_parser[section]:
                    self.config[key] = config_parser[section].get(key, None)
            elif section == 'Allowed Repos':
                self.config['ALLOWED_REPO_URLS'] = {name: config_parser['Allowed Repos'].get(name, name) for name in
                                                    config_parser['Allowed Repos']}
            else:
                for key in config_parser[section]:
                    if section not in self.config:
                        self.config[section] = {}
                    self.config[section][key] = config_parser[section].get(key, key)

        os.chdir(self.config['root_path'])

    def reload_all_modules(self, commit=None):
        """
        Get all of the modules for this repo at a given commit
        """
        self.modules = {}
        if self.parent:
            for module in self.parent.modules:
                self.modules[module] = self.parent.modules[module]
        if 'modulefolders' in self.config:
            for path in self.config['modulefolders'].split(";"):
                self.load_modules(path.strip(), commit)

    def load_modules(self, path, commit=None):
        """
        Load all of the modules at a given file path.
        """
        if commit is not None:
            path = os.path.join(os.path.dirname(os.path.abspath(self.commits[commit].name)), path)
        else:
            path = os.path.join(self.config['root_path'], path)
        for config in all_json_in_dir(path):
            for key, value in config.items():
                if key in self.modules:
                    # Module of same type was already defined somewhere else
                    raise ValueError("Duplicate module")
                self.modules[key] = Module(key, value)

    def get_all_probes(self):
        """
        Get all of the running probes for this repo
        """
        self.probe_lock.acquire()
        out = self.running_probes.copy()
        self.probe_lock.release()
        return out

    def load_probe_json(self):
        """
        Get all of the defined probes for this repo
        """
        if 'probefolders' not in self.config:
            print("No probes specified to run")
            return []
        output = []
        for filepath in split_config_list(self.config['probefolders']):
            path = os.path.join(self.get_commit('current'), filepath)
            if not os.path.isdir(path):
                print("No probes found at " + path)
                continue
            output.extend(list(all_json_in_dir(path)))
        return output

    def get_modules(self):
        return self.modules

    def get_current(self):
        """
        Load the most recent commit
        """
        self.commits['current'] = tempfile.TemporaryDirectory()
        print(self.commits['current'].name)
        print("################")
        print("Cloning commit current...\n")
        os.chdir(self.commits['current'].name)
        os.system("git clone " + self.repo + " .")
        os.system("git config --local advice.detachedHead false")
        os.chdir(self.config['root_path'])

    def get_commit(self, commit_name):
        """
        Load the specified commit into a temp directory
        """
        #First load the current commit, so we can use it to parse git commit name shorthand
        if 'current' not in self.commits:
            self.get_current()
        else:
            if not os.path.isdir(self.commits['current'].name):
                self.get_current()
        os.chdir(self.commits['current'].name)
        if commit_name == 'current':
            return self.commits['current'].name
        commit_name = subprocess.check_output(['git', 'rev-parse', commit_name]).decode("utf-8")
        
        #Then check if the commit specified is already loaded
        if commit_name in self.commits:
            if os.path.isdir(self.commits[commit_name].name):
                return self.commits[commit_name].name
        #Load it if it isn't.
        self.commits[commit_name] = tempfile.TemporaryDirectory()
        print("################")
        print("Cloning commit " + commit_name + "...\n")
        os.chdir(self.commits[commit_name].name)
        os.system("git clone " + self.repo + " .")
        os.system("git config --local advice.detachedHead false")
        os.system("git checkout " + commit_name)
        os.chdir(self.config['root_path'])
        return self.commits[commit_name].name

    def run_all_probes(self, new_commit, old_commit):
        """
        Run all of the probe files for this repository
        """
        if 'probefolders' not in self.config:
            print("No probes specified to run")
            return

        logging.debug('New commit: {}'.format(new_commit))
        logging.debug('Old commit: {}'.format(old_commit))
        logging.debug('self.commits: {}'.format(self.commits))

        for filepath in split_config_list(self.config['probefolders']):
            path = os.path.join(self.get_commit(new_commit), filepath)
            if not os.path.isdir(path):
                print("No probes found at " + path)
                continue

            # Default variables that can be accessed in module/monitoring configs
            default_variables = {
                "HEAD": self.get_commit(new_commit),
                "HEAD~1": self.get_commit(old_commit)
            }
            # Loop over all files
            for configs in all_json_in_dir(path):
                scope = Scope(default_variables)
                # Initialize Probes
                probes = []
                for probe_config in configs:
                    probe = Probe(probe_config, scope, self)
                    probes.append(probe)
                # Get the dependencies set
                for probe in probes:
                    probe.prep_input_dependencies()
                # Start all unblocked probes
                scope.lock.acquire()
                data = scope.blocking_counts
                for probe_name in data.keys():
                    if data[probe_name] == 0:
                        thread = threading.Thread(target=scope.probes[probe_name].run, args=())
                        thread.start()
                        #scope.probes[probe_name].run()
                scope.lock.release()


class Probe:
    def __init__(self, data, scope, repo):
        """
        Initialize a probe from the JSON
        """
        #Lock to enforce mutual exclusion
        self.lock = threading.Lock()
        self.lock.acquire()
        self.module = modules[data['type']]
        self.headers = {}
        self.headers['type'] = data['type']
        self.headers['status'] = "Preparing"
        self.headers['created'] = datetime.datetime.now()
        self.headers['started'] = None
        self.headers['finished'] = None
        self.repo = repo
        for key, value in data.items():
            if key == 'config':
                self.inputs = value
            else:
                self.headers[key] = value
        self.scope = scope
        self.pids = []
        self.name = False
        if 'name' in self.headers:
            self.name = self.headers['name']
            self.scope.add_probe(self, self.name)
        else:
            self.scope.add_probe(self)
        self.repo.probe_lock.acquire()
        self.repo.running_probes.append(self)
        self.repo.probe_lock.release()
        self.headers['status'] = "Waiting"
        self.output = None
        self.error = None
        self.lock.release()

    def prep_input_dependencies(self):
        """
        Find all of the dependencies of the probe, and register them with the scope
        """
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
        """
        Run the probe
        """
        if not self.evaluate_condition():
            return
        self.lock.acquire()
        self.headers['status'] = "Running"
        self.headers['started'] = datetime.datetime.now()
        self.scope.lock.acquire()
        populated_config = {k: insert_named_values(v, self.scope.bindings) for k, v in self.inputs.items()}
        quoted_config = {k: shlex.quote(v) for k, v in populated_config.items()}
        populated_command = insert_named_values(self.module.config['command'], quoted_config)
        populated_command = insert_named_values(populated_command, self.scope.bindings)
        self.scope.lock.release()

        # Make sure we're executing in the saad/ directory
        os.chdir(self.repo.config['root_path'])
        logging.debug('Current working directory: {}'.format(os.getcwd()))
        logging.debug('Executing command: {}'.format(populated_command))

        self.script = subprocess.Popen(populated_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        #Record all of the pids the probe creates, so that it can be cleaned up later.
        self.pids = [self.script.pid]
        if psutil.pid_exists(self.script.pid):
            for child in psutil.Process(self.script.pid).children(recursive=True):
                self.pids.append(child.pid)

        timeout = self.inputs.get("timeout", self.module.config.get("timeout", modules.get("defaultTimeout").config))
        
        #Actually run the probe in the command line
        try:
            if timeout > 0:
                self.output, self.error = self.script.communicate(timeout=timeout)
            else:
                self.output, self.error = self.script.communicate()
            self.log()
        #Timeout handler
        except subprocess.TimeoutExpired:
            self.kill()
            self.headers['status'] = "Timed Out"
            terminate_t = time.time()
            logging.warning("Script %s timed out after %ds, attempting to terminate", self.module.name, timeout)
            self.output, self.error = self.script.communicate()

            logging.warning("Script %s timed out, finished terminating (took %ds)", self.module.name,
                            time.time() - terminate_t)

        # Make sure we're back in the saad/ directory
        logging.debug('Working directory after command executed: {}'.format(os.getcwd()))
        os.chdir(self.repo.config['root_path'])
        logging.debug('Current working directory: {}'.format(os.getcwd()))

        self.output = self.output.decode('utf-8')
        self.error = self.error.decode('utf-8')
        # TODO: handle errors and return values better
        if self.error != '' and self.error is not None:
            self.headers['status'] = "Error"
            print(self.error)
            if self.name:
                self.scope.update_with_result(self.name, False)
        else:
            self.headers['status'] = "Finished"
            print(self.output)
            if self.name:
                self.scope.update_with_result(self.name, self.output)
        self.headers['finished'] = datetime.datetime.now()
        self.repo.probe_lock.acquire()
        self.repo.running_probes.remove(self)
        self.repo.probe_lock.release()
        self.lock.release()

    def log(self):
        """
        Record the probe in the database
        """
        global probes_db_path
        probes_db = connect_database(probe_db_path)
        if probes_db is None:
            return
        cursor = probes_db.cursor()
        tempname = ''
        if self.name:
            tempname = self.name
        times = [None, None, None]
        if self.headers['created'] is not None:
            times[0] = int(self.headers['created'].strftime("%s"))
        if self.headers['started'] is not None:
            times[1] = int(self.headers['started'].strftime("%s"))
        if self.headers['finished'] is not None:
            times[2] = int(self.headers['finished'].strftime("%s"))
        cursor.execute('INSERT INTO probes (type, name, create_time, start_time, end_time) VALUES (?, ?, ?, ?, ?);',
                       (self.headers['type'], tempname, times[0], times[1], times[2],))

        probe_id = cursor.lastrowid
        for probe_input, input_val in self.inputs.items():
            cursor.execute('INSERT INTO probe_inputs VALUES (?, ?, ?);', (probe_id, probe_input, input_val,))

        cursor.execute('INSERT INTO probe_outputs VALUES (?, ?, ?);', (probe_id, self.error, self.output,))
        probes_db.commit()
        probes_db.close()

    def kill(self):
        """
        Stop the probe and all processes it created
        """
        for pid in self.pids:
            if psutil.pid_exists(pid):
                psutil.Process(pid).kill()
        self.headers['status'] = "Terminated"
        self.headers['finished'] = datetime.datetime.now()
        self.log()
        return

    def evaluate_condition(self):
        """
        Check that the condition for running the probe is met
        """
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
    """
    Module class. Stores data about a module
    """
    def __init__(self, name, config):
        self.name = name
        self.config = config  # equivalent to modules[name]

    def run_probe(self, probe_inputs, scope, repo):
        """
        Start a probe with the given inputs.
        """
        p = Probe({"type": self.name, "config": probe_inputs}, scope, repo)
        thread = threading.Thread(target=p.run, args=())
        thread.start()

    def get_inputs(self):
        return get_named_values(self.config)

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
            probe = Probe(probe_config, scope, Repo("", "", os.path.dirname(os.path.abspath(__file__))))
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


probe_db_path = os.path.dirname(os.path.abspath(__file__)) + "/probeDatabase.sql"
probes_db = connect_database(probe_db_path)
init_database(probes_db)
modules = load_modules()

if __name__ == "__main__":
    iterate_over_configs(os.path.dirname(os.path.abspath(__file__)), os.path.dirname(os.path.abspath(__file__)))
