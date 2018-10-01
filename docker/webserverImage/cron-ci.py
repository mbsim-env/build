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
  sys.exit()

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="CI cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument("--servername", type=str, help="Servername")

args=argparser.parse_args()

# config files
configFilename="/mbsim-config/mbsimBuildService.conf"

def checkToBuild(tobuild):
  if not os.path.exists(configFilename):
    return None
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

  return tobuild

tobuild=checkToBuild(None)

if tobuild==None:
  # nothing to do, return with code 0
  sys.exit(0)

# wait at least 2 minutes after the timestamp to give the user the chance to update also other repos
while True:
  delta=tobuild['timestamp']+1*60 - time.time()
  if delta>0:
    time.sleep(delta)
    tobuild=checkToBuild(tobuild)
  else:
    break

# set branches
fmatvecBranch=tobuild['fmatvec'].encode('utf-8')
hdf5serieBranch=tobuild['hdf5serie'].encode('utf-8')
openmbvBranch=tobuild['openmbv'].encode('utf-8')
mbsimBranch=tobuild['mbsim'].encode('utf-8')

# run linux64-ci
setup.run("autobuild-linux64-ci", args.servername, args.jobs, printLog=False,
          fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch,
          openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
