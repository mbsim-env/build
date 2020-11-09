FROM fedora:31 AS fedoraBaseImage

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  git \
  ccache \
  patch \
  make \
  mingw64-gcc \
  mingw64-gcc-c++ \
  mingw64-gcc-gfortran \
  wine \
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
  mingw64-qwt-qt5 \
  wine \
  mingw64-xerces-c \
  mingw64-libarchive \
  diffutils \
  python3-psycopg2 \
  cmake \
  ninja-build \
  && yum clean all
RUN pip3 install django django-octicons
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
  bzip2 \
  mercurial

RUN mkdir /3rdparty

# 3rd party

COPY docker/buildwin64Image/toolchain-mingw64.cmake /context/toolchain-mingw64.cmake

# lapack
ARG LAPACKVERSION=3.4.2
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - http://www.netlib.org/lapack/lapack-$LAPACKVERSION.tgz | tar -xz
RUN mkdir /3rdparty/lapack-build
WORKDIR /3rdparty/lapack-build
RUN cmake ../lapack-$LAPACKVERSION -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local
RUN make -j $JOBS
RUN make install

# hdf5
ARG HDF5VERSION=1_8_12
WORKDIR /3rdparty
RUN git clone --depth 1 -b hdf5-$HDF5VERSION https://bitbucket.hdfgroup.org/scm/hdffv/hdf5.git
WORKDIR /3rdparty/hdf5
RUN git checkout -b test
COPY docker/buildwin64Image/hdf5.patch /context/hdf5.patch
RUN git apply /context/hdf5.patch
RUN mkdir /3rdparty/hdf5-build
WORKDIR /3rdparty/hdf5-build
RUN cmake ../hdf5 -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DMSVC=TRUE -DHDF5_BUILD_CPP_LIB=ON -DBUILD_SHARED_LIBS=1
RUN make -j $JOBS
RUN make install
RUN ln -s /3rdparty/local/lib/hdf5.lib /3rdparty/local/lib/libhdf5.lib && \
    ln -s /3rdparty/local/lib/hdf5_cpp.lib /3rdparty/local/lib/libhdf5_cpp.lib

# python (mingw64-python has several problems)
ARG PYTHONVERSION=3.4.4
WORKDIR /3rdparty
RUN wget https://www.python.org/ftp/python/$PYTHONVERSION/python-$PYTHONVERSION.amd64.msi
RUN wine msiexec -i python-$PYTHONVERSION.amd64.msi -q n TARGETDIR="$(winepath -w /3rdparty/local/python-win64)" && wineserver -w
# fix libfile name
RUN mv /3rdparty/local/python-win64/libs/python34.lib /3rdparty/local/python-win64/libs/libpython34.lib

# numpy
ARG NUMPYVERSION=1.15.0
WORKDIR /3rdparty
RUN wget https://files.pythonhosted.org/packages/11/9f/f7550ba7d6ea7d1da16ac2069157b42d225b02b47e4c30ccc1c5b6be3b8f/numpy-$NUMPYVERSION-cp34-none-win_amd64.whl
RUN mkdir /3rdparty/numpy-build
WORKDIR /3rdparty/numpy-build
RUN unzip ../numpy-$NUMPYVERSION-cp34-none-win_amd64.whl
RUN cp -a numpy /3rdparty/local/python-win64/Lib/site-packages/.

# mpmath/sympy
ARG MPMATHVERSION=1.1.0
ARG SYMPYVERSION=1.4
WORKDIR /3rdparty
RUN wget https://files.pythonhosted.org/packages/ca/63/3384ebb3b51af9610086b23ea976e6d27d6d97bf140a76a365bd77a3eb32/mpmath-$MPMATHVERSION.tar.gz \
  && wget https://github.com/sympy/sympy/releases/download/sympy-$SYMPYVERSION/sympy-$SYMPYVERSION.tar.gz
RUN mkdir /3rdparty/mpmath-build /3rdparty/mpmath-local /3rdparty/sympy-build /3rdparty/sympy-local
WORKDIR /3rdparty/mpmath-build
RUN tar -xzf ../mpmath-$MPMATHVERSION.tar.gz
WORKDIR /3rdparty/sympy-build
RUN tar -xzf ../sympy-$SYMPYVERSION.tar.gz
WORKDIR /3rdparty/mpmath-build/mpmath-$MPMATHVERSION
RUN wine /3rdparty/local/python-win64/python.exe setup.py build && \
    wine /3rdparty/local/python-win64/python.exe setup.py install && wineserver -w
WORKDIR /3rdparty/sympy-build/sympy-$SYMPYVERSION
RUN mkdir -p /3rdparty/sympy-inst/Lib/site-packages
RUN wine /3rdparty/local/python-win64/python.exe setup.py build && wineserver -w
RUN PYTHONPATH="$(winepath -w /3rdparty/sympy-inst/Lib/site-packages)" wine /3rdparty/local/python-win64/python.exe \
    setup.py install --prefix="$(winepath -w /3rdparty/sympy-inst)" && \
    wineserver -w
RUN unzip -d /3rdparty/local/python-win64/Lib/site-packages dist/sympy-$SYMPYVERSION-py3.4.egg

# octave
ARG OCTAVEVERSION=4.4.1
WORKDIR /3rdparty
RUN set -o pipefail && \
  wget -q -O - https://ftp.gnu.org/gnu/octave/octave-$OCTAVEVERSION.tar.gz | tar -xz
RUN mkdir /3rdparty/octave-build
WORKDIR /3rdparty/octave-build
RUN ax_blas_integer_size=4 ../octave-$OCTAVEVERSION/configure --enable-shared --disable-static --build=x86_64-redhat-linux --host=x86_64-w64-mingw32 --prefix=/3rdparty/local --disable-java --disable-gui --without-opengl --with-blas="-L/3rdparty/local/lib -lblas" --with-lapack="-L/3rdparty/local/lib -llapack" --disable-readline
RUN make -j $JOBS
RUN make install
# fix octave: it is not initializing when runnig without a DISPLAY
RUN sed -i -re "s/^ *if *\((.*)&& *have_window_system *\( *\)(.*)$/if(have_window_system() \&\& \1\2/" \
  /3rdparty/local/lib/octave/$OCTAVEVERSION/oct/x86_64-w64-mingw32/PKG_ADD && \
  sed -i -re "s/^.*gnuplot.*$/% gnuplot is removed/" \
  /3rdparty/local/lib/octave/$OCTAVEVERSION/oct/x86_64-w64-mingw32/PKG_ADD

# coin
ARG COINBRANCH=Coin-4.0.0
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/coin -r $COINBRANCH
WORKDIR /3rdparty/coin
RUN mkdir /3rdparty/coin-build
WORKDIR /3rdparty/coin-build
RUN cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DBoost_INCLUDE_DIR="/usr/x86_64-w64-mingw32/sys-root/mingw/include" -DSIM_TIMEVAL_TV_SEC_T=time_t -DSIM_TIMEVAL_TV_USEC_T=time_t ../coin
RUN make -j $JOBS
RUN make install

# soqt
ARG SOQTBRANCH=SoQt-1.6.0
WORKDIR /3rdparty
RUN hg clone https://bitbucket.org/Coin3D/soqt -r $SOQTBRANCH
RUN mkdir /3rdparty/soqt-build
WORKDIR /3rdparty/soqt-build
RUN cmake -DCMAKE_INSTALL_PREFIX=/3rdparty/local -DCMAKE_CXX_FLAGS="-g -O2 -fpermissive" -DCMAKE_TOOLCHAIN_FILE=/context/toolchain-mingw64.cmake -DQt5_DIR=/usr/x86_64-w64-mingw32/sys-root/mingw/lib/cmake/Qt5 ../soqt
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
  mkdir /mbsim-env /mbsim-ccache /databasemedia && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-ccache /databasemedia

# configure wine
COPY docker/buildwin64Image/wine.inf /context/wine.inf
RUN P=$(winepath -w /3rdparty/local/python-win64 | sed -re 's+\\+\\\\+g'); \
    sed -re "s+%_PYTHONHOME_%+$P+" /context/wine.inf >> /usr/share/wine/wine.inf

# copy
COPY misc /mbsim-build/build/misc
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildwin64Image/entrypoint.py /context/entrypoint.py
COPY docker/buildwin64Image/jni_md.h /context/java_jni/jni_md.h
COPY django/mbsimenv /context/mbsimenv

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# init conf
RUN wine cmd echo && wineserver -w

# config ccache
RUN ccache -M 20G

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
