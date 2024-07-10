FROM centos:centos7

# use other mirror since the official CentOS mirror is removed since 2014-07-01
#RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo && sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo && sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo
# install tinyproxy
RUN yum --setopt=skip_missing_names_on_install=False -y install epel-release && \
  yum --setopt=skip_missing_names_on_install=False -y install \
  python36 \
  tinyproxy \
  && yum clean all

# allow connection from everywhere
RUN sed -i -re "s/^( *Allow .*)/#\1/" /etc/tinyproxy/tinyproxy.conf

# configure tinyproxy
RUN echo -e '\
Filter "/etc/tinyproxy/filter"\n\
FilterCaseSensitive Yes\n\
FilterDefaultDeny Yes\n\
FilterURLs No\n\
FilterExtended Yes\n\
' >> /etc/tinyproxy/tinyproxy.conf

COPY entrypoint.py /context/entrypoint.py

HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
  CMD curl -I --proxy proxy:8888 https://${MBSIMENVSERVERNAME} || exit 1

# start tinyproxy
ENTRYPOINT ["/context/entrypoint.py"]
CMD [""]
