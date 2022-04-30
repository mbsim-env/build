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
import requests
import datetime
import shutil
import fcntl
import concurrent.futures

argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Run GUI in VNC via websocket.")
argparser.add_argument("--token", type=str, help="URI token")

args=argparser.parse_args()

# parse the token
print("Running webapp with token: "+args.token)
sys.stdout.flush()
data=json.loads(args.token)

directory='/home/dockeruser/mbsim/examples/'+data["exampleName"]

class FileLock(object):
  def __init__(self, fileName):
    self.fileName=fileName
  def __enter__(self):
    self.fd=os.open(self.fileName, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
    fcntl.flock(self.fd, fcntl.LOCK_EX)
  def __exit__(self, type, value, traceback):
    fcntl.flock(self.fd, fcntl.LOCK_UN)
    os.close(self.fd)

def subprocessAsDockerUser(subprocessCmd, cmd, **kwargs):
  userEnv=os.environ.copy()
  userEnv["HOME"]="/home/dockeruser"
  return getattr(subprocess, subprocessCmd)(["setpriv", "--reuid=1065", "--regid=1065", "--clear-groups",
    "--inh-caps=-all", "--no-new-privs"]+cmd, env=userEnv, **kwargs)

def startVncAndWM():
  # create XAUTH content
  COOKIE=''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
  subprocessAsDockerUser("check_call", ['/usr/bin/xauth', '-f', '/tmp/mbsimwebapp-xauth', 'add', 'localhost:1', '.', COOKIE])
  
  # start Xvnc in background ...
  xvnc=subprocessAsDockerUser("Popen", ['Xvnc', ':1', '-SecurityTypes', 'None',
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
  wm=subprocessAsDockerUser("Popen", ['/usr/bin/xfwm4', '--compositor=off'])

  # splash screen
  splash=subprocessAsDockerUser("Popen", ["/context/fullscreensplash", str(data["buildRunID"]), data["prog"], data["exampleName"]],
           stdin=subprocess.PIPE, bufsize=-1)
  splash.stdin.write(("Preparing, please wait!!!\n"+\
                      "This may take some time if this is the first time\n"+\
                      "the build NR "+str(data["buildRunID"])+" is used.").encode("utf-8"))
  splash.stdin.close()

  return (xvnc, wm, splash)

def installDistribution():
  with FileLock("/mbsim-env/.distribution.lock"):
    # remove old distributions
    for filename in glob.glob("/mbsim-env/distribution/*/.webappruninfo.json"):
      with open(filename, "r") as f:
        webappruninfo=json.load(f)
      distDate=datetime.datetime.strptime(webappruninfo["buildRunStartTime"], '%Y-%m-%dT%H:%M:%S%z')
      installDate=datetime.datetime.strptime(webappruninfo["installDate"], '%Y-%m-%dT%H:%M:%S%z')
      now=datetime.datetime.now(tz=datetime.timezone.utc)
      if installDate+datetime.timedelta(days=2)<now and distDate+datetime.timedelta(days=6)<now:
        shutil.rmtree(os.path.dirname(filename))
    # check if current distribution exist
    if os.path.isdir("/mbsim-env/distribution/"+data["buildRunID"]):
      return
    # install distribution
    os.makedirs("/mbsim-env/distribution/"+data["buildRunID"], exist_ok=True)
    with open("/mbsim-env/distribution/"+data["buildRunID"]+"/.webappruninfo.json", "w") as f:
      now=datetime.datetime.now(tz=datetime.timezone.utc)
      json.dump({"buildRunStartTime": data["buildRunStartTime"], "installDate": now.strftime('%Y-%m-%dT%H:%M:%S%z')}, f)
    url="https://webserver/builds/run/{ID}/distributionFile/".format(ID=data["buildRunID"])
    # we connect to webserver instead of MBSIMENVSERVERNAME to avoid IPv6 problems.
    # this requires to skip cert verification since the hostname is different.
    r=requests.get(url, stream=True, verify=False)
    with open("/tmp/distributionFile.tar.bz2", 'wb') as f:
      for chunk in r.iter_content(chunk_size=32768): 
        f.write(chunk)
    subprocess.check_call(['tar', "--no-same-owner", "--no-same-permissions", '-xjf', '/tmp/distributionFile.tar.bz2',
                           '-C', "/mbsim-env/distribution/"+data["buildRunID"]])

def checkoutMbsim():
  with FileLock("/mbsim-env/.mbsim.lock"):
    if not os.path.isdir("/mbsim-env/mbsim"):
      subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/mbsim.git"], cwd="/mbsim-env")
    subprocess.check_call(["git", "checkout", "-q", "HEAD~0"], cwd="/mbsim-env/mbsim")
    subprocess.check_call(["git", "fetch", "-q", "--depth", "1", "origin", data["mbsimBranch"]+":"+data["mbsimBranch"]],
                          cwd="/mbsim-env/mbsim")
    os.makedirs("/home/dockeruser/mbsim", exist_ok=True)
    os.chown("/home/dockeruser/mbsim", 1065, 1065)
    gittar=subprocess.Popen(["git", "archive", "--format=tar", data["mbsimBranch"]], stdout=subprocess.PIPE, cwd="/mbsim-env/mbsim")
    subprocessAsDockerUser("check_call", ["tar", "--no-same-owner", "--no-same-permissions", "-x", "-C", "/home/dockeruser/mbsim"],
                                          stdin=gittar.stdout)
    gittar.wait()

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
  startVncAndWMFuture=executor.submit(startVncAndWM)
  installDistributionFuture=executor.submit(installDistribution)
  checkoutMbsimFuture=executor.submit(checkoutMbsim)
  installDistributionFuture.result()
  checkoutMbsimFuture.result()

  # start mbsimxml if needed
  wait=False
  if data["prog"]=="h5plotserie" or data["prog"]=="openmbv":
    for mainFile in ["MBS.mbsx", "MBS.flat.mbsx", "FMI.mbsx", "FMI_cosim.mbsx"]:
      if os.path.isfile(directory+"/"+mainFile):
        subprocessAsDockerUser("Popen", ["/mbsim-env/distribution/"+data["buildRunID"]+"/mbsim-env/bin/mbsimxml", mainFile],
                               cwd=directory)
        wait=True
        break

  def waitForH5Files():
    if not wait:
      return
    for g in ["*.mbsh5", "*.ombvh5"]:
      while len(glob.glob(g))==0:
        time.sleep(0.25)
  
  # run the main program according to token/data
  absFile=[]
  if os.path.exists(directory):
    os.chdir(directory)
    if data["prog"]=="openmbv":
      waitForH5Files()
      absFile.extend(glob.glob("*.ombvx"))
    if data["prog"]=="h5plotserie":
      waitForH5Files()
      absFile.extend(glob.glob("*.mbsh5"))
      absFile.extend(glob.glob("*.ombvh5"))
    if data["prog"]=="mbsimgui":
      absFile.extend(glob.glob("*.mbsx"))

  xvnc, wm, splash=startVncAndWMFuture.result()
  splash.terminate()

  p=subprocessAsDockerUser("Popen", ["/mbsim-env/distribution/"+data["buildRunID"]+"/mbsim-env/bin/"+data["prog"], '--fullscreen']+\
                                    absFile)

# wait for all child processes
p.wait()
wm.terminate()
xvnc.terminate()
