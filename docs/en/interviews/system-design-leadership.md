# System Design & Leadership

## 🟢 Fundamentals

### Design approach

#### Q1. What two questions do you ask before starting any system design, and why do they come before any diagrams?
"What should it do?" (functional requirements — sign up, upload a photo, follow a user, scroll a
feed, like/comment) and "how well must it do it?" (non-functional requirements — speed,
durability, scale, availability, cost). They come first because every architectural decision
later in the design is a trade-off made *in service of* a specific non-functional requirement —
you can't meaningfully choose between strong and eventual consistency, or between a monolith and
microservices, without first knowing the actual scale, latency budget, and availability target;
skipping straight to a diagram produces a design optimized for assumptions nobody asked for.

#### Q2. What's the difference between high-level design (HLD) and low-level design (LLD)?
HLD is the zoomed-out view — the big pieces of the system (app servers, database, cache, queue,
CDN) and how requests move between them. Designing Instagram at HLD level asks: where does a
user's request go, where is data stored, what happens as traffic grows, what breaks first and
how is that component scaled or made resilient. LLD zooms into one specific feature and asks the
implementation-level questions: for a "like" feature specifically — what happens when the user
taps like, which function/service handles it, how do you check whether the user already liked
the post, how is the like persisted, how is the like count updated without double-counting the
same user. An interview (and a real design doc) typically moves from HLD to a deep dive into one
or two components at LLD depth, rather than staying entirely at one level throughout.

### Building blocks

#### Q3. What is a load balancer, and what specific problem does it solve?
When a single server runs out of CPU/RAM to handle growing traffic, adding another server only
helps if requests are actually distributed across both — a load balancer sits in front of
multiple servers and decides which one handles each incoming request (round-robin, least-
connections, or more sophisticated algorithms), turning "one server that's now overloaded" into
"N servers sharing the load," and also removing a failed server from rotation so traffic doesn't
keep flowing to something down. It's the first component most horizontally-scaled designs
introduce, because without it, adding more servers doesn't actually help — nothing routes traffic
to them.

#### Q4. What does it mean for a service to be stateless, and why does it matter for scaling and resilience?
A stateless service keeps no request-specific or user-specific state **in its own memory or local disk between
requests**: everything needed to handle a request arrives with it (parameters, a token) or is fetched from an external store (a
database, a cache like Redis, object storage). Any instance can then serve any request, so a load balancer can distribute traffic with
plain round-robin (Q3) — no sticky sessions — and you can add instances to scale out, replace a crashed instance without
losing anyone's data, deploy with rolling updates and autoscale up and down freely. The state doesn't disappear; it moves to the
tier designed to hold it, which is where replication, backups and consistency are handled deliberately. Typical places
where statefulness sneaks in: HTTP sessions stored in the app server's memory (move them to a shared session store or use a signed token), files written to the local
disk (use object storage), in-process caches that differ between instances (accept that, or use a shared cache), scheduled jobs that run on every replica (S18
of module 2) and WebSocket connections, which are inherently stateful and need a shared pub/sub backplane to route messages to the right instance.
Statelessness is a property to preserve wherever it is cheap, not an absolute: caches, connection pools and warmed-up state are fine as long as losing them only costs performance,
never correctness.

#### Q5. What is caching, and what's the basic idea behind cache invalidation?
Caching keeps a copy of frequently-requested or expensive-to-compute data in a faster-access
layer (in-memory, closer to the client) so repeated requests for the same data don't repeat the
expensive underlying work (a slow query, a heavy computation, a network call) every time.
Invalidation is the harder half: once cached data is served instead of the source of truth, the
cache has to be updated or expired when the underlying data changes, or clients get stale data
indefinitely — the basic strategies (TTL-based expiry, explicit invalidation on write, and the
read/write patterns in Q16) all exist because "cache it and forget it" silently trades
correctness for speed unless invalidation is deliberately designed.

#### Q6. How do you choose between a relational (SQL) database and a NoSQL store when designing a system?
Start from the **access patterns and consistency needs**, not from fashion. A relational database is the default for
data with relationships and invariants — orders, payments, inventory — because it gives you ACID
transactions, constraints, joins and ad-hoc queries you didn't plan for, and modern PostgreSQL handles a very large
scale on one primary plus replicas (Q13, Q10). NoSQL is a family, and each kind answers a specific pressure: a
**key-value/document** store (DynamoDB, MongoDB, Redis) for simple lookups by key at a huge scale and predictable
latency, with a flexible schema; a **wide-column** store (Cassandra) for very high write throughput across regions with
tunable consistency; a **search engine** (Elasticsearch/OpenSearch) for full-text and faceted queries; a **graph** store for deeply
connected data; a **time-series** store for metrics. What you give up is usually the ability to query on
anything except the designed access path, multi-row transactions and referential integrity, and you must model data *around the
queries* (denormalize, duplicate) and handle the resulting inconsistency yourself. A pragmatic answer: begin with a relational
database as the system of record, add a specialized store (a cache, a search index, a time-series DB) as a *derived* copy when a measured
requirement demands it, and choose a NoSQL primary only when you can name the specific reason — a write volume or data size a
single relational cluster can't carry, a key-based access pattern that will never need joins, or global multi-region writes. "Schema-less" is not
a benefit by itself: the schema still exists, in your application code, and you now enforce it there.

### Leadership

#### Q7. What makes technical feedback and mentorship actually effective, as opposed to just correct?
Effective feedback is specific (points at the actual line/decision, not a general impression),
timely (given close to when the work happened, not batched into a vague quarterly comment),
focused on the work and its impact rather than the person, and — critically for mentorship
specifically — explains the *why* behind the suggestion so the person can generalize it to the
next situation, not just fix this one instance. The distinction from "just correct" matters: a
technically accurate comment delivered in a way that reads as dismissive or purely critical can
be right and still fail at its actual goal, which is helping someone build better judgment over
time, not just getting this one PR fixed.

## 🟡 Senior traps

### Consistency & replication

#### Q8. Explain the CAP theorem with a concrete example — why can't a distributed system have all three?
**Answer:** CAP states that during a network partition (P — some communication failure between
nodes, which in any real distributed system *will* eventually happen), a system must choose
between Consistency (every read sees the most recent write, or an error) and Availability (every
request gets a response, even if it might not reflect the latest write) — you cannot have both
during the partition, though you can have either alone plus partition tolerance. A CP system (e.g.
a strongly consistent config store like ZooKeeper/etcd) refuses to serve a read/write on the
minority side rather than risk returning stale or conflicting data — sacrificing availability for
consistency. An AP system (e.g. Cassandra in its typical configuration, or a shopping cart
service) keeps both sides serving requests during the partition, accepting that the two sides may
briefly disagree, to be reconciled once the partition heals — sacrificing strict consistency for
availability. The senior-level point: this is a deliberate trade-off made per system based on what
failure mode is actually worse for that specific use case (a bank ledger leans CP; a "add to cart"
button leans AP), not a universal "correct" answer.

**Example:**
```
Network link between region A and region B drops for 90 seconds.

CP system (etcd-style):
  region B (minority side) -> write request -> "unavailable: no quorum" (fails loudly)
  region A (majority side) -> keeps serving, single source of truth preserved

AP system (Cassandra-style, quorum relaxed to ONE):
  region A -> accepts writes locally
  region B -> also accepts writes locally
  partition heals -> both sides' writes get reconciled/merged, possibly with conflicts
```

**Why it's a trap:** candidates recite "CAP means pick two of three" as a blanket rule, but
partition tolerance isn't optional in a real distributed system — the actual choice being made,
every time, is C vs A during the partition specifically, and a senior answer names *which specific
failure mode* (a stale read vs a rejected request) is worse for *this* system, not just the
theorem's name.

#### Q9. Give a concrete, practical example of choosing eventual consistency over strong consistency, and explain why it's the right call there.
**Answer:** A social media "like count" or "follower count" is the textbook case: showing a count
that's a few seconds stale is completely acceptable to users, and the alternative — strongly
consistent, requiring a coordinated read/write across every replica for every single like — would
add real latency and reduce availability for a piece of data where staleness has essentially zero
real-world cost. Contrast with an account balance or an inventory count at checkout, where the same
staleness could mean double-spending or overselling a limited-stock item — those operations
justify the latency/availability cost of stronger consistency (or at minimum a consistency check
at the exact moment of the transaction) precisely because the cost of being wrong there is real
and immediate, unlike a like count.

**Example:**
```
Like count:       read from any replica, cached, off by a few -> nobody notices
Checkout balance:  read must reflect the latest committed write, or two concurrent
                    checkouts can both succeed against the same last unit of stock
```

**Why it's a trap:** "eventual consistency everywhere for scale" and "strong consistency
everywhere to be safe" are both wrong defaults — the senior answer picks per data type based on
the actual cost of staleness for that specific field, not a blanket policy for the whole system.

#### Q10. What's the difference between synchronous and asynchronous database replication, and what does each trade off?
**Answer:** Synchronous replication waits for the replica(s) to confirm they've received and
applied a write before acknowledging it to the client — guarantees the replica is never behind the
primary, at the cost of added write latency (bounded by the slowest replica) and reduced
availability (if the replica is unreachable, does the write block or fail?). Asynchronous
replication acknowledges the write once the primary has it, without waiting for replicas — lower
write latency, better availability, but introduces replication lag: a replica can be measurably
behind the primary, and a failover to that replica after the primary dies can lose the most
recent, not-yet-replicated writes. Most large-scale systems choose async by default for the
latency/availability benefit, accepting the lag as a known, monitored trade-off, reserving
synchronous replication for the specific data where losing even a few seconds of recent writes on
failover is genuinely unacceptable.

**Example:**
```
Sync:  client -> primary -> [wait for replica ack] -> ack to client   (higher latency, no lag)
Async: client -> primary -> ack to client -> (replica catches up later)  (lower latency, lag window)

Primary fails during the lag window -> failover promotes the replica ->
any write the replica hadn't yet applied is gone.
```

**Why it's a trap:** candidates often present async replication as strictly worse ("you might lose
data!") without naming what it buys in return — the trap runs the other way too: defaulting
everything to synchronous "to be safe" quietly imposes a latency and availability cost on data
that never needed that guarantee (see Q9).

#### Q11. Why does read-your-own-writes break under asynchronous replication, and how do you fix it for the data that needs it?
**Answer:** With async replication (Q10), a write lands on the primary and is acknowledged before
every replica has applied it. If the very next request from the *same user* is a read routed to a
lagging replica — a common setup, since reads are usually load-balanced across replicas for
throughput — it can return the pre-write state, making it look like the user's own action didn't
take effect. This is a genuinely confusing bug for the user ("I just saved this, where did it
go?"), distinct from another user seeing stale data, which is usually tolerable. Fixes: route a
user's reads to the primary (or a replica known to be caught up) for a short window right after
their own write; pass a "read-your-own-writes" token/timestamp the read path checks against
replica lag before answering from a replica; or, for the specific fields affected, have the client
optimistically show what it just wrote rather than re-fetching immediately.

**Example:**
```
t=0.00  user PATCHes /profile {bio: "new bio"} -> primary commits, acks -> client shows "saved"
t=0.05  client re-fetches /profile to confirm -> load balancer routes to replica-3
t=0.05  replica-3 hasn't applied the write yet -> returns bio: "old bio"
        user sees their own save appear to have been silently reverted
```

**Why it's a trap:** this is easy to conflate with Q9's "eventual consistency is fine for
low-stakes data" — but the stakes here aren't about the data's importance, they're about *whose*
read is affected: staleness a different user sees is usually invisible and fine, staleness the
*writer* sees immediately after their own write reads as a broken feature.

#### Q12. Two-phase commit vs sagas — how do you keep data consistent across several services without a shared database?
**Answer:** **Two-phase commit (2PC)** coordinates a single atomic transaction over several resources: a coordinator asks every participant to
*prepare* (vote yes, holding locks), and only if all vote yes tells them to *commit*. It gives strong atomicity but at a
price: participants hold locks during the protocol, so throughput and availability drop; the coordinator is a single point whose failure between the phases leaves
participants **blocked in doubt**; and it needs every participant to support it (XA), which most message brokers, SaaS APIs and NoSQL stores don't.
A **saga** replaces one distributed transaction with a sequence of local transactions, each publishing an event or command that triggers the next; if a
step fails, previously completed steps are undone by **compensating actions** (refund the payment, release the reserved stock) rather than rolled back. It can be
**choreographed** (services react to each other's events — simple for few steps, hard to follow as it grows) or **orchestrated** (a coordinator holds the workflow state — easier to
reason about, monitor and time out). The consequences to design for: sagas are **eventually consistent**, with intermediate states visible to other requests (an order that is "pending" for a while); compensations must be
**idempotent** and can themselves fail (retry, then alert a human); some actions can't be undone (an email sent, a parcel shipped), so order steps to put the
irreversible ones last; and each step and its event must be published reliably with an outbox (module 4 Q26) so a crash between "write" and "publish" doesn't stall the saga. In practice: prefer to avoid the
distributed transaction altogether by keeping tightly coupled data in one service (Q22), use sagas for genuine cross-service business processes, and use 2PC only inside one
trusted platform where all participants support it and the latency is acceptable.

**Example:**
```text
Order saga (orchestrated):
  1. Orders:    create order PENDING                  compensation: mark CANCELLED
  2. Payments:  charge card                            compensation: refund
  3. Inventory: reserve stock                          compensation: release stock
  4. Shipping:  create shipment (irreversible - last)  compensation: n/a
  step 3 fails  ->  refund (2), cancel order (1); each compensation is idempotent and retried
```

**Why it's a trap:** candidates answer "we use distributed transactions" (an availability problem) or "we use a saga" without mentioning compensation failure, idempotency, visibility of intermediate
states or the outbox — and "exactly-once" claims across services almost always hide *at-least-once delivery plus idempotent processing* (module 4 Q15).

### Scaling & caching

#### Q13. Horizontal vs vertical scaling — what's the actual trade-off?
**Answer:** Vertical scaling (a bigger machine — more CPU/RAM on the same node) is simpler (no
distributed-systems complexity, no data partitioning to reason about) but has a hard ceiling
(there's a biggest machine money can buy) and a single point of failure. Horizontal scaling (more
machines) has no practical ceiling and improves fault tolerance, but introduces real complexity:
load balancing, data consistency across nodes, network latency between components that used to be
in-process calls, and operational overhead. The practical answer most systems land on: vertical
scale as far as it reasonably goes for genuine simplicity, and reach for horizontal scaling once
vertical's ceiling or single-point-of-failure risk becomes the actual constraint, not by default
from day one for a system that doesn't need it yet.

**Example:**
```
Vertical: db.small -> db.large -> db.2xlarge -> db.8xlarge -> ... -> biggest instance money buys
          one machine, one failure domain, zero coordination code

Horizontal: 1 node -> 3 nodes -> 20 nodes -> ...
          needs: a load balancer, a partitioning/sharding scheme, replica consistency,
          and monitoring for N failure domains instead of one
```

**Why it's a trap:** "just scale horizontally, it's more modern" is the naive answer — a senior
candidate names the actual complexity horizontal scaling buys (partitioning, consistency, ops
overhead) instead of treating it as a free upgrade, and can say plainly when vertical scaling is
still the right call.

#### Q14. How do you choose a database shard key, and what happens with a bad choice?
**Answer:** A shard key determines which physical shard a given row lives on (commonly via a hash
of the key, or a range partition on it) — the goal is distributing both data volume and, more
importantly, *query/write load* evenly across shards. A bad choice creates a "hot shard": choosing
a low-cardinality key (e.g. sharding by `country` when 80% of users are in one country) or a key
correlated with access pattern skew (a small number of accounts generating a disproportionate
share of all activity) puts most of the real load on one shard regardless of how evenly the
*storage* is distributed. Fixing a bad shard key after the fact (re-sharding a live system with
data already unevenly distributed) is one of the most operationally painful migrations in
distributed systems, which is exactly why the choice deserves real scrutiny before the system is
built around it.

**Example:**
```
Sharded by `country`: 4 shards, one per region
  shard(US) -> 80% of all users and all traffic  <- hot shard
  shard(NZ), shard(IS), shard(LU) -> nearly idle

Cluster-wide CPU on the main dashboard reads "35% utilized" while shard(US) sits at 95%.
```

**Why it's a trap:** aggregate cluster metrics hide a hot shard completely — a candidate who only
checks "is the cluster over capacity" misses the actual production symptom, which shows up as one
shard's latency degrading while the fleet-wide average still looks healthy.

#### Q15. What is consistent hashing, and why is it used for distributed caches and sharding instead of simple modulo hashing?
**Answer:** Simple modulo hashing (`hash(key) % N` to pick one of N servers) has a severe problem
when N changes (a server is added or removed): nearly every key's assigned server changes too,
because the modulus itself changed — for a distributed cache, this means a node change invalidates
almost the entire cache at once (a "cache stampede" hitting the database simultaneously, S2).
Consistent hashing maps both servers and keys onto a conceptual ring, and each key is owned by the
next server clockwise from it on the ring — adding or removing one server only remaps the keys
that specifically fell between it and its neighbor, leaving the vast majority of key-to-server
assignments unchanged.

**Example:**
```
Modulo, N=4->5 servers:  hash(key) % 4  vs  hash(key) % 5  -> ~80% of keys remap

Consistent hashing, ring with a 5th server added:
  only the keys between the new server and its counter-clockwise neighbor move
  -> roughly 1/5 of keys remap, not 4/5
```

**Why it's a trap:** candidates can usually explain modulo hashing's problem but stop short of the
mechanism that fixes it — "consistent hashing helps" without the ring/neighbor mechanics is a name
without an explanation, and an interviewer's follow-up ("why does only that subset move?") exposes
the gap immediately.

#### Q16. Name the main cache invalidation/write strategies and their trade-offs — "there are only two hard things in computer science."
**Answer:** **Cache-aside** (lazy loading): the application checks the cache first, and on a miss,
reads from the database and populates the cache — simple, but the first request for any key is
always a slow miss, and there's a real risk of serving stale data until TTL expiry or explicit
invalidation. **Write-through**: every write goes to the cache and the database together,
synchronously — keeps the cache always consistent, at the cost of added write latency and caching
data that might never actually be read. **Write-behind (write-back)**: writes go to the cache
immediately and are asynchronously flushed to the database later — fastest writes, but risks data
loss if the cache fails before the flush. TTL-based expiry is often layered on top of any of these
as a simple safety net, bounding how stale data can get even if explicit invalidation is missed.

**Example:**
```python
# Cache-aside
def get_user(id):
    if (u := cache.get(id)) is not None:
        return u
    u = db.query(id)
    cache.set(id, u, ttl=300)
    return u
```

**Why it's a trap:** "just add a cache" without naming which of these three strategies, and its
specific staleness/latency trade-off, is the actual anti-pattern the classic joke is warning
about — the interview signal is picking a strategy deliberately for the read/write ratio at hand,
not reciting all three as equally fine defaults.

#### Q17. What does a CDN actually solve, and when does it not help?
**Answer:** A CDN caches content at edge locations geographically close to end users, reducing
latency and offloading traffic from the origin server for content that's the same for every user.
It's highly effective for static or infrequently-changing content (images, JS/CSS bundles, video)
and, with the right cache-control configuration, even for semi-dynamic content that's the same
across users for a short window. It does *not* help for genuinely per-user, real-time dynamic
content — caching that at the edge either serves stale/wrong data to the wrong user or requires a
cache key so granular it stops functioning as a shared cache at all.

**Example:**
```
Cache-Control: public, max-age=86400          # product image — great CDN hit rate
Cache-Control: private, no-store               # "your account balance" — must not be cached
Cache-Control: private, max-age=0, must-revalidate  # personalized feed — edge can't help here
```

**Why it's a trap:** "put a CDN in front of it" is offered as a default performance fix even for
endpoints that are inherently per-user — the trap is treating the CDN as free speed rather than
checking first whether the response is actually shareable across requests.

### Reliability

#### Q18. What's the idempotency-key trap when a client retries a write after a timeout?
**Answer:** A client sends a write (e.g. "place order"), the server processes it and commits, but
the response is lost in transit or the client times out before it arrives — from the client's
point of view the request's outcome is unknown, so a naive client retries the exact same request.
Without an explicit mechanism to recognize "this is the same logical request, not a new one," the
retry executes the write a second time — a second order, a second charge. The fix is an
idempotency key: the client generates a unique key per logical operation (not per HTTP attempt)
and sends it with every attempt; the server persists the key alongside the result of the first
successful execution and, on seeing a repeated key, returns the stored result instead of
re-executing the write. This has to be enforced with a uniqueness constraint at the storage layer,
not just an in-memory check, or a race between two near-simultaneous retries can still slip both
through.

**Example:**
```
POST /orders
Idempotency-Key: 7f3a9c21-...   <- same key on every retry of THIS logical request

Attempt 1: times out client-side after the server already committed the order
Attempt 2 (retry, same key): server finds the key already recorded -> returns the
                              original order's result, does NOT insert a new row

CREATE UNIQUE INDEX ON idempotency_keys (key);  -- the actual enforcement point
```

**Why it's a trap:** "just retry on timeout, it's safer than losing the request" is the instinct —
true for reads, false for writes without idempotency, and a candidate who says "just retry"
without naming the duplicate-write risk hasn't actually thought through what "timeout" means: the
request may well have succeeded server-side even though the client never found out.

#### Q19. How do backpressure and load shedding keep an overloaded system alive, and what goes wrong without them?
**Answer:** Every system has a maximum throughput; when the arrival rate exceeds it, work piles up in queues (thread pools, connection
backlogs, message queues), **latency grows without bound**, memory fills, timeouts fire, clients retry, and the retries add *more*
load — a self-reinforcing collapse from which the system often cannot recover even after the original spike ends (a "metastable failure"; see S20). Two
mechanisms prevent it. **Backpressure** pushes the limit upstream: bounded queues that block or reject when full, a consumer that signals how much it can take
(reactive streams demand, TCP windows, Kafka's pull model), and a producer that slows down. **Load shedding** deliberately rejects excess work early and cheaply —
return `429`/`503` with `Retry-After` immediately — so the requests you do accept are served fast; prioritize by importance (health checks and paying customers over batch traffic) and shed
the *least valuable* first. Supporting practices: **timeouts** on every remote call (shorter than the caller's own timeout, a deadline propagated
downstream), **retries with exponential backoff and jitter** and a retry budget, **circuit breakers** to stop calling a failing dependency, **bulkheads**
(separate pools so one slow dependency can't consume all threads), and autoscaling as a *complement* — it reacts in minutes, while overload
arrives in seconds. Unbounded queues are the anti-pattern: they turn overload into invisible latency and finally an out-of-memory crash.

**Example:**
```java
// Bounded work queue: when full, reject immediately instead of queueing forever.
ThreadPoolExecutor pool = new ThreadPoolExecutor(
    16, 16, 0, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(200),                    // bounded: at most 200 waiting
    new ThreadPoolExecutor.AbortPolicy());            // -> RejectedExecutionException

@PostMapping("/reports")
ResponseEntity<?> create(@RequestBody ReportRequest r) {
    try {
        pool.execute(() -> reports.generate(r));
        return ResponseEntity.accepted().build();
    } catch (RejectedExecutionException e) {
        return ResponseEntity.status(503).header("Retry-After", "5").build();   // shed load early
    }
}
```

**Why it's a trap:** teams treat capacity as "add more servers" and leave every queue unbounded, so the first traffic
spike or slow dependency converts into minutes of latency and an outage that outlasts the trigger. Failing fast under overload looks like a worse
user experience in a demo, but it's what keeps the service available for the requests it can serve.

#### Q20. Why isn't a distributed lock (Redis `SET NX`, ZooKeeper, database row) as safe as it looks, and what are fencing tokens?
**Answer:** A lock is meant to guarantee that only one worker at a time performs an action on a resource. In a distributed system the lock holder
can be *wrong about still holding it*: the lock is acquired with a **TTL** (so a crashed holder doesn't block everyone forever), but a long GC pause, a stalled VM or a
slow network can make the holder continue to work after the lease expired — while a second worker has acquired the lock and is also working. Both then
write, and the guarantee is silently gone. Clock skew and the lock service itself failing over (a Redis primary crashing before
replicating the lock key) create the same effect. Checking "do I still hold the lock?" right before writing does not fix it, because the pause can occur between the check and the write. The robust
fix is a **fencing token**: the lock service hands out a monotonically increasing number with each grant; the worker sends the token with every write
to the protected resource, and the *resource* rejects any write carrying a token lower than one it has already seen. This moves the correctness guarantee from the (unreliable) lock
holder to the (authoritative) resource. Where a fencing token isn't possible, design so that the action is **idempotent** (Q18) or make the write conditional
(`UPDATE ... WHERE version = ?`, optimistic locking), which is often a simpler alternative to a lock. Use locks for *efficiency* (avoid duplicate work) rather than *correctness*
unless you have fencing; for real mutual exclusion prefer the database's own row locks/unique constraints, or a consensus-based system (etcd/ZooKeeper) with fencing.

**Example:**
```text
worker A: acquires lock, token=33   ── long GC pause ──────────────► writes (token=33)  REJECTED
lock TTL expires
worker B: acquires lock, token=34 ──► writes (token=34) OK   (storage remembers max token = 34)

storage rule:  if request.token < max_seen_token: reject
```
```sql
-- Optimistic alternative: the write only succeeds if nobody changed the row meanwhile.
update accounts set balance = :new, version = version + 1
where id = :id and version = :expected_version;      -- 0 rows updated -> conflict, retry
```

**Why it's a trap:** `SET key value NX PX 30000` in a code sample feels like a mutex, and the failure
only appears under the rare pause or failover that never happens in tests — then two workers double-charge a customer or corrupt a file. The defence is to stop
trusting the lock holder's opinion of the lock.

#### Q21. What do RTO and RPO mean in disaster recovery planning, and how do they drive architecture decisions?
**Answer:** **RTO (Recovery Time Objective)**: how long the system can be down before the business
impact is unacceptable — drives decisions about failover automation and standby infrastructure.
**RPO (Recovery Point Objective)**: how much data loss (measured in time) is acceptable — drives
replication and backup frequency decisions. Both are business decisions, not purely technical
ones — an architect's job is translating a stated RTO/RPO into the concrete technical mechanism
that actually achieves it, and pushing back if a stated target (e.g. "zero data loss, zero
downtime") would require cost or complexity disproportionate to the actual business need behind
it.

**Example:**
```
RTO = 5 min   -> needs automated failover to a hot standby, health checks, auto-promotion
RPO = 0       -> needs synchronous replication for the affected data (Q10), not async
RTO = 4 hours -> a documented manual runbook and a warm (not hot) standby is enough
```

**Why it's a trap:** candidates sometimes propose the most robust possible setup (synchronous
multi-region, automated everything) regardless of the stated targets — over-building against a
looser RTO/RPO than the business actually needs is its own real cost, not a safe default.

### Architecture & security

#### Q22. When is a monolith the better choice over microservices, and what's the real cost of choosing microservices too early?
**Answer:** A monolith is the better default for a small team, an early-stage product with an
evolving/unclear domain model, or a system where the operational overhead of distributed systems
isn't yet justified by an actual organizational or scaling need. The real cost of premature
microservices: splitting a system along boundaries that turn out to be wrong (the actual domain
boundaries weren't understood yet) is far more expensive to undo across network boundaries and
separate deployments than refactoring module boundaries within one codebase — and a small team now
also owns the full operational burden of a distributed system for a scale and organizational
structure that didn't need it yet. Microservices earn their cost specifically when independent
team ownership, independent deployability, and independent scaling become genuine, currently-felt
constraints.

**Example:**
```
Year 1, 4-person team splits into "user-service", "order-service", "notification-service" —
the actual bounded contexts weren't known yet, so "order" needs "user" data on every
request: a chatty network call replaces what used to be one in-process join, and the team
now debugs 3 deployments instead of 1 for every feature.
```

**Why it's a trap:** "microservices are the scalable/modern choice" is offered as a default — a
senior answer names the *specific*, currently-felt constraint that justifies the split, and is
comfortable saying a monolith is the right answer for a team that doesn't have that constraint yet.

#### Q23. What does an API Gateway centralize, and why put it in front of a microservices architecture?
**Answer:** An API Gateway sits as the single entry point in front of a set of backend services,
centralizing concerns that would otherwise need to be duplicated in every individual service:
authentication/authorization, rate limiting, request routing, protocol translation, and often
response aggregation. The trade-off: it's a new single point that, if it fails, can take down
access to every service behind it — which is why gateway availability/redundancy is treated with
the same seriousness as any other genuinely critical path component, and why gateway logic itself
should stay thin (routing and cross-cutting concerns) rather than accumulating actual business
logic.

**Example:**
```
client -> [API Gateway: authn, rate-limit, route] -> user-service
                                                    -> order-service
                                                    -> notification-service

Gateway goes down -> every service behind it becomes unreachable, even though each
individual service is still healthy on its own.
```

**Why it's a trap:** candidates propose a gateway as pure upside (auth in one place!) without
naming the SPOF it introduces — the follow-up worth pre-empting is "what happens when the gateway
itself goes down," which is exactly why gateway redundancy gets treated as seriously as the
services it fronts.

#### Q24. Name several OWASP Top 10 risks and how you mitigate each at a system-design level.
**Answer:** **Injection** (SQL, command): parameterized queries/prepared statements, never
string-concatenated input into a query. **Broken authentication**: strong password policies, MFA,
secure session management, not rolling your own crypto/auth. **Sensitive data exposure**: encrypt
data in transit (TLS) and at rest, don't log sensitive fields, minimize what's collected/retained
in the first place. **Broken access control**: enforce authorization server-side on every request
(never trust a client-side check alone), default-deny rather than default-allow. **Security
misconfiguration**: no default credentials, minimal exposed surface, patched dependencies.
**Cross-site scripting (XSS)**: escape/sanitize any user input rendered back into HTML, use a
framework's built-in escaping rather than hand-rolled string interpolation into markup.
**Insecure deserialization**: never deserialize untrusted input into arbitrary types without
strict validation. The system-design-level point: security is a set of deliberate boundary
decisions (where is input validated, where is output escaped, where is authorization enforced)
baked into the architecture, not a checklist applied after the fact.

**Example:**
```java
// Injection — vulnerable:
String sql = "SELECT * FROM users WHERE email = '" + input + "'"; // attacker: ' OR '1'='1

// Fixed — parameterized, input is always data, never concatenated into the query text:
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE email = ?");
ps.setString(1, input);
```

**Why it's a trap:** candidates list the risks fine but treat them as a checklist to mention, not
boundaries to design around — the follow-up that actually separates a senior answer is "where in
the architecture is this enforced, and can a caller bypass that layer" (a client-side-only
authorization check is the single most common version of this gap in practice).

#### Q25. How do you approach back-of-envelope capacity estimation in a system design interview?
**Answer:** Start from the given (or reasonably assumed, stated explicitly) scale — daily active
users, requests per user per day — and derive requests per second, being explicit about
peak-to-average ratio (a common simplifying assumption is peak ≈ 2-3x average). From there,
estimate storage (average size per record × records per day × retention period) and bandwidth
(requests/sec × average payload size). The point of doing this out loud isn't precision — it's
showing that architectural decisions later (does this need to be sharded, does this need a CDN, is
a single database instance remotely plausible) are grounded in actual numbers rather than vibes.

**Example:**
```
10M DAU, 20 requests/user/day -> 200M req/day -> ~2,300 req/sec average
Peak ~3x average -> ~7,000 req/sec peak -> this number decides whether one DB instance
                                             is even plausible before drawing anything
```

**Why it's a trap:** candidates often either skip this entirely or do it so quietly it doesn't
inform the design — the trap is treating it as a box to check rather than a number that should
visibly change a downstream decision (sharding, caching, CDN) in the same interview.

### Leadership

#### Q26. A junior engineer keeps making the same category of mistake despite repeated code review comments. What's your concrete approach?
**Answer:** First, check whether the feedback so far actually explained the underlying principle
or just corrected the specific instance each time — repeating "fix this" without the reusable
"why" behind it teaches pattern-matching to that one review comment, not the generalizable
judgment that would prevent the *next* instance. Have a direct, private conversation — walk
through two or three real examples together, ask them to articulate the underlying principle in
their own words, and agree on something concrete to try differently going forward. If the pattern
still continues after a genuinely clear, direct conversation, that's a signal to loop in their
manager — but the first move is always a real conversation focused on understanding, not an
escalation.

**Example:**
```
PR comment pattern (3 PRs in a row): "missing null check on line 42"
                                       "missing null check on line 88"
                                       "missing null check on line 15"
-> each was fixed individually, none explained *why* this class of input can be null here,
   or how to recognize the pattern before writing the code, not just after review flags it.
```

**Why it's a trap:** the instinct under interview pressure is "I'd just keep leaving clear review
comments" — the question is specifically testing whether the candidate recognizes that repeated
correct comments that don't land are a signal the intervention itself needs to change, not repeat.

#### Q27. How do you push back on a technical decision coming from a senior stakeholder or manager that you believe is wrong?
**Answer:** Lead with genuine curiosity about their reasoning before asserting your own — they may
have context you don't (a business constraint, a prior failed attempt, a timeline pressure that
changes the calculus). State your concern concretely and specifically (the actual risk or cost,
ideally with a rough quantification), propose a specific alternative rather than only raising an
objection, and be explicit about what you'd need to see to change your mind. If, after that
conversation, the decision still goes the other way and it's not a correctness-or-safety-critical
issue, the senior-level move is committing fully to the decided direction rather than relitigating
it repeatedly — "disagree and commit," reserved for genuinely non-critical disagreements.

**Example:**
```
Weak pushback:   "I don't think we should do it this way."
Strong pushback: "This approach adds ~2 weeks of migration risk because it touches the
                  payments schema live. If we instead do X, we lose feature Y for one
                  release but avoid that risk. What would need to be true for the
                  original approach to still be right?"
```

**Why it's a trap:** vague disagreement ("I have concerns") reads as friction without substance —
the trap is stopping at raising an objection instead of pairing it with a concrete cost and a
concrete alternative, which is what actually makes pushback persuasive rather than just noted.

#### Q28. As a tech lead, how do you handle a design review where two senior engineers strongly disagree?
**Answer:** Separate the disagreement from the individuals first — make sure both people feel
genuinely heard, then get both positions written down concretely enough to compare on the same
axes (what does each approach optimize for, what does each cost, under what future scenario would
each turn out to have been the better call). Look for whether this is a decision with a knowable
right answer reachable via more information (a spike, a benchmark) versus a genuine values/
priority trade-off with no objectively correct answer — the first case is resolved by getting the
missing information; the second is a judgment call that ultimately needs an owner to make, once
both sides are fully heard, rather than being left to fester as an unresolved standoff.

**Example:**
```
Position A: "Event-sourced — full audit trail, but higher complexity, 3 extra weeks."
Position B: "CRUD + audit table — simpler, ships now, harder to replay history later."

Resolvable by a spike? No — it's a genuine priority trade-off (audit depth vs. time-to-ship)
-> tech lead names the priority for this project explicitly, makes the call, explains why.
```

**Why it's a trap:** trying to reach full consensus on a genuine values trade-off can stall a
project indefinitely — the trap is treating "get everyone to agree" as the goal instead of "get
the decision made, explained, and owned," which is what a stalled review actually needs.

#### Q29. How do you scope and estimate a project with genuinely high uncertainty for stakeholders who want a firm date?
**Answer:** Be explicit that a single point estimate for a highly uncertain project is itself a
lie dressed up as precision — instead, communicate a range grounded in the actual sources of
uncertainty (spell out what's unknown: an unfamiliar third-party integration, an unclear
requirement, a dependency on another team's unshipped work). Propose a concrete way to *reduce*
the uncertainty early — a short time-boxed spike on the riskiest unknown before committing to a
full estimate. Break the project into milestones with their own checkpoints, so the stakeholder
gets real signal on whether the project is tracking to the estimate well before the final
deadline.

**Example:**
```
"3-5 weeks. The 2-week spread is entirely the unfamiliar payment-provider integration —
 we haven't confirmed their sandbox supports partial refunds yet. We'll spike that in
 week 1 and can tighten the estimate to +/- 2 days by end of week 1."
```

**Why it's a trap:** caving to pressure for a fake-precise single date, or refusing to estimate at
all, are both worse than a range with a named cause — the trap is treating "give me a firm date"
as a request that must be answered with a firm date, rather than reframed around what's actually
driving the uncertainty.

## 🔴 Expert / Open

### Design exercises

#### Q30. Design Instagram's feed at a high level, then go deep on one component.
**Answer:** Functional requirements: post a photo, follow users, view a feed of posts from
followed accounts, like/comment. Non-functional: read-heavy (far more feed views than posts), feed
generation must be fast, eventual consistency acceptable for like counts and even feed freshness
within a small window. HLD: a post service handling uploads (metadata to a database, the image to
object storage, served via CDN); a social graph service tracking follow relationships; and a feed
generation approach — the natural deep-dive point. **Fan-out on write** (when a user posts, push
the post into every follower's precomputed feed immediately, stored in a fast store like Redis)
makes feed *reads* extremely fast but is expensive for accounts with millions of followers and
wastes work precomputing feeds for followers who may never check them. **Fan-out on read**
(compute the feed at request time by querying posts from everyone the user follows) avoids that
write amplification but makes *reads* expensive for a user following many accounts. Real systems
use a hybrid: fan-out on write for the vast majority of users, and fan-out on read specifically for
posts from high-follower-count accounts, avoiding the fan-out-on-write explosion for exactly the
case where it would be worst.

**Example:**
```
Normal user posts (500 followers):
  write -> push post_id into all 500 followers' precomputed feed lists (Redis)

Celebrity posts (50M followers):
  write -> post stored once, NOT fanned out
  follower's feed read -> merge their precomputed list with "posts from celebrities I
                            follow, queried live" at request time
```

**Why it's a trap:** candidates often present fan-out-on-write as simply "the fast option" without
naming the celebrity-account failure mode — a design that doesn't special-case high-follower-count
accounts will visibly fall over (or silently rack up enormous write amplification) the moment a
real celebrity account is modeled in the same system.

#### Q31. Design a rate limiter as a distributed system component. What are the scale considerations?
**Answer:** Start from the algorithm choice (token bucket is a common default for allowing natural
bursts within an average-rate cap), then the harder system-design question: where does the rate
limit's state actually live, given the limiter needs to work correctly across many instances of
the service being protected, not just one. A per-instance in-memory counter is simple but wrong at
scale — it under-limits (each instance separately allows the full limit, so N instances
collectively allow N times the intended limit). The standard fix is centralizing counter state in
a fast shared store (Redis, using atomic increment-with-expiry operations) that every instance
checks against — introducing its own considerations: the shared store becomes a new critical-path
dependency (fail open vs. fail closed if it's briefly unavailable is a real design decision with
real trade-offs) and adds a network round-trip to every check, which needs to stay fast enough not
to become the new bottleneck for the very requests it's meant to protect.

**Example:**
```
Per-instance counter (wrong at scale):
  instance-1: allows 100/min   instance-2: allows 100/min   instance-3: allows 100/min
  -> a client behind a load balancer effectively gets ~300/min, not the intended 100/min

Shared Redis counter (correct):
  INCR rate:user123:2026-09-16T10:05  EX 60
  every instance checks the SAME counter -> the limit is actually 100/min, cluster-wide
```

**Why it's a trap:** the algorithm (token bucket vs sliding window) is the part candidates
over-prepare for — the actual scale-breaking bug is almost always the per-instance-state mistake,
which the algorithm choice alone doesn't fix.

#### Q32. Design a notification system (email, SMS, push) that serves many product teams. Then go deep on delivery guarantees.
Clarify first (Q1): channels, volume (say 50 M notifications/day with 10× spikes on marketing campaigns), latency classes (an OTP must arrive in seconds, a
newsletter can take hours), user preferences and opt-outs, and whether ordering or exactly-one delivery matters. **Architecture:** producers (other services) call a
notification API or publish an event; the service validates, applies user preferences, quiet hours and regulatory rules (unsubscribe, consent), renders a template with
localization, and puts a message on a **per-channel, per-priority queue** (separate queues so a bulk marketing burst can't delay OTPs — a bulkhead, Q19). **Channel workers** consume and
call providers (SES/SendGrid, Twilio, APNs/FCM), with **provider abstraction and failover** to a second vendor, per-provider rate limits and backoff. Persist a notification record with a
state machine (`QUEUED → SENT → DELIVERED / FAILED`), and ingest provider webhooks for delivery, bounce and complaint events, which feed a suppression list. **Delivery
guarantees:** end to end it is **at-least-once**: the queue redelivers on worker failure and a provider call may succeed while the response is lost, so
duplicates are possible; reduce them with an **idempotency key** per logical notification (dedupe table with a unique constraint before sending, Q18), use provider-supported
idempotency where it exists, and accept that a rare duplicate is better than a lost OTP — for critical messages prefer duplicates to loss, for marketing prefer the reverse. Failures: retry with exponential
backoff and jitter up to a limit, then a dead-letter queue with alerts; bad addresses and hard bounces stop retries. **Scale and abuse:** shard/partition by user or
tenant, apply per-user and per-tenant rate limits (Q31) so a bug in one producer can't spam every customer, and protect the provider reputation (warm-up, throttling, complaint monitoring).
Observability: queue lag and age per priority, send/delivery latency, bounce and complaint rates. The open trade-offs to discuss: a broker choice (SQS/Kafka/RabbitMQ), synchronous
send for OTPs versus everything through queues, per-user digesting to avoid notification fatigue, and whether to build this or buy it (Q35).

### Multi-region

#### Q33. How would you design a service to run active-active across two regions, and what do you have to give up?
Active-active means both regions serve **live traffic and accept writes**, giving lower latency for users near each region and survival of a whole-region loss with minimal
failover time (RTO close to zero, Q21). The hard part is data. With **asynchronous replication** between regions, a write in region A becomes visible in B some
milliseconds to seconds later (the replication lag is your RPO), and if both regions can write the *same record* you get **conflicts**: last-write-wins by timestamp (simple, silently loses
updates and depends on clock quality), CRDTs or merge functions for data with a natural merge (counters, sets, collaborative text), or application-level
resolution. **Synchronous** cross-region replication (Spanner-style consensus) avoids conflicts but adds a WAN round-trip (tens to hundreds of ms) to every write. The pragmatic designs sidestep the
problem: **partition data by ownership** (each user or tenant has a *home region* that handles their writes, with the other region as a warm replica — "active-active by
shard"), keep strongly consistent, conflict-prone data (balances, inventory) single-writer while allowing multi-region for read-heavy or naturally mergeable data, and route with geo-DNS or
global load balancing. What has to be built and tested: health-checked traffic failover, data-store choices that support multi-region writes (DynamoDB global tables, Cassandra,
CockroachDB/Spanner) or tolerated replication lag with read-your-writes handling (Q11) via sticky routing, **idempotent** event processing because events are replicated and replayed,
unique-ID generation that doesn't collide across regions, and **capacity headroom** — if one region dies the survivor must absorb 100% of traffic, so each runs at under
50% or autoscales fast. Costs: roughly double infrastructure, higher complexity and a bigger blast radius for bad deployments (roll out region by region). Be honest with the interviewer that many
systems are better served by active-passive with a tested failover, and that the requirement (a real RTO/RPO number, Q21) — not the technology — should justify active-active.

### Leadership & strategy

#### Q34. You inherit a team with low morale and significant technical debt. Describe your approach for the first 90 days as tech lead.
**Answer:** Resist the urge to immediately start big rewrites or sweeping changes before
understanding why things got this way — the first weeks are primarily for listening: 1:1s with
every team member, and reviewing recent incidents/postmortems and the actual state of the codebase
directly rather than relying on secondhand narrative alone. Find one or two concrete, visible wins
achievable within the first month — not the biggest technical debt item, but something that
demonstrably reduces a real daily pain point, building trust that things can actually improve
before asking for patience on the bigger, slower structural work. In parallel, establish a small
number of concrete, lightweight practices that compound over time (a blameless postmortem process,
protected time for technical debt, clearer definition of done), and be explicit and transparent
with the team about the plan and the reasoning behind prioritization decisions. By the end of 90
days, the goal isn't that the technical debt is gone — it's that the team trusts there's a
credible, visible plan being executed.

**Example:**
```
Weeks 1-2:  1:1s with all 6 engineers + read last 4 postmortems + skim the top 5 hottest files
Week 3:     ship one visible fix for the #1 complaint (flaky CI -> stable in 3 days)
Weeks 4-12: protected 20% time for debt, blameless postmortem template adopted,
            weekly written update on what shipped and why it was prioritized
Day 90:     debt backlog is still long, but every engineer can name what changed and why
```

**Why it's a trap:** the instinct under interview pressure is to open with a bold technical plan
(a rewrite, a new architecture) — the question is testing whether the candidate leads with
listening and a small trust-building win first, since a team with low morale won't buy into a big
plan from someone who hasn't yet earned credibility with them.

#### Q35. How do you decide between building a component yourself and buying (or adopting open source)?
Frame it as **total cost of ownership over the lifetime**, weighed against strategic value. Ask first: is this a **differentiator** — something that gives the product a competitive
advantage — or **commodity** (authentication, payments, email delivery, observability, search)? Commodity capabilities almost always favor buying or adopting: the vendor
has already spent thousands of engineer-years on edge cases, compliance (PCI, SOC 2, GDPR) and security patches, and your engineers' scarce time goes to
what only your company can build. Build when it *is* the differentiator, when no product fits the constraints (latency, data residency, unusual scale), or when vendor lock-in and pricing
at your scale would hurt more than the engineering cost. Include the full cost of each: for **build** — initial development, ongoing maintenance and on-call, security
and upgrade burden, hiring people who understand it, and the opportunity cost of what those people didn't build; for **buy** — license or usage fees that grow with volume (model the
price at 10× traffic), integration effort, **lock-in and exit cost** (data export, API differences), vendor stability, SLAs, and lost flexibility. Reduce the risk of buying by isolating the vendor behind
your own thin interface (an adapter or anti-corruption layer), keeping the data portable, and running a time-boxed proof of concept against your real requirements. Reduce the risk of building by
starting with the smallest version and re-evaluating: a homegrown component that has become a maintenance burden with no differentiating value is a signal to replace it with a product, and a
vendor whose costs or constraints now dominate is a signal to bring it in-house. Write the decision and its assumptions down (an ADR) with a date to revisit it, so the team can tell later whether the reasoning still holds.

## 🎯 Real-world scenarios

### S1. A single server outage takes down the entire application
- **Symptoms:** One server crashes or becomes unreachable, and the application is entirely down
  for all users until it's manually restarted or replaced.
- **Diagnosis:** No redundancy exists — a single instance with no load balancer in front of it and
  no standby is a textbook single point of failure; the "cause" isn't really the crash itself
  (servers crash) but the architecture's lack of tolerance for that entirely normal event.
- **Example:**
  ```
  10:14:02  app-01 (only instance) OOM-killed by the orchestrator
  10:14:02  no other instance registered -> 100% of traffic returns connection refused
  10:19:41  app-01 manually restarted -> service recovers, 5 minutes of full outage
  ```
- **Resolution:** Restore service immediately (restart, replace the instance), then as the actual
  fix, introduce a load balancer with at least two instances behind it, so any one instance's
  failure degrades capacity rather than taking down the whole system.
- **Prevention:** Treat "what happens when this single component fails" as a required design
  question for every component in a production architecture, not an afterthought addressed only
  after the first outage it causes.

### S2. A cache expiring for a hot key causes a sudden spike in database load
- **Symptoms:** A brief but severe database load spike (and often a corresponding latency spike or
  timeout wave) occurs at a predictable interval, correlating with a popular cached item's TTL
  expiring.
- **Diagnosis:** Cache stampede — many concurrent requests for the same now-expired hot key all
  simultaneously miss the cache and hit the database to recompute/refetch the same value at once,
  rather than one request refreshing it while others wait or serve stale data briefly.
- **Example:**
  ```
  14:00:00.000  hot key "homepage:featured" TTL expires
  14:00:00.010-14:00:00.300  4,800 concurrent requests all miss cache simultaneously
  14:00:00.310  database connection pool exhausted -> unrelated queries start timing out too
  ```
- **Resolution:** Add request coalescing (only one request actually queries the database on a
  miss for a given key; concurrent requests for the same key wait on that one result), or serve
  slightly stale data while asynchronously refreshing in the background ("stale-while-revalidate"),
  or stagger TTLs with jitter so many keys don't expire at exactly the same instant.
- **Prevention:** For any hot key with a scale where simultaneous cache misses could plausibly
  overwhelm the source-of-truth, request coalescing or TTL jitter should be part of the caching
  design from the start, not a reactive fix after the first stampede-caused incident.

### S3. A client's retried request after a timeout creates a duplicate order instead of one
- **Symptoms:** A customer is charged twice, or sees two identical orders from a single checkout
  click, and support tickets mention "I only clicked once."
- **Diagnosis:** Trace the request logs for the duplicate pair — check whether both requests came
  from the same client within a short window (a client-side retry after a timeout) and whether the
  API accepted the write without any de-duplication mechanism (Q18).
- **Example:**
  ```
  10:02:01  POST /orders  (attempt #1) -> server commits order #4471, response lost in transit
  10:02:04  client times out waiting for a response -> automatically retries
  10:02:04  POST /orders  (attempt #2, no idempotency key) -> server has no way to
            recognize this as the same logical request -> commits a second order #4472
  ```
- **Resolution:** Add an idempotency-key requirement to the write endpoint, backed by a unique
  constraint at the database layer, and manually refund/merge the duplicate orders already created
  for affected customers.
- **Prevention:** Require an idempotency key on every client-facing write endpoint from the start,
  specifically flagged in API design review for any endpoint a client might retry (payments, order
  creation, anything triggered by a button a user might double-click or a mobile client might
  retry on flaky connectivity).

### S4. Two halves of a distributed system independently accept conflicting writes during a network partition
- **Symptoms:** After a network partition between two data centers (or two sets of nodes) is
  resolved, conflicting data is discovered — both sides accepted writes for what should have been
  the same, single logical record, and they disagree.
- **Diagnosis:** This is a "split-brain" outcome, and it's the direct, expected consequence of an
  AP (Availability-favoring) system design choice during a partition (Q8) — both sides kept
  serving requests during the partition (by design, for availability), and reconciling the
  resulting conflict is the cost that choice always deferred to partition-recovery time.
- **Example:**
  ```
  region A (majority) accepts: UPDATE inventory SET qty = qty - 1 WHERE sku = 'X'  (5 -> 4)
  region B (minority, still serving for availability) accepts the same decrement independently
  partition heals: both sides claim qty = 4, but 2 units actually sold -> real qty should be 3
  ```
- **Resolution:** Apply the system's chosen conflict-resolution strategy (last-write-wins by
  timestamp, a custom merge function, or in genuinely ambiguous cases, surfacing the conflict for
  manual/business-level resolution) — the specific mechanism should have been decided as part of
  choosing AP in the first place, not improvised during the actual incident.
- **Prevention:** If a system is designed AP, conflict resolution needs to be a first-class,
  designed-and-tested part of the architecture from day one, not an assumption that partitions
  "probably won't happen" — they will, eventually, and the system needs a real answer ready.

### S5. A user immediately re-reads their own just-saved data and sees the old value
- **Symptoms:** A user updates their profile/settings, sees a "saved" confirmation, but on the
  very next page load the old value is back — support gets reports of "my changes aren't saving"
  even though the write clearly succeeded server-side.
- **Diagnosis:** Check whether reads are load-balanced across replicas independently of where the
  preceding write landed (Q11) — confirm by checking whether the "reverted" value reappears
  consistently after a short delay (replication lag catching up) rather than staying wrong forever.
- **Example:**
  ```
  10:00:00.000  PATCH /settings {theme: "dark"}  -> primary commits, ack sent
  10:00:00.050  GET /settings                    -> routed to replica-2, lag = 180ms
  10:00:00.050  replica-2 still has theme: "light" -> UI reverts to light before the
                replica catches up 130ms later
  ```
- **Resolution:** Route the immediate post-write read for that user to the primary (or a replica
  confirmed caught up) for a short window, or have the client trust its own optimistic write
  instead of immediately re-fetching.
- **Prevention:** Treat "does this flow read its own write" as a required check for any feature
  with an immediate confirm-then-redisplay pattern, before it ships on top of a load-balanced
  read-replica setup.

### S6. One database shard is consistently far busier than the others, and its overload periodically degrades the whole system
- **Symptoms:** Monitoring shows one specific shard with disproportionately high CPU/latency
  compared to its siblings, and its degradation correlates with broader system slowdowns.
- **Diagnosis:** A hot shard from a bad shard key choice (Q14) — a small number of high-activity
  keys landing on the same shard are generating a disproportionate share of total load, and the
  shard's own capacity is the actual bottleneck even though overall cluster capacity looks fine in
  aggregate.
- **Example:**
  ```
  shard-us: cpu 94%, p99 latency 890ms
  shard-eu, shard-apac, shard-latam: cpu 20-30%, p99 latency 40ms
  cluster-wide average CPU reported on the main dashboard: 36% ("looks healthy")
  ```
- **Resolution:** Short-term mitigation might include manually isolating or specially caching the
  specific hot key(s)' data; the durable fix is re-sharding with a key (or a strategy incorporating
  consistent hashing, Q15, or splitting an outlier key further) that distributes load more evenly.
- **Prevention:** Model realistic access-pattern skew (not just storage volume) when initially
  choosing a shard key, specifically checking for known or plausible high-activity outliers before
  committing to a key that would concentrate them on one shard.

### S7. A design review between two senior engineers stalls a project for weeks with no resolution
- **Symptoms:** Two senior engineers have strongly held, opposing views on a core architectural
  decision, and repeated review meetings fail to converge — the project's timeline is slipping
  while the disagreement continues.
- **Diagnosis:** As the tech lead reviewing this, check whether the disagreement is actually about
  a knowable technical fact (resolvable with a spike/benchmark) or an unstated difference in what
  each person is optimizing for (Q28) — a stalled disagreement often persists specifically because
  neither side has identified that they're arguing from different, unstated priorities.
- **Example:**
  ```
  Week 1: review meeting -> no resolution, "let's discuss again next week"
  Week 2: same two positions restated, no new information surfaced
  Week 3: project owner asks each engineer to write down what their approach optimizes
          for -> reveals a genuine time-to-ship vs. long-term-flexibility trade-off, not a
          resolvable factual disagreement -> tech lead makes the call the same day
  ```
- **Resolution:** Facilitate a conversation that makes both positions' actual trade-offs explicit
  and comparable, get any resolvable factual question answered directly, and if it's genuinely a
  judgment call with no objectively right answer, make the call explicitly as the decision-owner.
- **Prevention:** Establish a clear decision-making process (who has final say, and under what
  circumstances a time-boxed spike settles a disagreement) before a project starts, so a genuine
  disagreement has a known path to resolution rather than defaulting to indefinite debate.

### S8. A junior engineer's PRs keep repeating the same category of mistake despite review comments
- **Symptoms:** Code review comments correctly identify the same class of issue across several
  consecutive PRs from the same engineer, each time fixed individually but recurring in the next
  PR.
- **Diagnosis:** Per Q26 — the review comments are correcting instances, not building the
  underlying judgment that would prevent the *next* instance; a pattern of recurrence despite
  repeated correct feedback usually means the "why" hasn't actually landed, not that the person
  isn't listening.
- **Example:**
  ```
  PR #212 review comment: "missing null check here"
  PR #219 review comment: "same issue as #212 — missing null check"
  PR #227 review comment: "third time — let's talk"  <- direct 1:1 held after this, not #212
  ```
- **Resolution:** Have the direct, principle-focused conversation from Q26 rather than another PR
  comment — walk through several real examples together, have them explain the underlying
  principle back in their own words, and agree on a concrete forward practice.
- **Prevention:** For any category of mistake appearing more than twice from the same person,
  switch from PR comments to a direct conversation proactively, rather than waiting for it to
  become an obviously entrenched pattern.

### S9. Team morale visibly drops after a layoff or reorg, and productivity/trust suffer
- **Symptoms:** Remaining team members show reduced engagement, increased skepticism toward
  leadership communication, and a noticeable slowdown in delivery beyond what headcount reduction
  alone would explain.
- **Diagnosis:** Trust erosion after a layoff/reorg is a normal, expected response, not a
  discipline problem — people are processing uncertainty about their own security and grieving
  colleagues/working relationships that changed.
- **Example:**
  ```
  Before reorg: sprint velocity ~40 pts, Slack activity in #team normal
  2 weeks after: velocity ~22 pts, 1:1s reveal 4/6 remaining engineers are job-searching,
                 standup updates get noticeably shorter and less detailed
  ```
- **Resolution:** Over-communicate, honestly, more than feels necessary — acknowledge what
  happened directly, be transparent about what is and isn't known about the future, and rebuild
  predictability through consistent, smaller commitments kept reliably, rather than one large
  gesture to "fix" morale.
- **Prevention:** This is largely not preventable at the individual-manager level once a
  layoff/reorg decision is made above them, but a manager's own consistent, honest communication
  pattern *before* any such event is what determines how much residual trust there is to rebuild
  from.

### S10. A stakeholder demands an unrealistic deadline for a complex feature
- **Symptoms:** A stakeholder states a hard deadline for a feature the engineering team assesses
  as requiring meaningfully more time than that, with the deadline apparently non-negotiable from
  the stakeholder's framing.
- **Diagnosis:** Before assuming the deadline itself is the immovable constraint, clarify what's
  actually driving it (a real external commitment versus an internally chosen target that's more
  flexible than it sounds) and separately clarify whether the *scope* is truly fixed.
- **Example:**
  ```
  Stakeholder: "This needs to ship by the 30th, no exceptions — it's tied to a partner launch."
  Follow-up: "Is the 30th the partner's hard date, or our internal target for it?"
  Answer: "...it's actually our target, the partner's real cutoff is 6 weeks later."
  -> the "non-negotiable" deadline had 6 weeks of hidden slack once actually asked about.
  ```
- **Resolution:** Present the actual trade-off explicitly — "here's what fits by that date, here's
  what would need to move to a follow-up, here's the risk if we compress it instead" — and let the
  stakeholder make an informed decision, using Q29's estimation-under-uncertainty approach if the
  scope itself is still unclear.
- **Prevention:** Build a working relationship with recurring stakeholders where scope and
  timeline trade-offs are a normal, expected part of the conversation from the start of any
  project, rather than the first such conversation happening under deadline pressure.

### S11. Two team members are in ongoing conflict over code ownership or technical approach
- **Symptoms:** Repeated friction in reviews or planning between two specific team members,
  escalating beyond normal technical disagreement into a personal or territorial dynamic that's
  starting to affect the wider team's dynamics.
- **Diagnosis:** Distinguish a genuine, resolvable technical disagreement (Q28's territory) from a
  relationship/communication breakdown that happens to be expressed through technical
  disagreements — the second needs a different intervention than more technical discussion.
- **Example:**
  ```
  Reviewer A (1:1): "I keep getting blocked because B rewrites my PRs in review instead of
                      commenting."
  Reviewer B (1:1): "A's code doesn't follow the patterns we agreed on, so I just fix it
                      myself to keep things moving."
  -> both are reacting to a missing shared review norm, not to each other personally.
  ```
- **Resolution:** Have separate 1:1 conversations with each person first, then, if appropriate, a
  facilitated joint conversation focused on working relationship and communication norms going
  forward, not relitigating the specific technical disagreements that triggered it.
- **Prevention:** Address friction early, at the first sign of a pattern rather than after it's
  visibly affecting the broader team — a private, low-stakes conversation early is far easier than
  a larger mediation after weeks of accumulated friction.

### S12. A production incident traces back to an architectural decision you personally made
- **Symptoms:** A postmortem investigation identifies the root cause as a specific design choice
  you advocated for and made, not an unrelated bug or an outside factor.
- **Diagnosis/reflection:** This is a moment where how you handle it matters as much as the
  technical fix — minimizing your own role, or conversely over-apologizing in a way that derails
  the postmortem's actual purpose, are both less useful than a clear, factual account of the
  decision and what's different now that makes the outcome visible.
- **Example:**
  ```
  Postmortem timeline entry, written by the decision-maker themselves:
  "2026-02-11: I chose async replication for the orders DB to hit the launch date,
   accepting the RPO trade-off documented in ADR-014. That trade-off is what caused
   today's data loss on failover. The information available in Feb didn't include our
   current write volume."
  ```
- **Resolution:** Own the decision plainly without deflecting blame elsewhere, focus the
  discussion on the blameless postmortem's actual goal (what systemic factor allowed this outcome,
  and what changes reduce the chance of a similar mistake from anyone in the future), and follow
  through visibly on the agreed action items.
- **Prevention:** A team that's watched their tech lead handle their own mistake this way builds
  far more trust in the blameless postmortem process than one that's only seen it applied to
  others — this specific moment is disproportionately influential in whether the team actually
  believes the process is blameless in practice.

### S13. Choosing asynchronous replication for availability leads to a real, user-visible data-loss incident during a failover
- **Symptoms:** A primary database failure triggers failover to a replica, and users report data
  they'd recently submitted (in the seconds before the failure) is missing from the promoted
  replica.
- **Diagnosis:** This is the direct, known consequence of the async replication design choice
  (Q10) manifesting for real — replication lag meant the replica wasn't fully caught up at the
  moment of failover, and any writes not yet replicated at that instant are genuinely lost.
- **Example:**
  ```
  10:41:03  primary DB fails
  10:41:03  replica was 1.8s behind at time of failure (normal lag for this system)
  10:41:05  replica promoted -> the last ~40 writes in that 1.8s window are gone,
            confirmed missing when customers report orders they placed "disappeared"
  ```
- **Resolution:** Communicate transparently with affected users about the specific lost data if
  it's identifiable, and reassess whether the RPO (Q21) this incident just demonstrated in
  practice actually matches what the business intended when async replication was chosen — if the
  tolerance was overestimated, that's the trigger to revisit toward a tighter-RPO design for the
  specific data where this matters most.
- **Prevention:** Make the RPO trade-off an explicit, documented decision communicated to
  stakeholders when async replication is chosen, framed around "this means up to N seconds of
  recent writes can be lost on an unplanned failover" in concrete terms.

### S14. A core service becomes the system's dominant bottleneck as the company's traffic grows 10x
- **Symptoms:** A service architected years earlier for a much smaller scale is now consistently
  the limiting factor on overall system throughput and latency, despite various tactical
  optimizations already applied to it.
- **Diagnosis:** Distinguish a genuine architectural ceiling (the current design fundamentally
  can't scale further regardless of tuning) from a solvable inefficiency (an unoptimized query, a
  missing cache) being mistaken for an architectural problem — the fix and its cost differ greatly
  depending on which it actually is.
- **Example:**
  ```
  order-service p99 latency: 80ms (2 years ago, 500 req/s) -> 1,400ms (today, 6,000 req/s)
  already applied: query caching, connection pool tuning, read replicas
  still degrading linearly with load -> single-writer primary is the actual ceiling,
  not a fixable inefficiency
  ```
- **Resolution:** If it's genuinely architectural, this is where Q22's monolith-to-microservices
  or Q14's sharding decisions get revisited with the benefit of now actually knowing the real
  access patterns and bottleneck — propose a specific re-architecture targeted at the measured
  bottleneck, not a broad rewrite for its own sake.
- **Prevention:** Revisit architectural assumptions proactively at meaningful growth milestones —
  a system architected for the previous order of magnitude of scale is exactly the kind of thing
  worth explicitly re-evaluating before it becomes the thing blocking the next order of magnitude.

### S15. An on-call rotation drowns in non-actionable pages, and the team stops trusting alerts enough to react quickly to a real one
- **Symptoms:** The on-call rotation receives dozens of pages a week, the large majority of which
  resolve themselves or require no action; engineers report muting or delaying pages, and a
  genuinely critical incident recently went unacknowledged for 20+ minutes because it looked like
  routine noise.
- **Diagnosis:** Pull the last month of pages and categorize each as actionable (required a human
  response) vs. non-actionable (self-resolved, flapping, or symptomatic of a known, already-tracked
  issue) — a high non-actionable ratio is the direct cause of the desensitization, not a discipline
  problem with whoever's on call.
- **Example:**
  ```
  Last 30 days: 214 pages fired
    - 6   required actual human intervention
    - 91  self-resolved within 2 minutes (flapping health check, no action needed)
    - 117 duplicate/downstream alerts for one root-cause incident, firing separately
  -> signal-to-noise ratio ~2.8%, and the one incident that mattered was buried in it
  ```
- **Resolution:** Re-tune alert thresholds against actual actionability, add alert deduplication/
  grouping so one root cause fires one page instead of many, and delete or downgrade-to-
  non-paging any alert that hasn't required action in the review window.
- **Prevention:** Review paging alerts against actual actionability on a recurring cadence, and
  treat "did this page require a human to actually do something" as the bar for keeping it as a
  page at all, rather than a ticket or a dashboard metric.

### S16. A team member consistently responds defensively to code review feedback, regardless of how it's delivered
- **Symptoms:** Reasonable, well-phrased review feedback is repeatedly met with pushback,
  justification, or visible frustration from one specific team member, even when the feedback is
  factually correct and delivered constructively by multiple different reviewers.
- **Diagnosis:** Consistent defensiveness across multiple reviewers and multiple delivery styles
  suggests the issue isn't really about how feedback is phrased — it's more likely about how the
  person experiences feedback generally.
- **Example:**
  ```
  Reviewer A: "consider extracting this into a helper" -> pushback + justification thread
  Reviewer B: "nit: this could be simplified" -> same pattern, different reviewer, same person
  Reviewer C (different team, first time reviewing this person): same pattern again
  -> consistent across reviewers and phrasing rules out "it's how it's being said."
  ```
- **Resolution:** Have a direct, private, curious (not accusatory) conversation specifically about
  the pattern itself, separate from any specific PR, and separately, make sure the team's review
  culture itself isn't inadvertently contributing.
- **Prevention:** Establish clear, shared review norms and expectations across the team early, so
  an individual's reaction to feedback is more likely to be about the specific content than an
  ambiguous or inconsistently-applied standard.

### S17. A cross-team dependency repeatedly blocks your team's delivery
- **Symptoms:** Your team's roadmap keeps slipping because a required piece of work from another
  team isn't ready when needed, recurring across multiple projects rather than a one-off
  scheduling miss.
- **Diagnosis:** A recurring pattern suggests a structural issue — priorities aren't actually
  aligned between the teams, or there's no clear process for negotiating and committing to
  cross-team work items with any real accountability.
- **Example:**
  ```
  Project Alpha: slipped 3 weeks waiting on Team Y's export API
  Project Beta (2 months later): slipped 2 weeks waiting on the same Team Y, different API
  -> a recurring pattern with the same team, not a one-off scheduling miss
  ```
- **Resolution:** Escalate to make the dependency and its business impact visible at a level where
  both teams' priorities can actually be reconciled, bringing concrete, quantified impact rather
  than a vague "we're blocked" complaint.
- **Prevention:** For known, recurring cross-team dependencies, establish an explicit
  prioritization/commitment process before the next project needs it, rather than informal asks
  that have no real mechanism for being honored under competing priorities.

### S18. Sunsetting a legacy system that many teams still depend on proves far harder than expected
- **Symptoms:** A planned deprecation of an old system stalls repeatedly — teams keep having "just
  one more" dependency that isn't ready to migrate, and the sunset date keeps slipping.
- **Diagnosis:** The plan likely underestimated the actual scope of dependents and/or didn't give
  dependent teams sufficient incentive or support to actually prioritize their migration work over
  their own roadmap pressures.
- **Example:**
  ```
  known dependents at planning time: 4 services
  actual dependents discovered mid-migration: 11 services, including one found only
  because it started throwing errors the week the legacy write path was deprecated
  ```
- **Resolution:** Do a genuinely thorough dependency audit before committing to a hard date,
  provide concrete migration support (tooling, documentation, direct engineering help for the
  highest-friction migrations), and consider a staged sunset that surfaces forgotten dependents
  earlier and less catastrophically.
- **Prevention:** For any future system expected to have broad internal adoption, build in
  deprecation/migration tooling and dependency tracking from early in its life, not as an
  afterthought once sunsetting becomes necessary years later.

### S19. As an interviewer, you need to evaluate a candidate's system design answer fairly
- **Symptoms:** A candidate produces a design with a reasonable-looking diagram, but you need to
  assess whether it actually reflects strong system design judgment versus memorized, template
  answers that don't demonstrate real understanding.
- **Diagnosis:** The strongest signal isn't whether they drew the "right" diagram — it's whether
  they asked clarifying questions before designing (Q1), whether they can articulate the actual
  trade-off behind each significant decision, and whether they can go deep on at least one
  component when pushed.
- **Example:**
  ```
  Candidate proposes fan-out-on-write for the whole feed design, no mention of celebrity
  accounts. Interviewer: "This account has 50M followers — walk me through what happens
  when they post."
  Strong candidate: adapts live, proposes the fan-out-on-read special case (Q30).
  Weak candidate: repeats the original design unchanged, doesn't register the new constraint.
  ```
- **Resolution:** Push on trade-offs specifically ("why this and not X") rather than accepting a
  stated design at face value, and introduce a changed constraint mid-interview to see whether
  they can adapt their design and reasoning live.
- **Prevention:** Calibrate interviewer expectations and rubrics around trade-off reasoning and
  adaptability specifically, not diagram completeness or matching a specific "correct" reference
  architecture.

### S20. A slow dependency triggers a full-system outage that continues long after the dependency recovers
- **Symptoms:** The recommendations service becomes slow for two minutes (a bad deploy, since rolled back). Within
  five minutes the product page, checkout and login all fail with timeouts. The dependency is healthy again, yet the platform stays down
  for 40 more minutes and only recovers after engineers restart services and block traffic at the load balancer.
- **Diagnosis:** A **cascading and metastable failure** (Q19). Trace the request path: the product service calls recommendations synchronously with a
  10-second timeout, so during the slowdown every worker thread is parked waiting; the thread pool and connection pool
  saturate, health checks fail, instances are restarted (cold caches, heavy start-up), and clients and upstream services **retry**, multiplying the load
  2–3×. Even when the dependency recovers, the retry traffic plus the cold start keep the system above capacity, so it stays down — the trigger is gone but the feedback loop sustains it.
  Evidence: thread-pool queue length and active-thread count flat at maximum, request rate to each layer higher than the
  user request rate, and a timeline showing retries as the dominant traffic.
- **Example:**
  ```text
  user req/s:               1,000  (constant)
  product -> reco calls:    1,000 -> 3,000 req/s (3 attempts, no backoff, no budget)
  reco capacity:            1,500 req/s   => stays overloaded although the original bug is fixed
  ```
- **Resolution:** Break the loop: shed load at the edge (rate-limit or reject a share of traffic with `503`), disable the non-essential call (feature flag on recommendations),
  scale out warmed instances, and reopen traffic gradually. Then fix the design: short timeouts (well under the user-facing budget), a **circuit breaker with a
  fallback** (show generic recommendations), bulkheaded pools so an optional dependency can't take all threads, retries with backoff, jitter and a retry budget, and bounded queues. Verify with a
  game-day test that injects 5 s latency into recommendations and confirms checkout stays healthy.
- **Prevention:** Classify dependencies as critical vs optional and degrade gracefully for the latter; propagate deadlines; alert on saturation (queue depth, thread usage) as well as errors;
  practice failure injection regularly; include "how does this behave when the dependency is slow, not down?" in every design review.

### S21. One Redis key receives most of the traffic; that node saturates while the cluster average looks fine
- **Symptoms:** During a flash sale, a Redis Cluster node sits at 100% CPU with rising latency and timeouts, while the other nodes are at 10%.
  Adding nodes and resharding doesn't help. The product-detail page for the sale item is slow for everyone.
- **Diagnosis:** A **hot key**: one key is mapped to one slot on one node, so adding shards cannot spread its load (Q14's shard-key lesson in a cache). Confirm with
  `redis-cli --hotkeys` (needs LFU policy) or `MONITOR` sampling briefly, per-key access metrics in the client, and node-level CPU/network compared across the cluster.
  Related to S2's cache-expiry stampede: check whether the key also expires simultaneously for all clients.
- **Example:**
  ```text
  GET product:99871      # 180,000 req/s -> all routed to the node owning slot 4128
  other keys             # ~2,000 req/s per node
  ```
- **Resolution:** Reduce the load on the single key: add a small **local in-process cache** (a TTL of a few seconds via Caffeine) so most reads never leave the app instance; **replicate
  the hot key** under several names (`product:99871#0..7`, choose one at random on reads, write to all) to spread it over nodes; use read replicas for reads; serve the
  page through the CDN (Q17). Protect against the expiry stampede with jittered TTLs and request coalescing/single-flight. Verify with a load test at flash-sale rates that no single node
  exceeds ~60% CPU.
- **Prevention:** Load-test with realistic *skewed* distributions (Zipf), not uniform keys; monitor per-key or per-slot traffic; pre-warm and pre-replicate known hot items
  (campaign products) before an event; design keys so extremely popular items have a multi-level cache.

### S22. The monthly cloud bill is 3× the forecast and nobody knows why
- **Symptoms:** Finance flags a bill of $180k versus the $60k expected. There has been no traffic growth of that order, and no one can point to
  a specific change; the cost dashboard shows "EC2-Other" and "Data Transfer" as the largest lines.
- **Diagnosis:** Break the cost down by **service, account, region, and tag** (Cost Explorer / CUR queries) and look at *when* it increased, then correlate with the deploy
  and change history. Typical culprits: **NAT gateway / cross-AZ / cross-region data transfer** (a chatty service in another zone, traffic to S3 through a NAT rather than a gateway endpoint),
  a **logging or metrics explosion** (debug logging left on, high-cardinality labels), forgotten resources (unattached volumes, idle load balancers, old snapshots, abandoned test clusters),
  autoscaling that scales out but never in, oversized instances, uncapped serverless invocations from a retry loop or infinite trigger, and unlimited storage retention. The absence of tagging
  is itself the root cause of "nobody knows".
- **Example:**
  ```text
  Cost Explorer, group by usage type (month over month):
    NatGateway-Bytes           $ 4,200 -> $ 61,000     <- a new service reads S3 through the NAT
    CloudWatch Logs ingestion  $ 3,100 -> $ 38,000     <- DEBUG level enabled in production
  ```
- **Resolution:** Stop the largest leak first (add the S3 gateway endpoint, restore log levels, set a retention policy), delete orphaned resources, right-size and tune autoscaling
  scale-in; then confirm the daily cost curve bends within days. Negotiate with the owners using data, not blame, and record savings.
- **Prevention:** Mandatory **cost-allocation tags** (team, service, environment) enforced at deploy time; budgets and **anomaly-detection alerts** per account/team; cost review in
  architecture review (estimate the bill of a new design at 10× traffic); show teams their own spend (FinOps); lifecycle and retention defaults for logs, snapshots and buckets.

### S23. Product wants features only; engineering says the tech debt is slowing everyone down — and leadership won't fund cleanup
- **Symptoms:** Lead time per feature has doubled in a year, incidents recur in the same legacy module, and the best engineers grumble about "the
  billing code". Every request for a "refactoring sprint" is turned down as an unquantified cost with no customer value.
- **Diagnosis:** The problem is usually **communication and prioritization**, not a lack of goodwill: debt is described in engineering terms ("it's messy") that
  the business cannot weigh against features. Gather evidence: how much of each sprint goes to rework and bug fixes in that module, cycle time and change-failure rate before and
  after, incident count and cost attributable to it, onboarding time, and the features it has *blocked or delayed*. Identify which debt has interest (in the path of upcoming roadmap
  work) versus debt that is ugly but stable and can be left alone (Q34's 90-day approach).
- **Example:**
  ```text
  Billing module, last 2 quarters:
    31% of bug tickets, 4 of 6 Sev-2 incidents, median PR lead time 9 days (vs 2 days elsewhere)
    Q3 roadmap: 3 of 5 planned features touch it  ->  estimated 6 weeks of extra work if untouched
  ```
- **Resolution:** Present it as a business case: cost of delay and risk versus a bounded investment ("3 weeks now saves ~6 weeks in Q3 and removes the main
  source of Sev-2s"). Propose an incremental approach that keeps shipping — refactor *as part of* the roadmap features that touch the area, protect a fixed capacity
  share (10–20%) for debt with agreed metrics, or a strangler approach — rather than a big-bang "stop features for a quarter". Agree on success measures and review them.
- **Prevention:** Track debt explicitly (a visible register with impact and cost of delay), make quality metrics part of regular product reviews, apply the "boy scout" rule
  in day-to-day work, and keep engineering leaders and product in a standing conversation about capacity allocation rather than a crisis-time negotiation.

### S24. An engineer's output and quality have dropped over several months, and the team notices
- **Symptoms:** A previously reliable engineer now misses commitments, PRs are late and low-effort, they are quieter in meetings, and colleagues quietly start
  routing around them. No one has raised it directly.
- **Diagnosis:** Don't assume "performance problem" — first find out **what changed**: the person's work (a mismatch of role or skill, unclear expectations, an
  unwanted project), the environment (a reorg, a new manager, unclear priorities, a toxic dynamic, blocked by other teams) or their life (health, burnout, family). Have a
  private, curious one-to-one (before any formal process) asking open questions and looking at facts: specific examples of missed expectations, how they got there, whether goals were clear, whether
  the workload is realistic. Compare against the expectations the person was actually given, not an unstated bar.
- **Example:**
  ```text
  1:1 opening: "I've noticed the last three deliverables slipped and you seem less engaged than usual.
                I want to understand what's going on and how I can help - what's your view?"
  -> reveals: moved to a legacy project against their wishes + no clear ownership since the reorg
  ```
- **Resolution:** Depending on the cause: clarify expectations and ownership in writing, remove blockers, adjust the work or give support (time off, reduced load
  if it is a personal situation, coaching or pairing for a skill gap), and agree on **specific, measurable goals with a check-in cadence** (e.g. weekly for 4–6 weeks). Document the conversations. If
  there is no improvement despite clear expectations and real support, involve HR/the manager and move to a formal improvement plan — with dignity, and with honest communication about the possible outcomes. Verify
  progress against the agreed goals, not impressions.
- **Prevention:** Regular 1:1s and early, specific feedback so problems surface in weeks, not quarters; explicit expectations per level; watch for burnout signals; and address the issue directly instead of letting
  the team compensate silently, which erodes the trust of everyone else.

### S25. A big-bang data migration fails halfway through the cutover, and the team cannot cleanly roll back
- **Symptoms:** On a Saturday cutover to a new database (or new service) after a six-month migration project, the migration script fails at 60% because of unexpected
  data (malformed legacy rows). The application has already switched some writers to the new system, so the two stores now contain different data. The team debates
  rolling forward versus rolling back for hours; leadership asks for an ETA nobody can give.
- **Diagnosis:** The plan lacked a **reversible, incremental path**: it depended on a single point-in-time copy with no
  validation of data quality beforehand, no way to keep both systems in sync, and a rollback plan that was never rehearsed (and impossible once new writes went to the new system only). The
  root causes are the big bang itself and untested assumptions about production data; the immediate need is to determine exactly which writes exist in which system.
- **Example:**
  ```text
  T-0   switch writes to new DB              (old DB frozen, no reverse sync)
  T+2h  migration of history fails at 60%    (legacy rows violate new constraints)
  T+3h  new DB has 3h of writes not in old DB -> "rollback" would lose 3h of customer data
  ```
- **Resolution:** Stabilize: stop further changes, **decide from data** — put the app in maintenance/read-only mode if needed, and reconcile by replaying the post-cutover writes into the old system
  (from the change log/outbox) or complete the fix-forward if the failure is understood and bounded. Communicate honestly and regularly. After recovery, redo the migration with the safe pattern:
  **expand/contract** and **dual-write or CDC-based sync** so old and new stay consistent, **shadow reads** comparing results, a **backfill in batches** that is
  idempotent and restartable, gradual traffic shifting by percentage or tenant, and a **rehearsed rollback** that is valid at each step until the old system is decommissioned. Verify by automated
  reconciliation (row counts, checksums, sampled comparisons) before each step.
- **Prevention:** Never plan a migration whose only rollback is restoring a backup; profile production data for anomalies early; rehearse the whole thing on a production-sized copy with timing; define go/no-go criteria and abort points in advance;
  keep the old system read-only and available for a fixed period after cutover; and treat the decommissioning of the old system as a separate, later decision (see S18).

## 📌 Cheat-sheet

- **Before designing**: functional requirements (what) + non-functional requirements (how well — scale, latency, availability, cost) — always first.
- **HLD vs LLD**: big pieces and data flow vs one feature's implementation detail.
- **CAP**: during a partition, pick Consistency or Availability — not a universal answer, a per-system, per-use-case trade-off.
- **OWASP mitigations**: parameterized queries (injection), server-side authz on every request (broken access control), escape output (XSS), TLS + encryption at rest (sensitive data), minimal exposed surface (misconfiguration).
- **Horizontal vs vertical**: vertical = simple, hard ceiling, SPOF; horizontal = no ceiling, fault-tolerant, real distributed-systems complexity.
- **Idempotency keys**: a client's retry-after-timeout can duplicate a write without one — enforce with a unique constraint at the storage layer, not an in-memory check.
- **Sync vs async replication**: sync = no lag, higher latency/lower availability; async = lower latency/higher availability, replication lag = possible data loss on failover.
- **Read-your-own-writes**: async replica reads can make a user's own write look reverted — route the immediate post-write read to the primary, or trust the client's optimistic write.
- **Shard key**: pick for even *load* distribution, not just storage — watch for low-cardinality or activity-skewed keys, which a healthy cluster-wide average can hide.
- **Consistent hashing**: minimizes remapping when nodes join/leave — avoids cache-stampede-style mass invalidation that modulo hashing causes.
- **CDN**: great for static/shared content; no help for genuinely per-user real-time dynamic data.
- **Cache strategies**: cache-aside (lazy, simple, staleness risk) / write-through (consistent, slower writes) / write-behind (fast, data-loss risk) — pick deliberately, plus TTL as a safety net.
- **Back-of-envelope**: DAU → requests/sec (with peak multiplier) → storage/bandwidth — ground decisions in real numbers, even rough ones.
- **Monolith vs microservices**: default to monolith until independent team ownership/deployability/scaling is a *current*, real constraint — premature splitting costs more to undo than late splitting costs to do.
- **API Gateway**: centralizes auth, rate limiting, routing — becomes a new critical single point, keep it thin.
- **Eventual vs strong consistency**: eventual for low-cost-of-staleness data (like counts); strong for anything where staleness has real financial/business cost (balances, inventory).
- **RTO/RPO**: business-defined tolerances for downtime and data loss — translate into concrete replication/failover/backup architecture, don't over- or under-build against them.
- **On-call alert fatigue**: a low actionable-page ratio is what desensitizes a team, not a discipline problem — tune thresholds and dedupe against actual actionability, not theoretical risk.
- **Leadership**: specific, timely, why-focused feedback; separate people from disagreements in design reviews; own mistakes plainly in blameless postmortems; make trade-offs and estimates-under-uncertainty explicit rather than implicit.
- **SQL vs NoSQL**: relational by default (ACID, joins, ad-hoc queries); add specialized stores as *derived* copies; choose a NoSQL primary only for a nameable reason (key-based access at huge scale, write volume, multi-region writes).
- **Stateless services**: no per-user state in instance memory or local disk — sessions, files and jobs move to shared stores; state losses may only cost performance, never correctness.
- **Overload**: unbounded queues turn spikes into invisible latency and OOM; use bounded queues, backpressure, load shedding (`429`/`503` + `Retry-After`), timeouts, backoff + jitter, retry budgets, circuit breakers, bulkheads.
- **Distributed locks**: a TTL lock can expire while its holder is paused — use fencing tokens checked by the resource, or idempotent/conditional writes (`WHERE version = ?`); locks are for efficiency, not correctness.
- **2PC vs saga**: 2PC = atomic but blocking and coordinator-bound; saga = local transactions + idempotent compensations, eventually consistent, irreversible steps last, publish events via an outbox.
- **Notification system**: per-channel/priority queues (bulkheads), provider failover, idempotency key, at-least-once with dedupe, DLQ, webhooks feed suppression lists, per-tenant rate limits.
- **Active-active**: the hard part is write conflicts — partition by home region, keep conflict-prone data single-writer, LWW loses updates; survivor must absorb 100% of traffic; often active-passive is enough.
- **Build vs buy**: build differentiators, buy commodity; compare TCO at 10× scale including lock-in and exit cost; isolate vendors behind an adapter; record the decision as an ADR with a review date.
- **Cascading failure**: slow beats down — retries + saturated pools + cold restarts keep a system down after the trigger is gone; break the loop by shedding load and degrading optional dependencies.
- **Hot keys**: adding shards can't split one key — local cache, key replication, read replicas, CDN; jittered TTLs and single-flight.
- **Cloud cost**: group by service/usage type/tag; usual suspects are data transfer/NAT, logs and metric cardinality, orphaned resources; enforce tags, budgets and anomaly alerts.
- **Tech-debt negotiation**: translate debt into cost of delay, incidents and blocked roadmap items; refactor along the roadmap and reserve a fixed capacity share.
- **Declining performance**: find *what changed* before assuming a performance problem; clear written expectations, support, measurable goals, then a formal process if needed.
- **Migrations**: expand/contract, dual-write or CDC sync, shadow reads, idempotent batched backfill, gradual cutover, rehearsed rollback, and reconciliation before decommissioning.
