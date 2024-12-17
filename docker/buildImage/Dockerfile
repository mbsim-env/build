# build image: this image is used to build mbsim-env

FROM debian:12.7

# install using apt
RUN apt update -y && apt install -y \
  gcc g++ gfortran \
  python3 \
  python3-django python3-psutil python3-pip python3-django-allauth python3-psycopg2 python3-paramiko \
  python3-github python3-dev python3-numpy python3-h5py python3-pyside2.qtwidgets python3-scipy python3-matplotlib \
  libboost-thread-dev libboost-system-dev libboost-stacktrace-dev libboost-regex-dev \
  libboost-filesystem-dev libboost-date-time-dev libboost-chrono-dev libboost-program-options-dev libboost-timer-dev \
  ccache \
  git \
  libtool \
  automake \
  autoconf \
  doxygen \
  cmake \
  make \
  ninja-build \
  graphviz \
  ninja-build \
  patchelf \
  gdb \
  valgrind \
  lcov \
  qtbase5-dev \
  libqt5svg5-dev \
  libopenblas-serial-dev \
  libxalan-c-dev \
  libxerces-c-dev \
  libarchive-dev \
  libarpack2-dev libspooles-dev \
  libhdf5-dev \
  libcoin-dev libsoqt520-dev \
  libqwt-qt5-dev \
  octave-dev \
  which \
  dos2unix \
  file \
  rsync \
  pkg-config \
  npm \
  nodejs \
  swig \
  xalan \
  wget \
  unzip \
  tigervnc-standalone-server \
  sshpass \
  p7zip-full \
  qt5-flatpak-platformtheme qt5-gtk-platformtheme qt5-gtk2-platformtheme qt5-style-kvantum-themes \
  qt5-ukui-platformtheme qt5-xdgdesktopportal-platformtheme qt5-style-plugin-cleanlooks \
  qt5-style-plugin-motif qt5-style-plugin-plastique \
  && rm -rf /var/lib/apt/lists/* 

# install using pip
RUN pip3 install --break-system-packages django-octicons

RUN mkdir /3rdparty

#mfmf # install using npm
#mfmf WORKDIR /3rdparty
#mfmf RUN npm install mathjax-node@2.1
#mfmf ENV NODE_PATH=/3rdparty/node_modules

# nu-html
ARG NUHTMLVERSION=20.6.30
RUN mkdir /dummy && cd /dummy && \
    wget -q https://github.com/validator/validator/releases/download/$NUHTMLVERSION/vnu.jar_$NUHTMLVERSION.zip && \
    unzip vnu.jar_$NUHTMLVERSION.zip && \
    cp dist/vnu.jar /3rdparty/vnu.jar && \
    rm -rf dummy
ENV CLASSPATH=$CLASSPATH:/3rdparty/vnu.jar

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/build" \
  org.label-schema.description="Build all tools from MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/buildImage" \
  org.label-schema.vendor="MBSim-Environment" \
  org.label-schema.docker.params="JOBS=number of parallel jobs,QWTVERSION=QWT version to use,COINBRANCH=Coin3D branch to use,SOQTBRANCH=SoQt version to use"

# copy build repo
COPY docker/buildImage/entrypoint.py /context/entrypoint.py
COPY docker/buildImage/distribute.py /context/distribute.py
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
# PATH for cache
# add octave path to LD_LIBRARY_PATH just to enable distribute.py to find it for compiled *.oct files (e.g. OpenMBV.oct)
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    PATH=/usr/lib/ccache:$PATH \
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/octave/7.3.0

# user/group handling
# - add group dockeruser and user dockeruser with group dockeruser
# - create volume mount dirs
# - set permissions of volume mount dirs
ARG DOCKERUSERID=1065
RUN groupadd -g $DOCKERUSERID dockeruser && useradd --no-log-init -u $DOCKERUSERID -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-ccache /home/dockeruser /run/user/$DOCKERUSERID && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-ccache /home/dockeruser /run/user/$DOCKERUSERID && \
  chmod 0700 /run/user/$DOCKERUSERID

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# configuration, mainly for X11
ENV XDG_RUNTIME_DIR=/run/user/$DOCKERUSERID

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["timeout", "-k", "30s", "5h", "/context/entrypoint.py"]
