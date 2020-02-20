import json
import sys
import subprocess

target_file = sys.argv[1]
target = sys.argv[2]
threshold = float(sys.argv[3])

output = json.loads(subprocess.check_output(['radon', 'cc', '-a', '-s', '-j', target_file]))[target_file]

for field in output:
    if field['name'] == target:
        print(int(field['complexity']) > threshold)
        quit()
