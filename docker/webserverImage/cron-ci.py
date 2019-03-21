#!/usr/bin/python

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

if os.environ["MBSIMENVTAGNAME"]=="staging":
  # the staging service delays the CI script by 30min to avoid load conflicts with the production service (on the same machine)
  time.sleep(30*60)

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
  
  # write file config file
  fd.seek(0);
  json.dump(config, fd, indent=2)
  fd.truncate();
  fcntl.lockf(fd, fcntl.LOCK_UN)
  fd.close()

  return tobuild, config["status_access_token"]

tobuild, statusAccessToken=checkToBuild(None)

if tobuild==None:
  # nothing to do, return with code 0
  sys.exit(0)

print("Found something to build: "+str(tobuild))
sys.stdout.flush()

# wait at least 2 minutes after the timestamp to give the user the chance to update also other repos
while True:
  delta=tobuild['timestamp']+1*60 - time.time()
  if delta>0:
    time.sleep(delta)
    tobuild, _=checkToBuild(tobuild)
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
