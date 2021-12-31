#!/usr/bin/python3

import sys
import os
import subprocess
import random
import time
import signal
import argparse
import json
import glob

argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Run GUI in VNC via websocket.")
argparser.add_argument("--token", type=str, help="URI token")

args=argparser.parse_args()

# parse the token
print("Running webapp with token: "+args.token)
sys.stdout.flush()
data=json.loads(args.token)

# get prog of file
buildType=data.get('buildType', None)
prog=data.get('prog', None)
exampleName=data.get('exampleName', "")

# check arg
if buildType not in ["linux64-dailydebug", "linux64-ci", "linux64-dailyrelease", "linux64-dailydebug-nonedefbranches", "linux64-dailyrelease-nonedefbranches"] or \
   prog not in ["openmbv", "h5plotserie", "mbsimgui"]:
  raise RuntimeError('Unknown buildType or prog.')

# create XAUTH content
COOKIE=''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
subprocess.check_call(['/usr/bin/xauth', '-f', '/tmp/mbsimwebapp-xauth', 'add', 'localhost:1', '.', COOKIE])

# start Xvnc in background ...
xvnc=subprocess.Popen(['Xvnc', ':1', '-SecurityTypes', 'None',
  '-auth', '/tmp/mbsimwebapp-xauth', "-sigstop", "-NeverShared", "-DisconnectClients"])
# ... and wait for Xvnc to be ready (Xvnc stops itself, using -sigstop option, if ready; than we continoue it)
count=0
while open('/proc/%d/stat'%(xvnc.pid)).readline().split()[2]!='T' and count<1000:
  time.sleep(0.01)
  count=count+1
if open('/proc/%d/stat'%(xvnc.pid)).readline().split()[2]!='T':
  xvnc.terminate()
  raise RuntimeError("Xvnc failed to start.")
xvnc.send_signal(signal.SIGCONT) # continue Xvnc

# run window manager
wm=subprocess.Popen(['/usr/bin/xfwm4', '--compositor=off'])

# run the main program according to token/data
absFile=[]
d='/mbsim-env-'+buildType+'/mbsim/examples/'+exampleName
if os.path.exists(d):
  os.chdir(d)
  if prog=="openmbv":
    absFile.extend(glob.glob("*.ombvx"))
  if prog=="h5plotserie":
    absFile.extend(glob.glob("*.mbsh5"))
    absFile.extend(glob.glob("*.ombvh5"))
  if prog=="mbsimgui":
    absFile.extend(glob.glob("*.mbsx"))
p=subprocess.Popen(['/mbsim-env-'+buildType+'/local/bin/'+prog, '--fullscreen']+absFile)

# wait for all child processes
p.wait()
wm.terminate()
xvnc.terminate()
