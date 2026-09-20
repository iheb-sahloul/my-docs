# Messaging (RabbitMQ / Kafka)

## 🟢 Fondamentaux

### Pourquoi le messaging

#### Q1. Pourquoi utiliser un message broker plutôt qu'un appel synchrone direct entre services ?
Un appel direct couple l'appelant à la disponibilité et à la latence de l'appelé en temps réel — si
l'appelé est lent ou en panne, l'appelant est bloqué ou échoue immédiatement. Un broker les
découple dans le temps et dans la gestion des pannes : le producer publie et passe à autre chose,
le consumer traite quand il le peut, et une panne du consumer ne fait pas tomber le producer (les
messages s'accumulent simplement dans la queue, dans certaines limites). Il découple aussi la
*cardinalité* — un même événement peut être diffusé à plusieurs consumers indépendants (un
événement order-placed déclenchant facturation, expédition et analytics) sans que le producer
sache ni se soucie de qui écoute.

#### Q2. Quand privilégier une requête/réponse synchrone plutôt que du messaging asynchrone ?
Les appels synchrones (REST/gRPC) conviennent quand l'appelant a réellement besoin du résultat
*tout de suite* pour continuer (une autorisation de paiement sans laquelle le checkout ne peut pas
avancer, une lecture que l'UI attend pour s'afficher) et quand une indisponibilité temporaire de
l'appelé doit être un échec visible plutôt que silencieusement mise en file d'attente pour plus
tard. Le messaging asynchrone convient quand l'appelant n'a pas besoin d'un résultat immédiat
(émettre un événement « send welcome email » et passer à la suite), quand le découplage de la
disponibilité compte plus que la cohérence instantanée, ou quand la diffusion (fan-out) vers
plusieurs consumers indépendants est le vrai besoin. Beaucoup de systèmes réels combinent les
deux : un appel synchrone pour la décision sur le chemin critique, puis des événements asynchrones
publiés ensuite pour tout ce qui peut se produire à terme.

#### Q3. Quelle est la différence entre une queue (point-à-point) et un topic (publish/subscribe), et comment s'insèrent les competing consumers ?
Dans une queue **point-à-point**, chaque message est livré à exactement *un* consumer : plusieurs
instances du même service lisant une même queue sont des **competing consumers** qui se partagent
la charge, ce qui permet de scaler le traitement horizontalement (10 workers vidant une queue
`emails`). En **publish/subscribe**, chaque message est livré à *chaque* abonné intéressé : un
événement `OrderPlaced` atteint la facturation, l'expédition et l'analytics de façon indépendante,
chacun à son propre rythme. Les deux sont généralement combinés : chaque abonné *logique*
(facturation) possède sa propre queue ou son propre consumer group, et les instances *à
l'intérieur* de cet abonné se font concurrence pour ses messages. Dans RabbitMQ, c'est un exchange
`fanout` ou `topic` lié à une queue par abonné, les instances d'un service consommant la queue de
ce service. Dans Kafka, c'est le consumer group : les consumers ayant le **même** `group.id` se
répartissent les partitions d'un topic (competing), tandis que les consumers ayant des group ids
**différents** reçoivent chacun le flux complet (pub/sub) — et le parallélisme est plafonné par le
nombre de partitions (Q11). Se tromper ici a deux symptômes classiques : deux services différents
partageant une même queue/un même group, si bien que chacun ne voit que la *moitié* des
événements, ou un service scalé horizontalement où chaque instance a son propre group et traite
donc chaque message N fois.

### Modèles de brokers

#### Q4. Décrivez le modèle de base de RabbitMQ : exchange, queue, binding, routing key.
Un producer ne publie jamais directement dans une queue — il publie dans un **exchange**, qui
route le message vers zéro ou plusieurs **queues** en fonction des **bindings** (règles reliant un
exchange à une queue) et, selon le type d'exchange, d'une **routing key**. Un exchange `direct`
route vers les queues dont la binding key correspond exactement à la routing key ; un exchange
`topic` compare les routing keys à des patterns avec jokers (`orders.*.created`) ; un exchange
`fanout` ignore complètement la routing key et diffuse à toutes les queues liées. Les consumers
s'abonnent à des queues, pas à des exchanges — c'est la couche exchange/binding qui donne à
RabbitMQ un routage flexible sans que les producers aient besoin de savoir quelles queues existent.

#### Q5. Décrivez le modèle de base de Kafka : topic, partition, offset, consumer group.
Un **topic** est un log en append-only, découpé en une ou plusieurs **partitions** pour le
parallélisme — chaque partition est sa propre séquence append-only, ordonnée indépendamment, et la
position d'un message dans celle-ci est son **offset**. Les producers écrivent dans une partition
(choisie par le hash d'une clé, ou en round-robin s'il n'y a pas de clé), et les consumers lisent
les partitions séquentiellement, en suivant leur propre offset (jusqu'où ils ont lu). Un
**consumer group** est un ensemble de consumers qui se partagent le travail d'un topic — Kafka
assigne chaque partition à exactement un consumer au sein d'un group, de sorte qu'un group avec
autant de consumers que de partitions obtient un parallélisme complet, et que plusieurs consumer
groups indépendants peuvent chacun lire indépendamment tout le topic (contrairement à une queue
RabbitMQ, où un message va à un seul consumer, point final).

### Sémantiques de livraison

#### Q6. Quelle est la différence entre livraison at-most-once, at-least-once et exactly-once ?
**At-most-once** : un message est livré zéro ou une fois — si quelque chose échoue après l'envoi,
il est simplement perdu, jamais rejoué (fire-and-forget). **At-least-once** : un message est
garanti d'être livré une fois ou plus — les échecs déclenchent un retry/une redelivery, mais cela
signifie qu'un consumer peut voir le même message deux fois (Q13 explique pourquoi c'est de très
loin le défaut le plus courant dans le monde réel). **Exactly-once** : livré et traité exactement
une fois, sans doublon ni perte — réellement difficile à garantir de bout en bout à travers un
réseau, et là où les brokers le revendiquent (les « exactly-once semantics » de Kafka), il s'agit
typiquement d'exactly-once *à l'intérieur* de la frontière transactionnelle du broker (producer →
topic → commit d'offset du consumer, le tout interne à Kafka), et non d'une garantie qui
s'étendrait automatiquement à un effet de bord externe arbitraire réalisé par le consumer
(débiter une carte, envoyer un email) — cet effet de bord final nécessite toujours une
idempotence au niveau applicatif (Q13).

#### Q7. À quoi servent les acknowledgements dans un message broker, et que devient un message dont le consumer plante avant d'acquitter ?
Un acknowledgement, c'est le consumer qui dit au broker « j'ai traité ceci — tu peux l'oublier ».
Tant qu'il n'est pas arrivé, le broker conserve le message et le considère *in flight*. Si le
consumer meurt, si sa connexion tombe, ou s'il rejette explicitement (`nack`/`reject`), le broker
remet le message à disposition — en le **redélivrant**, au même consumer ou à un autre. C'est le
mécanisme derrière la livraison at-least-once (Q6) : acquitter *après* le traitement signifie
qu'un plantage en cours de route provoque un doublon, jamais une perte ; acquitter *avant* le
traitement (auto-ack) transforme un plantage en perte silencieuse de message (at-most-once). Un
message rejeté peut être remis en queue, abandonné ou routé vers une dead-letter queue (Q22) —
remettre en queue un message qui échoue systématiquement crée une boucle chaude infinie, d'où
l'importance d'une limite de retry (Q23). Kafka n'a pas d'ack par message : l'équivalent est le
commit de l'*offset* du consumer group, signifiant « tout jusqu'ici est traité » (Q17), donc un
offset commité trop tôt perd des messages et un offset commité trop tard provoque du retraitement.
Dans tous les cas, la redelivery est un fonctionnement normal, et c'est pourquoi les consumers
doivent être idempotents (Q13).

## 🟡 Pièges seniors

### Comparaison des brokers et rétention

#### Q8. Quelle est la différence architecturale fondamentale entre RabbitMQ et Kafka, et comment guide-t-elle le choix de l'un ou de l'autre ?
**Réponse :** RabbitMQ est un message broker traditionnel : un modèle « smart broker, simple
consumer » — le broker gère le routage (exchanges/bindings), suit l'état de livraison/d'acquittement
de chaque message, et une fois qu'un message est acquitté et consommé, il disparaît définitivement
de la queue. Kafka est un commit log distribué : un modèle « dumb broker, smart consumer » — le
broker se contente d'ajouter les messages à une partition et de les conserver pendant une durée ou
une taille configurée, sans suivre l'état de livraison par consumer au-delà de ce qu'un consumer
group rapporte comme son propre offset ; le même message peut être relu en repositionnant un
offset, rejoué par un tout nouveau consumer group, ou lu indépendamment par de nombreux groups à
leur propre rythme. La conséquence architecturale qui guide réellement le choix : le modèle de
RabbitMQ offre un routage flexible côté broker (priority queues, fan-out par pattern de topic,
request/reply) à un débit modéré ; le modèle de Kafka offre un très haut débit et le
replay/retraitement comme capacité de premier ordre, au prix de l'absence de toute intelligence de
routage dans le broker — c'est un consumer Kafka qui décide de ce qu'un message signifie et de ce
qu'il faut en faire, le broker n'inspecte jamais le contenu.

**Exemple :**
```java
// RabbitMQ : le broker prend la décision de routage via les bindings — le publisher choisit juste une clé.
channel.exchangeDeclare("orders", BuiltinExchangeType.TOPIC);
channel.queueBind("billing-queue", "orders", "order.created.*");
channel.basicPublish("orders", "order.created.eu", null, payload);
// Le broker compare la routing key à chaque binding et décide où ça va.

// Kafka : le broker ne fait aucun routage — le producer choisit la partition (via la clé),
// et n'importe quel consumer group peut décider indépendamment de lire ce topic depuis n'importe quel offset.
producer.send(new ProducerRecord<>("orders", orderId, payload)); // clé -> hash de partition
// Six mois plus tard, un tout nouveau consumer group "fraud-detection" peut s'abonner à "orders"
// et rejouer tout l'historique retenu — RabbitMQ n'a pas d'équivalent une fois un message acquitté.
```

**Pourquoi c'est un piège :** « Kafka, c'est juste un RabbitMQ plus rapide » est le mauvais modèle
mental — choisir Kafka pour un problème de request/reply ou de routage complexe (où
l'intelligence côté broker de RabbitMQ est la vraie réponse) ou choisir RabbitMQ pour un besoin de
replay/audit-log (que son modèle consume-and-gone ne peut pas fournir) revient à choisir l'outil
sur sa réputation, et non selon l'architecture dont l'exigence a réellement besoin.

#### Q9. Rétention Kafka vs TTL RabbitMQ — en quoi les modèles mentaux des deux systèmes diffèrent-ils sur la durée de vie d'un message ?
**Réponse :** Kafka conserve les messages pendant une durée ou une taille configurée
*indépendamment de la consommation* — un message reste dans le log et peut être relu en
repositionnant un offset, ou lu depuis le début par un tout nouveau consumer group, jusqu'à ce que
la rétention l'expire ; la consommation ne supprime rien. Le modèle de RabbitMQ est orienté
consommation : un message est retiré d'une queue dès qu'il a été consommé et acquitté avec succès
(c'est tout l'intérêt d'une queue traditionnelle), et le TTL est purement un filet de sécurité du
type « abandonne et expire/dead-lettere ceci si personne ne le consomme dans un délai de N », pas
un mécanisme de replay. La conséquence pratique : Kafka supporte naturellement le
replay/retraitement (reconstruire une projection à partir des 7 derniers jours d'événements) comme
capacité de base ; RabbitMQ non — une fois consommé, un message a disparu, et construire du replay
au-dessus de RabbitMQ signifie que le producer ou le consumer doit persister l'historique
séparément par lui-même.

**Exemple :**
```
# Kafka : conservé 7 jours indépendamment de la consommation ; un nouveau consumer group peut démarrer
# depuis le début et lire les 7 jours d'historique complets.
retention.ms=604800000

# RabbitMQ : une expiration filet de sécurité, pas un mécanisme de replay — une fois consommé, il a disparu de toute façon.
x-message-ttl: 3600000  # 1 heure — expire (ou dead-lettere) si personne ne le consomme à temps
```

**Pourquoi c'est un piège :** supposer que « RabbitMQ a aussi une notion proche de la rétention,
donc je peux reconstruire l'historique avec comme je le ferais avec Kafka » — le TTL est un
mécanisme d'abandon pour les messages non livrés, pas un historique interrogeable ; RabbitMQ jette
un message dès qu'il est acquitté avec succès, aussi récemment que cela se soit produit.

### Ordre et partitionnement

#### Q10. Quelles garanties d'ordre Kafka et RabbitMQ fournissent-ils réellement, et qu'est-ce qui les brise couramment ?
**Réponse :** Kafka ne garantit l'ordre que *au sein d'une seule partition* — les messages avec la
même clé atterrissent toujours dans la même partition et sont lus dans l'ordre où ils ont été
écrits, mais il n'y a aucune garantie d'ordre *entre* partitions. Le cas classique où l'ordre se
brise : choisir une clé de partition à faible cardinalité ou sans rapport (ou pas de clé, ce qui
provoque une distribution round-robin) pour des événements qui ont réellement besoin d'un ordre
par entité — p. ex. « order created » et « order cancelled » pour la même commande atterrissant
dans des partitions différentes ne garantit pas que cancelled ne sera pas traité avant created.
RabbitMQ garantit l'ordre au sein d'une seule queue avec un seul consumer, mais cette garantie
saute dès que plusieurs consumers se font concurrence sur la même queue (le dispatch round-robin
signifie que les messages 1 et 2 pour la même entité peuvent être pris et traités par des
consumers différents en concurrence, et se terminer dans un ordre ou dans l'autre) — donc
garantir l'ordre par entité dans RabbitMQ nécessite typiquement de router tous les messages de
cette entité vers la même queue *et* un seul consumer pour celle-ci.

**Exemple :**
```java
// Pas de clé -> Kafka distribue en round-robin entre les partitions -> aucune relation d'ordre
// entre "created" et "cancelled" pour la même commande.
producer.send(new ProducerRecord<>("orders", null, createdEvent));
producer.send(new ProducerRecord<>("orders", null, cancelledEvent));

// Clé = order ID -> les deux atterrissent dans la même partition, lus dans l'ordre d'envoi par
// le seul consumer qui possède actuellement cette partition.
producer.send(new ProducerRecord<>("orders", orderId, createdEvent));
producer.send(new ProducerRecord<>("orders", orderId, cancelledEvent));
```

**Pourquoi c'est un piège :** « Kafka préserve l'ordre des messages » est vrai mais incomplet —
c'est une demi-vérité facile à répéter sans la réserve « au sein d'une partition, et seulement si
la clé est correcte », et l'écart reste invisible dans des tests à faible trafic où le round-robin
se trouve, par chance, garder les événements liés proches les uns des autres.

#### Q11. Comment choisir le nombre de partitions d'un topic Kafka, et que se passe-t-il si vous devez le changer plus tard ?
**Réponse :** Le nombre de partitions fixe le plafond du parallélisme des consumers au sein d'un
group (plus de partitions que de consumers signifie que certains consumers gèrent plusieurs
partitions ; plus de consumers que de partitions signifie que certains consumers restent
inactifs) — il faut donc choisir en fonction du débit cible et de la taille attendue du consumer
group, avec de la marge pour le scaling futur, car les partitions peuvent être *augmentées* plus
tard mais les consumers existants ne se rééquilibreront pas automatiquement pour en tirer
pleinement parti sans un redémarrage/déclencheur de rebalance, et surtout : augmenter le nombre de
partitions change le mapping clé → partition du hash pour les *nouveaux* messages, brisant la
garantie que tous les messages d'une clé donnée continuent d'atterrir dans la même partition
qu'avant — tout ce qui repose sur l'ordre au niveau de la partition pour une clé (Q10) doit
prendre en compte cette discontinuité au moment du repartitionnement. Le nombre de partitions ne
peut pas du tout être *diminué* dans Kafka sans recréer entièrement le topic.

**Exemple :**
```
$ kafka-topics.sh --alter --topic orders --partitions 12 --bootstrap-server broker:9092
# Les nouveaux messages d'une clé donnée sont maintenant hashés dans 1 des 12 partitions au lieu
# de 1 des 6 — une clé qui atterrissait toujours dans la partition 3 peut maintenant atterrir
# dans la partition 9, alors que son historique plus ancien reste dans la partition 3. Tout
# consumer qui repose sur « l'historique de cette clé est entièrement dans une seule
# partition » casse silencieusement à partir de ce moment.
```

**Pourquoi c'est un piège :** « on pourra toujours ajouter des partitions plus tard si on sous-dimensionne »
n'est vrai qu'à moitié — on peut en ajouter, mais cela change silencieusement le mapping
clé→partition pour les nouveaux messages, un vrai risque de correction facile à manquer pour tout
consumer dépendant de l'ordre, et non un levier de scaling gratuit.

#### Q12. Quels défis posent la priorité des messages ou l'équité (fairness) entre de nombreuses queues/topics ?
**Réponse :** RabbitMQ supporte des priority queues explicites (un champ de priorité par message,
le broker livrant généralement en premier les messages de plus haute priorité) — mais les priority
queues ajoutent un vrai surcoût au broker et ne garantissent pas un ordre strict sous charge,
seulement un biais en faveur des priorités élevées. Kafka n'a aucun concept de priorité intégré —
un contournement courant consiste à avoir des topics séparés par niveau de priorité, avec des
consumers qui poll le topic haute priorité plus agressivement (ou qui lui dédient une capacité de
consumer séparée) plutôt que de s'appuyer sur une quelconque priorisation dans le broker. Le défi
d'équité entre de nombreuses queues/topics pour la *même* ressource sous-jacente (p. ex. une
limite de débit d'une API aval partagée par les consumers de cinq topics différents) est un
problème réellement difficile que les brokers ne résolvent pas pour vous — il nécessite
typiquement un rate limiter applicatif ou un token-bucket partagé entre ces consumers,
indépendant de la couche de messaging.

**Exemple :**
```java
// Kafka n'a pas de priorité native — le contournement courant est un topic séparé par niveau,
// avec la capacité des consumers orientée vers le topic haute priorité.
while (true) {
    pollAndProcess(highPriorityConsumer, Duration.ofMillis(100));
    pollAndProcess(highPriorityConsumer, Duration.ofMillis(100)); // polled deux fois plus souvent
    pollAndProcess(lowPriorityConsumer, Duration.ofMillis(100));
}
```

**Pourquoi c'est un piège :** supposer que les priority queues de RabbitMQ donnent une garantie
d'ordre strict comme le ferait une liste triée — elles ne font que biaiser la livraison vers les
messages de plus haute priorité sous charge, elles ne garantissent pas qu'un message de plus
basse priorité ne passe jamais devant, donc construire une logique qui dépend d'un ordre de
priorité strict par-dessus revient à s'appuyer sur une garantie qui n'a jamais été donnée.

### Garanties de livraison et idempotence

#### Q13. Pourquoi un consumer doit-il être idempotent même quand le système de messaging revendique « exactly-once » ou « at-least-once avec dedup » ?
**Réponse :** Parce que la frontière que le broker peut garantir (message livré au consumer,
offset commité) n'est pas la même frontière que l'effet de bord réel du consumer (une écriture en
base, un email envoyé, une carte débitée) — un plantage entre « message traité » et « commit du
fait qu'il a été traité » est exactement ce qui force la redelivery avec une sémantique
at-least-once, et il n'y a aucun moyen de distinguer cela d'un véritable message dupliqué sans que
le consumer lui-même garde la trace de ce qu'il a déjà fait. L'idempotence doit résider dans la
logique propre du consumer (ou dans son modèle de données) car c'est le seul endroit qui sait
réellement, en même temps, « ai-je fait cet effet de bord » et « ai-je reçu ce message ».

**Exemple :**
```java
void handle(Message msg) {
    chargeCard(msg.orderId(), msg.amount()); // l'effet de bord se termine...
    // ...plantage juste ici, avant que le commit d'offset ci-dessous ne s'exécute...
    consumer.commitSync();
}
// Au redémarrage, le broker redélivre exactement ce message (at-least-once), et chargeCard()
// s'exécute une seconde fois — le broker a tenu toutes ses promesses ; le double débit est
// entièrement de la responsabilité du consumer, qui aurait dû l'empêcher.
```

**Pourquoi c'est un piège :** entendre « notre broker supporte exactly-once » ou « la librairie
cliente fait la dédup » et en conclure que le consumer n'a pas besoin de sa propre idempotence
est le piège — cette garantie, là où elle existe, couvre la comptabilité interne du broker
(offsets, écritures transactionnelles vers un autre topic Kafka), pas un effet de bord externe
arbitraire comme un débit de carte, qui vit entièrement en dehors de la frontière transactionnelle
du broker.

#### Q14. Quelles sont les stratégies d'idempotence courantes pour un consumer de messages ?
**Réponse :** (1) Une clé métier unique (order ID, idempotency key du producer) imposée comme
contrainte d'unicité en base sur la table dans laquelle l'effet de bord écrit — une tentative de
traitement dupliquée heurte la contrainte et est traitée comme un no-op, pas comme une erreur, ce
qui est l'approche la plus robuste car la base de données elle-même sérialise les tentatives
dupliquées concurrentes. (2) Un log/une table de messages traités indexé(e) par message ID,
vérifié(e) avant le traitement et écrit(e) atomiquement avec l'effet de bord dans la même
transaction — fonctionne pour les effets de bord qui n'ont pas naturellement de clé unique propre.
(3) Une idempotence naturelle dans l'opération elle-même quand c'est possible (`SET status =
'shipped'` est idempotent quel que soit le nombre d'exécutions ; `increment counter by 1` ne
l'est pas) — concevoir l'opération pour qu'elle soit idempotente par construction coûte moins cher
que détecter les doublons quand c'est réalisable.

**Exemple :**
```sql
-- Fragile : check-then-insert, ce sont deux instructions, pas une — deux copies redélivrées du même
-- message, traitées en concurrence par deux threads de consumer, peuvent toutes deux passer le SELECT
-- avant que l'un des INSERT ne soit commité.
SELECT 1 FROM processed_payments WHERE payment_id = ?;   -- les deux voient "not found"
INSERT INTO processed_payments (payment_id) VALUES (?);  -- les deux insèrent -> race, ou une
                                                          -- erreur de contrainte d'unicité que l'un
                                                          -- d'eux ne s'attendait pas à gérer

-- Robuste : laisser la contrainte d'unicité de la base être l'unique point de décision atomique.
INSERT INTO processed_payments (payment_id) VALUES (?)
ON CONFLICT (payment_id) DO NOTHING; -- la seconde tentative est un no-op sans risque, aucune fenêtre de race
```

**Pourquoi c'est un piège :** « vérifier si c'est déjà traité, puis traiter » semble idempotent
mais c'est un bug classique de time-of-check-to-time-of-use en cas de redelivery concurrente —
l'approche par contrainte d'unicité est préférée précisément parce qu'elle fait de la base de
données l'unique arbitre atomique au lieu de compter sur deux aller-retours séparés qui ne se
chevaucheraient jamais.

#### Q15. Que garantissent réellement respectivement les transactions Kafka et les publisher confirms de RabbitMQ ?
**Réponse :** Les transactions Kafka permettent à un producer d'écrire atomiquement dans plusieurs
partitions/topics *et* de commiter atomiquement l'offset d'un consumer en même temps qu'une sortie
produite — c'est ce qui soutient la revendication « exactly-once » de Kafka pour un pipeline
read-process-write (consommer depuis le topic A, produire vers le topic B, commiter l'offset —
le tout atomique), mais là encore, uniquement dans la frontière propre de Kafka (Q6). Les
publisher confirms dans RabbitMQ sont une garantie plus simple et plus étroite : un acquittement
asynchrone du broker indiquant qu'un message publié a été reçu et persisté en toute sécurité
(pour une queue durable) — il dit au producer « le broker l'a », et rien sur le traitement par
le consumer en aval ; sans confirms, une publication peut être perdue entre le client et le broker
sans que le producer sache qu'elle a échoué. Le piège courant : traiter les publisher confirms
comme une garantie de livraison de bout en bout alors qu'ils ne couvrent que producer→broker, pas
broker→consumer→traitement réussi.

**Exemple :**
```java
// Producer transactionnel Kafka — atomique sur produce + commit d'offset.
producer.initTransactions();
producer.beginTransaction();
producer.send(outputRecord);
producer.sendOffsetsToTransaction(offsets, consumerGroupId);
producer.commitTransaction(); // tout-ou-rien, y compris l'avancée d'offset du consumer lui-même

// Publisher confirms RabbitMQ — plus étroit : seulement « le broker a durablement ce message ».
channel.confirmSelect();
channel.basicPublish(exchange, routingKey, props, body);
channel.waitForConfirmsOrDie(5000); // ne dit rien sur le fait qu'un consumer l'ait jamais vu
```

**Pourquoi c'est un piège :** traiter « le broker a confirmé ma publication » comme « le message a
été entièrement traité de bout en bout » — les deux mécanismes s'arrêtent à la frontière propre du
broker ; ce qu'un consumer fait du message ensuite est entièrement en dehors de l'une ou l'autre
garantie.

#### Q16. Quels réglages du producer et du broker décident si un message Kafka survit à une panne de broker ?
**Réponse :** La durabilité est la combinaison de quatre réglages, et elle n'est aussi solide que
le plus faible d'entre eux. **`acks`** indique quand le producer considère une écriture comme
terminée : `0` = fire and forget, `1` = le leader de la partition l'a écrite (perdue si le leader
meurt avant que les followers ne répliquent — le message a été acquitté mais s'évanouit),
`all` = le leader *et* chaque réplique in-sync l'ont écrite. **`min.insync.replicas`**
(topic/broker) est le plancher pour « all » : avec la valeur par défaut de 1, `acks=all` peut
dégénérer en une seule copie si l'ISR se réduit au seul leader, donc le réglage de production
standard est un replication factor de 3, `min.insync.replicas=2` — tolérant la perte d'un broker
sans perdre de données ni de disponibilité, tandis qu'une seconde perte fait que les producers
reçoivent `NotEnoughReplicasException` (le système choisit délibérément la cohérence plutôt que la
disponibilité, le compromis CAP en pratique). **`unclean.leader.election.enable=false`** (le
défaut) interdit de promouvoir une réplique désynchronisée en leader ; l'activer restaure la
disponibilité après une double panne mais *jette silencieusement* les enregistrements que cette
réplique n'avait pas encore copiés. **`enable.idempotence=true`** (défaut depuis Kafka 3.0) rend
les retries du producer sûrs : le broker déduplique par producer id + numéro de séquence, donc un
retry après un timeout n'écrit pas l'enregistrement deux fois et — avec
`max.in.flight.requests.per.connection <= 5` — ne le réordonne pas non plus. Fixez un
`delivery.timeout.ms` borné pour que `send()` finisse par échouer visiblement au lieu de retenter
indéfiniment, et *vérifiez le résultat* (callback / `Future`), car un `send()` fire-and-forget qui
échoue est sinon invisible. Notez les limites : l'idempotence couvre une session de producer sur
une partition ; ce n'est pas de l'exactly-once de bout en bout (Q15, Q28), et la durabilité côté
broker dépend toujours du modèle de flush OS/réplication, pas d'un `fsync` par message.

**Exemple :**
```properties
# producer
acks=all
enable.idempotence=true
delivery.timeout.ms=120000
max.in.flight.requests.per.connection=5

# topic (créé avec)  --replication-factor 3
min.insync.replicas=2
unclean.leader.election.enable=false
```
```java
producer.send(record, (metadata, ex) -> {
    if (ex != null) failureMetrics.increment();   // ne jamais ignorer le callback
});
```

**Pourquoi c'est un piège :** « on utilise Kafka, c'est répliqué » n'est pas une réponse. Avec
`acks=1`, un plantage du leader perd des données acquittées, et avec `min.insync.replicas=1`,
`acks=all` est un placebo — les deux paraissent corrects sur tous les tests du chemin nominal et
n'échouent que lors d'une vraie panne de broker.

### Consumers, offsets et rebalancing

#### Q17. Auto-commit vs commit manuel d'offset dans un consumer Kafka — quel est le compromis ?
**Réponse :** L'auto-commit commite périodiquement le dernier offset consommé sur un timer,
indépendamment du fait que le message ait réellement été entièrement traité — simple, mais il peut
commiter l'offset d'un message encore en cours de traitement (ou qui a échoué) juste avant un
plantage, le sautant silencieusement au redémarrage (perte de données, violant at-least-once). Le
commit manuel, effectué *après* que l'effet de bord du message s'est réellement terminé avec
succès, donne correctement une sémantique at-least-once — l'offset n'avance qu'une fois le travail
fait, donc un plantage avant ce point provoque une redelivery (gérée par l'idempotence, Q13/Q14)
plutôt qu'une perte silencieuse. Le défaut au niveau senior : commit manuel après un traitement
réussi pour tout cas où perdre silencieusement un message est inacceptable, ce qui correspond à la
plupart des usages en production — la simplicité de l'auto-commit vaut rarement sa fenêtre de
perte de données.

**Exemple :**
```java
// Auto-commit : l'offset avance sur un timer, indépendamment du succès du traitement.
props.put("enable.auto.commit", "true");
props.put("auto.commit.interval.ms", "5000");
// Un plantage 4 secondes après qu'un message a été poll mais jamais réellement traité peut quand
// même avoir eu cet offset commité quelques instants avant — le message est sauté silencieusement pour toujours.

// Manuel : l'offset n'avance qu'après que l'effet de bord s'est réellement terminé.
props.put("enable.auto.commit", "false");
process(record);
consumer.commitSync(); // un plantage avant cette ligne provoque une redelivery, pas une perte silencieuse
```

**Pourquoi c'est un piège :** l'auto-commit qui « marche tout seul » dans chaque démo et chaque
test de staging à faible débit est exactement la raison pour laquelle il survit jusqu'en
production — la fenêtre d'échec est une course contre un plantage à un moment très précis, assez
rare pour ne jamais apparaître tant que le volume réel de production et l'agitation réelle de
l'infrastructure ne le rendent inévitable.

#### Q18. Comment les acknowledgments RabbitMQ et le prefetch count interagissent-ils, et pourquoi le prefetch est-il important ?
**Réponse :** Un consumer acquitte un message une fois qu'il a fini de le traiter ; un message non
acquitté sur lequel le consumer se déconnecte (ou qu'il nack explicitement) est remis en queue
pour redelivery — c'est le mécanisme at-least-once de RabbitMQ. Le **prefetch count** limite le
nombre de messages non acquittés que le broker poussera à un consumer à la fois, avant d'attendre
des acks — un prefetch de 1 signifie strictement un-à-la-fois (le plus sûr, mais sérialise le
traitement par consumer et peut gaspiller du débit sur des consumers rapides) ; un prefetch très
élevé ou illimité permet au broker de confier à un consumer un grand lot de messages, ce qui peut
affamer les autres consumers de la même queue (ils restent inactifs pendant qu'un consumer
accapare un backlog) et, si ce consumer plante, remet en queue un grand lot d'un coup,
provoquant potentiellement un pic de retraitement en thundering-herd. La réponse pratique :
régler le prefetch pour correspondre au nombre de messages qu'un seul consumer peut réellement
traiter en concurrence, et non « le plus haut possible pour le débit ».

**Exemple :**
```java
channel.basicQos(1); // strictement un-à-la-fois — le plus sûr, mais plafonne le débit propre de ce consumer

// vs.
channel.basicQos(0); // illimité — le broker peut confier à ce seul consumer un énorme lot,
// affamant tous les autres consumers de la queue et risquant un gros pic de redelivery en cas de plantage
```

**Pourquoi c'est un piège :** supposer que « prefetch plus élevé = débit plus élevé » est un gain
gratuit universel — un prefetch illimité nuit activement à l'équité au sein d'un pool de
consumers et transforme le plantage d'un seul consumer en un gros requeue thundering-herd, donc
il faut le dimensionner selon la capacité concurrente réelle par consumer, et non le maximiser
par défaut.

#### Q19. Que se passe-t-il lors d'un rebalance de consumer group Kafka, et pourquoi peut-il provoquer un traitement en double ?
**Réponse :** Un rebalance réassigne les partitions entre les consumers d'un group — déclenché par
l'arrivée d'un consumer, son départ (y compris une défaillance perçue suite à un heartbeat
manqué), ou un changement du nombre de partitions. Pendant un rebalance, la consommation est en
pause le temps que les partitions soient réassignées, et surtout : un consumer qui était en train
de traiter un lot de messages au démarrage du rebalance, et n'avait pas encore commité son offset
pour ce lot, verra cette même partition (et ces mêmes messages non commités) confiée à un autre
consumer — qui les retraite alors depuis le dernier offset *commité*, dupliquant tout ce que le
premier consumer avait déjà fait avant que le rebalance ne l'interrompe. C'est exactement pourquoi
les consumers ont besoin d'idempotence (Q13) quelle que soit la rigueur de la stratégie de commit
d'offset — les rebalances font de la redelivery at-least-once un événement de routine, pas un cas
limite.

**Exemple :**
```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    for (ConsumerRecord<String, String> r : records) {
        process(r); // si un rebalance se déclenche ici, en plein milieu de ce lot...
    }
    consumer.commitSync(); // ...cette ligne ne s'exécute jamais pour les enregistrements déjà traités
}
// Le consumer réassigné reprend depuis le dernier offset *commité*, retraitant tout ce que
// cette instance avait déjà géré depuis son précédent commitSync() réussi.
```

**Pourquoi c'est un piège :** traiter un rebalance comme un cas limite rare qu'on peut ignorer —
en réalité, tout déploiement, événement d'autoscaling ou heartbeat manqué en déclenche un, ce qui
fait de la redelivery en double un événement de routine que l'idempotence (Q13/Q14) doit gérer
inconditionnellement, et non un risque de queue de distribution qu'on balaie d'un haussement
d'épaules.

#### Q20. Pourquoi un consumer Kafka *lent* — et non planté — peut-il déclencher des rebalances sans fin, et quels réglages le contrôlent ?
**Réponse :** Un consumer doit rappeler `poll()` dans les **`max.poll.interval.ms`** (5 minutes par
défaut) ; les heartbeats sont envoyés par un *thread d'arrière-plan séparé* (régi par
`session.timeout.ms` et `heartbeat.interval.ms`), donc un consumer peut sembler parfaitement sain
au broker alors que sa boucle de traitement est bloquée. Si le temps entre deux appels à `poll()`
dépasse l'intervalle — parce qu'un lot de `max.poll.records` (500 par défaut) enregistrements prend
chacun quelques secondes, ou qu'un appel reste suspendu sur un service aval — le consumer est
considéré comme défaillant, retiré du group et ses partitions réassignées (Q19). Quand il termine
enfin, son commit d'offset échoue avec `CommitFailedException`, le lot est redélivré au nouveau
propriétaire, *ce* consumer est tout aussi lent, se fait éjecter à son tour, et le group entre
dans une **boucle de rebalance** : la consommation stagne, le lag grandit et les doublons se
multiplient. Corrections, dans l'ordre : réduire le lot (`max.poll.records`) pour que le travail
d'un poll tienne confortablement dans l'intervalle ; poser des timeouts sur chaque appel aval pour
que rien ne puisse rester suspendu ; n'augmenter `max.poll.interval.ms` qu'en dernier recours
(cela ralentit la détection d'un consumer réellement bloqué) ; utiliser `pause()`/`resume()` ou
confier les enregistrements à un worker pool tout en continuant à poll (en ne commitant
soigneusement que les offsets terminés) ; et réduire le *coût* de chaque rebalance avec le
`CooperativeStickyAssignor` (incrémental, sans stop-the-world) et le static membership
(`group.instance.id`) pour qu'un rolling restart ne rebrasse pas tout.

**Exemple :**
```properties
max.poll.records=50                 # 50 enregistrements * ~2s chacun = ~100s, bien en dessous de l'intervalle
max.poll.interval.ms=300000
session.timeout.ms=45000
heartbeat.interval.ms=15000
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```
```java
// Mauvais : 500 enregistrements x 3s chacun = 1500s entre deux polls -> le consumer est évincé à chaque fois.
for (ConsumerRecord<String, Order> r : consumer.poll(Duration.ofSeconds(1))) {
    slowRemoteCall(r.value());
}
```

**Pourquoi c'est un piège :** les heartbeats continuent de fonctionner, donc les dashboards disent
que le consumer est « vivant » alors qu'il est évincé à répétition ; et le réflexe standard —
augmenter `max.poll.interval.ms` — ne fait que masquer le handler lent jusqu'à ce que la charge
monte.

#### Q21. Que se passe-t-il quand un consumer n'arrive pas à suivre le rythme d'arrivée des messages, et comment le gérer ?
**Réponse :** Un backlog se construit — dans Kafka, le consumer lag (l'écart entre le dernier
offset et l'offset commité du consumer) grandit ; dans RabbitMQ, la profondeur de la queue
grandit, et au-delà d'un seuil mémoire/disque configuré, RabbitMQ peut déclencher une alarme de
flow-control qui bloque entièrement les publishers (une mesure de protection qui transforme un
problème de consumer lent en problème de producer bloqué si on ne le traite pas). Pour le gérer :
scaler les consumers horizontalement (plus de consumers jusqu'au nombre de partitions dans Kafka,
ou plus de consumers sur la même queue RabbitMQ), s'assurer que c'est bien le temps de traitement
par message qui est le goulot traité plutôt que d'ajouter des consumers par-dessus un appel aval
lent, ou appliquer délibérément du backpressure — le prefetch de RabbitMQ (Q18) est lui-même un
mécanisme de backpressure, limitant ce qu'un broker poussera en avance par rapport au rythme réel
de traitement d'un consumer.

**Exemple :**
```
$ kafka-consumer-groups.sh --bootstrap-server broker:9092 --describe --group billing-group
TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
orders  0          482910          511200          28290
orders  1          483012          511344          28332
```

**Pourquoi c'est un piège :** ajouter réflexivement des consumers sans d'abord vérifier si le
nombre de partitions est déjà le plafond (Q11) ou si le temps de traitement par message lui-même a
régressé — jeter davantage de consumers sur un problème qui est en réalité limité par les
partitions ou par la latence ne change rien.

### Gestion des échecs

#### Q22. Qu'est-ce qu'une dead-letter queue, et pourquoi un système de production en a-t-il besoin ?
**Réponse :** Une dead-letter queue (DLQ) est l'endroit où vont les messages après avoir échoué au
traitement au-delà d'une limite de retry configurée, ou expiré, ou été explicitement rejetés sans
requeue — au lieu d'être retentés indéfiniment (bloquant la queue derrière un message qui ne
pourra jamais réussir, Q23) ou silencieusement jetés (perdant l'événement sans aucune trace). Elle
existe pour qu'un message « poison pill » ne bloque pas le traitement de tous les messages
derrière lui, tout en préservant le message en échec pour investigation, retraitement manuel ou
alerte, plutôt que les deux mauvaises alternatives du retry infini ou de la perte silencieuse.

**Exemple :**
```java
Map<String, Object> args = new HashMap<>();
args.put("x-dead-letter-exchange", "dlx");
args.put("x-dead-letter-routing-key", "orders.dead");
args.put("x-max-length", 100_000); // filet de sécurité supplémentaire optionnel
channel.queueDeclare("orders-queue", true, false, false, args);
// Une fois qu'un consumer a nack le même message au-delà d'un nombre de retries suivi, le router
// vers "dlx" au lieu de le remettre encore une fois dans "orders-queue".
```

**Pourquoi c'est un piège :** considérer « on a configuré une DLQ » comme la tâche terminée — une
DLQ avec routage de retry mais sans consumer ni alerte pour la surveiller n'est qu'une version plus
lente et plus discrète de la perte de données exacte qu'elle était censée prévenir (S9).

#### Q23. Qu'est-ce qu'un message « poison pill », et comment en gérer un sans bloquer toute la queue ?
**Réponse :** Un poison pill est un message qui ne peut jamais être traité avec succès — données
malformées, bug déclenché par ce payload spécifique, référence à une entité depuis supprimée —
donc chaque tentative de redelivery échoue à l'identique et, sans limite, il est retenté
indéfiniment. Sur RabbitMQ, une boucle illimitée de requeue-on-nack signifie que ce message (et,
si l'ordre/le prefetch le maintient en tête, tout ce qui est derrière) n'avance jamais. La
correction : configurer un nombre maximal de livraisons/retries (le suivi via le header `x-death`
de RabbitMQ, ou un compteur de retries applicatif), et une fois dépassé, router le message vers
une dead-letter queue (Q22) au lieu de le remettre encore en queue — cela permet au traitement de
continuer au-delà du poison pill tout en le préservant pour investigation.

**Exemple :**
```java
int deathCount = getXDeathCount(delivery); // lit le compteur du header x-death de RabbitMQ
if (deathCount >= MAX_RETRIES) {
    channel.basicPublish("dlx", "orders.dead", null, delivery.getBody()); // dead-letter manuel
    channel.basicAck(deliveryTag, false); // ack de l'original pour qu'il ne soit pas remis en queue
} else {
    channel.basicNack(deliveryTag, false, true); // requeue pour une nouvelle tentative
}
```

**Pourquoi c'est un piège :** « il suffit de nack et requeue à chaque échec » est le réflexe par
défaut, et il est correct pour un échec transitoire (un timeout aval) mais catastrophique pour un
poison pill — sans compteur borné, il est indiscernable d'une boucle de retry infinie qui ne laisse
jamais la queue se vider.

#### Q24. Comment concevoir des retries avec backoff pour un consumer Kafka (ou RabbitMQ) sans bloquer le flux ?
**Réponse :** Retenter *sur place* est l'option la plus simple et elle convient pour un court
incident transitoire : dormir et retenter le même enregistrement quelques fois. Mais dans Kafka
une partition est une séquence stricte, donc un retry sur place **bloque tout ce qui est derrière
lui** — un enregistrement en échec avec un backoff de 10 minutes bloque toute la partition
(head-of-line blocking), et de longs sleeps risquent aussi l'éviction `max.poll.interval.ms` de la
Q20. Les **retries non bloquants** déplacent l'enregistrement en échec ailleurs et laissent le
topic principal continuer : le publier dans une chaîne de *retry topics* avec des délais
croissants (`orders-retry-5s`, `orders-retry-1m`, `orders-retry-10m`) dont les consumers attendent
jusqu'au timestamp de l'enregistrement plus le délai, et après la dernière tentative l'envoyer
vers un dead-letter topic (Q22). RabbitMQ fait de même avec un TTL par queue et un dead-letter
exchange qui route les messages expirés vers l'exchange de travail (une delay queue) — ou le
plugin delayed-message. Les coûts : **l'ordre n'est plus préservé** pour l'enregistrement retenté
(les messages suivants de la même clé le dépassent), donc c'est acceptable uniquement quand les
handlers sont indépendants de l'ordre ou vérifient les versions ; il y a plus de topics/queues à
exploiter ; et les headers ont besoin d'un compteur de tentatives. Quel que soit le mécanisme, la
politique compte plus que la plomberie : ne retenter que les erreurs **transitoires** (timeouts,
503) et envoyer les **permanentes** (échec de validation, poison pill, Q23) directement au DLT ;
utiliser un **backoff exponentiel avec jitter** pour que de nombreux consumers ne retentent pas
en cadence (S17) ; plafonner les tentatives ; et garder les handlers idempotents (Q13) puisque
chaque retry est un doublon potentiel.

**Exemple :**
```java
@RetryableTopic(
    attempts = "4",
    backoff = @Backoff(delay = 5_000, multiplier = 3.0, random = true),   // ~5s, ~15s, ~45s + jitter
    include = TransientDownstreamException.class,                         // ne retenter que les erreurs transitoires
    dltStrategy = DltStrategy.FAIL_ON_ERROR)
@KafkaListener(topics = "orders", groupId = "billing")
void handle(OrderEvent event) { billing.charge(event); }

@DltHandler
void deadLetter(OrderEvent event) { alerts.page("order " + event.id() + " exhausted retries"); }
```

**Pourquoi c'est un piège :** « il suffit de retenter 3 fois » semble complet. Les questions de
suivi sont le head-of-line blocking, la perte d'ordre, retenter indéfiniment des erreurs non
retentables, et la retry storm synchronisée qui transforme une petite panne en grosse panne.

### Patterns et schémas

#### Q25. Pattern saga — orchestration vs choreography — quelle est la vraie différence et le compromis ?
**Réponse :** Les deux gèrent une transaction distribuée entre services sans two-phase-commit
(qui ne scale pas entre services appartenant à des équipes indépendantes) en la découpant en une
séquence de transactions locales, chacune avec une transaction compensatoire correspondante pour
l'annuler si une étape ultérieure échoue. **Orchestration** : un coordinateur central appelle
explicitement chaque étape en séquence et appelle explicitement les compensations dans l'ordre
inverse en cas d'échec — le flux se voit facilement en un seul endroit (lisible, debuggable,
testable comme une unité) mais introduit un composant central qui doit connaître chaque
participant, un point unique potentiel de logique de coordination à maintenir. **Choreography** :
chaque service réagit aux événements de l'étape précédente et émet son propre événement pour la
suivante, sans coordinateur central — entièrement découplé, aucun service ne connaît le flux
complet, mais c'est aussi la faiblesse : comprendre ou debugger le flux de bout en bout signifie
tracer les événements dans les logs de chaque service, et il n'y a aucun endroit unique qui
« possède » la logique de retry/compensation pour toute la saga. L'orchestration tend à
l'emporter quand le nombre d'étapes et le besoin de visibilité augmentent ; la choreography tend à
l'emporter pour des flux plus simples et plus faiblement couplés.

**Exemple :**
```java
// Orchestration : un seul endroit prend chaque décision et connaît tout le flux.
try {
    paymentClient.authorize(orderId);
    inventoryClient.reserve(orderId);
    shippingClient.schedule(orderId);
} catch (InventoryUnavailableException e) {
    paymentClient.voidAuthorization(orderId); // compensation explicite, dans l'ordre inverse
    orderService.markFailed(orderId);
}
// Choreography : aucun bloc de ce genre n'existe nulle part — chaque service réagit à l'événement
// du service précédent et émet le sien ; tracer ce même échec signifie lire les logs de
// trois services distincts, sans aucun endroit unique montrant toute la séquence.
```

**Pourquoi c'est un piège :** « la choreography est plus découplée donc c'est toujours la
meilleure architecture » ignore que le découplage a un vrai coût — la debuggabilité — une réponse
senior choisit selon la complexité du flux et le besoin réel de l'équipe en visibilité centralisée,
et non en faisant du découplage une vertu inconditionnelle.

#### Q26. Qu'est-ce que le pattern outbox, et quel problème résout-il ?
**Réponse :** Le problème : un service qui doit à la fois écrire dans sa propre base *et* publier
un événement sur cette écriture (p. ex. sauvegarder une commande, puis publier `OrderCreated`) ne
peut pas faire les deux atomiquement comme deux opérations séparées — un plantage entre le commit
en base et la publication du message laisse la base mise à jour mais l'événement jamais envoyé
(ou, dans l'autre ordre, un événement publié pour une écriture en base qui a ensuite échoué au
commit), et ni les transactions de base de données ni les transactions de message broker ne
couvrent les deux systèmes par défaut. Le pattern outbox le résout en écrivant l'événement dans
une table « outbox » dans la *même* transaction de base de données que l'écriture métier — l'atomicité
est garantie car c'est une seule transaction dans une seule base — et un processus séparé (un job
de polling, ou un change-data-capture de style Debezium lisant le write-ahead log de la base) lit
les nouvelles lignes outbox et les publie réellement vers le broker, en les marquant comme
envoyées. Cela donne une publication d'événement effectivement-exactly-once liée à l'écriture
métier, au prix d'un petit délai de publication et de la table outbox/infrastructure de relais
supplémentaire.

**Exemple :**
```sql
BEGIN;
INSERT INTO orders (id, status) VALUES ('123', 'created');
INSERT INTO outbox (id, topic, payload, published)
    VALUES (gen_random_uuid(), 'orders', '{"orderId":"123"}', false);
COMMIT;
-- Un processus relais séparé poll `WHERE published = false`, publie vers le broker, puis
-- marque la ligne comme publiée — l'écriture métier et l'« intention de publier » ne peuvent jamais
-- diverger, car elles ont été commitées comme une seule unité atomique.
```

**Pourquoi c'est un piège :** « résoudre » le problème du dual-write en publiant l'événement
d'abord et en écrivant en base ensuite (ou l'inverse) avec un try/catch autour de l'appel qui vient
en second ne fait que déplacer *le sens* dans lequel l'échec peut se produire — cela ne supprime pas
la non-atomicité fondamentale ; seul écrire les deux dans une seule transaction de base de données
comble réellement l'écart.

#### Q27. Pourquoi l'évolution de schéma compte-t-elle pour les messages, et quels outils la traitent ?
**Réponse :** Un producer et ses consumers sont des services déployés indépendamment — un producer
qui ajoute un champ obligatoire, renomme un champ ou change un type peut casser silencieusement
chaque consumer qui désérialise le message à l'ancienne, et contrairement à une API synchrone où un
client recevrait une erreur immédiate au prochain appel, un schéma de message cassé peut rester
dans le topic/la queue en faisant échouer rétroactivement chaque consumer, ou pire, être
désérialisé de façon incorrecte sans aucune erreur. Les schema registries (Confluent Schema
Registry avec Avro ou Protobuf étant l'association courante pour Kafka) imposent des règles de
compatibilité au moment de la publication — un producer ne peut pas publier un message au schéma
incompatible sans un changement explicite du mode de compatibilité — et supportent des patterns
d'évolution sûrs (ajouter un champ optionnel avec une valeur par défaut est sûr ; supprimer ou
renommer un champ obligatoire ne l'est pas, sans période de transition). Même sans schema registry
formel, la discipline qu'il impose (changements uniquement rétrocompatibles, nouveaux champs
optionnels avec valeurs par défaut, ne jamais réaffecter un champ) vaut la peine d'être appliquée
manuellement avec du JSON simple.

**Exemple :**
```json
// Rétrocompatible : le nouveau champ est optionnel avec une valeur par défaut — les anciens
// consumers qui lisent les nouveaux messages ne le voient simplement pas ; les nouveaux consumers
// qui lisent les anciens messages obtiennent la valeur par défaut.
{"name": "promoCode", "type": ["null", "string"], "default": null}

// Cassant : supprimer un champ obligatoire sans valeur par défaut — chaque consumer qui l'attend
// encore lève une erreur de désérialisation dès le message suivant, silencieusement, en production.
```

**Pourquoi c'est un piège :** « on préviendra simplement chaque équipe consumer du changement »
ne passe pas à l'échelle — les consumers se déploient indépendamment et à leur propre rythme, donc
une règle de compatibilité imposée mécaniquement (un schema registry rejetant un schéma
incompatible à la publication) est la seule version qui ne finit pas par reposer sur quelqu'un se
souvenant d'un message Slack.

## 🔴 Expert / Ouvert

### Garanties de livraison

#### Q28. Concevez un consumer de paiement à traitement exactly-once sur Kafka. Détaillez toute l'approche.
Partez du principe que l'« exactly-once » pour l'effet de bord réel (débiter une carte, créditer
un solde) doit être conçu au niveau applicatif, et non supposé acquis grâce au broker (Q6/Q13).
Concrètement : le consumer lit un message de demande de paiement, et au sein d'une seule
transaction de base de données, (1) vérifie une contrainte d'unicité sur l'idempotency key du
message (l'ID de la demande de paiement) dans une table `processed_payments` — si elle existe
déjà, la transaction court-circuite en no-op, gérant sans risque une redelivery due à un rebalance
ou à un retry ; (2) si c'est nouveau, effectue la vraie mise à jour de solde/ledger ; (3) insère
la ligne de l'idempotency key ; le tout comme une seule transaction de base atomique, de sorte
qu'un plantage à n'importe quel moment commite soit les trois intégralement, soit aucun. Ce n'est
qu'*après* le commit de cette transaction que le consumer commite son offset Kafka (commit manuel,
Q17) — donc un plantage entre le commit en base et le commit d'offset provoque une redelivery,
qui est absorbée sans risque par la vérification d'unicité de l'étape (1) lors du rejeu. Cela donne
un traitement effectivement-exactly-once de l'effet de bord métier, construit à partir d'une
garantie de livraison at-least-once plus un consumer idempotent et transactionnellement sûr — ce
qui est le pattern général, pas quelque chose de spécifique aux paiements.

### Workflows et conception d'événements

#### Q29. Concevez une saga pour commande → paiement → réservation de stock → expédition. Choisissez orchestration ou choreography et expliquez les compensations.
L'orchestration est le meilleur choix ici précisément parce que le flux a une chaîne de
dépendances linéaire claire et que l'échec à n'importe quelle étape a une annulation bien définie
et spécifique — exactement le cas où la visibilité d'un coordinateur central justifie son coût.
Flux : l'orchestrateur crée la commande (pending), appelle le paiement pour autoriser (transaction
locale, compensable par un remboursement/void), appelle le stock pour réserver (compensable en
libérant la réservation), puis appelle l'expédition pour planifier l'envoi (compensable en
annulant l'expédition) — et enfin marque la commande confirmée. En cas d'échec à n'importe quelle
étape, l'orchestrateur invoque les transactions compensatoires de chaque étape déjà réussie, dans
l'ordre inverse : si la réservation de stock échoue (rupture de stock), il déclenche un
void/remboursement du paiement et marque la commande en échec, sans jamais appeler l'expédition.
Le point de conception le plus délicat est que les compensations doivent elles-mêmes pouvoir être
retentées sans risque et être idempotentes (un appel de remboursement qui timeout et est retenté ne
doit pas rembourser deux fois) — le pattern saga ne supprime pas le besoin d'idempotence, il ajoute
simplement une couche de coordination par-dessus des services qui en ont toujours individuellement
besoin (Q13 s'applique à chaque étape et à chaque compensation).

#### Q30. Comparez dual writes, outbox par polling et CDC basé sur les logs (Debezium) pour publier des événements de façon fiable. Quand utiliser lequel ?
Un **dual write** — commiter en base, puis publier vers le broker dans la même méthode — est
l'anti-pattern que l'outbox existe pour empêcher (Q26) : un plantage ou une panne du broker entre
les deux étapes perd l'événement ou en publie un pour une écriture annulée, et aucune logique de
retry ne peut dire lequel des deux cas s'est produit. L'**outbox par polling** écrit l'événement
dans une table `outbox` dans la transaction métier et un relais poll les lignes non publiées :
simple, sans infrastructure supplémentaire, et facile à raisonner ; ses coûts sont la latence et
la charge du polling, la concurrence entre plusieurs instances de relais (utiliser
`FOR UPDATE SKIP LOCKED`, module 3 Q17), le maintien de l'ordre par aggregate, la suppression des
lignes publiées, et une publication at-least-once (un plantage entre la publication et « marquer
envoyé » duplique). Le **CDC basé sur les logs** — Debezium lisant le WAL de PostgreSQL via un
logical replication slot, idéalement avec l'outbox event router — supprime le polling : les
événements sont capturés dans l'ordre de commit avec une faible latence et sans charge de requêtes
supplémentaire, et le même mécanisme peut aussi streamer les changements de tables ordinaires vers
d'autres systèmes. Ses coûts sont opérationnels : un déploiement Kafka Connect à faire tourner et
à surveiller, une dépendance à la configuration de la base (`wal_level=logical`, permissions), la
gestion du snapshotting et des changements de schéma, et surtout le **replication slot** : si le
connecteur est arrêté ou lent, PostgreSQL retient le WAL pour ce slot *indéfiniment* et peut
remplir le disque de la base (S22), donc `max_slot_wal_keep_size`, des alertes de lag et un
runbook « connecteur arrêté » testé sont obligatoires. Dans toutes les variantes la livraison est
at-least-once, donc les consumers restent idempotents (Q13). Ma règle : commencer avec l'outbox par
polling pour un volume modeste et peu de services ; passer à Debezium quand la charge ou la
latence du polling devient le goulot, ou quand de nombreux systèmes aval ont besoin de flux de
changements — et ne jamais publier directement depuis le code métier.

#### Q31. Un événement doit-il porter les données, ou seulement dire que quelque chose s'est produit ? Comparez notification events, event-carried state transfer et event sourcing.
Ce sont trois contrats différents, et les confondre est une source fréquente de couplage. Un
**notification event** est léger — `{"orderId": 123, "type": "OrderPlaced"}` — et les consumers
rappellent le service propriétaire pour les détails. Il garde les événements petits et le
propriétaire faisant autorité, mais recrée un *couplage à l'exécution* (le consumer a besoin que
le producer soit up, ajoute de la charge, et peut lire un état plus récent que celui décrit par
l'événement). L'**event-carried state transfer** met dans l'événement les données dont les
consumers ont besoin (ou publie le nouvel état complet de l'entité, idéal pour un topic compacté),
de sorte que les consumers construisent leurs propres read models locaux et ne rappellent jamais :
les services restent autonomes et rapides et survivent à une panne du producer, au prix
d'événements plus gros, d'un schéma qui devient un contrat public (Q27), de données dupliquées
*à terme* cohérentes, et du risque de fuite de champs que les consumers ne devraient pas avoir.
L'**event sourcing** est une idée entièrement différente : les événements *sont* la source de
vérité dans le service propriétaire — l'état courant est un fold sur le log append-only de
`OrderPlaced`, `ItemAdded`, `OrderCancelled` — offrant une piste d'audit complète, du time travel
et la capacité de reconstruire n'importe quelle projection, mais exigeant un vrai investissement
dans le versioning/upcasting d'événements, les snapshots pour les longs streams, les projections et
CQRS, et la « suppression » (RGPD) devient difficile car le log est immuable. Ce n'est pas une
échelle qu'on gravit : la plupart des systèmes veulent de l'event-carried state transfer entre
services et du CRUD ordinaire (plus un outbox, Q26) à l'intérieur ; les notification events
conviennent quand les payloads sont gros ou sensibles ; l'event sourcing convient aux domaines où
l'historique *est* le produit (ledgers, réservations, trading). Je choisirais par frontière, et
nommerais explicitement la cohérence que chaque consumer peut tolérer.

### Décisions de plateforme

#### Q32. Quand migrer de RabbitMQ vers Kafka est-il réellement justifié, et que coûte cette migration ?
Justifié quand le besoin moteur est devenu l'un de ceux-ci : une capacité de
replay/retraitement que RabbitMQ ne peut structurellement pas fournir (Q9) ; un débit qui a
dépassé ce que la comptabilité par message du broker RabbitMQ gère bien ; ou plusieurs consumer
groups indépendants qui ont réellement besoin de lire le même flux d'événements à leur propre
rythme et avec leur propre rétention, plutôt qu'un message allant à un seul consumer. Non justifié
par « Kafka est plus populaire/scalable » dans l'abstrait — si l'usage réel est de simples task
queues, du request/reply ou du routage à débit modéré avec une logique d'exchange complexe,
RabbitMQ reste un meilleur choix architectural et une migration en bloc ajoute un vrai coût sans
bénéfice correspondant. La migration elle-même coûte plus que le remplacement d'une librairie
cliente : les consumers construits autour du modèle ack-and-gone de RabbitMQ doivent être repensés
autour de la gestion des offsets et du retraitement idempotent (Q13) comme préoccupation de premier
ordre, la conception des partitions/clés doit être choisie délibérément selon les besoins d'ordre
(Q10), et le modèle opérationnel (la gestion propre du cluster Kafka, ZooKeeper ou KRaft, le
rééquilibrage des partitions) est une charge opérationnelle réellement différente — c'est un
changement architectural de plusieurs trimestres pour un système de taille réelle, pas un
remplacement à l'identique, et il doit être cadré et justifié comme tel plutôt que fait parce que
Kafka est le choix tendance.

#### Q33. Comment répliqueriez-vous des données Kafka entre régions, et à quoi devez-vous renoncer ?
Les clusters Kafka sont conçus pour vivre dans une seule région (liens à faible latence entre
brokers), donc le cross-region se fait via un **replicator** qui consomme depuis le cluster A et
produit vers le cluster B : MirrorMaker 2 (construit sur Kafka Connect), Confluent Cluster Linking
ou équivalents. Le principal choix de conception est la topologie. **Active-passive** : la région
A sert le trafic, B détient une copie et prend le relais en cas de désastre — simple à raisonner,
mais la réplication est *asynchrone*, donc le recovery point (RPO, module 7 Q21) est tout ce qui
n'avait pas encore été mirroré, et le failover implique de repointer producers et consumers et de
choisir où les consumers reprennent, puisque les offsets dans B ne sont *pas* les mêmes nombres
que dans A (MM2 traduit les offsets commités, imparfaitement ; l'hypothèse sûre est « reprendre
légèrement plus tôt et dédupliquer », c.-à-d. des consumers idempotents, Q13). **Active-active** :
chaque région produit localement et mirrore vers l'autre, avec des topics préfixés par l'origine
(`us.orders`, `eu.orders`) pour éviter les boucles de réplication ; la latence est excellente, mais
la même entité peut maintenant être mise à jour dans deux régions à la fois, donc il faut une
stratégie de conflit (propriété de partition par clé entité/région, last-writer-wins par version,
ou merge de style CRDT) — le compromis CAP (module 7 Q8) appliqué à votre flux d'événements.
**Stretch cluster** (un cluster sur 3 régions, `acks=all` avec rack awareness) donne un RPO nul au
prix d'une latence cross-region sur *chaque* écriture et d'une exigence stricte d'un RTT
inter-région faible et stable — approprié pour un cœur de paiements, pas pour de la télémétrie à
gros volume. Décidez aussi quoi répliquer (tous les topics ne le méritent pas), comment garder les
schémas et les ACLs synchronisés, et répétez le failover : un runbook non testé n'est pas un plan
de DR. Mon défaut : active-passive avec des consumers idempotents et un exercice de failover
planifié ; active-active seulement quand le métier a réellement besoin d'écritures locales dans les
deux régions et peut définir la propriété des entités.

## 🎯 Scénarios réels

### S1. Un client est débité deux fois pour la même commande
- **Symptômes :** Un consumer de traitement de paiement traite occasionnellement deux fois le même
  message order-placed, entraînant un double débit, signalé par des clients ou détecté par la
  réconciliation.
- **Diagnostic :** Vérifier si le consumer de paiement est idempotent (Q13/Q14) — la cause racine la
  plus courante est un consumer qui traite l'effet de bord *puis* commite l'offset, mais plante
  ou timeout entre les deux, provoquant une redelivery que le consumer n'a aucun moyen de
  reconnaître comme un doublon.
- **Exemple :**
  ```java
  // Le pattern de bug auquel remonte cet incident :
  chargeCard(order.customerId(), order.amount()); // se termine — le client est débité
  consumer.commitSync();                          // plantage juste ici, avant l'exécution de cette ligne
  // Le redémarrage redélivre le même message ; chargeCard() s'exécute à nouveau sans que rien ne
  // le reconnaisse comme un doublon.
  ```
- **Résolution :** Ajouter une contrainte d'unicité sur l'idempotency key du paiement/de la
  commande au niveau de la base, pour qu'une tentative de traitement dupliquée soit rejetée ou
  soit un no-op sans risque au lieu de débiter à nouveau ; émettre des remboursements pour tous les
  clients déjà débités en double à cause de cette faille.
- **Prévention :** Traiter l'idempotence comme un élément de conception obligatoire pour tout
  consumer ayant un effet de bord externe difficile à annuler (débiter de l'argent, envoyer une
  notification irréversible) — et non comme une étape de durcissement optionnelle ajoutée après un
  incident.

### S2. Les messages s'accumulent dans une queue et cessent complètement d'être traités
- **Symptômes :** La profondeur de la queue grandit régulièrement ; les consumers tournent et
  semblent sains, mais le débit est tombé à zéro ou presque.
- **Diagnostic :** Vérifier si le message en tête de queue est un poison pill (Q23) — un message
  malformé ou déclenchant un bug qui échoue à chaque fois et, sans limite de retry, est redélivré
  et échoue à nouveau en boucle, bloquant la progression de tout ce qui est derrière si l'ordre ou
  le prefetch le maintient en tête.
- **Exemple :**
  ```
  $ rabbitmqctl list_queues name messages messages_unacknowledged
  orders-queue   48213   1
  ```
  Une profondeur de queue qui grandit régulièrement alors que `messages_unacknowledged` reste figé
  à exactement `1` est la signature d'un message redélivré et qui échoue à nouveau en boucle, sans
  jamais se vider, pendant que tout ce qui est derrière attend.
- **Résolution :** Identifier manuellement et retirer/rerouter le message bloqué spécifique pour
  débloquer la queue immédiatement, puis ajouter un nombre maximal de retries avec dead-lettering
  pour que cela ne puisse plus se reproduire silencieusement.
- **Prévention :** Chaque consumer a besoin d'un nombre de retries borné et d'une cible DLQ
  configurés dès le départ — « retenter indéfiniment » ne devrait jamais être le comportement par
  défaut du traitement de messages.

### S3. Le consumer lag Kafka grandit régulièrement et ne se résorbe pas, même pendant les périodes de faible trafic
- **Symptômes :** L'écart entre le dernier offset produit et l'offset commité du consumer group
  continue de s'élargir sur plusieurs jours, y compris pendant les périodes où le volume de
  production de messages est normal, voire faible.
- **Diagnostic :** Cela signifie que le débit de traitement est structurellement inférieur au débit
  de production, et non un pic temporaire — vérifier si le nombre de consumers correspond au nombre
  de partitions (plus de consumers ne peuvent pas aider si les partitions sont le goulot, Q11), si
  le temps de traitement de chaque message a régressé (un appel aval lent ajouté sur le hot path du
  consumer), ou si une boucle de rebalance (Q19, possiblement due à des consumers qui redémarrent
  fréquemment) interrompt à répétition la progression.
- **Exemple :**
  ```
  $ kafka-consumer-groups.sh --describe --group billing-group --bootstrap-server broker:9092
  TOPIC   PARTITION  LAG
  orders  0          182004
  orders  1          179664
  ```
  Un lag qui monte régulièrement sur *toutes* les partitions, et pas seulement une, indique un
  déficit de débit structurel (trop peu de consumers, ou une régression de latence par message)
  plutôt qu'un pic transitoire localisé à une partition.
- **Résolution :** Scaler les consumers jusqu'au nombre de partitions si sous-dimensionné,
  profiler et corriger le temps de traitement par message si c'est le vrai goulot, ou augmenter le
  nombre de partitions (en acceptant la discontinuité du mapping de clés de la Q11) si le topic
  lui-même est sous-partitionné pour le débit requis.
- **Prévention :** Alerter sur la tendance du consumer lag (et pas seulement sur un seuil absolu)
  pour qu'un ralentissement structurel soit détecté quand il n'est encore qu'un petit écart, et
  non après des jours de backlog non traité.

### S4. RabbitMQ se met à bloquer tous les publishers sur l'ensemble du broker
- **Symptômes :** La publication échoue ou se bloque soudainement sur des queues apparemment sans
  rapport, et pas seulement celle qui s'accumulait réellement.
- **Diagnostic :** Vérifier une alarme mémoire ou disque — le flow control de RabbitMQ bloque
  *tous* les publishers à l'échelle du broker dès que les seuils mémoire ou disque configurés sont
  dépassés, comme mesure de protection contre l'épuisement total des ressources ; une seule queue
  qui s'accumule parce que ses consumers sont bloqués peut être la vraie cause racine même si le
  symptôme paraît concerner tout le broker.
- **Exemple :**
  ```
  2024-03-11 09:41:02 [warning] <0.612.0> vm_memory_high_watermark set. Memory used: 6.42GB Limit: 6.40GB
  2024-03-11 09:41:02 [warning] <0.612.0> Blocking all publishers until this alarm clears...
  ```
- **Résolution :** Identifier et corriger le ou les consumers réellement bloqués à l'origine de la
  queue qui s'accumule, libérer du disque/de la mémoire, et une fois sous le seuil d'alarme, la
  publication reprend automatiquement — mais scaler les consumers ou ajouter des limites de
  longueur de queue (avec dead-lettering) empêche cette même queue de déclencher à nouveau ceci.
- **Prévention :** Définir des policies de longueur max par queue avec dead-lettering pour qu'une
  queue qui s'emballe se dégrade proprement (en rejetant/dead-letterant les nouveaux messages) au
  lieu d'épuiser les ressources de tout le broker et de faire tomber tous les publishers.

### S5. Un événement « cancel order » est traité avant l'événement « create order » correspondant, laissant la commande active
- **Symptômes :** Une commande créée puis immédiatement annulée se retrouve active (create traité
  après cancel) au lieu d'annulée, de façon intermittente, pour une petite fraction des commandes.
- **Diagnostic :** Vérifier la clé de partition/routage utilisée pour ces événements (Q10) — si les
  événements create et cancel de la même commande ne sont pas garantis d'atterrir dans la même
  partition (Kafka) ou d'être traités par le même consumer unique (RabbitMQ), il n'y a aucune
  garantie d'ordre entre eux, et sous charge ils peuvent être traités dans le désordre.
- **Exemple :**
  ```java
  // Publication sans clé -> round-robin entre les partitions -> aucune garantie d'ordre.
  producer.send(new ProducerRecord<>("orders", null, createdEvent));
  producer.send(new ProducerRecord<>("orders", null, cancelledEvent));
  ```
- **Résolution :** Clé des deux événements sur l'order ID pour qu'ils atterrissent
  garantis dans la même partition Kafka (traités dans l'ordre d'envoi par un seul consumer au sein
  de cette partition), ou router les deux vers la même queue RabbitMQ avec un traitement
  mono-consumer pour cette entité ; ajouter dans tous les cas une vérification défensive de
  state-machine dans le consumer (rejeter un « create » pour une commande déjà à l'état
  « cancelled ») comme seconde ligne de défense.
- **Prévention :** Concevoir dès le départ les clés de partition/routage autour des exigences
  d'ordre par entité pour tout flux d'événements où la séquence compte, et ajouter des garde-fous
  de state-machine dans les consumers comme pratique standard plutôt que de supposer que l'ordre de
  livraison est garanti.

### S6. Les consumers retraitent à répétition le même lot de messages pendant une période de redémarrages fréquents
- **Symptômes :** Le traitement en double est corrélé spécifiquement aux fenêtres de déploiement ou
  à une instance de consumer qui flappe (crash-loop, ou un autoscaler agressif ajoutant/retirant
  à répétition des instances).
- **Diagnostic :** Chaque arrivée/départ de consumer déclenche un rebalance Kafka (Q19) ; si les
  consumers redémarrent fréquemment, les rebalances sont fréquents, et tout lot in-flight non
  encore commité est retraité par le consumer qui récupère cette partition ensuite — une
  « rebalance storm » causée par des instances qui flappent multiplie le taux de traitement en
  double bien au-dessus de la base normale.
- **Exemple :**
  ```
  2024-03-11 10:02:01 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 joined
  2024-03-11 10:02:47 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 left
  2024-03-11 10:03:12 INFO [ConsumerCoordinator] Group billing-group rebalancing, member consumer-3 joined
  ```
  `consumer-3` flappe toutes les 30 à 60 secondes — chaque arrivée/départ déclenche un nouveau
  rebalance qui retraite le dernier lot non commité de cette partition.
- **Résolution :** Corriger le flapping sous-jacent (un bug de crash-loop, ou un autoscaler
  configuré trop agressivement pour cette charge), et séparément, s'assurer que l'arrêt du consumer
  est graceful (commiter les offsets et quitter proprement le group sur `SIGTERM` plutôt que d'être
  tué en plein lot) pour minimiser la fenêtre de retraitement même quand les redémarrages sont
  légitimes.
- **Prévention :** L'idempotence (Q13/Q14) est le vrai filet de sécurité ici quelle que soit la
  fréquence des redémarrages — mais régler correctement les timeouts de session/heartbeat et
  corriger directement les instances qui flappent réduit la fréquence à laquelle ce filet est
  réellement sollicité.

### S7. Un enregistrement apparaît comme sauvegardé en base, mais le service aval correspondant n'a jamais reçu l'événement le concernant
- **Symptômes :** Une commande existe en base, mais le service d'expédition n'a jamais reçu
  l'événement `OrderCreated` et n'a aucune trace du besoin de l'expédier — découvert seulement
  quand un client demande où est sa commande.
- **Diagnostic :** Incohérence classique de dual-write (Q26) — le service a commité l'écriture en
  base puis a planté (ou l'appel de publication lui-même a échoué) avant de publier avec succès
  l'événement, et comme l'écriture en base et la publication du message n'étaient pas atomiques,
  l'une a réussi sans l'autre.
- **Exemple :**
  ```java
  orderRepository.save(order);                      // commit — la commande existe en base
  eventPublisher.publish(orderCreatedEvent(order));  // timeout ici — jamais réellement envoyé
  // Aucune transaction ne couvre les deux appels ; un échec entre les deux est invisible jusqu'à ce
  // qu'un client remarque que la commande n'a jamais été expédiée.
  ```
- **Résolution :** L'atténuation immédiate consiste à identifier manuellement et republier les
  événements des enregistrements concernés (un script de réconciliation comparant les « commandes
  en base » aux « événements observés en aval »). La correction structurelle est le pattern outbox
  (Q26) — écrire l'événement dans une table outbox dans la même transaction que l'écriture métier,
  et faire publier depuis l'outbox par un processus relais séparé, garantissant que les deux ne
  peuvent pas diverger.
- **Prévention :** Traiter « comment l'événement est-il publié de façon fiable » comme une question
  de conception obligatoire pour toute écriture devant déclencher un événement aval, de la même
  manière que les frontières de transaction sont une question obligatoire pour toute écriture en
  base en plusieurs étapes.

### S8. Les consumers se mettent à lever des erreurs de désérialisation juste après le déploiement d'un changement par un producer
- **Symptômes :** Plusieurs consumers d'un topic se mettent à échouer (ou à mal parser
  silencieusement) les messages immédiatement après un déploiement de producer d'apparence sans
  rapport.
- **Diagnostic :** Le producer a modifié le schéma du message de façon non rétrocompatible — a
  supprimé un champ requis par un consumer, changé le type d'un champ, ou renommé quelque chose —
  sans qu'aucune vérification de compatibilité ne l'attrape avant la publication, puisqu'aucun
  schema registry (ni discipline équivalente) n'imposait des règles de compatibilité (Q27).
- **Exemple :**
  ```
  org.apache.avro.AvroTypeException: Found orders, expecting orders,
      missing required field customerId
  	at org.apache.avro.io.parsing.Symbol$...
  ```
  Le dernier déploiement du producer a supprimé `customerId` du schéma sans valeur par défaut —
  chaque consumer qui l'attend encore échoue dès le message suivant qu'il lit.
- **Résolution :** Annuler (rollback) le changement de schéma du producer si possible, ou livrer
  un correctif compatible (restaurer le champ, ou mettre à jour tous les consumers simultanément
  si le changement ne peut réellement pas être rétrocompatible — coordonné avec soin puisque les
  consumers se déploient indépendamment).
- **Prévention :** Adopter un schema registry avec un mode de compatibilité imposé (Q27) pour
  qu'un changement incompatible soit rejeté à la publication en CI/staging, et non découvert par
  des consumers qui échouent en production.

### S9. Une dead-letter queue s'avère, des semaines plus tard, contenir des milliers d'événements métier non traités
- **Symptômes :** Un audit ou une investigation sans rapport révèle une DLQ qui accumule
  silencieusement des messages en échec depuis des semaines — représentant de vrais événements
  métier (commandes, paiements) qui n'ont jamais été réellement menés à terme.
- **Diagnostic :** Une DLQ était correctement configurée pour capter les échecs (Q22, Q23), mais
  aucune alerte n'a jamais été mise en place dessus — les messages qui y atterrissaient ont réussi
  l'objectif étroit de « ne pas bloquer la queue principale » mais l'objectif plus large de
  « quelqu'un s'en rend compte et corrige » n'a jamais été câblé.
- **Exemple :**
  ```
  $ rabbitmqctl list_queues name messages
  orders-dlq   14382
  ```
  14 382 messages accumulés sans aucune alerte configurée sur la profondeur de cette queue — chacun
  représente un événement métier qui n'a jamais réellement abouti.
- **Résolution :** Trier le contenu de la DLQ — pour chaque message, déterminer s'il peut être
  retraité sans risque maintenant (échec transitoire depuis résolu) ou s'il nécessite une
  réconciliation manuelle côté métier (définitivement invalide, nécessite une décision humaine sur
  ce qui aurait dû se passer).
- **Prévention :** Une DLQ sans alerte sur sa profondeur n'est pas réellement un filet de
  sécurité, juste un échec silencieux au ralenti — alerter dès qu'un message arrive dans la DLQ (ou
  quand la profondeur dépasse un petit seuil) doit être livré en même temps que la DLQ elle-même,
  et non comme une tâche de suivi qui glisse.

### S10. Une instance de consumer traite la plupart des messages tandis que les autres restent presque inactives
- **Symptômes :** Charge inégale dans un pool de consumers RabbitMQ — le monitoring montre un ou
  deux consumers systématiquement bien plus occupés que les autres, alors que tous les consumers
  sont configurés à l'identique et tout aussi capables.
- **Diagnostic :** Vérifier le prefetch count (Q18) — un prefetch élevé ou illimité permet au
  broker de pousser un grand lot vers le consumer qui le demande en premier, et si ce consumer est
  ne serait-ce que légèrement plus rapide à acquitter, il continue de recevoir davantage de travail
  dans une boucle de rétroaction, pendant que les consumers plus lents attendent inactifs leur tour.
- **Exemple :**
  ```
  consumer-a: 8420 messages processed
  consumer-b: 412 messages processed
  consumer-c: 390 messages processed
  ```
  `consumer-a` n'est que marginalement plus rapide à ack, mais avec un prefetch illimité le broker
  continue de lui confier le lot suivant avant que `b`/`c` n'aient leur chance — une boucle de
  rétroaction, et non une différence significative de capacité des consumers.
- **Résolution :** Réduire le prefetch count (couramment à 1, ou un petit nombre adapté à la
  capacité de traitement concurrent réelle par consumer) pour que le broker distribue les messages
  plus uniformément à mesure que chaque consumer termine et acquitte, plutôt que de charger d'un
  gros lot un seul consumer.
- **Prévention :** Fixer par défaut pour les nouveaux consumers RabbitMQ une valeur de prefetch
  petite et choisie délibérément plutôt que de la laisser illimitée — un prefetch illimité est
  rarement l'optimisation de débit qu'il paraît être.

### S11. Un topic Kafka ne peut pas augmenter son débit de consommation, quel que soit le nombre d'instances de consumer ajoutées
- **Symptômes :** Ajouter des instances à un consumer group n'a aucun effet sur le débit total
  au-delà d'un certain point, alors que chaque instance a de la capacité disponible.
- **Diagnostic :** Le nombre de partitions (Q11) est le plafond strict du parallélisme au sein d'un
  consumer group — si le topic a, disons, 4 partitions, un 5e consumer dans le group reste
  simplement inactif sans partition assignée, quelle que soit sa capacité.
- **Exemple :**
  ```
  $ kafka-consumer-groups.sh --describe --group orders-group --bootstrap-server broker:9092
  CONSUMER-ID   PARTITION
  consumer-1    0
  consumer-2    1
  consumer-3    2
  consumer-4    3
  consumer-5    -           <- aucune partition assignée, inactif
  ```
- **Résolution :** Augmenter le nombre de partitions du topic pour correspondre au parallélisme
  réellement requis (en acceptant la discontinuité du mapping de clés de la Q11 pour toute clé
  dépendante de l'ordre), puis scaler les consumers en conséquence.
- **Prévention :** Provisionner dès le départ le nombre de partitions avec de la marge pour le
  scaling futur, car l'augmenter plus tard perturbe l'ordre par clé, et le diminuer n'est
  pas possible du tout sans recréer le topic.

### S12. Une saga reste bloquée à mi-chemin, certains services ayant terminé leur étape et d'autres non
- **Symptômes :** Une saga commande-paiement-stock-expédition échoue à l'étape du stock,
  l'orchestrateur déclenche une compensation de remboursement du paiement, mais l'appel de
  remboursement lui-même timeout ou échoue — la saga est maintenant dans un état ambigu : le
  paiement a-t-il été remboursé ou non ?
- **Diagnostic :** La transaction compensatoire elle-même a échoué, ce que la conception initiale
  de la saga n'avait pas pleinement prévu — les compensations étaient traitées comme « réussissant
  toujours » au lieu de nécessiter la même fiabilité (retry, idempotence) que les étapes aller.
- **Exemple :**
  ```java
  // L'étape de saga de la version stable attend :
  record ReserveRequest(String orderId, int quantity) {}
  // Une version canary commence à exiger un champ supplémentaire que la logique de compensation de
  // la version stable n'a jamais appris à renvoyer :
  record ReserveRequest(String orderId, int quantity, String warehouseId) {}
  // Un appel de compensation construit contre l'ancien contrat échoue contre le nouveau en pleine saga.
  ```
- **Résolution :** Retenter la compensation en échec avec les mêmes garanties d'idempotence qu'une
  étape aller nécessiterait (le point de la Q29 : les compensations ne sont pas exemptées de la
  Q13) ; si les retries sont réellement épuisés, la saga a besoin d'un état explicite « bloquée,
  intervention manuelle requise » avec alerte, plutôt que d'apparaître silencieusement terminée ou
  de disparaître silencieusement.
- **Prévention :** Concevoir chaque transaction compensatoire avec la même rigueur que les
  transactions aller dès le départ — idempotente, retentable, et avec un état d'échec terminal
  explicite qui alerte un humain plutôt que de boucler indéfiniment ou d'échouer silencieusement.

### S13. Des utilisateurs reçoivent plusieurs fois le même email de notification pour un seul événement
- **Symptômes :** Un email « votre commande a été expédiée » (ou une notification transactionnelle
  similaire) est envoyé deux ou trois fois au même utilisateur pour la même expédition.
- **Diagnostic :** Le consumer de notification n'est pas idempotent (Q13) — sous une livraison
  at-least-once normale (un rebalance, un retry après un échec transitoire juste après l'envoi de
  l'email mais avant le commit de l'offset), le même message est redélivré et l'effet de bord
  « envoyer un email » se ré-exécute simplement, puisque l'envoi d'un email n'a pas d'idempotence
  naturelle comme le ferait un `UPDATE` en base.
- **Exemple :**
  ```java
  if (notificationLog.exists(shipmentId)) return; // déjà envoyé — traiter comme un no-op
  sendShippedEmail(user, shipmentId);
  notificationLog.recordSent(shipmentId); // idéalement écrit dans la même transaction que la vérification
  ```
- **Résolution :** Ajouter une vérification d'idempotence spécifique à cet effet de bord —
  enregistrer « notification envoyée pour l'expédition X » dans une table avec une contrainte
  d'unicité sur l'ID d'expédition/d'événement, vérifiée (et insérée, dans la même transaction que
  l'appel au fournisseur d'email, ou au moins avant lui) avant l'envoi effectif.
- **Prévention :** Reconnaître que les effets de bord sans idempotence naturelle (envoyer un email,
  appeler une API tierce sans support d'idempotency key) sont exactement les cas nécessitant un
  enregistrement de dédup explicite — ne pas supposer que « le système de messaging gère les
  doublons », puisqu'il garantit généralement l'inverse (at-least-once, pas exactly-once pour les
  effets de bord externes).

### S14. Pendant une panne du broker, certains services perdent silencieusement des messages tandis que d'autres se bloquent complètement
- **Symptômes :** Une brève panne du broker provoque des comportements très différents selon les
  services — les appels de publication de certains producers se bloquent jusqu'au timeout, d'autres
  semblent réussir mais le message n'arrive jamais réellement une fois le broker rétabli.
- **Diagnostic :** Vérifier la configuration d'acknowledgment de chaque producer — un producer
  qui n'attend aucun acquittement (RabbitMQ sans publisher confirms, ou `acks=0` de Kafka)
  considère la publication comme « terminée » à l'instant où elle est envoyée sur la socket, sans
  confirmation que le broker l'a réellement reçue ou persistée, donc un message envoyé juste au
  moment où le broker tombe est simplement perdu sans que le producer n'en sache rien ; un producer
  configuré pour attendre l'acquittement complet se bloque/retente jusqu'à en obtenir un, ce qui
  explique pourquoi il se bloque à la place.
- **Exemple :**
  ```java
  props.put("acks", "0");   // fire-and-forget — l'appel retourne avant même que le broker ne réponde
  props.put("acks", "all"); // attend l'acquittement de réplication complet — se bloque/retente à la place
  ```
- **Résolution :** Standardiser un niveau d'acknowledgment adapté à l'importance du message —
  `acks=all`/publisher confirms avec un retry borné puis échec (pas de blocage indéfini) pour tout
  ce qui ne peut pas être perdu silencieusement, donnant au producer un signal clair lui indiquant
  qu'il doit se replier sur quelque chose (queue locale, alerte, dégradation gracieuse) plutôt
  que de subir soit une perte silencieuse, soit un blocage indéfini.
- **Prévention :** Auditer explicitement la configuration d'acknowledgment par producer comme une
  décision de fiabilité délibérée, et non comme un défaut laissé à ce que la librairie cliente
  fournit, et fixer un timeout borné avec un repli explicite pour tout producer qui se
  bloquerait sinon indéfiniment lors d'une panne du broker.

### S15. Un lot d'événements s'avère avoir simplement disparu, sans aucune erreur nulle part
- **Symptômes :** Un trou dans les données aval attendues correspond à une période où le consumer
  responsable était arrêté (un déploiement, un incident) plus longtemps que d'habitude — et une
  fois revenu, ces messages précis n'ont jamais été traités, sans aucune erreur loguée nulle part.
- **Diagnostic :** Vérifier la configuration du TTL des messages (Q9, RabbitMQ) — si le consumer
  était arrêté plus longtemps que le TTL configuré, les messages ont expiré et ont soit été
  silencieusement jetés, soit routés vers une DLQ qui n'était pas non plus surveillée (S9) avant
  que quiconque ne s'en aperçoive ; c'est fonctionnellement une perte de données silencieuse même
  si le broker a « fonctionné correctement » selon sa propre configuration.
- **Exemple :**
  ```java
  Map<String, Object> args = new HashMap<>();
  args.put("x-message-ttl", 1_800_000); // 30 minutes
  // pas de x-dead-letter-exchange défini — les messages qui survivent à l'indisponibilité du consumer
  // sont simplement jetés par le broker, sans plus rien à retraiter ensuite.
  channel.queueDeclare("shipments-queue", true, false, false, args);
  ```
- **Résolution :** Si une DLQ a capté les messages expirés, les retraiter à partir de là ; si le
  TTL était configuré sans aucun repli de dead-lettering, les messages sont réellement
  irrécupérables et nécessitent une réconciliation côté métier pour combler le trou.
- **Prévention :** Tout TTL configuré sur une queue transportant des événements critiques pour le
  métier a besoin d'une cible dead-letter explicite (jamais de drop silencieux) et d'une alerte sur
  cette DLQ — et la valeur du TTL elle-même doit être fixée en tenant compte d'une indisponibilité
  réaliste du consumer dans le pire cas, et non des seules attentes du chemin nominal.

### S16. Augmenter le nombre de partitions d'un topic pour améliorer le débit casse les hypothèses d'un consumer aval
- **Symptômes :** Peu après l'augmentation du nombre de partitions d'un topic pour aider avec un
  problème de lag (la correction de S11), un autre consumer aval se met à présenter le symptôme de
  violation d'ordre de S5, pour des clés qui n'avaient jamais eu de problème d'ordre auparavant.
- **Diagnostic :** Augmenter le nombre de partitions (Q11) change le mapping du hash clé →
  partition pour la suite — une clé qui atterrissait systématiquement dans la partition 3 atterrit
  maintenant dans une autre partition pour les nouveaux messages, alors que les anciens messages de
  cette même clé restent dans l'historique de la partition 3 ; un consumer qui repose sur « tous
  les messages de cette clé ont toujours été dans la même partition, donc je peux suivre en toute
  sécurité un état par partition » casse dès que le repartitionnement a lieu.
- **Exemple :**
  ```java
  // Fragile : suppose que tout l'historique d'une clé vit dans une seule partition pour toujours.
  Map<Integer, State> statePerPartition = new HashMap<>();
  void onRecord(ConsumerRecord<String, String> r) {
      statePerPartition.computeIfAbsent(r.partition(), p -> new State()).apply(r);
  }
  // Après repartitionnement, une clé qui était toujours hashée vers la partition 3 est maintenant
  // hashée vers la partition 9 pour les nouveaux messages — cette map scinde maintenant en deux
  // l'état d'une seule entité logique.
  ```
- **Résolution :** Le consumer spécifique qui repose sur cette hypothèse doit être repensé pour ne
  pas dépendre d'un mapping clé-partition stable pendant toute la vie du topic (suivre l'état par
  clé sur toutes les partitions où elle peut apparaître, et non par partition), car ce n'est
  souvent pas réversible en pratique.
- **Prévention :** Provisionner généreusement le nombre de partitions dès le départ précisément
  parce que le repartitionnement a ce coût caché (Q11), et traiter toute future décision de
  repartitionnement comme nécessitant un audit explicite des hypothèses d'ordre de chaque consumer,
  et non comme un simple levier de débit à actionner librement.

### S17. Un court incident aval se transforme en panne de 40 minutes parce que chaque consumer retente en même temps
- **Symptômes :** Un fournisseur de paiement renvoie des `503` pendant ~30 secondes. Les consumers
  de traitement des commandes restent au rouge pendant 40 minutes : le consumer lag monte à des
  millions, la page de statut du fournisseur indique un rétablissement, pourtant il continue de nous
  rate-limiter (`429`), et les logs d'erreur montrent les mêmes enregistrements échouant à répétition
  à haute vitesse.
- **Diagnostic :** Comparer le débit de requêtes vers le fournisseur *pendant* l'incident au débit
  normal : il est 5 à 10 fois plus élevé. Les consumers retentent instantanément et
  inconditionnellement (une boucle `retry` serrée, ou un broker qui remet en queue sur `nack`
  immédiatement), donc chaque échec multiplie le trafic exactement quand la dépendance est la plus
  faible, et quand elle se rétablit elle est immédiatement écrasée par le backlog plus les retries —
  une **retry storm**. Comme toutes les instances ont échoué au même instant, leurs tentatives de
  retry sont elles aussi synchronisées. Vérifier : pas de backoff, pas de jitter, pas de plafond de
  tentatives, requeue avec `requeue=true` à chaque échec, et pas de circuit breaker (Q30 du
  module 2).
- **Exemple :**
  ```java
  @RabbitListener(queues = "payments")
  void handle(Payment p) {
      try { provider.charge(p); }
      catch (Exception e) { throw new AmqpRejectAndDontRequeueException(e); } // ok
  }
  // mais la config du container avait :  spring.rabbitmq.listener.simple.default-requeue-rejected=true
  //   -> le message retourne directement en tête de queue et échoue à nouveau en quelques microsecondes
  ```
- **Résolution :** Arrêter l'hémorragie : mettre en pause les consumers (ou les scaler à zéro)
  jusqu'à ce que le fournisseur soit sain, puis reprendre progressivement. Correction de fond :
  des retries avec **backoff exponentiel et jitter** et un nombre de tentatives borné (Q24), un
  **circuit breaker** qui met en pause la consommation tant que la dépendance est ouverte
  (`KafkaListenerEndpointRegistry.pause()`, ou Resilience4j), du dead-lettering après la dernière
  tentative, et un rate limit sur les appels sortants. Vérifier avec un chaos test : faire renvoyer
  `503` au stub pendant 30 s et asserter que le débit de requêtes sortantes reste sous un plafond,
  et que le lag se résorbe en quelques minutes après le rétablissement au lieu d'osciller.
- **Prévention :** Une librairie de politique de retry partagée (backoff + jitter + plafond) plutôt
  que des boucles ad hoc par listener ; circuit breaker plus bulkhead par dépendance ; dashboards
  du nombre de retries et du débit sortant ; game-days qui injectent des pannes de dépendances.

### S18. Un consumer group rebalance sans cesse, le lag grimpe, et les mêmes messages sont traités encore et encore
- **Symptômes :** Après une release qui a ajouté un appel à un service d'enrichissement, un consumer
  group Kafka montre une activité constante mais presque aucune progression : le lag monte
  régulièrement, les logs sont pleins de `Member consumer-billing-3 ... has left the group` /
  `Attempt to heartbeat failed since group is rebalancing` et de `CommitFailedException: ... the
  time between subsequent calls to poll() was longer than the configured max.poll.interval.ms`.
  Des effets de bord en double apparaissent en aval.
- **Diagnostic :** Multiplier les *enregistrements par poll* par le *temps par enregistrement*. Le
  consumer poll jusqu'à `max.poll.records=500` ; le nouvel appel d'enrichissement prend ~1 s, donc
  un lot nécessite ~500 s, au-dessus des 300 s de `max.poll.interval.ms` — le consumer est évincé
  en plein lot, ne peut pas commiter, et ses partitions (avec le lot non commité) vont à un autre
  membre qui a le même problème (Q20). Confirmer à partir des logs de group côté broker et des
  métriques consumer `time-between-poll-avg/max`, et avec un thread dump d'un consumer montrant
  qu'il est dans l'appel distant.
- **Exemple :**
  ```java
  @KafkaListener(topics = "invoices", groupId = "billing")
  void onBatch(List<Invoice> batch) {          // jusqu'à 500 enregistrements par poll
      for (Invoice i : batch) enrichment.lookup(i);   // ~1s chacun, sans timeout -> 500s+
  }
  ```
- **Résolution :** Réduire le lot (`max.poll.records=50`), ajouter un timeout strict à l'appel
  d'enrichissement, et — si le travail est réellement lent — le paralléliser avec un worker pool
  borné pendant que la boucle de poll continue d'appeler `poll()` (ou `pause()` les partitions) et
  ne commiter que les offsets des enregistrements terminés. Garder `max.poll.interval.ms`
  proportionnel au pire cas d'un lot, et non « assez grand pour le masquer ». Passer au cooperative
  sticky assignor pour rendre tout rebalance moins coûteux. Vérifier que les logs de group ne
  montrent aucun rebalance sur une période de soak, que `time-between-poll-max` reste sous 50 % de
  l'intervalle, et que le lag se résorbe.
- **Prévention :** Alerter sur le taux de rebalance et sur `time-between-poll-max` en fraction de
  l'intervalle ; load-tester tout nouvel appel synchrone dans un listener ; faire en sorte que
  chaque appel distant dans un consumer ait un timeout ; garder les consumers idempotents car les
  rebalances se produiront quand même.

### S19. Rejouer la dead-letter queue après un correctif de bug envoie des emails en double aux clients et en débite certains une seconde fois
- **Symptômes :** Un bug avait dead-letteré 80 000 événements `OrderShipped` sur trois jours. Après
  le correctif, un ingénieur « shovel » toute la DLQ vers la queue principale. En quelques minutes,
  les clients reçoivent des emails d'expédition en double, l'API partenaire nous rate-limite, et
  environ 300 clients sont débités deux fois.
- **Diagnostic :** Inspecter le contenu et les headers de la DLQ (`x-death` dans RabbitMQ, les
  headers de topic d'origine / d'exception dans un DLT Kafka). De nombreux messages avaient été
  *partiellement* traités avant d'échouer (le handler a débité la carte, puis a planté à l'étape de
  l'email), et le handler corrigé n'est pas idempotent, donc le rejeu ré-exécute les étapes déjà
  terminées. Le flot contourne aussi le throttling normal, puisque 80 000 messages arrivent d'un
  coup, et certains sont simplement périmés (un `OrderShipped` pour une commande annulée depuis).
- **Exemple :**
  ```java
  void handle(OrderShipped e) {
      payments.capture(e.orderId());     // l'étape 1 a réussi à la première tentative...
      mail.sendShipped(e.orderId());     // ...l'étape 2 a levé une exception -> message dead-letteré
  }                                      // rejeu -> l'étape 1 s'exécute à nouveau -> double capture
  ```
- **Résolution :** Arrêter immédiatement le rejeu et chiffrer les dégâts (requêter les captures par
  `orderId` ayant count > 1 ; rembourser/annuler les doublons ; s'excuser auprès des clients dont
  les mails sont partis deux fois). Corriger correctement avant de rejouer à nouveau : rendre chaque
  étape idempotente (dédup par event id / idempotency key de capture, Q13-Q14) ; rejouer par
  **petits lots limités en débit** et avec un filtre de péremption (ignorer les événements dont
  l'état de l'entité a évolué depuis) ; rejouer d'abord un échantillon d'environ 50 et vérifier les
  résultats ; conserver les message ids d'origine pour que l'idempotence tienne.
- **Prévention :** Un runbook DLQ qui dit « diagnostiquer, corriger, rendre idempotent, rejouer un
  lot canary, puis throttler le reste » ; un outil de rejeu avec rate limiting et dry-run ; des
  alertes sur la profondeur *et* l'âge de la DLQ (Q22, S9) ; des idempotency keys sur chaque étape
  à effet de bord — y compris les appels aux fournisseurs de paiement.

### S20. La publication échoue par intermittence avec `RecordTooLargeException` (ou le broker coupe la connexion) pour quelques grosses commandes
- **Symptômes :** La plupart des commandes circulent normalement, mais un petit pourcentage — celles
  avec des centaines de lignes ou un PDF attaché — n'atteint jamais les services aval. Les logs du
  producer montrent `org.apache.kafka.common.errors.RecordTooLargeException: The message is
  1,347,220 bytes when serialized which is larger than 1,048,576` (ou RabbitMQ ferme le channel sur
  une frame surdimensionnée). La ligne en base a été sauvegardée.
- **Diagnostic :** Les enregistrements en échec sont les gros : comparer l'échec à la taille du
  payload. Le `max.request.size` du producer Kafka (1 MiB par défaut) et le `message.max.bytes` /
  `max.message.bytes` du broker/topic les rejettent ; les `fetch.max.bytes`/`max.partition.fetch.bytes`
  du consumer peuvent aussi bloquer leur lecture. Remarquer aussi *pourquoi* l'événement est si
  gros : il embarque un document entier alors que les consumers n'ont besoin que d'un identifiant et
  de quelques champs — et que l'échec a été avalé (`send()` fire-and-forget), si bien que la
  commande existait en base sans événement (Q16, S7).
- **Exemple :**
  ```java
  // L'événement porte le PDF complet de la facture (base64) plus chaque ligne.
  kafkaTemplate.send("orders", order.id(), new OrderCreated(order.id(), order.pdfBase64(), order.lines()));
  ```
- **Résolution :** Ne pas relever les limites à l'aveugle (des enregistrements plus gros gonflent la
  mémoire, le temps de réplication et le risque de rebalance). Utiliser le **claim-check pattern** :
  stocker le gros payload dans un stockage objet (S3/Blob) ou la base et publier un petit
  événement contenant une référence plus les champs dont les consumers ont réellement besoin (Q31) ;
  compresser si le payload est du texte. Gérer le résultat du send — en cas d'échec, conserver la
  ligne outbox et alerter au lieu de l'abandonner. Vérifier avec un test qui publie une pièce jointe
  de 20 Mo et asserte que l'événement reste sous ~10 Ko et que l'aval peut récupérer le document.
- **Prévention :** Fixer une taille maximale d'événement explicite dans le contrat et la valider
  dans le wrapper du producer ; surveiller `record-size-max` ; un point de checklist de revue de
  schéma « cet événement embarque-t-il des blobs ? » ; rendre les échecs de publication visibles
  via l'outbox (Q26).

### S21. Après un plantage de broker, des commandes que le producer avait confirmées manquent dans le topic
- **Symptômes :** Un broker d'un cluster Kafka à 3 nœuds a planté puis redémarré. Tout s'est
  rétabli, mais la réconciliation montre ~2 000 commandes dont les événements `OrderCreated`, que le
  producer a loggés comme envoyés avec succès, sont absents du topic ; les systèmes aval ne les ont
  jamais vus. Aucune erreur n'a été signalée à ce moment-là.
- **Diagnostic :** « Acquitté mais disparu » signifie que l'acquittement a été donné avant que
  l'enregistrement ne soit répliqué. Vérifier la config du producer : `acks=1`, donc le leader a
  confirmé après avoir écrit dans son propre log ; il a ensuite planté avant que les followers ne
  copient ces enregistrements, et un follower qui les avait manqués est devenu le nouveau leader —
  les enregistrements ont été tronqués sur l'ancien leader à son retour. Vérifier aussi
  `min.insync.replicas` (1 signifie que `acks=all` n'aurait pas aidé) et si
  `unclean.leader.election.enable=true` (Q16). Les métriques du cluster montrent une élection de
  leader et des `UnderReplicatedPartitions` au moment du plantage.
- **Exemple :**
  ```properties
  # producer                                # topic
  acks=1                                    replication.factor=3
                                            min.insync.replicas=1
  ```
- **Résolution :** Récupérer les données depuis la source de vérité — ré-émettre les événements
  manquants depuis la base/l'outbox en comparant les order ids (ce qui exige des consumers
  idempotents, Q13). Puis corriger les réglages de durabilité : `acks=all`,
  `enable.idempotence=true`, `min.insync.replicas=2`, replication factor 3, unclean election
  désactivée. Vérifier avec un test d'injection de pannes : produire en continu, tuer le broker
  leader, et asserter qu'aucun enregistrement acquitté ne manque et que les producers voient des
  erreurs (et non un succès silencieux) si le quorum est perdu.
- **Prévention :** Intégrer les défauts producer/topic dans une librairie cliente partagée et dans
  le provisioning des topics pour que les équipes ne choisissent pas `acks=1` par accident ;
  exécuter régulièrement des exercices de panne de broker ; ajouter une réconciliation entre la
  base et le topic pour les flux critiques.

### S22. Le disque PostgreSQL se remplit et le primary n'accepte plus d'écritures, des jours après qu'un connecteur CDC « s'est simplement arrêté »
- **Symptômes :** Un connecteur Debezium alimentant l'outbox des commandes est tombé en panne un
  week-end et personne ne l'a remarqué. Des jours plus tard, le volume de la base alerte à 90 %,
  puis 100 % : le primary passe en lecture seule ou plante, entraînant toute la plateforme. Les
  tables elles-mêmes n'ont pas grossi ; le répertoire `pg_wal` fait des centaines de Go.
- **Diagnostic :** Un logical replication slot force PostgreSQL à conserver tout le WAL que le
  consumer du slot n'a pas encore confirmé. Avec le connecteur mort, le slot est inactif et son
  `restart_lsn` n'avance jamais :
  ```sql
  select slot_name, active,
         pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) as retained_wal
  from pg_replication_slots;
  --  debezium_orders | f | 412 GB
  ```
  Puis trouver *pourquoi* le connecteur s'est arrêté (tâche Kafka Connect en échec, changement de
  schéma qu'il n'a pas su gérer, broker injoignable) dans les logs de Connect (Q30).
- **Exemple :**
  ```json
  { "name": "orders-outbox", "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "slot.name": "debezium_orders", "plugin.name": "pgoutput" } }
  ```
- **Résolution :** Urgence : libérer d'abord du disque, puis soit redémarrer/réparer le connecteur
  pour qu'il draine le slot, soit — si la récupération est impossible à temps — supprimer le slot
  (`select pg_drop_replication_slot('debezium_orders');`), en acceptant que le connecteur ait
  besoin d'un nouveau snapshot et que les événements depuis la panne doivent être re-dérivés depuis
  l'outbox/la table (consumers idempotents). Prévenir la récidive : définir
  `max_slot_wal_keep_size` (PostgreSQL 13+) pour qu'un slot abandonné soit invalidé au lieu de
  manger le disque, et vérifier en simulant une indisponibilité du connecteur en staging.
- **Prévention :** Alerter sur `retained_wal` par slot et sur l'état des tâches Kafka Connect
  (`FAILED`), surveiller le disque avec une prévision, maintenir un runbook pour « connecteur
  arrêté > 1 heure », et traiter chaque replication slot comme une ressource ayant un propriétaire.

## 📌 Cheat-sheet

- **RabbitMQ** = smart broker (routage, suivi de livraison par message), un message consommé a disparu. **Kafka** = dumb broker (log append-only, conserve indépendamment de la consommation), permet le replay.
- **Sémantiques de livraison** : at-most-once (fire-and-forget, peut perdre) vs at-least-once (défaut en pratique, peut dupliquer) vs exactly-once (interne au broker seulement — les effets de bord applicatifs nécessitent toujours de l'idempotence).
- **Stratégies d'idempotence** : contrainte d'unicité sur une clé métier (la plus forte — atomique, sans race check-then-insert), log de messages traités, ou opérations naturellement idempotentes (`SET x = y`, pas `x += 1`).
- **Ordre Kafka** = par partition uniquement ; le choix de la clé détermine quelles entités partagent des garanties d'ordre.
- **Ordre RabbitMQ** = par queue avec un seul consumer uniquement ; plusieurs consumers sur une queue le brisent.
- **DLQ** = obligatoire pour tout consumer avec un nombre de retries borné ; une DLQ sans alerte est une perte de données silencieuse, pas un filet de sécurité.
- **Rebalance Kafka** = déclenché par arrivée/départ/changement de partitions ; provoque le retraitement des lots non commités → l'idempotence n'est pas optionnelle.
- **Commit d'offset** : manuel, après un traitement réussi, pour la correction at-least-once ; l'auto-commit risque une perte silencieuse.
- **Prefetch (RabbitMQ)** : bas = distribution équitable, plus sûr en cas de plantage ; illimité = débit mais charge inégale et gros pics de requeue en cas de plantage.
- **Saga** : orchestration (centrale, visible, facile à raisonner) vs choreography (découplée, plus difficile à tracer) — les compensations demandent la même rigueur d'idempotence/retry que les étapes aller.
- **Pattern outbox** : écrire l'événement + les données métier dans une seule transaction de base ; un processus relais publie depuis l'outbox — résout le problème du dual-write.
- **Poison pill** : nombre de retries borné + DLQ, jamais de requeue illimité.
- **Évolution de schéma** : le schema registry (Avro/Protobuf) impose la rétrocompatibilité à la publication ; un champ additif optionnel avec valeur par défaut est toujours sûr.
- **Nombre de partitions Kafka** : plafond du parallélisme, peut être augmenté (casse le mapping clé→partition pour les nouveaux messages) mais jamais diminué.
- **Publisher confirms / acks Kafka** : confirment uniquement la persistance producer→broker — jamais une garantie de traitement de bout en bout.
- **Problème du dual-write** : écriture en base + publication de message n'est jamais atomique entre deux systèmes par défaut — le pattern outbox est la correction standard.
</content>
- **Queue vs topic** : les competing consumers *se partagent* une queue (scale-out) ; le pub/sub donne à *chaque* abonné sa propre queue/son propre consumer group — même `group.id` = compétition, `group.id` différent = fan-out ; parallélisme ≤ partitions.
- **Sémantique d'ack** : ack après traitement = at-least-once (plantage → redelivery) ; auto-ack = at-most-once ; l'équivalent Kafka est l'offset commité. Requeue-on-failure sans limite est une boucle chaude.
- **Durabilité Kafka** = `acks=all` + `min.insync.replicas=2` + RF 3 + `unclean.leader.election.enable=false` + producer idempotent + *vérifier le résultat du send* ; `acks=1` perd des données acquittées en cas de défaillance du leader.
- **`max.poll.interval.ms`** : les heartbeats viennent d'un thread séparé, donc une boucle de traitement lente est évincée alors qu'elle est « saine » → boucle de rebalance ; réduire `max.poll.records`, timeouts sur les appels aval, cooperative assignor, static membership.
- **Retries** : un retry sur place bloque la partition ; utiliser des retry topics/TTL+DLX avec backoff exponentiel + jitter, plafonner les tentatives, ne retenter que les erreurs transitoires, s'attendre à une perte d'ordre, garder les handlers idempotents.
- **Kafka multi-région** : MM2/cluster linking est asynchrone (RPO > 0), les offsets diffèrent entre clusters, l'active-active exige une propriété d'entité/des règles de conflit ; stretch cluster = RPO nul au prix de la latence.
- **Contenu d'événement** : notification (léger, rappel) vs event-carried state (gros, consumers autonomes, schéma = contrat) vs event sourcing (le log est la vérité, nécessite versioning/snapshots).
- **Publier de façon fiable** : jamais de dual-write ; outbox par polling (simple, `SKIP LOCKED`) → CDC Debezium (faible latence, mais les replication slots peuvent remplir le disque — plafonner avec `max_slot_wal_keep_size`, alerter sur le lag).
- **Rejouer une DLQ est un déploiement** : corriger, rendre idempotent, rejouer un lot canary, puis throttler ; filtrer les événements périmés.
- **Gros payloads** : claim-check (stocker le blob ailleurs, publier une référence) ; ne pas simplement relever `max.request.size`.
