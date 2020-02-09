import json
from pathlib import Path
import os
import importlib
import subprocess
import shlex

def parseProbeFile(probe_file_path):
    with open(probe_file_path, 'r') as probe_config_file:
        probe = probe_config_file.read()

    return json.loads(probe)

def iterate_over_probes(current_commit_dir):
	probes_dir = os.path.join(current_commit_dir, 'probes')

	# Search recursively in order to allow user to decide
	# their preferred method of organization
	pathlist = Path(probes_dir).glob('**/*.json')

	for path in pathlist:
		path_str = str(path)
		print(path_str)

def runActuatorScript():
    return True

def findProbeTarget():
    #Example: Run AST script
    return True

def runProbeScript(probeFile,target,args):
    script=subprocess.Popen(shlex.split(probeFile)+[json.dumps(target),json.dumps(args)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output,error=script.communicate()
    return output
    
iterateOverProbes()
