# Full Stack & DevOps

## 🟢 Fundamentals

### REST

#### Q1. What are the core principles of good REST API design?
Model URLs around resources (nouns), not actions — `/orders/123`, not `/getOrder?id=123` — and
use HTTP methods to express the action: `GET` (read, safe and idempotent), `POST` (create, not
idempotent), `PUT` (full replace, idempotent), `PATCH` (partial update), `DELETE` (remove,
idempotent). Use status codes to carry real meaning (`200`/`201`/`204` for success variants,
`400` for a malformed request, `401`/`403` for auth failures, `404` for missing resources, `409`
for a conflict, `422` for semantically invalid data, `500` for server errors) rather than always
returning `200` with an error flag buried in the body. Nest resources to express genuine
ownership (`/orders/123/items`), keep responses consistent in shape across endpoints, and version
the API deliberately (Q8) rather than letting breaking changes ship silently.

### Containers

#### Q2. What is a container, and how does it fundamentally differ from a virtual machine?
A container packages an application with its dependencies and shares the host machine's kernel —
it's an isolated process (via Linux namespaces for isolation and cgroups for resource limits),
not a separate operating system, which makes it lightweight (starts in milliseconds to seconds,
small image footprint) compared to a VM, which virtualizes hardware and runs a full separate
guest OS and kernel (starts in tens of seconds to minutes, much larger footprint). The trade-off:
a VM gives stronger isolation (a separate kernel means a kernel-level exploit in one VM doesn't
automatically reach others) at a real resource cost; a container's shared-kernel model is
lighter and denser but means containers on the same host are isolated processes, not isolated
operating systems.

#### Q3. Walk through how Docker image layers and build caching work.
Each instruction in a Dockerfile (`RUN`, `COPY`, `ADD`) creates a new, immutable layer stacked on
the previous one, and Docker caches each layer — if a layer's instruction and its inputs haven't
changed since the last build, Docker reuses the cached layer instead of re-executing it, and
every layer *after* the first changed one must be rebuilt (cache invalidates from that point
forward, not selectively). This is why instruction order matters for build speed: put
infrequently-changing steps first (installing OS packages, restoring dependencies from a lock
file) and frequently-changing steps last (copying application source code), so a source code
change only invalidates and rebuilds the last few layers instead of the whole image, including
re-downloading dependencies unnecessarily.

#### Q4. Docker volumes vs bind mounts vs the container's writable layer — where should data live?
A container's own filesystem is a thin **writable layer** on top of the read-only image layers: it is
fast to start, but everything in it disappears when the container is removed, and heavy writes
through the copy-on-write storage driver are slower than a real volume. Anything that must
survive a container's life — a database's data directory, uploaded files — belongs outside it. A
**named volume** (`docker run -v pgdata:/var/lib/postgresql/data`) is created and managed by
Docker, lives in Docker's own area of the host, works the same on every OS, is portable between
containers, is the right default for persistent data, and can be backed up or driven by a volume
plugin (NFS, cloud disk). A **bind mount** (`-v $(pwd)/src:/app/src`) maps a specific host path into
the container: ideal for development, where your editor changes should be visible inside the container
immediately, but it ties the container to the host's directory layout and permissions (the classic
"files created by the container are owned by root on my host" problem, or the reverse on Linux with
mismatched UIDs) and is slower on macOS/Windows because of the VM file sharing layer. A `tmpfs` mount is
memory-only, useful for secrets or scratch files that must never touch the disk. Kubernetes has the same
distinction: `emptyDir` for scratch data tied to the pod's life, and a `PersistentVolumeClaim` for data
that must outlive it. The interview point is the failure mode: a database container run without a
volume loses all its data on `docker rm`, and `docker compose down -v` deletes the volumes as well.

### Kubernetes

#### Q5. What is a Kubernetes Pod, and why doesn't Kubernetes just run containers directly?
A Pod is the smallest deployable unit in Kubernetes — one or more containers that are always
scheduled together on the same node, share a network namespace (so they can reach each other via
`localhost` and share one IP), and can share storage volumes. Kubernetes doesn't manage bare
containers directly because most real workloads need this "always co-located, always
co-scheduled" grouping — a primary application container plus a sidecar (a log shipper, a service
mesh proxy) that must run alongside it on the same node and share its network — and the Pod
abstraction gives Kubernetes one unit to schedule, health-check, and scale as a whole, rather
than trying to reason about loosely-coupled containers that happen to need each other nearby.

#### Q6. A pod isn't working — what are your first `kubectl` commands, in order?
Go from "what state is it in?" to "why?" without guessing. `kubectl get pods -o wide` shows status,
restarts, the node and the IP: the status already narrows things (`Pending` = scheduling problem,
`ImagePullBackOff` = image or registry credentials, `CrashLoopBackOff` = the process starts and dies,
`Running` but `0/1 READY` = failing readiness probe). Then `kubectl describe pod <name>` — read the
**Events** section at the bottom first: it tells you about `FailedScheduling` (insufficient CPU, taints,
unbound volume), failed probes, OOM kills, or image pull errors, and the `Last State` block shows the
previous container's exit code and reason (`OOMKilled`, `Error`, exit 137/143). Next
`kubectl logs <pod>` for the application's output — and `--previous` for a container that has already
restarted, because the current instance may have logged nothing yet — with `-c <container>` in a
multi-container pod. If it's running but misbehaving, `kubectl exec -it <pod> -- sh` to poke at it (DNS
lookups, `curl` to a dependency, environment variables), or `kubectl debug` with an ephemeral container when the image has no shell.
For traffic issues check the layer above: `kubectl get endpoints <service>` (empty = selector or
readiness problem, S4) and `kubectl get events --sort-by=.lastTimestamp` for the namespace. Only
after that reach for `top`, node conditions, or the controller's rollout status
(`kubectl rollout status deploy/<name>`). The habit that separates seniors is reading Events and
`--previous` logs *before* changing anything.

### Observability

#### Q7. What are the three pillars of observability, and what does each one actually tell you?
**Logs** are discrete, timestamped events — what specifically happened, with detail (an error
message, a specific request's parameters) — best for deep-diving into one specific occurrence
once you already know roughly where to look. **Metrics** are aggregated numeric measurements over
time (request rate, error rate, latency percentiles, CPU/memory usage) — best for seeing trends,
setting alerting thresholds, and answering "is the system healthy right now" at a glance, but
without the detail of any single event. **Traces** follow one request's path through a
distributed system, showing the timing of each hop/span — best for answering "where in this
multi-service call chain did the time go, or where did it fail" for a specific request. The three
are complementary, not substitutes: metrics tell you something is wrong and roughly where; traces
narrow down which specific hop; logs give you the exact detail of what happened there.

## 🟡 Senior traps

### API design & security

#### Q8. How do you version a REST API without breaking existing clients?
**Answer:** The core discipline is distinguishing backward-compatible changes (adding a new
optional field, adding a new endpoint) — which don't need a version bump, since old clients
simply ignore fields they don't know about — from breaking changes (removing/renaming a field,
changing a field's type or meaning, changing required parameters), which do. For breaking
changes, common strategies: URL path versioning (`/v1/orders`, `/v2/orders` — simple, highly
visible, easy to route, but can lead to duplicated implementation logic across versions);
header-based versioning (`Accept: application/vnd.api.v2+json` — keeps URLs stable, less
visible/discoverable); or, more robustly, treat versioning as a last resort and design changes to
be additive and backward-compatible wherever possible (the same discipline behind Q27 in module
4's schema evolution question), reserving a hard version bump for genuinely unavoidable breaking
changes, with a clear deprecation window and communication to consumers before the old version is
retired.

**Example:**
```
GET /v1/orders/123        # URL path versioning — simple, visible, but duplicates logic across versions
GET /orders/123
Accept: application/vnd.api.v2+json   # header versioning — stable URL, less discoverable
```

**Why it's a trap:** reaching for a version bump on every change, including additive ones, forces
every client to explicitly upgrade for something that was backward-compatible in the first place
— a senior answer treats versioning as the last resort for genuinely breaking changes, not the
default response to any schema change.

#### Q9. What does idempotency mean for a REST API, and why does `POST` need special handling for it?
**Answer:** An idempotent operation produces the same end state no matter how many times it's
applied — `GET`, `PUT`, and `DELETE` are idempotent by definition/convention (calling
`DELETE /orders/123` five times leaves the same end state as calling it once), but `POST`
(typically "create a new resource") is not — retrying a `POST` due to a timeout or network blip
can create duplicate resources, exactly the pattern from module 4's messaging idempotency problem
(Q9/Q10 there) but at the HTTP layer. The fix is the same shape: accept an explicit idempotency
key from the client (a UUID generated once per logical operation, sent as a header, and resent
unchanged on any retry), and the server checks whether that key has already been processed before
creating a new resource — a client retrying a timed-out request with the same key gets the
original result back safely instead of a duplicate.

**Example:**
```http
POST /payments
Idempotency-Key: 7c9e6679-7425-40de-944b-e07fc1f90ae7
{...}
```
A network timeout causes the client to retry with the same key — the server recognizes the key
was already processed and returns the original result instead of creating a second payment.

**Why it's a trap:** assuming retry logic alone ("just retry on any timeout") is a safe default
regardless of HTTP method — retrying a `POST` without an idempotency key can silently create
duplicate resources exactly when the client is trying to be resilient.

#### Q10. What are common API rate-limiting algorithms, and what's the trade-off between them?
**Answer:** **Fixed window** counts requests in a fixed time bucket (e.g. per-minute) and resets
at the boundary — simple, but allows a burst of up to 2x the limit right at a window boundary (a
full allowance right before the boundary, then another full allowance right after). **Sliding
window** smooths this by weighting the count across the current and previous window
proportionally to elapsed time — more accurate, modestly more complex to implement. **Token
bucket** fills tokens at a steady rate up to a capacity, and each request consumes a token —
naturally allows brief bursts (up to the bucket's capacity) while enforcing a steady average rate
over time, which matches many real traffic patterns better than a hard per-window cap. **Leaky
bucket** processes requests at a strictly constant output rate regardless of input burstiness,
smoothing output completely at the cost of added latency for bursty legitimate traffic. The
choice depends on whether legitimate traffic is naturally bursty (favoring token bucket) or
whether a strictly smooth downstream rate is required (favoring leaky bucket).

**Example:**
```
# Fixed window: up to 2x burst possible right at the boundary.
11:00:59 -> 100 requests allowed (window resets at 11:01:00)
11:01:00 -> another 100 requests allowed immediately -> 200 in ~1 second

# Token bucket smooths this by capping burst to the bucket's own capacity, refilled steadily.
```

**Why it's a trap:** picking fixed window because it's the simplest to implement, without
accounting for its boundary-burst flaw, means the limit is only a soft guideline at exactly the
moment traffic is most bursty — the opposite of when it needs to actually hold.

#### Q11. Why does a browser request fail with a CORS error even though the API works in curl, and how do preflights and cookies (`SameSite`) change the picture?
**Answer:** CORS is enforced by the **browser**, not the server or network: `curl` and server-to-server calls never
see it. When a page on `https://app.example.com` calls `https://api.example.com`, the browser only lets
JavaScript read the response if the API returns matching `Access-Control-Allow-Origin` headers. For
"non-simple" requests — a method other than `GET`/`POST`/`HEAD`, a `Content-Type: application/json`, or a custom header like
`Authorization` — the browser first sends a **preflight** `OPTIONS` request with `Access-Control-Request-Method/Headers`,
and the server must answer `2xx` with `Access-Control-Allow-Methods/Headers` (cacheable with `Access-Control-Max-Age`) or the real
request is never sent. The classic mistakes: the preflight is blocked by authentication (the `OPTIONS` carries no
credentials, so a security filter answers `401` and CORS "fails"), a wildcard `*` origin combined with credentials
(not allowed — with `Access-Control-Allow-Credentials: true` you must echo one explicit origin and add
`Vary: Origin`), a reverse proxy that strips or duplicates the CORS headers, and error responses (`500`, `502`
from a gateway) that lack CORS headers so the browser reports "CORS error" and hides the real status. Cookies add a second layer: a cookie is sent
on cross-site requests only if it is `SameSite=None; Secure` (the default is `Lax`), the request sets
`credentials: "include"`, and the server allows credentials; third-party cookie restrictions in browsers may block it anyway,
so prefer same-site deployment (api.example.com and app.example.com share the site `example.com`) or a
same-origin reverse proxy that removes CORS from the problem.

**Example:**
```java
// Spring Security: CORS must be handled *before* the auth filter, or the preflight gets a 401.
@Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
    return http.cors(Customizer.withDefaults())
               .authorizeHttpRequests(a -> a.anyRequest().authenticated())
               .build();
}
@Bean CorsConfigurationSource cors() {
    var c = new CorsConfiguration();
    c.setAllowedOrigins(List.of("https://app.example.com"));   // explicit origin, not "*"
    c.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
    c.setAllowedHeaders(List.of("Authorization", "Content-Type"));
    c.setAllowCredentials(true);
    c.setMaxAge(Duration.ofHours(1));
    var s = new UrlBasedCorsConfigurationSource();
    s.registerCorsConfiguration("/**", c);
    return s;
}
```

**Why it's a trap:** developers "fix" it with `Access-Control-Allow-Origin: *` or by disabling the browser's checks,
which either fails as soon as credentials are involved or weakens security (reflecting any `Origin`
back with credentials lets any site call the API as the logged-in user). CORS is also *not* a security
control against non-browser clients or CSRF — it only relaxes the same-origin policy, so authentication and
CSRF protections still matter.

#### Q12. JWT in `localStorage`, JWT in an `HttpOnly` cookie, or a server-side session — what are the trade-offs and pitfalls?
**Answer:** A **server-side session** stores state (user, roles) on the server and gives the browser an opaque id in a
cookie: revocation is trivial (delete the session), the client never holds claims, but it needs shared
storage (Redis) when scaled out. A **JWT** is a signed, self-contained token verified without a lookup, which
is convenient across services, but the flip side is that it **can't be revoked before it expires**, its
claims are visible to anyone (signed, not encrypted), and stale roles stay valid until expiry. Where you keep
it matters most: in `localStorage` any XSS can read and exfiltrate it; in an `HttpOnly; Secure; SameSite` cookie JavaScript
can't read it, but cookies are sent automatically, so you need CSRF protection (`SameSite=Lax/Strict`, CSRF tokens). Common
JWT mistakes: accepting `alg: none` or letting the token choose its own algorithm (pin the algorithm and key), not
validating `iss`/`aud`/`exp`, long-lived access tokens, storing sensitive data in claims, and using a shared HMAC secret across
services. The usual sound design is a **short-lived access token (5–15 min) plus a rotating refresh token** held in an
`HttpOnly` cookie, with refresh-token reuse detection, plus a server-side deny-list only for the emergency case. For a
browser-facing first-party app, a plain session cookie is often simpler and safer than JWTs; JWTs earn their place for service-to-service
calls and third-party APIs (OAuth2/OIDC).

**Example:**
```http
Set-Cookie: refresh=9f2c...; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh; Max-Age=1209600

# Access token: short-lived, sent in memory only:
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjIwMjYtMDEifQ...
# Verifier must pin: alg=RS256, iss=https://id.example.com, aud=orders-api, and check exp/nbf with a small clock skew.
```

**Why it's a trap:** "stateless JWT" is sold as scalable and simple, but teams discover it cannot log out a stolen token,
that permission changes lag by the token lifetime, and that the `localStorage` convenience turns every XSS into
an account takeover. The right answer names the threat model (XSS vs CSRF vs theft) rather than declaring one mechanism the winner.

### Docker

#### Q13. Why does Dockerfile instruction order matter for both cache efficiency and final image size, and what does a multi-stage build solve?
**Answer:** Per Q3's caching mechanics, instructions should be ordered from least-frequently-
changing (installing OS/system dependencies) to most-frequently-changing (copying application
source) so routine code changes invalidate only the last few layers, not the whole build.
Multi-stage builds solve a separate problem: compiling/building an application often needs tools
(a JDK, build caches, `node_modules` including devDependencies) that the *running* application
doesn't need at all — a multi-stage Dockerfile builds in one stage with the full toolchain, then
copies only the final build artifact (a jar, a compiled binary, the built static assets) into a
fresh, minimal final stage (`FROM eclipse-temurin:21-jre-alpine`, not the full JDK image), so the
shipped image doesn't carry the entire build toolchain's weight and attack surface into
production.

**Example:**
```dockerfile
# Single-stage: ships the entire JDK + build cache into production.
FROM eclipse-temurin:21-jdk
COPY . .
RUN mvn package

# Multi-stage: only the final artifact crosses into the runtime image.
FROM eclipse-temurin:21-jdk AS build
COPY . .
RUN mvn package

FROM eclipse-temurin:21-jre-alpine
COPY --from=build /app/target/app.jar .
```

**Why it's a trap:** "the build works, the image runs" is treated as the finish line — but a
single-stage Dockerfile silently ships the entire build toolchain (and its attack surface) into
production, an issue that looks purely cosmetic (image size) until it becomes a real security or
cost problem.

#### Q14. Walk through diagnosing a Docker container that exits with code 137.
**Answer:** Exit code 137 is 128 + 9 (`SIGKILL`, signal 9) — the container's main process was
forcibly terminated by an external force, not shut down gracefully by its own logic, and logs are
often empty precisely because a `SIGKILL` gives the process no chance to flush or log anything on
the way out. The most common cause is the OOM killer: the container exceeded its memory limit (or
the host is under severe memory pressure), and the kernel killed the process to protect the
system. Diagnosis: run `docker inspect` on the stopped container and check the `OOMKilled` field
under `State` — if `true`, confirmed; the fix is raising the container's memory limit (if it was
merely undersized) or fixing an actual memory leak in the application if usage climbs
unboundedly rather than plateauing. If `OOMKilled` is `false`, check host-level kernel logs
(`dmesg`, `journalctl -k`) for signs of an external kill — a `docker stop` timing out past its
grace period and escalating to `SIGKILL`, or an orchestrator (Kubernetes) evicting the pod for
its own resource-pressure reasons.

**Example:**
```
$ docker inspect mycontainer --format '{{.State.OOMKilled}}'
true
```

**Why it's a trap:** treating an empty log as "no evidence, so it must be something obscure" — an
empty log after a 137 exit is the *expected* signature of `SIGKILL`, not a mystery; checking
`OOMKilled` in `docker inspect` first is faster than combing through application logs that were
never going to contain anything.

#### Q15. Why might an application fail only inside a Docker container, but work fine run directly on the host?
**Answer:** Common causes: a hardcoded `localhost` reference that meant "this same machine" on
the host but, inside a container, refers to the container's own isolated network namespace rather
than another service the container needs to reach (which instead needs a service name/container
network alias, or `host.docker.internal` in specific setups); a file permission mismatch, since a
container's default user (sometimes `root`, sometimes a specific UID baked into the image) may
not match the host user's permissions on a mounted volume; a missing environment variable or
configuration file that existed on the host's environment but wasn't explicitly passed into the
container; or a base image with a different OS/library version than the host, surfacing a
dependency that was implicitly satisfied on the host but isn't present in the (often much more
minimal, e.g. Alpine-based) container image.

**Example:**
```yaml
environment:
  - DB_HOST=localhost   # meant "this same machine" on the host; inside the container this
                         # resolves to the container's own network namespace, not the DB
```

**Why it's a trap:** assuming "the code is identical, so the environment must be identical too" —
a container's network namespace, filesystem, and base image are genuinely different execution
contexts, even when running the exact same application code and binary as the host.

### Kubernetes workloads

#### Q16. What's the difference between Kubernetes liveness, readiness, and startup probes, and what happens when they're misconfigured?
**Answer:** **Liveness** answers "is this container alive, or should it be restarted" — failing
it causes Kubernetes to kill and restart the container. **Readiness** answers "can this container
currently serve traffic" — failing it removes the pod from the Service's load-balancing endpoints
without restarting it, which is the correct response to a pod that's alive but temporarily unable
to serve (warming a cache, waiting on a dependency). **Startup** exists for slow-starting
applications, delaying when liveness/readiness even begin being checked, so a legitimately slow
startup isn't mistaken for a liveness failure and killed before it ever finishes booting. The
common misconfiguration: using the same check (or no check at all, letting Kubernetes assume
"ready" immediately) for both liveness and readiness — a liveness probe that's too aggressive
(short timeout, low failure threshold) on a pod under temporary load can trigger unnecessary
restarts of an otherwise-healthy pod (a self-inflicted outage), while a missing or trivial
readiness probe sends traffic to a pod before it's actually able to handle it, causing errors
during every rollout (S4).

**Example:**
```yaml
livenessProbe:
  httpGet: { path: /healthz, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 5
readinessProbe:
  httpGet: { path: /ready, port: 8080 } # checks dependencies/warm-up, not just "process is up"
  periodSeconds: 5
```

**Why it's a trap:** reusing the same shallow check ("the process responds") for both liveness and
readiness treats two different questions — "should this be restarted" vs. "should this receive
traffic" — as one; an aggressive liveness probe built like a readiness check can restart a
healthy-but-busy pod, turning a load spike into a self-inflicted outage.

#### Q17. What happens if a Kubernetes Pod has no resource requests or limits set?
**Answer:** Without a **request** (the amount the scheduler reserves for this pod on a node), the
scheduler has no real basis for bin-packing pods sensibly, and a pod without requests is treated
as lowest priority (`BestEffort` QoS class) — the first to be evicted under node memory pressure,
even if it's actually an important workload. Without a **limit** (the hard cap enforced at
runtime), a pod can consume unbounded memory/CPU on its node — a memory leak in one unbounded pod
can starve every other pod on that node ("noisy neighbor," S11) rather than being contained to
itself, and can eventually trigger the node's own OOM killer, which doesn't necessarily kill the
offending pod specifically. Setting both deliberately (with limits comfortably above expected
steady-state usage, but bounded) is what gives Kubernetes the information it needs to schedule
fairly and contain a single workload's failure to itself.

**Example:**
```yaml
resources:
  requests: { memory: "256Mi", cpu: "250m" }
  limits: { memory: "512Mi", cpu: "500m" }
# Omit this block entirely and the pod is BestEffort QoS — first evicted, and free to
# consume unbounded resources on its node in the meantime.
```

**Why it's a trap:** treating resource requests/limits as an optional tuning knob rather than
required scheduling input — "it works fine without them in dev" is true right up until real node
contention exposes both failure modes (unfair eviction, noisy-neighbor) at once.

#### Q18. How does the Horizontal Pod Autoscaler (HPA) decide to scale, and what's a common misconfiguration?
**Answer:** The HPA periodically compares a target metric (commonly CPU or memory utilization, or
a custom metric like request queue depth) against a configured target value, and computes a
desired replica count roughly proportional to how far current usage is from the target. A common
misconfiguration: the HPA scales based on CPU utilization, but the pod has no CPU *request* set
(Q17) — utilization percentage is calculated relative to the request, so with no request defined,
the HPA has no meaningful baseline to compute against and either doesn't scale at all or behaves
unpredictably. Another common issue: scaling on a metric that doesn't actually correlate with the
real bottleneck (scaling on CPU when the service is actually I/O-bound and blocked waiting on a
downstream call, so CPU never crosses the threshold even while the service is genuinely
overwhelmed) — the fix there is scaling on a custom metric that actually reflects load (request
rate, queue depth) rather than defaulting to CPU because it's the built-in option.

**Example:**
```
$ kubectl get hpa orders-hpa
NAME         REFERENCE           TARGETS         MINPODS   MAXPODS   REPLICAS
orders-hpa   Deployment/orders   <unknown>/70%   2         10        2
```
`<unknown>` as the current value means the HPA has no CPU request baseline on the pod to compute
utilization against — it will never scale from this state no matter how loaded the service is.

**Why it's a trap:** assuming "the HPA is configured, so autoscaling works" — an HPA scaling on
CPU with no CPU request set, or scaling on CPU for a genuinely I/O-bound service, can silently
never trigger, and that gap stays invisible until a real traffic spike exposes it.

#### Q19. Walk through a Kubernetes rolling update and how `maxSurge`/`maxUnavailable` interact with graceful shutdown.
**Answer:** A rolling update replaces old-version pods with new-version pods incrementally rather
than all at once: `maxSurge` controls how many extra pods beyond the desired count can be created
temporarily during the rollout (higher = faster rollout, more resource headroom needed), and
`maxUnavailable` controls how many pods can be down at once during the transition (higher =
faster rollout, more capacity reduction tolerated meanwhile). The interaction with graceful
shutdown (module 2's Q22/S16) matters at the moment an old pod is terminated: Kubernetes sends
`SIGTERM`, and the pod has `terminationGracePeriodSeconds` to finish in-flight requests and shut
down before a hard `SIGKILL` follows — but the pod is also removed from the Service's endpoints as
part of this process, and if that endpoint removal isn't correctly sequenced *before* new
connections stop being routed to it (a `preStop` hook adding a brief delay before the app actually
starts shutting down is the standard mitigation), there's a window where the load balancer can
still route new traffic to a pod that's already stopped accepting it, causing a burst of errors
during every rollout.

**Example:**
```yaml
lifecycle:
  preStop:
    exec: { command: ["sleep", "5"] } # gives the Service time to deregister this pod first
terminationGracePeriodSeconds: 30
```

**Why it's a trap:** assuming `SIGTERM` alone is enough for a zero-error rollout — without a brief
`preStop` delay, the pod can stop accepting connections before the Service has finished removing
it from its endpoint list, causing a burst of errors on every single deployment.

#### Q20. Why isn't a Kubernetes Pod's IP address a stable thing to rely on, and what does a Service provide instead?
**Answer:** Pods are ephemeral by design — a Deployment can recreate a pod (on a crash, a rolling
update, a node failure) at any time, and the new pod gets a new IP address; hardcoding or caching
a pod IP anywhere is guaranteed to break eventually. A **Service** provides a stable virtual IP
and DNS name that load-balances across whichever pods currently match its label selector,
updating automatically as pods come and go — clients target the Service, never a pod directly.
`ClusterIP` (the default) is reachable only within the cluster; `NodePort` exposes the service on
a static port on every node, reachable from outside the cluster; `LoadBalancer` provisions an
actual external load balancer (via the cloud provider) pointing at the service, the standard way
to expose a service to the internet.

**Example:**
```yaml
apiVersion: v1
kind: Service
metadata: { name: orders-svc }
spec:
  selector: { app: orders }
  ports: [{ port: 80, targetPort: 8080 }]
# Clients target "orders-svc" — never a specific pod's IP, which changes on every recreate.
```

**Why it's a trap:** caching or hardcoding a pod IP anywhere "because it was stable during my
testing" — pod IPs are guaranteed to change on the very next reschedule, and code that assumes
otherwise works right up until the first rolling update or node failure.

#### Q21. How do you keep a Kubernetes service available during node drains and zone failures (PodDisruptionBudget, anti-affinity, topology spread)?
**Answer:** Three different failure types need three different tools. **Voluntary disruptions** — a node drain for
an upgrade, cluster autoscaler scale-down — evict pods deliberately; a **PodDisruptionBudget** (`minAvailable` or
`maxUnavailable`) tells the eviction API to refuse an eviction that would take the service below the budget, so
draining proceeds node by node without dropping capacity. A PDB does *nothing* against involuntary failures (a node crashing,
OOM kills). To survive **node and zone loss**, replicas must not all land on the same failure domain: `podAntiAffinity`
(hard `required...` or soft `preferred...`) or better, `topologySpreadConstraints` with `topologyKey: topology.kubernetes.io/zone` and
`maxSkew: 1` spread the pods evenly and keep spreading during rollouts. Combine with `replicas >= 3`, correct readiness probes, and
graceful shutdown (Q19). Pitfalls: a PDB with `minAvailable: 100%` or equal to the replica count makes the node
**un-drainable** and blocks upgrades (S21); a single-replica Deployment plus a PDB has the same problem; hard anti-affinity with
more replicas than nodes leaves pods `Pending`; and the spread rules only apply at *scheduling* time, so they don't rebalance existing pods
after nodes come and go (the descheduler does that).

**Example:**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: orders }
spec:
  maxUnavailable: 1              # never fewer than replicas-1 during drains
  selector: { matchLabels: { app: orders } }
---
# in the Deployment's pod spec
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway     # DoNotSchedule if the spread is a hard requirement
    labelSelector: { matchLabels: { app: orders } }
```

**Why it's a trap:** teams run 3 replicas, feel safe, and lose the service because the scheduler put all three on one node,
or "harden" with an over-strict PDB that later blocks every cluster upgrade at 2 a.m. High availability is a property of the
*placement and disruption policy*, not of the replica count.

#### Q22. What's the difference between a Kubernetes ConfigMap and a Secret, and what's the common misunderstanding about Secret security?
**Answer:** Both store key-value configuration injected into pods (as environment variables or
mounted files); the intended distinction is that a ConfigMap holds non-sensitive configuration and
a Secret holds sensitive data (credentials, tokens, keys). The common misunderstanding: a
Secret's values are base64-*encoded*, not encrypted — anyone with read access to the Secret
object via the Kubernetes API (or `kubectl get secret -o yaml`) can trivially decode it back to
plaintext, so a Secret alone provides no confidentiality against anyone with sufficient cluster
RBAC access, only a mild obfuscation against accidental exposure. Genuine protection requires
enabling encryption-at-rest for Secrets in etcd (not the default in every cluster setup), tightly
scoping RBAC access to Secrets, and, for stronger guarantees, integrating an actual secrets
manager (Vault, cloud-provider secret stores) rather than relying on the base Secret object as if
it were inherently encrypted.

**Example:**
```
$ kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d
SuperSecretPassword123
```

**Why it's a trap:** treating "it's stored as a Secret" as sufficient protection on its own —
without encryption-at-rest and tight RBAC, a Secret is one `kubectl get` away from plaintext for
anyone with cluster read access.

#### Q23. What problem does Helm solve over raw Kubernetes manifests?
**Answer:** Raw YAML manifests duplicate boilerplate across environments (dev/staging/prod each
needing near-identical Deployment/Service/ConfigMap files differing only in a handful of values)
and have no built-in concept of a "release" — no easy way to install, upgrade, or roll back a
whole set of related resources as one versioned unit. Helm templates the manifests
(parameterizing the differences into a `values.yaml` per environment) and tracks each
install/upgrade as a numbered release, supporting `helm rollback` to a previous release as one
command rather than manually reconstructing what the previous manifest state was. The trade-off
is added complexity (a templating layer and its own tooling/learning curve) that's worth it once
the same application needs to be deployed across multiple environments or multiple times with
variations — for a single, simple, rarely-changing deployment, raw manifests can still be the
simpler choice.

**Example:**
```
$ helm upgrade orders ./chart -f values-prod.yaml
$ helm rollback orders 4   # back to release revision 4, one command
```

**Why it's a trap:** adopting Helm (or any templating layer) for a single, simple, rarely-changing
deployment adds real complexity for no corresponding benefit — its value only shows up once the
same chart is deployed across multiple environments or multiple times with genuine variation.

### Delivery & debugging

#### Q24. What stages does a solid CI/CD pipeline need, and what does "fail fast" mean in that context?
**Answer:** Roughly, in increasing cost/time order: lint/static analysis and fast unit tests first
(cheapest, catch the most common mistakes in seconds), then a build/compile step, then
integration tests (slower, need real dependencies like a database), then security/dependency
scanning, then a deploy to a staging environment with smoke tests, then the actual production
deployment (often gated behind a canary or manual approval for critical services). "Fail fast"
means ordering stages so the cheapest, most likely-to-catch-something checks run first — a lint
failure should fail in seconds, not after waiting for a 20-minute integration test suite to
finish first — so developers get feedback as quickly as possible and expensive resources aren't
spent running later stages on a change that was already going to fail an earlier, cheaper check.

**Example:**
```yaml
stages: [lint, unit-test, build, integration-test, security-scan, deploy-staging, deploy-prod]
# lint/unit-test run first and finish in seconds; integration-test and deploy are last and
# most expensive — a lint failure should never wait behind a 20-minute test suite.
```

**Why it's a trap:** ordering pipeline stages by when they were historically added rather than by
cost — an expensive integration-test stage running before a cheap lint check wastes CI minutes
and developer feedback time on every single failing lint change.

#### Q25. Compare blue-green, canary, and rolling deployment strategies.
**Answer:** **Rolling** (Kubernetes's default, Q19) incrementally replaces old pods with new ones
— simple, resource-efficient (no need to run two full environments simultaneously), but rollback
means rolling the update back the same incremental way, and a bad version is serving *some*
traffic for the duration of the rollout before it's caught. **Blue-green** runs two complete,
independent environments (blue = current, green = new) and switches all traffic over at once
(typically at the load balancer/DNS level) once the new environment is verified — rollback is
just switching traffic back, nearly instant, but it requires double the infrastructure running
simultaneously during the transition, and any stateful component (a database schema, S15) still
needs to be compatible with both environments during the switch. **Canary** routes a small
percentage of real traffic to the new version first, observes real metrics/errors from that
subset, and gradually increases the percentage if healthy (or rolls back the canary immediately
if not) — the best real-world signal before a full rollout, at the cost of more deployment
complexity and the requirement that both versions coexist safely for the duration (S12's
schema-compatibility trap applies here too).

**Example:**
```
Rolling:    old -> [old,new] -> [new] over N steps        (partial exposure during rollout)
Blue-green: [blue] -> [blue,green verified] -> [green]    (instant switch, double infra)
Canary:     [old 95%, new 5%] -> ... -> [new 100%]        (real-traffic validation first)
```

**Why it's a trap:** picking a strategy because it's "the modern one" (canary, blue-green)
without accounting for its actual cost — blue-green's double infrastructure and schema-
compatibility burden, or canary's requirement that both versions coexist safely — can be worse
than a well-tested rolling update for a system that doesn't actually need the extra safety.

#### Q26. How do you use `git bisect` to find which commit introduced a regression?
**Answer:** `git bisect start`, then mark a known-bad commit (`git bisect bad <hash>`, often just
`HEAD` or the current broken state) and a known-good commit (`git bisect good <hash>`, a point
before the bug existed) — git checks out the midpoint commit between them, and you test it and
report `git bisect good` or `git bisect bad`, repeating until git narrows it down to the exact
commit that introduced the regression, in O(log n) steps rather than checking every commit
individually. If the "test" step (does this commit exhibit the bug) can be scripted (a specific
failing test, a command with a distinguishable exit code), `git bisect run <command>` automates
the entire process end-to-end without manual checkout/test/report cycles. `git bisect reset`
returns the repository to its original state once the culprit commit is identified.

**Example:**
```
$ git bisect start
$ git bisect bad HEAD
$ git bisect good v2.3.0
$ git bisect run ./run-failing-test.sh
```

**Why it's a trap:** manually eyeballing "which of these 200 commits looks suspicious" instead of
bisecting wastes exactly the log-n advantage bisect gives for free — and skipping
`git bisect run` in favor of manual checkout/test cycles turns a scriptable, 8-step process into a
slow, error-prone manual one.

### Observability

#### Q27. Put the three pillars of observability into practice — what does "good" actually look like for each?
**Answer:** **Structured logging**: emit logs as structured data (JSON, not free-text) with
consistent fields (a request/trace ID, service name, severity) so they're searchable and
correlatable across services, not just human-readable one at a time. **Metrics**: the RED method
for request-driven services (Rate, Errors, Duration — per endpoint) and the USE method for
resources (Utilization, Saturation, Errors — per CPU/memory/disk/queue) give a structured,
repeatable checklist for what to instrument, rather than an ad-hoc collection of whatever metrics
happened to seem interesting at the time. **Distributed tracing**: propagate a trace ID across
every hop (HTTP headers, message metadata for async hops — module 4's messaging content) using a
standard (OpenTelemetry) so a single request's full path and timing across services is
reconstructible, not just each service's isolated view.

**Example:**
```json
{"ts":"2024-03-11T10:00:00Z","level":"error","service":"orders","traceId":"a1b2c3","msg":"payment failed"}
```

**Why it's a trap:** treating "we have logs" as equivalent to "we have observability" —
unstructured, untraceable logs with no shared trace ID across services still leave you manually
correlating timestamps across a dozen services during an incident, exactly the slow-diagnosis
failure mode structured logging plus tracing exists to eliminate.

## 🔴 Expert / Open

### Delivery

#### Q28. Design a CI/CD pipeline and deployment strategy for a critical payment service that needs zero downtime and fast rollback.
Pipeline: fast static analysis and unit tests first (fail fast, Q24), then integration tests
against a real (containerized, ephemeral) database and any critical downstream mocks, then a
security/dependency scan (payment services are a natural target for supply-chain and dependency
vulnerability scanning to be non-negotiable), then build a versioned, immutable artifact (a
tagged container image, never `latest`) that's the *same* artifact promoted through every
environment rather than rebuilt per environment (eliminating "built differently in prod" as a
failure class). Deployment strategy: canary (Q25) specifically for a payment-critical service,
routing a small percentage of real traffic first and watching error rate/latency against tight,
automated rollback thresholds (not just human judgment) before progressively increasing traffic
— combined with the additive-migration discipline from module 3's Q32 so the database schema is
compatible with both the old and new version throughout the canary window. Rollback needs to be a
single, fast, tested command (redirect traffic back to the previous version, which is why the
previous version's pods often aren't torn down immediately after a rollout, specifically to make
rollback near-instant) rather than a manual, error-prone unwind. Observability (Q27) with tight
alerting on the payment-critical path specifically is what makes the canary's automated rollback
threshold trustworthy in the first place — this entire design is only as good as the signal it's
making rollback decisions from.

#### Q29. How would you design environment promotion (dev → staging → production) so that what you tested is exactly what you ship?
The principle is **build once, promote the same artifact**: the CI pipeline builds one immutable container image per commit,
tags it with the commit SHA (never `latest`), pushes it, and signs it; every environment then
deploys *that digest* and differs only in **configuration** injected at deploy time (values files, ConfigMaps, secrets from a secret
manager) — never by rebuilding for each environment, which would mean production runs a binary nobody tested. Promotion is a
change in Git, not a click: with a GitOps setup (Argo CD/Flux) each environment has a directory or branch with the desired image
digest and values, and "promote" is a reviewed pull request (or an automated one after gates pass) that bumps the version in the next
environment, which yields an audit trail and a one-line rollback (revert). Gates between environments should be automated
and meaningful: staging runs the integration/contract and smoke tests plus the DB migration against a production-shaped dataset; production
rolls out progressively (canary with automatic analysis of error rate and latency, Q25) and halts or rolls back on SLO regression.
Keep environments as similar as practical (same manifests, same Helm chart, different values), use short-lived preview
environments per pull request for feedback, and treat database migrations as a separate, backward-compatible step
(expand → migrate → contract, S15) so the app and the schema can roll back independently. Trade-offs: identical
staging is costly, so decide what really needs parity (versions, topology, data volume) and accept the rest; long-lived
divergent branches per environment create drift, so prefer trunk-based development with feature flags to separate *deploy* from *release*.

### Reliability & observability

#### Q30. Design the observability stack for a new microservices platform from scratch.
Standardize instrumentation *before* services multiply — adopt OpenTelemetry as the common
standard across services for traces and metrics from day one (retrofitting consistent tracing
across a large, already-fragmented fleet is far more expensive than starting consistent), with
every service propagating trace context across both synchronous (HTTP headers) and asynchronous
(message metadata, module 4) boundaries. Structured logging (Q27) shipped to a central
aggregator (rather than each service's logs living only on its own host/pod, inaccessible once
that pod is gone) with a consistent schema including the trace ID, so a specific trace can be
cross-referenced directly to its corresponding log lines across every service it touched. Metrics
following RED/USE (Q27) scraped centrally (Prometheus or equivalent) with dashboards built around
actual service-level objectives (SLOs) rather than a raw wall of every available metric, and
alerting tied to those SLOs (symptom-based: "error rate/latency budget is being burned,"
detected from the user-facing impact) rather than purely cause-based alerts (a specific internal
metric crossing a threshold that may or may not actually be user-impacting) — symptom-based
alerting scales much better as the number of services grows, since it doesn't require anticipating
and alerting on every possible internal failure mode individually. The single highest-leverage
early decision is the tracing standard and propagation discipline, since every other pillar
becomes far more valuable once traces let you cross-reference logs and metrics to a specific
request's actual path.

#### Q31. How can SLOs and error budgets drive release decisions, and what do you do when the budget is exhausted?
An **SLI** is a measured indicator of user-visible quality (the fraction of requests that succeed and complete under 300 ms), an
**SLO** is the target for it over a window (99.9% over 30 days), and the **error budget** is the allowed failure that remains
(0.1% ≈ 43 minutes of full downtime per month). The budget turns the argument "ship faster" vs "be more reliable" into a shared, data-driven rule:
while budget remains, teams can take risk — deploy often, run experiments, do migrations; when it is burning too fast, feature
releases slow and engineering effort shifts to reliability work until it recovers. To make it operational: define SLIs from the user's viewpoint (not CPU),
alert on **burn rate** with multiple windows (a fast burn pages immediately, a slow burn opens a ticket) instead of on raw thresholds
that flap (S22), and let the deployment pipeline consult the budget — progressive delivery halts a canary that consumes budget too quickly
(Q25). Agree beforehand on the **policy** for exhaustion (freeze non-critical releases, prioritize the postmortem's action items) and get product
and engineering leadership to sign it, or it becomes toothless. Pitfalls: a 99.99% SLO nobody needs (each extra nine costs disproportionately
more), SLOs on internal components no user notices, budgets that are never enforced, and measuring at the server while ignoring what the
client experiences. A good answer also notes that a service *too* reliable (a permanently untouched budget) is a signal to release faster or relax the SLO.

#### Q32. Walk through debugging a "works on my machine, fails in CI/production" issue end to end.
Start by establishing exactly *where* the divergence happens — reproduce the failure in the
target environment directly if at all possible (don't debug blind from logs alone if you can get
a shell in the failing container/pod). Systematically compare the two environments along the axes
that commonly differ: environment variables and configuration (Q15, module 2's S1/S3), base
image/OS/library versions if one runs in Docker and the other doesn't, file permissions and
mounted volume ownership, and timezone/locale defaults (a classic silent difference between a
developer's host locale and a minimal container's default `C` locale, breaking date parsing or
sorting in subtle ways). If the divergence is genuinely a recent regression rather than an
environment difference, `git bisect` (Q26) — run against the specific environment where it
actually fails, not locally — narrows down the exact introducing commit efficiently rather than
manually reviewing a large diff. Once isolated, the fix is usually one of: making the two
environments more consistent (running the same containerized environment locally that CI/
production uses, removing the "works on my machine" class of bug at the source), or fixing an
actual environment-dependent bug the code shouldn't have had (a hardcoded assumption about
locale, timezone, or network reachability).

### Security

#### Q33. How should application secrets be managed in Kubernetes — Kubernetes Secrets, Vault, or an external secrets operator?
Start from the threats: secrets committed to Git, secrets readable by anyone with cluster access, long-lived credentials that never rotate,
and no audit trail. Plain Kubernetes `Secret` objects are base64, not encryption (Q22): they need encryption at rest
(KMS provider), tight RBAC (who can `get secrets` in a namespace), and they still have to *originate* somewhere — committing
them to Git is the wrong place. The mainstream patterns keep the source of truth in an external manager (AWS Secrets Manager, GCP
Secret Manager, Azure Key Vault, HashiCorp Vault): the **External Secrets Operator** (or the CSI Secrets Store driver) syncs
selected secrets into the cluster as `Secret`s or mounted files, authenticated by the workload's identity (IRSA/Workload Identity), so no static
credentials sit in the manifests; **Sealed Secrets/SOPS** let you keep *encrypted* secrets in Git for GitOps when you don't
run an external manager. **Vault** goes further with **dynamic, short-lived credentials** (a database user created on demand
with a 1-hour lease) and detailed audit logs, at the price of operating Vault (HA, unsealing, upgrades). Design rules: give each workload its own identity and least
privilege, prefer mounted files over environment variables (env vars leak into crash dumps, `docker inspect` and child processes),
make the application able to **reload rotated secrets** without a redeploy, rotate on a schedule and immediately on suspicion of leakage,
and scan repos and images for committed secrets (S9). Choose by team size: a small team on one cloud is well served by the cloud secret
manager plus External Secrets; Vault pays off when you need dynamic credentials, multi-cloud consistency and strong audit requirements.

## 🎯 Real-world scenarios

### S1. A container repeatedly dies with exit code 137, and logs show nothing useful
- **Symptoms:** `docker ps -a` shows exit code 137 on a container that stopped abruptly; no
  application logs captured the shutdown.
- **Diagnosis:** Run `docker inspect` on the stopped container and check `State.OOMKilled` — if
  `true`, the container exceeded its memory limit and the kernel's OOM killer terminated it with
  `SIGKILL`, which gives no opportunity to log anything on the way out (Q14).
- **Example:**
  ```
  $ docker inspect mycontainer --format '{{.State.OOMKilled}}'
  true
  ```
- **Resolution:** If usage plateaus below a reasonable ceiling but the current limit is simply too
  tight, raise the memory limit. If usage grows unboundedly over time, that's an actual
  application memory leak (module 1's leak scenarios) needing a code fix, not a limit increase.
- **Prevention:** Load-test with realistic memory pressure before setting production limits, and
  alert on memory usage trend approaching the configured limit, not just on the OOMKill event
  after it's already happened.

### S2. An application starts successfully but immediately fails to reach a dependency, only when run inside a container
- **Symptoms:** The exact same code and config work when run directly on a developer's machine,
  but inside a Docker container, a call to what should be "the same database/service" fails to
  connect.
- **Diagnosis:** Almost always a networking assumption mismatch — `localhost` inside the
  container refers to the container's own network namespace, not the host or another container
  the way it might have on bare metal, and the dependency's actual reachable address inside the
  container network (a service name on a Docker network, or `host.docker.internal`) is different.
- **Example:**
  ```yaml
  # docker-compose.yml
  services:
    app:
      environment:
        - DB_HOST=localhost   # resolves to the app container's own namespace, not the db service
    db:
      image: postgres
  # Fix: DB_HOST=db (the service name on the same Docker network)
  ```
- **Resolution:** Replace the hardcoded `localhost` reference with the correct address for the
  container's actual network context — the dependency's service/container name if both run in
  the same Docker network, or the appropriate host-bridging address if it's genuinely on the
  host.
- **Prevention:** Never hardcode `localhost` for a dependency in configuration meant to run
  containerized — always make the target host configurable via environment variable, defaulting
  appropriately per environment.

### S3. A Kubernetes pod repeatedly enters `CrashLoopBackOff`
- **Symptoms:** `kubectl get pods` shows a pod restarting on a growing backoff interval, never
  reaching a stable running state.
- **Diagnosis:** `kubectl logs <pod> --previous` (the previous, crashed instance's logs, since the
  current instance may not have logged anything yet) usually shows the actual crash reason
  directly — a startup-time exception, a missing required environment variable/config, or a
  failing dependency check the application intentionally crashes on. If logs are empty, check
  `kubectl describe pod` for the exit reason (often OOMKilled, same diagnosis as S1, but at the
  Kubernetes-scheduling layer rather than plain Docker).
- **Example:**
  ```
  $ kubectl logs orders-7d9f8-x2k4p --previous
  Error: required env var DATABASE_URL is not set
  $ kubectl describe pod orders-7d9f8-x2k4p | grep -A2 "Last State"
  ```
- **Resolution:** Fix the underlying startup failure identified in logs, or adjust resource
  limits if it's memory-related, or fix a missing ConfigMap/Secret reference if that's the gap.
- **Prevention:** Fail fast and *loudly* on missing required configuration at startup (a clear
  error message naming the missing config), rather than a generic crash that requires digging
  through logs to identify — this turns a `CrashLoopBackOff` investigation into a five-second log
  read instead of a guessing exercise.

### S4. During a rollout, a burst of `502`/`503` errors hits users, correlating exactly with new pods coming online
- **Symptoms:** Errors spike specifically during deployments, for requests routed to newly-created
  pods, and resolve once the rollout finishes.
- **Diagnosis:** The readiness probe (Q16) isn't accurately reflecting when the pod can actually
  serve traffic — either it's missing entirely (Kubernetes assumes ready immediately on
  container start) or it's checking something too shallow (process is up) rather than something
  that actually reflects readiness (dependencies connected, caches warmed, the actual health
  endpoint the application exposes for this purpose).
- **Example:**
  ```yaml
  # Missing entirely -> Kubernetes routes traffic the instant the container process starts:
  # readinessProbe: (none configured)
  ```
- **Resolution:** Add or fix the readiness probe to check a meaningful health endpoint that only
  returns success once the application is genuinely able to serve traffic (dependencies
  connected, any required warm-up complete), so Kubernetes doesn't route traffic to the pod until
  that's true.
- **Prevention:** Treat a correct readiness probe as a required part of shipping any new service,
  tested specifically by observing a rollout under load in staging before it's trusted in
  production — this class of bug is invisible until a real rollout under real traffic exposes it.

### S5. A deployment causes a burst of errors specifically at the moment old pods are terminated, not when new ones start
- **Symptoms:** Distinct from S4 — errors correlate with pod *termination* during rollout, not
  pod startup, and affect requests that were presumably already in flight or newly routed right
  as the old pod stopped.
- **Diagnosis:** This is the graceful-shutdown/endpoint-deregistration race from Q19 — the load
  balancer/Service hasn't finished removing the terminating pod from its routing table before
  the pod actually stops accepting connections, so some requests land on a pod that's already
  shutting down.
- **Example:**
  ```yaml
  # Missing preStop delay -> the pod can stop accepting connections before the Service
  # finishes deregistering it:
  terminationGracePeriodSeconds: 30
  # lifecycle.preStop: (none configured)
  ```
- **Resolution:** Add a `preStop` hook with a brief sleep before the application begins its own
  shutdown sequence, giving the Service/load balancer's endpoint update time to propagate before
  the pod actually stops accepting new connections, combined with `terminationGracePeriodSeconds`
  large enough for in-flight requests to finish.
- **Prevention:** Test rollouts under continuous synthetic load in staging specifically watching
  for a zero-error-rate guarantee through the full deployment cycle — this class of race is easy
  to miss without deliberately generating traffic exactly through a deployment.

### S6. A single client's excessive request volume degrades response times for every other client of a shared API
- **Symptoms:** Overall API latency and error rate spike, and investigation traces the bulk of the
  volume to one client/API key making far more requests than any reasonable normal usage.
- **Diagnosis:** No rate limiting (Q10) is in place on the affected endpoint(s), so one client's
  excessive (whether abusive or simply buggy — a retry loop without backoff, per module 1's Q's
  scenario territory) traffic consumes shared capacity (thread pool, database connections) that
  every other client also depends on.
- **Example:**
  ```
  # Access log aggregated by API key over the last hour:
  api-key-a7f3: 480,000 requests
  api-key-b2e1: 1,200 requests
  ```
- **Resolution:** Add rate limiting per client/API key immediately as a mitigation (even a coarse
  limit stops the bleeding), and separately follow up with the offending client if it's a known
  partner/integration to fix their retry/traffic pattern at the source.
- **Prevention:** Rate limiting per client should be a standard, non-optional part of any
  public-facing (or even internal, multi-team) API's design from launch — retrofitting it during
  an active incident is strictly worse than having it from day one.

### S7. A regression is reported, but it's unclear which of the last two months of commits introduced it
- **Symptoms:** A bug is confirmed present now and confirmed absent in a build from a couple
  months ago, but the intervening history has hundreds of commits and no obvious suspect.
- **Diagnosis/resolution:** `git bisect start`, mark the current commit `bad` and the known-good
  older commit `good` (Q26) — git checks out the midpoint, test it (ideally scripted via
  `git bisect run` against an automated reproduction of the bug), mark `good`/`bad`, and repeat;
  for hundreds of commits, this typically converges in under 10 steps (log2 of the commit count)
  rather than requiring a manual, linear review of the whole range.
- **Example:**
  ```
  $ git bisect start
  $ git bisect bad HEAD
  $ git bisect good v3.4.0
  $ git bisect run ./reproduce.sh
  # Converges on the exact commit in ~8 steps instead of reviewing 300 commits by hand.
  ```
- **Prevention:** Keep commits reasonably small and focused (a bisect that lands on a 2,000-line
  commit touching a dozen unrelated things is far less useful than one landing on a small,
  single-purpose commit), and maintain a fast, reliable way to test "does this specific commit
  exhibit the bug" (an automated repro) so `git bisect run` can fully automate the search instead
  of requiring manual testing at every step.

### S8. CI passes cleanly on every check, but the feature breaks immediately in production
- **Symptoms:** All automated tests and quality gates are green, yet the deployed feature fails
  for real users in a way none of the test suite caught.
- **Diagnosis:** Look for an environment-parity gap between CI/test and production — a test
  double/mock standing in for a dependency that behaves differently from the real one in
  production, a config or feature flag that's different between test and prod (a feature gated
  off in test but on in prod, or vice versa), or simply a genuine test coverage gap for the
  specific path that broke.
- **Example:**
  ```yaml
  # CI config points at a mock with no timeout enforcement:
  PAYMENT_GATEWAY_URL: http://mock-gateway:8080
  # Production points at the real gateway, which enforces a stricter timeout the mock never did.
  ```
- **Resolution:** Reproduce the failure with a new test that would have caught it (confirming the
  actual gap, not just guessing), fix the underlying bug, and specifically evaluate whether the
  test environment needs to more closely mirror production for the class of dependency/config
  that caused this gap.
- **Prevention:** Periodically audit where test and production environments diverge (mocked
  dependencies, differing config/feature flags) as a deliberate exercise, rather than only
  discovering each gap reactively after it causes a production incident.

### S9. Database credentials from a Kubernetes Secret end up posted in a team chat or ticket, treated as if that were safe
- **Symptoms:** Someone shares `kubectl get secret db-creds -o yaml` output (or the base64-decoded
  value) in a chat channel or support ticket, apparently under the assumption that a "Secret" is
  inherently protected.
- **Diagnosis:** This confirms the Q22 misunderstanding directly — base64 is encoding, not
  encryption, trivially reversible by anyone, and treating a Secret's contents as safe to share
  because "it's a Secret object" is exactly the false sense of security the base64-not-encrypted
  distinction warns against.
- **Example:**
  ```
  $ kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d
  SuperSecretPassword123
  ```
- **Resolution:** Rotate the exposed credential immediately, the same as any other leaked secret
  (module 2's S10 applies identically here), and remove/redact the shared message where possible.
- **Prevention:** Train the team explicitly that Kubernetes Secrets are access-controlled, not
  encrypted-by-default containers — enable encryption-at-rest for Secrets in the cluster, and
  treat any Secret's decoded value with the same handling discipline as a plaintext password,
  never pasted into chat or tickets.

### S10. Autoscaling doesn't kick in despite the service clearly being under heavy load
- **Symptoms:** Latency and error rate climb under high traffic, but `kubectl get hpa` shows the
  replica count unchanged, or scaling far more slowly than the load would justify.
- **Diagnosis:** Check whether the pods have a CPU/memory *request* configured at all — the HPA's
  utilization percentage is computed relative to the request, and without one, the HPA has no
  baseline to scale against (Q18). Separately, check whether the metric being scaled on actually
  reflects the real bottleneck — if the service is I/O-bound (blocked on a slow downstream call)
  rather than CPU-bound, CPU utilization can stay well under the scaling threshold even while the
  service is genuinely saturated and failing to keep up.
- **Example:**
  ```
  $ kubectl get hpa orders-hpa
  NAME         REFERENCE           TARGETS         MINPODS   MAXPODS   REPLICAS
  orders-hpa   Deployment/orders   <unknown>/70%   2         10        2
  ```
- **Resolution:** Set explicit resource requests if missing, and switch to (or add) a custom
  metric that actually correlates with real load (request queue depth, in-flight request count)
  if CPU isn't the real constraint.
- **Prevention:** Validate that the HPA actually triggers under realistic load during load
  testing, before relying on it as the production safety net during a real traffic spike —
  "the HPA is configured" and "the HPA actually works for this service's load profile" are
  different claims.

### S11. One misbehaving pod causes unrelated pods on the same node to slow down or get evicted
- **Symptoms:** Performance degradation or unexpected evictions affect pods that have nothing to
  do with a separate service that's currently consuming unusually high memory/CPU, but all are
  co-located on the same node.
- **Diagnosis:** The offending pod has no resource limits set (Q17) — it's free to consume
  unbounded memory/CPU on the node, starving every other pod scheduled there ("noisy neighbor"),
  and depending on QoS class, an unrelated `BestEffort` or low-priority pod can be evicted first
  to relieve node pressure caused entirely by the unlimited pod.
- **Example:**
  ```
  $ kubectl top pods --sort-by=memory
  NAME          CPU(cores)   MEMORY(bytes)
  batch-job-x   1800m        7500Mi   <- no limit set, consuming most of the node
  orders-api    120m         180Mi    <- evicted first despite being unrelated and healthy
  ```
- **Resolution:** Set an appropriate memory/CPU limit on the offending pod so its resource
  consumption is contained to itself rather than the whole node, and separately fix whatever
  caused its unusually high consumption in the first place if it's not expected/normal behavior.
- **Prevention:** Require resource requests and limits on every deployed workload as a policy
  (enforced via an admission controller/policy engine, not just a code-review reminder), so a
  workload without limits can't be deployed to a shared cluster at all.

### S12. A canary release causes intermittent errors that don't correlate cleanly with either the old or new version alone
- **Symptoms:** During a canary rollout, errors appear that don't clearly implicate either version
  individually — the same request type sometimes succeeds and sometimes fails, seemingly
  depending on which pod it happened to hit.
- **Diagnosis:** The canary (new) and stable (old) versions are running simultaneously and are
  not actually compatible with each other at some shared boundary — commonly an API/schema
  contract change, or a shared database schema that only one of the two versions expects (module
  3's Q32 territory, but exposed by a canary rather than a rolling update) — so the specific
  behavior depends on which version's pod handled a given request or which version's assumption
  about shared state was violated.
- **Example:**
  ```java
  // Stable version expects: record ReserveRequest(String orderId, int quantity)
  // Canary now requires an extra field the stable version's deserializer rejects:
  record ReserveRequest(String orderId, int quantity, String warehouseId) {}
  // Whichever pod handles a given request determines whether it succeeds or fails.
  ```
- **Resolution:** Roll back the canary immediately (this is exactly the failure mode canary
  deployments are designed to catch before full rollout), and redesign the change to be genuinely
  backward/forward compatible for the duration both versions must coexist, before attempting the
  canary again.
- **Prevention:** Explicitly verify compatibility between the new and old version for every shared
  dependency (API contracts, database schema, message formats) as a required check before any
  canary or blue-green deployment that requires both versions to coexist even briefly — this
  isn't optional just because the coexistence window is short.

### S13. An outage is diagnosed slowly because it's unclear which of many services in the request path is actually responsible
- **Symptoms:** A user-facing incident is confirmed real, but with a dozen microservices in the
  request path and each team checking only their own service's dashboards, no one can quickly
  pinpoint where the actual fault originates.
- **Diagnosis:** No centralized, correlatable observability exists across the services — logs
  live only per-service with no shared trace ID connecting them, and there's no distributed
  tracing to show the request's actual path and where it failed or slowed (module 2's S15 at the
  application-code level, but here it's the platform-wide infrastructure gap causing it).
- **Example:**
  ```
  service-a.log: 10:02:01.442 request received
  service-b.log: 10:02:01.503 forwarded to inventory
  # No shared trace ID -> no way to confirm these two lines even belong to the same request.
  ```
- **Resolution:** Once diagnosed via manual cross-team log comparison (slow, but the only option
  without tracing already in place), fix the immediate incident, and treat this incident as the
  forcing function to actually implement distributed tracing platform-wide.
- **Prevention:** Build the observability stack (Q30) — consistent trace propagation, centralized
  structured logging, RED/USE metrics — before the platform grows to a scale where this
  investigation becomes routine and expensive; retrofitting it after several of these incidents
  costs far more than building it in from an early, smaller scale.

### S14. Docker images have grown large enough to noticeably slow down CI/CD pipeline runs and deployments
- **Symptoms:** Build, push, and pull times for the application's Docker image have grown
  steadily, adding real minutes to every CI run and every deployment.
- **Diagnosis:** Check whether the final image includes the full build toolchain (a JDK plus
  Maven's dependency cache, `node_modules` with devDependencies, compilers) rather than just the
  runtime artifact — a common cause is a single-stage Dockerfile that builds and runs in the same
  image, carrying build-time weight all the way into the shipped artifact.
- **Example:**
  ```
  $ docker images | grep myapp
  myapp   latest   1.8GB   <- includes the full JDK, Maven cache, and devDependencies
  ```
- **Resolution:** Convert to a multi-stage build (Q13) — build in a full-toolchain stage, then
  copy only the final artifact into a minimal runtime base image, dramatically shrinking the final
  image size without changing the build process's own capabilities.
- **Prevention:** Default new services' Dockerfiles to a multi-stage pattern from the start, and
  track image size as a metric in CI (failing or warning on a significant unexpected increase)
  the same way build time or bundle size might be tracked.

### S15. After a blue-green deployment is rolled back, the application still fails, because the database schema it expects doesn't match what's actually running
- **Symptoms:** A rollback to the previous (blue) application version is expected to instantly fix
  an issue found in the new (green) version, but the rolled-back version now fails against the
  database, which was already migrated for the green version's schema requirements.
- **Diagnosis:** The deployment's migration step wasn't designed with rollback in mind — the new
  version's schema migration was applied and isn't backward-compatible with the old version's
  expectations, so "rolling back the application" alone doesn't actually restore a fully working
  state, since the database is still in the new schema.
- **Example:**
  ```sql
  -- Applied for green, not safe for blue, which still reads/writes this column:
  ALTER TABLE orders DROP COLUMN legacy_status;
  ```
- **Resolution:** Either roll the database migration back too (risky and not always possible if
  data was written in the new schema's shape in the meantime), or — the safer approach —
  redesign the migration to have been additive and backward-compatible in the first place (module
  3's Q32 pattern), so the old application version continues working correctly against the
  already-migrated schema without needing a database-level rollback at all.
- **Prevention:** Treat "is this migration safe for the previous application version to keep
  running against, in case of rollback" as a required question for any migration shipped
  alongside a blue-green or canary deployment — a deployment strategy that assumes instant
  rollback only actually delivers that if every accompanying schema change was designed the same
  way.

### S16. A load-balancer switch during a blue-green cutover drops long-lived client connections abruptly
- **Symptoms:** Clients with long-running or sticky connections (WebSocket sessions, long-polling
  requests, connections pinned to a specific backend by session affinity) are abruptly
  disconnected at the exact moment traffic is switched from blue to green, even though the
  cutover was otherwise "instant."
- **Diagnosis:** The cutover redirected new connections correctly, but didn't account for
  *existing* long-lived connections still attached to the old (blue) environment — an instant
  traffic switch at the load-balancer level doesn't gracefully drain connections that are
  expected to persist for minutes or hours, it just stops routing to blue immediately, effectively
  killing them.
- **Example:**
  ```
  # At cutover, the load balancer stops routing to blue immediately — a WebSocket client
  # mid-session on blue receives a hard connection reset, not a graceful close frame.
  ```
- **Resolution:** For the specific connections already in progress, implement a connection-drain
  period — keep the blue environment running and reachable for existing connections for a bounded
  window after the cutover (new connections go to green immediately, existing ones on blue are
  allowed to complete or gracefully reconnect to green on their own terms) rather than an
  instantaneous hard cutover for every connection regardless of its lifecycle.
- **Prevention:** Explicitly account for long-lived/stateful connection types as a distinct
  requirement when designing a blue-green (or any traffic-switching) deployment strategy — a
  strategy that only considers short-lived request/response traffic will systematically break
  this class of client, and it needs to be a named part of the design, not an edge case discovered
  in production.

### S17. Latency spikes every few seconds and p99 is 10x the median, yet CPU usage looks low and there are no errors
- **Symptoms:** An API's p99 response time is 2 s while the median is 80 ms, in a regular sawtooth pattern. The pod's CPU
  graph is well below the limit (~40%), memory is fine, no restarts, no error logs. Adding replicas helps only a little.
- **Diagnosis:** Average CPU usage hides **CFS throttling**. A CPU *limit* (say `500m`) is enforced in 100 ms periods:
  a multi-threaded process (JVM GC threads, a burst of requests) can consume its 50 ms quota in the first 20 ms of the
  period and is then *frozen* for the rest of it — requests stall although the 1-minute average looks low. Look at
  `container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total` (or `nr_throttled` in
  `/sys/fs/cgroup/cpu.stat`): a ratio of several percent to tens of percent confirms it, and the latency spikes line up with throttled periods (Q17).
- **Example:**
  ```yaml
  resources:
    requests: { cpu: "250m", memory: "512Mi" }
    limits:   { cpu: "500m", memory: "512Mi" }   # tight CPU limit on a bursty, multi-threaded JVM
  ```
- **Resolution:** Raise or remove the CPU *limit* while keeping a realistic *request* (many teams set CPU requests but no CPU limits, since CPU is
  compressible and requests already guarantee a fair share; memory limits stay). Tune the runtime to the container (JVM `-XX:ActiveProcessorCount`, thread pool sizes
  matched to the cores actually granted). Verify that the throttling ratio drops near 0 and p99 converges toward the median under the same load.
- **Prevention:** Dashboard and alert on throttling ratio, not just utilization; load-test with the production resource
  settings; make "set requests from measurement, be careful with CPU limits" a platform default.

### S18. A new deployment is stuck in `ImagePullBackOff` / `ErrImagePull` and the rollout never completes
- **Symptoms:** After a release, new pods stay in `ImagePullBackOff` while the old ones keep serving (the rolling
  update stalls, which is the safe part). `kubectl rollout status` times out; the pipeline reports success because the manifest was applied.
- **Diagnosis:** `kubectl describe pod` — the Events say exactly why. Typical causes: a **wrong tag or a tag that was never pushed**
  (the pipeline deployed before the push finished, or a typo), a private registry with **missing/expired `imagePullSecrets`** (`pull access denied`, `401`), a node that can't reach the registry
  (network policy, egress firewall, DNS), a registry **rate limit** (`toomanyrequests` from Docker Hub for anonymous pulls from many nodes), or an architecture
  mismatch (an `arm64` image on `amd64` nodes: `no matching manifest`). Try `docker pull` from a node/debug pod with the same credentials.
- **Example:**
  ```text
  Warning  Failed  kubelet  Failed to pull image "registry.example.com/orders:1.4.2":
           rpc error: code = Unknown desc = failed to resolve reference: pull access denied, ... 401 Unauthorized
  ```
- **Resolution:** Fix the specific cause — push the missing tag, refresh the pull secret (`kubectl create secret docker-registry ...` and reference it in the
  ServiceAccount), allow egress, mirror base images to your own registry, or publish a multi-arch manifest. Pods then retry with backoff automatically; if not,
  `kubectl rollout restart`. Verify with `kubectl rollout status` reaching success and all pods `Ready`.
- **Prevention:** Deploy by immutable digest/SHA tag only after the push step succeeded; make the pipeline **wait for `rollout status`** and fail (and roll back) on
  timeout with `progressDeadlineSeconds`; pull through a caching registry mirror; rotate registry credentials with automation and alert on their expiry.

### S19. Calls to external hosts take ~5 seconds intermittently, and service-to-service calls are slow, but only inside the cluster
- **Symptoms:** An application that calls `api.partner.com` sees random 5-second delays or "unknown host" errors under load; the same
  call from a laptop takes 50 ms. Latency dashboards show a fat tail with a suspicious round number: 5 s (sometimes 2.5 s or 10 s).
- **Diagnosis:** Time DNS separately: `kubectl exec ... -- time nslookup api.partner.com` and check the CoreDNS pods' logs, CPU, and request/latency metrics. Two frequent
  causes: **`ndots:5`** — in a pod `/etc/resolv.conf` a name with fewer than 5 dots is first tried with every search suffix
  (`api.partner.com.default.svc.cluster.local`, `...svc.cluster.local`, `...cluster.local`) before the real name, multiplying
  the DNS queries (and `NXDOMAIN` answers) per lookup, and an overloaded CoreDNS or a lost UDP packet turns one into a **5 s timeout** (the resolver's default retry
  interval); and the conntrack race on UDP DNS in older kernels, dropping packets under load. Apps that don't cache DNS, or that create a new connection per request, make this much worse.
- **Example:**
  ```text
  # /etc/resolv.conf inside the pod
  search default.svc.cluster.local svc.cluster.local cluster.local
  options ndots:5
  # lookup of "api.partner.com" (2 dots) -> 4 queries, 3 of them NXDOMAIN, before the final answer
  ```
- **Resolution:** Use fully-qualified names with a trailing dot (`api.partner.com.`) or lower `ndots` via `dnsConfig` for pods that mostly call
  external hosts; reuse connections (keep-alive, connection pools) so lookups are rare; scale CoreDNS and deploy **NodeLocal DNSCache** to
  cut latency and avoid the conntrack path; give the JVM/HTTP client sensible DNS TTLs. Verify by comparing DNS query counts and the p99 of
  external calls before and after.
- **Prevention:** Monitor CoreDNS latency and error rate, load-test with realistic external calls, and keep "DNS" on the incident checklist —
  "it's always DNS" is a joke because it's frequently true.

### S20. Users suddenly get browser security warnings and API clients fail with `x509: certificate has expired`
- **Symptoms:** At 02:14 on a Saturday, the site shows `NET::ERR_CERT_DATE_INVALID`, partner integrations fail their TLS handshakes,
  and internal services calling each other over mTLS start failing. No deployment happened; everything worked on Friday.
- **Diagnosis:** Check the certificate actually served, not the one you believe is configured:
  `echo | openssl s_client -connect host:443 -servername host 2>/dev/null | openssl x509 -noout -dates -issuer -subject`. Then find
  *why* renewal didn't happen: a cert-manager `Certificate`/`Order`/`Challenge` stuck failing (an HTTP-01 challenge blocked by a new redirect or
  firewall rule, DNS-01 credentials expired, ACME rate limit), a manually managed certificate nobody had in a calendar, a renewed cert that was issued but **not reloaded** by the proxy/JVM
  that loaded it at startup, or an expired internal CA / intermediate certificate.
- **Example:**
  ```bash
  kubectl get certificate,certificaterequest,order,challenge -A       # cert-manager state
  kubectl describe challenge <name>                                     # "Waiting for HTTP-01 challenge propagation: 404"
  ```
- **Resolution:** Restore service first — force renewal (`cmctl renew`) or install a new certificate manually and reload the servers/ingress — then fix the root cause (the
  challenge path, credentials, or the reload). Verify by re-running the `openssl s_client` check against every endpoint (and from an
  external vantage point) and confirming the new expiry date.
- **Prevention:** Automate issuance and renewal (cert-manager/ACME), **alert well ahead of expiry** — 30, 14 and 7 days —
  using an external probe or `x509_certificate_expires` metrics, inventory all certs (including internal CAs, client certificates
  and the ones embedded in appliances), ensure processes hot-reload certificates, and rehearse renewal in staging.

### S21. A cluster upgrade hangs for hours because a node refuses to drain
- **Symptoms:** During a node-pool upgrade, `kubectl drain` sits at `Cannot evict pod as it would violate the pod's disruption budget`
  and repeats forever. The rollout of the managed cluster times out after the provider's limit, leaving nodes on mixed versions.
- **Diagnosis:** List the blocking budgets: `kubectl get pdb -A` — look for `ALLOWED DISRUPTIONS = 0`. The usual reasons are
  a PDB with `minAvailable` equal to the replica count (or `100%`), a Deployment with **one replica** and a PDB `minAvailable: 1`,
  pods that are already unhealthy (a `CrashLoopBackOff` pod counts against availability), or a `StatefulSet` whose pod cannot be rescheduled because its
  volume is bound to a zone that has no capacity. Also check for pods with no controller ("naked" pods) and local storage, which `drain` refuses without flags (Q21).
- **Example:**
  ```yaml
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  metadata: { name: reports }
  spec:
    minAvailable: 1          # the Deployment has replicas: 1 -> zero evictions are ever allowed
    selector: { matchLabels: { app: reports } }
  ```
- **Resolution:** Unblock the upgrade by scaling the service to at least 2 replicas (or temporarily loosening the PDB), fixing the
  unhealthy pods, then draining again; as a last resort delete the pod deliberately, accepting a brief interruption for that service. Verify that `ALLOWED DISRUPTIONS >= 1` for
  every PDB and the node drains within minutes.
- **Prevention:** Use `maxUnavailable: 1` (or a percentage) rather than a fixed `minAvailable`, require
  replicas ≥ 2 for anything with a PDB, add a policy check (Kyverno/OPA) rejecting PDBs that make eviction impossible, upgrade first in a staging cluster
  with the same workloads, and schedule upgrades with the surge-node capacity to reschedule pods.

### S22. The on-call phone rings dozens of times a night for alerts that resolve themselves
- **Symptoms:** A "CPU > 80% for 1 minute" alert fires and clears 30 times a night; another pages whenever a single
  request fails. The on-call engineer has started muting the channel, and last week a real incident sat unacknowledged for 25 minutes.
- **Diagnosis:** Review the alert history: measure how many alerts were *actionable* (someone did something) against how many self-resolved.
  Flapping comes from static thresholds on noisy signals (CPU, single error), evaluation windows shorter than the signal's natural variance, alerts on **causes** instead of
  **user-visible symptoms** (high CPU is not an outage), missing `for:` durations, and alerts that cover
  the same failure many times (the pod, the node, the service and the endpoint all page for one incident).
- **Example:**
  ```yaml
  # Noisy: pages on any CPU blip, whether or not users are affected.
  - alert: HighCPU
    expr: avg(rate(container_cpu_usage_seconds_total[1m])) > 0.8
    for: 1m
  ```
- **Resolution:** Replace cause-based alerts with **symptom- and SLO-based** ones (Q31): page on a fast error-budget burn, e.g. a `5xx` ratio
  above the threshold over 5 *and* 1 hour windows, and route everything else to tickets or dashboards. Add `for:` durations, aggregation, grouping and inhibition
  (a node-down alert suppresses its pod alerts), and delete alerts nobody acts on. Verify by measuring pages per on-call shift and the share that were actionable: the goal is
  every page needs a human decision and links to a runbook.
- **Prevention:** Review alert quality in every postmortem and on-call handover, require a runbook link and an owner for each
  paging alert, keep a "pages per shift" target, and treat alert fatigue as a reliability risk in itself.

## 📌 Cheat-sheet

- **REST design**: nouns in URLs, verbs via HTTP methods, status codes carry real meaning — never `200` + error-in-body.
- **Container vs VM**: shared kernel (namespaces + cgroups), lightweight, weaker isolation vs a full separate OS, heavier, stronger isolation.
- **Docker caching**: order Dockerfile instructions least-to-most frequently changing; multi-stage builds strip build-time weight from the shipped image.
- **Exit 137** = `SIGKILL` (128+9) — check `docker inspect` → `State.OOMKilled`; empty logs are expected, not a mystery.
- **Idempotency**: `GET`/`PUT`/`DELETE` idempotent by convention; `POST` isn't — use an idempotency key for safe retries.
- **Rate limiting**: fixed window (simple, boundary-burst flaw) vs sliding window (smoother) vs token bucket (allows natural bursts) vs leaky bucket (strictly smooth output).
- **Probes**: liveness = restart if failing; readiness = remove from LB if failing, no restart; startup = delay both for slow boots. Wrong probe choice = self-inflicted outages or traffic-to-unready-pods.
- **Resource requests/limits**: no request = poor scheduling + first evicted; no limit = noisy neighbor + uncontained OOM risk.
- **HPA**: scales off utilization relative to *requests* — no request set = HPA has no baseline. Scale on the metric that actually reflects the bottleneck, not just CPU by default.
- **Rolling update**: `maxSurge`/`maxUnavailable` control rollout speed vs capacity; graceful shutdown + `preStop` delay needed so LB deregistration finishes before the pod actually stops accepting traffic.
- **`git bisect`**: mark good/bad, O(log n) steps to the culprit commit; `git bisect run <cmd>` automates it fully with a scripted repro.
- **Deployment strategies**: rolling (efficient, gradual exposure) vs blue-green (instant switch/rollback, double infra, needs schema compat both ways) vs canary (real-traffic validation before full rollout, needs version coexistence compat).
- **Observability**: metrics (is it healthy, where roughly) → traces (which hop) → logs (exact detail) — complementary, not substitutes. RED for requests, USE for resources.
- **K8s Service**: stable VIP/DNS over ephemeral pod IPs — never target a pod IP directly.
- **Secrets are base64, not encrypted** — enable encryption-at-rest, scope RBAC, never treat decoded output as safe to share.
- **Helm**: templating + versioned releases + one-command rollback, worth it once deploying across multiple environments/times.
- **CI/CD fail fast**: cheapest checks (lint, unit tests) first, expensive ones (integration, deploy) last.
</content>
- **Volumes**: writable layer dies with the container; named volume = persistent data; bind mount = dev convenience (host paths, permissions); `tmpfs` = memory-only; `docker compose down -v` deletes data.
- **`kubectl` triage order**: `get pods -o wide` → `describe` (read *Events* and *Last State*) → `logs --previous` → `exec`/`debug` → `get endpoints` for traffic issues.
- **CORS**: browser-enforced; preflight `OPTIONS` must succeed *without* auth; no `*` with credentials; error responses need CORS headers too; not a substitute for auth/CSRF.
- **Cookies & sessions**: cross-site cookies need `SameSite=None; Secure` + `credentials: "include"`; prefer same-site deployment or a reverse proxy.
- **JWT**: can't be revoked before expiry, claims are readable — short-lived access token + rotating refresh token in an `HttpOnly` cookie; pin `alg`, validate `iss`/`aud`/`exp`.
- **PDB + spread**: PDB protects against *voluntary* disruption only; `topologySpreadConstraints` for zone/node failure; an over-strict PDB makes nodes un-drainable.
- **Promotion**: build once, promote the same digest; environments differ only by config; promotion = a Git change (GitOps); DB migrations backward-compatible.
- **Secrets**: Secrets are encoded, not encrypted — external manager + External Secrets/CSI, per-workload identity, mounted files over env vars, rotation and reload, Vault for dynamic credentials.
- **SLO / error budget**: SLIs from the user's view, budget = 1 − SLO; alert on multi-window burn rate; predefine what happens when it is exhausted.
- **CPU limits cause throttling** — p99 spikes with low average CPU; watch `cfs_throttled_periods`, keep requests realistic, be cautious with CPU limits.
- **`ImagePullBackOff`**: read the Events — wrong tag, pull secret, registry rate limit, arch mismatch; pipeline must wait for `rollout status`.
- **DNS in pods**: `ndots:5` multiplies lookups, 5 s = resolver timeout; FQDN with trailing dot, connection reuse, NodeLocal DNSCache.
- **Certificates**: automate renewal, alert at 30/14/7 days, ensure reload, inventory internal CAs and mTLS certs; verify with `openssl s_client`.
- **Alert fatigue**: page on user-visible symptoms/SLO burn, not causes; add `for:`, grouping and inhibition; every page needs an owner and a runbook.
