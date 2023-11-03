#!/bin/bash

BASEDIR=$(pwd)

export MBSIM_SWIG=1
export PATH=$BASEDIR/local-msys2ucrt64/bin:$PATH
export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:$BASEDIR/local-msys2ucrt64/lib/pkgconfig

if (return 0 2>/dev/null); then
  echo "Script is sources! (just setting envvars)"
  return
fi

export CC="ccache gcc"
export CXX="ccache g++"
export CXXFLAGS="-O0 -g"
export CFLAGS="-O0 -g"
export FFLAGS="-O0 -g"
export FCFLAGS="-O0 -g"

CMAKEFLAGS=()
CMAKEFLAGS+=("-DCMAKE_BUILD_TYPE=Release")
CMAKEFLAGS+=("-DCMAKE_CXX_FLAGS_RELEASE=$CXXFLAGS")
CMAKEFLAGS+=("-DCMAKE_C_FLAGS_RELEASE=$CFLAGS")
CMAKEFLAGS+=("-DCMAKE_Fortran_FLAGS_RELEASE=$FFLAGS")
export LDFLAGS_LIBTOOL=""

CONFIGUREFLAGS=()

ARGS=()
ARGS+=("--disableUpdate")
#ARGS+=("--disableConfigure")
ARGS+=("--disableMakeClean")
#ARGS+=("--disableMake")
#ARGS+=("--disableMakeCheck")
#ARGS+=("--disableDoxygen")
#ARGS+=("--disableXMLDoc")
#ARGS+=("--disableRunExamples")
#ARGS+=("--enableDistribution")

ARGSRUNEXAMPLES=()
ARGSRUNEXAMPLES+=("xmlflat/hierachical_modelling")
ARGSRUNEXAMPLES+=("xml/hierachical_modelling")

python3 $(dirname $0)/../django/mbsimenv/build.py \
  "${ARGS[@]}" \
  --sourceDir $BASEDIR --binSuffix=-msys2ucrt64 --prefix $BASEDIR/local-msys2ucrt64 -j 2 --buildType msys2ucrt64 \
  --passToConfigure \
  "${CONFIGUREFLAGS[@]}" \
  --disable-static \
  --with-boost-system-lib=boost_system-mt \
  --with-boost-filesystem-lib=boost_filesystem-mt \
  --with-boost-chrono-lib=boost_chrono-mt \
  --with-boost-thread-lib=boost_thread-mt \
  --with-boost-program-options-lib=boost_program_options-mt \
  --with-boost-regex-lib=boost_regex-mt \
  --with-boost-timer-lib=boost_timer-mt \
  --with-boost-date-time-lib=boost_date_time-mt \
  --with-qwt-inc-prefix=/ucrt64/include/qwt-qt5 \
  --with-qwt-lib-name=qwt-qt5 \
  --passToCMake \
  -DSPOOLES_INCLUDE_DIRS=/ucrt64/include/spooles \
  -DSPOOLES_LIBRARIES=/ucrt64/lib/libspooles.a \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=1 \
  "${CMAKEFLAGS[@]}" \
  --passToRunexamples \
  --checkGUIs --exeExt .exe \
  "${ARGSRUNEXAMPLES[@]}"
