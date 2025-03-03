#!/usr/bin/env python3

# imports
import sys
import argparse
import io
import os
import subprocess
import setup
import traceback
import psutil
import socket
import django
sys.path.append("/context/mbsimenv")
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/build.")
  
argparser.add_argument("commitID", type=str, help="The commit ID to build")
argparser.add_argument("--jobs", "-j", type=int, default=max(1,min(round(psutil.virtual_memory().total/pow(1024,3)/2),psutil.cpu_count(False))), help="Number of jobs to run in parallel")

args=argparser.parse_args()

print("Building build system from commit ID "+args.commitID)
sys.stdout.flush()

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

f=io.StringIO()
failed=False
try:
  print("Start building build system from commit ID "+args.commitID+" at "+\
        django.utils.timezone.now().strftime("%Y-%m-%dT%H:%M:%S%z")+"\n\n", file=f)
  
  if not os.path.isdir("/mbsim-env/build"):
    p=subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/build.git"], cwd="/mbsim-env",
                     stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
    f.write(p.stdout)
    p.check_returncode()
  p=subprocess.run(["git", "checkout", "-q", "HEAD~0"], cwd="/mbsim-env/build",
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
  f.write(p.stdout)
  p.check_returncode()
  p=subprocess.run(["git", "fetch", "-q", "-f", "--depth", "1", "origin", args.commitID+":"+args.commitID], cwd="/mbsim-env/build",
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
  f.write(p.stdout)
  p.check_returncode()
  p=subprocess.run(["git", "checkout", "-q", args.commitID], cwd="/mbsim-env/build",
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE, encoding="UTF-8")
  f.write(p.stdout)
  p.check_returncode()
  for s in setup.allServices:
    ret=setup.build(s, args.jobs, fd=f, baseDir="/mbsim-env/build/docker")
    if ret!=0:
      raise RuntimeError("Building the docker image failed.")
  
  print("\n\nFinished building build system from commit ID "+args.commitID+" at "+\
        django.utils.timezone.now().strftime("%Y-%m-%dT%H:%M:%S%z"), file=f)

except:
  print(traceback.format_exc(), file=f)
  failed=True
finally:
  print("Save build result output in database", file=f)
  if not failed:
    print("and restart services.", file=f)
  sys.stdout.flush()
  
  info, _=service.models.Info.objects.get_or_create(id=args.commitID)
  info.longInfo=f.getvalue()
  info.save()
  service.models.Info.objects.exclude(id=args.commitID).delete() # remove everything except the current runnig Info object

  django.db.connections.close_all() # close all connections before restarting

if not failed:
  print("Restart now.")
  print("Stopping service now.")
  sys.stdout.flush()
  if setup.run('service', 6, daemon="stop", keepBuildDockerContainerRunning=True)!=0:
    raise RuntimeError("Stopping service failed.")
  print("Restarting service now.")
  sys.stdout.flush()
  if setup.run('service', 6, daemon="start")!=0:
    raise RuntimeError("Starting service failed.")
  print("All done.")
  sys.stdout.flush()
