FROM centos:centos7

RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  python36-docker \
  git \
  && yum clean all

COPY builddockerImage/entrypoint.py /context/entrypoint.py
COPY setup.py /context/setup.py

ENTRYPOINT ["/context/entrypoint.py"]
