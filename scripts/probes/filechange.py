import sys
import json
import filecmp

target=json.loads(sys.argv[1])

if(target):
    #print(target['current'])
    print(not filecmp.cmp(target['current'],target['last']), end="")


