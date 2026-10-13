# Kafka & RabbitMQ

## Kafka

Commands use the scripts shipped with Kafka (`kafka-topics.sh` etc.; in Confluent images they have no `.sh`). `$BS` is the bootstrap server, for example `localhost:9092`.

### Topics

```bash
kafka-topics.sh --bootstrap-server $BS --list
kafka-topics.sh --bootstrap-server $BS --describe --topic orders          # partitions, leaders, ISR
kafka-topics.sh --bootstrap-server $BS --create --topic orders \
  --partitions 12 --replication-factor 3 --config min.insync.replicas=2
kafka-topics.sh --bootstrap-server $BS --alter --topic orders --partitions 24   # can only increase; changes key -> partition mapping
kafka-configs.sh --bootstrap-server $BS --entity-type topics --entity-name orders \
  --alter --add-config retention.ms=604800000                                 # 7 days
kafka-topics.sh --bootstrap-server $BS --describe --under-replicated-partitions
```

### Produce & consume

```bash
kafka-console-producer.sh --bootstrap-server $BS --topic orders \
  --property parse.key=true --property key.separator=:          # type  42:{"status":"PAID"}
kafka-console-consumer.sh --bootstrap-server $BS --topic orders --from-beginning \
  --property print.key=true --property print.headers=true --property print.timestamp=true
kafka-console-consumer.sh --bootstrap-server $BS --topic orders \
  --partition 3 --offset 1500 --max-messages 10                  # read one exact spot
```

[kcat](https://github.com/edenhill/kcat) is quicker for debugging:

```bash
kcat -b $BS -L                                   # metadata: brokers, topics, partitions
kcat -b $BS -t orders -C -o -10 -e               # last 10 messages per partition, then exit
kcat -b $BS -t orders -C -f '%p %o %k %s\n'      # partition, offset, key, value
echo '42:{"status":"PAID"}' | kcat -b $BS -t orders -P -K:
```

### Consumer groups & lag

```bash
kafka-consumer-groups.sh --bootstrap-server $BS --list
kafka-consumer-groups.sh --bootstrap-server $BS --describe --group billing   # CURRENT-OFFSET, LOG-END-OFFSET, LAG, CONSUMER-ID
kafka-consumer-groups.sh --bootstrap-server $BS --describe --group billing --members --verbose
```

### Reset offsets (replay or skip)

The group must have no active consumers: scale the deployment to 0 first. Always run with `--dry-run` before `--execute`.

```bash
kafka-consumer-groups.sh --bootstrap-server $BS --group billing --topic orders \
  --reset-offsets --to-datetime 2026-10-05T08:00:00.000 --dry-run
kafka-consumer-groups.sh --bootstrap-server $BS --group billing --topic orders \
  --reset-offsets --to-earliest --execute
kafka-consumer-groups.sh --bootstrap-server $BS --group billing --topic orders:3 \
  --reset-offsets --shift-by 1 --execute          # skip one poison message on partition 3
```

### Docker one-liner for local work

```bash
docker run -d --name kafka -p 9092:9092 apache/kafka:latest      # single-node KRaft broker
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## RabbitMQ

### Inspect with `rabbitmqctl` / `rabbitmq-diagnostics`

```bash
rabbitmqctl list_queues name type messages messages_ready messages_unacknowledged consumers
rabbitmqctl list_exchanges name type
rabbitmqctl list_bindings source_name destination_name routing_key
rabbitmqctl list_connections name user state channels
rabbitmqctl list_consumers queue_name channel_pid prefetch_count
rabbitmq-diagnostics status
rabbitmq-diagnostics check_port_connectivity
rabbitmq-diagnostics memory_breakdown                  # who uses the memory
rabbitmq-queues quorum_status orders.q                 # quorum queue members and leader
```

`messages_unacknowledged` high with consumers present → consumers are slow or stuck holding messages (check prefetch). `messages_ready` growing → not enough consumers.

### Manage with `rabbitmqadmin` (management plugin)

```bash
rabbitmqadmin declare exchange name=orders type=topic durable=true
rabbitmqadmin declare queue name=billing.q durable=true arguments='{"x-queue-type":"quorum","x-dead-letter-exchange":"orders.dlx"}'
rabbitmqadmin declare binding source=orders destination=billing.q routing_key='order.*'
rabbitmqadmin publish exchange=orders routing_key=order.placed payload='{"id":42}'
rabbitmqadmin get queue=billing.q count=5 ackmode=reject_requeue_true    # peek without consuming
rabbitmqadmin purge queue name=billing.q                                  # ⚠️ deletes messages
```

### Policies (DLX, TTL, length limit)

```bash
rabbitmqctl set_policy dlx '^billing\.' '{"dead-letter-exchange":"orders.dlx"}' --apply-to queues
rabbitmqctl set_policy ttl '^tmp\.' '{"message-ttl":60000,"max-length":10000}' --apply-to queues
rabbitmqctl list_policies
```

### Move messages from a DLQ back (shovel)

```bash
rabbitmq-plugins enable rabbitmq_shovel rabbitmq_shovel_management
rabbitmqctl set_parameter shovel replay-billing \
  '{"src-uri":"amqp://","src-queue":"billing.dlq","dest-uri":"amqp://","dest-queue":"billing.q","src-delete-after":"queue-length"}'
```

### Docker one-liner for local work

```bash
docker run -d --name rabbit -p 5672:5672 -p 15672:15672 rabbitmq:4-management   # UI: http://localhost:15672 guest/guest
```
