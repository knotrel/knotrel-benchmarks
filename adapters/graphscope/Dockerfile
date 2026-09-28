# A functional Linux/x86_64 probe on Apple Silicon; do not compare to native timings.
FROM --platform=linux/amd64 python:3.11-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake libopenmpi-dev openmpi-bin libgoogle-glog-dev libgflags-dev \
    libboost-filesystem-dev libboost-system-dev libboost-regex-dev \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir graphscope==0.29.0
ENV OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
WORKDIR /work
