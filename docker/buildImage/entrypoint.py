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
sys.path.append("/mbsim-build/build/buildScripts")
import build

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
argparser.add_argument("--updateReferences", nargs='*', default=[], help="Update these references.")

args=argparser.parse_args()

statusAccessToken=os.environ["STATUSACCESSTOKEN"]
os.environ["STATUSACCESSTOKEN"]=""

ret=0

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")
if "MBSIMENVTAGNAME" not in os.environ or os.environ["MBSIMENVTAGNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVTAGNAME is not defined.")

# check buildtype
if args.buildType != "linux64-ci" and args.buildType != "linux64-dailydebug" and args.buildType != "linux64-dailyrelease":
  raise RuntimeError("Unknown build type "+args.buildType+".")

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
  ARGS=["--docOutDir", "/mbsim-report/doc", "--coverage", "--staticCodeAnalyzis"]
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

# update references of examples
if len(args.updateReferences)>0:
  CURDIR=os.getcwd()
  os.chdir("/mbsim-env/mbsim/examples")
  if subprocess.call(["python3", "./runexamples.py", "--action", "copyToReference"]+args.updateReferences)!=0:
    ret=ret+1
    print("runexamples.py --action copyToReference ... failed.")
    sys.stdout.flush()
  os.chdir(CURDIR)

  # update references for download
  os.chdir("/mbsim-env/mbsim/examples")
  if subprocess.call(["python3", "./runexamples.py", "--action", "pushReference=/mbsim-report/references"]+RUNEXAMPLESFILTER)!=0:
    ret=ret+1
    print("pushing references to download dir failed.")
    sys.stdout.flush()
  os.chdir(CURDIR)

  if "--forceBuild" not in ARGS:
    ARGS.append('--forceBuild')

# run build
os.environ["STATUSACCESSTOKEN"]=statusAccessToken
ROTATE=3 if os.environ["MBSIMENVTAGNAME"]=="staging" else 20
localRet=subprocess.call(
  ["/mbsim-build/build/buildScripts/build.py"]+ARGS+["--url", "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/"+args.buildType+"/report",
  "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--rotate", str(ROTATE), "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix", "--webapp",
  "--reportOutDir", "/mbsim-report/report", "--buildType", args.buildType, "--passToConfigure", "--disable-static",
  "--enable-python", "--with-qwt-inc-prefix=/3rdparty/local/include", "--with-qwt-lib-prefix=/3rdparty/local/lib",
  "--with-qwt-lib-name=qwt", "--with-qmake=qmake-qt5", "COIN_CFLAGS=-I/3rdparty/local/include",
  "COIN_LIBS=-L/3rdparty/local/lib64 -lCoin", "SOQT_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib64 -lSoQt", "--passToRunexamples"]+RUNEXAMPLESARGS+RUNEXAMPLESFILTER,
  stdout=sys.stdout, stderr=sys.stderr)
os.environ["STATUSACCESSTOKEN"]=""
if localRet==255:
  sys.exit(0)
if localRet!=0:
  ret=ret+1
  print("build.py failed.")
  sys.stdout.flush()

if args.valgrindExamples:
  # run examples with valgrind
  
  # set github statuses
  timeID=datetime.datetime.utcnow()
  timeID=datetime.datetime(timeID.year, timeID.month, timeID.day, timeID.hour, timeID.minute, timeID.second)
  with codecs.open("/mbsim-report/report/result_current/repoState.json", "r", encoding="utf-8") as f:
    commitidfull=json.load(f)
  build.setStatus(statusAccessToken, commitidfull, "pending", timeID,
        "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/"+args.buildType+"/report/runexamples_valgrind_report",
        args.buildType+"-valgrind")
  # update
  CURDIR=os.getcwd()
  os.chdir("/mbsim-env/mbsim-valgrind/examples")
  if subprocess.call(["git", "pull"])!=0:
    ret=ret+1
    print("git pull of mbsim-valgrind/examples failed.")
    sys.stdout.flush()
  valgrindEnv=os.environ
  valgrindEnv["MBSIM_SET_MINIMAL_TEND"]="1"
  # build
  coverage = ["--coverage", "/mbsim-env:-build:/mbsim-env/local:/mbsim-env/mbsim-valgrind/examples"] if "--coverage" in ARGS else []
  localRet=subprocess.call(["python3", "./runexamples.py", "--timeID", timeID.isoformat()+"Z", "--rotate", str(ROTATE), "-j", str(args.jobs)]+coverage+["--reportOutDir",
            "/mbsim-report/report/runexamples_valgrind_report", "--url",
            "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/"+args.buildType+"/report/runexamples_valgrind_report",
            "--buildSystemRun", "--checkGUIs", "--prefixSimulationKeyword=VALGRIND", "--prefixSimulation",
            "valgrind --trace-children=yes --trace-children-skip=*/rm,*/dbus-launch,*/ldconfig,*/sh --child-silent-after-fork=yes --num-callers=300 --gen-suppressions=all "+
            "--suppressions=/mbsim-build/build/buildScripts/valgrind-mbsim.supp "+
            "--suppressions=/mbsim-build/build/buildScripts/valgrind-python.supp "+
            "--leak-check=full", "--disableCompare", "--disableValidate",
            "--buildType", args.buildType+"-valgrind"]+RUNEXAMPLESFILTER
            , env=valgrindEnv)
  if localRet!=0:
    ret=ret+1
    print("running examples with valgrind failed.")
    sys.stdout.flush()
  os.chdir(CURDIR)
  # set github statuses
  endTime=datetime.datetime.now()
  endTime=datetime.datetime(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second)
  linkName=os.readlink("/mbsim-report/report/runexamples_valgrind_report/result_current")
  currentID=int(re.sub(".*result_([0-9]+)$", "\\1", linkName))
  build.setStatus(statusAccessToken, commitidfull, "success" if ret==0 else "failure", timeID,
        "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/"+args.buildType+"/report/runexamples_valgrind_report/result_%010d/index.html"%(currentID),
        args.buildType+"-valgrind", endTime)

sys.exit(ret)
