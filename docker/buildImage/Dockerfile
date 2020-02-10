# build image: this image is used to build mbsim-env

ARG MBSIMENVTAGNAME=latest
FROM mbsimenv/base:$MBSIMENVTAGNAME AS centosBaseImage

# install everything needed to build mbsim-env tools from centos7
RUN yum --setopt=skip_missing_names_on_install=False -y install \
  chrpath \
  gdb \
  valgrind \
  libxslt \
  lcov \
  tigervnc-server \
  git \
  make \
  gcc-c++ \
  libtool \
  automake \
  autoconf \
  pcre-devel \
  python3-devel \
  qt5-qtbase-devel \
  qt5-qtsvg-devel \
  hdf5-devel \
  python3-pip \
  boost169-devel \
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
  qrupdate-devel \
  suitesparse-devel \
  file \
  libarchive-devel \
  ccache \
  mesa-libGLU-devel \
  npm \
  java-1.8.0-openjdk-devel \
  python36-requests \
  perl-Text-Glob \
  clang-analyzer \
  graphviz \
  python36-numpy \
  swig3 \
  && yum clean all
RUN npm install mathjax-node
RUN pip3 install h5py sympy





# build/install additional tools needed by mbsim-env but not available from centos7
FROM centosBaseImage AS thirdpartyBuildImage

# configuration
ARG JOBS=4
ARG QWTVERSION=6.1.3
ARG COINBRANCH=7e191c8f6a31
ARG SOQTBRANCH=945ec22f6219
ARG NUHTMLVERSION=18.8.29

# install additional packaged needed to build the tools not part of centos7
RUN yum --setopt=skip_missing_names_on_install=False -y install \
  wget \
  bzip2 \
  unzip \
  qt5-qttools-devel \
  mercurial \
  cmake3 \
  && yum clean all

# configure path and envvar for the 3rd party tools
RUN mkdir /3rdparty

# get tools to build
WORKDIR /3rdparty

# qwt
RUN set -o pipefail && \
  wget -q -O - https://sourceforge.net/projects/qwt/files/qwt/$QWTVERSION/qwt-$QWTVERSION.tar.bz2 | tar -xj
# fix the install dir (this cannot be done via options in qwt)
RUN sed -i -re "s~^( *QWT_INSTALL_PREFIX *= *).*~\1/3rdparty/local~" qwt-$QWTVERSION/qwtconfig.pri
RUN mkdir /3rdparty/qwt-build

# coin
RUN hg clone https://bitbucket.org/Coin3D/coin -r $COINBRANCH
RUN mkdir /3rdparty/coin-build

# soqt
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt -r $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build

# nu-html
WORKDIR /3rdparty/nuhtml
RUN wget -q https://github.com/validator/validator/releases/download/$NUHTMLVERSION/vnu.jar_$NUHTMLVERSION.zip
RUN unzip vnu.jar_$NUHTMLVERSION.zip

# compile/install

# qwt6 for Qt5 (centos only provides qwt6 for Qt4)
WORKDIR /3rdparty/qwt-build
RUN qmake-qt5 ../qwt-$QWTVERSION
RUN make -j $JOBS
RUN make install

# Coin3D
WORKDIR /3rdparty/coin-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../coin
RUN make -j $JOBS
RUN make install

# SoQt
WORKDIR /3rdparty/soqt-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../soqt
RUN make -j $JOBS
RUN make install





# now stick back to centosBaseImage and copy over the local dir from the 3rd party build stage
FROM centosBaseImage

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/build" \
  org.label-schema.description="Build all tools from MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/buildImage" \
  org.label-schema.vendor="MBSim-Environment" \
  org.label-schema.docker.params="JOBS=number of parallel jobs,QWTVERSION=QWT version to use,COINBRANCH=Coin3D branch to use,SOQTBRANCH=SoQt version to use"

# copy over the local dir from the 3rd party build stage
COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local
COPY --from=thirdpartyBuildImage /3rdparty/nuhtml/dist/vnu.jar /3rdparty/vnu.jar

# copy build repo
COPY docker/buildImage/entrypoint.py /context/entrypoint.py
COPY docker/buildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildImage/c++-analyzer /context/c++-analyzer
COPY docker/buildImage/ccc-analyzer /context/ccc-analyzer
COPY buildScripts /mbsim-build/build/buildScripts

# enable ccache (after all other things are done); note /mbsim-env is usually a persistent Docker volume;
# enable nu-html -> add to CLASSPATH
ENV PATH=/usr/lib64/ccache:/mbsim-env/mbsim/examples:/mbsim-env/build/buildScripts:$PATH \
    CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    CLASSPATH=$CLASSPATH:/3rdparty/vnu.jar

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# ccache config
RUN ccache -M 10G

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
