#!/usr/bin/env python3

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
  mbsimBranchSplit=args.mbsimBranch.split("*")
  sha=mbsimBranchSplit[1 if len(mbsimBranchSplit)>=2 and mbsimBranchSplit[1]!="" else 0]
  os.chdir("/mbsim-env/mbsim")
  if subprocess.call(["git", "checkout", "-q", "HEAD~0"])!=0:
    ret=ret+1
    print("git checkout detached failed.")
    sys.stdout.flush()
  if subprocess.call(["git", "fetch", "-q", "-f", "--depth", "1", "origin", sha+":"+sha])!=0:
    ret=ret+1
    print("git fetch failed.")
    sys.stdout.flush()
  if subprocess.call(["git", "checkout", "-q", sha])!=0:
    ret=ret+1
    print("git checkout of branch "+args.mbsimBranch+" failed.")
    sys.stdout.flush()

# run builddoc.py
subprocess.check_call(["/context/mbsimenv/builddoc.py", "--buildSystemRun"], cwd="/mbsim-env/mbsim/manuals")
