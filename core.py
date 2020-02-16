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

def handle_probe_file(file_path, current_commit_dir, previous_commit_dir):
    print('Handling ', file_path)
    parsed = parse_probe_file(file_path)
    for probe in parsed['probes'].keys():
        print("Probing "+probe)
        out=run_probe_script(parsed['probes'][probe]['script'],find_probe_target(parsed),parsed['probes'][probe]['arguments'])
        if(out=="True"):
            print("\tProbe "+probe+" should Fire")
            for actuator in parsed['actuators'].values():
                run_actuator_script(actuator['script'],actuator['arguments'])

def iterate_over_probe_files(current_commit_dir, previous_commit_dir):
    probes_dir = os.path.join(current_commit_dir, 'probes')

    # Search recursively in order to allow user to decide
    # their preferred method of organization
    pathlist = Path(probes_dir).glob('**/*.json')

    for path in pathlist:
        path_str = str(path)
        handle_probe_file(path_str, current_commit_dir, previous_commit_dir)

def run_actuator_script(script, args):
    script=subprocess.Popen(shlex.split(script)+shlex.split(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error=script.communicate()
    error=error.decode("utf-8")
    if(error!=""):
        print(error)
        return False
    else:
        print(output)
    return True

def find_probe_target(config):
    if(config['targetType']=='file'):
        return {'last': config['target'],'current': config['target']}
    #Example: Run AST script
    return True

def run_probe_script(probeFile,target,args):
    script=subprocess.Popen(shlex.split(probeFile)+[json.dumps(target),json.dumps(args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error=script.communicate()
    error=error.decode("utf-8")
    if(error!=""):
        print(error)
        return False
    
    return output.decode("utf-8")
    
iterate_over_probe_files(os.path.dirname(os.path.abspath(__file__)),os.path.dirname(os.path.abspath(__file__)))
