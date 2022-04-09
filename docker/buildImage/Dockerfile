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
RUN yum install -y http://www6.atomicorp.com/channels/atomic/centos/7/x86_64/RPMS/atomic-release-1.0-21.el7.art.noarch.rpm && \
  yum --setopt=skip_missing_names_on_install=False -y install epel-release centos-release-scl && \
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
  python36-pytz \
  python36-pygithub \
  python3-psycopg2 \
  adwaita-qt5 \
  qt5-qtstyleplugins \
  cmake3 \
  ninja-build \
  atomic-sqlite \
  ca-certificates \
  && yum clean all
# config devtoolset-7 and atomic SCL
ENV PATH=/opt/atomicorp/atomic/root/usr/bin:/opt/atomicorp/atomic/root/usr/sbin:/opt/rh/devtoolset-7/root/usr/bin:$PATH \
    LD_LIBRARY_PATH=/opt/atomicorp/atomic/root/usr/lib64:/opt/rh/devtoolset-7/root/usr/lib64:/opt/rh/devtoolset-7/root/usr/lib:/opt/rh/devtoolset-7/root/usr/lib64/dyninst:/opt/rh/devtoolset-7/root/usr/lib/dyninst:/opt/rh/devtoolset-7/root/usr/lib64:/opt/rh/devtoolset-7/root/usr/lib:$LD_LIBRARY_PATH
#RUN npm install mathjax-node
RUN pip3 install h5py==2.9.0 sympy django==3.1 django-octicons==1.0





# build/install additional tools needed by mbsim-env but not available from centos7
FROM centosBaseImage AS thirdpartyBuildImage

# configuration
ARG JOBS=4
ARG MESAVERSION=18.1.3
ARG OCTAVEVERSION=4.4.1
ARG SWIGVERSION=4.0.1
ARG QWTVERSION=6.1.3
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
RUN git clone https://github.com/coin3d/coin.git
ARG COINBRANCH=CI-builds
RUN (cd coin; git checkout $COINBRANCH)
RUN mkdir /3rdparty/coin-build

# soqt
RUN git clone https://github.com/coin3d/soqt.git
ARG SOQTBRANCH=CI-builds
RUN (cd soqt; git checkout $SOQTBRANCH)
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
RUN (cd ../coin && git submodule init && git submodule update)
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DBoost_INCLUDE_DIR=/usr/include/boost169 -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../coin
RUN make -j $JOBS
RUN make install

# SoQt
WORKDIR /3rdparty/soqt-build
RUN (cd ../soqt && git submodule init && git submodule update)
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local ../soqt
RUN make -j $JOBS
RUN make install

# HDF5
WORKDIR /3rdparty
RUN git clone https://github.com/HDFGroup/hdf5.git
ARG HDF5BRANCH=hdf5-1_10_7
RUN (cd hdf5; git checkout $HDF5BRANCH)
RUN mkdir /3rdparty/hdf5-build
WORKDIR /3rdparty/hdf5-build
RUN cmake3 -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DHDF5_ENABLE_Z_LIB_SUPPORT=on ../hdf5
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
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildImage/c++-analyzer /context/c++-analyzer
COPY docker/buildImage/ccc-analyzer /context/ccc-analyzer
COPY misc /mbsim-build/build/misc
COPY django/mbsimenv/build.py           /context/mbsimenv/build.py                    
COPY django/mbsimenv/runexamples.py     /context/mbsimenv/runexamples.py              
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenv/mbsimenvSecrets.py          
COPY django/mbsimenv/mbsimenv           /context/mbsimenv/mbsimenv                        
COPY django/mbsimenv/base               /context/mbsimenv/base                        
COPY django/mbsimenv/builds             /context/mbsimenv/builds                      
COPY django/mbsimenv/runexamples        /context/mbsimenv/runexamples                 
COPY django/mbsimenv/service            /context/mbsimenv/service                     

# enable ccache (after all other things are done); note /mbsim-env is usually a persistent Docker volume;
# enable nu-html -> add to CLASSPATH
# PATH for cache
ENV PATH=/usr/lib64/ccache:/mbsim-env/build/misc:$PATH \
    LD_LIBRARY_PATH=/3rdparty/local/lib/octave/4.4.1:$LD_LIBRARY_PATH \
    CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    CLASSPATH=$CLASSPATH:/3rdparty/vnu.jar

# user/group handling
# - add group dockeruser and user dockeruser with group dockeruser
# - add group apache with id 48
# - create volume mount dirs
# - set permissions of volume mount dirs
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  groupadd -g 48 apache && \
  mkdir /mbsim-env /mbsim-ccache /databasemedia /webserverstatic && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-ccache /webserverstatic && \
  chown dockeruser:apache /databasemedia && chmod ug+rwx /databasemedia

# add g++/c++ to cache dir (its not added automatically since g++ is not installed since scl is used
RUN ln -s $(readlink /usr/lib64/ccache/gcc) /usr/lib64/ccache/g++ && ln -s $(readlink /usr/lib64/ccache/gcc) /usr/lib64/ccache/c++

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# ccache config
RUN ccache -M 20G

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
