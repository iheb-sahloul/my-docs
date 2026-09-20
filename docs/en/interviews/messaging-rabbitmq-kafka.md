# Messaging (RabbitMQ / Kafka)

## 🟢 Fundamentals

### Why messaging

#### Q1. Why use a message broker instead of a direct synchronous call between services?
A direct call couples the caller to the callee's availability and latency in real time — if the
callee is slow or down, the caller is blocked or fails immediately. A broker decouples them in
time and failure: the producer publishes and moves on, the consumer processes when able, and a
consumer outage doesn't take down the producer (messages simply queue up, within limits). It
also decouples *cardinality* — one event can fan out to multiple independent consumers (an
order-placed event triggering billing, shipping, and analytics) without the producer knowing or
caring who's listening.

#### Q2. When do you reach for synchronous request/response instead of async messaging?
Synchronous calls (REST/gRPC) fit when the caller genuinely needs the result *right now* to
proceed (a payment authorization the checkout flow can't continue without, a read the UI is
waiting to render) and when a temporary unavailability of the callee should be a visible failure
rather than silently queued for later. Async messaging fits when the caller doesn't need an
immediate result (fire off a "send welcome email" event and move on), when decoupling
availability matters more than instant consistency, or when fan-out to multiple independent
consumers is the actual requirement. Many real systems mix both: a synchronous call for the
critical-path decision, with async events published afterward for everything that can happen
eventually.

#### Q3. What's the difference between a queue (point-to-point) and a topic (publish/subscribe), and how do competing consumers fit in?
In a **point-to-point** queue each message is delivered to exactly *one* consumer: several
instances of the same service reading one queue are **competing consumers** that share the
workload, which is how you scale processing horizontally (10 workers draining one `emails` queue).
In **publish/subscribe** each message is delivered to *every* interested subscriber: one
`OrderPlaced` event reaches billing, shipping and analytics independently, each at its own pace.
The two are usually combined: every *logical* subscriber (billing) owns its own queue or consumer
group, and the instances *inside* that subscriber compete for its messages. In RabbitMQ that is a
`fanout` or `topic` exchange bound to one queue per subscriber, with the instances of a service
consuming from that service's queue. In Kafka it is the consumer group: consumers with the
**same** `group.id` split a topic's partitions between them (competing), while consumers with
**different** group ids each receive the full stream (pub/sub) — and parallelism is capped by the
partition count (Q11). Getting this wrong has two classic symptoms: two different services
sharing one queue/group so each sees only *half* the events, or a scaled-out service where every
instance has its own group and so processes every message N times.

### Broker models

#### Q4. Describe RabbitMQ's core model: exchange, queue, binding, routing key.
A producer never publishes directly to a queue — it publishes to an **exchange**, which routes
the message to zero or more **queues** based on **bindings** (rules connecting an exchange to a
queue) and, depending on exchange type, a **routing key**. A `direct` exchange routes to queues
whose binding key exactly matches the routing key; a `topic` exchange matches routing keys
against wildcard patterns (`orders.*.created`); a `fanout` exchange ignores the routing key
entirely and broadcasts to every bound queue. Consumers subscribe to queues, not exchanges — the
exchange/binding layer is what gives RabbitMQ flexible routing without producers needing to know
which queues exist.

#### Q5. Describe Kafka's core model: topic, partition, offset, consumer group.
A **topic** is an append-only log, split into one or more **partitions** for parallelism — each
partition is its own independently ordered, append-only sequence, and a message's position in it
is its **offset**. Producers write to a partition (chosen by a key's hash, or round-robin if no
key), and consumers read partitions sequentially, tracking their own offset (how far they've
read). A **consumer group** is a set of consumers sharing the work of a topic — Kafka assigns
each partition to exactly one consumer within a group, so a group with as many consumers as
partitions gets full parallelism, and multiple independent consumer groups can each read the
entire topic independently (unlike a RabbitMQ queue, where one message goes to one consumer,
period).

### Delivery semantics

#### Q6. What's the difference between at-most-once, at-least-once, and exactly-once delivery?
**At-most-once**: a message is delivered zero or one times — if anything fails after send, it's
simply lost, never retried (fire-and-forget). **At-least-once**: a message is guaranteed to be
delivered one or more times — failures trigger a retry/redelivery, but that means a consumer can
see the same message twice (Q13 explains why this is the overwhelmingly common real-world
default). **Exactly-once**: delivered and processed exactly one time, no duplicates, no loss —
genuinely difficult to guarantee end-to-end across a network, and where brokers claim it (Kafka's
"exactly-once semantics"), it's typically exactly-once *within* the broker's own transactional
boundary (producer → topic → consumer offset commit, all Kafka-internal), not automatically
extended to an arbitrary external side effect the consumer performs (charging a card, sending an
email) — that final side effect still needs application-level idempotency (Q13).

#### Q7. What do acknowledgements do in a message broker, and what happens to a message whose consumer crashes before acknowledging?
An acknowledgement is the consumer telling the broker "I have processed this — you may forget
it". Until it arrives, the broker keeps the message and treats it as *in flight*. If the consumer
dies, its connection drops, or it explicitly rejects (`nack`/`reject`), the broker makes the
message available again — **redelivering** it, to the same or another consumer. That is the
mechanism behind at-least-once delivery (Q6): acknowledging *after* processing means a crash
mid-way causes a duplicate, never a loss; acknowledging *before* processing (auto-ack) turns a
crash into silent message loss (at-most-once). A rejected message can be requeued, dropped or
routed to a dead-letter queue (Q22) — requeueing a message that always fails creates an endless
hot loop, which is why a retry limit matters (Q23). Kafka has no per-message ack: the equivalent
is committing the consumer group's *offset*, meaning "everything up to here is done" (Q17), so an
offset committed too early loses messages and one committed too late causes reprocessing.
Either way, redelivery is normal operation, which is why consumers must be idempotent (Q13).

## 🟡 Senior traps

### Broker comparison & retention

#### Q8. What's the core architectural difference between RabbitMQ and Kafka, and how does it drive when you'd pick each?
**Answer:** RabbitMQ is a traditional message broker: a "smart broker, simple consumer" model —
the broker owns routing (exchanges/bindings), tracks per-message delivery/acknowledgment state,
and once a message is acknowledged and consumed, it's gone from the queue for good. Kafka is a
distributed commit log: a "dumb broker, smart consumer" model — the broker just appends messages
to a partition and retains them for a configured period or size, without tracking per-consumer
delivery state beyond whatever a consumer group reports as its own offset; the same message can
be re-read by re-seeking an offset, replayed by a brand-new consumer group, or read independently
by many groups at their own pace. The architectural consequence that actually drives the choice:
RabbitMQ's model gives flexible, broker-side routing (priority queues, topic-pattern fan-out,
request/reply) at moderate throughput; Kafka's model gives very high throughput and
replay/reprocessing as a first-class capability, at the cost of any routing intelligence living
in the broker — a Kafka consumer decides what a message means and what to do with it, the broker
never inspects content.

**Example:**
```java
// RabbitMQ: the broker makes the routing decision via bindings — the publisher just picks a key.
channel.exchangeDeclare("orders", BuiltinExchangeType.TOPIC);
channel.queueBind("billing-queue", "orders", "order.created.*");
channel.basicPublish("orders", "order.created.eu", null, payload);
// The broker inspects the routing key against every binding and decides where this goes.

// Kafka: the broker does no routing at all — the producer picks the partition (via key),
// and any consumer group can independently decide to read this topic from any offset.
producer.send(new ProducerRecord<>("orders", orderId, payload)); // key -> partition hash
// Six months later, a brand-new "fraud-detection" consumer group can subscribe to "orders"
// and replay the full retained history — RabbitMQ has no equivalent once a message is acked.
```

**Why it's a trap:** "Kafka is just a faster RabbitMQ" is the wrong mental model — reaching for
Kafka on a request/reply or complex-routing problem (where RabbitMQ's broker-side intelligence is
the actual fit) or reaching for RabbitMQ on a replay/audit-log requirement (which its
consume-and-gone model can't provide) means picking the tool by reputation, not by which
architecture the requirement actually needs.

#### Q9. Kafka retention vs RabbitMQ TTL — how do the two systems' mental models around message lifetime differ?
**Answer:** Kafka retains messages for a configured period or size *regardless of consumption* —
a message stays in the log and can be re-read by re-seeking an offset, or read fresh by an
entirely new consumer group starting from the beginning, until retention expires it; consumption
doesn't delete anything. RabbitMQ's model is consumption-oriented: a message is removed from a
queue once successfully consumed and acked (that's the whole point of a traditional queue), and
TTL is purely a "give up and expire/dead-letter this if nobody consumes it within N time" safety
net, not a replay mechanism. The practical consequence: Kafka naturally supports
replay/reprocessing (rebuild a projection from the last 7 days of events) as a core capability;
RabbitMQ does not — once consumed, a message is gone, and building replay on top of RabbitMQ
means the producer or consumer has to separately persist the history itself.

**Example:**
```
# Kafka: retained for 7 days regardless of consumption; a new consumer group can start
# from the beginning and read the full 7 days of history.
retention.ms=604800000

# RabbitMQ: a safety-net expiry, not a replay mechanism — once consumed, it's gone either way.
x-message-ttl: 3600000  # 1 hour — expires (or dead-letters) if nobody consumes it in time
```

**Why it's a trap:** assuming "RabbitMQ also has a retention-like concept, so I can rebuild
history from it the way I would with Kafka" — TTL is a give-up mechanism for undelivered
messages, not a queryable history; RabbitMQ discards a message the moment it's successfully
acked, no matter how recently that happened.

### Ordering & partitioning

#### Q10. What ordering guarantees do Kafka and RabbitMQ actually provide, and what commonly breaks them?
**Answer:** Kafka guarantees order only *within a single partition* — messages with the same key
always land in the same partition and are read in the order they were written, but there's no
ordering guarantee *across* partitions. The common way ordering breaks: choosing a
low-cardinality or unrelated partition key (or no key, causing round-robin distribution) for
events that actually need per-entity ordering — e.g. "order created" and "order cancelled" for
the same order landing in different partitions gives no guarantee cancelled won't be processed
before created. RabbitMQ guarantees order within a single queue with a single consumer, but that
guarantee breaks the moment multiple consumers compete on the same queue (round-robin dispatch
means message 1 and message 2 for the same entity can be picked up and processed by different
consumers concurrently, finishing in either order) — so ordering per-entity in RabbitMQ typically
requires routing all messages for that entity to the same queue *and* a single consumer for it.

**Example:**
```java
// No key -> Kafka distributes round-robin across partitions -> no ordering relationship
// between "created" and "cancelled" for the same order at all.
producer.send(new ProducerRecord<>("orders", null, createdEvent));
producer.send(new ProducerRecord<>("orders", null, cancelledEvent));

// Keyed on order ID -> both land in the same partition, read in send order by whichever
// single consumer currently owns that partition.
producer.send(new ProducerRecord<>("orders", orderId, createdEvent));
producer.send(new ProducerRecord<>("orders", orderId, cancelledEvent));
```

**Why it's a trap:** "Kafka preserves message order" is true but incomplete — it's an easy
half-truth to repeat without the "within a partition, and only if you keyed it correctly"
qualifier, and the gap stays invisible in low-traffic testing where round-robin happens, by luck,
to keep related events close together.

#### Q11. How do you choose a Kafka topic's partition count, and what happens if you need to change it later?
**Answer:** Partition count sets the ceiling on consumer parallelism within a group (more
partitions than consumers means some consumers handle multiple partitions; more consumers than
partitions means some consumers sit idle) — so choose based on target throughput and expected
consumer group size, with headroom for future scaling, since partitions can be *increased* later
but existing consumers won't automatically rebalance to make full use of them without a
restart/rebalance trigger, and more importantly: increasing partition count changes the key →
partition hash mapping for *new* messages, breaking the guarantee that all messages for a given
key continue landing in the same partition as before — anything relying on partition-level
ordering for a key (Q10) needs to account for this discontinuity at the moment of repartitioning.
Partition count cannot be *decreased* at all in Kafka without recreating the topic entirely.

**Example:**
```
$ kafka-topics.sh --alter --topic orders --partitions 12 --bootstrap-server broker:9092
# New messages for a given key now hash into 1 of 12 partitions instead of 1 of 6 — a key
# that always landed in partition 3 before may now land in partition 9, while its older
# history stays in partition 3. Any consumer relying on "this key's history is all in one
# partition" breaks silently from this point forward.
```

**Why it's a trap:** "we can always just add more partitions later if we under-provision" is only
half true — you can add them, but doing so silently changes the key→partition mapping for new
messages, a real and easy-to-miss correctness risk for any ordering-dependent consumer, not a
free scaling lever.

#### Q12. What challenges come up with message priority or fairness across many queues/topics?
**Answer:** RabbitMQ supports explicit priority queues (a priority field per message, with the
broker generally delivering higher-priority messages first) — but priority queues add real broker
overhead and don't guarantee strict ordering under load, only a bias toward higher priority.
Kafka has no built-in priority concept at all — a common workaround is separate topics per
priority tier, with consumers polling the high-priority topic more aggressively (or dedicating
separate consumer capacity to it) rather than relying on any in-broker prioritization. The
fairness challenge across many queues/topics for the *same* underlying resource (e.g. one
downstream API rate limit shared by consumers of five different topics) is a genuinely hard
problem brokers don't solve for you — it typically needs an application-level rate limiter or
token-bucket shared across those consumers, independent of the messaging layer.

**Example:**
```java
// Kafka has no native priority — the common workaround is separate topics per tier,
// with consumer capacity biased toward the high-priority topic.
while (true) {
    pollAndProcess(highPriorityConsumer, Duration.ofMillis(100));
    pollAndProcess(highPriorityConsumer, Duration.ofMillis(100)); // polled twice as often
    pollAndProcess(lowPriorityConsumer, Duration.ofMillis(100));
}
```

**Why it's a trap:** assuming RabbitMQ's priority queues give a strict ordering guarantee the way
a sorted list would — they only bias delivery toward higher-priority messages under load, they
don't guarantee a lower-priority message never jumps ahead, so building logic that depends on
strict priority ordering on top of them is building on a guarantee that was never actually made.

### Delivery guarantees & idempotency

#### Q13. Why must a consumer be idempotent even when the messaging system claims "exactly-once" or "at-least-once with dedup"?
**Answer:** Because the boundary the broker can guarantee (message delivered to the consumer,
offset committed) is not the same boundary as the consumer's actual side effect (a database
write, an email sent, a card charged) — a crash between "processed the message" and "committed
that it was processed" is exactly what forces redelivery under at-least-once semantics, and
there is no way to distinguish that from a genuine duplicate message without the consumer itself
tracking what it's already done. Idempotency has to live in the consumer's own logic (or its data
model) because it's the only place that actually knows both "did I do this side effect" and "did
I receive this message" at the same time.

**Example:**
```java
void handle(Message msg) {
    chargeCard(msg.orderId(), msg.amount()); // side effect completes...
    // ...crash right here, before the offset commit below ever runs...
    consumer.commitSync();
}
// On restart, the broker redelivers this exact message (at-least-once), and chargeCard()
// runs a second time — the broker kept every promise it made; the duplicate charge is
// entirely the consumer's responsibility to have prevented.
```

**Why it's a trap:** hearing "our broker supports exactly-once" or "the client library dedups"
and concluding the consumer doesn't need its own idempotency is the trap — that guarantee, where
it exists, covers broker-internal bookkeeping (offsets, transactional writes to another Kafka
topic), not an arbitrary external side effect like a card charge that lives entirely outside the
broker's own transaction boundary.

#### Q14. What are the common idempotency strategies for a message consumer?
**Answer:** (1) A unique business key (order ID, idempotency key from the producer) enforced as a
database unique constraint on the table the side effect writes to — a duplicate processing
attempt hits the constraint and is treated as a no-op, not an error, which is the most robust
approach because the database itself serializes concurrent duplicate attempts. (2) A
processed-messages log/table keyed by message ID, checked before processing and written
atomically with the side effect in the same transaction — works for side effects that don't
naturally have a unique key of their own. (3) Natural idempotency in the operation itself where
possible (`SET status = 'shipped'` is idempotent regardless of how many times it runs;
`increment counter by 1` is not) — designing the operation to be idempotent by construction is
cheaper than detecting duplicates when it's achievable.

**Example:**
```sql
-- Fragile: check-then-insert is two statements, not one — two redelivered copies of the same
-- message, processed concurrently by two consumer threads, can both pass the SELECT before
-- either INSERT commits.
SELECT 1 FROM processed_payments WHERE payment_id = ?;   -- both see "not found"
INSERT INTO processed_payments (payment_id) VALUES (?);  -- both then insert -> race, or a
                                                          -- unique-constraint error one of
                                                          -- them didn't expect to handle

-- Robust: let the database's own unique constraint be the single atomic decision point.
INSERT INTO processed_payments (payment_id) VALUES (?)
ON CONFLICT (payment_id) DO NOTHING; -- second attempt safely no-ops, no race window at all
```

**Why it's a trap:** "check if it's already processed, then process it" sounds idempotent but is
a classic time-of-check-to-time-of-use bug under concurrent redelivery — the unique-constraint
approach is preferred specifically because it makes the database the single atomic arbiter
instead of relying on two separate round-trips never overlapping.

#### Q15. What do Kafka transactions and RabbitMQ publisher confirms each actually guarantee?
**Answer:** Kafka transactions let a producer atomically write to multiple partitions/topics
*and* atomically commit a consumer's offset alongside a produced output — this is what backs
Kafka's "exactly-once" claim for a read-process-write pipeline (consume from topic A, produce to
topic B, commit offset — all atomic together), but again, only within Kafka's own boundary (Q6).
Publisher confirms in RabbitMQ are a simpler, narrower guarantee: an async acknowledgment from
the broker that a published message has been safely received and persisted (for a durable queue)
— it tells the producer "the broker has it," not anything about downstream consumer processing;
without confirms, a publish can be lost between the client and broker with the producer having no
idea it failed. The common trap: treating publisher confirms as an end-to-end delivery guarantee
when they only cover producer→broker, not broker→consumer→successful processing.

**Example:**
```java
// Kafka transactional producer — atomic across produce + offset commit.
producer.initTransactions();
producer.beginTransaction();
producer.send(outputRecord);
producer.sendOffsetsToTransaction(offsets, consumerGroupId);
producer.commitTransaction(); // all-or-nothing, including the consumer's own offset advance

// RabbitMQ publisher confirms — narrower: only "the broker durably has this message."
channel.confirmSelect();
channel.basicPublish(exchange, routingKey, props, body);
channel.waitForConfirmsOrDie(5000); // says nothing about whether any consumer ever saw it
```

**Why it's a trap:** treating "the broker confirmed my publish" as "the message was fully
handled end-to-end" — both mechanisms stop at the broker's own boundary; what a consumer does
with the message afterward is outside either guarantee entirely.

#### Q16. Which producer and broker settings decide whether a Kafka message survives a broker failure?
**Answer:** Durability is the combination of four settings, and it is only as strong as the
weakest one. **`acks`** says when the producer considers a write done: `0` = fire and forget,
`1` = the partition leader wrote it (lost if the leader dies before followers replicate — the
message was acknowledged yet vanishes), `all` = the leader *and* every in-sync replica wrote it.
**`min.insync.replicas`** (topic/broker) is the floor for "all": with the default of 1, `acks=all`
can degrade to a single copy if the ISR shrinks to just the leader, so the standard
production setting is replication factor 3, `min.insync.replicas=2` — tolerating one broker loss
without losing data or availability, while a second loss makes producers get
`NotEnoughReplicasException` (the system deliberately chooses consistency over availability,
the CAP trade-off in practice). **`unclean.leader.election.enable=false`** (the default) forbids
promoting an out-of-sync replica to leader; enabling it restores availability after a
double failure but *silently discards* the records that replica hadn't yet copied.
**`enable.idempotence=true`** (default since Kafka 3.0) makes producer retries safe: the broker
de-duplicates by producer id + sequence number, so a retry after a timeout does not write the
record twice and — with `max.in.flight.requests.per.connection <= 5` — doesn't reorder it either.
Set a bounded `delivery.timeout.ms` so `send()` eventually fails visibly instead of retrying
forever, and *check the result* (callback / `Future`), because a fire-and-forget `send()` that
fails is otherwise invisible. Note the limits: idempotence covers one producer session on one
partition; it is not end-to-end exactly-once (Q15, Q28), and durability on the broker side still
depends on the OS flush/replication model, not on `fsync` per message.

**Example:**
```properties
# producer
acks=all
enable.idempotence=true
delivery.timeout.ms=120000
max.in.flight.requests.per.connection=5

# topic (created with)  --replication-factor 3
min.insync.replicas=2
unclean.leader.election.enable=false
```
```java
producer.send(record, (metadata, ex) -> {
    if (ex != null) failureMetrics.increment();   // never ignore the callback
});
```

**Why it's a trap:** "we use Kafka, it's replicated" is not an answer. With `acks=1` a
leader crash loses acknowledged data, and with `min.insync.replicas=1` `acks=all` is a
placebo — both look fine on every happy-path test and only fail during a real broker outage.

### Consumers, offsets & rebalancing

#### Q17. Auto-commit vs manual offset commit in a Kafka consumer — what's the trade-off?
**Answer:** Auto-commit periodically commits the latest consumed offset on a timer, regardless of
whether the message was actually fully processed — simple, but it can commit an offset for a
message that's still being processed (or that failed) right before a crash, silently skipping it
on restart (data loss, violating at-least-once). Manual commit, done *after* the message's side
effect has genuinely completed successfully, gives at-least-once semantics correctly — the
offset only advances once the work is done, so a crash before that point causes redelivery
(handled by idempotency, Q13/Q14) rather than silent loss. The senior-level default: manual commit
after successful processing for anything where losing a message silently is unacceptable, which
is most production use cases — auto-commit's simplicity is rarely worth its data-loss window.

**Example:**
```java
// Auto-commit: offset advances on a timer, independent of whether processing succeeded.
props.put("enable.auto.commit", "true");
props.put("auto.commit.interval.ms", "5000");
// A crash 4 seconds after a message was polled but never actually processed can still have
// had that offset committed moments before — the message is silently skipped forever.

// Manual: offset only advances after the side effect genuinely completed.
props.put("enable.auto.commit", "false");
process(record);
consumer.commitSync(); // a crash before this line causes redelivery, not silent loss
```

**Why it's a trap:** auto-commit "just working" in every demo and low-throughput staging test is
exactly why it survives into production — the failure window is a race against a crash at a very
specific moment, rare enough to never surface until real production volume and real
infrastructure churn make it inevitable.

#### Q18. How do RabbitMQ acknowledgments and prefetch count interact, and why does prefetch matter?
**Answer:** A consumer acks a message once it's done processing it; an unacked message that the
consumer disconnects on (or explicitly nacks) gets requeued for redelivery — this is RabbitMQ's
at-least-once mechanism. **Prefetch count** limits how many unacknowledged messages the broker
will push to a consumer at once, before waiting for acks — a prefetch of 1 means strictly
one-at-a-time (safest, but serializes processing per consumer and can waste throughput on fast
consumers); a very high or unbounded prefetch lets the broker hand one consumer a large batch of
messages, which can starve other consumers on the same queue of work (they sit idle while one
consumer hoards a backlog) and, if that consumer crashes, requeues a large batch at once,
potentially causing a thundering-herd reprocessing spike. The practical answer: set prefetch to
match how many messages a single consumer can meaningfully process concurrently, not "as high as
possible for throughput."

**Example:**
```java
channel.basicQos(1); // strict one-at-a-time — safest, but caps this consumer's own throughput

// vs.
channel.basicQos(0); // unbounded — the broker may hand this single consumer a huge batch,
// starving every other consumer on the queue and risking a large redelivery spike on crash
```

**Why it's a trap:** assuming "higher prefetch = higher throughput" is a universal free win —
unbounded prefetch actively harms fairness across a consumer pool and turns a single consumer
crash into a large thundering-herd requeue, so it should be sized to actual per-consumer
concurrent capacity, not maximized by default.

#### Q19. What happens during a Kafka consumer group rebalance, and why can it cause duplicate processing?
**Answer:** A rebalance reassigns partitions across the consumers in a group — triggered by a
consumer joining, leaving (including a perceived failure from a missed heartbeat), or a partition
count change. During a rebalance, consumption pauses while partitions are reassigned, and
critically: a consumer that was mid-processing a batch of messages when the rebalance started,
and hadn't yet committed its offset for that batch, will have that same partition (and those
same uncommitted messages) handed to a different consumer — which then reprocesses them from the
last *committed* offset, duplicating whatever the first consumer already did before the rebalance
interrupted it. This is exactly why consumers need idempotency (Q13) regardless of how careful the
offset-commit strategy is — rebalances make at-least-once redelivery a routine occurrence, not an
edge case.

**Example:**
```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> r : records) {
        process(r); // if a rebalance fires here, partway through this batch...
    }
    consumer.commitSync(); // ...this line never runs for the already-processed records
}
// The reassigned consumer resumes from the last *committed* offset, reprocessing everything
// this instance already handled since its previous successful commitSync().
```

**Why it's a trap:** treating a rebalance as a rare edge case worth ignoring — in reality, any
deploy, autoscaling event, or missed heartbeat triggers one, making duplicate redelivery a
routine occurrence that idempotency (Q13/Q14) must handle unconditionally, not a tail risk to
shrug off.

#### Q20. Why can a *slow* Kafka consumer — not a crashed one — trigger endless rebalances, and which settings control it?
**Answer:** A consumer must call `poll()` again within **`max.poll.interval.ms`** (default 5
minutes); heartbeats are sent by a *separate background thread* (governed by
`session.timeout.ms` and `heartbeat.interval.ms`), so a consumer can look perfectly healthy to the
broker while its processing loop is stuck. If the time between two `poll()` calls exceeds the
interval — because a batch of `max.poll.records` (default 500) records each takes a few
seconds, or one call hangs on a downstream service — the consumer is considered failed, removed
from the group and its partitions reassigned (Q19). When it finally finishes, its offset commit
fails with `CommitFailedException`, the batch is redelivered to the new owner, *that* consumer is
just as slow, gets kicked in turn, and the group enters a **rebalance loop**: consumption
stalls, lag grows, and duplicates multiply. Fixes, in order: shrink the batch
(`max.poll.records`) so one poll's work fits comfortably inside the interval; set timeouts on
every downstream call so nothing can hang; raise `max.poll.interval.ms` only as a last resort
(it slows detection of a really stuck consumer); use `pause()`/`resume()` or hand records to a
worker pool while continuing to poll (carefully committing only completed offsets); and reduce the
*cost* of each rebalance with the `CooperativeStickyAssignor` (incremental, no stop-the-world)
and static membership (`group.instance.id`) so a rolling restart doesn't reshuffle everything.

**Example:**
```properties
max.poll.records=50                 # 50 records * ~2s each = ~100s, well under the interval
max.poll.interval.ms=300000
session.timeout.ms=45000
heartbeat.interval.ms=15000
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```
```java
// Bad: 500 records x 3s each = 1500s between polls -> the consumer is evicted every time.
for (ConsumerRecord<String, Order> r : consumer.poll(Duration.ofSeconds(1))) {
    slowRemoteCall(r.value());
}
```

**Why it's a trap:** heartbeats keep working, so dashboards say the consumer is "alive" while it
is being repeatedly evicted; and the standard reflex — bump `max.poll.interval.ms` — only hides
the slow handler until load rises.

#### Q21. What happens when a consumer can't keep up with the rate messages arrive, and how do you handle it?
**Answer:** Backlog builds — in Kafka, consumer lag (the gap between the latest offset and the
consumer's committed offset) grows; in RabbitMQ, queue depth grows, and past a configured
memory/disk threshold, RabbitMQ can trigger a flow-control alarm that blocks publishers entirely
(a protective measure that turns a slow-consumer problem into a producer-blocking problem if left
unaddressed). Handling it: scale consumers horizontally (more consumers up to the partition
count in Kafka, or more consumers on the same RabbitMQ queue), ensure the actual per-message
processing time is the bottleneck being addressed rather than just adding consumers on top of a
slow downstream call, or apply backpressure deliberately — RabbitMQ's prefetch (Q18) is itself a
backpressure mechanism, limiting how much a broker will push ahead of a consumer's actual
processing rate.

**Example:**
```
$ kafka-consumer-groups.sh --bootstrap-server broker:9092 --describe --group billing-group
TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
orders  0          482910          511200          28290
orders  1          483012          511344          28332
```

**Why it's a trap:** reflexively adding more consumers without first checking whether partition
count is already the ceiling (Q11) or whether per-message processing time itself regressed —
throwing more consumers at a problem that's actually partition-bound or latency-bound changes
nothing.

### Failure handling

#### Q22. What is a dead-letter queue, and why does a production system need one?
**Answer:** A dead-letter queue (DLQ) is where messages go after they've failed processing beyond
a configured retry limit, or expired, or were explicitly rejected without requeue — instead of
being retried forever (blocking the queue behind a message that can never succeed, Q23) or
silently discarded (losing the event with no trace). It exists so a "poison pill" message doesn't
stall processing of every message behind it, while still preserving the failed message for
investigation, manual reprocessing, or alerting, rather than the two bad alternatives of infinite
retry or silent loss.

**Example:**
```java
Map<String, Object> args = new HashMap<>();
args.put("x-dead-letter-exchange", "dlx");
args.put("x-dead-letter-routing-key", "orders.dead");
args.put("x-max-length", 100_000); // optional additional safety net
channel.queueDeclare("orders-queue", true, false, false, args);
// Once a consumer nacks the same message beyond a tracked retry count, route it to "dlx"
// instead of requeueing to "orders-queue" yet again.
```

**Why it's a trap:** treating "we configured a DLQ" as the finished task — a DLQ with retry
routing but no consumer or alert watching it is just a slower, quieter version of the exact data
loss it was built to prevent (S9).

#### Q23. What is a "poison pill" message, and how do you handle one without stalling the whole queue?
**Answer:** A poison pill is a message that can never be successfully processed — malformed data,
a bug triggered by that specific payload, a reference to an entity that was since deleted — so
every redelivery attempt fails identically and, without a limit, it retries forever. On RabbitMQ,
an unlimited requeue-on-nack loop means that message (and, if ordering/prefetch keeps it at the
front, everything behind it) never makes progress. The fix: configure a maximum delivery/retry
count (RabbitMQ's `x-death` header tracking, or an application-level retry counter), and once
exceeded, route the message to a dead-letter queue (Q22) instead of requeueing again — this lets
processing continue past the poison pill while preserving it for investigation.

**Example:**
```java
int deathCount = getXDeathCount(delivery); // reads RabbitMQ's x-death header count
if (deathCount >= MAX_RETRIES) {
    channel.basicPublish("dlx", "orders.dead", null, delivery.getBody()); // manual dead-letter
    channel.basicAck(deliveryTag, false); // ack the original so it doesn't requeue again
} else {
    channel.basicNack(deliveryTag, false, true); // requeue for another attempt
}
```

**Why it's a trap:** "just nack and requeue on any failure" is the default reflex, and it's
correct for a transient failure (a downstream timeout) but catastrophic for a poison pill —
without a bounded count it's indistinguishable from an infinite retry loop that never lets the
queue drain.

#### Q24. How do you design retries with backoff for a Kafka (or RabbitMQ) consumer without blocking the stream?
**Answer:** Retrying *in place* is the simplest option and it is fine for a short, transient
blip: sleep and retry the same record a few times. But in Kafka a partition is a strict sequence,
so an in-place retry **blocks everything behind it** — one failing record with a 10-minute backoff
stalls the whole partition (head-of-line blocking), and long sleeps also risk the
`max.poll.interval.ms` eviction from Q20. **Non-blocking retries** move the failed record
elsewhere and let the main topic continue: publish it to a chain of *retry topics* with
increasing delays (`orders-retry-5s`, `orders-retry-1m`, `orders-retry-10m`) whose consumers wait
until the record's timestamp plus the delay, and after the final attempt send it to a
dead-letter topic (Q22). RabbitMQ does the same with a per-queue TTL and a dead-letter exchange
that routes expired messages back to the work exchange (a delay queue) — or the delayed-message
plugin. The costs: **ordering is no longer preserved** for the retried record (later messages for
the same key overtake it), so it is only acceptable when handlers are order-independent or
version-checked; there are more topics/queues to operate; and headers need an attempt counter.
Whichever mechanism, the policy matters more than the plumbing: retry only **transient** errors
(timeouts, 503s) and send **permanent** ones (validation failure, poison pill, Q23) straight to the
DLT; use **exponential backoff with jitter** so many consumers don't retry in lockstep (S17);
cap attempts; and keep handlers idempotent (Q13) since every retry is a potential duplicate.

**Example:**
```java
@RetryableTopic(
    attempts = "4",
    backoff = @Backoff(delay = 5_000, multiplier = 3.0, random = true),   // ~5s, ~15s, ~45s + jitter
    include = TransientDownstreamException.class,                         // only retry transient errors
    dltStrategy = DltStrategy.FAIL_ON_ERROR)
@KafkaListener(topics = "orders", groupId = "billing")
void handle(OrderEvent event) { billing.charge(event); }

@DltHandler
void deadLetter(OrderEvent event) { alerts.page("order " + event.id() + " exhausted retries"); }
```

**Why it's a trap:** "just retry 3 times" sounds complete. The follow-ups are head-of-line
blocking, lost ordering, retrying non-retryable errors forever, and the synchronized retry storm
that turns a small outage into a large one.

### Patterns & schemas

#### Q25. Saga pattern — orchestration vs choreography — what's the actual difference and trade-off?
**Answer:** Both handle a distributed transaction across services without a two-phase-commit
(which doesn't scale across independently-owned services) by breaking it into a sequence of
local transactions, each with a corresponding compensating transaction to undo it if a later step
fails. **Orchestration**: a central coordinator explicitly calls each step in sequence and
explicitly calls the compensations in reverse order on failure — the flow is easy to see in one
place (readable, debuggable, testable as a unit) but introduces a central component that needs to
know about every participant, a potential single point of coordination logic to maintain.
**Choreography**: each service reacts to events from the previous step and emits its own event
for the next, with no central coordinator — fully decoupled, no single service knows the whole
flow, but that's also the weakness: understanding or debugging the end-to-end flow means tracing
events across every service's logs, and there's no single place that "owns" retry/compensation
logic for the whole saga. Orchestration tends to win as the number of steps and the need for
visibility grows; choreography tends to win for simpler, more loosely-coupled flows.

**Example:**
```java
// Orchestration: one place makes every decision and knows the whole flow.
try {
    paymentClient.authorize(orderId);
    inventoryClient.reserve(orderId);
    shippingClient.schedule(orderId);
} catch (InventoryUnavailableException e) {
    paymentClient.voidAuthorization(orderId); // explicit compensation, in reverse order
    orderService.markFailed(orderId);
}
// Choreography: no such block exists anywhere — each service reacts to the previous
// service's event and emits its own; tracing this same failure means reading logs across
// three separate services, with no single place showing the whole sequence.
```

**Why it's a trap:** "choreography is more decoupled so it's always the better architecture"
ignores that decoupling has a real cost — debuggability — a senior answer picks based on flow
complexity and the team's actual need for centralized visibility, not decoupling as an
unconditional virtue.

#### Q26. What is the outbox pattern, and what problem does it solve?
**Answer:** The problem: a service that needs to both write to its own database *and* publish an
event about that write (e.g. save an order, then publish `OrderCreated`) can't do both atomically
as two separate operations — a crash between the DB commit and the message publish leaves the
database updated but the event never sent (or, in the other order, an event published for a DB
write that then failed to commit), and neither database transactions nor message broker
transactions span across both systems by default. The outbox pattern solves it by writing the
event to an "outbox" table in the *same* database transaction as the business write — atomicity
is guaranteed because it's one transaction in one database — and a separate process (a polling
job, or Debezium-style change-data-capture reading the database's write-ahead log) reads new
outbox rows and actually publishes them to the broker, marking them sent. This gives
effectively-exactly-once event publication tied to the business write, at the cost of a small
publish delay and the extra outbox table/relay infrastructure.

**Example:**
```sql
BEGIN;
INSERT INTO orders (id, status) VALUES ('123', 'created');
INSERT INTO outbox (id, topic, payload, published)
    VALUES (gen_random_uuid(), 'orders', '{"orderId":"123"}', false);
COMMIT;
-- A separate relay process polls `WHERE published = false`, publishes to the broker, then
-- marks the row published — the business write and the "intent to publish" can never
-- diverge, because they committed as one atomic unit.
```

**Why it's a trap:** "solving" the dual-write problem by publishing the event first and writing
to the database second (or vice versa) with a try/catch around whichever call comes second only
moves *which direction* the failure can happen in — it doesn't remove the fundamental
non-atomicity; only writing both inside one database transaction actually closes the gap.

#### Q27. Why does schema evolution matter for messages, and what tools address it?
**Answer:** A producer and its consumers are independently deployed services — a producer adding
a required field, renaming a field, or changing a type can silently break every consumer that
deserializes the message the old way, and unlike a synchronous API where a client would get an
immediate error on the next call, a broken message schema can sit in the topic/queue failing
every consumer retroactively, or worse, deserializing incorrectly without erroring at all. Schema
registries (Confluent Schema Registry with Avro or Protobuf being the common Kafka pairing)
enforce compatibility rules at publish time — a producer can't publish a schema-incompatible
message without an explicit compatibility mode change — and support safe evolution patterns
(adding an optional field with a default is safe; removing or renaming a required field is not,
without a transition period). Even without a formal schema registry, the discipline it enforces
(backward-compatible-only changes, new fields optional with defaults, never repurpose a field) is
worth applying manually with plain JSON.

**Example:**
```json
// Backward-compatible: new field is optional with a default — old consumers reading new
// messages simply don't see it; new consumers reading old messages get the default.
{"name": "promoCode", "type": ["null", "string"], "default": null}

// Breaking: removing a required field with no default — every consumer still expecting it
// throws a deserialization error on the very next message, silently, in production.
```

**Why it's a trap:** "we'll just tell every consumer team about the change" doesn't scale —
consumers deploy independently and on their own schedule, so a compatibility rule enforced
mechanically (a schema registry rejecting an incompatible schema at publish time) is the only
version of this that doesn't eventually rely on someone remembering a Slack message.

## 🔴 Expert / Open

### Delivery guarantees

#### Q28. Design an exactly-once-processing payment consumer on Kafka. Walk through the full approach.
Start from the premise that "exactly-once" for the actual side effect (charging a card, crediting
a balance) has to be engineered at the application layer, not assumed from the broker (Q6/Q13).
Concretely: the consumer reads a payment-request message, and within a single database
transaction, (1) checks a unique constraint on the message's idempotency key (the payment
request ID) against a `processed_payments` table — if it already exists, the transaction
short-circuits as a no-op, safely handling redelivery from a rebalance or retry; (2) if new,
performs the actual balance/ledger update; (3) inserts the idempotency-key row; all as one atomic
database transaction, so a crash at any point either fully commits all three or none of them.
Only *after* that transaction commits does the consumer commit its Kafka offset (manual commit,
Q17) — so a crash between the DB commit and the offset commit causes redelivery, which is safely
absorbed by step (1)'s uniqueness check on replay. This gets you effectively-exactly-once
processing of the business side effect, built from an at-least-once delivery guarantee plus an
idempotent, transactionally-safe consumer — which is the general pattern, not something specific
to payments.

### Workflows & event design

#### Q29. Design a saga for order → payment → inventory reservation → shipping. Choose orchestration or choreography and explain the compensations.
Orchestration is the stronger fit here specifically because the flow has a clear linear
dependency chain and failure at any step has a well-defined, specific undo — exactly the case
where a central coordinator's visibility earns its cost. Flow: the orchestrator creates the order
(pending), calls payment to authorize (local transaction, compensatable by a refund/void), calls
inventory to reserve stock (compensatable by releasing the reservation), then calls shipping to
schedule dispatch (compensatable by cancelling the shipment) — and finally marks the order
confirmed. On failure at any step, the orchestrator invokes the compensating transactions for
every step that already succeeded, in reverse order: if inventory reservation fails (out of
stock), it triggers a payment void/refund and marks the order failed, without ever calling
shipping. The trickiest design point is that compensations must themselves be safe to retry and
idempotent (a refund call that times out and gets retried shouldn't refund twice) — the saga
pattern doesn't remove the need for idempotency, it just adds a coordination layer on top of
services that still individually need it (Q13 applies to every step and every compensation).

#### Q30. Compare dual writes, a polling outbox and log-based CDC (Debezium) for publishing events reliably. When do you use which?
A **dual write** — commit to the database, then publish to the broker in the same method — is
the anti-pattern the outbox exists to prevent (Q26): a crash or broker outage between the two
steps loses the event or publishes one for a rolled-back write, and no retry logic can tell which
happened. The **polling outbox** writes the event to an `outbox` table in the business
transaction and a relay polls unpublished rows: simple, needs no extra infrastructure, and easy
to reason about; its costs are polling latency and load, concurrency between several relay
instances (use `FOR UPDATE SKIP LOCKED`, module 3 Q17), keeping ordering per aggregate,
deleting published rows, and at-least-once publication (a crash between publish and "mark sent"
duplicates). **Log-based CDC** — Debezium reading PostgreSQL's WAL via a logical replication
slot, ideally with the outbox event router — removes polling: events are captured in commit order
with low latency and no extra query load, and the same mechanism can also stream ordinary table
changes to other systems. Its costs are operational: a Kafka Connect deployment to run and monitor,
a dependency on database configuration (`wal_level=logical`, permissions), snapshotting and
schema-change handling, and above all the **replication slot**: if the connector is down or
slow, PostgreSQL retains WAL for the slot *indefinitely* and can fill the database disk (S22),
so `max_slot_wal_keep_size`, lag alerts and a tested "connector down" runbook are mandatory. In
every variant delivery is at-least-once, so consumers stay idempotent (Q13). My rule: start with
the polling outbox for modest volume and few services; move to Debezium when polling load or
latency becomes the bottleneck, or when many downstream systems need change streams — and never
publish directly from business code.

#### Q31. Should an event carry the data, or only say something happened? Compare notification events, event-carried state transfer and event sourcing.
These three are different contracts, and confusing them is a frequent source of coupling. A
**notification event** is thin — `{"orderId": 123, "type": "OrderPlaced"}` — and consumers call
back to the owning service for details. It keeps events small and the owner authoritative, but
recreates *runtime coupling* (the consumer needs the producer up, adds load, and may read newer
state than the event described). **Event-carried state transfer** puts the data the consumers need
into the event (or publishes the entity's full new state, ideal for a compacted topic), so
consumers build their own local read models and never call back: services stay autonomous and fast
and survive the producer's outage, at the price of larger events, a schema that becomes a public
contract (Q27), duplicated data that is *eventually* consistent, and the risk of
leaking fields consumers shouldn't have. **Event sourcing** is a different idea altogether: the
events *are* the source of truth in the owning service — current state is a fold over the
append-only log of `OrderPlaced`, `ItemAdded`, `OrderCancelled` — giving a complete audit trail,
time travel and the ability to rebuild any projection, but demanding real investment in event
versioning/upcasting, snapshots for long streams, projections and CQRS, and "delete" (GDPR)
becomes hard because the log is immutable. They are not a ladder you climb: most systems want
event-carried state transfer between services and ordinary CRUD (plus an outbox, Q26) inside them;
notification events fit when payloads are large or sensitive; event sourcing fits domains where
the history *is* the product (ledgers, bookings, trading). I'd choose per boundary, and
explicitly name the consistency each consumer can tolerate.

### Platform decisions

#### Q32. When is migrating from RabbitMQ to Kafka actually justified, and what does that migration cost?
Justified when the driving need has become one of: replay/reprocessing capability that RabbitMQ
structurally can't provide (Q9); throughput has outgrown what RabbitMQ's per-message broker
bookkeeping handles well; or multiple independent consumer groups genuinely need to read the same
event stream at their own pace and retention, rather than one message going to one consumer. Not
justified by "Kafka is more popular/scalable" in the abstract — if the actual usage is simple
task queues, request/reply, or moderate-throughput routing with complex exchange logic, RabbitMQ
remains a better architectural fit and a wholesale migration adds real cost for no corresponding
benefit. The migration itself costs more than swapping a client library: consumers built around
RabbitMQ's ack-and-gone model need to be redesigned around offset management and idempotent
reprocessing (Q13) as a first-class concern, partition/key design needs to be chosen deliberately
for ordering needs (Q10), and the operational model (Kafka's own cluster/ZooKeeper-or-KRaft
management, partition rebalancing) is a genuinely different operational burden — this is a
multi-quarter architectural change for a system of any real size, not a drop-in replacement, and
should be scoped and justified as such rather than done because Kafka is the trendier choice.

#### Q33. How would you replicate Kafka data across regions, and what do you have to give up?
Kafka clusters are designed to live inside one region (low-latency links between brokers), so
cross-region is done by a **replicator** that consumes from cluster A and produces to cluster B:
MirrorMaker 2 (built on Kafka Connect), Confluent Cluster Linking or equivalents. The main design
choice is topology. **Active-passive**: region A serves traffic, B holds a copy and takes over on
disaster — simple to reason about, but replication is *asynchronous*, so the recovery point (RPO,
module 7 Q21) is whatever hadn't been mirrored yet, and failing over means re-pointing producers
and consumers and choosing where consumers resume, since offsets in B are *not* the same numbers
as in A (MM2 translates committed offsets, imperfectly; the safe assumption is "resume slightly
earlier and de-duplicate", i.e. idempotent consumers, Q13). **Active-active**: each region
produces locally and mirrors to the other, with topics prefixed by origin (`us.orders`,
`eu.orders`) to avoid replication loops; latency is excellent, but the same entity can now be
updated in two regions at once, so you need a conflict strategy (partition ownership by
entity/region key, last-writer-wins by version, or CRDT-style merge) — the CAP trade-off (module
7 Q8) applied to your event stream. **Stretch cluster** (one cluster across 3 regions, `acks=all`
with rack awareness) gives zero RPO at the price of cross-region latency on *every* write and
a hard requirement of low, stable inter-region RTT — appropriate for a payments core, not for
high-volume telemetry. Also decide what to replicate (not every topic deserves it), how to keep
schemas and ACLs in sync, and rehearse the failover: an untested runbook is not a DR plan. My
default: active-passive with idempotent consumers and a scheduled failover drill; active-active
only when the business genuinely needs local writes in both regions and can define entity
ownership.

## 🎯 Real-world scenarios

### S1. A customer is charged twice for the same order
- **Symptoms:** A payment-processing consumer occasionally processes the same order-placed
  message twice, resulting in a duplicate charge, reported by customers or caught by
  reconciliation.
- **Diagnosis:** Check whether the payment consumer is idempotent (Q13/Q14) — the most common root
  cause is a consumer that processes the side effect and *then* commits the offset, but crashes
  or times out in between, causing redelivery that the consumer has no way to recognize as a
  duplicate.
- **Example:**
  ```java
  // The bug pattern this incident traces back to:
  chargeCard(order.customerId(), order.amount()); // completes — the customer is charged
  consumer.commitSync();                          // crash right here, before this line runs
  // Restart redelivers the same message; chargeCard() runs again with nothing recognizing
  // it as a duplicate.
  ```
- **Resolution:** Add a unique constraint on the payment/order idempotency key at the database
  level, so a duplicate processing attempt is rejected or safely no-ops instead of charging
  again; issue refunds for any customers already double-charged by this gap.
- **Prevention:** Treat idempotency as a required design element for any consumer with an
  external, hard-to-undo side effect (charging money, sending an irreversible notification) — not
  an optional hardening step added after an incident.

### S2. Messages pile up in a queue and stop being processed entirely
- **Symptoms:** Queue depth grows steadily; consumers are running and appear healthy, but
  throughput has dropped to zero or near-zero.
- **Diagnosis:** Check whether the message at the head of the queue is a poison pill (Q23) — a
  malformed or bug-triggering message that fails every time, and without a retry limit, gets
  redelivered and re-fails in a loop, blocking progress on everything behind it if ordering or
  prefetch keeps it at the front.
- **Example:**
  ```
  $ rabbitmqctl list_queues name messages messages_unacknowledged
  orders-queue   48213   1
  ```
  A queue depth growing steadily while `messages_unacknowledged` stays pinned at exactly `1` is
  the signature of one message being redelivered and re-failed in a loop, never draining, while
  everything behind it waits.
- **Resolution:** Manually identify and remove/reroute the specific stuck message to unblock the
  queue immediately, then add a maximum retry count with dead-lettering so this can't recur
  silently.
- **Prevention:** Every consumer needs a bounded retry count and a DLQ target configured from the
  start — "retry forever" should never be the default behavior for message processing.

### S3. Kafka consumer lag grows steadily and doesn't recover even during low-traffic periods
- **Symptoms:** The gap between the latest produced offset and the consumer group's committed
  offset keeps widening over days, including during periods when message production volume is
  normal or even low.
- **Diagnosis:** This means processing throughput is structurally below production rate, not a
  temporary spike — check whether the consumer count matches the partition count (more
  consumers can't help if partitions are the bottleneck, Q11), whether each message's processing
  time has regressed (a slow downstream call added to the consumer's hot path), or whether a
  rebalance loop (Q19, possibly from consumers frequently restarting) is repeatedly interrupting
  progress.
- **Example:**
  ```
  $ kafka-consumer-groups.sh --describe --group billing-group --bootstrap-server broker:9092
  TOPIC   PARTITION  LAG
  orders  0          182004
  orders  1          179664
  ```
  Lag climbing steadily across *every* partition, not just one, points at a structural
  throughput deficit (too few consumers, or a per-message latency regression) rather than a
  transient blip localized to one partition.
- **Resolution:** Scale consumers up to the partition count if under-provisioned, profile and fix
  the per-message processing time if that's the actual bottleneck, or increase partition count
  (accepting Q11's key-mapping discontinuity) if the topic itself is under-partitioned for the
  required throughput.
- **Prevention:** Alert on consumer lag trend (not just an absolute threshold) so a structural
  slowdown is caught while it's still a minor gap, not after days of unprocessed backlog.

### S4. RabbitMQ starts blocking all publishers across the broker
- **Symptoms:** Publishing suddenly fails or hangs across seemingly unrelated queues, not just
  the one that was actually backing up.
- **Diagnosis:** Check for a memory or disk alarm — RabbitMQ's flow control blocks *all*
  publishers broker-wide once configured memory or disk thresholds are exceeded, as a protective
  measure against running out of resources entirely; a single queue backing up because its
  consumers stalled can be the actual root cause even though the symptom looks broker-wide.
- **Example:**
  ```
  2024-03-11 09:41:02 [warning] <0.612.0> vm_memory_high_watermark set. Memory used: 6.42GB Limit: 6.40GB
  2024-03-11 09:41:02 [warning] <0.612.0> Blocking all publishers until this alarm clears...
  ```
- **Resolution:** Identify and fix the actual stalled consumer(s) causing the backing-up queue,
  free up disk/memory, and once below the alarm threshold, publishing resumes automatically —
  but scaling consumers or adding queue length limits (with dead-lettering) prevents the same
  queue from triggering this again.
- **Prevention:** Set per-queue max-length policies with dead-lettering so one runaway queue
  degrades gracefully (rejecting/dead-lettering new messages) instead of exhausting broker-wide
  resources and taking down every publisher.

### S5. A "cancel order" event is processed before the corresponding "create order" event, leaving the order active
- **Symptoms:** An order that was created and immediately cancelled ends up active (create
  processed after cancel) instead of cancelled, intermittently, for a small fraction of orders.
- **Diagnosis:** Check the partition/routing key used for these events (Q10) — if create and
  cancel events for the same order aren't guaranteed to land in the same partition (Kafka) or be
  processed by the same single consumer (RabbitMQ), there's no ordering guarantee between them at
  all, and under load they can be processed out of order.
- **Example:**
  ```java
  // Unkeyed publish -> round-robin across partitions -> no ordering guarantee at all.
  producer.send(new ProducerRecord<>("orders", null, createdEvent));
  producer.send(new ProducerRecord<>("orders", null, cancelledEvent));
  ```
- **Resolution:** Key both events on the order ID so they're guaranteed to land in the same
  Kafka partition (processed in send order by a single consumer within that partition), or route
  both to the same RabbitMQ queue with single-consumer processing for that entity; add a
  defensive state-machine check in the consumer regardless (reject a "create" for an order
  already in "cancelled" state) as a second line of defense.
- **Prevention:** Design partition/routing keys around per-entity ordering requirements from the
  start for any event stream where sequence matters, and add state-machine guards in consumers as
  standard practice rather than assuming delivery order is guaranteed.

### S6. Consumers repeatedly process the same batch of messages during a period of frequent restarts
- **Symptoms:** Duplicate processing correlates specifically with deployment windows or a flapping
  consumer instance (crash-looping, or an aggressive autoscaler repeatedly adding/removing
  instances).
- **Diagnosis:** Each consumer join/leave triggers a Kafka rebalance (Q19); if consumers are
  restarting frequently, rebalances happen frequently, and any in-flight, not-yet-committed batch
  gets reprocessed by whichever consumer picks up that partition next — a "rebalance storm" from
  flapping instances multiplies the duplicate-processing rate far above the normal baseline.
- **Example:**
  ```
  2024-03-11 10:02:01 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 joined
  2024-03-11 10:02:47 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 left
  2024-03-11 10:03:12 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 joined
  ```
  `consumer-3` flapping every 30–60 seconds — each join/leave triggers a fresh rebalance that
  reprocesses whatever that partition's last uncommitted batch was.
- **Resolution:** Fix the underlying flapping (a crash-looping bug, or an autoscaler configured
  too aggressively for this workload), and separately, ensure consumer shutdown is graceful
  (commit offsets and leave the group cleanly on `SIGTERM` rather than being killed mid-batch)
  to minimize the reprocessing window even when restarts are legitimate.
- **Prevention:** Idempotency (Q13/Q14) is the real safety net here regardless of restart frequency
  — but tuning session/heartbeat timeouts appropriately and fixing flapping instances directly
  reduces how often that safety net actually gets exercised.

### S7. A record shows as saved in the database, but the corresponding downstream service never received the event about it
- **Symptoms:** An order exists in the database, but the shipping service never got the
  `OrderCreated` event and has no record of needing to ship it — discovered only when a customer
  asks where their order is.
- **Diagnosis:** Classic dual-write inconsistency (Q26) — the service committed the database
  write and crashed (or the publish call itself failed) before successfully publishing the event,
  and because the DB write and the message publish weren't atomic, one succeeded without the
  other.
- **Example:**
  ```java
  orderRepository.save(order);                      // commits — the order exists in the DB
  eventPublisher.publish(orderCreatedEvent(order));  // times out here — never actually sent
  // No transaction spans both calls; a failure between them is invisible until a customer
  // notices the order was never shipped.
  ```
- **Resolution:** Immediate mitigation is manually identifying and republishing events for the
  affected records (a reconciliation script comparing "orders in DB" against "events observed
  downstream"). The structural fix is the outbox pattern (Q26) — write the event to an outbox
  table in the same transaction as the business write, and have a separate relay process publish
  from the outbox, guaranteeing the two can't diverge.
- **Prevention:** Treat "how does the event reliably get published" as a required design question
  for any write that must trigger a downstream event, the same way transaction boundaries are a
  required question for any multi-step database write.

### S8. Consumers start throwing deserialization errors right after a producer deploys a change
- **Symptoms:** Multiple consumers of a topic begin failing (or silently misparsing) messages
  immediately following an unrelated-looking producer deployment.
- **Diagnosis:** The producer changed the message schema in a backward-incompatible way — removed
  a field a consumer required, changed a field's type, or renamed something — without any
  compatibility check catching it before publish, since no schema registry (or equivalent
  discipline) was enforcing compatibility rules (Q27).
- **Example:**
  ```
  org.apache.avro.AvroTypeException: Found orders, expecting orders,
      missing required field customerId
  	at org.apache.avro.io.parsing.Symbol$...
  ```
  The producer's last deploy removed `customerId` from the schema with no default — every
  consumer still expecting it fails on the very next message it reads.
- **Resolution:** Roll back the producer's schema change if possible, or ship a compatible fix
  (restore the field, or update every consumer simultaneously if the change genuinely can't be
  backward-compatible — coordinated carefully since consumers deploy independently).
- **Prevention:** Adopt a schema registry with enforced compatibility mode (Q27) so an
  incompatible change is rejected at publish time in CI/staging, not discovered by consumers
  failing in production.

### S9. A dead-letter queue is discovered, weeks later, to contain thousands of unprocessed business events
- **Symptoms:** An audit or unrelated investigation turns up a DLQ that's been silently
  accumulating failed messages for weeks — representing real business events (orders, payments)
  that were never actually completed.
- **Diagnosis:** A DLQ was correctly configured to catch failures (Q22, Q23), but no alerting was
  ever set up on it — messages landing there succeeded at the narrow goal of "don't block the
  main queue" but the broader goal of "someone finds out and fixes it" was never wired up.
- **Example:**
  ```
  $ rabbitmqctl list_queues name messages
  orders-dlq   14382
  ```
  14,382 messages accumulated with zero alerting configured on this queue's depth — each one
  represents a business event that never actually completed.
- **Resolution:** Triage the DLQ contents — for each message, determine whether it can be safely
  reprocessed now (transient failure since resolved) or needs manual business-side reconciliation
  (permanently invalid, needs a human decision on what should have happened).
- **Prevention:** A DLQ without an alert on its depth is not actually a safety net, just a
  slower-motion silent failure — alerting on any DLQ message arriving (or on depth exceeding a
  small threshold) needs to ship alongside the DLQ itself, not as a follow-up task that slips.

### S10. One consumer instance processes most of the messages while others sit mostly idle
- **Symptoms:** Uneven load across a RabbitMQ consumer pool — monitoring shows one or two
  consumers consistently far busier than the rest, despite all consumers being identically
  configured and capable.
- **Diagnosis:** Check the prefetch count (Q18) — a high or unbounded prefetch lets the broker
  push a large batch to whichever consumer happens to ask first, and if that consumer is even
  marginally faster to acknowledge, it keeps getting handed more work in a feedback loop, while
  slower consumers wait idle for their turn.
- **Example:**
  ```
  consumer-a: 8420 messages processed
  consumer-b: 412 messages processed
  consumer-c: 390 messages processed
  ```
  `consumer-a` is only marginally faster to ack, but with prefetch unbounded the broker keeps
  handing it the next batch before `b`/`c` ever get a look — a feedback loop, not a meaningful
  difference in consumer capability.
- **Resolution:** Lower the prefetch count (commonly to 1, or a small number matched to actual
  per-consumer concurrent-processing capacity) so the broker distributes messages more evenly as
  each consumer finishes and acks, rather than front-loading one consumer with a large batch.
- **Prevention:** Default new RabbitMQ consumers to a deliberately-chosen, small prefetch value
  rather than leaving it unbounded — unbounded prefetch is rarely actually the right throughput
  optimization it appears to be.

### S11. A Kafka topic can't scale consumer throughput no matter how many consumer instances are added
- **Symptoms:** Adding more instances to a consumer group has no effect on total throughput past
  a certain point, even though each instance has spare capacity.
- **Diagnosis:** Partition count (Q11) is the hard ceiling on parallelism within a consumer group
  — if the topic has, say, 4 partitions, a 5th consumer in the group simply sits idle with no
  partition assigned, no matter how much capacity it has.
- **Example:**
  ```
  $ kafka-consumer-groups.sh --describe --group orders-group --bootstrap-server broker:9092
  CONSUMER-ID   PARTITION
  consumer-1    0
  consumer-2    1
  consumer-3    2
  consumer-4    3
  consumer-5    -           <- no partition assigned, sitting idle
  ```
- **Resolution:** Increase the topic's partition count to match the actual required parallelism
  (accepting the key-mapping discontinuity from Q11 for any ordering-dependent keys), then scale
  consumers up to match.
- **Prevention:** Provision partition count with future scaling headroom from the start, since
  increasing it later is disruptive to per-key ordering, and decreasing it isn't possible at all
  without recreating the topic.

### S12. A saga gets stuck halfway through, with some services having completed their step and others not
- **Symptoms:** An order-payment-inventory-shipping saga fails at the inventory step, the
  orchestrator triggers a payment refund compensation, but the refund call itself times out or
  fails — the saga is now in an ambiguous state: was the payment refunded or not?
- **Diagnosis:** The compensating transaction itself failed, which the original saga design
  didn't fully account for — compensations were treated as "always succeed" rather than needing
  the same reliability (retry, idempotency) as the forward steps.
- **Example:**
  ```java
  // Stable version's saga step expects:
  record ReserveRequest(String orderId, int quantity) {}
  // A canary version starts requiring an extra field the stable version's compensation
  // logic never learned to send back:
  record ReserveRequest(String orderId, int quantity, String warehouseId) {}
  // A compensation call built against the old contract fails against the new one mid-saga.
  ```
- **Resolution:** Retry the failed compensation with the same idempotency guarantees a forward
  step would need (Q29's point that compensations aren't exempt from Q13); if retries are
  genuinely exhausted, the saga needs an explicit "stuck, needs manual intervention" state with
  alerting, rather than silently appearing complete or silently disappearing.
- **Prevention:** Design every compensating transaction with the same rigor as forward
  transactions from the start — idempotent, retryable, and with an explicit terminal failure
  state that pages a human rather than looping forever or failing silently.

### S13. Users receive the same notification email multiple times for a single event
- **Symptoms:** A "your order has shipped" email (or similar transactional notification) is sent
  two or three times to the same user for the same shipment.
- **Diagnosis:** The notification consumer isn't idempotent (Q13) — under normal at-least-once
  delivery (a rebalance, a retry after a transient failure right after the email was sent but
  before the offset committed), the same message is redelivered and the "send email" side effect
  simply re-executes, since sending an email has no natural idempotency the way a database
  `UPDATE` does.
- **Example:**
  ```java
  if (notificationLog.exists(shipmentId)) return; // already sent — treat as a no-op
  sendShippedEmail(user, shipmentId);
  notificationLog.recordSent(shipmentId); // ideally written in the same transaction as the check
  ```
- **Resolution:** Add an idempotency check specific to this side effect — record "notification
  sent for shipment X" in a table with a unique constraint on the shipment/event ID, checked (and
  inserted, in the same transaction as calling the email provider, or at least before it) before
  actually sending.
- **Prevention:** Recognize that side effects without natural idempotency (sending an email,
  calling a third-party API with no idempotency key support) are exactly the cases needing an
  explicit dedup record — don't assume "the message system handles duplicates," since it usually
  guarantees the opposite (at-least-once, not exactly-once for external side effects).

### S14. During a broker outage, some services silently lose messages while others hang entirely
- **Symptoms:** A brief broker outage causes very different behavior across services — some
  producers' publish calls hang until timeout, others appear to succeed but the message never
  actually arrives once the broker recovers.
- **Diagnosis:** Check each producer's acknowledgment configuration — a producer with no wait for
  acknowledgment (RabbitMQ without publisher confirms, or Kafka's `acks=0`) considers the publish
  "done" the instant it's sent over the socket, with no confirmation the broker actually received
  or persisted it, so a message sent right as the broker goes down is simply lost with the
  producer none the wiser; a producer configured to wait for full acknowledgment blocks/retries
  until it gets one, which is why it hangs instead.
- **Example:**
  ```java
  props.put("acks", "0");   // fire-and-forget — the call returns before the broker even replies
  props.put("acks", "all"); // waits for full replication acknowledgment — blocks/retries instead
  ```
- **Resolution:** Standardize on an acknowledgment level appropriate to the message's importance
  — `acks=all`/publisher confirms with a bounded retry-then-fail (not indefinite hang) for
  anything that can't be silently lost, giving the producer a clear signal it needs to
  fall back to something (queue locally, alert, degrade gracefully) rather than either silent
  loss or indefinite hang.
- **Prevention:** Audit acknowledgment configuration explicitly per producer as a deliberate
  reliability decision, not a default left at whatever the client library ships with, and set a
  bounded timeout with an explicit fallback for any producer that would otherwise hang
  indefinitely during a broker outage.

### S15. A batch of events is discovered to have simply vanished, with no error anywhere
- **Symptoms:** A gap in expected downstream data corresponds to a period where the responsible
  consumer was down (a deployment, an incident) for longer than usual — and once it came back up,
  those specific messages were never processed, with no error logged anywhere.
- **Diagnosis:** Check message TTL configuration (Q9, RabbitMQ) — if the consumer was down
  longer than the configured TTL, the messages expired and were either silently dropped or routed
  to a DLQ that also wasn't being monitored (S9) before anyone noticed; this is functionally
  silent data loss even though the broker "worked correctly" according to its own configuration.
- **Example:**
  ```java
  Map<String, Object> args = new HashMap<>();
  args.put("x-message-ttl", 1_800_000); // 30 minutes
  // no x-dead-letter-exchange set — messages that outlive the consumer's downtime are
  // simply dropped by the broker, with nothing left to reprocess afterward.
  channel.queueDeclare("shipments-queue", true, false, false, args);
  ```
- **Resolution:** If a DLQ captured the expired messages, reprocess them from there; if TTL was
  configured with no dead-lettering fallback at all, the messages are genuinely unrecoverable and
  need business-side reconciliation for the gap.
- **Prevention:** Any TTL configured on a queue carrying business-critical events needs an
  explicit dead-letter target (never silent drop) and alerting on that DLQ — and the TTL value
  itself should be set with realistic worst-case consumer downtime in mind, not just
  happy-path expectations.

### S16. Increasing a topic's partition count to improve throughput breaks a downstream consumer's assumptions
- **Symptoms:** Shortly after a topic's partition count is increased to help with a lag problem
  (S11's fix), a different downstream consumer starts exhibiting the ordering-violation symptom
  from S5, for keys that previously never had ordering issues.
- **Diagnosis:** Increasing partition count (Q11) changes the key → partition hash mapping going
  forward — a key that consistently landed in partition 3 before now lands in a different
  partition for new messages, while older messages for that same key remain in partition 3's
  history; a consumer relying on "all messages for this key have always been in the same
  partition, so I can safely track per-partition state" breaks the moment repartitioning happens.
- **Example:**
  ```java
  // Fragile: assumes a key's entire history lives in one partition forever.
  Map<Integer, State> statePerPartition = new HashMap<>();
  void onRecord(ConsumerRecord<String, String> r) {
      statePerPartition.computeIfAbsent(r.partition(), p -> new State()).apply(r);
  }
  // After repartitioning, a key that used to always hash to partition 3 now hashes to
  // partition 9 for new messages — this map now splits one logical entity's state in two.
  ```
- **Resolution:** For the specific consumer relying on this assumption, it needs to be redesigned
  to not depend on a stable key-to-partition mapping across the topic's lifetime (track state by
  key across all partitions it might appear in, not by partition), since this is often not
  practically reversible.
- **Prevention:** Provision partition count generously up front specifically because
  repartitioning has this hidden cost (Q11), and treat any future repartitioning decision as
  requiring an explicit audit of every consumer's ordering assumptions, not just a throughput
  lever to pull freely.

### S17. A short downstream blip turns into a 40-minute outage because every consumer retries at once
- **Symptoms:** A payment provider returns `503`s for ~30 seconds. The order-processing
  consumers stay red for 40 minutes: consumer lag climbs to millions, the provider's own
  status page shows recovery, yet it keeps rate-limiting us (`429`), and error logs show the
  same records failing repeatedly at high speed.
- **Diagnosis:** Compare request rate to the provider *during* the incident with normal: it is
  5–10x higher. The consumers retry instantly and unconditionally (a tight `retry` loop, or a
  broker that requeues on `nack` immediately), so every failure multiplies traffic exactly when
  the dependency is weakest, and when it recovers it is immediately flattened by the backlog plus
  the retries — a **retry storm**. Because all instances failed at the same instant, their retry
  attempts are synchronized as well. Check for: no backoff, no jitter, no attempt cap, requeue
  with `requeue=true` on every failure, and no circuit breaker (Q30 of module 2).
- **Example:**
  ```java
  @RabbitListener(queues = "payments")
  void handle(Payment p) {
      try { provider.charge(p); }
      catch (Exception e) { throw new AmqpRejectAndDontRequeueException(e); } // ok
  }
  // but the container config had:  spring.rabbitmq.listener.simple.default-requeue-rejected=true
  //   -> the message goes straight back to the head of the queue and fails again in microseconds
  ```
- **Resolution:** Stop the bleeding: pause the consumers (or scale them to zero) until the provider
  is healthy, then resume gradually. Root fix: retries with **exponential backoff and jitter**
  and a bounded attempt count (Q24), a **circuit breaker** that pauses consumption while the
  dependency is open (`KafkaListenerEndpointRegistry.pause()`, or Resilience4j), dead-lettering after
  the last attempt, and a rate limit on outbound calls. Verify with a chaos test: make the stub
  return `503` for 30 s and assert that outbound request rate stays below a cap, and that lag
  drains within a few minutes of recovery instead of oscillating.
- **Prevention:** A shared retry policy library (backoff + jitter + cap) rather than
  per-listener ad hoc loops; circuit breaker plus bulkhead per dependency; dashboards for retry
  count and outbound rate; game-day exercises that inject dependency failures.

### S18. A consumer group keeps rebalancing, lag climbs, and the same messages are processed again and again
- **Symptoms:** After a release that added a call to an enrichment service, a Kafka consumer
  group shows constant activity but almost no progress: lag rises steadily, logs are full of
  `Member consumer-billing-3 ... has left the group` / `Attempt to heartbeat failed since group is
  rebalancing` and `CommitFailedException: ... the time between subsequent calls to poll() was
  longer than the configured max.poll.interval.ms`. Duplicate side effects appear downstream.
- **Diagnosis:** Multiply *records per poll* by *time per record*. The consumer polls up to
  `max.poll.records=500`; the new enrichment call takes ~1 s, so a batch needs ~500 s, above
  the 300 s `max.poll.interval.ms` — the consumer is evicted mid-batch, can't commit, and its
  partitions (with the uncommitted batch) go to another member with the same problem (Q20).
  Confirm from broker-side group logs and consumer metrics `time-between-poll-avg/max`, and with
  a thread dump of a consumer showing it inside the remote call.
- **Example:**
  ```java
  @KafkaListener(topics = "invoices", groupId = "billing")
  void onBatch(List<Invoice> batch) {          // up to 500 records per poll
      for (Invoice i : batch) enrichment.lookup(i);   // ~1s each, no timeout -> 500s+
  }
  ```
- **Resolution:** Shrink the batch (`max.poll.records=50`), add a hard timeout to the enrichment
  call, and — if the work is genuinely slow — parallelize it with a bounded worker pool while
  the poll loop keeps calling `poll()` (or `pause()` the partitions) and only commit offsets of
  finished records. Keep `max.poll.interval.ms` proportional to the worst-case batch, not
  "large enough to hide it". Switch to the cooperative sticky assignor to make any rebalance
  cheaper. Verify that group logs show no rebalances over a soak period, `time-between-poll-max`
  stays under 50% of the interval, and lag drains.
- **Prevention:** Alert on rebalance rate and on `time-between-poll-max` as a fraction of the
  interval; load-test any new synchronous call inside a listener; make every remote call inside a
  consumer have a timeout; keep consumers idempotent because rebalances will still happen.

### S19. Replaying the dead-letter queue after a bug fix sends customers duplicate emails and re-charges some of them
- **Symptoms:** A bug had dead-lettered 80,000 `OrderShipped` events over three days. After the
  fix, an engineer "shovels" the whole DLQ back to the main queue. Within minutes, customers get
  duplicate shipping emails, the partner API rate-limits us, and about 300 customers are charged
  twice.
- **Diagnosis:** Inspect the DLQ contents and headers (`x-death` in RabbitMQ, the original topic /
  exception headers in a Kafka DLT). Many messages *were* partially processed before failing (the
  handler charged the card, then crashed on the email step), and the fixed handler isn't
  idempotent, so replaying re-executes the completed steps. The flood also bypasses normal
  throttling, since 80k messages arrive at once, and some are simply stale (an `OrderShipped` for an
  order cancelled since).
- **Example:**
  ```java
  void handle(OrderShipped e) {
      payments.capture(e.orderId());     // step 1 succeeded on the first attempt...
      mail.sendShipped(e.orderId());     // ...step 2 threw -> message dead-lettered
  }                                      // replay -> step 1 runs again -> double capture
  ```
- **Resolution:** Immediately stop the replay and quantify the damage (query captures by
  `orderId` having count > 1; refund/void the duplicates; apologize to customers where mails
  went out twice). Fix properly before replaying again: make each step idempotent (dedupe by
  event id / capture idempotency key, Q13-Q14); replay in **small, rate-limited batches** and with a
  staleness filter (skip events whose entity state has moved on); replay a sample of ~50 first
  and verify results; keep the original message ids so idempotency holds.
- **Prevention:** A DLQ runbook that says "diagnose, fix, make idempotent, replay a canary
  batch, then throttle the rest"; a replay tool with rate limiting and dry-run; alerts on DLQ
  depth *and* age (Q22, S9); idempotency keys on every side-effecting step — including calls to
  payment providers.

### S20. Publishing intermittently fails with `RecordTooLargeException` (or the broker drops the connection) for a few big orders
- **Symptoms:** Most orders flow normally, but a small percentage — those with hundreds of line
  items or an attached PDF — never reach downstream services. Producer logs show
  `org.apache.kafka.common.errors.RecordTooLargeException: The message is 1,347,220 bytes when
  serialized which is larger than 1,048,576` (or RabbitMQ closes the channel on an oversized
  frame). The DB row was saved.
- **Diagnosis:** The failing records are the large ones: compare failure to payload size. Kafka's
  producer `max.request.size` (default 1 MiB) and the broker/topic `message.max.bytes` /
  `max.message.bytes` reject them; the consumer's `fetch.max.bytes`/`max.partition.fetch.bytes`
  can also block reading them. Notice also *why* the event is that big: it embeds a whole document
  where consumers need an identifier and a few fields — and that the failure was swallowed
  (fire-and-forget `send()`) so the order existed in the DB with no event (Q16, S7).
- **Example:**
  ```java
  // Event carries the full invoice PDF (base64) plus every line item.
  kafkaTemplate.send("orders", order.id(), new OrderCreated(order.id(), order.pdfBase64(), order.lines()));
  ```
- **Resolution:** Don't raise limits blindly (bigger records inflate memory, replication time and
  rebalance risk). Use the **claim-check pattern**: store the large payload in object storage
  (S3/Blob) or the database and publish a small event holding a reference plus the fields
  consumers actually need (Q31); compress if the payload is text. Handle the send result — on
  failure, keep the outbox row and alert instead of dropping it. Verify with a test that publishes
  a 20 MB attachment and asserts that the event stays under ~10 KB and downstream can fetch the
  document.
- **Prevention:** Set an explicit maximum event size in the contract and validate it in the
  producer wrapper; monitor `record-size-max`; a schema review checklist item "does this
  event embed blobs?"; make publish failures visible through the outbox (Q26).

### S21. After a broker crash, orders that the producer confirmed are missing from the topic
- **Symptoms:** A broker in a 3-node Kafka cluster crashed and restarted. Everything recovered,
  but reconciliation shows ~2,000 orders whose `OrderCreated` events the producer logged as
  successfully sent are absent from the topic; downstream systems never saw them. No errors were
  reported at the time.
- **Diagnosis:** "Acknowledged but gone" means the acknowledgement was given before the record
  was replicated. Check producer config: `acks=1`, so the leader confirmed after writing to its
  own log; it then crashed before followers copied those records, and a follower missing them
  became the new leader — the records were truncated on the old leader when it rejoined. Also
  check `min.insync.replicas` (1 means `acks=all` wouldn't have helped) and whether
  `unclean.leader.election.enable=true` (Q16). The cluster metrics show a leader election and
  `UnderReplicatedPartitions` at the crash time.
- **Example:**
  ```properties
  # producer                                # topic
  acks=1                                    replication.factor=3
                                            min.insync.replicas=1
  ```
- **Resolution:** Recover data from the source of truth — re-emit the missing events from the
  database/outbox by comparing order ids (which requires idempotent consumers, Q13). Then fix
  the durability settings: `acks=all`, `enable.idempotence=true`, `min.insync.replicas=2`,
  replication factor 3, unclean election disabled. Verify with a fault-injection test: produce
  continuously, kill the leader broker, and assert that no acknowledged record is missing and that
  producers see errors (not silent success) if quorum is lost.
- **Prevention:** Bake the producer/topic defaults into a shared client library and topic
  provisioning so individual teams don't choose `acks=1` by accident; run broker failure drills
  regularly; add reconciliation between the database and the topic for critical flows.

### S22. The PostgreSQL disk fills up and the primary stops accepting writes, days after a CDC connector "just stopped"
- **Symptoms:** A Debezium connector feeding the orders outbox failed one weekend and nobody
  noticed. Days later the database volume alerts at 90%, then 100%: the primary goes read-only or
  crashes, taking the whole platform down. The tables themselves haven't grown; the `pg_wal`
  directory is hundreds of GB.
- **Diagnosis:** A logical replication slot forces PostgreSQL to retain all WAL the slot's
  consumer hasn't yet confirmed. With the connector dead, the slot is inactive and its
  `restart_lsn` never advances:
  ```sql
  select slot_name, active,
         pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) as retained_wal
  from pg_replication_slots;
  --  debezium_orders | f | 412 GB
  ```
  Then find *why* the connector stopped (Kafka Connect task failed, schema change it couldn't
  handle, broker unreachable) in the Connect logs (Q30).
- **Example:**
  ```json
  { "name": "orders-outbox", "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "slot.name": "debezium_orders", "plugin.name": "pgoutput" } }
  ```
- **Resolution:** Emergency: free disk first, then either restart/fix the connector so it drains
  the slot, or — if recovery is impossible in time — drop the slot
  (`select pg_drop_replication_slot('debezium_orders');`), accepting that the connector needs a new
  snapshot and that events since the failure must be re-derived from the outbox/table (consumers
  idempotent). Prevent recurrence: set `max_slot_wal_keep_size` (PostgreSQL 13+) so an abandoned
  slot is invalidated instead of eating the disk, and verify by simulating connector downtime in
  staging.
- **Prevention:** Alert on `retained_wal` per slot and on Kafka Connect task state (`FAILED`),
  monitor disk with a forecast, keep a runbook for "connector down > 1 hour", and treat every
  replication slot as a resource with an owner.

## 📌 Cheat-sheet

- **RabbitMQ** = smart broker (routing, per-message delivery tracking), consumed message is gone. **Kafka** = dumb broker (append-only log, retains regardless of consumption), enables replay.
- **Delivery semantics**: at-most-once (fire-and-forget, can lose) vs at-least-once (default in practice, can duplicate) vs exactly-once (broker-internal only — app side effects still need idempotency).
- **Idempotency strategies**: unique constraint on a business key (strongest — atomic, no check-then-insert race), processed-message log, or naturally idempotent operations (`SET x = y`, not `x += 1`).
- **Kafka ordering** = per-partition only; key choice determines which entities share ordering guarantees.
- **RabbitMQ ordering** = per-queue with a single consumer only; multiple consumers on one queue breaks it.
- **DLQ** = required for any consumer with a bounded retry count; a DLQ with no alerting is silent data loss, not a safety net.
- **Kafka rebalance** = triggered by join/leave/partition change; causes reprocessing of uncommitted batches → idempotency is not optional.
- **Offset commit**: manual, after successful processing, for at-least-once correctness; auto-commit risks silent loss.
- **Prefetch (RabbitMQ)**: low = fair distribution, safer on crash; unbounded = throughput but uneven load and big requeue spikes on crash.
- **Saga**: orchestration (central, visible, easy to reason about) vs choreography (decoupled, harder to trace) — compensations need the same idempotency/retry rigor as forward steps.
- **Outbox pattern**: write event + business data in one DB transaction; a relay process publishes from the outbox — solves the dual-write problem.
- **Poison pill**: bounded retry count + DLQ, never unlimited requeue.
- **Schema evolution**: schema registry (Avro/Protobuf) enforces backward compatibility at publish time; additive-optional-field-with-default is always safe.
- **Kafka partition count**: ceiling on parallelism, can increase (breaks key→partition mapping for new messages) but never decrease.
- **Publisher confirms / Kafka acks**: confirm producer→broker persistence only — never end-to-end processing guarantee.
- **Dual-write problem**: DB write + message publish is never atomic across two systems by default — outbox pattern is the standard fix.
</content>
- **Queue vs topic**: competing consumers *share* a queue (scale-out); pub/sub gives *each* subscriber its own queue/consumer group — same `group.id` = compete, different `group.id` = fan-out; parallelism ≤ partitions.
- **Ack semantics**: ack after processing = at-least-once (crash → redelivery); auto-ack = at-most-once; Kafka's equivalent is the committed offset. Requeue-on-failure without a limit is a hot loop.
- **Kafka durability** = `acks=all` + `min.insync.replicas=2` + RF 3 + `unclean.leader.election.enable=false` + idempotent producer + *check the send result*; `acks=1` loses acknowledged data on leader failure.
- **`max.poll.interval.ms`**: heartbeats come from a separate thread, so a slow processing loop gets evicted while "healthy" → rebalance loop; shrink `max.poll.records`, timeout downstream calls, cooperative assignor, static membership.
- **Retries**: in-place retry blocks the partition; use retry topics/TTL+DLX with exponential backoff + jitter, cap attempts, retry only transient errors, expect lost ordering, keep handlers idempotent.
- **Multi-region Kafka**: MM2/cluster linking is async (RPO > 0), offsets differ across clusters, active-active needs entity ownership/conflict rules; stretch cluster = zero RPO at latency cost.
- **Event content**: notification (thin, call back) vs event-carried state (fat, autonomous consumers, schema = contract) vs event sourcing (log is the truth, needs versioning/snapshots).
- **Publishing reliably**: never dual-write; polling outbox (simple, `SKIP LOCKED`) → Debezium CDC (low latency, but replication slots can fill the disk — cap with `max_slot_wal_keep_size`, alert on lag).
- **DLQ replay is a deploy**: fix, make idempotent, replay a canary batch, then throttle; filter stale events.
- **Big payloads**: claim-check (store blob elsewhere, publish a reference); don't just raise `max.request.size`.
