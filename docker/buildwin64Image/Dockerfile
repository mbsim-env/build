FROM fedora:31 AS fedoraBaseImage

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  git \
  ccache \
  patch \
  make \
  mingw64-gcc \
  mingw64-gcc-c++ \
  mingw64-gcc-gfortran \
  python3-requests \
  libtool automake autoconf \
  python3-pip \
  python3-numpy \
  python3-pygithub \
  mingw64-boost \
  doxygen \
  tigervnc-server \
  xalan-c \
  which \
  dos2unix \
  file \
  java-1.8.0-openjdk-devel \
  graphviz \
  swig \
  mingw64-qt5-qtsvg \
  mingw64-qt5-qtbase \
  python3-h5py \
  python3-pytz \
  python3-sqlparse \
  python3-psutil \
  mingw64-qwt-qt5 \
  mingw64-xerces-c \
  mingw64-libarchive \
  diffutils \
  python3-psycopg2 \
  cmake \
  ninja-build \
  sqlite \
  && dnf install -y 'dnf-command(config-manager)' \
  && dnf config-manager --add-repo https://dl.winehq.org/wine-builds/fedora/31/winehq.repo \
  && dnf install -y winehq-stable \
  && yum clean all
RUN python3 -m pip install --upgrade pip && pip3 install django==3.2 django-allauth==0.48 django-octicons==1.0 paramiko==2.9
# bugfix for moc
RUN mv /usr/x86_64-w64-mingw32/bin/qt5/moc /usr/x86_64-w64-mingw32/bin/qt5/moc.org
COPY docker/buildwin64Image/moc /usr/x86_64-w64-mingw32/bin/qt5/moc
# bugfix for swig
COPY docker/buildwin64Image/swig.patch /context/swig.patch
RUN patch -d /usr/share/swig/4.0.1 -p0 < /context/swig.patch


##################################################################################


FROM fedoraBaseImage AS thirdpartyBuildImage

ARG JOBS=4

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  wget \
  unzip \
  bzip2

RUN mkdir /3rdparty

# 3rd party

COPY docker/buildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake

# openblas (blas + lapack)
RUN mkdir /3rdparty/openblas-build
WORKDIR /3rdparty/openblas-build
RUN wget https://github.com/xianyi/OpenBLAS/releases/download/v0.3.21/OpenBLAS-0.3.21-x64.zip
RUN unzip OpenBLAS-0.3.21-x64.zip
RUN mkdir -p /3rdparty/local/bin/ /3rdparty/local/lib/ /3rdparty/local/include/ /3rdparty/local/lib/cmake/openblas/; \
  cp bin/libopenblas.dll /3rdparty/local/bin/; \
  cp lib/libopenblas.dll.a /3rdparty/local/lib/; \
  cp include/lapack.h include/lapacke_utils.h include/cblas.h include/lapacke_config.h include/f77blas.h include/openblas_config.h include/lapacke_mangling.h include/lapacke.h /3rdparty/local/include/; \
  cp lib/cmake/openblas/OpenBLASConfigVersion.cmake lib/cmake/openblas/OpenBLASConfig.cmake /3rdparty/local/lib/cmake/openblas/

# hdf5
# HDF5
WORKDIR /3rdparty
RUN git clone https://github.com/HDFGroup/hdf5.git
ARG HDF5BRANCH=hdf5-1_10_7
RUN (cd hdf5; git checkout $HDF5BRANCH)
RUN mkdir /3rdparty/hdf5-build
WORKDIR /3rdparty/hdf5-build
RUN cmake ../hdf5 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DBUILD_SHARED_LIBS=1 -DBUILD_STATIC_LIBS=0 -DHDF5_ENABLE_Z_LIB_SUPPORT=on -DZLIB_INCLUDE_DIR=/usr/x86_64-w64-mingw32/sys-root/mingw/include -DZLIB_LIBRARY=/usr/x86_64-w64-mingw32/sys-root/mingw/lib/libz.dll.a
RUN make -j $JOBS
RUN make install
# fixes and adaptions
# remove static programs and replace by shared
RUN for i in /3rdparty/local/bin/*-shared.exe; do mv -f $i ${i:0:-11}.exe; done
# remove static libs
RUN rm /3rdparty/local/lib/libhdf5.a /3rdparty/local/lib/libhdf5_cpp.a /3rdparty/local/lib/libhdf5_hl.a /3rdparty/local/lib/libhdf5_hl_cpp.a /3rdparty/local/lib/libhdf5_tools.a 
# fix link filenames
RUN ln -s /3rdparty/local/lib/hdf5.lib /3rdparty/local/lib/libhdf5.lib && \
    ln -s /3rdparty/local/lib/hdf5_cpp.lib /3rdparty/local/lib/libhdf5_cpp.lib

# python (mingw64-python has several problems)
WORKDIR /3rdparty
# we cannot download and install the python-3.6.8-amd64.exe since this fails using wine
# hence, python-3.6.8-amd64.exe is installed on a native windows machine and the result is zipped to python3.6.8.zip
COPY docker/buildwin64Image/python3.6.8.zip python3.6.8.zip
RUN mkdir -p /3rdparty/local/python-win64 && cd /3rdparty/local/python-win64 && unzip /3rdparty/python3.6.8.zip
# fix libfile name
RUN mv /3rdparty/local/python-win64/libs/python36.lib /3rdparty/local/python-win64/libs/libpython36.lib

# numpy
RUN wine /3rdparty/local/python-win64/python.exe -m pip install numpy==1.12.1 && wineserver -w

# mpmath/sympy
RUN wine /3rdparty/local/python-win64/python.exe -m pip install sympy==1.9 && wineserver -w

# octave
ARG OCTAVEVERSION=4.4.1
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.gz | tar -xz
RUN mkdir /3rdparty/octave-build
WORKDIR /3rdparty/octave-build
RUN ax_blas_integer_size=4 ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --with-blas="-L/3rdparty/local/lib -lopenblas" --with-lapack="-L/3rdparty/local/lib -lopenblas" --disable-readline
RUN make -j $JOBS
RUN make install
# fix octave: it is not initializing when runnig without a DISPLAY
RUN sed -i -re "s/^ *if *\((.*)&& *have_window_system *\( *\)(.*)$/if(have_window_system() \&\& \1\2/" \
  /3rdparty/local/lib/octave/$OCTAVEVERSION/oct/x86_64-w64-mingw32/PKG_ADD && \
  sed -i -re "s/^.*gnuplot.*$/% gnuplot is removed/" \
  /3rdparty/local/lib/octave/$OCTAVEVERSION/oct/x86_64-w64-mingw32/PKG_ADD

# coin
ARG COINBRANCH=CI-builds
WORKDIR /3rdparty
RUN git clone https://github.com/coin3d/coin.git
WORKDIR /3rdparty/coin
RUN git checkout $COINBRANCH && git submodule init && git submodule update
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DBoost_INCLUDE_DIR="/usr/x86_64-w64-mingw32/sys-root/mingw/include" -DSIM_TIMEVAL_TV_SEC_T=time_t -DSIM_TIMEVAL_TV_USEC_T=time_t ../coin
RUN make -j $JOBS
RUN make install

# soqt
ARG SOQTBRANCH=CI-builds
WORKDIR /3rdparty
RUN git clone https://github.com/coin3d/soqt.git
WORKDIR /3rdparty/soqt
RUN git checkout $SOQTBRANCH && git submodule init && git submodule update
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DQt5_DIR=/usr/x86_64-w64-mingw32/sys-root/mingw/lib/cmake/Qt5 ../soqt
RUN make -j $JOBS
RUN make install

# spooles
WORKDIR /3rdparty
RUN wget http://www.netlib.org/linalg/spooles/spooles.2.2.tgz
RUN mkdir /3rdparty/spooles-build
WORKDIR /3rdparty/spooles-build
RUN tar -xzf ../spooles.2.2.tgz
RUN sed -i -re "s/^ *CC *=.*$/CC=x86_64-w64-mingw32-gcc/;s/^ *OPTLEVEL *=.*$/OPTLEVEL=-O2/;s/^ *AR *=.*$/AR=x86_64-w64-mingw32-ar/" Make.inc
RUN make -j $JOBS lib
RUN cp spooles.a /3rdparty/local/lib
RUN mkdir /3rdparty/local/include/spooles
RUN find -name "*.h" | xargs tar -c | tar -x -C /3rdparty/local/include/spooles

# arpack
WORKDIR /3rdparty
RUN git clone https://github.com/opencollab/arpack-ng.git
WORKDIR /3rdparty/arpack-ng
ARG ARPACKBRANCH=3.8.0
RUN git checkout $ARPACKBRANCH
RUN mkdir /3rdparty/arpack-build
WORKDIR /3rdparty/arpack-build
RUN cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2" -DICB=1 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DBLAS_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a -DLAPACK_LIBRARIES=/3rdparty/local/lib/libopenblas.dll.a ../arpack-ng
RUN make -j $JOBS
RUN make install


##################################################################################


FROM fedoraBaseImage

COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local
COPY docker/buildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake

# ccache
# enable swig interface to mbsim
# compile flags
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    PATH=/usr/lib64/ccache:$PATH \
    WINEPATH="/usr/x86_64-w64-mingw32/sys-root/mingw/bin;/3rdparty/local/bin;/3rdparty/local/lib;/3rdparty/local/python-win64;/3rdparty/local/python-win64/Lib/site-packages/numpy/core;/3rdparty/local/python-win64/Lib/site-packages/numpy/.libs" \
    MOC=/usr/x86_64-w64-mingw32/bin/qt5/moc.org \
    UIC=/usr/x86_64-w64-mingw32/bin/qt5/uic \
    RCC=/usr/x86_64-w64-mingw32/bin/qt5/rcc \
    PKG_CONFIG_PATH=/3rdparty/local/lib/pkgconfig:/usr/x86_64-w64-mingw32/sys-root/mingw/lib/pkgconfig \
    PLATFORM=Windows \
    CXX=x86_64-w64-mingw32-g++

# set labels
LABEL org.label-schema.schema-version="1.0" \
  org.label-schema.name="mbsimenv/buildwin64" \
  org.label-schema.description="Automatic build (win64) for the MBSim-Environment." \
  org.label-schema.vcs-url="https://github.com/mbsim-env/build/tree/master/docker/buildwin64Image" \
  org.label-schema.vendor="MBSim-Environment"

# Add user dockeruser, create volumes and set volume ownership and permissions
RUN groupadd -g 1065 dockeruser && useradd --no-log-init -u 1065 -g dockeruser dockeruser && \
  mkdir /mbsim-env /mbsim-ccache && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-ccache

# configure wine
COPY docker/buildwin64Image/wine.inf /context/wine.inf
RUN P=$(winepath -w /3rdparty/local/python-win64 | sed -re 's+\\+\\\\+g'); \
    sed -re "s+%_PYTHONHOME_%+$P+" /context/wine.inf >> /opt/wine-stable/share/wine/wine.inf

# init conf
USER dockeruser:dockeruser
RUN wine cmd /c echo dummy && wineserver -w
USER root:root

# copy
COPY misc /mbsim-build/build/misc
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildwin64Image/entrypoint.py /context/entrypoint.py
COPY docker/buildwin64Image/jni_md.h /context/java_jni/jni_md.h
COPY django/mbsimenv/build.py           /context/mbsimenv/build.py                    
COPY django/mbsimenv/runexamples.py     /context/mbsimenv/runexamples.py              
COPY django/mbsimenv/mbsimenvSecrets.py /context/mbsimenv/mbsimenvSecrets.py          
COPY django/mbsimenv/mbsimenv           /context/mbsimenv/mbsimenv                        
COPY django/mbsimenv/base               /context/mbsimenv/base                        
COPY django/mbsimenv/builds             /context/mbsimenv/builds                      
COPY django/mbsimenv/runexamples        /context/mbsimenv/runexamples                 
COPY django/mbsimenv/service            /context/mbsimenv/service                     

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
