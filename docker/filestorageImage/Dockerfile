FROM centos:centos7

# use other mirror since the official CentOS mirror is removed since 2014-07-01
#RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
# install software
RUN yum --setopt=skip_missing_names_on_install=False install -y epel-release && \
  yum --setopt=skip_missing_names_on_install=False install -y \
  python3 \
  openssh-server \
  rsync \
  rssh \
  && yum clean all

# openssh config
RUN ssh-keygen -A
RUN echo -e "Port 1122\nX11Forwarding no\nAllowTcpForwarding no" >> /etc/ssh/sshd_config
# rssh config
RUN echo -e "allowsftp\nallowrsync" >> /etc/rssh.conf

# copy context files
COPY docker/filestorageImage/entrypoint.py /context/entrypoint.py
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenvSecrets.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/filestorage" \
  org.label-schema.description="Django file storage using SFTP for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/filestorageImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser: with rssh as shell to restrict the ssh access; group rsshuser needed to execute rssh
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -s /usr/bin/rssh -u 1065 -g dockeruser -G rsshusers dockeruser && \
  mkdir -p /data/databasemedia /data/webserverstatic && \
  chown root:root /data && chown dockeruser:dockeruser /data/databasemedia /data/webserverstatic

#HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
#  CMD /usr/pgsql-13/bin/pg_isready || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
