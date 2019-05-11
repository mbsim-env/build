#!/usr/bin/python3

import fcntl
import json
import sys
import time
import os
import socket
import argparse
sys.path.append("/context")
import setup

# run only one instance of this program at the same time
processLock=socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
try:
  processLock.bind('\0'+os.path.basename(__file__))
except socket.error:
  sys.exit(0)

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="CI cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

# config files
configFilename="/mbsim-config/mbsimBuildService.conf"

def checkToBuild(tobuild):
  if not os.path.exists(configFilename):
    return None, ""
  # read file config file
  fd=open(configFilename, 'r+')
  fcntl.lockf(fd, fcntl.LOCK_EX)
  config=json.load(fd)
  
  # get branch to build
  if tobuild==None and len(config['tobuild'])>0:
    tobuild=config['tobuild'][0]
  newTobuild=[]
  for b in config['tobuild']:
    if tobuild['fmatvec']==b['fmatvec'] and \
       tobuild['hdf5serie']==b['hdf5serie'] and \
       tobuild['openmbv']==b['openmbv'] and \
       tobuild['mbsim']==b['mbsim']:
      tobuild=b
    else:
      newTobuild.append(b)
  config['tobuild']=newTobuild

  # if no build is waiting check for docker builds
  bd=None
  if "buildDocker" in config:
    buildDocker=config["buildDocker"]
  else:
    buildDocker=[]
  if tobuild==None and len(buildDocker)>0:
    bd=buildDocker.pop(0)
  
  # write file config file
  fd.seek(0);
  json.dump(config, fd, indent=2)
  fd.truncate();
  fcntl.lockf(fd, fcntl.LOCK_UN)
  fd.close()

  return tobuild, bd, config["status_access_token"]

tobuild, bd, statusAccessToken=checkToBuild(None)

if tobuild==None and bd==None:
  # nothing to do, return with code 0
  sys.exit(0)

if bd!=None and os.environ["MBSIMENVTAGNAME"]=="staging":
  # mfmf more this to a docker container?!
  import subprocess
  print("Found new docker service to build: "+str(bd))
  sys.stdout.flush()
  with open("/var/www/html/mbsim/docker/buildDocker.txt", "w") as f:
    if not os.path.isdir("/mbsim-docker/build"):
      subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/build.git"], cwd="/mbsim-docker", stdout=f, stderr=f)
    subprocess.check_call(["git", "fetch"], cwd="/mbsim-docker/build", stdout=f, stderr=f)
    subprocess.check_call(["git", "checkout", bd], cwd="/mbsim-docker/build", stdout=f, stderr=f)
    for s in setup.allServices:
      ret=setup.build(s, args.jobs, fd=f, baseDir="/mbsim-docker/build/docker")
      if ret!=0:
        sys.exit(ret)
  print("Sucessfully build docker service. Restarting service now.")
  #mfmf subprocess.check_call(["systemctl", "status", "mbsimenvstaging"])
  print("Service restarted.")
  sys.exit(0)

if os.environ["MBSIMENVTAGNAME"]=="staging":
  # the staging service delays the CI script by 30min to avoid load conflicts with the production service (on the same machine)
  print("Found something to build, but wait 30min since this is the staging service: "+str(tobuild))
  sys.stdout.flush()
  time.sleep(30*60)

print("Found something to build: "+str(tobuild))
sys.stdout.flush()

# wait at least 2 minutes after the timestamp to give the user the chance to update also other repos
while True:
  delta=tobuild['timestamp']+1*60 - time.time()
  if delta>0:
    time.sleep(delta)
    tobuild, bd, _=checkToBuild(tobuild)
  else:
    break

print("Starting build: "+str(tobuild))
sys.stdout.flush()

# set branches
fmatvecBranch=tobuild['fmatvec']
hdf5serieBranch=tobuild['hdf5serie']
openmbvBranch=tobuild['openmbv']
mbsimBranch=tobuild['mbsim']

# run linux64-ci
ret=setup.run("build-linux64-ci", args.jobs, printLog=False,
              fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch,
              openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
              statusAccessToken=statusAccessToken)
sys.exit(ret)
