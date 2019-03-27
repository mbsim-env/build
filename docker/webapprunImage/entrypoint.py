#!/usr/bin/python3

import sys
import os
import subprocess
import random
import time
import signal
import urllib.parse
import argparse

argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Run GUI in VNC via websocket.")
argparser.add_argument("--token", type=str, help="URI token")

args=argparser.parse_args()

# parse the token
print("Running webapp with token: "+args.token)
sys.stdout.flush()
cmd=urllib.parse.parse_qs(args.token)

# get prog of file
buildType=cmd.get('buildType', [None])[0]
prog=cmd.get('prog', [None])[0]
file=cmd.get('file', [])

# check arg
if buildType not in ["linux64-dailydebug", "linux64-ci", "linux64-dailyrelease"] or \
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
wm=subprocess.Popen(['/usr/bin/xfwm4'])

# run the main program according to token
absFile=[]
cdir=None
for f in file:
  af='/mbsim-env-'+buildType+'/mbsim/examples/'+f
  if os.path.exists(af):
    absFile.append(af)
    if cdir==None: # use first file as current dir for the started program
      cdir=os.path.dirname(af)
p=subprocess.Popen(['/mbsim-env-'+buildType+'/local/bin/'+prog, '--fullscreen']+absFile, cwd=cdir)

# wait for all child processes
p.wait()
wm.terminate()
xvnc.terminate()
