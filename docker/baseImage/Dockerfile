# base image: this image is used for the images build and run

# centos7 is our operating system
FROM centos:centos7 AS baseImage

# configuration, mainly for X11
RUN systemd-machine-id-setup
RUN mkdir /run/user/$UID

# environment variables to find the osupdate, 3rd party and mbsim libraries and binaries
ENV LD_LIBRARY_PATH=/osupdate/local/lib:/osupdate/local/lib64:/3rdparty/local/lib:/3rdparty/local/lib64:/mbsim-env/local/lib:/mbsim-env/local/lib64 \
    PKG_CONFIG_PATH=/osupdate/local/lib/pkgconfig:/osupdate/local/lib64/pkgconfig:/3rdparty/local/lib/pkgconfig:/3rdparty/local/lib64/pkgconfig \
    PATH=$PATH:/3rdparty/local/bin:/mbsim-env/local/bin \
    XDG_RUNTIME_DIR=/run/user/$UID

# install everything from centos7 needed to run mbsim-env tools
RUN yum -y install epel-release && \
  yum -y install \
  hdf5 \
  numpy \
  boost-regex \
  xerces-c \
  lapack \
  boost-filesystem \
  boost-timer \
  libarchive \
  boost-date-time \
  qt5-qtsvg \
  qt5-qtwebkit \
  xkeyboard-config \
  xorg-x11-fonts-Type1 \
  urw-fonts \
  octave \
  && yum clean all
# fix octave 3.8.2: it is not initializing when runnig without a DISPLAY
RUN sed -re "s/\<__have_fltk__ *\( *\) *&& *have_window_system *\( *\)/have_window_system () \&\& __have_fltk__ ()/" \
  /usr/lib64/octave/3.8.2/oct/x86_64-redhat-linux-gnu/PKG_ADD > /tmp/mbsim-env.tmp && \
  mv -f /tmp/mbsim-env.tmp /usr/lib64/octave/3.8.2/oct/x86_64-redhat-linux-gnu/PKG_ADD





# build a newer mesa library
FROM baseImage AS mesaBuild

# configuration
ARG JOBS=4
ARG MESAVERSION=18.1.3

# install required packages to build mesa
RUN yum install -y \
  wget \
  make \
  gcc-c++ \
  zlib-devel \
  xorg-x11-proto-devel \
  libxcb-devel \
  libXext-devel \
  expat-devel \
  && yum clean all

# create dirs
RUN mkdir /osupdate /osupdate/local /osupdate/mesa-build

# download new mesa
WORKDIR /osupdate
RUN set -o pipefail && \
  wget -q -O - https://mesa.freedesktop.org/archive/mesa-$MESAVERSION.tar.gz | tar -xz

# build and install new meas
WORKDIR /osupdate/mesa-build
RUN ../mesa-$MESAVERSION/configure --prefix=/osupdate/local --with-platforms=x11 --disable-driglx-direct --with-dri-drivers=swrast --with-gallium-drivers=swrast --disable-dri --disable-dri3 --enable-glx=xlib --disable-driglx-direct --disable-gbm --disable-egl CXXFLAGS="-O2" CFLAGS="-O2"
RUN make -j $JOBS
RUN make install





# continue baseImage
FROM baseImage

# copy over the osupdate dir from the mesa build image
COPY --from=mesaBuild /osupdate/local /osupdate/local

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/base" \
  org.label-schema.description="Build the base image for all MBSim-Environment images." \
  org.label-schema.url="https://www.mbsim-env.de" \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/baseImage" \
  org.label-schema.vendor="MBSim-Environment" \
  org.label-schema.docker.params="JOBS=number of parallel jobs,MESAVERSION=mesa verion to use"

# run bash per default
CMD ["bash"]
