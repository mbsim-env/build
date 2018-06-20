# prepare base system
FROM mbsimenv/mbsim-env-build AS mbsimenvRun

# configuration
ARG JOBS=4
ARG FMATVECBRANCH=master
ARG HDF5SERIEBRANCH=master
ARG OPENMBVBRANCH=master
ARG MBSIMBRANCH=master
ARG BUILDBRANCH=master

# get mbsim-env sources
RUN mkdir /mbsim-env

WORKDIR /mbsim-env
RUN git clone https://github.com/mbsim-env/fmatvec.git
WORKDIR /mbsim-env/fmatvec
RUN git checkout $FMATVECBRANCH

WORKDIR /mbsim-env
RUN git clone https://github.com/mbsim-env/hdf5serie.git
WORKDIR /mbsim-env/hdf5serie
RUN git checkout $HDF5SERIEBRANCH

WORKDIR /mbsim-env
RUN git clone https://github.com/mbsim-env/openmbv.git
WORKDIR /mbsim-env/openmbv
RUN git checkout $OPENMBVBRANCH

WORKDIR /mbsim-env
RUN git clone https://github.com/mbsim-env/mbsim.git
WORKDIR /mbsim-env/mbsim
RUN git checkout $MBSIMBRANCH

WORKDIR /mbsim-env
RUN git clone https://github.com/mbsim-env/build.git
WORKDIR /mbsim-env/build
RUN git checkout $BUILDBRANCH

# build
WORKDIR /mbsim-env
# mfmf use --filter "'basic' in labels" instead of directories in runexamples
RUN /mbsim-env/mbsim/misc/BuildService/scripts/build.py --sourceDir /mbsim-env --binSuffix=-build --prefix /mbsim-env/local -j $JOBS --disableUpdate --passToConfigure --disable-static --enable-python --with-qwt-inc-prefix=/3rdparty/local/include --with-qwt-lib-prefix=/3rdparty/local/lib --with-qwt-lib-name=qwt --with-qmake=qmake-qt5 COIN_CFLAGS=-I/3rdparty/local/include COIN_LIBS="-L/3rdparty/local/lib64 -lCoin" SOQT_CFLAGS=-I/3rdparty/local/include SOQT_LIBS="-L/3rdparty/local/lib64 -lSoQt" --passToRunexamples xmlflat/bouncing_ball_boostodeint xmlflat/hierachical_modelling mechanics/basics/time_dependent_kinematics fmi/sphere_on_plane mechanics/basics/hierachical_modelling





# mfmf rework the next commands
FROM centos:centos7

ENV LD_LIBRARY_PATH=/3rdparty/local/lib:/3rdparty/local/lib64:/mbsim-env/local/lib:/mbsim-env/local/lib64 \
    PATH=$PATH:/3rdparty/local/bin:/mbsim-env/local/bin

COPY --from=mbsimenvRun /3rdparty/local /3rdparty/local
COPY --from=mbsimenvRun /mbsim-env/local /mbsim-env/local

RUN yum -y install epel-release
RUN yum -y install hdf5
RUN yum -y install boost-regex
RUN yum -y install xerces-c
RUN yum -y install lapack
RUN yum -y install boost-filesystem
RUN yum -y install boost-timer
RUN yum -y install libarchive
RUN yum -y install boost-date-time
RUN yum -y install qt5-qtbase-gui
RUN yum -y install qt5-qtsvg
RUN yum -y install mesa-libGLU
RUN yum -y install qt5-qtwebkit

# mfmf
RUN yum -y install xkeyboard-config
RUN systemd-machine-id-setup
RUN yum -y install mesa-dri-drivers
RUN yum -y install libdrm
RUN mbxmlutilspp
RUN mbsimflatxml
RUN mbsimxml
RUN mbxmlutilsvalidate
RUN mbsimCreateFMU
RUN h5dumpserie
RUN h5flushserie
RUN h5lsserie
RUN mbsimgui -h
RUN openmbv -h
RUN h5plotserie -h || true
