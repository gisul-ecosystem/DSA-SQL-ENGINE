# Debian bookworm is pinned on purpose: its Podman 4.3 client works with the
# Podman 4.x/5.x service on the host, while a newer client (Podman 5 on trixie)
# refuses to talk to a Podman 4 host.
FROM docker.io/library/python:3.11-slim-bookworm

WORKDIR /app

# Only the Podman client is used: with CONTAINER_HOST set it drives the host's
# rootful Podman service through the socket mounted by docker-compose.yml, and
# never runs containers itself.
RUN apt-get update && \
    apt-get install -y --no-install-recommends podman && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV CONTAINER_CLI=podman \
    CONTAINER_HOST=unix:///run/podman/podman.sock

# Copy only requirements first (better layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Then copy source code
COPY . .

EXPOSE 8000 9101

CMD ["sh", "-c", "mkdir -p ${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc} && rm -f ${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}/* && gunicorn api.main:app -c gunicorn.conf.py -w ${GUNICORN_WORKERS:-4} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --backlog 1024 --timeout 900 --graceful-timeout 900 --keep-alive 5"]
