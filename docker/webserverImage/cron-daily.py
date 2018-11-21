#!/usr/bin/python

import subprocess
import os
import argparse
import sys
sys.path.append("/context")
import setup

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument("--servername", type=str, help="Servername")

args=argparser.parse_args()

# linux64-dailydebug
contldd=setup.run("build-linux64-dailydebug", args.servername, 6, printLog=False, detach=True, addCommands=["--forceBuild"])

# build doc
contd=setup.run("builddoc", args.servername, 2, printLog=False, detach=True, addCommands=["--forceBuild"])
retd=contd.wait()

# linux64-dailyrelease
contldr=setup.run("build-linux64-dailyrelease", args.servername, 2, printLog=False, detach=True, addCommands=["--forceBuild"])
retldr=contldr.wait()

# win64-dailyrelease
contwdr=setup.run("build-win64-dailyrelease", args.servername, 2, printLog=False, detach=True, addCommands=["--forceBuild"])
retwdr=contwdr.wait()

retldd=contldd.wait()

# return
sys.exit(0 if retldd["StatusCode"]==0 and retd["StatusCode"]==0 and retldr["StatusCode"]==0 and retwdr["StatusCode"]==0 else 1)
