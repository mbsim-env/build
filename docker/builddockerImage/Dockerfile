FROM centos:centos7

# use other mirror since the official CentOS mirror is removed since 2014-07-01
#RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release centos-release-scl && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  python36 \
  python36-docker \
  python36-pytz \
  python3-psycopg2 \
  python3-psutil \
  rh-git227-git \
  && yum clean all
RUN python3 -m pip install --upgrade pip && pip3 install django==3.2 django-allauth==0.48 django-octicons==1.0 paramiko==2.9
# config git2.27
ENV PATH=/opt/rh/rh-git227/root/usr/bin:$PATH \
    LD_LIBRARY_PATH=/opt/rh/httpd24/root/usr/lib64:$LD_LIBRARY_PATH

COPY docker/builddockerImage/entrypoint.py /context/entrypoint.py
COPY docker/setup.py /context/setup.py
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenv/mbsimenvSecrets.py
COPY django/mbsimenv/mbsimenv           /context/mbsimenv/mbsimenv
COPY django/mbsimenv/base               /context/mbsimenv/base
COPY django/mbsimenv/service            /context/mbsimenv/service

ENTRYPOINT ["/context/entrypoint.py"]
