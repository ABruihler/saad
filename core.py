import json

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

def runProbeScript():
    return False
