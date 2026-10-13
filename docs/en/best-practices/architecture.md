# Architecture Best Practices

Rules for structuring a Spring Boot codebase so it stays changeable. The interview questions are in [Spring & Architecture](../interviews/spring-architecture.md) and [System Design](../interviews/system-design.md).

## 📦 Structure

### Package by feature, not by layer

Group code by business capability (`order`, `billing`, `catalog`), with controller, service and repository inside
each feature package.

**Why it's a best practice:** `controller/`, `service/` and `repository/` folders put every feature in every folder,
so one change touches four packages and nothing can be package-private. Feature packages keep related code together,
make boundaries visible, and let you hide internals; they are also the natural seams if a module is extracted later.

```text
// ⛔                         // ✅
controller/OrderController    order/OrderController
service/OrderService          order/OrderService
repository/OrderRepository    order/OrderRepository       (package-private where possible)
controller/InvoiceController  billing/InvoiceController
```

### Keep the domain free of framework code

Put business rules in plain classes that don't depend on HTTP, JPA or messaging; adapters at the edges translate.
This is the core of hexagonal (ports and adapters) architecture.

**Why it's a best practice:** rules mixed with `HttpServletRequest`, `@Entity` lifecycle quirks or Kafka headers can
only be tested with the whole framework running, and they change whenever the infrastructure changes. A pure domain is
fast to unit test and survives a switch from REST to messaging, or from JPA to JDBC. Apply it where the business logic
is rich; a simple CRUD service doesn't need the extra layers.

```java
// ✅ domain decides, adapter persists
public class Order {
    public void cancel(Clock clock) {
        if (status == SHIPPED) throw new OrderAlreadyShipped(id);
        status = CANCELLED; cancelledAt = clock.instant();
    }
}
```

### Enforce boundaries with tests

Check dependency rules with ArchUnit or Spring Modulith in the normal test suite.

**Why it's a best practice:** architecture diagrams don't fail the build; an import from `billing.internal`
into `order`, added under deadline pressure, triggers nothing until the modules are tangled. A rule test turns the intended structure into a check that
every pull request runs.

```java
// ✅
@ArchTest static final ArchRule domainIsPure =
    noClasses().that().resideInAPackage("..domain..")
               .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta.persistence..");

@Test void modulesRespectBoundaries() { ApplicationModules.of(App.class).verify(); }   // Spring Modulith
```

## 🧱 Domain modelling

### Design aggregates around invariants, and reference others by id

An aggregate is the unit that must be consistent after each transaction (an order and its lines). Change one
aggregate per transaction, and reference other aggregates by id rather than by object.

**Why it's a best practice:** large object graphs with bidirectional JPA associations load too much, lock too much and
let any code change anything. Small aggregates keep invariants in one place (`order.addLine()` checks the limit),
transactions short, and boundaries clear; cross-aggregate consistency goes through domain events, which also prepares
a later split into services.

```java
// ⛔ @ManyToOne Customer customer;  @OneToMany List<Invoice> invoices;   (whole graph reachable)
// ✅ private CustomerId customerId;  invoices are another aggregate, updated by an OrderPlaced event
```

### Use value objects instead of primitives for domain concepts

Wrap concepts such as `Money`, `Email`, `OrderId` in small immutable types (records) that validate themselves.

**Why it's a best practice:** `BigDecimal amount, String currency` lets anyone add euros to dollars, and
`(long customerId, long orderId)` lets arguments be swapped without a compiler error. A value object makes invalid
states unrepresentable and puts the rule in one place.

```java
// ✅
public record Money(BigDecimal amount, Currency currency) {
    public Money { if (amount.scale() > currency.getDefaultFractionDigits()) throw new IllegalArgumentException(); }
    public Money plus(Money o) { requireSameCurrency(o); return new Money(amount.add(o.amount), currency); }
}
```

## 🧭 Decisions

### Start with a modular monolith

Build one deployable with strong module boundaries, and extract a service only when there's a concrete reason:
independent scaling, a separate team, a different release cadence or a different technology.

**Why it's a best practice:** microservices trade code complexity for distributed-systems complexity (network
failures, eventual consistency, distributed tracing, many pipelines) before you know where the real boundaries are.
Wrong boundaries in a monolith cost a refactor; wrong boundaries between services cost a migration. A well-modularized
monolith keeps both options open.

### Record significant decisions in ADRs

Write a short Architecture Decision Record (context, decision, alternatives considered, consequences) in the repository
for decisions that are expensive to reverse.

**Why it's a best practice:** six months later nobody remembers why Kafka was chosen over RabbitMQ or why a module
talks to another through events, so decisions are re-argued or undone by accident. An ADR takes 20 minutes, is
reviewed like code, and lets new team members understand the trade-offs instead of guessing.

```text
docs/adr/0007-use-outbox-for-order-events.md
Status: Accepted · Context: dual writes lost events twice in Q2 · Decision: transactional outbox + Debezium
Alternatives: Kafka transactions (no DB coverage), listener after commit (still loses on crash)
Consequences: at-least-once, consumers must be idempotent; one more component to operate
```
