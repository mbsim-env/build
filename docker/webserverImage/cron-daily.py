#!/usr/bin/python

import subprocess
import os
import argparse

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Daily cron job.")
  
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument("--servername", type=str, help="Servername")

args=argparser.parse_args()

# linux64-dailydebug
subprocess.check_call(["python3", "/context/setup.py", "run", "autobuild-linux64-dailydebug", "--servername", args.servername, "-j", str(args.jobs)])

# linux64-dailyrelease
subprocess.check_call(["python3", "/context/setup.py", "run", "autobuild-linux64-dailyrelease", "--servername", args.servername, "-j", str(args.jobs)])
