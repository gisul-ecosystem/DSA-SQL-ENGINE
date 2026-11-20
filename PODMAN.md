# Running on Podman

The DSA execution engine runs on **rootful Podman** instead of Docker. Image builds on
GitHub's runners still use Docker (they only produce images, which Podman runs
unchanged); everything on the servers uses Podman.

## How it runs

The `api` and `worker` containers start one sandbox container per
submission. They run the Podman client (installed in `Dockerfile`), which
reaches the host's root Podman service through the socket that
`docker-compose.yml` mounts at `/run/podman/podman.sock` (`CONTAINER_HOST`).
`CONTAINER_CLI` (default `podman`) is the command the engine runs.

- The API image is pinned to Debian bookworm: its Podman 4.3 client works with
  a Podman 4.x/5.x host, while a Podman 5 client refuses a Podman 4 host.
- The sandbox images (`python-sandbox`, `cpp-sandbox`, ...) live in Podman's
  image store. `scripts/deploy-remote.sh` builds any that are missing, so the
  first deploy after the switch rebuilds all of them (several minutes).
- Sandbox limits keep their names: `DOCKER_MEMORY_LIMIT`, `DOCKER_CPU_LIMIT`,
  `DOCKER_PIDS_LIMIT`, `DOCKER_RUN_CONCURRENCY`, ... (renaming them would break
  existing `.env` files and dashboards), and so do the
  `execution_engine_docker_*` metrics.
- `security_opt: label=disable` lets the containers use the socket on SELinux
  hosts; it does nothing elsewhere.

## One-time setup on each server

Podman runs **rootful** (as root), which behaves like the Docker daemon did: the
same resource limits, `pause`, ports below 1024 and one shared image store. The
deploy user (SSH user or self-hosted runner user) never runs `sudo podman`; it
talks to the root Podman service through its API socket, the same way it used
the Docker socket through the `docker` group.

1. **Install Podman 4.7 or newer** (`podman compose` appeared in 4.7; Ubuntu
   24.04 ships 4.9):

   ```bash
   sudo apt-get update && sudo apt-get install -y podman
   podman --version
   ```

2. **Install a compose provider.** `podman compose` runs Docker's
   `docker-compose` v2 binary against the Podman API. It is only the compose
   file interpreter; no Docker engine is installed or running. (`podman-compose`
   also works for simple stacks, but it names containers differently and does
   not support everything these files use, such as `--scale` and healthcheck
   conditions.)

   ```bash
   sudo curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
     -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Enable the API socket, and restart containers after a reboot.** Unlike
   Docker, Podman has no always-on daemon: `restart: always` /
   `--restart always` containers come back after a reboot only through
   `podman-restart.service`.

   ```bash
   sudo systemctl enable --now podman.socket
   sudo systemctl enable --now podman-restart.service
   ```

   On **Podman 4.x** (Ubuntu 24.04 ships 4.9) that service only restarts
   `restart: always` containers; `unless-stopped` ones (several of these
   stacks) stay down after a reboot. Podman 5 handles both. On 4.x add:

   ```bash
   sudo mkdir -p /etc/systemd/system/podman-restart.service.d
   printf '[Service]\nExecStart=\nExecStart=/usr/bin/podman $LOGGING start --all --filter restart-policy=always\nExecStart=/usr/bin/podman $LOGGING start --all --filter restart-policy=unless-stopped\n' \
     | sudo tee /etc/systemd/system/podman-restart.service.d/unless-stopped.conf
   sudo systemctl daemon-reload
   ```

   Do not `systemctl restart podman-restart.service` on a running server: its
   stop step stops every `restart: always` container first.

4. **Let the deploy user use the root socket** (the equivalent of the `docker`
   group; like that group, access to this socket is root-equivalent):

   ```bash
   sudo groupadd -f podman
   sudo usermod -aG podman "$DEPLOY_USER"
   sudo mkdir -p /etc/systemd/system/podman.socket.d
   printf '[Socket]\nSocketMode=0660\nSocketGroup=podman\n' \
     | sudo tee /etc/systemd/system/podman.socket.d/override.conf
   # Podman's own tmpfiles.d recreates /run/podman as 0700 at every boot, which
   # blocks the group even though the socket is 0660. Override just that line
   # (a file with the same name in /etc replaces the packaged one).
   sed 's#^D! /run/podman 0700 root root$#D! /run/podman 0755 root root#' \
     /usr/lib/tmpfiles.d/podman.conf | sudo tee /etc/tmpfiles.d/podman.conf
   sudo chmod 0755 /run/podman
   sudo systemctl daemon-reload && sudo systemctl restart podman.socket
   ```

   Do this before the first deploy: restarting `podman.socket` replaces the
   socket file, so containers that already mount it (the DSA and
   Data-Engineering engines) must be restarted afterwards.

   Log out and back in (and restart the GitHub runner service, if this server
   has one), then check that the user reaches the root service:

   ```bash
   CONTAINER_HOST=unix:///run/podman/podman.sock podman version   # shows Client and Server
   ```

   The deploy scripts and workflows set `CONTAINER_HOST` (and `DOCKER_HOST`
   for the compose provider) to this socket themselves.

5. **Check the network backend** is `netavark`, which gives containers DNS by
   service/container name (CNI, left over from old installs, does not):

   ```bash
   sudo podman info --format '{{.Host.NetworkBackend}}'
   ```

6. **If UFW (or another host firewall) is active, let containers reach their
   DNS server.** Podman's DNS (`aardvark-dns`) listens on each Podman bridge's
   gateway (`10.89.x.1:53`), which the firewall sees as traffic *into* the host,
   and UFW's default `INPUT DROP` blocks it: containers then cannot resolve
   each other (`redis`, `penpot-backend`, ...). Docker never hit this because its
   DNS runs inside each container. Allow just that:

   ```bash
   sudo ufw allow from 10.89.0.0/16 to any port 53 proto udp comment 'podman container DNS'
   sudo ufw allow from 10.89.0.0/16 to any port 53 proto tcp comment 'podman container DNS'
   ```

Docker and Podman can run side by side on one server (other stacks there can
stay on Docker); only the ports must not overlap.

Images are referenced with their full registry name (`docker.io/...`) because
Podman does not assume Docker Hub for short names.

If you build an image on a server with `podman build`, add `--format docker`
when its Dockerfile has a `HEALTHCHECK`: Podman's default OCI format drops it,
and `podman inspect -f '{{.State.Health.Status}}'` then fails. Images built by
Docker on GitHub keep it.

Compose health checks use the `CMD-SHELL` form whenever the command has
spaces in its arguments: Podman 4.x splits `["CMD", "python", "-c", "import x; ..."]`
on spaces, so the check fails and the container shows as unhealthy.

These steps were tested on rootful Podman 5.8 (Fedora), including a reboot,
and used on the production server 103.99.38.225 (Ubuntu 24.04, Podman 4.9.3,
Docker still running other stacks).

## Switching a server from Docker (once)

Docker and Podman keep separate image, container and volume stores: nothing
Docker has is visible to Podman.

1. Stop the Docker deployment so it frees its ports:

   ```bash
   cd "$DEPLOY_PATH" && docker compose down
   ```

2. **Copy the named volumes, or the service starts with empty data.** For each
   volume (`<project>_prometheus-data`, `<project>_grafana-data`; `<project>` is the deploy directory's name. They hold metrics history and Grafana settings only, so copying them is optional):

   ```bash
   docker volume ls                      # exact names
   VOL=<project>_prometheus-data
   sudo podman volume create "$VOL"
   sudo cp -a "/var/lib/docker/volumes/$VOL/_data/." \
     "$(sudo podman volume inspect "$VOL" --format '{{.Mountpoint}}')/"
   ```

   Keep the Docker copy until the Podman deployment is verified.

3. Once nothing else on the server needs Docker, turn it off so the two
   runtimes never compete for ports:

   ```bash
   sudo systemctl disable --now docker.service docker.socket
   ```

4. Run the deploy as usual (push to `main`, or re-run the workflow).

## Check the deployment

```bash
export CONTAINER_HOST=unix:///run/podman/podman.sock
podman compose ps                              # api, worker x2, redis healthy
podman compose exec worker podman version      # Client 4.3.x, Server = host version
podman images | grep sandbox                   # 8 sandbox images
curl -s localhost:8900/health
```

Then run and submit one solution per language from the Aaptor test window.

## Docker to Podman commands

The CLI is the same: `docker ps` is `podman ps`, `docker logs` is
`podman logs`, `docker compose up -d` is `podman compose up -d`. Run them as the
deploy user with both variables pointing at the root service, or as root with
`sudo podman ...`:

```bash
export CONTAINER_HOST=unix:///run/podman/podman.sock
export DOCKER_HOST=$CONTAINER_HOST   # podman compose passes this to the provider
```

Set `DOCKER_HOST` explicitly even if it is already set: `podman compose` hands the
existing value to docker-compose, and a leftover value (from a login profile or a
rootless setup) sends the deployment to a different Podman service. The deploy
scripts and workflows already do this.
