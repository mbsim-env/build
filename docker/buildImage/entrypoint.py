#!/usr/bin/python3

# imports
import argparse
import os
import subprocess
import sys
import datetime
import codecs
import json
import re
import time
import django
sys.path.append("/context/mbsimenv")
import builds

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/build.")
  
argparser.add_argument("--buildType", type=str, required=True, help="The build type")
argparser.add_argument("--fmatvecBranch", type=str, default="master", help="fmatvec branch")
argparser.add_argument("--hdf5serieBranch", type=str, default="master", help="hdf5serie branch")
argparser.add_argument("--openmbvBranch", type=str, default="master", help="openmbv branch")
argparser.add_argument("--mbsimBranch", type=str, default="master", help="mbsim branch")
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")
argparser.add_argument("--valgrindExamples", action="store_true", help="Run examples also with valgrind.")
#mfmfargparser.add_argument("--updateReferences", nargs='*', default=[], help="Update these references.")

args=argparser.parse_args()

ret=0

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

# check buildtype
if args.buildType != "linux64-ci" and args.buildType != "linux64-dailydebug" and args.buildType != "linux64-dailyrelease":
  raise RuntimeError("Unknown build type "+args.buildType+".")

os.environ["DJANGO_SETTINGS_MODULE"]="mbsimenv.settings"
django.setup()

# wait for database server
while True:
  try:
    django.db.connections['default'].cursor()
    break
  except django.db.utils.OperationalError:
    print("Waiting for database to startup. Retry in 0.5s")
    time.sleep(0.5)

# run

# clone repos if needed
if not os.path.isdir("/mbsim-env/fmatvec"):
  subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/fmatvec.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/hdf5serie"):
  subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/hdf5serie.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/openmbv"):
  subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/openmbv.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if not os.path.isdir("/mbsim-env/mbsim"):
  subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/mbsim.git"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)
if args.valgrindExamples and not os.path.isdir("/mbsim-env/mbsim-valgrind"):
  subprocess.check_call(["git", "clone", "https://github.com/mbsim-env/mbsim.git", "mbsim-valgrind"], cwd="/mbsim-env",
    stdout=sys.stdout, stderr=sys.stderr)

# compile flags
if args.buildType == "linux64-ci" or args.buildType == "linux64-dailydebug":
  os.environ["CXXFLAGS"]="-O0 -g"
  os.environ["CFLAGS"]="-O0 -g"
  os.environ["FFLAGS"]="-O0 -g"
elif args.buildType == "linux64-dailyrelease":
  os.environ["CXXFLAGS"]="-g -O2 -DNDEBUG"
  os.environ["CFLAGS"]="-g -O2 -DNDEBUG"
  os.environ["FFLAGS"]="-g -O2 -DNDEBUG"
else:
  raise RuntimeError("Unknown build type "+args.buildType)

# args
if args.buildType == "linux64-ci":
  ARGS=["--forceBuild", "--disableConfigure", "--disableMakeClean", "--disableDoxygen", "--disableXMLDoc"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableMakeClean"]
  RUNEXAMPLESFILTER=["--filter", "'basic' in labels"]
elif args.buildType == "linux64-dailydebug":
  ARGS=["--docOutDir", "/mbsim-report/doc", "--coverage",]
  RUNEXAMPLESARGS=["--checkGUIs"]
  RUNEXAMPLESFILTER=(["--filter", "'basic' in labels"] if os.environ["MBSIMENVTAGNAME"]=="staging" else [])
elif args.buildType == "linux64-dailyrelease":
  ARGS=["--enableDistribution"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs"]
  RUNEXAMPLESFILTER=["--filter", "'basic' in labels"]

# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')

# env
os.environ['PKG_CONFIG_PATH']=((os.environ['PKG_CONFIG_PATH']+":") if 'PKG_CONFIG_PATH' in os.environ else "")+\
                              "/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig"

#mfmf# update references of examples
#mfmfif len(args.updateReferences)>0:
#mfmf  CURDIR=os.getcwd()
#mfmf  os.chdir("/mbsim-env/mbsim/examples")
#mfmf  if subprocess.call(["python3", "./runexamples.py", "--action", "copyToReference"]+args.updateReferences)!=0:
#mfmf    ret=ret+1
#mfmf    print("runexamples.py --action copyToReference ... failed.")
#mfmf    sys.stdout.flush()
#mfmf  os.chdir(CURDIR)
#mfmf
#mfmf  # update references for download
#mfmf  os.chdir("/mbsim-env/mbsim/examples")
#mfmf  if subprocess.call(["python3", "./runexamples.py", "--action", "pushReference=/mbsim-report/references"]+RUNEXAMPLESFILTER)!=0:
#mfmf    ret=ret+1
#mfmf    print("pushing references to download dir failed.")
#mfmf    sys.stdout.flush()
#mfmf  os.chdir(CURDIR)
#mfmf
#mfmf  if "--forceBuild" not in ARGS:
#mfmf    ARGS.append('--forceBuild')

# run build
os.environ["LDFLAGS"]="-L/usr/lib64/boost169" # use boost 1.69 libraries (and includes, see --with-boost-inc)
localRet=subprocess.call(
  ["/context/mbsimenv/build.py"]+ARGS+[
  "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix", "--webapp",
  "--buildType", args.buildType, "--passToConfigure", "--disable-static",
  "--enable-python", "--with-qwt-inc-prefix=/3rdparty/local/include", "--with-qwt-lib-prefix=/3rdparty/local/lib",
  "--with-boost-inc=/usr/include/boost169",
  "--with-mkoctfile=/3rdparty/local/bin/mkoctfile",
  "--with-qwt-lib-name=qwt", "--with-qmake=qmake-qt5", "COIN_CFLAGS=-I/3rdparty/local/include",
  "COIN_LIBS=-L/3rdparty/local/lib64 -lCoin", "SOQT_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib64 -lSoQt", "--passToRunexamples"]+RUNEXAMPLESARGS+RUNEXAMPLESFILTER,
  stdout=sys.stdout, stderr=sys.stderr)
buildRunID=builds.models.Run.objects.getCurrent(args.buildType).id
if localRet==255:
  sys.exit(0)
if localRet!=0:
  ret=ret+1
  print("build.py failed.")
  sys.stdout.flush()

if args.valgrindExamples:
  # run examples with valgrind
  
  # update
  CURDIR=os.getcwd()
  os.chdir("/mbsim-env/mbsim-valgrind/examples")
  if subprocess.call(["git", "pull"])!=0:
    ret=ret+1
    print("git pull of mbsim-valgrind/examples failed.")
    sys.stdout.flush()
  valgrindEnv=os.environ.copy()
  valgrindEnv["MBSIM_SET_MINIMAL_TEND"]="1"
  # build
  localRet=subprocess.call(["python3", "/context/mbsimenv/runexamples.py", "--checkGUIs", "--disableCompare", "--disableValidate",
    "--buildType", args.buildType+"-valgrind", "--buildSystemRun", "-j", str(args.jobs),
    "--buildRunID", str(buildRunID)]+\
    (["--coverage", "/mbsim-env:-build:/mbsim-env/local:/mbsim-env/mbsim-valgrind/examples"] if "--coverage" in ARGS else [])+\
    ["--prefixSimulationKeyword=VALGRIND", "--prefixSimulation",
    "valgrind --trace-children=yes --trace-children-skip=*/rm,*/dbus-launch,*/ldconfig,*/sh "+\
    "--child-silent-after-fork=yes --num-callers=300 --gen-suppressions=all "+\
    "--suppressions=/mbsim-build/build/misc/valgrind-mbsim.supp "+\
    "--suppressions=/mbsim-build/build/misc/valgrind-python.supp --leak-check=full"]+RUNEXAMPLESFILTER
    , env=valgrindEnv)
  if localRet!=0:
    ret=ret+1
    print("running examples with valgrind failed.")
    sys.stdout.flush()
  os.chdir(CURDIR)

sys.exit(ret)
