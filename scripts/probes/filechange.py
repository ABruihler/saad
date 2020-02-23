import filecmp
import sys

if len(sys.argv) > 2:
    old = sys.argv[1]
    cur = sys.argv[2]
    print(not filecmp.cmp(old, cur), end="")
