# mbsim-env-build image: this image is used to build mbsim-env

FROM mbsimenv/mbsim-env-base AS centosBaseImage

# install everything needed to build mbsim-env tools from centos7
RUN yum -y install \
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





# build/install additional tools needed by mbsim-env but not available from centos7
FROM centosBaseImage AS thirdpartyBuildImage

# configuration
ARG JOBS=4
ARG SWIGVERSION=3.0.7
ARG CASADIBRANCH=470b5b3f0cc4044e3cb0eb20dfb2a85e247c62a6
ARG QWTVERSION=6.1.3
ARG COINBRANCH=7e191c8f6a31
ARG SOQTBRANCH=945ec22f6219

# install additional packaged needed to build the tool not part of centos7
RUN yum -y install \
  wget \
  bzip2 \
  qt5-qttools-devel \
  mercurial \
  cmake3

# configure path and envvar for the 3rd party tools
RUN mkdir /3rdparty
ENV PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig

# compile/install swig3 (centos7 only provides swig2)
WORKDIR /3rdparty
RUN wget -q -O - https://kent.dl.sourceforge.net/project/swig/swig/swig-$SWIGVERSION/swig-$SWIGVERSION.tar.gz | tar -xz
RUN mkdir /3rdparty/swig-build
WORKDIR /3rdparty/swig-build
RUN ../swig-$SWIGVERSION/configure --disable-static --enable-shared CXXFLAGS="-O2" CFLAGS="-O2" --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install

# compile/install casadi (we use the fork from friedrichatgc)
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

# compile/install qwt6 for Qt5 (centos only provides qwt6 for Qt4)
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

# compile/install Coin3D
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/coin
WORKDIR /3rdparty/coin
RUN hg update $COINBRANCH
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../coin
RUN make -j $JOBS
RUN make install

# compile/install SoQt
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt
WORKDIR /3rdparty/soqt
RUN hg update $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../soqt
RUN make -j $JOBS
RUN make install





# now stick back to centosBaseImage and copy over the local dir from the 3rd party build stage
FROM centosBaseImage

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsim-env-build" \
  org.label-schema.description="Build all tools from MBSim-Environment." \
  org.label-schema.url="https://www.mbsim-env.de" \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/runBuildContext" \
  org.label-schema.vendor="MBSim-Environment" \
  org.label-schema.docker.params="SWIGVERSION=swig verion to use,CASADIBRANCH=CasADi branch to use,QWTVERSION=QWT version to use,COINBRANCH=Coin3D branch to use,SOQTBRANCH=SoQt version to use"

# configure pkg-config
ENV PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig:/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig

# copy over the local dir from the 3rd party build stage
COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local

# enable ccache (after all other things are done); note /mbsim-env is usually a persistent Docker volume
ENV PATH=/usr/lib64/ccache:$PATH \
    CCACHE_DIR=/mbsim-env/.ccache
