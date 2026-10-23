# Observability

Going beyond the three pillars: SLO-based alerting, correlation, cardinality, sampling and cost. The pillars themselves are in [Full Stack & DevOps](fullstack-devops-k8s.md#three-pillars-observability-each-one) and the practical "what good looks like" in [Q30](fullstack-devops-k8s.md#put-three-pillars-observability-practice); rules live in [Best practices › Observability](../best-practices/observability.md).

## 🟢 Fundamentals

#### Q1. What is the difference between monitoring and observability? {#monitoring-observability}
**Answer:** Monitoring checks known failure modes with predefined dashboards and alerts. Observability lets you ask **new** questions about unknown failures from the telemetry you emit (rich, high-cardinality events, traces, metrics). In practice: structured logs with context, traces across services, and metrics for SLIs, so you can go from a symptom to a cause without shipping new code.

#### Q2. What are the RED and USE methods, and which metrics do you alert on? {#red-methods-metrics-alert}
**Answer:** **RED** for services: Rate, Errors, Duration (per endpoint). **USE** for resources: Utilization, Saturation, Errors. Alert on **symptoms users feel** (error rate, latency SLI burning budget), not on every cause (CPU 80%). Causes go on dashboards for diagnosis.

## 🟡 Senior traps

#### Q3. How do you correlate logs, metrics and traces across services? {#correlate-logs-metrics-traces-across}
**Answer:** Propagate a **trace context** (W3C `traceparent`) on every hop, HTTP and messaging; put `traceId`/`spanId` into every log line through MDC so a log search jumps to the trace and back. Use exemplars on metrics to link a slow bucket to a sample trace. In Spring Boot 3 this comes from Micrometer Tracing with an OpenTelemetry bridge.

**Example:**

```text
2026-10-13 10:02:11 INFO  traceId=4bf92f35 spanId=00f067aa  Payment captured id=981
```

#### Q4. What is metric cardinality, and how does it blow up a monitoring bill? {#metric-cardinality-blow-up-monitoring}
**Answer:** Each unique combination of label values is a separate time series. Labels such as `userId`, `orderId`, a full URL or an exception message multiply series into millions, causing memory pressure and cost. Keep labels bounded (endpoint template, status class, region); put high-cardinality detail in logs and traces instead.

#### Q5. Head-based vs tail-based trace sampling: how do you choose? {#head-based-tail-based-trace}
**Answer:** Head-based decides at the start (for example 5% of requests): cheap and simple but may drop the interesting traces. Tail-based decides after the trace completes in a collector, keeping all errors and slow requests plus a sample of the rest: more useful but needs buffering and more memory. Always keep error and high-latency traces.

## 🔴 Expert / Open

#### Q6. How do you design SLO-based alerting with burn rates? {#design-slo-based-alerting-burn}
**Answer:** Define an SLI (for example share of requests under 300 ms and non-5xx) and an SLO (99.9% over 30 days), giving an error budget. Alert on **burn rate**: a fast window (for example 14× burn over 1 h) pages immediately, a slow window (for example 2× over 6 h) opens a ticket. This cuts noise from short blips and still catches slow leaks. See [Full Stack Q35](fullstack-devops-k8s.md#slos-error-budgets-drive-release) for SLOs and error budgets.

## 🎯 Real-world scenarios

### S1. Customers report errors, but all dashboards are green {#customers-report-errors-but-all}
- **Symptoms:** Support tickets mention failed payments for one region; error-rate and CPU dashboards look normal.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Averages hide a partial failure. Slice the error rate by region, endpoint and version, then follow one failed request's trace to the failing dependency.
- **Resolution:** Fix or roll back the cause, then add the missing SLI (per-region success rate) and a burn-rate alert on it.
- **Prevention:** Alert on user-facing SLIs with meaningful dimensions, and run synthetic probes per region.

</details>

### S2. Users tweet about failed checkouts 40 minutes before the first alert fires {#alert-fires-after-users-notice}
- **Symptoms:** The post-mortem timeline shows support tickets at 14:05, the page at 14:45. The alert was `error_rate > 5% for 30m` on the whole API.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The alert averages checkout (low volume, critical) with high-volume healthy endpoints, so a 30% checkout failure is diluted below 5%. The long `for:` window adds 30 minutes on top.
- **Example:**

  ```promql
  # per-SLO burn rate, fast window: 2% of a 30-day budget in 1h
  sum(rate(http_requests_total{route="/checkout",code=~"5.."}[5m]))
    / sum(rate(http_requests_total{route="/checkout"}[5m])) > 14.4 * 0.001
  ```

- **Resolution:** Define an SLO per critical user journey (checkout, login), alert on multi-window burn rate (fast 1h/5m + slow 6h/30m) instead of a global threshold, and add a synthetic probe that runs a real checkout every minute.
- **Prevention:** Every post-mortem records 'time to detect' and 'who detected it'; if customers detected it first, an alerting action item is mandatory.

</details>

### S3. Prometheus restarts in a loop with OOM after a harmless-looking release {#prometheus-oom-label-cardinality}
- **Symptoms:** Dashboards go blank, Prometheus memory goes from 6 GB to 40 GB within hours of a deploy; `prometheus_tsdb_head_series` jumped from 800k to 12M.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A new label carries an unbounded value: `userId`, a raw URL path with IDs (`/orders/8812`), or an exception message. Every distinct value creates a new time series.
- **Example:**

  ```promql
  topk(10, count by (__name__)({__name__=~".+"}))
  # then, for the top metric:
  count(count by (uri) (http_server_requests_seconds_count))
  ```

- **Resolution:** Drop or relabel the offending label at scrape (`metric_relabel_configs` with `labeldrop`), roll back or fix the instrumentation to use the route template (`/orders/{id}`), then restart Prometheus with the bad series gone.
- **Prevention:** Review rule: labels must have a bounded value set; IDs belong in logs and traces, not metrics. Add `sample_limit` per scrape job and an alert on head-series growth.

</details>

### S4. Traces stop at the Kafka producer, so nobody can tell why some orders take 10 minutes end to end {#trace-breaks-at-kafka-hop}
- **Symptoms:** In the tracing UI the `POST /orders` trace ends at `kafka.send`; the consumer side shows up as hundreds of unrelated root traces with no link to the request.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Trace context isn't propagated in message headers: either the producer isn't instrumented, a custom serializer/wrapper drops headers, or the consumer processes in a thread pool where the context is lost.
- **Example:**

  ```text
  producer record headers: traceparent: 00-4bf92f35...-00f067aa0ba902b7-01
  consumer: extract context from headers -> new span with a link (or parent) to it
  ```

- **Resolution:** Use the OpenTelemetry Kafka instrumentation (or Spring Kafka observation) on both sides so `traceparent` travels in headers, propagate context into executor threads, and record queue time (consume time − produce time) as a span attribute/metric.
- **Prevention:** A contract test that asserts `traceparent` is present on produced messages, and a dashboard of end-to-end latency split into 'in queue' vs 'processing'.

</details>

### S5. The logging bill triples in a month and log search becomes too slow to use during incidents {#log-bill-explodes-debug-left-on}
- **Symptoms:** Ingestion went from 200 GB/day to 1.5 TB/day; most volume is `DEBUG` lines from one service and full request/response bodies.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Group ingestion by service and level in the log backend. Typical causes: a `DEBUG` level enabled for an incident and never reverted, logging payloads in a loop, or a retry loop logging a stack trace per attempt.
- **Resolution:** Revert the level (Spring Boot `/actuator/loggers` lets you change it at runtime without redeploy, and back), stop logging bodies (also a PII risk), log one line per failure instead of per retry, and set retention per index (e.g. 7 days for debug, 30 for audit).
- **Prevention:** Default level `INFO` enforced in config review, temporary debug levels with an expiry, per-service ingestion quotas/alerts, and sampling for high-volume success logs.

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q1. What is the difference between monitoring and observability?
2. Q2. What are the RED and USE methods, and which metrics do you alert on?
3. Q3. How do you correlate logs, metrics and traces across services?
4. Q4. What is metric cardinality, and how does it blow up a monitoring bill?
5. Q5. Head-based vs tail-based trace sampling: how do you choose?
6. Q6. How do you design SLO-based alerting with burn rates?
7. S1. Customers report errors, but all dashboards are green

## 📌 Cheat-sheet

- **Monitoring vs observability** — known failures vs new questions. *Emit rich context, not only counters.*
- **RED / USE** — services: rate, errors, duration; resources: utilization, saturation, errors. *Alert on symptoms.*
- **Correlation** — `traceparent` on every hop and `traceId` in every log line. *Exemplars link metrics to traces.*
- **Cardinality** — bounded labels only. *Never `userId` or full URLs in metrics.*
- **Sampling and SLOs** — tail-based keeps errors/slow; burn-rate alerts (fast + slow window). *Fewer pages, fewer misses.*
