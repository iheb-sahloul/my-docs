# Messaging Best Practices

Rules for Kafka and RabbitMQ producers and consumers in Spring services. The interview questions behind them are in [Messaging](../interviews/messaging-rabbitmq-kafka.md).

## 📤 Producing

### Publish events with the transactional outbox, not after the commit

Write the event to an `outbox` table in the same database transaction as the business change, and let a relay
(polling or CDC with Debezium) publish it.

**Why it's a best practice:** "save, then `kafkaTemplate.send()`" is a dual write. If the broker is down or the pod
dies between the two, the order exists but nobody is told; if you send first, consumers can see an order that was
rolled back. The outbox makes the event as durable as the data, at the cost of at-least-once delivery, which
consumers must handle anyway.

```java
// ✅ same transaction
@Transactional
public void place(Order order) {
    orders.save(order);
    outbox.save(OutboxEvent.of("order", order.id(), "OrderPlaced", toJson(order)));
}
```

### Configure producers for durability

For Kafka: `acks=all`, idempotence enabled (the default in recent clients), and `min.insync.replicas=2` on topics
with replication factor 3. For RabbitMQ: publisher confirms, persistent messages and durable (quorum) queues.

**Why it's a best practice:** with `acks=1` a leader crash can lose messages it had acknowledged; without publisher
confirms, a RabbitMQ publish can fail silently. These settings cost a few milliseconds of latency, which is almost
always cheaper than investigating a lost payment event.

```properties
spring.kafka.producer.acks=all
spring.kafka.producer.properties.enable.idempotence=true
spring.rabbitmq.publisher-confirm-type=correlated
```

### Choose the message key for ordering and spread

In Kafka, use the entity id whose events must stay in order (order id, account id) as the key.

**Why it's a best practice:** ordering is only guaranteed within a partition, and the key decides the partition. No key
means round-robin and no ordering; a low-cardinality key (country, status) puts most traffic on a few partitions and
caps your consumers' parallelism.

⛔ `send("orders", null, event)` or `send("orders", event.country(), event)`
✅ `send("orders", event.orderId(), event)`

## 📥 Consuming

### Make every consumer idempotent

Assume every message can arrive twice and make processing it twice harmless: a processed-message table with a
unique key, upserts, or a natural idempotency key checked in the same transaction as the side effect.

**Why it's a best practice:** both Kafka and RabbitMQ deliver at least once in practice: rebalances, retries, outbox
relays and redeliveries all produce duplicates. "Exactly-once" in Kafka covers Kafka-to-Kafka processing, not your
database or the email you sent.

```java
// ✅
@Transactional
@KafkaListener(topics = "payments")
void on(PaymentCaptured e) {
    if (processed.insertIfAbsent(e.eventId())) {      // unique constraint on event_id
        invoices.markPaid(e.orderId());
    }
}
```

### Retry with backoff, then dead-letter

Retry transient failures a few times with exponential backoff, send messages that still fail (and poison messages
right away) to a dead-letter topic or queue, and alert on it.

**Why it's a best practice:** infinite retries on a poison message block the partition (Kafka) or spin the CPU
(RabbitMQ requeue loop), and every message behind it waits. Dropping errors silently loses data. A DLQ with the
original payload, the error and headers lets someone fix and replay.

```java
// ✅ Spring Kafka
@Bean DefaultErrorHandler errorHandler(KafkaTemplate<?, ?> template) {
    var handler = new DefaultErrorHandler(new DeadLetterPublishingRecoverer(template),
                                          new ExponentialBackOff(500, 2.0));
    handler.addNotRetryableExceptions(ValidationException.class);
    return handler;
}
```

### Keep processing within the poll interval

Keep the work per message short, or lower `max.poll.records`, so a batch is processed well within
`max.poll.interval.ms`.

**Why it's a best practice:** if processing a batch takes longer than the interval, the consumer is evicted from the
group, its partitions are reassigned, the uncommitted batch is processed again elsewhere, and the cycle repeats: a
rebalance storm with duplicates and growing lag.

## 📐 Contracts & operations

### Version message schemas and evolve them compatibly

Define events with a schema (Avro, Protobuf or JSON Schema) in a registry, with compatibility checks, and only make
backward-compatible changes: add optional fields, never rename or retype.

**Why it's a best practice:** producers and consumers deploy independently, and a topic keeps old messages; a
consumer may read last week's format today. A registry rejects a breaking change at build time instead of at 3 a.m.
on the consumer side.

### Monitor consumer lag, not just errors

Alert on consumer lag (messages or, better, time behind) and on DLQ size, per consumer group.

**Why it's a best practice:** a stuck or slow consumer produces no errors; it just falls behind until users notice
that emails or statuses are hours late. Lag is the metric that shows it, and time lag is easier to relate to an SLO
than a message count.
