FROM centos:centos7

# install software
RUN yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm && \
  yum --setopt=skip_missing_names_on_install=False install -y \
  postgresql13-server \
  python3 \
  && yum clean all

# copy context files
COPY docker/databaseImage/entrypoint.py /context/entrypoint.py
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenvSecrets.py

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/database" \
  org.label-schema.description="PostgreSQL database server for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/databaseImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /database && \
  chown dockeruser:dockeruser /database /var/run/postgresql

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# init database (the password is changed during entrypoint.py)
RUN echo dummy | /usr/pgsql-13/bin/initdb --pgdata=/database --auth=md5 --username=mbsimenvuser --pwfile=/dev/stdin
# configure database
RUN grep -v "^ *timezone *=.*$" /database/postgresql.conf > /database/postgresql.conf2 && \
    mv /database/postgresql.conf2 /database/postgresql.conf
RUN echo "client_encoding = 'UTF8'" >> /database/postgresql.conf && \
    echo "default_transaction_isolation = 'read committed'" >> /database/postgresql.conf && \
    echo "listen_addresses = '*'" >> /database/postgresql.conf && \
    echo "timezone = 'UTC'" >> /database/postgresql.conf
RUN echo "host all all localhost md5" >> /database/pg_hba.conf
# create django database
RUN /usr/pgsql-13/bin/postgres -D /database -h localhost & \
    while ! PGPASSWORD=dummy /usr/pgsql-13/bin/psql -l -h localhost --username=mbsimenvuser &> /dev/null; do sleep 0.5; done && \
    PGPASSWORD=dummy createdb -h localhost --username=mbsimenvuser mbsimenv-service-database && \
    kill %% && rm -f /database/postmaster.pid

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD /usr/pgsql-13/bin/pg_isready || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
