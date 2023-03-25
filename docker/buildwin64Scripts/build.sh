#!/bin/bash

set -e
set -o pipefail

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script runs the build.py script from mbsim-env in a mbsimenv/buildwin64 Docker container."
    echo "If you don't know Docker consider a mbsimenv/buildwin64 container as a virtual machine with mbsimenv installed."
    echo "It automatically passes all required arguments to build.py needed for the Docker build of mbsim-env."
    echo "All arguments to this script are passed (added) to build.py."
    echo ""
    echo "When the mbsim-env git repositories are not already cloned, it does for you the first time."
    echo "Hence, just cloning https://github.com/mbsim-env/build.git and running this script will build mbsim-env using Docker."
    echo ""
    echo "Their is one special argument which build.py does not have: --bt [Debug|Release]"
    echo "It passes debug or release compile/link flags to build.py. If not given Debug is used."
    echo ""
    break
  fi
done

# clone mbsim-env if not already done
if [ ! -d $MBSIMENVDIR/fmatvec ]; then
  (cd $MBSIMENVDIR; git clone https://github.com/mbsim-env/fmatvec.git)
fi
if [ ! -d $MBSIMENVDIR/hdf5serie ]; then
  (cd $MBSIMENVDIR; git clone https://github.com/mbsim-env/hdf5serie)
fi
if [ ! -d $MBSIMENVDIR/openmbv ]; then
  (cd $MBSIMENVDIR; git clone https://github.com/mbsim-env/openmbv)
fi
if [ ! -d $MBSIMENVDIR/mbsim ]; then
  (cd $MBSIMENVDIR; git clone https://github.com/mbsim-env/mbsim)
fi

# split args to normal, --passToConfigure, --passToCMake and --passToRunexamples args
BT=Debug
ADDTOARGS=normal
NORMALARGS=()
CONFIGUREARGS=()
CMAKEARGS=()
RUNEXAMPLEARGS=(--exeExt .exe)
while [ $# -ge 1 ]; do
  test "$1" == "--bt" && { BT=$2; shift; shift; continue; }
  test "$1" == "--passToConfigure" && { ADDTOARGS=configure; shift; continue; }
  test "$1" == "--passToCMake" && { ADDTOARGS=cmake; shift; continue; }
  test "$1" == "--passToRunexamples" && { ADDTOARGS=runExamples; shift; continue; }
  if [ $ADDTOARGS == "normal" ]; then
    NORMALARGS+=("$1")
  elif [ $ADDTOARGS == "configure" ]; then
    CONFIGUREARGS+=("$1")
  elif [ $ADDTOARGS == "cmake" ]; then
    CMAKEARGS+=("$1")
  elif [ $ADDTOARGS == "runExamples" ]; then
    RUNEXAMPLEARGS+=("$1")
  fi
  shift
done
if [ ${#RUNEXAMPLEARGS[*]} -gt 0 ]; then
  RUNEXAMPLEARGS=(--passToRunexamples "${RUNEXAMPLEARGS[@]}")
fi

# config home
mkdir -p $MBSIMENVDIR/.home

# debug or release build
# set envvar for configure build and pass to --passToCMake for cmake builds, see below
if [ $BT == "Debug" ]; then
  export CXXFLAGS="-g -O0 -gdwarf-2"
  export CFLAGS="-g -O0 -gdwarf-2"
  export FFLAGS="-g -O0 -gdwarf-2"
elif [ $BT == "Release" ]; then
  export CXXFLAGS="-g -O2 -gdwarf-2 -DNDEBUG"
  export CFLAGS="-g -O2 -gdwarf-2 -DNDEBUG"
  export FFLAGS="-g -O2 -gdwarf-2 -DNDEBUG"
else
  echo "Unknown build type: --bt $BT"
  break
fi

MBSIMENVTAGNAME=${MBSIMENVTAGNAME:-latest}
docker run -d --init --entrypoint= --rm \
  --user $(id -u):$(id -g) \
  -v "$MBSIMENVDIR":/mbsim-env \
  --net=host \
  mbsimenv/buildwin64:$MBSIMENVTAGNAME \
  /mbsim-env/build/docker/buildImage/runlocalserver.py > /dev/null
# wait until localserver.json exists to avoid a race-condition between containers
while [ ! -e $MBSIMENVDIR/build/django/mbsimenv/localserver.json ]; do sleep 0.1; done

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd "$MBSIMENVDIR"/build/django/mbsimenv/build.py \
  --buildType win64-docker \
  --executor '<span class="MBSIMENV_EXECUTOR_LOCALDOCKER">Local Docker</span>' \
  --disableUpdate \
  --sourceDir "$MBSIMENVDIR" \
  --binSuffix=-dockerwin64 \
  --prefix "$MBSIMENVDIR"/local-dockerwin64 \
  "${NORMALARGS[@]}" \
  --passToConfigure \
  --enable-shared --disable-static \
  --enable-python \
  --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 \
  --with-hdf5-prefix=/3rdparty/local \
  --with-qmake=/usr/bin/x86_64-w64-mingw32-qmake-qt5 \
  --with-qwt-inc-prefix=/usr/x86_64-w64-mingw32/sys-root/mingw/include/qt5/qwt --with-qwt-lib-name=qwt-qt5 \
  --with-windres=x86_64-w64-mingw32-windres \
  --with-mkoctfile=/3rdparty/local/bin/mkoctfile.exe \
  --with-javajniosdir=/context/java_jni \
  --with-pythonversion=3.4 \
  --with-boost-filesystem-lib=boost_filesystem-mt-x64 \
  --with-boost-thread-lib=boost_thread-mt-x64 \
  --with-boost-program-options-lib=boost_program_options-mt-x64 \
  --with-boost-system-lib=boost_system-mt-x64 \
  --with-boost-regex-lib=boost_regex-mt-x64 \
  --with-boost-date-time-lib=boost_date_time-mt-x64 \
  --with-boost-timer-lib=boost_timer-mt-x64 \
  --with-boost-chrono-lib=boost_chrono-mt-x64 \
  CXXFLAGS="$CXXFLAGS" \
  CFLAGS="$CFLAGS" \
  FFLAGS="$FFLAGS" \
  PYTHON_CFLAGS="-I/3rdparty/local/python-win64/include -DMS_WIN64" \
  PYTHON_LIBS="-L/3rdparty/local/python-win64/libs -L/3rdparty/local/python-win64 -lpython34" \
  PYTHON_BIN="/3rdparty/local/python-win64/python.exe" \
  COIN_LIBS="-L/3rdparty/local/lib -lCoin" \
  COIN_CFLAGS=-I/3rdparty/local/include \
  SOQT_LIBS="-L/3rdparty/local/lib -lSoQt" \
  SOQT_CFLAGS=-I/3rdparty/local/include \
  "${CONFIGUREARGS[@]}" \
  --passToCMake \
  -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake \
  -DBLAS_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a -DBLAS=1 \
  -DLAPACK_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a -DLAPACK=1 \
  -DARPACK_INCLUDE_DIRS=/3rdparty/local/include/arpack -DARPACK_LIBRARIES=/3rdparty/local/lib/libarpack.dll.a \
  -DSPOOLES_INCLUDE_DIRS=/3rdparty/local/include/spooles -DSPOOLES_LIBRARIES=/3rdparty/local/lib/spooles.a \
  -DBOOST_ROOT=/usr/x86_64-w64-mingw32/sys-root/mingw \
  -DBoost_ARCHITECTURE=-x64 \
  -DCMAKE_BUILD_TYPE=$BT \
  -DCMAKE_CXX_FLAGS_${BT^^}="$CXXFLAGS" \
  -DCMAKE_C_FLAGS_${BT^^}="$CFLAGS" \
  -DCMAKE_Fortran_FLAGS_${BT^^}="$FFLAGS" \
  "${CMAKEARGS[@]}" \
  "${RUNEXAMPLEARGS[@]}"
