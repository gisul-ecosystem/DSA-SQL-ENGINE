FROM python:3.11-slim

WORKDIR /app

# Install ONLY docker CLI (not full engine)
RUN apt-get update && \
    apt-get install -y docker-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first (better layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Then copy source code
COPY . .

EXPOSE 8000 9101

CMD ["sh", "-c", "mkdir -p ${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc} && rm -f ${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}/* && gunicorn api.main:app -c gunicorn.conf.py -w ${GUNICORN_WORKERS:-4} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --backlog 1024 --timeout 900 --graceful-timeout 900 --keep-alive 5"]
