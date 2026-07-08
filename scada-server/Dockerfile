FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential cmake git swig \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/mz-automation/libiec61850.git

WORKDIR /opt/libiec61850
RUN mkdir build && cd build && \
    cmake -DBUILD_PYTHON_BINDINGS=ON .. && \
    make -j$(nproc) && make install

RUN pip3 install influxdb-client

WORKDIR /app
COPY scada_server.py .

CMD ["python3", "scada_server.py"]
