FROM centos:centos7 AS webapp

# use other mirror since the official CentOS mirror is removed since 2014-07-01
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  python36-numpy \
  python36-docker \
  python3-setuptools \
  python3-psutil \
  && yum clean all



FROM webapp AS websockify

ARG WEBSOCKIFYBRANCH=518e6e0e560e71b3176b54cc4b2023f07efc9d57

RUN yum --setopt=skip_missing_names_on_install=False -y install git && yum clean all

# install websockify
RUN mkdir /3rdparty
WORKDIR /3rdparty
RUN git clone https://github.com/novnc/websockify.git
WORKDIR /3rdparty/websockify
RUN git checkout $WEBSOCKIFYBRANCH
COPY webappImage/websockify.patch /context/websockify.patch
RUN git apply /context/websockify.patch
RUN python3 setup.py bdist_egg



FROM webapp

COPY --from=websockify /3rdparty/websockify/dist/websockify-0.8.0-py3.6.egg /3rdparty/websockify/dist/websockify-0.8.0-py3.6.egg
RUN easy_install-3.6 /3rdparty/websockify/dist/websockify-0.8.0-py3.6.egg

COPY webappImage/entrypoint.py /context/entrypoint.py
COPY webappImage/webapprun.py /context/webapprun.py
COPY setup.py /context/setup.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webapp" \
  org.label-schema.description="WebApp for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webappImage" \
  org.label-schema.vendor="MBSim-Environment"

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD curl -i -N -d dummydata -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Host: webapp" \
  -H "Origin: http://webapp:10080" http://webapp:10080 || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
