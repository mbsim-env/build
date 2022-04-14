FROM centos:centos7

# install software
RUN yum --setopt=skip_missing_names_on_install=False install -y \
  python3 \
  openssh-server \
  && yum clean all

# openssh config
RUN ssh-keygen -A
RUN sed -i -re "s/^[ \t]*Subsystem[ \t].*$/Subsystem sftp internal-sftp/" /etc/ssh/sshd_config
RUN echo -e "Port 1122\nMatch User dockeruser\n  ChrootDirectory /jail\n  X11Forwarding no\n  AllowTcpForwarding no\n  ForceCommand internal-sftp" >> /etc/ssh/sshd_config

# copy context files
COPY docker/filestorageImage/entrypoint.py /context/entrypoint.py
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenvSecrets.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/filestorage" \
  org.label-schema.description="Django file storage using SFTP for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/filestorageImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser: /jail must be owned by root for ChrootDirectory of sshd
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir -p /jail/databasemedia && \
  chown root:root /jail && chown dockeruser:dockeruser /jail/databasemedia

#HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
#  CMD /usr/pgsql-13/bin/pg_isready || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
