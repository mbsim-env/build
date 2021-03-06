#!/usr/bin/python3

# imports
import argparse
import os
import subprocess
import sys
import django
sys.path.append("/context/mbsimenv")

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

# check environment
if "MBSIMENVSERVERNAME" not in os.environ or os.environ["MBSIMENVSERVERNAME"]=="":
  raise RuntimeError("Envvar MBSIMENVSERVERNAME is not defined.")

# check buildtype
if not args.buildType.startswith("win64-dailyrelease"):
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

# args
ARGS=["--enableDistribution"]
RUNEXAMPLES=["--disableCompare", "--disableValidate", "--checkGUIs", "--exeExt", ".exe", "--filter", "'basic' in labels"]

# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')

os.environ['WINEPATH']=((os.environ['WINEPATH']+";") if 'WINEPATH' in os.environ else "")+"/mbsim-env/local/bin"
os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"
os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -g -O2 -gdwarf-2 -DNDEBUG"

# run build
subprocess.check_call(["wineserver", "-p"], stdout=sys.stdout, stderr=sys.stderr) # start wine server
subprocess.check_call(["wine", "cmd", "/c", "echo", "dummy"], stdout=sys.stdout, stderr=sys.stderr) # dummy wine call; needed to avoid zombies when the first wine call is done from ninja
ret=subprocess.call(
  ["/context/mbsimenv/build.py"]+ARGS+[
  "--sourceDir", "/mbsim-env", "--binSuffix=-build", "--prefix", "/mbsim-env/local", "-j", str(args.jobs), "--buildSystemRun",
  "--fmatvecBranch", args.fmatvecBranch,
  "--hdf5serieBranch", args.hdf5serieBranch, "--openmbvBranch", args.openmbvBranch,
  "--mbsimBranch", args.mbsimBranch, "--enableCleanPrefix",
  "--buildType", args.buildType,
  "--passToConfigure", "--enable-shared", "--disable-static", "--enable-python",
  "--build=x86_64-redhat-linux", "--host=x86_64-w64-mingw32",
  "--with-lapack-lib-prefix=/3rdparty/local/lib", "--with-hdf5-prefix=/3rdparty/local", 
  "--with-qmake=/usr/bin/x86_64-w64-mingw32-qmake-qt5",
  "--with-qwt-inc-prefix=/usr/x86_64-w64-mingw32/sys-root/mingw/include/qt5/qwt", "--with-qwt-lib-name=qwt-qt5",
  "--with-windres=x86_64-w64-mingw32-windres",
  "--with-mkoctfile=/3rdparty/local/bin/mkoctfile.exe",
  "--with-javajniosdir=/context/java_jni",
  "--with-pythonversion=3.4",
  "--with-boost-filesystem-lib=boost_filesystem-x64",
  "--with-boost-system-lib=boost_system-x64",
  "--with-boost-regex-lib=boost_regex-x64",
  "--with-boost-date-time-lib=boost_date_time-x64",
  "--with-boost-timer-lib=boost_timer-x64",
  "--with-boost-chrono-lib=boost_chrono-x64",
  "PYTHON_CFLAGS=-I/3rdparty/local/python-win64/include -DMS_WIN64",
  "PYTHON_LIBS=-L/3rdparty/local/python-win64/libs -L/3rdparty/local/python-win64 -lpython34",
  "PYTHON_BIN=/3rdparty/local/python-win64/python.exe",
  "COIN_LIBS=-L/3rdparty/local/lib -lCoin",
  "COIN_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib -lSoQt",
  "SOQT_CFLAGS=-I/3rdparty/local/include",
  "--passToCMake", "-DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake",
  "-DBLAS_LIBRARIES=/3rdparty/local/lib/libblas.dll.a", "-DBLAS=1",
  "-DLAPACK_LIBRARIES=/3rdparty/local/lib/liblapack.dll.a", "-DLAPACK=1",
  "-DBOOST_ROOT=/usr/x86_64-w64-mingw32/sys-root/mingw",
  "-DBoost_ARCHITECTURE=-x64",
  "-DCMAKE_BUILD_TYPE=Release",
  "-DCMAKE_CXX_FLAGS_RELEASE=-g -O2 -gdwarf-2 -DNDEBUG",
  "-DCMAKE_C_FLAGS_RELEASE=-g -O2 -gdwarf-2 -DNDEBUG",
  "-DCMAKE_Fortran_FLAGS_RELEASE=-g -O2 -gdwarf-2 -DNDEBUG",
  "--passToRunexamples"]+RUNEXAMPLES,
  stdout=sys.stdout, stderr=sys.stderr)
subprocess.check_call(["wineserver", "-k"], stdout=sys.stdout, stderr=sys.stderr) # kill wine server
if ret!=255:
  sys.exit(0)
if ret!=0:
  print("build.py failed.")
  sys.stdout.flush()

sys.exit(ret)
