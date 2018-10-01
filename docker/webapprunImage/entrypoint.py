#!/usr/bin/python

import sys
import os
import subprocess
import random
import time
import signal
import urlparse

token=sys.argv[1]

XAUTHTMPL='/tmp/mbsimwebapp-xauth'

# parse the token
print("Running webapp with token: "+token)
sys.stdout.flush()
cmd=urlparse.parse_qs(token)

# get prog of file
buildType=cmd.get('buildType', [None])[0]
prog=cmd.get('prog', [None])[0]
file=cmd.get('file', [])

# check arg
if buildType not in ["linux64-dailydebug", "linux64-ci", "linux64-dailyrelease"] or \
   prog not in ["openmbv", "h5plotserie", "mbsimgui"]:
  raise RuntimeError('Unknown buildType or prog.')

# create XAUTH file
os.open(XAUTHTMPL, os.O_CREAT, 0o600)

# create XAUTH content
COOKIE=''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
subprocess.check_call(['/usr/bin/xauth', '-f', XAUTHTMPL, 'add', 'localhost:1', '.', COOKIE])

# start Xvnc in background ...
xvnc=subprocess.Popen(['Xvnc', ':1', '-SecurityTypes', 'None',
  '-auth', XAUTHTMPL, "-sigstop", "-NeverShared", "-DisconnectClients"])
# ... and wait for Xvnc to be ready (Xvnc stops itself, using -sigstop option, if ready; than we continoue it)
count=0
while open('/proc/%d/stat'%(xvnc.pid)).readline().split()[2]!='T' and count<1000:
  time.sleep(0.01)
  count=count+1
if open('/proc/%d/stat'%(xvnc.pid)).readline().split()[2]!='T':
  xvnc.terminate()
  raise RuntimeError("Xvnc failed to start.")
xvnc.send_signal(signal.SIGCONT) # continue Xvnc

# prepare env for starting programs in the vnc server
xenv=os.environ.copy()
xenv['XAUTHORITY']=XAUTHTMPL
xenv['DISPLAY']=':1'
xenv['QT_X11_NO_MITSHM']='1' # required for Qt!??

# run window manager
wm=subprocess.Popen(['/usr/bin/xfwm4'], env=xenv)

# run the main program according to token
absFile=[]
cdir=None
for f in file:
  af='/mbsim-env-'+buildType+'/mbsim/examples/'+f
  if os.path.exists(af):
    absFile.append(af)
    if cdir==None: # use first file as current dir for the started program
      cdir=os.path.dirname(af)
p=subprocess.Popen(['/mbsim-env-'+buildType+'/local/bin/'+prog, '--fullscreen']+absFile, cwd=cdir, env=xenv)

# wait for all child processes
p.wait()
wm.terminate()
xvnc.terminate()
