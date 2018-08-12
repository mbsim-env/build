#!/usr/bin/python

# imports
import argparse
import os
import subprocess
import sys
import datetime
import codecs
import json
sys.path.append("/mbsim-build/build/buildScripts")
import build

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/autobuild.")
  
argparser.add_argument("--buildType", type=str, required=True, help="The build type")
argparser.add_argument("--fmatvecBranch", type=str, default="master", help="fmatvec branch")
argparser.add_argument("--hdf5serieBranch", type=str, default="master", help="hdf5serie branch")
argparser.add_argument("--openmbvBranch", type=str, default="master", help="openmbv branch")
argparser.add_argument("--mbsimBranch", type=str, default="master", help="mbsim branch")
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")
argparser.add_argument("--staticCodeAnalyzis", action="store_true", help="Passed to build.py if existing")
argparser.add_argument("--buildDoc", action="store_true", help="Build external docu, like papers ...")
argparser.add_argument("--valgrindExamples", action="store_true", help="Run examples also with valgrind.")
argparser.add_argument("--updateReferences", nargs='*', default=[], help="Update these references.")

args=argparser.parse_args()

ret=0

# check volumes
if not os.path.isdir("/mbsim-env"):
  raise RuntimeError("Need a volume /mbsim-env mounted when running the container")
if not os.path.isdir("/mbsim-ccache"):
  raise RuntimeError("Need a volume /mbsim-ccache mounted when running the container")
if not os.path.isdir("/mbsim-report"):
  raise RuntimeError("Need a volume /mbsim-report mounted when running the container")
if not os.path.isdir("/mbsim-state"):
  raise RuntimeError("Need a volume /mbsim-state mounted when running the container")
if not os.path.isdir("/mbsim-config"):
  raise RuntimeError("Need a volume /mbsim-config mounted when running the container")

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
  RUNEXAMPLES=["--disableCompare", "--disableMakeClean", "--filter", "'basic' in labels"]
elif args.buildType == "linux64-dailydebug":
  ARGS=["--docOutDir", "/mbsim-report/"+args.buildType+"/doc", "--coverage"]
  ARGS=ARGS+["--forceBuild"]#mfmfdeline
  RUNEXAMPLES=["--checkGUIs"]
  RUNEXAMPLES=RUNEXAMPLES+["xml/hierachical_modelling"]#mfmfdeline
elif args.buildType == "linux64-dailyrelease":
  ARGS=["--enableDistribution"]
  ARGS=ARGS+["--forceBuild"]#mfmfdeline
  RUNEXAMPLES=["--disableCompare", "--disableValidate", "--checkGUIs", "--filter", "'basic' in labels"]

# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')
if args.staticCodeAnalyzis:
  ARGS.append("--staticCodeAnalyzis")

# uncomment this to run static code analyzis
# ARGS.append("--staticCodeAnalyzis")

# build swig interfaces
os.environ["MBSIM_SWIG"]="1"

# update references of examples
if len(args.updateReferences)>0:
  CURDIR=os.getcwd()
  os.chdir("/mbsim-env/mbsim/examples")
  if subprocess.call(["./runexamples.py", "--action", "copyToReference"]+args.updateReferences)!=0:
    ret=ret+1
    print("runexamples.py --action copyToReference ... failed.")
  os.chdir(CURDIR)

  # update references for download
  os.chdir("/mbsim-env/mbsim/examples")
  if subprocess.call(["./runexamples.py", "--action", "pushReference=/mbsim-report/"+args.buildType+"/references"])!=0:
    ret=ret+1
    print("pushing references to download dir failed.")
  os.chdir(CURDIR)

  if "--forceBuild" not in ARGS:
    ARGS.append('--forceBuild')

# run build
localRet=subprocess.call(
  ["/mbsim-build/build/buildScripts/build.py"]+ARGS+["--url", "https://www.mbsim-env.de/mbsim/"+args.buildType+"/report",
  "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--configDir", "/mbsim-config", "--stateDir", "/mbsim-state", "--rotate", "20", "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix", "--webapp",
  "--reportOutDir", "/mbsim-report/"+args.buildType+"/report", "--buildType", args.buildType, "--passToConfigure", "--disable-static",
  "--enable-python", "--with-qwt-inc-prefix=/3rdparty/local/include", "--with-qwt-lib-prefix=/3rdparty/local/lib",
  "--with-qwt-lib-name=qwt", "--with-qmake=qmake-qt5", "COIN_CFLAGS=-I/3rdparty/local/include",
  "COIN_LIBS=-L/3rdparty/local/lib64 -lCoin", "SOQT_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib64 -lSoQt", "--passToRunexamples"]+RUNEXAMPLES,
  stdout=sys.stdout, stderr=sys.stderr)
if localRet!=0:
  ret=ret+1
  print("build.py failed.")

if args.valgrindExamples:
  # run examples with valgrind
  
  # set github statuses
  currentID=int(os.readlink("/mbsim-report/"+args.buildType+"/report/result_current")[len("result_"):])
  timeID=datetime.datetime.now()
  timeID=datetime.datetime(timeID.year, timeID.month, timeID.day, timeID.hour, timeID.minute, timeID.second)
  with codecs.open("/mbsim-report/"+args.buildType+"/report/result_current/repoState.json", "r", encoding="utf-8") as f:
    commitidfull=json.load(f)
  build.setStatus(commitidfull, "pending", currentID, timeID,
        "https://www.mbsim-env.de/mbsim/"+args.buildType+"/report/runexamples_valgrind_report/result_%010d/index.html"%(currentID),
        args.buildType+"-valgrind")
  # update
  CURDIR=os.getcwd()
  os.chdir("/mbsim-env/mbsim-valgrind/examples")
  if subprocess.call(["git", "pull"])!=0:
    ret=ret+1
    print("git pull of mbsim-valgrind/examples failed.")
  valgrindEnv=os.environ
  valgrindEnv["MBSIM_SET_MINIMAL_TEND"]="1"
  # build
  coverage = ["--coverage", "/mbsim-env::/mbsim-env/local"] if "--coverage" in ARGS else []
  localRet=subprocess.call(["./runexamples.py", "--rotate", "20", "-j", str(args.jobs)]+coverage+["--reportOutDir",
            "/mbsim-report/"+args.buildType+"/report/runexamples_valgrind_report", "--url",
            "https://www.mbsim-env.de/mbsim/"+args.buildType+"/report/runexamples_valgrind_report",
            "--buildSystemRun", "/mbsim-build/build/buildSystem/scripts", "--stateDir", "/mbsim-state",
            "--prefixSimulationKeyword=VALGRIND", "--prefixSimulation",
            "valgrind --trace-children=yes --trace-children-skip=*/rm --num-callers=150 --gen-suppressions=all --suppressions="+
            "/mbsim-build/build/buildScripts/valgrind-mbsim.supp --leak-check=full", "--disableCompare", "--disableValidate",
            "--buildType", args.buildType+"-valgrind"]+
            ["xml/hierachical_modelling"]#mfmfdeline
            , env=valgrindEnv)
  if localRet!=0:
    ret=ret+1
    print("running examples with valgrind failed.")
  os.chdir(CURDIR)
  # set github statuses
  endTime=datetime.datetime.now()
  endTime=datetime.datetime(endTime.year, endTime.month, endTime.day, endTime.hour, endTime.minute, endTime.second)
  build.setStatus(commitidfull, "success" if ret==0 else "failure", currentID, timeID,
        "https://www.mbsim-env.de/mbsim/"+args.buildType+"/report/runexamples_valgrind_report/result_%010d/index.html"%(currentID),
        args.buildType+"-valgrind", endTime)

if args.buildDoc:
  # build doc
  if subprocess.call(["/mbsim-build/build/buildSystem/scripts/builddoc.py", "/mbsim-state",
                      "/mbsim-env/mbsim/manuals", "/mbsim-report/"+args.buildType+"/manuals"])!=0:
    ret=ret+1
    print("builddoc.py failed.")

sys.exit(ret)
