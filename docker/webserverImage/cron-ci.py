#!/usr/bin/python3

import sys
import os
import socket
import argparse
import django
import datetime
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
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

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
  if ciq.fmatvecBranch and ciq.hdf5serieBranch and ciq.openmbvBranch and ciq.mbsimBranch:
    print("Found something to build: "+ciq.fmatvecBranch+", "+ciq.hdf5serieBranch+", "+\
          ciq.openmbvBranch+", "+ciq.mbsimBranch+" starting in, at most, "+str(waitTime))
    sys.stdout.flush()
    if django.utils.timezone.now()-ciq.recTime>waitTime:
      print("Start build: "+ciq.fmatvecBranch+", "+ciq.hdf5serieBranch+", "+\
            ciq.openmbvBranch+", "+ciq.mbsimBranch)
      sys.stdout.flush()
      # run linux64-ci
      ret=setup.run("build-linux64-ci", args.jobs, printLog=False,
                    fmatvecBranch=ciq.fmatvecBranch, hdf5serieBranch=ciq.hdf5serieBranch,
                    openmbvBranch=ciq.openmbvBranch, mbsimBranch=ciq.mbsimBranch)
      ciq.delete()
      sys.exit(ret)
  if ciq.buildCommitID:
    print("Start build of build-system: "+ciq.buildCommitID)
    sys.stdout.flush()
    # run rebuild build-system
    ret=setup.run("builddocker", args.jobs, printLog=False, builddockerBranch=ciq.buildCommitID)
    ciq.delete()
    sys.exit(ret)
