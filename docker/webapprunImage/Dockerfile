ARG MBSIMENVTAGNAME=latest
FROM mbsimenv/build:$MBSIMENVTAGNAME

USER root:root

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  xfwm4 \
  bzip2 \
  && yum clean all

# compile splash program
COPY fullscreensplash.cc /context/fullscreensplash.cc
RUN g++ -fPIC -o /context/fullscreensplash -I/usr/include/qt5 /context/fullscreensplash.cc -lQt5Widgets -lQt5Core

COPY entrypoint.py /context/entrypoint.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webapprun" \
  org.label-schema.description="WebApp VNC server for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webapprunImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN mkdir -p /mbsim-env && chown root:root /mbsim-env

# proxy and
# prepare env for starting programs in the vnc server
ENV https_proxy=proxy:8888 \
  XAUTHORITY=/tmp/mbsimwebapp-xauth \
  DISPLAY=:1 \
  COIN_FULL_INDIRECT_RENDERING=1 \
  LIBGL_ALWAYS_INDIRECT=1 \
  QT_X11_NO_MITSHM=1

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# create XAUTH file
RUN touch /tmp/mbsimwebapp-xauth && chmod 600 /tmp/mbsimwebapp-xauth

USER root:root

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["timeout", "-k", "30s", "2h", "/context/entrypoint.py"]
