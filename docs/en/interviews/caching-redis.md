# Caching & Redis

Deeper caching questions: Redis data structures, eviction, stampedes, Spring Cache pitfalls, locks and cluster topology. The basics are in System Design ([System Design Q7](system-design.md#caching-basic-idea-behind-cache), [System Design Q17](system-design.md#invalidate-cached-entry-race-hides), [System Design Q26](system-design.md#cache-aside-write-write-behind)), along with the incident scenarios [System Design S1](system-design.md#after-deploy-every-cache-entry) (mass expiry), [System Design S7](system-design.md#cache-expiring-hot-key-causes) (hot key expiry) and [System Design S15](system-design.md#one-redis-key-receives-most) (hot shard).

## 🟢 Fundamentals

#### Q1. Why cache, and at which layer? {#why-cache-which-layer}
**Answer:** A cache trades freshness for latency and load: it pays off when reads dominate, the same keys are read repeatedly, and slightly stale data is acceptable. Layers, from closest to the user: browser (`Cache-Control`), CDN, reverse proxy, in-process (Caffeine), distributed (Redis), and the database's own buffer cache. Cache as close to the user as the data's privacy and freshness allow. Measure the **hit ratio** and the load it removes from the database. A 30% hit ratio on a cheap query adds a network hop and a consistency problem for little gain.

#### Q2. Which Redis data structures do you use, and for what? {#redis-data-structures-use-what}
**Answer:** **String**: cached JSON, counters (`INCR`), flags with TTL. **Hash**: an object with fields you update individually (`HINCRBY`), memory-efficient for small objects. **List**: simple queues, latest-N items (`LPUSH` + `LTRIM`). **Set**: membership, unique visitors per day, tags. **Sorted set**: leaderboards, sliding-window rate limits, delayed jobs scored by timestamp. **Stream**: an append-only log with consumer groups, a light alternative to Kafka. **HyperLogLog**: approximate distinct counts in 12 KB. **Bitmap**: per-user daily flags. Picking the right structure moves logic into a single atomic command instead of read-modify-write in the application.

**Example:**

```text
ZADD leaderboard 1520 user:42          # score update, O(log n)
ZREVRANGE leaderboard 0 9 WITHSCORES   # top 10
```

#### Q3. How do TTL and eviction work in Redis, and which `maxmemory-policy` do you pick? {#ttl-eviction-maxmemory-policy}
**Answer:** A TTL deletes a key after a fixed time; eviction deletes keys when `maxmemory` is reached. The default policy is `noeviction`, which **rejects writes** with an OOM error when memory is full. That is right for Redis used as a datastore and wrong for a pure cache. For a cache use `allkeys-lru` or `allkeys-lfu` (LFU keeps frequently read keys better under scans). The `volatile-*` policies only evict keys that have a TTL, so a cache full of keys without TTL behaves like `noeviction`. Redis LRU/LFU is approximate (sampled), which is fine in practice. Always set `maxmemory` below the container limit, with headroom for fork-based persistence.

## 🟡 Senior traps

#### Q4. Cache-aside, read-through, write-through or write-behind: what changes in practice? {#cache-aside-read-write-through}
**Answer:** The trade-offs are in [System Design Q26](system-design.md#cache-aside-write-write-behind). In practice: **cache-aside** (the application reads the cache, falls back to the DB and populates it) is the default with Redis because Redis has no loader. **Read-through** is what Caffeine's `LoadingCache` or Spring `@Cacheable` give you in-process. **Write-through** keeps the cache warm but writes data nobody may read. **Write-behind** risks data loss on a crash and needs idempotent flushes. On a write, prefer **delete the key after the DB commit** over updating it: two concurrent updates can otherwise leave the older value in the cache.

#### Q5. What is a cache stampede, and how do you prevent it? {#cache-stampede-prevent}
**Answer:** When a popular key expires, every concurrent request misses and recomputes it at once, hitting the database with N identical queries. Defences: **TTL jitter** (`ttl ± 10%`) so keys written together do not expire together; **single-flight** (one request recomputes, the others wait or serve stale), using an in-process lock or a short Redis `SET lock NX PX`; **early or background refresh** (refresh before expiry, probabilistically or on a schedule, for known hot keys); **serve stale on error**. Caffeine's `refreshAfterWrite` does early refresh in-process. See [System Design S7](system-design.md#cache-expiring-hot-key-causes) for the incident.

**Example:**

```java
Cache<String, Price> prices = Caffeine.newBuilder()
    .expireAfterWrite(Duration.ofMinutes(10))
    .refreshAfterWrite(Duration.ofMinutes(8))   // async refresh, callers keep the old value
    .build(key -> priceRepository.load(key));
```

#### Q6. What are the classic Spring Cache (`@Cacheable`) pitfalls? {#spring-cacheable-pitfalls}
**Answer:** (1) **Self-invocation**: a call from the same class bypasses the proxy, so nothing is cached. (2) **Keys**: the default key is the method parameters; two methods sharing a cache name with the same parameters collide, and a parameter without `equals`/`hashCode` never hits. Use explicit `key = "#id"`. (3) **No TTL by default**: configure it per cache on the `RedisCacheManager`. (4) **Null caching**: on by default with Redis, which is useful against penetration but hides data created later; tune with `unless = "#result == null"` or a short TTL. (5) **Mutable cached objects** with a local cache: callers mutate the shared instance ([Spring Q20](spring-architecture.md#trap-cacheable-returning-mutable-object)). (6) **Serialization**: JDK serialization breaks when the class changes; prefer JSON with a versioned cache prefix. (7) `@CacheEvict` runs after the method, but **before the transaction commits** if the method is inside one, so a concurrent reader can re-cache the old value.

#### Q7. When do you combine a local cache with Redis, and how do you keep them consistent? {#local-cache-plus-redis}
**Answer:** A local (L1) Caffeine cache avoids the network hop (sub-microsecond vs about 0.5 ms) and protects Redis from hot keys. Redis (L2) is shared by all pods and survives restarts. The cost is that each pod holds its own copy, so an update leaves N stale L1 copies. Options: a **short L1 TTL** (seconds) when slightly stale data is acceptable, which is simplest; **invalidation broadcast** through Redis Pub/Sub or client-side caching (`CLIENT TRACKING`), which is fast but best-effort because messages are lost if a pod is disconnected, so keep a TTL as a safety net. Use L1 only for small, hot, rarely changing data (configuration, reference data, feature flags).

#### Q8. Is Redis durable? When can you use it as a primary datastore? {#redis-durability-rdb-aof}
**Answer:** **RDB** takes periodic fork-based snapshots, so you lose everything since the last snapshot. **AOF** logs every write; with `appendfsync everysec` you lose up to about a second. Replication is **asynchronous**, so a failover can lose acknowledged writes (`WAIT` reduces this but does not make it a consensus system). Treat Redis as a cache (losable, rebuildable) by default. Use it as the source of truth only for data whose loss is tolerable or reconstructible: sessions, rate-limit counters, leaderboards. Otherwise use a managed option with stronger guarantees and accept the trade-offs explicitly. Also plan for Redis being down entirely: [System Design R17](system-design.md#redis-cache-crashes-unexpectedly-application).

## 🔴 Expert / Open

#### Q9. How do you build a lock with Redis, and why is Redlock debated? {#redis-lock-redlock-debate}
**Answer:** Single instance: `SET lock:job42 <random-token> NX PX 30000` to acquire, and release with a Lua script that deletes only if the value is still your token. Otherwise you may delete a lock someone else took after yours expired. The lease expires, so a GC pause or network stall longer than the TTL lets two holders run at once. **Redlock** acquires on a majority of N independent masters. Kleppmann's critique: it relies on bounded clock drift and pauses, and it cannot stop a paused holder from writing. The fix is a **fencing token** (a monotonic number checked by the resource itself), which Redis does not provide. Conclusion: a Redis lock is fine for **efficiency** (avoid duplicate work). For **correctness** use the database (row lock, unique constraint, version column) or a consensus system with fencing. See [System Design Q30](system-design.md#isn-distributed-lock-redis-set).

**Example:**

```lua
-- release only if we still own it
if redis.call("GET", KEYS[1]) == ARGV[1] then return redis.call("DEL", KEYS[1]) else return 0 end
```

#### Q10. Sentinel or Cluster: how does Redis scale and fail over? {#redis-sentinel-cluster-scaling}
**Answer:** **Sentinel** gives high availability for one primary plus replicas: it monitors, elects and promotes, and clients ask Sentinel for the current primary. It does not scale writes. **Cluster** shards the keyspace into 16,384 **hash slots** spread across primaries, each with replicas, so it scales memory and writes. The catch is that multi-key commands, transactions and Lua scripts only work when all keys are in the same slot. Force this with **hash tags** (`{user:42}:cart`, `{user:42}:profile`), at the risk of creating a hot slot. Clients must handle `MOVED`/`ASK` redirects (Lettuce does). Managed services (ElastiCache, MemoryDB) run either mode. Read from replicas only if stale reads are acceptable.

#### Q11. How do you implement a rate limiter, a leaderboard or a session store with Redis atomically? {#redis-atomic-patterns}
**Answer:** The key is to avoid read-modify-write across round trips. **Fixed window**: `INCR key` then `EXPIRE key 60` on the first hit (in a `MULTI` block or Lua, otherwise a crash between the two leaves a counter that never expires). **Sliding window**: a sorted set of timestamps (`ZREMRANGEBYSCORE`, `ZADD`, `ZCARD`) in one Lua script. **Token bucket**: a Lua script storing tokens and last refill time in a hash. **Leaderboard**: `ZINCRBY` / `ZREVRANK`. **Sessions**: a hash per session with a sliding TTL (`EXPIRE` on each access), as Spring Session does. Lua scripts run atomically but block the server, so keep them short. `MULTI` gives atomic execution, not rollback.

#### Q12. How do you keep the cache consistent with the database at scale? {#cache-db-consistency-scale}
**Answer:** Accept that cache-aside is **eventually consistent** and bound the staleness. Patterns, from simplest: a **TTL** as the upper bound on staleness; **delete after commit** (in an `afterCommit` hook or `@TransactionalEventListener(phase = AFTER_COMMIT)`) instead of during the transaction; **delayed double delete** to cover a concurrent reader that re-cached the old value; **CDC-driven invalidation** (Debezium reads the WAL and deletes keys), which catches writes from every service and from manual SQL; **versioned keys** (`product:42:v17`), so a new version is a new key and old entries simply age out. For data that must never be stale (balances, stock at checkout), do not cache it, or re-check against the database at the decision point.

## 🎯 Real-world scenarios

### S1. After a price update, some users see the old price for hours {#stale-price-after-update}
- **Symptoms:** The admin changes a price; the database is correct, but some product pages show the old price until the 6-hour TTL expires. It happens only under load.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A race in cache-aside. `@CacheEvict` runs inside the update transaction, before commit. A concurrent reader misses, reads the **old** committed row and writes it back to Redis. Then the commit lands, and the stale value stays for the full TTL. Confirm by comparing the key's write time (`OBJECT IDLETIME` or a logged timestamp) with the commit time.
- **Resolution:** Evict after commit (`@TransactionalEventListener(phase = AFTER_COMMIT)`), add a delayed second delete for safety, and shorten the TTL for prices.
- **Prevention:** Team rule: cache invalidation happens after commit, never inside the transaction. Add an integration test that runs a concurrent read during an update, and consider CDC-based invalidation ([Q12](#cache-db-consistency-scale)).

</details>

### S2. Writes to Redis start failing with `OOM command not allowed` {#redis-oom-noeviction}
- **Symptoms:** `OOM command not allowed when used memory > 'maxmemory'` in the logs; logins fail because sessions cannot be written; `used_memory` is flat at the limit.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** `INFO memory` and `CONFIG GET maxmemory-policy` show `noeviction` (or `volatile-lru` with keys that have no TTL). `INFO keyspace` shows `expires` far below `keys`; `redis-cli --bigkeys` / `--memkeys` finds the growing prefix, often a cache written without TTL.
- **Resolution:** Delete or add a TTL to the offending prefix (`SCAN` + `UNLINK`, in batches), raise `maxmemory` temporarily, and separate the cache from sessions: one instance with `allkeys-lru` for the cache, another with `noeviction` for data you cannot lose.
- **Prevention:** Every cache write has a TTL (enforced in a shared wrapper), alert on `used_memory / maxmemory > 80%` and on evicted or rejected writes, and track key count per prefix.

</details>

### S3. Redis latency spikes to seconds for every client, a few times a day {#redis-blocked-keys-command}
- **Symptoms:** All services report Redis timeouts simultaneously for 2–5 seconds; Redis CPU hits 100% on one core; there is no traffic spike.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Redis executes commands on a single thread, so one slow command blocks everyone. `SLOWLOG GET 20` shows `KEYS user:*` from an admin job, or `HGETALL`/`SMEMBERS`/`DEL` on a key with millions of elements. `LATENCY DOCTOR` and the fork time in `INFO persistence` rule out an RDB snapshot as the cause.
- **Resolution:** Replace `KEYS` with `SCAN` (cursor-based), use `UNLINK` instead of `DEL` for big keys, split big collections, and paginate with `HSCAN`/`SSCAN`.
- **Prevention:** Disable dangerous commands (`rename-command KEYS ""` or ACLs), alert on slowlog entries, and review any O(n) command in code review.

</details>

### S4. A bot requests random product ids and the database melts despite a 95% hit ratio {#cache-penetration-missing-ids}
- **Symptoms:** Database CPU at 100%; nearly all queries are `SELECT … WHERE id = ?` returning zero rows; the cache hit ratio for real users is unchanged.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** **Cache penetration**: misses for keys that do not exist are never cached, so every request for a fake id goes to the database. The access logs show many distinct ids from a few IPs or tokens.
- **Resolution:** Cache negative results with a short TTL (`product:999999 → NULL`, 60 s), validate the id format at the edge, and rate-limit the caller. For huge id spaces, put a **Bloom filter** of existing ids in front (RedisBloom `BF.EXISTS`).
- **Prevention:** Monitor the miss rate and the "not found" rate separately, and rate-limit per client at the gateway.

</details>

### S5. A nightly job that "can only run once" runs twice and double-charges customers {#redis-lock-two-holders}
- **Symptoms:** Two pods log `acquired lock billing-run` about 40 seconds apart; the job takes 2 minutes; the lock TTL is 30 seconds.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The lease expired while the first pod was still working (the job ran longer than the TTL, or a GC pause stopped it). The second pod acquired the lock legitimately. A Redis lock only gives mutual exclusion while the lease holds ([Q9](#redis-lock-redlock-debate)).
- **Resolution:** Refund the duplicates. Make the charge idempotent at the resource: a unique constraint on `(customer_id, billing_period)` so the second insert fails. Renew the lease while working (a watchdog, as in Redisson) or use a database lock (`SELECT … FOR UPDATE SKIP LOCKED`, ShedLock on a DB table).
- **Prevention:** Never rely on a lease lock alone for correctness; the protected operation must be idempotent or fenced. Alert on job duration approaching the lock TTL.

</details>

### S6. After a deploy, every cached read throws `SerializationException` and traffic falls through to the database {#cache-serialization-after-deploy}
- **Symptoms:** `SerializationException` / `ClassCastException` on `GET` from the cache right after the release; the database load triples; the rollback "fixes" it but breaks again on the next deploy.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The cached class changed shape (renamed field, moved package, JDK serialization `serialVersionUID`) and the new code reads entries written by the old version. During a rolling deploy both versions also overwrite each other's entries.
- **Resolution:** Treat deserialization errors as a miss (evict and reload) instead of failing the request, and bump a **version prefix** in the cache name (`v2:product:42`) so the new release uses fresh keys and old ones age out by TTL.
- **Prevention:** Use JSON (Jackson with `FAIL_ON_UNKNOWN_PROPERTIES` off) instead of JDK serialization, version cache prefixes along with the schema, and pre-warm hot keys on deploy to avoid a cold-cache stampede ([System Design S1](system-design.md#after-deploy-every-cache-entry)).

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q2. Which Redis data structures do you use, and for what?
2. Q3. How do TTL and eviction work in Redis, and which `maxmemory-policy` do you pick?
3. Q5. What is a cache stampede, and how do you prevent it?
4. Q6. What are the classic Spring Cache (`@Cacheable`) pitfalls?
5. Q7. When do you combine a local cache with Redis, and how do you keep them consistent?
6. Q8. Is Redis durable? When can you use it as a primary datastore?
7. Q9. How do you build a lock with Redis, and why is Redlock debated?
8. Q10. Sentinel or Cluster: how does Redis scale and fail over?
9. Q12. How do you keep the cache consistent with the database at scale?
10. S1. After a price update, some users see the old price for hours

## 📌 Cheat-sheet

- **Where** — cache as close to the user as privacy allows. *Measure the hit ratio; a low one is just extra latency.*
- **Eviction** — `allkeys-lru`/`lfu` for a cache, `noeviction` for data. *Every cache key has a TTL.*
- **Writes** — delete the key **after commit**, do not update it. *CDC or versioned keys at scale.*
- **Stampede** — TTL jitter, single-flight, early refresh, serve stale. *Caffeine `refreshAfterWrite`.*
- **Penetration** — cache negative results, Bloom filter. *Rate-limit the caller.*
- **Spring** — explicit keys, per-cache TTL, JSON serializer, no self-invocation. *`@CacheEvict` before commit is a race.*
- **Ops** — single thread: no `KEYS`, no big keys, `UNLINK`, watch `SLOWLOG`. *Separate cache and data instances.*
- **Locks** — `SET NX PX` + token, Lua release. *Efficiency only; correctness needs fencing or the DB.*
- **Cluster** — 16,384 slots, hash tags for multi-key. *Sentinel = HA, Cluster = scale.*
