FROM ubuntu:bionic-20201119

USER root

ARG DEBIAN_FRONTEND="noninteractive"

ENV LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8" \
    ND_ENTRYPOINT="/neurodocker/startup.sh"

RUN export ND_ENTRYPOINT="/neurodocker/startup.sh" \
    && apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG="en_US.UTF-8" \
    && chmod 777 /opt && chmod a+s /opt \
    && mkdir -p /neurodocker \
    && if [ ! -f "$ND_ENTRYPOINT" ]; then \
         echo '#!/usr/bin/env bash' >> "$ND_ENTRYPOINT" \
    &&   echo 'set -e' >> "$ND_ENTRYPOINT" \
    &&   echo 'export USER="${USER:=`whoami`}"' >> "$ND_ENTRYPOINT" \
    &&   echo 'if [ -n "$1" ]; then "$@"; else /usr/bin/env bash; fi' >> "$ND_ENTRYPOINT"; \
    fi \
    && chmod -R 777 /neurodocker && chmod a+s /neurodocker

# Install ANTs
ENV ANTSPATH="/opt/ants-2.3.4/" \
    PATH="/opt/ants-2.3.4:$PATH"
RUN  echo "Downloading ANTs ..." \
    && mkdir -p /opt/ants-2.3.4 \
    && curl -fsSL https://dl.dropbox.com/s/gwf51ykkk5bifyj/ants-Linux-centos6_x86_64-v2.3.4.tar.gz \
    | tar -xz -C /opt/ants-2.3.4 --strip-components 1

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

RUN pip3 install setuptools wheel
RUN pip3 install nipype==1.8.6

RUN wget -qO- https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin/

COPY nextflow/micaflow.nf /opt/micaflow/nextflow/micaflow.nf

COPY /atlas/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz /opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
COPY /atlas/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz /opt/micaflow/mni_icbm152_t1_tal_nlin_sym_09a_synthseg.nii.gz

RUN bash -c 'cp -r /opt/freesurfer-7.4.0/subjects'

WORKDIR /home/mica

ENV MICAFLOW="/opt/micaflow"

ENV PROC="container_micaflow-v0.0.1"

ENTRYPOINT ["/neurodocker/startup.sh", "nextflow", "run", "/opt/micaflow/nextflow/micaflow.nf"]