#!/usr/bin/python3

import subprocess
import os
import argparse
import fcntl
import json
import sys
sys.path.append("/context")
import setup

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")

args=argparser.parse_args()

# read config file
def readConfigFile():
  configFilename="/mbsim-config/mbsimBuildService.conf"
  fd=open(configFilename, 'r')
  fcntl.lockf(fd, fcntl.LOCK_SH)
  config=json.load(fd)
  fcntl.lockf(fd, fcntl.LOCK_UN)
  fd.close()
  return config

config=readConfigFile()

# linux64-dailydebug
contldd=setup.run("build-linux64-dailydebug", 6, printLog=False, detach=True, addCommands=["--forceBuild"],
                  statusAccessToken=config["status_access_token"])

# linux64-dailyrelease
contldr=setup.run("build-linux64-dailyrelease", 2, printLog=False, detach=True, addCommands=["--forceBuild"],
                  statusAccessToken=config["status_access_token"])
retldr=setup.waitContainer(contldr)

# win64-dailyrelease
contwdr=setup.run("build-win64-dailyrelease", 2, printLog=False, detach=True, addCommands=["--forceBuild"],
                  statusAccessToken=config["status_access_token"])
retwdr=setup.waitContainer(contwdr)

retldd=setup.waitContainer(contldd)

# build doc
contd=setup.run("builddoc", 2, printLog=False, detach=True, addCommands=["--forceBuild"],
                statusAccessToken=config["status_access_token"])
retd=setup.waitContainer(contd)

# return
sys.exit(0 if retldd==0 and retd==0 and retldr==0 and retwdr==0 else 1)
