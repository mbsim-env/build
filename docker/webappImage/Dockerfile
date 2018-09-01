FROM centos:centos7

ARG WEBSOCKIFYBRANCH=518e6e0e560e71b3176b54cc4b2023f07efc9d57

RUN yum install -y git
RUN yum install -y python-setuptools
RUN yum install -y numpy
RUN yum install -y python-requests

# websockify
RUN mkdir /3rdparty
WORKDIR /3rdparty
RUN git clone https://github.com/novnc/websockify.git
WORKDIR /3rdparty/websockify
RUN git checkout $WEBSOCKIFYBRANCH
RUN python setup.py install

COPY entrypoint.py /opt/entrypoint.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webapp" \
  org.label-schema.description="WebApp for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webappImage" \
  org.label-schema.vendor="MBSim-Environment"

#mfmf run as what user?

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/opt/entrypoint.py"]
