#!/bin/bash

SCRIPTDIR=$(readlink -m $(dirname $0))
MBSIMENVDIR=$(readlink -f "$SCRIPTDIR"/../../..)

# help
for A in "$@"; do
  if [ "$A" == "-h" -o "$A" == "--help" ]; then
    echo "This script runs the build.py script from mbsim-env."
    echo "It automatically passes all required arguments to build.py needed for the Docker win64 build of mbsim-env."
    echo "All arguments to this script are also passed (added) to build.py."
    echo "Moreover, when the mbsim-env git repositories are not already cloned, it does for you."
    echo "(Hence, just cloning https://github.com/mbsim-env/build.git and running this script will build mbsim-env using Docker)"
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

# split args to normal, --passToConfigure and --passToRunexamples args
ADDTOARGS=normal
NORMALARGS=()
CONFIGUREARGS=()
RUNEXAMPLEARGS=(--exeExt .exe)
while [ $# -ge 1 ]; do
  test "$1" == "--passToConfigure" && { ADDTOARGS=configure; shift; continue; }
  test "$1" == "--passToRunexamples" && { ADDTOARGS=runExamples; shift; continue; }
  if [ $ADDTOARGS == "normal" ]; then
    NORMALARGS+=("$1")
  elif [ $ADDTOARGS == "configure" ]; then
    CONFIGUREARGS+=("$1")
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

# run using mbsbd with all required args all all user args appended
"$SCRIPTDIR"/mbsbd "$MBSIMENVDIR"/build/buildScripts/build.py \
  --reportOutDir $MBSIMENVDIR/build_report-dockerwin64 \
  --sourceDir "$MBSIMENVDIR" \
  --binSuffix=-dockerwin64 \
  --prefix "$MBSIMENVDIR"/local-dockerwin64 \
  "${NORMALARGS[@]}" \
  --passToConfigure \
  --enable-shared --disable-static \
  --enable-python \
  --build=x86_64-redhat-linux \
  --host=x86_64-w64-mingw32 \
  --with-lapack-lib-prefix=/3rdparty/local/lib \
  --with-hdf5-prefix=/3rdparty/local \
  --with-qwt-inc-prefix=/3rdparty/local/include \
  --with-qwt-lib-prefix=/3rdparty/local/lib \
  --with-qwt-lib-name=qwt \
  --with-qmake=/usr/bin/x86_64-w64-mingw32-qmake-qt5 \
  COIN_CFLAGS=-I/3rdparty/local/include \
  COIN_LIBS="-L/3rdparty/local/lib -lCoin" \
  SOQT_CFLAGS=-I/3rdparty/local/include \
  SOQT_LIBS="-L/3rdparty/local/lib -lSoQt" \
  --with-windres=x86_64-w64-mingw32-windres \
  --with-mkoctfile=/3rdparty/local/bin/mkoctfile.exe \
  --with-javajniosdir=/context/java_jni \
  --with-pythonversion=3.4 \
  PYTHON_CFLAGS="-I/3rdparty/local/python-win64/include -DMS_WIN64" \
  PYTHON_LIBS="-L/3rdparty/local/python-win64 -lpython34" \
  PYTHON_BIN="/3rdparty/local/python-win64/python.exe" \
  "${CONFIGUREARGS[@]}" "${RUNEXAMPLEARGS[@]}"
