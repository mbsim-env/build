#!/usr/bin/env python3

import sys
import os
import socket
import argparse
import django
import datetime
import psutil
import json
sys.path.append("/context")
import setup
sys.path.append("/context/mbsimenv")
import service

# run only one instance of this program at the same time
processLock=socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
try:
  processLock.bind('\0'+os.path.basename(__file__))
except socket.error:
  print("Another cront-ci instance is still running. exiting.")
  sys.stdout.flush()
  sys.exit(0)

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="CI cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=max(1,min(round(psutil.virtual_memory().total/pow(1024,3)/2),psutil.cpu_count(False))), help="Number of jobs to run in parallel")

args=argparser.parse_args()

if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

# (the staging service delays the CI script by 20min to avoid load conflicts with the production service (on the same machine))
# a CI build is delayed by 1min to give the user the change to push something else to another branch
waitTime=datetime.timedelta(minutes=1) if os.environ["MBSIMENVTAGNAME"]!="staging" else datetime.timedelta(minutes=20)

ciq=service.models.CIQueue.objects.all().order_by("recTime").first()
if ciq is not None:
  if ciq.fmatvecBranch is not None   and ciq.fmatvecBranch!="" and \
     ciq.hdf5serieBranch is not None and ciq.hdf5serieBranch!="" and \
     ciq.openmbvBranch is not None   and ciq.openmbvBranch!="" and \
     ciq.mbsimBranch is not None     and ciq.mbsimBranch!="":
    print("Found something to build: "+ciq.fmatvecBranch+", "+ciq.hdf5serieBranch+", "+\
          ciq.openmbvBranch+", "+ciq.mbsimBranch+" starting in, at most, "+str(waitTime))
    sys.stdout.flush()
    if django.utils.timezone.now()-ciq.recTime>waitTime:
      print("Start build: "+ciq.fmatvecBranch+", "+ciq.hdf5serieBranch+", "+\
            ciq.openmbvBranch+", "+ciq.mbsimBranch)
      sys.stdout.flush()
      # run linux64-ci (win64-ci is not run by crone for now!!!)
      ciq.delete()
      enforceConfigure=False # if this is set to True the CI build enforces a configure run which is sometime required.
      with open("/context/buildConfig.json", "rt") as f:
        buildConfig=json.load(f)
      ret=setup.run("build-linux64-ci", args.jobs, printLog=False, enforceConfigure=enforceConfigure,
                    fmatvecBranch=ciq.fmatvecBranch, hdf5serieBranch=ciq.hdf5serieBranch,
                    openmbvBranch=ciq.openmbvBranch, mbsimBranch=ciq.mbsimBranch,
                    buildConfig=buildConfig)
      sys.exit(ret)
  #elif os.environ["MBSIMENVTAGNAME"]=="staging" and ciq.buildCommitID is not None and ciq.buildCommitID!="":
  #  print("Start build of staging build-system: "+ciq.buildCommitID)
  #  sys.stdout.flush()
  #  # run rebuild build-system
  #  ciq.delete()
  #  ret=setup.run("builddocker", args.jobs, printLog=False, builddockerBranch=ciq.buildCommitID)
  #  sys.exit(ret)
  else:
    print("Removed queue entry: not a CI or staging-dockerbuild entry")
    ciq.delete()
