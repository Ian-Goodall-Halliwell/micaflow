FROM ubuntu:bionic-20201119

USER root

ARG DEBIAN_FRONTEND="noninteractive"

ENV LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8" \
    ND_ENTRYPOINT="/neurodocker/startup.sh"

RUN apt-get update -qq && \
    apt-get install -y -q --no-install-recommends \
        apt-utils \
        bzip2 \
        ca-certificates \
        curl \
        locales \
        unzip \
        wget \
        git \
        python3 \
        python3-pip \
        python3-setuptools \
        openjdk-8-jdk \
        build-essential \
        gfortran \
        libatlas-base-dev \
        libblas-dev \
        liblapack-dev \
        bc \
        libgomp1 \
        libxmu6 \
        libxt6 \
        perl \
        tcsh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG="en_US.UTF-8" && \
    chmod 777 /opt && chmod a+s /opt && \
    mkdir -p /neurodocker && \
    if [ ! -f "$ND_ENTRYPOINT" ]; then \
        echo '#!/usr/bin/env bash' >> "$ND_ENTRYPOINT" && \
        echo 'set -e' >> "$ND_ENTRYPOINT" && \
        echo 'export USER="${USER:=`whoami`}"' >> "$ND_ENTRYPOINT" && \
        echo 'if [ -n "$1" ]; then "$@"; else /usr/bin/env bash; fi' >> "$ND_ENTRYPOINT"; \
    fi && \
    chmod -R 777 /neurodocker && chmod a+s /neurodocker

RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install numpy==1.19.5
RUN pip3 install nipype==1.7.1

# Install Nextflow
RUN wget -qO- https://get.nextflow.io -O /tmp/nextflow && \
    chmod +x /tmp/nextflow && \
    mv /tmp/nextflow /usr/local/bin/nextflow

COPY nextflow/micaflow.nf /opt/micaflow/nextflow/micaflow.nf

# Install ANTs
ENV ANTSPATH="/opt/ants-2.4.3/" \
    PATH="/opt/ants-2.4.3:$PATH"

RUN echo "Downloading ANTs ..." \
    && mkdir -p /opt/ants-2.3.4 \
    && curl -fsSL -o ants.zip https://github.com/ANTsX/ANTs/releases/download/v2.4.3/ants-2.4.3-ubuntu-20.04-X64-gcc.zip \
    && unzip ants.zip -d /opt \
    && mv /opt/ants-2.4.3/bin/* /opt/ants-2.4.3 \
    && rm ants.zip

# Install FreeSurfer
ENV FREESURFER_HOME="/opt/freesurfer-7.4.0" \
    PATH="/opt/freesurfer-7.4.0/bin:$PATH"
RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
           bc \
           libgomp1 \
           libxmu6 \
           libxt6 \
           perl \
           tcsh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Downloading FreeSurfer ..." \
    && mkdir -p /opt/freesurfer-7.4.0 \
    && curl -fsSL --retry 5 ftp://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.4.0/freesurfer-linux-ubuntu18_amd64-7.4.0.tar.gz \
    | tar -xz -C /opt/freesurfer-7.4.0 --strip-components 1 \
         --exclude='freesurfer/average/mult-comp-cor' \
         --exclude='freesurfer/lib/cuda' \
         --exclude='freesurfer/lib/qt' \
         --exclude='freesurfer/subjects/V1_average' \
         --exclude='freesurfer/subjects/bert' \
         --exclude='freesurfer/subjects/cvs_avg35' \
         --exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
         --exclude='freesurfer/subjects/fsaverage3' \
         --exclude='freesurfer/subjects/fsaverage4' \
         --exclude='freesurfer/subjects/fsaverage5' \
         --exclude='freesurfer/subjects/fsaverage6' \
         --exclude='freesurfer/subjects/fsaverage_sym' \
         --exclude='freesurfer/trctrain' \
    && sed -i '$isource "/opt/freesurfer-7.4.0/SetUpFreeSurfer.sh"' "$ND_ENTRYPOINT"

COPY /atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz /opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
COPY /atlas/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz /opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz

WORKDIR /home/mica

ENV MICAFLOW="/opt/micaflow"
ENV PROC="container_micaflow-v0.0.1"

ENTRYPOINT ["/opt/micaflow/nextflow/micaflow.nf"]