import json
from pathlib import Path
import os
import importlib
import subprocess
import shlex

def parse_probe_file(probe_file_path):
    with open(probe_file_path, 'r') as probe_config_file:
        probe_file_contents = probe_config_file.read()

    return json.loads(probe_file_contents)

def handle_probe_file(file_path):
    print('Handling ', file_path)
    parsed = parse_probe_file(file_path)
    print(parsed)

def iterate_over_probe_files(current_commit_dir):
    probes_dir = os.path.join(current_commit_dir, 'probes')

    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(probes_dir).glob('**/*.json')

    for path in pathlist:
        path_str = str(path) # According to stack overflow, path isn't a string
        handle_probe_file(path_str)

def runActuatorScript():
    return True

def findProbeTarget():
    #Example: Run AST script
    return True

def runProbeScript(probeFile,target,args):
    script=subprocess.Popen(shlex.split(probeFile)+[json.dumps(target),json.dumps(args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error=script.communicate()
    return output
    
iterate_over_probe_files(os.path.dirname(os.path.abspath(__file__)))
