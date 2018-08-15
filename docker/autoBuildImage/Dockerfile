# use the build image as base
FROM mbsimenv/build

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

# ccache
ENV CCACHE_DIR=/mbsim-ccache

# copy build repo
COPY docker/autoBuildImage/entrypoint.py /mbsim-build/build/docker/autoBuildImage/entrypoint.py
COPY buildScripts /mbsim-build/build/buildScripts
COPY buildSystem/scripts /mbsim-build/build/buildSystem/scripts

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/autobuild" \
  org.label-schema.description="Automatic build (CI and daily) for the MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/autobuildImage" \
  org.label-schema.vendor="MBSim-Environment"

# use a unpriviliged user to run the container
RUN groupadd -r dockeruser && useradd --no-log-init -r -g dockeruser dockeruser
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/mbsim-build/build/docker/autoBuildImage/entrypoint.py"]
