# build image: this image is used to build mbsim-env

FROM centos:centos7 AS centosBaseImage

# configuration, mainly for X11
RUN systemd-machine-id-setup
RUN mkdir /run/user/$UID

# environment variables to find the osupdate, 3rd party and mbsim libraries and binaries
ENV LD_LIBRARY_PATH=/osupdate/local/lib:/osupdate/local/lib64:/3rdparty/local/lib:/3rdparty/local/lib64 \
    PKG_CONFIG_PATH=/osupdate/local/lib/pkgconfig:/osupdate/local/lib64/pkgconfig:/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig \
    PATH=$PATH:/3rdparty/local/bin \
    XDG_RUNTIME_DIR=/run/user/$UID

# install everything needed to build mbsim-env tools from centos7
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release centos-release-scl && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  xkeyboard-config \
  xorg-x11-fonts-Type1 \
  urw-fonts \
  patchelf \
  gdb \
  valgrind \
  libxslt \
  lcov \
  tigervnc-server \
  git \
  make \
  devtoolset-7-gcc devtoolset-7-gcc-c++ devtoolset-7-gcc-gfortran \
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
  && yum clean all
# config gcc7 => do not use the "exec form" form now on use the "shell form"!!!!!
SHELL ["scl", "enable", "devtoolset-7"]
RUN npm install mathjax-node
RUN pip3 install h5py sympy





# build/install additional tools needed by mbsim-env but not available from centos7
FROM centosBaseImage AS thirdpartyBuildImage

# configuration
ARG JOBS=4
ARG MESAVERSION=18.1.3
ARG OCTAVEVERSION=4.4.1
ARG SWIGVERSION=4.0.1
ARG QWTVERSION=6.1.3
ARG COINBRANCH=7e191c8f6a31
ARG SOQTBRANCH=945ec22f6219
ARG NUHTMLVERSION=18.8.29

# install additional packaged needed to build the tools not part of centos7
RUN yum --setopt=skip_missing_names_on_install=False -y install \
  wget \
  zlib-devel \
  xorg-x11-proto-devel \
  libxcb-devel \
  libXext-devel \
  libXext-devel \
  bzip2 \
  unzip \
  qt5-qttools-devel \
  mercurial \
  cmake3 \
  patch \
  && yum clean all

# configure path and envvar for the 3rd party tools
RUN mkdir /3rdparty /osupdate /osupdate/local

# get tools to build

# mesa
WORKDIR /osupdate
RUN set -o pipefail && \
  wget -q -O - https://mesa.freedesktop.org/archive/mesa-$MESAVERSION.tar.gz | tar -xz
RUN mkdir /osupdate/mesa-build

WORKDIR /3rdparty

# octave
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.gz | tar -xz
RUN mkdir /3rdparty/octave-build

# swig
RUN set -o pipefail && \
  wget -q -O - https://netcologne.dl.sourceforge.net/project/swig/swig/swig-4.0.1/swig-4.0.1.tar.gz | tar -xz
RUN mkdir /3rdparty/swig-build

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

# meas
WORKDIR /osupdate/mesa-build
RUN ../mesa-$MESAVERSION/configure --prefix=/osupdate/local --with-platforms=x11 --disable-driglx-direct --with-dri-drivers=swrast --with-gallium-drivers=swrast --disable-dri --disable-dri3 --enable-glx=xlib --disable-driglx-direct --disable-gbm --disable-egl CXXFLAGS="-O2" CFLAGS="-O2"
RUN make -j $JOBS
RUN make install

# octave
WORKDIR /3rdparty/octave-build
RUN ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --disable-readline
RUN make -j $JOBS
RUN make install
# fix octave: it is not initializing when runnig without a DISPLAY
RUN sed -i -re "s/^ *if *\((.*)&& *have_window_system *\( *\)(.*)$/if(have_window_system() \&\& \1\2/" \
  /3rdparty/local/lib/octave/4.4.1/oct/x86_64-pc-linux-gnu/PKG_ADD && \
  sed -i -re "s/^.*gnuplot.*$/% gnuplot is removed/" \
  /3rdparty/local/lib/octave/4.4.1/oct/x86_64-pc-linux-gnu/PKG_ADD

# swig
WORKDIR /3rdparty/swig-build
RUN ../swig-$SWIGVERSION/configure --enable-shared --disable-static --prefix=/3rdparty/local
RUN make -j $JOBS
RUN make install
# bugfix for swig
COPY docker/buildwin64Image/swig.patch /context/swig.patch
RUN patch -d /3rdparty/local/share/swig/4.0.1 -p0 < /context/swig.patch

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
COPY --from=thirdpartyBuildImage /osupdate/local /osupdate/local
ENV LIBGL_ALWAYS_INDIRECT=1

# copy build repo
COPY docker/buildImage/entrypoint.py /context/entrypoint.py
COPY docker/buildImage/scl_wrapper_entrypoint.sh /context/scl_wrapper_entrypoint.sh
COPY docker/buildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildImage/c++-analyzer /context/c++-analyzer
COPY docker/buildImage/ccc-analyzer /context/ccc-analyzer
COPY buildScripts /mbsim-build/build/buildScripts

# enable ccache (after all other things are done); note /mbsim-env is usually a persistent Docker volume;
# enable nu-html -> add to CLASSPATH
# CCACHE handling: /usr/lib64/ccache cannot be added here to PATH due to scl.
#                  this is done in the entrypoint wrapper, see below
ENV PATH=/mbsim-env/mbsim/examples:/mbsim-env/build/buildScripts:$PATH \
    LD_LIBRARY_PATH=/3rdparty/local/lib/octave/4.4.1:$LD_LIBRARY_PATH \
    CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    CLASSPATH=$CLASSPATH:/3rdparty/vnu.jar

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state

# add g++/c++ to cache dir (its not added automatically since g++ is not installed since scl is used
RUN ln -s $(readlink /usr/lib64/ccache/gcc) /usr/lib64/ccache/g++ && ln -s $(readlink /usr/lib64/ccache/gcc) /usr/lib64/ccache/c++

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# ccache config
RUN ccache -M 10G

# these are the default arguments when running the container
CMD []
# call this script when running the container
# (we need a special wrapper to call the entrypoint.py inside of scl
#  also handling of ccache PATH handling is needed their)
ENTRYPOINT ["/context/scl_wrapper_entrypoint.sh"]
