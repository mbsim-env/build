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
ret1=setup.run("build-linux64-dailydebug", args.servername, args.jobs, printLog=False)

# build doc
ret2=setup.run("builddoc", args.servername, args.jobs, printLog=False)

# linux64-dailyrelease
ret3=setup.run("build-linux64-dailyrelease", args.servername, args.jobs, printLog=False)

# win64-dailyrelease
ret4=setup.run("build-win64-dailyrelease", args.servername, args.jobs, printLog=False)

sys.exit(0 if ret1==0 and ret2==0 and ret3==0 and ret4==0 else 1)
