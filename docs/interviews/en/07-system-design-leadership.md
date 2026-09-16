# System Design & Leadership

## 🟢 Fundamentals

### Q1. What two questions do you ask before starting any system design, and why do they come before any diagrams?
"What should it do?" (functional requirements — sign up, upload a photo, follow a user, scroll a
feed, like/comment) and "how well must it do it?" (non-functional requirements — speed,
durability, scale, availability, cost). They come first because every architectural decision
later in the design is a trade-off made *in service of* a specific non-functional requirement —
you can't meaningfully choose between strong and eventual consistency, or between a monolith and
microservices, without first knowing the actual scale, latency budget, and availability target;
skipping straight to a diagram produces a design optimized for assumptions nobody asked for.

### Q2. What's the difference between high-level design (HLD) and low-level design (LLD)?
HLD is the zoomed-out view — the big pieces of the system (app servers, database, cache, queue,
CDN) and how requests move between them. Designing Instagram at HLD level asks: where does a
user's request go, where is data stored, what happens as traffic grows, what breaks first and
how is that component scaled or made resilient. LLD zooms into one specific feature and asks the
implementation-level questions: for a "like" feature specifically — what happens when the user
taps like, which function/service handles it, how do you check whether the user already liked
the post, how is the like persisted, how is the like count updated without double-counting the
same user. An interview (and a real design doc) typically moves from HLD to a deep dive into one
or two components at LLD depth, rather than staying entirely at one level throughout.

### Q3. What is a load balancer, and what specific problem does it solve?
When a single server runs out of CPU/RAM to handle growing traffic, adding another server only
helps if requests are actually distributed across both — a load balancer sits in front of
multiple servers and decides which one handles each incoming request (round-robin, least-
connections, or more sophisticated algorithms), turning "one server that's now overloaded" into
"N servers sharing the load," and also removing a failed server from rotation so traffic doesn't
keep flowing to something down. It's the first component most horizontally-scaled designs
introduce, because without it, adding more servers doesn't actually help — nothing routes traffic
to them.

### Q4. What is caching, and what's the basic idea behind cache invalidation?
Caching keeps a copy of frequently-requested or expensive-to-compute data in a faster-access
layer (in-memory, closer to the client) so repeated requests for the same data don't repeat the
expensive underlying work (a slow query, a heavy computation, a network call) every time.
Invalidation is the harder half: once cached data is served instead of the source of truth, the
cache has to be updated or expired when the underlying data changes, or clients get stale data
indefinitely — the basic strategies (TTL-based expiry, explicit invalidation on write, and the
read/write patterns in Q15) all exist because "cache it and forget it" silently trades
correctness for speed unless invalidation is deliberately designed.

### Q5. What makes technical feedback and mentorship actually effective, as opposed to just correct?
Effective feedback is specific (points at the actual line/decision, not a general impression),
timely (given close to when the work happened, not batched into a vague quarterly comment),
focused on the work and its impact rather than the person, and — critically for mentorship
specifically — explains the *why* behind the suggestion so the person can generalize it to the
next situation, not just fix this one instance. The distinction from "just correct" matters: a
technically accurate comment delivered in a way that reads as dismissive or purely critical can
be right and still fail at its actual goal, which is helping someone build better judgment over
time, not just getting this one PR fixed.

## Senior traps🟡

### Q6. Explain the CAP theorem with a concrete example — why can't a distributed system have all three?
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

### Q7. Name several OWASP Top 10 risks and how you mitigate each at a system-design level.
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

### Q8. Horizontal vs vertical scaling — what's the actual trade-off?
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

### Q9. What's the idempotency-key trap when a client retries a write after a timeout?
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

### Q10. What's the difference between synchronous and asynchronous database replication, and what does each trade off?
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
that never needed that guarantee (see Q19).

### Q11. Why does read-your-own-writes break under asynchronous replication, and how do you fix it for the data that needs it?
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

**Why it's a trap:** this is easy to conflate with Q19's "eventual consistency is fine for
low-stakes data" — but the stakes here aren't about the data's importance, they're about *whose*
read is affected: staleness a different user sees is usually invisible and fine, staleness the
*writer* sees immediately after their own write reads as a broken feature.

### Q12. How do you choose a database shard key, and what happens with a bad choice?
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

### Q13. What is consistent hashing, and why is it used for distributed caches and sharding instead of simple modulo hashing?
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

### Q14. What does a CDN actually solve, and when does it not help?
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

### Q15. Name the main cache invalidation/write strategies and their trade-offs — "there are only two hard things in computer science."
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

### Q16. How do you approach back-of-envelope capacity estimation in a system design interview?
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

### Q17. When is a monolith the better choice over microservices, and what's the real cost of choosing microservices too early?
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

### Q18. What does an API Gateway centralize, and why put it in front of a microservices architecture?
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

### Q19. Give a concrete, practical example of choosing eventual consistency over strong consistency, and explain why it's the right call there.
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

### Q20. What do RTO and RPO mean in disaster recovery planning, and how do they drive architecture decisions?
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

### Q21. A junior engineer keeps making the same category of mistake despite repeated code review comments. What's your concrete approach?
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

### Q22. How do you push back on a technical decision coming from a senior stakeholder or manager that you believe is wrong?
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

### Q23. As a tech lead, how do you handle a design review where two senior engineers strongly disagree?
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

### Q24. How do you scope and estimate a project with genuinely high uncertainty for stakeholders who want a firm date?
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

## Expert / Open🔴

### Q25. Design Instagram's feed at a high level, then go deep on one component.
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

### Q26. Design a rate limiter as a distributed system component. What are the scale considerations?
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

### Q27. You inherit a team with low morale and significant technical debt. Describe your approach for the first 90 days as tech lead.
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

## Real-world scenarios🎯

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
  API accepted the write without any de-duplication mechanism (Q9).
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
  AP (Availability-favoring) system design choice during a partition (Q6) — both sides kept
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
- **Diagnosis:** A hot shard from a bad shard key choice (Q12) — a small number of high-activity
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
  consistent hashing, Q13, or splitting an outlier key further) that distributes load more evenly.
- **Prevention:** Model realistic access-pattern skew (not just storage volume) when initially
  choosing a shard key, specifically checking for known or plausible high-activity outliers before
  committing to a key that would concentrate them on one shard.

### S7. A design review between two senior engineers stalls a project for weeks with no resolution
- **Symptoms:** Two senior engineers have strongly held, opposing views on a core architectural
  decision, and repeated review meetings fail to converge — the project's timeline is slipping
  while the disagreement continues.
- **Diagnosis:** As the tech lead reviewing this, check whether the disagreement is actually about
  a knowable technical fact (resolvable with a spike/benchmark) or an unstated difference in what
  each person is optimizing for (Q23) — a stalled disagreement often persists specifically because
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
- **Diagnosis:** Per Q21 — the review comments are correcting instances, not building the
  underlying judgment that would prevent the *next* instance; a pattern of recurrence despite
  repeated correct feedback usually means the "why" hasn't actually landed, not that the person
  isn't listening.
- **Example:**
  ```
  PR #212 review comment: "missing null check here"
  PR #219 review comment: "same issue as #212 — missing null check"
  PR #227 review comment: "third time — let's talk"  <- direct 1:1 held after this, not #212
  ```
- **Resolution:** Have the direct, principle-focused conversation from Q21 rather than another PR
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
  stakeholder make an informed decision, using Q24's estimation-under-uncertainty approach if the
  scope itself is still unclear.
- **Prevention:** Build a working relationship with recurring stakeholders where scope and
  timeline trade-offs are a normal, expected part of the conversation from the start of any
  project, rather than the first such conversation happening under deadline pressure.

### S11. Two team members are in ongoing conflict over code ownership or technical approach
- **Symptoms:** Repeated friction in reviews or planning between two specific team members,
  escalating beyond normal technical disagreement into a personal or territorial dynamic that's
  starting to affect the wider team's dynamics.
- **Diagnosis:** Distinguish a genuine, resolvable technical disagreement (Q23's territory) from a
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
  it's identifiable, and reassess whether the RPO (Q20) this incident just demonstrated in
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
- **Resolution:** If it's genuinely architectural, this is where Q17's monolith-to-microservices
  or Q12's sharding decisions get revisited with the benefit of now actually knowing the real
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
  Strong candidate: adapts live, proposes the fan-out-on-read special case (Q25).
  Weak candidate: repeats the original design unchanged, doesn't register the new constraint.
  ```
- **Resolution:** Push on trade-offs specifically ("why this and not X") rather than accepting a
  stated design at face value, and introduce a changed constraint mid-interview to see whether
  they can adapt their design and reasoning live.
- **Prevention:** Calibrate interviewer expectations and rubrics around trade-off reasoning and
  adaptability specifically, not diagram completeness or matching a specific "correct" reference
  architecture.

## Cheat-sheet📌

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
