#!/bin/bash

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script runs the build.py script from mbsim-env in a mbsimenv/build Docker container."
    echo "If you don't know Docker consider a mbsimenv/build container as a virtual machine with mbsimenv installed."
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
RUNEXAMPLEARGS=()
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

# config ccache
CCACHE_DIR=$MBSIMENVDIR/.ccache ccache -M 10G

# config home
mkdir -p $MBSIMENVDIR/.home

# debug or release build
# set envvar for configure build and pass to --passToCMake for cmake builds, see below
if [ $BT == "Debug" ]; then
  export CXXFLAGS="-O0 -g"
  export CFLAGS="-O0 -g"
  export FFLAGS="-O0 -g"
elif [ $BT == "Release" ]; then
  export CXXFLAGS="-g -O2 -DNDEBUG"
  export CFLAGS="-g -O2 -DNDEBUG"
  export FFLAGS="-g -O2 -DNDEBUG"
else
  echo "Unknown build type: --bt $BT"
  break
fi

MBSIMENVTAGNAME=${MBSIMENVTAGNAME:-latest}
docker run -d --init --entrypoint= --rm \
  --user $(id -u):$(id -g) \
  -v "$MBSIMENVDIR":/mbsim-env \
  --net=host \
  mbsimenv/build:$MBSIMENVTAGNAME \
  /mbsim-env/build/docker/buildImage/runlocalserver.py > /dev/null

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd "$MBSIMENVDIR"/build/django/mbsimenv/build.py \
  --buildType localDocker \
  --sourceDir "$MBSIMENVDIR" \
  --binSuffix=-docker \
  --prefix "$MBSIMENVDIR"/local-docker \
  "${NORMALARGS[@]}" \
  --passToConfigure \
  --disable-static \
  --enable-python \
  --with-qwt-inc-prefix=/3rdparty/local/include --with-qwt-lib-prefix=/3rdparty/local/lib --with-qwt-lib-name=qwt \
  --with-boost-inc=/usr/include/boost169 \
  --with-hdf5-prefix=/3rdparty/local \
  --with-mkoctfile=/3rdparty/local/bin/mkoctfile \
  --with-qmake=qmake-qt5 \
  CXXFLAGS="$CXXFLAGS" \
  CFLAGS="$CFLAGS" \
  FFLAGS="$FFLAGS" \
  COIN_CFLAGS=-I/3rdparty/local/include COIN_LIBS=-"L/3rdparty/local/lib64 -lCoin" \
  SOQT_CFLAGS=-I/3rdparty/local/include SOQT_LIBS="-L/3rdparty/local/lib64 -lSoQt" \
  "${CONFIGUREARGS[@]}" \
  --passToCMake \
  -DBOOST_INCLUDEDIR=/usr/include/boost169 -DBOOST_LIBRARYDIR=/usr/lib64/boost169 \
  -DCMAKE_BUILD_TYPE=$BT \
  -DCMAKE_CXX_FLAGS_${BT^^}="$CXXFLAGS" \
  -DCMAKE_C_FLAGS_${BT^^}="$CFLAGS" \
  -DCMAKE_Fortran_FLAGS_${BT^^}="$FFLAGS" \
  "${CMAKEARGS[@]}" \
  "${RUNEXAMPLEARGS[@]}"
