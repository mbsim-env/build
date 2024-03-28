#!/usr/bin/env python3

# imports
import argparse
import os
import subprocess
import sys
import psutil
import django
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
argparser.add_argument("--jobs", "-j", type=int, default=psutil.cpu_count(False), help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")
argparser.add_argument("--ccacheSize", default=10, type=int, help="Maximal ccache size in GB.")
argparser.add_argument("--buildRunID", default=None, type=int, help="The id of the builds.model.Run dataset this example run belongs to.")

args=argparser.parse_args()

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# check buildtype
if args.buildType != "win64-ci" and not args.buildType.startswith("win64-dailyrelease"):
  raise RuntimeError("Unknown build type "+args.buildType+".")

#mfmfos.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_buildsystem"
os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings_local"
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
if not os.path.isdir("/mbsim-env/fmatvec"):
  subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/fmatvec.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/hdf5serie"):
  subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/hdf5serie.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/openmbv"):
  subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/openmbv.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/mbsim"):
  subprocess.check_call(["git", "clone", "-q", "--depth", "1", "https://github.com/mbsim-env/mbsim.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)

# args
if args.buildType.startswith("win64-dailyrelease"):
  BUILDTYPE="Release"
  os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
  ARGS=["--enableDistribution"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs", "--exeExt", ".exe", "--filter", "'basic' in labels"]
  
elif args.buildType == "win64-ci":
  BUILDTYPE="Debug"
  os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -Og -g -gdwarf-2"
  os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -Og -g -gdwarf-2"
  os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -Og -g -gdwarf-2"
  ARGS=["--disableDoxygen", "--disableXMLDoc"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs", "--disableMakeClean", "--exeExt", ".exe", "--filter", "'basic' in labels"]

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
os.environ['PKG_CONFIG_PATH']=((os.environ['PKG_CONFIG_PATH']+":") if 'PKG_CONFIG_PATH' in os.environ else "")+\
                              "/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig"

subprocess.call(["ccache", "-M", str(args.ccacheSize)+"G"])
print("Zeroing ccache statistics.")
subprocess.call(["ccache", "-z"])
sys.stdout.flush()

if args.buildRunID is not None:
  ARGS.append("--buildRunID")
  ARGS.append(str(args.buildRunID))

# run build
ret=subprocess.call(
  ["c:/msys64/ucrt64/bin/python.exe", "c:/mbsim-env/build/django/mbsimenv/build.py"]+ARGS+[
  "--sourceDir", "c:/mbsim-env", "--binSuffix=-dockermsys2ucrt64", "--prefix", "c:/mbsim-env/local-dockermsys2ucrt64", "-j", str(args.jobs), "--buildSystemRun",
  "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix",
  "--buildType", args.buildType,
  "--executor", args.executor,
  "--passToConfigure", "--enable-shared", "--disable-static", "--enable-python",
  "--with-boost-system-lib=boost_system-mt",
  "--with-boost-filesystem-lib=boost_filesystem-mt",
  "--with-boost-chrono-lib=boost_chrono-mt",
  "--with-boost-thread-lib=boost_thread-mt",
  "--with-boost-program-options-lib=boost_program_options-mt",
  "--with-boost-regex-lib=boost_regex-mt",
  "--with-boost-timer-lib=boost_timer-mt",
  "--with-boost-date-time-lib=boost_date_time-mt",
  "--passToCMake",
  "-DSPOOLES_INCLUDE_DIRS=/ucrt64/include/spooles",
  "-DSPOOLES_LIBRARIES=/ucrt64/lib/libspooles.a",
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
