import json
from pathlib import Path
import os

def parseProbeFile(probeFilePath):
    probeConfigFile = open(probeFilePath, 'r')
    probe = probeConfigFile.read()
    probeConfigFile.close()

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

def runProbeScript():
    return False
