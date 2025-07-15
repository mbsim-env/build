#!/usr/bin/env python3

# imports
import argparse
import os
import subprocess
import sys
import psutil
import django
import time
import json
sys.path.append("c:/msys64/context/mbsimenv")
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/buildmsys2ucrt64.")
  
argparser.add_argument("--buildType", type=str, required=True, help="The build type")
argparser.add_argument("--executor", type=str, required=True, help="The executor of this build")
argparser.add_argument("--enforceConfigure", action="store_true", help="Enforce the configure step")
argparser.add_argument("--fmatvecBranch", type=str, default="master", help="fmatvec branch")
argparser.add_argument("--hdf5serieBranch", type=str, default="master", help="hdf5serie branch")
argparser.add_argument("--openmbvBranch", type=str, default="master", help="openmbv branch")
argparser.add_argument("--mbsimBranch", type=str, default="master", help="mbsim branch")
argparser.add_argument("--jobs", "-j", type=int, default=max(1,min(round(psutil.virtual_memory().total/pow(1024,3)/2),psutil.cpu_count(False))), help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")
argparser.add_argument("--ccacheSize", default=10, type=float, help="Maximal ccache size in GB.")
argparser.add_argument("--buildRunID", default=None, type=int, help="The id of the builds.model.Run dataset this example run belongs to.")
argparser.add_argument("--buildConfig", type=json.loads, default={}, help="Load an additional build(/examples) configuration as json string")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# check buildtype
if args.buildType!="msys2win64-ci" and args.buildType!="msys2win64-dailyrelease":
  raise RuntimeError("Unknown build type "+args.buildType+".")

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
django.setup()

# wait for database server
while True:
  try:
    django.db.connections['default'].cursor()
    break
  except django.db.utils.OperationalError:
    print("Waiting for database to startup. Retry in 0.5s")
    sys.stdout.flush()
    time.sleep(0.5)
django.db.connections.close_all()

# run

# clone repos if needed
for repo in [
              "https://github.com/mbsim-env/fmatvec.git",
              "https://github.com/mbsim-env/hdf5serie.git",
              "https://github.com/mbsim-env/openmbv.git",
              "https://github.com/mbsim-env/mbsim.git",
            ]+list(map(lambda repo: repo["gitURL"], args.buildConfig.get("addRepos", []))):
  localDir=repo.split("/")[-1][0:-4]
  if not os.path.isdir("c:/msys64/mbsim-env/"+localDir):
      subprocess.check_call(["git", "clone", "-q", "--depth", "1", repo], cwd="c:/msys64/mbsim-env",
      stdout=sys.stdout, stderr=sys.stderr)

# args
if args.buildType == "msys2win64-dailyrelease":
  BUILDTYPE="Release"
  os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  ARGS=["--enableDistribution"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs", "--filter", "'basic' in labels", "--prefixSimulation", "gdb -q -n -batch --return-child-result -ex run -ex backtrace -ex quit --args"]
  
elif args.buildType == "msys2win64-ci":
  BUILDTYPE="Debug"
  os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -Og -g -gdwarf-2"
  os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -Og -g -gdwarf-2"
  os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -Og -g -gdwarf-2"
  ARGS=["--disableDoxygen", "--disableXMLDoc"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs", "--disableMakeClean", "--filter", "'basic' in labels", "--prefixSimulation", "gdb -q -n -batch --return-child-result -ex run -ex backtrace -ex quit --args"]

  #mfmf# get current/last image ID
  #mfmfcurImageID=os.environ.get("MBSIMENVIMAGEID", None)
  #mfmfif curImageID is not None:
  #mfmf  info=service.models.Info.objects.all().first()
  #mfmf  lastImageID=info.buildmsys2ucrt64ImageID if info is not None else ""
  #mfmf  # configure needed?
  #mfmf  if lastImageID==curImageID and not args.enforceConfigure:
  #mfmf    ARGS.append("--disableConfigure")
  #mfmf  # save build image id
  #mfmf  info.buildmsys2ucrt64ImageID=curImageID
  #mfmf  info.save()
else:
  raise RuntimeError("Unknown build type "+args.buildType)
  
# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')

# env
os.environ['PKG_CONFIG_PATH']=((os.environ['PKG_CONFIG_PATH']+";") if 'PKG_CONFIG_PATH' in os.environ else "")+\
                              "c:/msys64/mbsim-env/local/lib/pkgconfig;c:/msys64/mbsim-env/local/lib64/pkgconfig"
os.environ["PATH"]="c:/msys64/mbsim-env/local/bin;"+os.environ["PATH"]

subprocess.call(["ccache", "-M", f"{args.ccacheSize:f}G"])
print("Zeroing ccache statistics.")
subprocess.call(["ccache", "-z"])
sys.stdout.flush()

if args.buildRunID is not None:
  ARGS.append("--buildRunID")
  ARGS.append(str(args.buildRunID))

# run build
ret=subprocess.call(
  ["c:/msys64/ucrt64/bin/python.exe", "c:/msys64/context/mbsimenv/build.py"]+ARGS+[
  "--toolJobs", "4", "--sourceDir", "c:/msys64/mbsim-env", "--binSuffix=-build", "--prefix", "c:/msys64/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix",
  "--buildType", args.buildType,
  "--executor", args.executor,
  "--buildConfig", json.dumps(args.buildConfig),
  "--passToConfigure", "--enable-shared", "--disable-static",
  "--with-boost-system-lib=boost_system-mt",
  "--with-boost-filesystem-lib=boost_filesystem-mt",
  "--with-boost-iostreams-lib=boost_iostreams-mt",
  "--with-boost-chrono-lib=boost_chrono-mt",
  "--with-boost-thread-lib=boost_thread-mt",
  "--with-boost-program-options-lib=boost_program_options-mt",
  "--with-boost-regex-lib=boost_regex-mt",
  "--with-boost-timer-lib=boost_timer-mt",
  "--with-boost-date-time-lib=boost_date_time-mt",
  "--with-qwt-inc-prefix=/ucrt64/include/qwt-qt5",
  "--with-qwt-lib-name=qwt-qt5",
  "--passToCMake",
  "-DSPOOLES_INCLUDE_DIRS=c:/msys64/ucrt64/include/spooles",
  "-DSPOOLES_LIBRARIES=c:/msys64/ucrt64/lib/libspooles.a",
  "-DCMAKE_BUILD_TYPE="+BUILDTYPE,
  "-DCMAKE_CXX_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CXXFLAGS"],
  "-DCMAKE_C_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CFLAGS"],
  "-DCMAKE_Fortran_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["FFLAGS"],
  "--passToRunexamples"]+RUNEXAMPLESARGS,
  stdout=sys.stdout, stderr=sys.stderr)

print("Dump ccache statistics:")
subprocess.call(["ccache", "-s"])
sys.stdout.flush()

if ret!=0:
  print("build.py failed.")
  sys.stdout.flush()

sys.exit(ret)
