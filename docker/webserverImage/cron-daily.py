#!/usr/bin/python3

import argparse
import sys
import os
sys.path.append("/context")
import setup
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets
import django
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

def dailyBuild(fmatvecBranch, hdf5serieBranch, openmbvBranch, mbsimBranch, ext):
  # linux64-dailydebug
  contldd=setup.run("build-linux64-dailydebug"+ext, 6, printLog=False, detach=True, addCommands=["--forceBuild"],
                    fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
  
  # win64-dailyrelease
  contwdr=setup.run("build-win64-dailyrelease"+ext, 3, printLog=False, detach=True, addCommands=["--forceBuild"],
                    fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
  retwdr=setup.waitContainer(contwdr)
  
  # linux64-dailyrelease
  contldr=setup.run("build-linux64-dailyrelease"+ext, 3, printLog=False, detach=True, addCommands=["--forceBuild"],
                    fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
  retldr=setup.waitContainer(contldr)
  
  retldd=setup.waitContainer(contldd)
  
  # return
  return 0 if retldd==0 and retldr==0 and retwdr==0 else 1

ret=0
# build the master branch combi first
ret=ret+dailyBuild("master", "master", "master", "master", "")
  
# build doc
contd=setup.run("builddoc", 2, printLog=False, detach=True, addCommands=["--forceBuild"])
ret=ret+abs(setup.waitContainer(contd))

# now build all others
for db in service.models.DailyBranches.objects.all():
  # skip the master branch combi (already done first, see above)
  if db.fmatvecBranch=="master" and db.hdf5serieBranch=="master" and db.openmbvBranch=="master" and db.mbsimBranch=="master":
    continue
  # build the db branch combi
  ret=ret+dailyBuild(db.fmatvecBranch, db.hdf5serieBranch, db.openmbvBranch, db.mbsimBranch, "-nonedefbranches")

sys.exit(ret)
