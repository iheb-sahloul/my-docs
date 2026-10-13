# Docker, Kubernetes & DevOps Best Practices

## 🐳 Docker images

### Use multi-stage builds

Build in one stage with the full toolchain, and copy only the result into a small runtime image.

**Why it's a best practice:** a single-stage image ships the JDK, Maven, the `~/.m2` cache, the source code and
the Node toolchain to production. That's hundreds of MB to pull on every deploy, a slower cold start, and many
more packages with known vulnerabilities to patch. The final stage only needs a JRE and the jar.

```dockerfile
# ✅
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN ./mvnw -q package -DskipTests

FROM eclipse-temurin:21-jre
COPY --from=build /app/target/app.jar /app/app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Pin base image versions

Use a specific version tag, or a digest for full reproducibility. Never `latest`.

**Why it's a best practice:** `latest` points to whatever was pushed last. The same Dockerfile builds a different
image next week, maybe with a new major version of the runtime, and a build that worked yesterday breaks with no
change in your repo. You also can't tell which version is in production. Pin the version, and let a bot
(Renovate, Dependabot) open PRs to update it so upgrades are reviewed and tested.

⛔ `FROM node:latest`
✅ `FROM node:22.11-alpine` or `FROM node:22.11-alpine@sha256:...`

### Order layers from least to most frequently changed

Copy dependency files and install dependencies first, then copy the source code.

**Why it's a best practice:** Docker caches each layer and rebuilds everything after the first one that
changed. With `COPY . .` first, any source change invalidates the dependency layer, so every build downloads all
dependencies again. Copying `package.json` / `pom.xml` alone first means dependencies are only reinstalled when
they actually change: builds go from minutes to seconds.

```dockerfile
# ✅
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
```

### Add a `.dockerignore`

Exclude `.git`, `node_modules`, `target`, local `.env` files and IDE folders from the build context.

**Why it's a best practice:** without it, `COPY . .` sends the whole directory to the build, including a
`.git` folder that can weigh more than the app, local build output that overwrites the one built in the image,
and `.env` files with real secrets that end up inside a layer anyone with the image can read.

✅ `.dockerignore`: `.git`, `node_modules`, `target`, `.env*`, `*.log`

### Don't run as root

Create a non-root user in the image and switch to it with `USER`.

**Why it's a best practice:** by default, the process in the container runs as root. If the app is compromised,
the attacker is root inside the container, can modify its files, and is one kernel or runtime vulnerability away
from root on the node. With a non-root user, a container escape gives far less. Kubernetes can enforce it with
`securityContext.runAsNonRoot: true`.

```dockerfile
# ✅
RUN useradd --system --uid 10001 app
USER 10001
```

### Never put secrets in the image

Don't `COPY` credentials or set them with `ENV` / `ARG`. Inject them at runtime (Kubernetes Secret, vault). Use
`RUN --mount=type=secret` if the build itself needs one.

**Why it's a best practice:** every layer of an image is kept and can be extracted with `docker save` or
`docker history`, even if a later layer deletes the file. `ENV` and `ARG` values are stored in the image
metadata in clear text. Anyone who can pull the image (a registry, a CI cache, a developer laptop) gets the
secret, and rotating it means rebuilding every image.

⛔ `ENV DB_PASSWORD=s3cr3t`, `COPY id_rsa /root/.ssh/`
✅ secret mounted at runtime, `RUN --mount=type=secret,id=npmrc npm ci` at build time

## 📦 Containers at runtime

### Use the exec form and handle `SIGTERM`

Write `ENTRYPOINT` / `CMD` as a JSON array, and make the app finish in-flight work when it receives `SIGTERM`.

**Why it's a best practice:** the shell form (`ENTRYPOINT java -jar app.jar`) starts `/bin/sh` as PID 1, and the
shell doesn't forward signals. On a stop or a deploy, the app never receives `SIGTERM`, is killed with `SIGKILL`
after the grace period, and in-flight requests fail. The exec form makes the app PID 1 so it gets the signal and
can shut down cleanly.

⛔ `ENTRYPOINT java -jar /app/app.jar`
✅ `ENTRYPOINT ["java", "-jar", "/app/app.jar"]`

### One process per container, logs to stdout

Run a single main process per container, and write logs to stdout / stderr, not to files.

**Why it's a best practice:** the container's lifecycle follows its main process: if you start several with a
script, one can crash while the container stays "running" and healthy. Separate containers can be scaled,
restarted and monitored independently. The platform collects stdout automatically; log files inside a container
fill its disk and disappear when it restarts. Log in JSON so the aggregator can index fields.

⛔ a `start.sh` that runs nginx and the app in the background and tails a log file
✅ one container per process, JSON logs to stdout

## ☸️ Kubernetes

### Set resource requests and limits

Give every container CPU and memory `requests`, and a memory `limit`.

**Why it's a best practice:** the scheduler places pods based on `requests`. Without them, it packs too many pods
on a node, and they fight for CPU and memory. Without a memory limit, one leaking pod can use all the node's memory
and get other pods evicted. A memory limit that's too low gets the pod `OOMKilled`, so measure real usage first.
For the JVM, size the heap relative to the container (`-XX:MaxRAMPercentage=75`). A CPU limit causes throttling,
so many teams set a CPU request only.

```yaml
# ✅
resources:
  requests: { cpu: 250m, memory: 512Mi }
  limits: { memory: 512Mi }
```

### Configure liveness, readiness and startup probes correctly

Readiness decides whether the pod gets traffic. Liveness decides whether it gets restarted. Startup protects slow
starts.

**Why it's a best practice:** without a readiness probe, traffic is sent to a pod that hasn't finished starting,
and clients get errors on every deploy. A liveness probe that checks the database restarts every pod when the
database has a hiccup, which turns a small outage into a full one: liveness should only check that the process
itself is alive. A slow-starting app with only a liveness probe gets killed before it's ready, in a restart loop;
a `startupProbe` disables the other probes until startup succeeds.

```yaml
# ✅
startupProbe:   { httpGet: { path: /actuator/health/liveness,  port: 8080 }, failureThreshold: 30, periodSeconds: 5 }
livenessProbe:  { httpGet: { path: /actuator/health/liveness,  port: 8080 } }
readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
```

### Keep config in ConfigMaps and Secrets

Store environment-specific configuration in `ConfigMap`s and credentials in `Secret`s (ideally synced from a
vault), not in the image.

**Why it's a best practice:** the same image should run in every environment, only the configuration changes.
If the database URL is baked into the image, you need one build per environment, and what you tested isn't what
you deploy. Secrets are only base64-encoded, not encrypted: enable encryption at rest, restrict access with RBAC,
and prefer a tool like External Secrets or Sealed Secrets rather than committing them.

⛔ one image per environment, credentials in `values.yaml` in Git
✅ `envFrom: [{ configMapRef: { name: app-config } }, { secretRef: { name: app-secrets } }]`

### Run several replicas with a `PodDisruptionBudget`

Run at least 2 replicas of anything user-facing, spread across nodes, and protect them with a
`PodDisruptionBudget`.

**Why it's a best practice:** with one replica, every deploy, node upgrade or crash is downtime. Even with
several, a node drain can evict them all at once. A PDB tells Kubernetes how many pods must stay up during
voluntary disruptions, so maintenance waits instead of taking the service down. Topology spread constraints stop
all replicas from landing on the same node.

```yaml
# ✅
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector: { matchLabels: { app: orders } }
```

### Use rolling updates with `maxUnavailable: 0`

Configure the deployment strategy so new pods are ready before old ones are removed.

**Why it's a best practice:** combined with a readiness probe, `maxUnavailable: 0` and `maxSurge: 1` means
Kubernetes starts a new pod, waits until it's ready, and only then stops an old one. If the new version never
becomes ready, the rollout stops and the old pods keep serving traffic. Roll back with `kubectl rollout undo`.

✅ `strategy: { type: RollingUpdate, rollingUpdate: { maxUnavailable: 0, maxSurge: 1 } }`

All of the above in one manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: orders }
spec:
  replicas: 3
  strategy: { type: RollingUpdate, rollingUpdate: { maxUnavailable: 0, maxSurge: 1 } }
  selector: { matchLabels: { app: orders } }
  template:
    metadata: { labels: { app: orders } }
    spec:
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: { matchLabels: { app: orders } }
      securityContext: { runAsNonRoot: true }
      containers:
        - name: orders
          image: registry.example.com/orders:3f9c2ab   # immutable tag, never latest
          ports: [{ containerPort: 8080 }]
          envFrom:
            - configMapRef: { name: app-config }
            - secretRef: { name: app-secrets }
          resources:
            requests: { cpu: 250m, memory: 512Mi }
            limits: { memory: 512Mi }
          startupProbe:   { httpGet: { path: /actuator/health/liveness,  port: 8080 }, failureThreshold: 30, periodSeconds: 5 }
          livenessProbe:  { httpGet: { path: /actuator/health/liveness,  port: 8080 } }
          readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: orders }
spec:
  minAvailable: 1
  selector: { matchLabels: { app: orders } }
```

## ⎈ Helm

### One chart, one values file per environment

Keep a single chart with sensible defaults in `values.yaml`, and override only what differs in
`values-<env>.yaml`.

**Why it's a best practice:** copying the chart or the manifests per environment means every fix has to be
applied several times, and the copies drift until production no longer matches what you tested. With per-env
values files, the difference between environments is small and visible in one diff.

⛔ `charts/orders-dev/`, `charts/orders-prod/`
✅ `helm upgrade --install orders ./chart -f values.yaml -f values-prod.yaml`

### Lint and render charts in CI

Run `helm lint` and `helm template` (plus a schema validator like kubeconform) on every change.

**Why it's a best practice:** a template error or wrong indentation in YAML is only discovered at deploy time,
often in production. Rendering the chart in CI catches syntax errors and invalid manifests before merge, and the
rendered output can be diffed in review so you see the real Kubernetes objects that will change.

✅ `helm lint ./chart && helm template ./chart -f values-prod.yaml | kubeconform -strict`

## 🚀 CI/CD

### Build once, promote the same artifact

Build the image once, tag it with the commit SHA, and deploy that same image to every environment.

**Why it's a best practice:** rebuilding for each environment can produce a different image (a new base image, a
different dependency version), so what you tested in staging isn't what runs in production. An immutable tag
like the commit SHA tells you exactly which code is running and makes rollback a redeploy of the previous tag.
Mutable tags (`latest`, `prod`) change under you and break both.

⛔ rebuild on each branch merge, deploy `myapp:latest`
✅ `myapp:3f9c2ab` built once, promoted dev → staging → prod

### Scan images and dependencies in the pipeline

Scan images (Trivy, Grype) and dependencies on every build, and fail on critical vulnerabilities.

**Why it's a best practice:** most vulnerabilities come from base images and third-party libraries, not your own
code, and new ones are published every day for packages you shipped months ago. Scanning in CI blocks known
issues before they reach production, and regular scans of running images tell you when you need to rebuild.

✅ `trivy image --exit-code 1 --severity CRITICAL myapp:3f9c2ab`

A minimal pipeline that builds once, scans, and promotes the same SHA-tagged image (cluster credentials setup omitted):

```yaml
# .github/workflows/ci.yml
name: ci
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./mvnw -B verify                       # fail fast: tests before anything else
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: "${{ github.actor }}", password: "${{ secrets.GITHUB_TOKEN }}" }
      - run: |
          IMAGE=ghcr.io/${{ github.repository }}:${GITHUB_SHA::7}
          docker build -t "$IMAGE" .
          docker run --rm aquasec/trivy image --exit-code 1 --severity CRITICAL "$IMAGE"
          docker push "$IMAGE"                      # build once, push once

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging                            # prod uses its own environment with required reviewers
    steps:
      - uses: actions/checkout@v4
      - run: helm upgrade --install orders ./chart -f values.yaml -f values-staging.yaml --set image.tag=${GITHUB_SHA::7} --atomic
```
