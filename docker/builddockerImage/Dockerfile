FROM centos:centos7

RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  python36 \
  python36-docker \
  python36-pytz \
  python3-psycopg2 \
  git \
  && yum clean all
RUN pip3 install django django-octicons

COPY docker/builddockerImage/entrypoint.py /context/entrypoint.py
COPY docker/setup.py /context/setup.py
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenv/mbsimenvSecrets.py
COPY django/mbsimenv/mbsimenv           /context/mbsimenv/mbsimenv
COPY django/mbsimenv/base               /context/mbsimenv/base
COPY django/mbsimenv/service            /context/mbsimenv/service

ENTRYPOINT ["/context/entrypoint.py"]
