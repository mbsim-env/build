#!/usr/bin/python3

import argparse
import sys
sys.path.append("/context")
import setup
sys.path.append("/context/mbsimenv")
import mbsimenvSecrets

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

# branches to use
fmatvecBranch="master"
hdf5serieBranch="master"
openmbvBranch="master"
mbsimBranch="master"

# linux64-dailydebug
contldd=setup.run("build-linux64-dailydebug", 6, printLog=False, detach=True, addCommands=["--forceBuild"],
                  fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)

# linux64-dailyrelease
contldr=setup.run("build-linux64-dailyrelease", 2, printLog=False, detach=True, addCommands=["--forceBuild"],
                  fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
retldr=setup.waitContainer(contldr)

# win64-dailyrelease
contwdr=setup.run("build-win64-dailyrelease", 2, printLog=False, detach=True, addCommands=["--forceBuild"],
                  fmatvecBranch=fmatvecBranch, hdf5serieBranch=hdf5serieBranch, openmbvBranch=openmbvBranch, mbsimBranch=mbsimBranch)
retwdr=setup.waitContainer(contwdr)

retldd=setup.waitContainer(contldd)

# build doc
contd=setup.run("builddoc", 2, printLog=False, detach=True, addCommands=["--forceBuild"])
retd=setup.waitContainer(contd)

# return
sys.exit(0 if retldd==0 and retd==0 and retldr==0 and retwdr==0 else 1)
