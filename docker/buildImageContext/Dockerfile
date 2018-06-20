# prepare base system
FROM centos:centos7 AS centosBaseImage
RUN yum -y install epel-release
RUN yum update && \
    yum -y install \
      git \
      make \
      gcc-c++ \
      libtool \
      automake \
      autoconf \
      pcre-devel \
      python-devel \
      numpy \
      qt5-qtbase-devel \
      qt5-qtsvg \
      qt5-qtsvg-devel \
      hdf5-devel \
      h5py \
      boost-devel \
      lapack-devel \
      doxygen \
      xalan-c-devel \
      which \
      octave-devel \
      dos2unix \
      xerces-c-devel \
      arpack-devel \
      fontconfig-devel \
      freetype-devel \
      gl2ps-devel \
      libcurl-devel \
      mesa-libGLU-devel \
      qrupdate-devel \
      suitesparse-devel \
      file \
      qt5-qtwebkit-devel \
      libarchive-devel \
      ccache





# build additional dependencies not available via the package manager
FROM centosBaseImage AS thirdpartyBuildImage

RUN yum -y install \
  wget \
  bzip2 \
  qt5-qttools-devel \
  mercurial \
  cmake3

# configuration
ARG JOBS=4

RUN mkdir /3rdparty
ENV PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig \
    LD_LIBRARY_PATH=/3rdparty/local/lib:/3rdparty/local/lib64 \
    PATH=$PATH:/3rdparty/local/bin

# compile/install swig (we use swig 3.0.7; centos7 only provides swig 2)
ARG SWIGVERSION=3.0.7
WORKDIR /3rdparty
RUN wget -q -O - https://kent.dl.sourceforge.net/project/swig/swig/swig-$SWIGVERSION/swig-$SWIGVERSION.tar.gz | tar -xz
RUN mkdir /3rdparty/swig-build
WORKDIR /3rdparty/swig-build
RUN ../swig-$SWIGVERSION/configure --disable-static --enable-shared CXXFLAGS="-O2" CFLAGS="-O2" --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

# compile/install casadi (we use the for from friedrichatgc at the current default branch)
ARG CASADIBRANCH=470b5b3f0cc4044e3cb0eb20dfb2a85e247c62a6
WORKDIR /3rdparty
RUN git clone https://github.com/friedrichatgc/casadi.git
WORKDIR /3rdparty/casadi
RUN git checkout $CASADIBRANCH
RUN mkdir /3rdparty/casadi-build
WORKDIR /3rdparty/casadi-build
RUN cmake3 -DENABLE_STATIC=OFF -DENABLE_SHARED=ON -DCMAKE_BUILD_TYPE=Release -DWITH_PYTHON=on \
  -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../casadi
RUN make -j $JOBS
RUN make install

# compile/install qwt (we use qwt 6.1.3; centos only provides qwt 6 linked to Qt4)
ARG QWTVERSION=6.1.3
WORKDIR /3rdparty
RUN wget -q -O - https://kent.dl.sourceforge.net/project/qwt/qwt/$QWTVERSION/qwt-$QWTVERSION.tar.bz2 | tar -xj
# fix the install dir (this cannot be done via options in qwt)
RUN sed -re "s~^( *QWT_INSTALL_PREFIX *= *).*~\1/3rdparty/local~" qwt-$QWTVERSION/qwtconfig.pri > qwt-$QWTVERSION/qwtconfig.pri.new && \
  mv -f qwt-$QWTVERSION/qwtconfig.pri.new qwt-$QWTVERSION/qwtconfig.pri
RUN mkdir /3rdparty/qwt-build
WORKDIR /3rdparty/qwt-build
RUN qmake-qt5 ../qwt-$QWTVERSION
RUN make -j $JOBS
RUN make install

# compile/install coin (we use mercurial commit 7e191c8f6a31)
ARG COINBRANCH=7e191c8f6a31
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/coin
WORKDIR /3rdparty/coin
RUN hg update $COINBRANCH
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../coin
RUN make -j $JOBS
RUN make install

# compile/install soqt (we use mercurial commit 945ec22f6219)
ARG SOQTBRANCH=945ec22f6219
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt
WORKDIR /3rdparty/soqt
RUN hg update $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../soqt
RUN make -j $JOBS
RUN make install





# build the build image: use the base image and copy the build dependencies
FROM centosBaseImage

# prepare mbsim-env
ENV PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig:/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig \
    LD_LIBRARY_PATH=/3rdparty/local/lib:/3rdparty/local/lib64:/mbsim-env/local/lib:/mbsim-env/local/lib64 \
    PATH=$PATH:/3rdparty/local/bin:/mbsim-env/local/bin

COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local

# enable ccache (after all other things are done); you need to set CCACHE_DIR to a persistent dir when running the image
ENV PATH=/usr/lib64/ccache:$PATH
