#!/usr/bin/python3

import argparse
import os
import sys
import subprocess

argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/builddoc.")
  
argparser.add_argument("--mbsimBranch", type=str, required=False, help="The mbsim branch name to use for the manuals")

args=argparser.parse_args()

# clone repos if needed
if not os.path.isdir("/mbsim-env/mbsim"):
  subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/mbsim.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)

if args.mbsimBranch is not None and args.mbsimBranch!="":
  sha=args.mbsimBranch.split("*")[-1]
  os.chdir("/mbsim-env/mbsim")
  if subprocess.call(["git", "checkout", "-q", "HEAD~0"])!=0:
    ret=ret+1
    print("git checkout detached failed.")
  if subprocess.call(["git", "fetch", "-q", "--depth", "1", "origin", sha+":"+sha])!=0:
    ret=ret+1
    print("git fetch failed.")
  if subprocess.call(["git", "checkout", "-q", sha])!=0:
    ret=ret+1
    print("git checkout of branch "+args.mbsimBranch+" failed.")

# run builddoc.py
subprocess.check_call(["/context/mbsimenv/builddoc.py", "--buildSystemRun"], cwd="/mbsim-env/mbsim/manuals")
