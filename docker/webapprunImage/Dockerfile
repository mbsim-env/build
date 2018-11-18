ARG FROMTAG=latest
FROM mbsimenv/build:$FROMTAG

USER root:root

RUN yum install -y \
  xfwm4 \
  && yum clean all

COPY entrypoint.py /context/entrypoint.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webapprun" \
  org.label-schema.description="WebApp VNC server for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webapprunImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN mkdir -p /mbsim-env-linux64-ci /mbsim-env-linux64-dailydebug /mbsim-env-linux64-dailyrelease /mbsim-env-win64-dailyrelease && \
  chown dockeruser:dockeruser /mbsim-env-linux64-ci /mbsim-env-linux64-dailydebug /mbsim-env-linux64-dailyrelease /mbsim-env-win64-dailyrelease

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

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
