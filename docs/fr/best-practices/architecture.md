# Bonnes pratiques d'architecture

Règles pour structurer une base de code Spring Boot afin qu'elle reste facile à faire évoluer. Les questions d'entretien sont dans [Spring & Architecture](../interviews/spring-architecture.md) et [System Design](../interviews/system-design.md).

## 📦 Structure

### Organisez les packages par fonctionnalité, pas par couche

Regroupez le code par capacité métier (`order`, `billing`, `catalog`), avec controller, service et repository dans
chaque package de fonctionnalité.

**Pourquoi c'est une bonne pratique :** des dossiers `controller/`, `service/` et `repository/` mettent chaque
fonctionnalité dans chaque dossier : un changement touche quatre packages et rien ne peut être package-private. Les
packages par fonctionnalité gardent ensemble le code lié, rendent les frontières visibles et permettent de cacher les
détails internes ; ce sont aussi les coutures naturelles si un module est extrait plus tard.

```text
// ⛔                         // ✅
controller/OrderController    order/OrderController
service/OrderService          order/OrderService
repository/OrderRepository    order/OrderRepository       (package-private si possible)
controller/InvoiceController  billing/InvoiceController
```

### Gardez le domaine libre de tout code de framework

Placez les règles métier dans des classes simples qui ne dépendent ni de HTTP, ni de JPA, ni du messaging ; les
adaptateurs en bordure traduisent. C'est le cœur de l'architecture hexagonale (ports et adaptateurs).

**Pourquoi c'est une bonne pratique :** des règles mêlées à `HttpServletRequest`, aux subtilités du cycle de vie
`@Entity` ou aux en-têtes Kafka ne se testent qu'avec tout le framework démarré, et changent dès que l'infrastructure
change. Un domaine pur se teste vite en unitaire et survit à un passage de REST au messaging, ou de JPA à JDBC.
Appliquez-le là où la logique métier est riche ; un simple service CRUD n'a pas besoin de couches supplémentaires.

```java
// ✅ le domaine décide, l'adaptateur persiste
public class Order {
    public void cancel(Clock clock) {
        if (status == SHIPPED) throw new OrderAlreadyShipped(id);
        status = CANCELLED; cancelledAt = clock.instant();
    }
}
```

### Faites respecter les frontières par des tests

Vérifiez les règles de dépendance avec ArchUnit ou Spring Modulith dans la suite de tests habituelle.

**Pourquoi c'est une bonne pratique :** les schémas d'architecture ne font pas échouer le build ; un import de
`billing.internal` dans `order` fait sous la pression d'une deadline ne déclenche rien jusqu'à ce que les modules
soient enchevêtrés. Un test de règle transforme la structure voulue en contrôle exécuté par chaque pull request.

```java
// ✅
@ArchTest static final ArchRule domainIsPure =
    noClasses().that().resideInAPackage("..domain..")
               .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta.persistence..");

@Test void modulesRespectBoundaries() { ApplicationModules.of(App.class).verify(); }   // Spring Modulith
```

## 🧱 Modélisation du domaine

### Concevez les agrégats autour des invariants, et référencez les autres par id

Un agrégat est l'unité qui doit être cohérente après chaque transaction (une commande et ses lignes). Modifiez un seul
agrégat par transaction, et référencez les autres agrégats par id plutôt que par objet.

**Pourquoi c'est une bonne pratique :** de grands graphes d'objets avec des associations JPA bidirectionnelles chargent
trop, verrouillent trop et laissent n'importe quel code modifier n'importe quoi. De petits agrégats gardent les
invariants à un seul endroit (`order.addLine()` vérifie la limite), des transactions courtes et des frontières
claires ; la cohérence entre agrégats passe par des événements de domaine, ce qui prépare aussi un découpage ultérieur
en services.

```java
// ⛔ @ManyToOne Customer customer;  @OneToMany List<Invoice> invoices;   (tout le graphe accessible)
// ✅ private CustomerId customerId;  les factures sont un autre agrégat, mis à jour par un événement OrderPlaced
```

### Utilisez des value objects plutôt que des primitifs pour les concepts métier

Enveloppez des concepts comme `Money`, `Email`, `OrderId` dans de petits types immuables (records) qui se valident
eux-mêmes.

**Pourquoi c'est une bonne pratique :** `BigDecimal amount, String currency` permet à n'importe qui d'additionner des
euros et des dollars, et `(long customerId, long orderId)` permet d'inverser les arguments sans erreur de compilation.
Un value object rend les états invalides impossibles à représenter et place la règle à un seul endroit.

```java
// ✅
public record Money(BigDecimal amount, Currency currency) {
    public Money { if (amount.scale() > currency.getDefaultFractionDigits()) throw new IllegalArgumentException(); }
    public Money plus(Money o) { requireSameCurrency(o); return new Money(amount.add(o.amount), currency); }
}
```

## 🧭 Décisions

### Commencez par un monolithe modulaire

Construisez un seul livrable avec des frontières de modules fortes, et n'extrayez un service que pour une raison
concrète : montée en charge indépendante, équipe séparée, rythme de livraison ou technologie différents.

**Pourquoi c'est une bonne pratique :** les microservices échangent la complexité du code contre celle des systèmes
distribués (pannes réseau, cohérence à terme, traçage distribué, multiples pipelines) avant même de savoir où sont les
vraies frontières. De mauvaises frontières dans un monolithe coûtent un refactoring ; entre services, elles coûtent une
migration. Un monolithe bien modularisé garde les deux options ouvertes.

### Consignez les décisions importantes dans des ADR

Rédigez un court Architecture Decision Record (contexte, décision, alternatives envisagées, conséquences) dans le dépôt
pour les décisions coûteuses à défaire.

**Pourquoi c'est une bonne pratique :** six mois plus tard, personne ne se souvient pourquoi Kafka a été choisi plutôt
que RabbitMQ ou pourquoi un module parle à un autre par événements : les décisions sont rediscutées ou défaites par
accident. Un ADR prend 20 minutes, se revoit comme du code, et permet aux nouveaux arrivants de comprendre les compromis
au lieu de les deviner.

```text
docs/adr/0007-use-outbox-for-order-events.md
Statut : Acceptée · Contexte : les doubles écritures ont perdu des événements deux fois au T2
Décision : outbox transactionnelle + Debezium
Alternatives : transactions Kafka (ne couvrent pas la base), listener après commit (perd encore en cas de crash)
Conséquences : at-least-once, les consommateurs doivent être idempotents ; un composant de plus à exploiter
```
