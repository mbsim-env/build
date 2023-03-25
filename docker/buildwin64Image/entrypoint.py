#!/usr/bin/python3

# imports
import argparse
import os
import subprocess
import sys
import psutil
import django
sys.path.append("/context/mbsimenv")
import service

# arguments
argparser=argparse.ArgumentParser(
  formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  description="Entrypoint for container mbsimenv/buildwin64.")
  
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

os.environ['WINEPATH']=((os.environ['WINEPATH']+";") if 'WINEPATH' in os.environ else "")+"/mbsim-env/local/bin"

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
  os.environ['CXXFLAGS']=os.environ.get('CXXFLAGS', '')+" -O0 -g -gdwarf-2"
  os.environ['CFLAGS']=os.environ.get('CFLAGS', '')+" -O0 -g -gdwarf-2"
  os.environ['FFLAGS']=os.environ.get('FFLAGS', '')+" -O0 -g -gdwarf-2"
  ARGS=["--disableDoxygen", "--disableXMLDoc"]
  RUNEXAMPLESARGS=["--disableCompare", "--disableValidate", "--checkGUIs", "--disableMakeClean", "--exeExt", ".exe", "--filter", "'basic' in labels"]

  # get current/last image ID
  curImageID=os.environ.get("MBSIMENVIMAGEID", None)
  if curImageID is not None:
    info=service.models.Info.objects.all().first()
    lastImageID=info.buildwin64ImageID if info is not None else ""
    # configure needed?
    if lastImageID==curImageID and not args.enforceConfigure:
      ARGS.append("--disableConfigure")
    # save build image id
    info.buildwin64ImageID=curImageID
    info.save()
else:
  raise RuntimeError("Unknown build type "+args.buildType)
  
# pass arguments to build.py
if args.forceBuild:
  ARGS.append('--forceBuild')

subprocess.call(["ccache", "-M", str(args.ccacheSize)+"G"])
print("Zeroing ccache statistics.")
subprocess.call(["ccache", "-z"])

if args.buildRunID is not None:
  ARGS.append("--buildRunID")
  ARGS.append(str(args.buildRunID))

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
  "--executor", args.executor,
  "--passToConfigure", "--enable-shared", "--disable-static", "--enable-python",
  "--build=x86_64-redhat-linux", "--host=x86_64-w64-mingw32",
  "--with-hdf5-prefix=/3rdparty/local", 
  "--with-qmake=/usr/bin/x86_64-w64-mingw32-qmake-qt5",
  "--with-qwt-inc-prefix=/usr/x86_64-w64-mingw32/sys-root/mingw/include/qt5/qwt", "--with-qwt-lib-name=qwt-qt5",
  "--with-windres=x86_64-w64-mingw32-windres",
  "--with-mkoctfile=/3rdparty/local/bin/mkoctfile.exe",
  "--with-javajniosdir=/context/java_jni",
  "--with-pythonversion=3.4",
  "--with-boost-filesystem-lib=boost_filesystem-mt-x64",
  "--with-boost-thread-lib=boost_thread-mt-x64",
  "--with-boost-program-options-lib=boost_program_options-mt-x64",
  "--with-boost-system-lib=boost_system-mt-x64",
  "--with-boost-regex-lib=boost_regex-mt-x64",
  "--with-boost-date-time-lib=boost_date_time-mt-x64",
  "--with-boost-timer-lib=boost_timer-mt-x64",
  "--with-boost-chrono-lib=boost_chrono-mt-x64",
  "PYTHON_CFLAGS=-I/3rdparty/local/python-win64/include -DMS_WIN64",
  "PYTHON_LIBS=-L/3rdparty/local/python-win64/libs -L/3rdparty/local/python-win64 -lpython34",
  "PYTHON_BIN=/3rdparty/local/python-win64/python.exe",
  "COIN_LIBS=-L/3rdparty/local/lib -lCoin",
  "COIN_CFLAGS=-I/3rdparty/local/include",
  "SOQT_LIBS=-L/3rdparty/local/lib -lSoQt",
  "SOQT_CFLAGS=-I/3rdparty/local/include",
  "--passToCMake", "-DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake",
  "-DBLAS_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a", "-DBLAS=1",
  "-DLAPACK_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a", "-DLAPACK=1",
  "-DBOOST_ROOT=/usr/x86_64-w64-mingw32/sys-root/mingw",
  "-DBoost_ARCHITECTURE=-x64",
  "-DARPACK_INCLUDE_DIRS=/3rdparty/local/include/arpack", "-DARPACK_LIBRARIES=/3rdparty/local/lib/libarpack.dll.a",
  "-DSPOOLES_INCLUDE_DIRS=/3rdparty/local/include/spooles", "-DSPOOLES_LIBRARIES=/3rdparty/local/lib/spooles.a",
  "-DCMAKE_BUILD_TYPE="+BUILDTYPE,
  "-DCMAKE_CXX_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CXXFLAGS"],
  "-DCMAKE_C_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["CFLAGS"],
  "-DCMAKE_Fortran_FLAGS_"+BUILDTYPE.upper()+"="+os.environ["FFLAGS"],
  "--passToRunexamples"]+RUNEXAMPLESARGS,
  stdout=sys.stdout, stderr=sys.stderr)
subprocess.check_call(["wineserver", "-k"], stdout=sys.stdout, stderr=sys.stderr) # kill wine server

print("Dump ccache statistics:")
subprocess.call(["ccache", "-s"])
sys.stdout.flush()

if ret!=0:
  print("build.py failed.")
  sys.stdout.flush()

sys.exit(ret)
