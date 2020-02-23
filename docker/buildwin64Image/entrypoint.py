#!/usr/bin/python3

# imports
import argparse
import os
import subprocess
import sys

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/buildwin64.")
  
argparser.add_argument("--buildType", type=str, required=True, help="The build type")
argparser.add_argument("--fmatvecBranch", type=str, default="master", help="fmatvec branch")
argparser.add_argument("--hdf5serieBranch", type=str, default="master", help="hdf5serie branch")
argparser.add_argument("--openmbvBranch", type=str, default="master", help="openmbv branch")
argparser.add_argument("--mbsimBranch", type=str, default="master", help="mbsim branch")
argparser.add_argument("--jobs", "-j", type=int, default=1, help="Number of jobs to run in parallel")
argparser.add_argument('--forceBuild', action="store_true", help="Passed to buily.py if existing")

args=argparser.parse_args()

statusAccessToken=os.environ["STATUSACCESSTOKEN"]
os.environ["STATUSACCESSTOKEN"]=""

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# check buildtype
if args.buildType != "win64-dailyrelease":
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

# start wine server
subprocess.check_call(["wineserver", "-p"], stdout=sys.stdout, stderr=sys.stderr)

# args
ARGS=["--enableDistribution"]
RUNEXAMPLES=["--disableCompare", "--disableValidate", "--checkGUIs", "--exeExt", ".exe", "--filter", "'basic' in labels"]

# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')

os.environ['WINEPATH']=((os.environ['WINEPATH']+";") if 'WINEPATH' in os.environ else "")+"/mbsim-env/local/bin"

# run build
os.environ["STATUSACCESSTOKEN"]=statusAccessToken
ROTATE=3 if os.environ["MBSIMENVTAGNAME"]=="staging" else 20
ret=subprocess.call(
  ["/mbsim-build/build/buildScripts/build.py"]+ARGS+["--url", "https://"+os.environ['MBSIMENVSERVERNAME']+"/mbsim/"+args.buildType+"/report",
  "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--rotate", str(ROTATE), "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix",
  "--reportOutDir", "/mbsim-report/report", "--buildType", args.buildType,
  "--passToConfigure", "--enable-shared", "--disable-static", "--enable-python",
  "--build=x86_64-redhat-linux", "--host=x86_64-w64-mingw32",
  "--with-lapack-lib-prefix=/3rdparty/local/lib", "--with-hdf5-prefix=/3rdparty/local", 
  "--with-qmake=/usr/bin/x86_64-w64-mingw32-qmake-qt5",
  "--with-qwt-inc-prefix=/usr/x86_64-w64-mingw32/sys-root/mingw/include/qt5/qwt", "--with-qwt-lib-name=qwt-qt5",
  "--with-windres=x86_64-w64-mingw32-windres",
  "--with-mkoctfile=/3rdparty/local/bin/mkoctfile.exe",
  "--with-javajniosdir=/context/java_jni",
  "--with-pythonversion=3.7",
  "PYTHON_CFLAGS=-I/usr/x86_64-w64-mingw32/sys-root/mingw/include/python3.7m",
  "PYTHON_LIBS=-lpython3.7m",
  "PYTHON_BIN=python3.exe",
  "COIN_LIBS=-L/3rdparty/local/lib -lCoin",
  "COIN_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib -lSoQt",
  "SOQT_CFLAGS=-I/3rdparty/local/include",
  "--passToRunexamples"]+RUNEXAMPLES,
  stdout=sys.stdout, stderr=sys.stderr)
os.environ["STATUSACCESSTOKEN"]=""
if ret!=255:
  sys.exit(0)
if ret!=0:
  print("build.py failed.")
  sys.stdout.flush()

sys.exit(ret)
