FROM alpine:latest

# docker login -u docker-it4es iai-artifactory.iai.kit.edu
# docker buildx build --platform linux/amd64 -t iai-artifactory.iai.kit.edu/docker-it4es/energyhub-mqtt:latest --push --provenance=false .
# kubectl kubectl config use-context cy2814.elab
# kubectl get pods
# kubectl exec -ti simon-energyhub-57bfb69df7-jkx7c -- tail -n 3 logs/mqtt_runner.log

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    gcc \
    g++ \
    make \
    musl-dev \
    gfortran \
    lapack-dev \
    blas-dev \
    pkgconfig

COPY . /app

RUN git clone https://github.com/coin-or/Ipopt.git
RUN cd Ipopt && mkdir build && cd build && ../configure && make && make install

RUN rm -rf Ipopt

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN cd /app && python3 -m venv .venv && .venv/bin/pip install -r Requirements.txt

# Set the entry point to run mqtt_runner.py
CMD ["/app/.venv/bin/python", "mqtt_runner.py"]