#!/usr/bin/env bash
set -euo pipefail

: "${DEPLOY_PATH:?Set GitHub secret DEPLOY_PATH to the remote deploy directory}"
: "${SANDBOX_HOST_PATH:?Set GitHub secret SANDBOX_HOST_PATH to a Linux path such as /home/gisuladmin/judge-sandbox}"
: "${IMAGE:?IMAGE is required}"
: "${DOCKERHUB_USERNAME:?DOCKERHUB_USERNAME is required}"
: "${DOCKERHUB_TOKEN:?DOCKERHUB_TOKEN is required}"

if [[ "${SANDBOX_HOST_PATH}" == /run/desktop/mnt/host/* ]]; then
  echo "SANDBOX_HOST_PATH is set to a Windows-host mount: ${SANDBOX_HOST_PATH}" >&2
  echo "Use a native Linux path instead, e.g. /home/gisuladmin/judge-sandbox" >&2
  exit 1
fi

# Rootful Podman: every podman command (and the compose provider) talks to the
# host's Podman service through its socket, so the deploy user only needs
# access to that socket (see PODMAN.md).
export CONTAINER_HOST="${CONTAINER_HOST:-unix:///run/podman/podman.sock}"
# Always follow CONTAINER_HOST: a DOCKER_HOST left in the environment (login
# profile, rootless setup) would send the compose provider to another service.
export DOCKER_HOST="${CONTAINER_HOST}"
if ! podman version >/dev/null 2>&1; then
  echo "Cannot reach the Podman service at ${CONTAINER_HOST}." >&2
  echo "Enable it with: sudo systemctl enable --now podman.socket (see PODMAN.md)" >&2
  exit 1
fi

mkdir -p "${DEPLOY_PATH}"
cd "${DEPLOY_PATH}"

# The live sandbox mount contains root-owned temp dirs; keep it out of the
# sandbox image build context or `podman build .` fails with "can't stat".
printf 'sandbox\n.env\n' > .dockerignore

echo "${DOCKERHUB_TOKEN}" | podman login docker.io -u "${DOCKERHUB_USERNAME}" --password-stdin
podman pull "${IMAGE}"

CHECKSUM_FILE="${HOME}/.sandbox_checksums"
touch "${CHECKSUM_FILE}"

python=0
js=0
java=0
kotlin=1
cpp=0
go=0
rust=0
csharp=0

check() {
  local flag_name="$1"
  local file="$2"
  if [ ! -f "$file" ]; then
    return
  fi
  local new_sum
  new_sum=$(sha256sum "$file" | awk '{print $1}')
  local old_sum
  old_sum=$(grep "^${file}=" "$CHECKSUM_FILE" 2>/dev/null | cut -d= -f2 || true)
  if [ "$new_sum" != "$old_sum" ]; then
    eval "${flag_name}=1"
  fi
}

check python docker/python.Dockerfile
check js docker/js.Dockerfile
check java docker/java.Dockerfile
check cpp docker/cpp.Dockerfile
check cpp docker/cpp_support.hpp
check go docker/go.Dockerfile
check rust docker/rust.Dockerfile
check csharp docker/csharp.Dockerfile

if ! podman image inspect python-sandbox:latest >/dev/null 2>&1; then python=1; fi
if ! podman image inspect js-sandbox:latest >/dev/null 2>&1; then js=1; fi
if ! podman image inspect java-sandbox:latest >/dev/null 2>&1; then java=1; fi
if ! podman image inspect kotlin-sandbox:latest >/dev/null 2>&1; then kotlin=1; fi
if ! podman image inspect cpp-sandbox:latest >/dev/null 2>&1; then cpp=1; fi
if ! podman image inspect go-sandbox:latest >/dev/null 2>&1; then go=1; fi
if ! podman image inspect rust-sandbox:latest >/dev/null 2>&1; then rust=1; fi
if ! podman image inspect csharp-sandbox:latest >/dev/null 2>&1; then csharp=1; fi

if [[ "${python}" == "1" ]]; then podman build -t python-sandbox:latest -f docker/python.Dockerfile .; fi
if [[ "${js}" == "1" ]]; then podman build -t js-sandbox:latest -f docker/js.Dockerfile .; fi
if [[ "${java}" == "1" ]]; then podman build -t java-sandbox:latest -f docker/java.Dockerfile .; fi
if [[ "${kotlin}" == "1" ]]; then podman build -t kotlin-sandbox:latest -f docker/kotlin.Dockerfile .; fi
if [[ "${cpp}" == "1" ]]; then podman build -t cpp-sandbox:latest -f docker/cpp.Dockerfile .; fi
if [[ "${go}" == "1" ]]; then podman build -t go-sandbox:latest -f docker/go.Dockerfile .; fi
if [[ "${rust}" == "1" ]]; then podman build -t rust-sandbox:latest -f docker/rust.Dockerfile .; fi
if [[ "${csharp}" == "1" ]]; then podman build -t csharp-sandbox:latest -f docker/csharp.Dockerfile .; fi

for f in docker/python.Dockerfile docker/js.Dockerfile docker/java.Dockerfile \
         docker/kotlin.Dockerfile docker/cpp.Dockerfile docker/cpp_support.hpp \
         docker/go.Dockerfile docker/rust.Dockerfile docker/csharp.Dockerfile; do
  [ -f "$f" ] || continue
  sed -i "\|^${f}=|d" "${CHECKSUM_FILE}" 2>/dev/null || true
  echo "${f}=$(sha256sum "$f" | awk '{print $1}')" >> "${CHECKSUM_FILE}"
done

podman image inspect python-sandbox:latest >/dev/null
podman image inspect js-sandbox:latest >/dev/null
podman image inspect java-sandbox:latest >/dev/null
podman image inspect kotlin-sandbox:latest >/dev/null
podman image inspect cpp-sandbox:latest >/dev/null
podman image inspect go-sandbox:latest >/dev/null
podman image inspect rust-sandbox:latest >/dev/null
podman image inspect csharp-sandbox:latest >/dev/null

export HOST_SANDBOX_ROOT="${SANDBOX_HOST_PATH}"
export WORKER_SCALE="${WORKER_SCALE:-2}"
export WORKER_CONCURRENCY="${WORKER_CONCURRENCY:-8}"
export DOCKER_RUN_CONCURRENCY="${DOCKER_RUN_CONCURRENCY:-6}"
export COMPILE_CONCURRENCY="${COMPILE_CONCURRENCY:-3}"
export WARM_CONTAINER_TTL_SECONDS="${WARM_CONTAINER_TTL_SECONDS:-300}"

podman compose config >/dev/null
podman compose up -d --no-build --remove-orphans --scale "worker=${WORKER_SCALE}"
