# Performance & Load Testing

How to measure, test and reason about performance: load shapes, tools (k6, Gatling), percentiles, bottleneck hunting and capacity. Latency percentiles are introduced in [Full Stack & DevOps](fullstack-devops-k8s.md#p50-p95-p99-latency-average); the end-to-end p95 exercise is [Q36](fullstack-devops-k8s.md#reducing-endpoint-p95-latency-9).

## 🟢 Fundamentals

#### Q1. What are load, stress, spike and soak tests, and what does each find? {#load-stress-spike-soak-tests}
**Answer:** **Load**: expected traffic, checks you meet the SLO. **Stress**: ramp beyond capacity to find the breaking point and how the system fails (gracefully or not). **Spike**: sudden jump, tests autoscaling and queues. **Soak**: moderate load for hours, finds leaks, connection exhaustion and slow degradation. Run them against a production-like environment with realistic data volume.

#### Q2. How do you write a load test in k6 or Gatling, and what makes it realistic? {#write-load-test-k6-gatling}
**Answer:** Model **user journeys** with think time, not one hot endpoint; use varied data (not the same id, which hits caches); ramp up; set **thresholds** that fail the run. Use an open model (fixed arrival rate) for public APIs, a closed model (fixed users) for internal tools.

**Example:**

```javascript
export const options = {
  scenarios: { api: { executor: 'constant-arrival-rate', rate: 100, timeUnit: '1s',
                      duration: '5m', preAllocatedVUs: 200 } },
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<300'] },
};
```

## 🟡 Senior traps

#### Q3. What is coordinated omission, and why do some load tests report latencies that are too good? {#coordinated-omission-some-load-tests}
**Answer:** A closed-loop tool that waits for each response before sending the next hides stalls: during a 5 s freeze it sends no requests, so the slow period is under-counted and the p99 looks fine. Use an open model with a fixed arrival rate, or a tool that corrects for it (wrk2, HdrHistogram, k6 arrival-rate executors), and always report p95/p99/max, never only the mean.

#### Q4. How do you find the bottleneck when throughput stops growing? {#find-bottleneck-throughput-stops-growing}
**Answer:** Apply the **USE method** per resource (Utilization, Saturation, Errors): CPU, memory, disk, network, then software resources such as connection pools, thread pools and locks. Look at the saturated one: a pool at 100% with a growing wait queue, a CPU core pinned, GC pauses, or a database at its connection limit. Confirm with a profiler or traces, change one thing, retest.

#### Q5. How do Little's law and the connection pool relate to capacity? {#little-law-connection-pool-relate}
**Answer:** Little's law: concurrency = throughput × latency. At 200 req/s with 100 ms latency you need about 20 requests in flight. A DB pool of 10 then caps you near 100 req/s whatever the CPU says. Size pools from this arithmetic, and remember that more threads than the database can serve only lengthens queues.

## 🔴 Expert / Open

#### Q6. How do you put performance checks into CI/CD without flaky results? {#put-performance-checks-ci-cd}
**Answer:** Run a small, fixed smoke load on every merge against a stable environment and compare to a baseline with a tolerance (for example p95 within 15%); run the long soak/stress nightly. Fail on SLO thresholds, store results over time, and isolate noisy neighbours (dedicated runners). Treat a regression like a failing test: bisect to the commit.

## 🎯 Real-world scenarios

### S1. The p99 is fine at 50% load but spikes to 8 s at 80% CPU {#p99-fine-50-load-but}
- **Symptoms:** Median latency is stable, the tail explodes as load rises, and errors appear in bursts.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Queueing: near saturation, wait time grows non-linearly. Check pool wait metrics, GC pauses, thread dumps and retries amplifying load.
- **Resolution:** Add capacity or reduce work per request, bound queues and timeouts, add load shedding and capped retries with jitter, and set autoscaling to trigger at ~60% rather than 90%.
- **Prevention:** Load-test to the knee of the curve before launch and alert on saturation (queue depth, pool wait), not only on CPU.

</details>

### S2. The load test passed at 3× expected traffic, yet production falls over on launch day at 1× {#load-test-green-prod-falls-over}
- **Symptoms:** The k6 report showed p95 at 120 ms for 3000 req/s. In production, at 1000 req/s, p95 is 4 s and the database CPU is at 100%.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Compare the test to reality: 50 test users hitting the same 10 products (all cache hits), a small staging dataset where every index fits in memory, no think time, a closed model that slows down when the system slows down (coordinated omission), and no background jobs running.
- **Example:**

  ```javascript
  // open model: arrivals don't wait for slow responses
  export const options = { scenarios: { launch: {
    executor: 'constant-arrival-rate', rate: 1000, timeUnit: '1s',
    duration: '15m', preAllocatedVUs: 500 } } };
  ```

- **Resolution:** Scale out / add the missing index to survive, then rebuild the test: production-sized anonymized data, realistic key distribution (long tail, not 10 hot items), an open arrival-rate model, and the same cron jobs running during the test.
- **Prevention:** Treat the load test as a product: review its realism like code, compare its traffic mix against production access logs each quarter, and run it in CI against a prod-like environment before big launches.

</details>

### S3. Throughput plateaus at ~400 req/s no matter how many pods you add, and CPU stays at 30% {#throughput-plateaus-cpu-idle}
- **Symptoms:** Doubling pods from 4 to 8 doesn't move throughput; latency grows linearly with load; neither app nor DB CPU is saturated.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A shared bounded resource is the bottleneck, so it's queueing, not compute. Look for waiting, not working: HikariCP `hikaricp_connections_pending`, a DB `max_connections` divided across pods, a downstream API rate limit, a single-partition queue, or a lock (`pg_stat_activity` with `wait_event_type = 'Lock'`).
- **Example:**

  ```text
  8 pods × pool 10 = 80 connections, but RDS max_connections = 100 and a hot row
  UPDATE stock SET qty = qty - 1 WHERE sku = 'BESTSELLER'  -> every request serializes on one row lock
  ```

- **Resolution:** Fix the contended resource: remove the hot-row update (reservation table, sharded counters, or async decrement), right-size pools from the DB core count, add a connection pooler (PgBouncer) if pods must scale further.
- **Prevention:** Load tests report saturation metrics (pool wait, lock waits, queue depth), not only latency; apply the USE method to every shared resource on the request path.

</details>

### S4. After a release, p50 is unchanged but p99 doubled, and the diff looks harmless {#p99-regression-after-release}
- **Symptoms:** Median latency identical, p99 from 180 ms to 400 ms; no error increase; CPU slightly higher.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Tail-only regressions usually mean something periodic or allocation-heavy: compare GC pause metrics (`jvm_gc_pause_seconds`) before/after, then profile with async-profiler in allocation mode. A common culprit: a new JSON mapping, logging or a `stream()` pipeline that allocates large temporary objects per request.
- **Example:**

  ```bash
  # allocation flame graph on one pod for 60 s
  ./asprof -e alloc -d 60 -f /tmp/alloc.html <pid>
  ```

- **Resolution:** Remove the allocation hotspot (reuse the `ObjectMapper`, avoid building strings for disabled log levels, stream instead of materializing large lists), or adjust heap/GC if the live set genuinely grew.
- **Prevention:** A performance gate in CI comparing p99 and allocation rate against the previous build on the same benchmark, with a tolerance; continuous profiling in production to diff releases.

</details>

### S5. Every weekday at 09:00 latency spikes for 10 minutes, then recovers once autoscaling catches up {#autoscaling-lags-morning-spike}
- **Symptoms:** HPA scales from 4 to 16 pods, but new pods take 90 s to be ready and the HPA reacts only after CPU has been high for a while; errors and timeouts during the ramp.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Plot the timeline: traffic ramps in 2 minutes; HPA sync + metrics delay ≈ 1 min; node provisioning (cluster autoscaler) 2–4 min; JVM startup + warm-up 90 s. The sum is longer than the spike.
- **Resolution:** Pre-scale on a schedule before the known peak (KEDA cron scaler or a scheduled `minReplicas` change), keep headroom (target CPU 50–60%), cut startup time (CDS/AppCDS, lazy init, smaller image) and use a readiness probe that waits for warm-up.
- **Prevention:** Load-test the ramp itself, not only the steady state; track 'time from scale decision to ready pod' as a metric; review capacity before known events (campaigns, payroll day).

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q1. What are load, stress, spike and soak tests, and what does each find?
2. Q2. How do you write a load test in k6 or Gatling, and what makes it realistic?
3. Q3. What is coordinated omission, and why do some load tests report latencies that are too good?
4. Q4. How do you find the bottleneck when throughput stops growing?
5. Q5. How do Little's law and the connection pool relate to capacity?
6. Q6. How do you put performance checks into CI/CD without flaky results?
7. S1. The p99 is fine at 50% load but spikes to 8 s at 80% CPU

## 📌 Cheat-sheet

- **Test types** — load = expected, stress = beyond, spike = sudden, soak = long. *Each finds a different failure.*
- **Realism** — journeys, think time, varied data, thresholds. *Open model for public APIs.*
- **Percentiles** — report p95/p99/max, never the mean alone. *Beware coordinated omission.*
- **Bottleneck** — USE method per resource; concurrency = throughput × latency. *Size pools from the arithmetic.*
- **CI** — small fixed smoke load per merge vs baseline, long runs nightly. *Isolate noisy runners.*
