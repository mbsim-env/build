# mbsim-env-run image: this image is used to run mbsim-env tools

# build mbsim-env using the mbsim-env-build image
FROM mbsimenv/mbsim-env-build AS buildImage

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

# build mbsim-env
WORKDIR /mbsim-env
# mfmf use --filter "'basic' in labels" instead of directories in runexamples when octave evaluator is working
RUN /mbsim-env/mbsim/misc/BuildService/scripts/build.py --sourceDir /mbsim-env --binSuffix=-build --prefix /mbsim-env/local -j $JOBS --disableUpdate --passToConfigure --disable-static --enable-python --with-qwt-inc-prefix=/3rdparty/local/include --with-qwt-lib-prefix=/3rdparty/local/lib --with-qwt-lib-name=qwt --with-qmake=qmake-qt5 COIN_CFLAGS=-I/3rdparty/local/include COIN_LIBS="-L/3rdparty/local/lib64 -lCoin" SOQT_CFLAGS=-I/3rdparty/local/include SOQT_LIBS="-L/3rdparty/local/lib64 -lSoQt" --passToRunexamples xmlflat/bouncing_ball_boostodeint xmlflat/hierachical_modelling mechanics/basics/time_dependent_kinematics fmi/sphere_on_plane mechanics/basics/hierachical_modelling





# now use the mbsim-env-base image and copy the local dir of 3rd party and mbsim-env
FROM mbsimenv/mbsim-env-base AS intermediateImage

COPY --from=buildImage /3rdparty/local /3rdparty/local
COPY --from=buildImage /mbsim-env/local /mbsim-env/local





# make some test in the run image (this image is throw away after the tests)
FROM intermediateImage

# install everything and configure for X11 tests
RUN yum install -y tigervnc-server
ENV DISPLAY=:0

# test command line tools
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
RUN h5plotserie -h

# test X11 tools
RUN vncserver :0 -SecurityTypes None && \
  mbsimgui --autoExit && \
  openmbv --autoExit && \
  h5plotserie --autoExit





# now continue with the mbsim-env-run image
FROM intermediateImage

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsim-env" \
  org.label-schema.description="All MBSim-Environment tools for runing and postprocessing simulations." \
  org.label-schema.url="https://www.mbsim-env.de" \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/runImageContext" \
  org.label-schema.vendor="MBSim-Environment" \
  org.label-schema.docker.cmd="docker run --rm --user $(id -u):$(id -g) mbsimenv/mbsim-env-run mbsimgui"
