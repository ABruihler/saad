import json
import importlib
import subprocess
import shlex

def parseProbeFile(probeFilePath):
    probeConfigFile = open(probeFilePath, 'r')
    probe = probeConfigFile.read()
    probeConfigFile.close()
    return json.loads(probe)

def iterateOverProbes():
    return True

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
