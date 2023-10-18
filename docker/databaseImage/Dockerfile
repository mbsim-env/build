FROM centos:centos7

# install software
RUN yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm && \
  yum install -y epel-release && \
  yum --setopt=skip_missing_names_on_install=False install -y \
  postgresql13-server \
  python3 \
  python36-pygithub \
  python36-pytz \
  python36-defusedxml \
  python36-docker \
  python3-psycopg2 \
  cronie \
  && yum clean all
RUN python3 -m pip install --upgrade pip && pip3 install django==3.2 django-allauth==0.47 django-octicons==1.0 h5py==2.9.0

# copy context files
COPY docker/databaseImage/entrypoint.py /context/entrypoint.py
COPY django/mbsimenv /context/mbsimenv

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/database" \
  org.label-schema.description="PostgreSQL database server for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/databaseImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /database /database.org && \
  chown dockeruser:dockeruser /database /database.org /var/run/postgresql

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# set crontab for to update certs (updated by the webserver)
RUN echo '1 0 * * * /usr/pgsql-13/bin/pg_ctl -D /database reload' | crontab /dev/stdin

# init database (the password is changed during entrypoint.py)
RUN echo dummy | /usr/pgsql-13/bin/initdb --pgdata=/database --auth=md5 --username=mbsimenvuser --pwfile=/dev/stdin
# configure database
RUN grep -v "^ *timezone *=.*$" /database/postgresql.conf > /database/postgresql.conf2 && \
    mv /database/postgresql.conf2 /database/postgresql.conf
RUN echo "client_encoding = 'UTF8'" >> /database/postgresql.conf && \
    echo "default_transaction_isolation = 'read committed'" >> /database/postgresql.conf && \
    echo "listen_addresses = '*'" >> /database/postgresql.conf && \
    echo "timezone = 'UTC'" >> /database/postgresql.conf
# allow database (=localhost) to connect to postgres
RUN sed -i -re "s/^ *host /hostnossl /" /database/pg_hba.conf
RUN echo "hostnossl mbsimenv-service-database mbsimenvuser database md5" >> /database/pg_hba.conf
RUN cp /database/postgresql.conf /database.org/postgresql.conf 
RUN cp /database/pg_hba.conf /database.org/pg_hba.conf 
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
