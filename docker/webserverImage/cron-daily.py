#!/usr/bin/env python3

import argparse
import sys
import os
import psutil
sys.path.append("/context")
import setup
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets
import django
import json
import math
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=max(1,min(round(psutil.virtual_memory().total/pow(1024,3)/2),psutil.cpu_count(False))), help="Number of jobs to run in parallel")

args=argparser.parse_args()

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

def dailyBuild(fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch):
  with open("/context/buildConfig.json", "rt") as f:
    buildConfig=json.load(f)
  # linux64-dailydebug
  contldd=setup.run("build-linux64-dailydebug", math.ceil(args.jobs/2), printLog=False, detach=True, addCommands=[],
                    fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                    buildConfig=buildConfig)

  # linux64-dailyrelease
  contldr=setup.run("build-linux64-dailyrelease", math.ceil(args.jobs/2), printLog=False, detach=True, addCommands=[],
                    fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch,
                    buildConfig=buildConfig)

  retldr=setup.waitContainer(contldr)
  retldd=setup.waitContainer(contldd)

  # return
  return 0 if retldd==0 and retldr==0 else 1

ret=0
# build the master branch combi first (if it exists)
if service.models.DailyBranches.objects.filter(fmatvecBranch="master", hdf5serieBranch="master",
                                               openmbvBranch="master", mbsimBranch="master").count()>0:
  ret=ret+dailyBuild("master", "master", "master", "master")
  
# build doc
contd=setup.run("builddoc", args.jobs, printLog=False, detach=True, addCommands=[])
ret=ret+abs(setup.waitContainer(contd))

# now build all others
for db in service.models.DailyBranches.objects.all():
  # skip the master branch combi (already done first, see above)
  if db.fmatvecBranch=="master" and db.hdf5serieBranch=="master" and db.openmbvBranch=="master" and db.mbsimBranch=="master":
    continue
  # build the db branch combi
  ret=ret+dailyBuild(db.fmatvecBranch, db.hdf5serieBranch, db.openmbvBranch, db.mbsimBranch)

sys.exit(ret)
