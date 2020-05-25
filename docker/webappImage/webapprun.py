#!/usr/bin/python3

import subprocess
import sys
import ctypes
import signal
import time
import os.path
sys.path.append("/context")
import setup

webapprun=None

def terminate(a, b):
  if webapprun is None:
    return
  webapprun[0].stop()

signal.signal(signal.SIGUSR1, terminate)

libc=ctypes.CDLL("libc.so.6")
PR_SET_PDEATHSIG=1
if libc.prctl(PR_SET_PDEATHSIG, signal.SIGUSR1, 0, 0, 0)!=0:
  raise auth_plugins.AuthenticationError(log_msg="Cannot call prctl.")

# start vnc and other processes in a new container (being reachable as hostname)
networkID=sys.argv[1]
token=sys.argv[2]
hostname=sys.argv[3]

webapprun=setup.run("webapprun", -1, addCommands=["--token", token], networkID=networkID, hostname=hostname, wait=False, printLog=False)
ret=setup.runWait(webapprun, printLog=False)
sys.exit(ret)
