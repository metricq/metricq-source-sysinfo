FROM python:3.13-slim-trixie AS builder

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY . /src
WORKDIR /src

RUN pip install --no-cache-dir '.'


FROM python:3.13-slim-trixie

RUN useradd -m metricq

COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

USER metricq
WORKDIR /home/metricq

ENTRYPOINT [ "metricq-source-sysinfo" ]
