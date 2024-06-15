FROM debian:latest

RUN apt-get update && apt-get install -y \
    wget \
    git \
    python3 \
    python3-pip \
    ants \
    freesurfer \
    locales \
    && apt-get clean

RUN pip3 install sys nipype==1.8.6

RUN wget -qO- https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin/

ENV FREESURFER_HOME /usr/local/freesurfer
ENV SUBJECTS_DIR /usr/local/freesurfer/subjects

RUN mkdir -p $FREESURFER_HOME && mkdir -p $SUBJECTS_DIR

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ENV PATH /usr/local/ants:$PATH