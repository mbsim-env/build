FROM centos:7

RUN yum -y install epel-release && \
  yum -y install git ccache
RUN yum -y install python-requests
RUN yum -y install libtool automake autoconf
RUN yum -y install make mingw64-gcc mingw64-gcc-c++ mingw64-gcc-gfortran
RUN yum -y install h5py numpy
RUN yum -y install mingw64-boost
RUN yum -y install cmake3
RUN yum -y install wget
RUN yum -y install wine
RUN yum -y install doxygen

# copy build repo
COPY docker/autobuildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake
COPY docker/autobuildwin64Image/hdf5.patch /context/hdf5.patch
COPY buildScripts /mbsim-build/build/buildScripts

# 3rd party

# configure path and envvar for the 3rd party tools
RUN mkdir /3rdparty

# get tools to build
WORKDIR /3rdparty

# lapack
ARG LAPACKVERSION=3.4.2
RUN set -o pipefail && \
  wget -q -O - http://www.netlib.org/lapack/lapack-$LAPACKVERSION.tgz | tar -xz
RUN mkdir /3rdparty/lapack-build

# hdf5
ARG HDF5VERSION=1_8_12
RUN git clone --depth 1 -b hdf5-$HDF5VERSION https://bitbucket.hdfgroup.org/scm/hdffv/hdf5.git
WORKDIR /3rdparty/hdf5
RUN git checkout -b test
RUN git apply /context/hdf5.patch
WORKDIR /3rdparty
RUN mkdir /3rdparty/hdf5-build

# qwt
ARG QWTVERSION=6.1.3
RUN set -o pipefail && \
  wget -q -O - https://netcologne.dl.sourceforge.net/project/qwt/qwt/6.1.3/qwt-6.1.3.tar.bz2 | tar -xj
RUN mkdir /3rdparty/qwt-build
RUN sed -ire "s|^ *QWT_INSTALL_PREFIX *=.*$|QWT_INSTALL_PREFIX = /3rdparty/local|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *QWT_CONFIG *+= *QwtDesigner *$|#|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri

# python
ARG PYTHONVERSION=2.7.13
RUN wget https://www.python.org/ftp/python/2.7.13/python-$PYTHONVERSION.amd64.msi

# swig
RUN yum install -y patch
ARG SWIGVERSION=3.0.7
RUN set -o pipefail && \
  wget -q -O - https://kent.dl.sourceforge.net/project/swig/swig/swig-$SWIGVERSION/swig-$SWIGVERSION.tar.gz | tar -xz
COPY docker/autobuildwin64Image/swig.patch /context/swig.patch
RUN patch -d /3rdparty/swig-$SWIGVERSION -p0 < /context/swig.patch
RUN mkdir /3rdparty/swig-build

# numpy
ARG NUMPYVERSION=1.12.0b1
RUN wget http://qpypi.qpython.org/repository/2314/numpy-$NUMPYVERSION-cp27-none-win_amd64.whl
RUN mkdir /3rdparty/numpy-build
 
# casadi
ARG CASADIBRANCH=470b5b3f0cc4044e3cb0eb20dfb2a85e247c62a6
RUN git clone https://github.com/friedrichatgc/casadi.git
WORKDIR /3rdparty/casadi
RUN git checkout $CASADIBRANCH
WORKDIR /3rdparty
RUN mkdir /3rdparty/casadi-build

# octave
ARG OCTAVEVERSION=3.8.2
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/octave-build

# xerces-c
ARG XERCESCVERSION=3.1.2
RUN set -o pipefail && \
  wget -q -O - https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-$XERCESCVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/xercesc-build

ARG JOBS=4

# compile/install

# lapack
WORKDIR /3rdparty/lapack-build
RUN cmake3 ../lapack-$LAPACKVERSION -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local
RUN make -j $JOBS
RUN make install

# hdf5
WORKDIR /3rdparty/hdf5-build
RUN cmake3 ../hdf5 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DMSVC=TRUE -DHDF5_BUILD_CPP_LIB=ON -DBUILD_SHARED_LIBS=1
RUN make -j $JOBS
RUN make install

RUN yum -y install mingw64-qt5-qtbase
RUN yum -y install mingw64-qt5-qmake
RUN yum -y install mingw64-qt5-qtsvg

# qwt
WORKDIR /3rdparty/qwt-build
# fix qwt
RUN sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri
RUN mingw64-qmake-qt5 ../qwt-$QWTVERSION
# the first make fails but the second not???
RUN make -j $JOBS || make -j $JOBS
RUN make install

# python
WORKDIR /3rdparty
RUN wine msiexec -i python-$PYTHONVERSION.amd64.msi TARGETDIR="$(winepath -w /3rdparty/local/python-win64)"

RUN yum install -y pcre-devel
RUN yum install -y gcc-c++

# swig3 (centos7 only provides swig2)
WORKDIR /3rdparty/swig-build
RUN ../swig-$SWIGVERSION/configure --disable-static --enable-shared CXXFLAGS="-O2" CFLAGS="-O2" --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

RUN yum install -y unzip

# numpy
WORKDIR /3rdparty/numpy-build
RUN unzip ../numpy-$NUMPYVERSION-cp27-none-win_amd64.whl
RUN cp -a numpy /3rdparty/local/python-win64/Lib/site-packages/.

# casadi
WORKDIR /3rdparty/casadi-build
RUN cmake3 -DENABLE_STATIC=OFF -DENABLE_SHARED=ON -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DWITH_DEPRECATED_FEATURES=OFF -DCMAKE_BUILD_TYPE=release -DWITH_PYTHON=ON -DPYTHON_EXECUTABLE=/3rdparty/local/python-win64/python.exe -DPYTHON_INCLUDE_DIR=/3rdparty/local/python-win64/include -DPYTHON_LIBRARY=/3rdparty/local/python-win64/libs/libpython27.a -DPYTHON_PREFIX=/3rdparty/local/python-win64/Lib/site-packages -DSWIG_EXECUTABLE=/3rdparty/local/bin/swig -DSWIG_DIR=/3rdparty/local -DNUMPY_PATH=/3rdparty/local/python-win64/Lib/site-packages/numpy -DNUMPY_INCLUDED_DIRS=/3rdparty/local/python-win64/Lib/site-packages/numpy/core/include/numpy -DCMAKE_C_FLAGS="-DMS_WIN64 -g -O2" -DCMAKE_CXX_FLAGS="-DMS_WIN64 -g -O2" ../casadi -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake
#
RUN make -j $JOBS
RUN make install

RUN yum install -y xalan-c
RUN yum install -y which

# octave
WORKDIR /3rdparty/octave-build
# fix mingw
COPY docker/autobuildwin64Image/mingw64.patch /context/mingw64.patch
RUN patch -d / -p0 < /context/mingw64.patch
# fix mingw end
# fix octave
COPY docker/autobuildwin64Image/octave.patch /context/octave.patch
RUN patch -d /3rdparty/octave-$OCTAVEVERSION -p0 < /context/octave.patch
# fix octave end
RUN ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --with-blas="-L/3rdparty/local/lib -lblas" --with-lapack="-L/3rdparty/local/lib -llapack" --disable-readline
RUN make -j $JOBS
RUN make install

RUN yum install -y dos2unix

# xerces-c
# fix octave
COPY docker/autobuildwin64Image/xercesc.patch /context/xercesc.patch
RUN patch -d /3rdparty/xerces-c-$XERCESCVERSION -p0 < /context/xercesc.patch
# fix octave end
WORKDIR /3rdparty/xercesc-build
RUN ../xerces-c-$XERCESCVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

RUN yum install -y file
RUN yum -y install mingw64-qt5-qtwebkit
RUN yum install -y mercurial

# coin
ARG COINBRANCH=3d7321d07d57
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/coin -r $COINBRANCH
COPY docker/autobuildwin64Image/coin.patch /context/coin.patch
WORKDIR /3rdparty/coin
RUN hg import --no-commit /context/coin.patch
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake3 -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake ../coin
RUN make -j $JOBS
RUN make install

# soqt
ARG SOQTBRANCH=945ec22f6219
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt -r $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake3 -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DQt5_DIR=/usr/x86_64-w64-mingw32/sys-root/mingw/lib/cmake/Qt5 ../soqt
RUN make -j $JOBS
RUN make install

# move to hdf5
RUN ln -s /3rdparty/local/lib/hdf5.lib /3rdparty/local/lib/libhdf5.lib & \
    ln -s /3rdparty/local/lib/hdf5_cpp.lib /3rdparty/local/lib/libhdf5_cpp.lib

# libarchive
ARG LIBARCHIVEVERION=3.1.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://libarchive.org/downloads/libarchive-$LIBARCHIVEVERION.tar.gz | tar -xz
RUN mkdir /3rdparty/libarchive-build
WORKDIR /3rdparty/libarchive-build
RUN ../libarchive-$LIBARCHIVEVERION/configure  --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --without-xml2 --without-expat --without-openssl --without-nettle --without-lzo2 --without-lzma --without-libiconv-prefix --without-iconv --without-lzmadec --without-bz2lib
RUN make -j $JOBS
RUN make install

RUN yum install -y tigervnc-server





COPY docker/autobuildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/autobuildImage/distribute.py /context/distribute.py
COPY docker/autobuildwin64Image/entrypoint.py /context/entrypoint.py








# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/autobuildwin64" \
  org.label-schema.description="Automatic build (win64) for the MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/autobuildwin64Image" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state

# ccache
# enable swig interface to mbsim
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    WINEPATH="/usr/x86_64-w64-mingw32/sys-root/mingw/bin;/3rdparty/local/bin;/3rdparty/local/lib;/3rdparty/local/python-win64;/mbsim-env/local/bin" \
    MOC=/usr/x86_64-w64-mingw32/bin/qt5/moc \
    UIC=/usr/x86_64-w64-mingw32/bin/qt5/uic \
    RCC=/usr/x86_64-w64-mingw32/bin/qt5/rcc

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]

#mfmf ccache in PATH
#mfmf java is missing in all docker images
