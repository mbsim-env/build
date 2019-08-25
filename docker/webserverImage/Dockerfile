# get noVNC
FROM centos:centos7 AS temp
ARG NOVNCBRANCH=v0.6.2
RUN yum --setopt=skip_missing_names_on_install=False -y install git && yum clean all
# install noVNC (the package from yum is to old)
WORKDIR /tmp
RUN git clone https://github.com/novnc/noVNC.git
WORKDIR /tmp/noVNC
RUN git checkout $NOVNCBRANCH



# use the build image as base
FROM centos:centos7

# install software
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release centos-release-scl && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  httpd \
  mod_ssl \
  rh-python36-mod_wsgi \
  python2-certbot \
  cronie \
  python36-docker \
  && yum clean all

# a webserver is running on port 80
EXPOSE 80/tcp 443/tcp

COPY --from=temp /tmp/noVNC/include /var/www/html/noVNC/include

# copy html script
COPY webserverImage/html /var/www/html/mbsim/html
# copy entrypoint
COPY webserverImage/entrypoint.py /context/entrypoint.py
COPY webserverImage/cron-daily.py /context/cron-daily.py
COPY webserverImage/cron-ci.py /context/cron-ci.py
COPY setup.py /context/setup.py

# configure web server
# add top level config (stored in docker/webserverImage/httpd_toplevel.conf)
COPY webserverImage/conf/httpd_toplevel.conf /tmp/httpd_toplevel.conf
RUN cat /tmp/httpd_toplevel.conf /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  mv /etc/httpd/conf/httpd.conf.new /etc/httpd/conf/httpd.conf && \
  rm -f /tmp/httpd_toplevel.conf
# replace <Directory "/var/www/html"> with docker/webserverImage/httpd_rootdir.conf
COPY webserverImage/conf/httpd_rootdir.conf /tmp/httpd_rootdir.conf
RUN set -o pipefail && \
  B=$(sed -rn '/^ *< *Directory +"\/var\/www\/html" *> *(#.*)?$/=' /etc/httpd/conf/httpd.conf | head -n 1); \
  O=$(sed -rn "$[$B+1],\$p" /etc/httpd/conf/httpd.conf | sed -rn '/^ *< *\/ *Directory *> *(#.*)?/=' | head -n 1); \
  sed -rn "1,$[$B-1]p;$[$B+$O+1],\$p" /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  cat /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf > /etc/httpd/conf/httpd.conf && \
  rm -f /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf

# configure wsgi
RUN cp /opt/rh/httpd24/root/usr/lib64/httpd/modules/mod_rh-python36-wsgi.so /lib64/httpd/modules && \
    cp /opt/rh/httpd24/root/etc/httpd/conf.modules.d/10-rh-python36-wsgi.conf /etc/httpd/conf.modules.d
COPY webserverImage/wsgi/mbsimBuildServiceServer.py /var/www/mbsimBuildServiceServer.py
RUN echo "WSGIScriptAlias /wsgi/mbsimBuildServiceServer.py /var/www/mbsimBuildServiceServer.py" >> /etc/httpd/conf.modules.d/10-wsgi.conf

# webserver SSL
RUN set -o pipefail && \
  sed -i -r "s|^( *< *VirtualHost +_default_ *: *443 *> *(#.*)?)$|\1\nServerName \${MBSIMENVSERVERNAME}\n|" /etc/httpd/conf.d/ssl.conf
COPY webserverImage/conf/mpm_prefork.conf /etc/httpd/cond.d/
COPY webserverImage/conf/le-redirect-mbsim-env.conf /etc/httpd/conf.d/

# set crontab for
# - cert updates (once a day at arbitary time)
RUN echo -e 'SHELL=/bin/bash\n\
1 0 * * * python3 -c "import time; import random; time.sleep(random.randint(0,24*60*60-100))"; \
/usr/bin/certbot-2 renew --webroot -w /var/www/html --post-hook "httpd -k graceful" 2> >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/2) > >(sed -re "s/^/CERTBOT: /" > /proc/1/fd/1)' | crontab /dev/stdin

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webserver" \
  org.label-schema.description="Webserver for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webserverImage" \
  org.label-schema.vendor="MBSim-Environment"

# Check apache user and group id (must be in sync with the one in buildImage)
# Add user dockeruser, create volumes and set volume ownership and permissions
RUN test $(id -u apache) -eq 48 && test $(id -g apache) -eq 48 && \
  groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir -p /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/win64-dailyrelease /var/www/html/mbsim/buildsystemstate \
    /etc/letsencrypt /var/www/html/mbsim/releases /mbsim-config && \
  chown dockeruser:dockeruser /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/win64-dailyrelease /var/www/html/mbsim/buildsystemstate && \
  chown apache:apache /var/www/html/mbsim/releases && \
  chown dockeruser:apache /mbsim-config && chmod ug+rw /mbsim-config
  # chown root:root /etc/letsencrypt # not needed

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD curl -f https://${MBSIMENVSERVERNAME} || exit 1

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
