# Bonnes pratiques Messaging

Règles pour les producteurs et consommateurs Kafka et RabbitMQ dans des services Spring. Les questions d'entretien correspondantes sont dans [Messaging](../interviews/messaging-rabbitmq-kafka.md).

## 📤 Production

### Publiez les événements avec l'outbox transactionnelle, pas après le commit

Écrivez l'événement dans une table `outbox` dans la même transaction que le changement métier, et laissez un relais
(polling ou CDC avec Debezium) le publier.

**Pourquoi c'est une bonne pratique :** « sauvegarder, puis `kafkaTemplate.send()` » est une double écriture. Si le
broker est indisponible ou si le pod meurt entre les deux, la commande existe mais personne n'est prévenu ; si vous
envoyez d'abord, les consommateurs peuvent voir une commande annulée par un rollback. L'outbox rend l'événement aussi
durable que les données, au prix d'une livraison at-least-once, que les consommateurs doivent de toute façon gérer.

```java
// ✅ même transaction
@Transactional
public void place(Order order) {
    orders.save(order);
    outbox.save(OutboxEvent.of("order", order.id(), "OrderPlaced", toJson(order)));
}
```

### Configurez les producteurs pour la durabilité

Pour Kafka : `acks=all`, idempotence activée (par défaut dans les clients récents), et `min.insync.replicas=2` sur les
topics avec un facteur de réplication de 3. Pour RabbitMQ : publisher confirms, messages persistants et files durables
(quorum).

**Pourquoi c'est une bonne pratique :** avec `acks=1`, un crash du leader peut perdre des messages qu'il avait
acquittés ; sans publisher confirms, une publication RabbitMQ peut échouer silencieusement. Ces réglages coûtent
quelques millisecondes de latence, presque toujours moins cher qu'enquêter sur un événement de paiement perdu.

```properties
spring.kafka.producer.acks=all
spring.kafka.producer.properties.enable.idempotence=true
spring.rabbitmq.publisher-confirm-type=correlated
```

### Choisissez la clé de message pour l'ordre et la répartition

Dans Kafka, utilisez comme clé l'identifiant de l'entité dont les événements doivent rester ordonnés (id de commande,
id de compte).

**Pourquoi c'est une bonne pratique :** l'ordre n'est garanti qu'au sein d'une partition, et la clé décide de la
partition. Sans clé, c'est du round-robin et aucun ordre ; une clé à faible cardinalité (pays, statut) concentre
l'essentiel du trafic sur quelques partitions et plafonne le parallélisme des consommateurs.

⛔ `send("orders", null, event)` ou `send("orders", event.country(), event)`
✅ `send("orders", event.orderId(), event)`

## 📥 Consommation

### Rendez chaque consommateur idempotent

Partez du principe que chaque message peut arriver deux fois et rendez son double traitement sans effet : une table
des messages traités avec une clé unique, des upserts, ou une clé d'idempotence naturelle vérifiée dans la même
transaction que l'effet de bord.

**Pourquoi c'est une bonne pratique :** Kafka comme RabbitMQ livrent en pratique au moins une fois : rebalances,
retries, relais d'outbox et redélivrances produisent tous des doublons. L'« exactly-once » de Kafka couvre le
traitement Kafka vers Kafka, pas votre base de données ni l'e-mail que vous avez envoyé.

```java
// ✅
@Transactional
@KafkaListener(topics = "payments")
void on(PaymentCaptured e) {
    if (processed.insertIfAbsent(e.eventId())) {      // contrainte unique sur event_id
        invoices.markPaid(e.orderId());
    }
}
```

### Réessayez avec backoff, puis envoyez en dead-letter

Réessayez quelques fois les échecs transitoires avec un backoff exponentiel, envoyez les messages qui échouent encore
(et les messages empoisonnés immédiatement) vers un topic ou une file de dead-letter, et alertez dessus.

**Pourquoi c'est une bonne pratique :** des retries infinis sur un message empoisonné bloquent la partition (Kafka) ou
font tourner le CPU (boucle de requeue RabbitMQ), et tous les messages derrière attendent. Ignorer silencieusement les
erreurs perd des données. Une DLQ avec le payload d'origine, l'erreur et les en-têtes permet de corriger et de rejouer.

```java
// ✅ Spring Kafka
@Bean DefaultErrorHandler errorHandler(KafkaTemplate<?, ?> template) {
    var handler = new DefaultErrorHandler(new DeadLetterPublishingRecoverer(template),
                                          new ExponentialBackOff(500, 2.0));
    handler.addNotRetryableExceptions(ValidationException.class);
    return handler;
}
```

### Restez dans l'intervalle de poll

Gardez un traitement court par message, ou baissez `max.poll.records`, pour qu'un lot soit traité bien avant
`max.poll.interval.ms`.

**Pourquoi c'est une bonne pratique :** si le traitement d'un lot dépasse l'intervalle, le consommateur est exclu du
groupe, ses partitions sont réassignées, le lot non commité est retraité ailleurs, et le cycle recommence : une tempête
de rebalances avec des doublons et un lag qui grandit.

## 📐 Contrats & exploitation

### Versionnez les schémas de messages et faites-les évoluer de façon compatible

Définissez les événements avec un schéma (Avro, Protobuf ou JSON Schema) dans un registre, avec contrôle de
compatibilité, et ne faites que des changements rétrocompatibles : ajoutez des champs optionnels, ne renommez ni ne
changez jamais de type.

**Pourquoi c'est une bonne pratique :** producteurs et consommateurs se déploient indépendamment, et un topic conserve
les anciens messages ; un consommateur peut lire aujourd'hui le format de la semaine dernière. Un registre rejette un
changement cassant au build plutôt qu'à 3 h du matin côté consommateur.

### Surveillez le lag des consommateurs, pas seulement les erreurs

Alertez sur le lag des consommateurs (en messages ou, mieux, en temps de retard) et sur la taille des DLQ, par groupe
de consommateurs.

**Pourquoi c'est une bonne pratique :** un consommateur bloqué ou lent ne produit aucune erreur ; il prend simplement
du retard jusqu'à ce que les utilisateurs remarquent que les e-mails ou les statuts ont des heures de décalage. Le lag
est la métrique qui le révèle, et un lag en temps se relie plus facilement à un SLO qu'un nombre de messages.
