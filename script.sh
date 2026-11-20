# Handy commands (not run by CI). The engine uses rootful Podman: see PODMAN.md.

# Sandbox images (built on the host that runs the engine)
podman build -t python-sandbox:latest -f docker/python.Dockerfile .
podman build -t cpp-sandbox:latest -f docker/cpp.Dockerfile .

# API image
podman build -t judge-api .

# API image for amd64, pushed to Docker Hub
podman build --platform linux/amd64 -t docker.io/gisul/execution-engine-py:latest .
podman push docker.io/gisul/execution-engine-py:latest

# Run the API against the host's Podman service
podman run \
  -p 8900:8000 \
  -v /run/podman/podman.sock:/run/podman/podman.sock \
  -e CONTAINER_HOST=unix:///run/podman/podman.sock \
  -v "$(pwd)/sandbox:/sandbox" \
  -e HOST_SANDBOX_ROOT="$(pwd)/sandbox" \
  --name judge-api \
  judge-api
