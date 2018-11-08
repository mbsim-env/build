FROM centos:7 AS centosBaseImage

RUN yum -y install epel-release && yum -y install \
  git \
  ccache \
  patch \
  make \
  mingw64-gcc \
  mingw64-gcc-c++ \
  mingw64-gcc-gfortran \
  wine \
  mingw64-qt5-qtsvg \
  python-requests \
  libtool automake autoconf \
  h5py \
  numpy \
  mingw64-boost \
  doxygen \
  tigervnc-server \
  xalan-c \
  which \
  dos2unix \
  file \
  mingw64-qt5-qtwebkit \
  java-1.8.0-openjdk-devel \
  && yum clean all

# fix mingw
COPY docker/autobuildwin64Image/mingw64.patch /context/mingw64.patch
RUN patch -d / -p0 < /context/mingw64.patch


##################################################################################


FROM centosBaseImage AS thirdpartyBuildImage

ARG JOBS=4

RUN yum -y install \
  wget \
  cmake3 \
  mingw64-qt5-qmake \
  gcc-c++ \
  pcre-devel \
  unzip \
  mercurial \
  && yum clean all

# 3rd party

RUN mkdir /3rdparty
COPY docker/autobuildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake

# lapack
ARG LAPACKVERSION=3.4.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - http://www.netlib.org/lapack/lapack-$LAPACKVERSION.tgz | tar -xz
RUN mkdir /3rdparty/lapack-build
WORKDIR /3rdparty/lapack-build
RUN cmake3 ../lapack-$LAPACKVERSION -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local
RUN make -j $JOBS
RUN make install

# hdf5
ARG HDF5VERSION=1_8_12
WORKDIR /3rdparty
RUN git clone --depth 1 -b hdf5-$HDF5VERSION https://bitbucket.hdfgroup.org/scm/hdffv/hdf5.git
WORKDIR /3rdparty/hdf5
RUN git checkout -b test
COPY docker/autobuildwin64Image/hdf5.patch /context/hdf5.patch
RUN git apply /context/hdf5.patch
RUN mkdir /3rdparty/hdf5-build
WORKDIR /3rdparty/hdf5-build
RUN cmake3 ../hdf5 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DMSVC=TRUE -DHDF5_BUILD_CPP_LIB=ON -DBUILD_SHARED_LIBS=1
RUN make -j $JOBS
RUN make install
RUN ln -s /3rdparty/local/lib/hdf5.lib /3rdparty/local/lib/libhdf5.lib & \
    ln -s /3rdparty/local/lib/hdf5_cpp.lib /3rdparty/local/lib/libhdf5_cpp.lib

# qwt
ARG QWTVERSION=6.1.3
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://netcologne.dl.sourceforge.net/project/qwt/qwt/6.1.3/qwt-6.1.3.tar.bz2 | tar -xj
RUN mkdir /3rdparty/qwt-build
WORKDIR /3rdparty/qwt-build
RUN sed -ire "s|^ *QWT_INSTALL_PREFIX *=.*$|QWT_INSTALL_PREFIX = /3rdparty/local|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *QWT_CONFIG *+= *QwtDesigner *$|#|" /3rdparty/qwt-$QWTVERSION/qwtconfig.pri && \
  sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri
RUN sed -ire "s|^ *CONFIG *+= *debug_and_release *$|CONFIG += release|" /3rdparty/qwt-$QWTVERSION/qwtbuild.pri
RUN mingw64-qmake-qt5 ../qwt-$QWTVERSION
# the first make fails but the second not???
RUN make -j $JOBS || make -j $JOBS
RUN make install

# python
ARG PYTHONVERSION=2.7.13
WORKDIR /3rdparty
RUN wget https://www.python.org/ftp/python/2.7.13/python-$PYTHONVERSION.amd64.msi
RUN wine msiexec -i python-$PYTHONVERSION.amd64.msi TARGETDIR="$(winepath -w /3rdparty/local/python-win64)"

# swig3 (centos7 only provides swig2)
ARG SWIGVERSION=3.0.7
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://kent.dl.sourceforge.net/project/swig/swig/swig-$SWIGVERSION/swig-$SWIGVERSION.tar.gz | tar -xz
COPY docker/autobuildwin64Image/swig.patch /context/swig.patch
RUN patch -d /3rdparty/swig-$SWIGVERSION -p0 < /context/swig.patch
RUN mkdir /3rdparty/swig-build
WORKDIR /3rdparty/swig-build
RUN ../swig-$SWIGVERSION/configure --disable-static --enable-shared CXXFLAGS="-O2" CFLAGS="-O2" --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

# numpy
ARG NUMPYVERSION=1.12.0b1
WORKDIR /3rdparty
RUN wget http://qpypi.qpython.org/repository/2314/numpy-$NUMPYVERSION-cp27-none-win_amd64.whl
RUN mkdir /3rdparty/numpy-build
WORKDIR /3rdparty/numpy-build
RUN unzip ../numpy-$NUMPYVERSION-cp27-none-win_amd64.whl
RUN cp -a numpy /3rdparty/local/python-win64/Lib/site-packages/.

# casadi
ARG CASADIBRANCH=470b5b3f0cc4044e3cb0eb20dfb2a85e247c62a6
WORKDIR /3rdparty
RUN git clone https://github.com/friedrichatgc/casadi.git
WORKDIR /3rdparty/casadi
RUN git checkout $CASADIBRANCH
WORKDIR /3rdparty
RUN mkdir /3rdparty/casadi-build
WORKDIR /3rdparty/casadi-build
RUN cmake3 -DENABLE_STATIC=OFF -DENABLE_SHARED=ON -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DWITH_DEPRECATED_FEATURES=OFF -DCMAKE_BUILD_TYPE=release -DWITH_PYTHON=ON -DPYTHON_EXECUTABLE=/3rdparty/local/python-win64/python.exe -DPYTHON_INCLUDE_DIR=/3rdparty/local/python-win64/include -DPYTHON_LIBRARY=/3rdparty/local/python-win64/libs/libpython27.a -DPYTHON_PREFIX=/3rdparty/local/python-win64/Lib/site-packages -DSWIG_EXECUTABLE=/3rdparty/local/bin/swig -DSWIG_DIR=/3rdparty/local -DNUMPY_PATH=/3rdparty/local/python-win64/Lib/site-packages/numpy -DNUMPY_INCLUDED_DIRS=/3rdparty/local/python-win64/Lib/site-packages/numpy/core/include/numpy -DCMAKE_C_FLAGS="-DMS_WIN64 -g -O2" -DCMAKE_CXX_FLAGS="-DMS_WIN64 -g -O2" ../casadi -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake
RUN make -j $JOBS
RUN make install

# octave
ARG OCTAVEVERSION=3.8.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/octave-build
WORKDIR /3rdparty/octave-build
COPY docker/autobuildwin64Image/octave.patch /context/octave.patch
RUN patch -d /3rdparty/octave-$OCTAVEVERSION -p0 < /context/octave.patch
RUN ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --with-blas="-L/3rdparty/local/lib -lblas" --with-lapack="-L/3rdparty/local/lib -llapack" --disable-readline
RUN make -j $JOBS
RUN make install

# xerces-c
ARG XERCESCVERSION=3.1.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://archive.apache.org/dist/xerces/c/3/sources/xerces-c-$XERCESCVERSION.tar.bz2 | tar -xj
RUN mkdir /3rdparty/xercesc-build
COPY docker/autobuildwin64Image/xercesc.patch /context/xercesc.patch
RUN patch -d /3rdparty/xerces-c-$XERCESCVERSION -p0 < /context/xercesc.patch
WORKDIR /3rdparty/xercesc-build
RUN ../xerces-c-$XERCESCVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

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


##################################################################################


FROM centosBaseImage

COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local

# ccache
# enable swig interface to mbsim
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    PATH=/usr/lib64/ccache:$PATH \
    WINEPATH="/usr/x86_64-w64-mingw32/sys-root/mingw/bin;/3rdparty/local/bin;/3rdparty/local/lib;/3rdparty/local/python-win64;/mbsim-env/local/bin" \
    MOC=/usr/x86_64-w64-mingw32/bin/qt5/moc \
    UIC=/usr/x86_64-w64-mingw32/bin/qt5/uic \
    RCC=/usr/x86_64-w64-mingw32/bin/qt5/rcc

# copy
COPY buildScripts /mbsim-build/build/buildScripts
COPY docker/autobuildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/autobuildImage/distribute.py /context/distribute.py
COPY docker/autobuildwin64Image/entrypoint.py /context/entrypoint.py
COPY docker/autobuildwin64Image/jni_md.h /context/jni_md.h

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

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
