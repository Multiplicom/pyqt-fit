FROM debian:stretch-slim AS build

RUN apt-get update && \ 
    apt-get -y --no-install-recommends --no-install-suggests install \
        build-essential \
        python \
        python-tk \
        python-dev \ 
        python-pip \
        python-setuptools && \
    rm -rf /var/lib/apt/lists/*

ADD . /tmp
WORKDIR /tmp 

#   python -m pip install -U pip 
#   https://github.com/pypa/pip/issues/5240#issuecomment-381673334
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt &&  \
    python setup.py install && \
    pip uninstall -y cython

# Only copy build artefacts
FROM debian:stretch-slim 
COPY --from=build /usr/local/lib/python2.7/dist-packages /usr/local/lib/python2.7/dist-packages
