# use the build image as base
#mfmf use a common base for this image and mbsim-env-base regarding all yum installs
FROM centos:centos7

# install software
RUN yum install -y epel-release && yum install -y \
  httpd \
  mod_ssl \
  python2-certbot \
  cronie \
  && yum clean all
#mfmf mbsimwebapp is not possible till now must be installed and configured (maybe as another service)
 
# a webserver is running on port 80
EXPOSE 80/tcp 443/tcp

# copy cgi script
COPY buildSystem/scripts/cgi-bin/mbsimBuildServiceServer.py /var/www/cgi-bin/mbsimBuildServiceServer.py
# copy html script
COPY buildSystem/html /var/www/html/mbsim/html
# copy entrypoint
COPY docker/webServerImage/entrypoint.py /mbsim-build/build/docker/webServerImage/entrypoint.py
COPY docker/webServerImage/cron-daily.py /mbsim-build/build/docker/webServerImage/cron-daily.py

# configure web server
# add top level config (stored in docker/webServerImage/httpd_toplevel.conf)
COPY docker/webServerImage/httpd_toplevel.conf /tmp/httpd_toplevel.conf
RUN cat /tmp/httpd_toplevel.conf /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  mv /etc/httpd/conf/httpd.conf.new /etc/httpd/conf/httpd.conf && \
  rm -f /tmp/httpd_toplevel.conf
# replace <Directory "/var/www/html"> with docker/webServerImage/httpd_rootdir.conf
COPY docker/webServerImage/httpd_rootdir.conf /tmp/httpd_rootdir.conf
RUN set -o pipefail && \
  B=$(sed -rn '/^ *< *Directory +"\/var\/www\/html" *> *(#.*)?$/=' /etc/httpd/conf/httpd.conf | head -n 1); \
  O=$(sed -rn "$[$B+1],\$p" /etc/httpd/conf/httpd.conf | sed -rn '/^ *< *\/ *Directory *> *(#.*)?/=' | head -n 1); \
  sed -rn "1,$[$B-1]p;$[$B+$O+1],\$p" /etc/httpd/conf/httpd.conf > /etc/httpd/conf/httpd.conf.new && \
  cat /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf > /etc/httpd/conf/httpd.conf && \
  rm -f /etc/httpd/conf/httpd.conf.new /tmp/httpd_rootdir.conf

# webserver SSL
RUN set -o pipefail && \
  sed -r "s|^( *< *VirtualHost +_default_ *: *443 *> *(#.*)?)$|\1\nServerName \${MBSIMENVSERVERNAME}|" /etc/httpd/conf.d/ssl.conf > \
  /etc/httpd/conf.d/ssl.conf.new && \
  mv -f /etc/httpd/conf.d/ssl.conf.new /etc/httpd/conf.d/ssl.conf
COPY docker/webServerImage/mpm_prefork.conf /etc/httpd/cond.d/
COPY docker/webServerImage/le-redirect-mbsim-env.conf /etc/httpd/conf.d/

# set crontab for
# - cert updates
RUN echo '35 20,8 * * * /usr/bin/certbot-2 renew --webroot -w /var/www/html --post-hook "httpd -k graceful"' | crontab /dev/stdin

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/webserver" \
  org.label-schema.description="Webserver for MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/webserverImage" \
  org.label-schema.vendor="MBSim-Environment"

# add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir -p /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/buildsystemstate \
    /etc/letsencrypt /var/www/html/mbsim/releases /mfmf/BuildServiceConfig && \
  chown dockeruser:dockeruser /var/www/html/mbsim/linux64-ci /var/www/html/mbsim/linux64-dailydebug \
    /var/www/html/mbsim/linux64-dailyrelease /var/www/html/mbsim/buildsystemstate && \
  chown apache:apache /var/www/html/mbsim/releases && \
  chown dockeruser:apache /mfmf/BuildServiceConfig && chmod ug+rw /mfmf/BuildServiceConfig
  # chown root:roo /etc/letsencrypt # not needed

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/mbsim-build/build/docker/webServerImage/entrypoint.py"]
