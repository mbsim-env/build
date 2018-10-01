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
setup.run("autobuild-linux64-dailydebug", args.servername, args.jobs, printLog=False)

# linux64-dailyrelease
setup.run("autobuild-linux64-dailyrelease", args.servername, args.jobs, printLog=False)
