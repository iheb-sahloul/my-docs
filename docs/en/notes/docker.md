# Docker

## Images

### Build an image

```bash
docker build -t myapp:1.0 .                       # Dockerfile in current dir
docker build -f docker/Dockerfile.prod -t myapp:prod .
docker build --build-arg JAR=app.jar -t myapp .   # ARG in Dockerfile
docker build --no-cache -t myapp .                # ignore layer cache
docker buildx build --platform linux/amd64,linux/arm64 -t me/myapp:1.0 --push .
```

### Multi-stage Dockerfile (small runtime image)

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q dependency:go-offline          # cached until pom.xml changes
COPY src ./src
RUN mvn -q package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/app.jar app.jar
USER 1000
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
```

Put rarely-changing steps first: each instruction is a layer and one changed layer invalidates all the layers after it.

### .dockerignore

```text
.git
target/
node_modules/
*.log
.env
```

### List, tag, push, remove

```bash
docker images                                  # local images
docker image ls --filter dangling=true
docker tag myapp:1.0 registry.example.com/team/myapp:1.0
docker login registry.example.com
docker push registry.example.com/team/myapp:1.0
docker pull postgres:16
docker rmi myapp:1.0
```

### Inspect image layers and size

```bash
docker history myapp:1.0                       # size of each layer
docker image inspect myapp:1.0 --format '{{.Size}} {{.Config.Env}}'
```

---

## Containers

### Run

```bash
docker run --rm -it alpine sh                  # interactive, removed on exit
docker run -d --name web -p 8080:80 nginx      # detached, host 8080 -> container 80
docker run -d --name db \
  -e POSTGRES_PASSWORD=secret \
  -v pgdata:/var/lib/postgresql/data \
  -p 5432:5432 postgres:16
docker run --rm -v "$PWD":/work -w /work node:20 npm test   # run a tool without installing it
```

### Common `run` flags

| Flag | Meaning |
|---|---|
| `-d` | Detached (background) |
| `-it` | Interactive + TTY (for shells) |
| `--rm` | Delete the container when it exits |
| `-p host:container` | Publish a port |
| `-e KEY=val` / `--env-file .env` | Environment variables |
| `-v name:/path` / `-v ./dir:/path` | Named volume / bind mount |
| `--network mynet` | Attach to a user-defined network |
| `--restart unless-stopped` | Restart policy |
| `--memory 512m --cpus 1.5` | Resource limits |
| `--user 1000:1000` | Run as non-root |
| `--read-only` | Read-only root filesystem |

### Lifecycle

```bash
docker ps                                      # running
docker ps -a                                   # including stopped
docker stop web                                # SIGTERM, then SIGKILL after 10s
docker start web
docker restart web
docker kill web                                # SIGKILL now
docker rm web                                  # remove stopped container
docker rm -f web                               # stop + remove
```

### Custom `ps` output

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

```text
NAMES   STATUS         PORTS
web     Up 2 minutes   0.0.0.0:8080->80/tcp
db      Up 2 minutes   0.0.0.0:5432->5432/tcp
```

---

## Debugging

### Logs

```bash
docker logs web
docker logs -f --tail 100 web                  # follow, last 100 lines
docker logs --since 10m web
docker logs -t web                             # with timestamps
```

### Shell into a running container

```bash
docker exec -it web sh                         # or bash if the image has it
docker exec web env                            # one-off command
docker exec -u root -it web sh                 # as root
```

### Copy files in and out

```bash
docker cp web:/etc/nginx/nginx.conf ./nginx.conf
docker cp ./index.html web:/usr/share/nginx/html/
```

### Inspect

```bash
docker inspect web                             # full JSON
docker inspect -f '{{.NetworkSettings.IPAddress}}' web
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' web   # why did it die?
docker port web                                # published ports
docker top web                                 # processes inside
docker stats                                   # live CPU/mem per container
docker events --since 10m                      # daemon events
```

### Container exits immediately

```bash
docker ps -a                                   # look at STATUS: Exited (137) = killed/OOM, (1) = app error
docker logs <name>
docker run --rm -it --entrypoint sh myapp:1.0  # bypass ENTRYPOINT and poke around
```

| Exit code | Usual cause |
|---|---|
| 0 | Main process finished normally |
| 1 | Application error |
| 125-127 | Docker error / command not executable / not found |
| 137 | SIGKILL (often out of memory) |
| 143 | SIGTERM (graceful stop) |

### Debug an image without a shell (distroless)

```bash
docker run --rm -it --pid=container:web --network=container:web nicolaka/netshoot
```

---

## Troubleshooting: find the cause, then fix it

Method, always in this order:

```bash
docker ps -a                                   # is it running? exit code?
docker logs --tail 100 <name>                  # what the app said
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}' <name>
docker exec -it <name> sh                      # or --entrypoint sh if it won't stay up
```

| Symptom | Likely cause | Confirm | Fix |
|---|---|---|---|
| Exits immediately (code 1) | App error / missing env | `docker logs` | Pass env (`-e`, `--env-file`), fix config |
| Exits with 137 | OOM or `docker kill` | `.State.OOMKilled` is `true` | Raise `--memory` / Docker Desktop memory, fix leak |
| Exits with 126 / 127 | Entrypoint not executable / not found | `docker logs`: `exec: not found` | `chmod +x` in the image, fix path, check shebang / CRLF line endings |
| `exec format error` | Image built for another CPU (arm64 vs amd64) | `docker image inspect -f '{{.Architecture}}' img` | Build/pull with `--platform linux/amd64` |
| Port published but unreachable | App listens on `127.0.0.1` inside | `docker exec x ss -tln` | Bind the app to `0.0.0.0` |
| `port is already allocated` | Host port in use | `lsof -i :8080` | Change the host side of `-p 8081:8080` or stop the other process |
| `name is already in use` | Stopped container keeps the name | `docker ps -a` | `docker rm <name>` or use `--rm` |
| Container can't reach another by name | On the default bridge | `docker network inspect bridge` | Use a user-defined network / Compose |
| Can't reach a service on the host | `localhost` is the container itself | | `host.docker.internal` (Linux: `--add-host=host.docker.internal:host-gateway`) |
| `permission denied` on a mount | UID mismatch between host and container | `docker exec x id`, `ls -ln` on host | `--user "$(id -u):$(id -g)"`, `chown`, or a named volume |
| Bind mount is empty | Wrong absolute path / not shared with Docker Desktop | `docker inspect -f '{{json .Mounts}}' x` | Use an absolute path, allow the folder in Docker Desktop |
| `no space left on device` | Images, layers, volumes piled up | `docker system df` | `docker system prune`, `docker volume prune` (check first!) |
| `pull access denied` / `unauthorized` | Not logged in or wrong image name | | `docker login <registry>`, fix the name/tag |
| Build ignores my change | Stale layer cache | | `docker build --no-cache`, or reorder `COPY` so deps are cached separately |
| Compose: app starts before the DB | `depends_on` only waits for start | `docker compose logs app` shows connection refused | Add `healthcheck` + `depends_on: { db: { condition: service_healthy } }` |

Applied fix, then verify:

```bash
docker compose up -d --build --force-recreate
docker compose ps
docker compose logs -f app
```

---

## Volumes and bind mounts

### Volumes

```bash
docker volume create pgdata
docker volume ls
docker volume inspect pgdata                   # Mountpoint, driver
docker volume rm pgdata
```

### Back up and restore a volume

```bash
docker run --rm -v pgdata:/data -v "$PWD":/backup alpine \
  tar czf /backup/pgdata.tgz -C /data .

docker run --rm -v pgdata:/data -v "$PWD":/backup alpine \
  tar xzf /backup/pgdata.tgz -C /data
```

| Type | Syntax | Use for |
|---|---|---|
| Named volume | `-v pgdata:/var/lib/...` | Persistent data managed by Docker |
| Bind mount | `-v "$PWD"/src:/app/src` | Live-editing source code |
| tmpfs | `--tmpfs /tmp` | Scratch data, never on disk |

---

## Networks

### User-defined bridge (containers resolve each other by name)

```bash
docker network create backend
docker run -d --name db  --network backend postgres:16
docker run -d --name api --network backend -e DB_HOST=db myapp   # host "db" works
docker network ls
docker network inspect backend                 # connected containers + IPs
docker network connect backend web             # attach a running container
docker network disconnect backend web
```

The default `bridge` network has **no** name resolution. Always create your own network.

### Reach the host from a container

```bash
# Docker Desktop (Mac/Windows): host.docker.internal
# Linux: add it yourself
docker run --add-host=host.docker.internal:host-gateway myapp
```

### Test connectivity

```bash
docker exec api sh -c 'nc -zv db 5432'
docker exec api wget -qO- http://web:80
```

---

## Docker Compose

### compose.yaml

```yaml
services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/app
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

### Daily commands

```bash
docker compose up -d                           # create + start in background
docker compose up -d --build                   # rebuild images first
docker compose ps
docker compose logs -f api
docker compose exec db psql -U postgres app
docker compose run --rm api ./mvnw test        # one-off container
docker compose restart api
docker compose stop                            # keep containers
docker compose down                            # remove containers + network
docker compose down -v                         # ...and volumes (deletes data!)
docker compose config                          # show the merged, resolved file
```

### Override files and profiles

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d   # later file overrides earlier
docker compose --profile debug up -d                       # services with `profiles: [debug]`
```

---

## Cleanup

### Disk usage and prune

```bash
docker system df                               # what is using space
docker container prune                         # stopped containers
docker image prune                             # dangling images
docker image prune -a                          # every image not used by a container
docker volume prune                            # unused volumes (data loss!)
docker network prune
docker builder prune                           # build cache
docker system prune -a --volumes               # everything unused
```

### Targeted removal

```bash
docker rm $(docker ps -aq -f status=exited)
docker rmi $(docker images -q -f dangling=true)
docker container prune --filter "until=24h"
```

---

## Useful one-liners

### Get a container's IP / env / mounts

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' web
docker inspect -f '{{json .Config.Env}}' web | jq
docker inspect -f '{{json .Mounts}}' web | jq
```

### Stop everything

```bash
docker stop $(docker ps -q)
```

### Run as your own user so files aren't root-owned

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/work -w /work maven:3.9 mvn package
```
