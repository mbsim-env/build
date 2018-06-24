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
# enable swig interface to mbsim
ENV MBSIM_SWIG=1
# build
RUN /mbsim-env/mbsim/misc/BuildService/scripts/build.py --sourceDir /mbsim-env --binSuffix=-build --prefix /mbsim-env/local -j $JOBS --disableUpdate --disableRunExamples --passToConfigure --disable-static --enable-python --with-qwt-inc-prefix=/3rdparty/local/include --with-qwt-lib-prefix=/3rdparty/local/lib --with-qwt-lib-name=qwt --with-qmake=qmake-qt5 COIN_CFLAGS=-I/3rdparty/local/include COIN_LIBS="-L/3rdparty/local/lib64 -lCoin" SOQT_CFLAGS=-I/3rdparty/local/include SOQT_LIBS="-L/3rdparty/local/lib64 -lSoQt"
# do not run examples here it is done later in the test image





# now use the mbsim-env-base image and copy the local dir of 3rd party and mbsim-env
FROM mbsimenv/mbsim-env-base AS intermediateImage

COPY --from=buildImage /3rdparty/local /3rdparty/local
COPY --from=buildImage /mbsim-env/local /mbsim-env/local





# make some test in the run image (this image is throw away after the tests)
FROM intermediateImage

# configuration
ARG JOBS=4

# copy over examples dir
COPY --from=buildImage /mbsim-env/mbsim/examples /mbsim-env/mbsim/examples

# configure pkg-config
ENV PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig:/mbsim-env/local/lib/pkgconfig:/mbsim-env/local/lib64/pkgconfig

# install everything and configure for X11 tests
RUN yum install -y \
  h5py \
  tigervnc-server \
  && yum clean all

# run basic examples but no source code example and run GUI tests
WORKDIR /mbsim-env
# MISSING we should run the examples with --checkGUIs options but this does not work sometimes for a unknown reason
# (simulations hang)
RUN /mbsim-env/mbsim/examples/runexamples.py -j $JOBS --filter "'basic' in labels and not src" /mbsim-env/mbsim/examples
# MISSING as a workaround we test now the GUI tools by hand
ENV DISPLAY=:0
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
  org.label-schema.docker.cmd="docker run --rm --user $(id -u):$(id -g) -e DISPLAY -v ${XAUTHORITY:-$HOME/.Xauthority}:/root/.Xauthority --net=host mbsimenv/mbsim-env-run"
 
# per default run mbsimgui
CMD ["mbsimgui"]
