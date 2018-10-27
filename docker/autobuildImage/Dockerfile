# use the build image as base
ARG FROMTAG=latest
FROM mbsimenv/build:$FROMTAG

# install software
RUN yum install -y \
  python-requests \
  texlive-latex-bin-bin \
  texlive-bibtex-bin \
  texlive-collection-fontsrecommended \
  texlive-subfigure \
  texlive-pdftex-def \
  texlive-epstopdf-bin \
  ghostscript \
  && yum clean all

# copy build repo
COPY docker/autobuildImage/entrypoint.py /context/entrypoint.py
COPY docker/autobuildImage/builddoc.py /context/builddoc.py
COPY docker/autobuildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/autobuildImage/distribute.py /context/distribute.py
COPY buildScripts /mbsim-build/build/buildScripts

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/autobuild" \
  org.label-schema.description="Automatic build (CI and daily) for the MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/autobuildImage" \
  org.label-schema.vendor="MBSim-Environment"

# Add apache group and user (just needed to set proper mode on /mbsim-config
# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 48 -r apache && useradd --no-log-init -u 48 -g apache -c "Apache" -s /sbin/nologin -r -d /usr/share/httpd apache && \
  groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state /mbsim-config && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:apache /mbsim-config && chmod ug+rw /mbsim-config

# ccache
# enable swig interface to mbsim
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
