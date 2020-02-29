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
  mingw64-qwt-qt5 \
  wine \
  mingw64-python3-numpy \
  mingw64-xerces-c \
  mingw64-libarchive \
  diffutils \
  && yum clean all
# bugfix for mingw64-python3
RUN ln -s /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/_sysconfigdata_m_win_.py \
          /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/_sysconfigdata_m_win32_.py
# bugfix for moc
RUN mv /usr/x86_64-w64-mingw32/bin/qt5/moc /usr/x86_64-w64-mingw32/bin/qt5/moc.org
COPY docker/buildwin64Image/moc /usr/x86_64-w64-mingw32/bin/qt5/moc
# bugfix for swig
COPY docker/buildwin64Image/swig.patch /context/swig.patch
RUN patch -d /usr/share/swig/4.0.1 -p0 < /context/swig.patch


############################


FROM fedoraBaseImage AS fedoraBaseImageFixes

# prepare for rpm rebuilds
RUN yum install -y yum-utils rpm-build
RUN mkdir /test
WORKDIR /test
RUN yumdownloader --source mingw64-python3 mingw64-python3-numpy
RUN rpm -ivh ./mingw-python3-*.src.rpm ./mingw-numpy-*.src.rpm
WORKDIR /root/rpmbuild/SPECS

# rebuild pyhton with some patches
RUN yum-builddep -y mingw64-python3
COPY docker/buildwin64Image/python-ctypes.patch /root/rpmbuild/SOURCES/python-ctypes.patch
COPY docker/buildwin64Image/python-ctypes-specs.patch /context/python-ctypes-specs.patch
RUN patch -d /root/rpmbuild/SPECS -p0 < /context/python-ctypes-specs.patch
RUN rpmbuild -ba mingw-python3.spec

# rebuild numpy to get some missing files
RUN yum-builddep -y mingw64-python3-numpy
RUN rpmbuild -ba mingw-numpy.spec


##################################################################################



FROM fedoraBaseImage AS fedoraBaseImage2

COPY --from=fedoraBaseImageFixes /root/rpmbuild/RPMS/noarch/mingw64-python3-3.7.4-2.fc31.noarch.rpm \
  /tmp/mingw64-python3-3.7.4-2.fc31.noarch.rpm
RUN rpm -e --nodeps mingw64-python3 && rpm -i /tmp/mingw64-python3-3.7.4-2.fc31.noarch.rpm
COPY --from=fedoraBaseImageFixes /root/rpmbuild/BUILD/numpy-1.17.0/build_py3_mingw64/src.linux-x86_64-3.7/numpy/core/include/numpy/_numpyconfig.h \
  /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/numpy/core/include/numpy/numpyconfig.h
COPY --from=fedoraBaseImageFixes /root/rpmbuild/BUILD/numpy-1.17.0/build_py3_mingw64/src.linux-x86_64-3.7/numpy/core/include/numpy/__multiarray_api.h \
  /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/numpy/core/include/numpy/__multiarray_api.h


##################################################################################


FROM fedoraBaseImage2 AS thirdpartyBuildImage

ARG JOBS=4

RUN yum --setopt=skip_missing_names_on_install=False -y install \
  wget \
  cmake \
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
RUN wine /usr/x86_64-w64-mingw32/sys-root/mingw/bin/python3.exe setup.py build && \
    wine /usr/x86_64-w64-mingw32/sys-root/mingw/bin/python3.exe setup.py install && wineserver -w
WORKDIR /3rdparty/sympy-build/sympy-$SYMPYVERSION
RUN mkdir -p /3rdparty/sympy-inst/Lib/site-packages
RUN wine /usr/x86_64-w64-mingw32/sys-root/mingw/bin/python3.exe setup.py build && \
    wine /usr/x86_64-w64-mingw32/sys-root/mingw/bin/python3.exe setup.py install && wineserver -w

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


FROM fedoraBaseImage2

COPY --from=thirdpartyBuildImage /3rdparty/local /3rdparty/local
COPY --from=thirdpartyBuildImage /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/mpmath \
  /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/mpmath
COPY --from=thirdpartyBuildImage /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/sympy \
  /usr/x86_64-w64-mingw32/sys-root/mingw/lib/python3.7/site-packages/sympy

# ccache
# enable swig interface to mbsim
# compile flags
ENV CCACHE_DIR=/mbsim-ccache \
    MBSIM_SWIG=1 \
    PATH=/usr/lib64/ccache:$PATH \
    WINEPATH="/usr/x86_64-w64-mingw32/sys-root/mingw/bin;/3rdparty/local/bin;/3rdparty/local/lib;" \
    MOC=/usr/x86_64-w64-mingw32/bin/qt5/moc.org \
    UIC=/usr/x86_64-w64-mingw32/bin/qt5/uic \
    RCC=/usr/x86_64-w64-mingw32/bin/qt5/rcc \
    CXXFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
    CFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
    FFLAGS="-g -O2 -gdwarf-2 -DNDEBUG" \
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
  mkdir /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state && \
  chown dockeruser:dockeruser /mbsim-env /mbsim-report /mbsim-ccache /mbsim-state

# copy
COPY buildScripts /mbsim-build/build/buildScripts
COPY docker/buildImage/buildSystemState.py /context/buildSystemState.py
COPY docker/buildImage/distribute.py /context/distribute.py
COPY docker/buildwin64Image/entrypoint.py /context/entrypoint.py
COPY docker/buildwin64Image/jni_md.h /context/java_jni/jni_md.h

# use a unpriviliged user to run the container
USER dockeruser:dockeruser

# init conf
RUN wine cmd echo && wineserver -w

# config ccache
RUN ccache -M 10G

# these are the default arguments when running the container
CMD []
# call this script when running the container
ENTRYPOINT ["/context/entrypoint.py"]
