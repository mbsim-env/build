FROM centos:centos7

# install software
RUN yum --setopt=skip_missing_names_on_install=False install -y epel-release centos-release-scl && \
  yum --setopt=skip_missing_names_on_install=False install -y \
  texlive-latex-bin-bin \
  texlive-bibtex-bin \
  texlive-collection-fontsrecommended \
  texlive-subfigure \
  texlive-pdftex-def \
  texlive-epstopdf-bin \
  ghostscript \
  rh-git227-git \
  python36 \
  python36-pytz \
  python3-psycopg2 \
  && yum clean all
RUN python3 -m pip install --upgrade pip && pip3 install django==3.2 django-octicons==1.0 paramiko==2.9
# config git2.27
ENV PATH=/opt/rh/rh-git227/root/usr/bin:$PATH \
    LD_LIBRARY_PATH=/opt/rh/httpd24/root/usr/lib64:$LD_LIBRARY_PATH

# copy context files
COPY docker/builddocImage/entrypoint.py /context/entrypoint.py
COPY django/mbsimenv /context/mbsimenv

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/builddoc" \
  org.label-schema.description="Build latex documentation for MBSim-Env." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/builddocImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env && \
  chown dockeruser:dockeruser /mbsim-env

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
