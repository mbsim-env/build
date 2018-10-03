#!/usr/bin/python

import subprocess
import sys

# use first argument as filter rules
filterStr=sys.argv[1]
with open("/etc/tinyproxy/filter", "w") as f:
  f.write(filterStr)

subprocess.check_call(["/sbin/tinyproxy", "-d"])
