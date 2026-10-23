# Observability Best Practices

## 📜 Logging

### Use structured (JSON) logs

Emit one JSON object per line with fixed field names, instead of free text.

**Why it's a best practice:** grepping "Order 42 failed for user ann" works on one server; with 30 pods sending
logs to Elasticsearch or Loki, you need to filter by `orderId` and `level`. Free text needs fragile regexes
that break when someone rewords a message. Spring Boot 3.4+ supports structured logging natively.

```yaml
# ⛔ plain pattern, parsed with regexes downstream

# ✅ Spring Boot 3.4+
logging.structured.format.console: ecs     # or logstash, gelf
```

```json
{"@timestamp":"2026-03-01T10:15:30Z","log.level":"ERROR","message":"Payment failed","orderId":42,"traceId":"4bf92f35"}
```

### Use SLF4J with parameterized messages

Log with `log.info("... {}", value)`, never string concatenation or `System.out`.

**Why it's a best practice:** concatenation builds the string even when the level is disabled, which costs
CPU and allocations on hot paths. `System.out` has no level, timestamp, or routing. Placeholders are
evaluated only if the level is enabled, and a template stays constant so log tools can group similar messages.

```java
// ⛔
System.out.println("Order " + order + " saved");
log.debug("Order " + order.toJson() + " saved");

// ✅
log.debug("Order saved id={} total={}", order.id(), order.total());
```

### Choose log levels deliberately

`ERROR` = someone must act, `WARN` = unexpected but handled, `INFO` = business events, `DEBUG` = diagnostics, `TRACE` = very detailed.

**Why it's a best practice:** if everything is `ERROR`, alerts fire constantly and get muted; if a real failure
is `INFO`, nobody sees it. A user typing a wrong password is not an ERROR. Running production at `INFO` keeps
cost sane: a service logging 1 KB at 500 req/s produces about 40 GB per day at DEBUG level.

```java
// ⛔
log.error("User not found: {}", id);           // normal 404, not an error
log.info("NullPointerException", ex);

// ✅
log.info("User lookup missed id={}", id);
log.error("Payment provider unreachable orderId={}", orderId, ex);
```

### Log the exception once, with its stack trace

Pass the exception as the last argument, and log it at the place where you handle it, not at every layer.

**Why it's a best practice:** logging and rethrowing at each layer prints the same stack trace 4 times, so one
failure looks like 4 incidents. `log.error(ex.getMessage())` loses the stack trace, and the root cause with it.

```java
// ⛔
catch (Exception e) { log.error(e.getMessage()); throw e; }

// ✅ wrap and throw; log once in the exception handler
catch (SQLException e) { throw new OrderStorageException(orderId, e); }

@ExceptionHandler(OrderStorageException.class)
ProblemDetail handle(OrderStorageException ex) {
    log.error("Order storage failed orderId={}", ex.orderId(), ex);
    return ProblemDetail.forStatus(500);
}
```

### Add context with MDC

Put request-scoped values (`requestId`, `userId`, `tenant`) in the MDC in a filter, so every line carries them.

**Why it's a best practice:** in a busy service, log lines from 200 concurrent requests are interleaved, and
"Insufficient funds" alone is useless. With a correlation id, one search shows the full story of one request.
Clear the MDC at the end, because threads are pooled and stale values leak into the next request.

```java
// ✅
@Component
class RequestContextFilter extends OncePerRequestFilter {
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        MDC.put("requestId", Optional.ofNullable(req.getHeader("X-Request-Id")).orElse(UUID.randomUUID().toString()));
        try { chain.doFilter(req, res); } finally { MDC.clear(); }
    }
}
```

### Never log secrets or personal data {#never-log-secrets-or-personal-data}

Mask passwords, tokens, card numbers and personal data, and avoid logging whole request bodies.

**Why it's a best practice:** logs are shipped to third parties, retained for months, and readable by many
engineers. A leaked bearer token in logs is a valid credential; personal data in logs raises GDPR obligations.

```java
// ⛔
log.info("Request: {}", request);        // contains password, card number

// ✅
log.info("Checkout started userId={} items={}", user.id(), cart.size());
```

## 📊 Metrics

### Expose metrics with Micrometer and Prometheus

Add `spring-boot-starter-actuator` and `micrometer-registry-prometheus`, then scrape `/actuator/prometheus`.

**Why it's a best practice:** logs tell you what happened once; metrics tell you how the system behaves over
time, cheaply. JVM memory, GC, thread pool, HTTP latency and DB pool usage are provided automatically and are
the first thing you check during an incident.

```yaml
# ✅
management:
  endpoints.web.exposure.include: health,info,prometheus
  metrics.tags.application: ${spring.application.name}
```

### Measure the RED and USE signals

For each service, track Rate, Errors, Duration (requests) and Utilization, Saturation, Errors (resources such as pools and queues).

**Why it's a best practice:** hundreds of metrics are useless without a checklist. RED answers "are users
suffering?", USE answers "which resource is the bottleneck?". A saturated connection pool (waiting threads
above 0) explains latency long before CPU does.

```text
# ✅ dashboards
Rate      http_server_requests_seconds_count
Errors    same, filtered on status=~"5.."
Duration  histogram_quantile(0.99, ...)
Saturation hikaricp_connections_pending
```

### Add business and custom metrics with a bounded set of tags

Count what the business cares about (orders placed, payments failed) and keep tag values low-cardinality.

**Why it's a best practice:** "CPU is fine" while payments fail silently is a common outage. But each unique tag
combination is a separate time series: `userId` as a tag creates a million series and can crash or bankrupt
your metrics backend.

```java
// ⛔ unbounded cardinality
registry.counter("orders", "userId", userId, "orderId", orderId).increment();

// ✅
registry.counter("orders.placed", "channel", "web", "country", "FR").increment();
Timer.builder("payment.duration").publishPercentileHistogram().register(registry)
     .record(() -> gateway.charge(order));
```

### Prefer percentiles over averages

Track p50, p95 and p99 latency with histograms.

**Why it's a best practice:** an average of 120 ms can hide 1% of requests taking 8 s. Users with the slow
requests are real, and at 100 requests per page the majority of users hit at least one slow one. Averages of
percentiles are meaningless, so publish histogram buckets and compute percentiles server-side.

```yaml
# ✅
management.metrics.distribution.percentiles-histogram.http.server.requests: true
management.metrics.distribution.slo.http.server.requests: 100ms,500ms,1s
```

## 🧵 Tracing

### Propagate trace context across services

Use Micrometer Tracing with OpenTelemetry, W3C `traceparent` headers, and add the trace id to your logs.

**Why it's a best practice:** one user request may touch 8 services; without a shared trace id you correlate by
timestamps and guesses. A trace shows which call took 2.3 s of a 2.5 s request. With Spring Boot 3, `RestClient`,
`WebClient` and Kafka clients built from the auto-configured builders propagate context automatically.

```yaml
# ✅
management:
  tracing.sampling.probability: 0.1      # 1.0 in dev
  otlp.tracing.endpoint: http://otel-collector:4318/v1/traces
logging.pattern.correlation: "[${spring.application.name:},%X{traceId:-},%X{spanId:-}] "
```

### Sample traces sensibly

Sample a percentage in production (or use tail-based sampling that keeps errors and slow traces).

**Why it's a best practice:** storing 100% of traces at high traffic is expensive and often unnecessary, while
a fixed 1% may miss the rare failure you need. Tail sampling in the collector keeps every error and slow trace,
and a sample of the rest.

```yaml
# ⛔ 1.0 in production at 5,000 req/s
management.tracing.sampling.probability: 1.0

# ✅
management.tracing.sampling.probability: 0.05
```

### Add custom spans around important operations

Wrap key business steps or external calls with an `Observation` (or `@Observed`) with a low-cardinality name.

**Why it's a best practice:** automatic instrumentation covers HTTP and JDBC, but not "calculate shipping
price", which may be the slow step. One `Observation` gives you a metric, a span, and a log context at once.

```java
// ✅
@Observed(name = "shipping.quote", contextualName = "quote-shipping")
public Quote quote(Cart cart) { ... }
```

## ❤️ Health & alerting

### Expose separate liveness and readiness probes

Use `/actuator/health/liveness` and `/actuator/health/readiness`, and wire them to Kubernetes.

**Why:** covered in [Configure liveness, readiness and startup probes correctly](docker-k8s-devops.md#configure-liveness-readiness-and-startup-probes-correctly).

```yaml
# ✅
management.endpoint.health.probes.enabled: true
management.endpoint.health.group.readiness.include: readinessState,db
```

```yaml
livenessProbe:  { httpGet: { path: /actuator/health/liveness,  port: 8080 } }
readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
```

### Shut down gracefully

Enable graceful shutdown so in-flight requests finish before the pod exits.

**Why it's a best practice:** without it, every deployment cuts running requests, giving users a burst of 502
errors on each rollout. Spring waits for active requests up to the timeout.

```yaml
# ✅
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
```

### Alert on symptoms, not causes

Page on user-visible problems (error rate, latency SLO burn, no traffic), and keep CPU and disk as tickets or dashboards.

**Why it's a best practice:** "CPU at 85%" may be perfectly fine and wakes someone at 3 a.m. for nothing;
alert fatigue leads people to ignore or mute alerts, and then the real one is missed. Alerting on an SLO
(for example, 99.9% of requests under 500 ms) ties pages to customer impact.

```yaml
# ⛔
- alert: HighCpu
  expr: cpu_usage > 0.8

# ✅
- alert: HighErrorRate
  expr: |
    sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
      / sum(rate(http_server_requests_seconds_count[5m])) > 0.02
  for: 5m
  labels: { severity: page }
  annotations: { runbook: https://wiki.example.com/runbooks/high-error-rate }
```

### Give every alert an owner and a runbook

Each page links to a runbook with what it means, how to check, and how to mitigate. Remove alerts that nobody acts on.

**Why it's a best practice:** at 3 a.m., nobody remembers what `queue_depth_high` means. A runbook cuts time to
mitigate, and an alert that was ignored three times in a row is noise that should be fixed or deleted.

```yaml
# ✅
annotations:
  summary: "Order queue backlog above 10k for 10 min"
  runbook: https://wiki.example.com/runbooks/order-queue
```

### Define SLOs and track the error budget

Set a target (say 99.9% availability over 30 days) and measure it from real request metrics.

**Why it's a best practice:** 99.9% allows about 43 minutes of downtime per 30 days, 99.99% only about 4. Without
a number, "reliable" is an argument. The remaining error budget tells you when to ship features and when to
stop and fix reliability.

```text
# ✅
SLI: successful requests / total requests (status < 500)
SLO: 99.9% over 30 days -> budget = 0.1% = ~43 min
```
