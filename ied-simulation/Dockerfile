FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/mz-automation/libiec61850.git

WORKDIR /opt/libiec61850
RUN mkdir build && cd build && cmake .. && make -j$(nproc)

WORKDIR /opt/libiec61850/examples/server_example_basic_io
RUN make

ENV IED_NAME="IED_DEFAULT"
EXPOSE 102
CMD ["./server_example_basic_io"]
