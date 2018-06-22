# mbsim-env-base image: this image is used for the images mbsim-env-build and mbsim-env-run

# centos7 is our operating system
FROM centos:centos7

# configuration, mainly for X11
RUN systemd-machine-id-setup
RUN mkdir /run/user/$UID

# environment variables to find the 3rd party and mbsim libraries and binaries
ENV LD_LIBRARY_PATH=/3rdparty/local/lib:/3rdparty/local/lib64:/mbsim-env/local/lib:/mbsim-env/local/lib64 \
    PATH=$PATH:/3rdparty/local/bin:/mbsim-env/local/bin \
    XDG_RUNTIME_DIR=/run/user/$UID

# install everything from centos7 needed to run mbsim-env tools
RUN yum -y install epel-release
RUN yum -y install \
  hdf5 \
  boost-regex \
  xerces-c \
  lapack \
  boost-filesystem \
  boost-timer \
  libarchive \
  boost-date-time \
  mesa-libGLU \
  qt5-qtsvg \
  qt5-qtwebkit \
  xkeyboard-config \
  mesa-dri-drivers \
  xorg-x11-fonts-Type1 \
  urw-fonts
