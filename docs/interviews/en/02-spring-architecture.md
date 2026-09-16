# Spring & Architecture

## 🟢 Fundamentals

### Q1. What is Dependency Injection in Spring, and what are its advantages?
DI means a class declares what it needs (via constructor, setter, or field) and the Spring
container supplies (injects) that dependency instead of the class creating it itself.
Advantages: loose coupling between classes, much easier unit testing (you can inject mocks
without touching production wiring), more flexible configuration (swap an implementation
without touching the consumer), and container-managed object lifecycles instead of hand-rolled
`new` calls scattered through the codebase.

### Q2. What is Spring Boot, and how does it differ from plain Spring?
Spring Boot is an opinionated layer on top of the Spring Framework that removes most manual
setup. Where plain Spring needs extensive XML or Java configuration and a separately
provisioned server, Spring Boot auto-configures beans based on the dependencies on the
classpath, ships an embedded server (Tomcat, Jetty, or Undertow) so the app runs as a
standalone jar, and bundles production-ready features (metrics, health checks, externalized
configuration) out of the box — which is also why it's the default choice for microservices.

### Q3. What does `@SpringBootApplication` actually do?
It's a convenience annotation bundling three others on the main class: `@Configuration` (marks
the class as a source of bean definitions), `@EnableAutoConfiguration` (turns on
classpath-based auto-configuration), and `@ComponentScan` (scans the current package and
sub-packages for components). Understanding it as three separate annotations matters the
moment you need to customize just one of them — e.g. excluding a specific auto-configuration
class without giving up component scanning.

### Q4. What's the difference between `@Component`, `@Service`, and `@Repository`?
All three register a class as a Spring-managed bean via component scanning. `@Component` is
the generic form; `@Service` and `@Repository` are semantic specializations — `@Service` marks
a service-layer bean (mostly documentation/intent), and `@Repository` additionally enables
Spring's exception translation for the data-access layer, converting driver-specific exceptions
into Spring's unchecked `DataAccessException` hierarchy so callers don't need to catch
vendor-specific SQL exceptions.

### Q5. What is hexagonal (ports & adapters) architecture, and what problem does it solve?
Hexagonal architecture puts the domain/business logic at the center, exposing **ports**
(interfaces) that describe what the domain needs or offers, with **adapters** implementing
those ports for specific technologies — a REST controller and a message listener might both be
inbound adapters calling the same use case; a JPA repository and an in-memory fake might both
be outbound adapters implementing the same persistence port. The problem it solves: without
this boundary, business logic tends to accumulate framework and infrastructure dependencies
(JPA annotations on domain entities, `HttpServletRequest` leaking into business rules), which
makes the core logic harder to test in isolation and harder to change infrastructure without
touching business rules.

## 🟡 Senior traps

### Q6. What design patterns show up naturally in how Spring itself works?
**Answer:**
- **DI / IoC**: constructor, setter, and field injection all directly implement this pattern.
- **Singleton**: the default bean scope — `@Service` effectively applies Singleton, one shared
  instance the container injects everywhere it's needed.
- **Factory**: `ApplicationContext` and `FactoryBean` implementations act as factories that
  create and manage beans, rather than callers instantiating objects with `new`.
- **Strategy**: injecting different implementations of the same interface depending on context
  (e.g. multiple `PaymentProcessor` implementations selected at runtime).
- **Proxy**: a placeholder object controlling access to the real bean — exactly the mechanism
  behind `@Transactional`, method-level security, and AOP in general.
- **Template**: abstractions like `JdbcTemplate` handle the boilerplate of a repetitive
  operation (open connection, run query, handle exceptions, close connection) while letting you
  plug in just the part that varies.

**Example:**
```java
// Proxy: @Transactional wraps the bean so start/commit/rollback happens around your code.
@Transactional
public void placeOrder(Order order) { repository.save(order); }

// Template: JdbcTemplate hides connection/exception/close boilerplate — you supply
// only the SQL and the row-mapping function, the parts that actually vary.
List<Order> pending = jdbcTemplate.query(
    "select * from orders where status = ?",
    (rs, rowNum) -> new Order(rs.getString("id"), rs.getString("status")),
    "PENDING");
```

**Why it's a trap:** naming the patterns is the easy half; the follow-up an interviewer actually
cares about is spotting where the abstraction leaks — e.g. assuming a `@Service` singleton is
safe for mutable instance state (Q10), or that a CGLIB proxy behaves identically to the real
object it wraps (Q14). Reciting "Spring uses Singleton, Factory, Proxy..." without being able to
name a concrete failure mode for at least one of them is a shallow answer.

### Q7. Can you call a `@Transactional` method from another method in the same class?
**Answer:** No — or rather, it silently doesn't work as expected. Spring implements
`@Transactional` via a proxy wrapped around the bean; a call from *outside* the class goes
through that proxy and the transaction logic runs, but a call from *within* the same class
(self-invocation) bypasses the proxy entirely, calling the real method directly, so no
transaction actually starts — with no error to tell you. Fixes: move the method to another
bean, inject the `ApplicationContext`-managed proxy of the same bean into itself
(self-injection), or fall back to AspectJ compile-time/load-time weaving, which doesn't rely on
runtime proxying and so isn't subject to this limitation.

**Example:**
```java
@Service
public class OrderService {
    public void placeOrder(Order order) {
        save(order); // self-invocation — this is a plain `this.save(...)` call,
                      // it never goes through the transactional proxy
    }

    @Transactional
    public void save(Order order) {
        repository.save(order); // no transaction is actually started here
    }
}
```

**Why it's a trap:** the code compiles, runs, and "looks" transactional — nothing throws. The
bug only surfaces the day something inside `save` fails partway through and a partial write
isn't rolled back, in production, under conditions a happy-path manual test never exercised.

### Q8. Since `@Transactional` relies on the Proxy pattern, what does that tell you about calling it on a private method?
**Answer:** A private method can't be proxied the way a public method can — the dynamic proxy
overrides/wraps the method from *outside* the class, and a private method isn't visible outside
the class to override in the first place. So `@Transactional` on a private method has the same
practical failure mode as self-invocation (Q7): it's silently ignored, no transaction ever
starts, and nothing tells you at compile time or even at startup.

**Example:**
```java
@Service
public class OrderService {
    @Transactional
    private void archive(Order order) { // a proxy can never override a private method
        repository.markArchived(order); // this annotation has zero effect
    }

    public void run(Order order) {
        archive(order); // same silent no-op as self-invocation — no error anywhere
    }
}
```

**Why it's a trap:** it's easy to assume "the annotation is on the method, so it must apply" —
Spring never validates this at startup, so a `@Transactional private` method is a landmine that
looks completely correct in code review.

### Q9. What does calling `flush()` on a persistence context actually do, and how does it differ from `commit()`?
**Answer:** `flush()` pushes all pending changes to the database immediately but does **not**
commit the transaction — it just synchronizes the persistence context (the first-level cache)
with the database early, which is sometimes necessary before running a query that needs to see
those uncommitted changes (e.g. a native query bypassing the persistence context). `commit()`
ends the transaction, making the changes permanent (and, depending on isolation level, visible
to other transactions) — a flush without a commit can still be rolled back.

**Example:**
```java
entityManager.persist(order);
entityManager.flush();       // INSERT is sent to the DB now, but the transaction is still open

Integer count = (Integer) entityManager
    .createNativeQuery("select count(*) from orders where id = :id")
    .setParameter("id", order.getId())
    .getSingleResult();      // sees the flushed row, because a native query bypasses
                              // the first-level cache and hits the DB directly

// entityManager.getTransaction().rollback(); // still fully reversible at this point —
                                                // the flushed INSERT is undone with everything else
```

**Why it's a trap:** candidates conflate "the data hit the database" with "the data is
permanent." Flushing early is sometimes necessary, but a flush is not a commit — the change is
still fully reversible until the transaction actually ends.

### Q10. What are Spring bean scopes, and what's the thread-safety implication of getting one wrong?
**Answer:** `singleton` (default) creates one shared instance for the whole application context;
`prototype` creates a new instance on every injection point/request; `request` and `session`
scope to the web request/HTTP session. The trap: a `singleton`-scoped bean is shared across
every concurrent request handled by the application, so any mutable instance field on it is
shared mutable state across threads — a common real bug is adding an instance field to a
`@Service` for "just passing a value between two methods" and getting cross-request data
corruption under load, because that field is one shared field, not one per request.

**Example:**
```java
@Service
public class ReportService { // singleton by default — one instance for the whole app
    private String currentUser; // shared mutable field, NOT one per request

    public Report generate(String user) {
        currentUser = user;              // request thread A sets it
        return buildReport(currentUser); // request thread B may have already
                                          // overwritten currentUser by the time this runs
    }
}
```

**Why it's a trap:** it passes every manual test and every low-traffic staging check (one
request at a time never races with itself) and only breaks once two requests actually overlap
in production — which also makes it maddening to reproduce after the fact.

### Q11. Why is constructor injection generally preferred over field injection?
**Answer:** Constructor injection makes dependencies explicit and immutable (`final` fields),
makes it impossible to construct the bean in an invalid, partially-wired state, and —
critically for testing — lets you instantiate the class directly with mocks in a plain unit
test, with no Spring container involved at all. Field injection (`@Autowired` on a field)
requires reflection to set, can't be `final`, hides the dependency list (you have to read the
whole class instead of the constructor signature to know what it needs), and forces tests to
either boot a Spring context or use reflection-based mocking frameworks just to substitute a
dependency.

**Example:**
```java
// Field injection — needs Spring (or reflection) to substitute a mock in a test.
@Service
class ReportService {
    @Autowired private ReportRepository repository;
}

// Constructor injection — a plain unit test, no container at all.
@Service
class ReportService {
    private final ReportRepository repository;
    ReportService(ReportRepository repository) { this.repository = repository; }
}
new ReportService(mockRepository); // just works, no Spring involved
```

**Why it's a trap:** field injection looks simpler and is what most IDEs auto-generate, but
it's the version that lets a bean end up half-wired and forces every future test of that class
to carry Spring-container weight it never needed to.

### Q12. Walk through the Spring bean lifecycle, and how does Spring resolve circular dependencies?
**Answer:** Roughly: bean definitions are read, instances are instantiated (constructor
called), properties are injected (setter/field injection happens here — *after* construction),
`BeanPostProcessor`s run (before/after initialization, including `@PostConstruct`), then the
bean is ready for use; on shutdown, `@PreDestroy` and `DisposableBean.destroy()` run. Spring
resolves *setter/field* circular dependencies (A needs B, B needs A) using a three-tier cache of
early bean references, exposing a not-yet-fully-initialized bean reference to break the cycle —
but this trick only works for singleton beans created via setter/field injection, not
constructor injection: two beans depending on each other purely through their constructors is
an unresolvable circular dependency, and Spring fails fast at startup with a clear error rather
than trying to guess.

**Example:**
```java
@Service class A { A(B b) {} }   // constructor injection
@Service class B { B(A a) {} }   // constructor injection
// Startup fails immediately: BeanCurrentlyInCreationException — genuinely unresolvable.

@Service class A2 { @Autowired B2 b; }  // setter/field injection
@Service class B2 { @Autowired A2 a; }  // setter/field injection
// Starts fine — Spring hands B2 an early, not-yet-fully-initialized reference to A2
// to break the cycle, then finishes wiring both once construction completes.
```

**Why it's a trap:** "just switch to field injection to fix the circular dependency" trades a
loud, fail-fast startup error for a bean that's usable before it's fully wired — it silences the
symptom instead of fixing the actual design smell (two services that need each other), and
resurfaces later as a subtler bug if either bean does real work during construction.

### Q13. Why do `@Async` methods lose the Spring Security context?
**Answer:** `@Async` executes the method on a different thread from a task executor's pool, and
by default Spring Security's context is held in a `ThreadLocal` scoped to the *original* request
thread — so the new async thread simply doesn't have it, and any security check inside the
async method silently sees an unauthenticated context. Fix: configure
`SecurityContextHolder.setStrategyName(MODE_INHERITABLETHREADLOCAL)`, or more robustly, wrap the
task executor with `DelegatingSecurityContextAsyncTaskExecutor`, which explicitly propagates the
calling thread's security context into the async thread.

**Example:**
```java
@Async
public void auditAccess(User user) {
    // Runs on a task-executor thread, not the request thread that authenticated —
    // this is null, even though the calling request was fully authenticated.
    Authentication auth = SecurityContextHolder.getContext().getAuthentication();
    log.info("accessed by {}", auth); // logs "accessed by null"
}

// Fix: propagate the security context into the async executor explicitly.
@Bean
public TaskExecutor taskExecutor() {
    return new DelegatingSecurityContextAsyncTaskExecutor(new ThreadPoolTaskExecutor());
}
```

**Why it's a trap:** the failure is silent, not an exception — code that reads the security
context for an authorization check can end up denying (or, worse, defaulting to allowing)
access based on an empty context, and the bug only shows up in the async path, never in a
synchronous test of the same logic.

### Q14. What's the practical difference between JDK dynamic proxies and CGLIB proxies in Spring AOP, and why does it matter?
**Answer:** Spring uses JDK dynamic proxies (interface-based) when the target bean implements at
least one interface, and CGLIB (subclass-based bytecode generation) when it doesn't, or when
explicitly configured to always use CGLIB. The practical trap: a JDK dynamic proxy can only
intercept calls made *through the interface type* — if you inject the concrete class and call a
method not on the interface, or self-invoke (Q7), it's bypassed. CGLIB subclasses the target
class, so `final` classes or `final` methods can't be proxied by CGLIB at all — silently
skipping the intended AOP advice (transactions, security, caching) rather than erroring, which
is why `final` on a Spring-managed class or its methods is a real footgun, not just a style
preference.

**Example:**
```java
@Service
public final class PricingService { // final class — CGLIB cannot subclass this
    @Transactional
    public void applyDiscount(Order order) {
        order.applyDiscount();
        repository.save(order);
    }
}
// PricingService implements no interface, so Spring needs CGLIB — but CGLIB can't
// subclass a final class, so the proxy is never created and @Transactional silently
// never runs. No startup error; the annotation is simply inert.
```

**Why it's a trap:** the failure mode is identical to Q7/Q8 (silent no-op, no error anywhere),
but the root cause here is a class modifier that has nothing to do with the transaction code
itself — a `final` added for unrelated "good practice" reasons quietly disables AOP.

### Q15. Which Actuator endpoints matter in production, and what should you be careful about exposing?
**Answer:** `/actuator/health` (liveness/readiness for orchestrators), `/actuator/metrics`
(feeds Prometheus/monitoring), `/actuator/info` (build/version metadata), `/actuator/loggers`
(change log levels live without a redeploy — invaluable mid-incident), `/actuator/prometheus` if
the metrics registry is configured for it. The trap: several endpoints (`/actuator/env`,
`/actuator/beans`, `/actuator/heapdump`, `/actuator/mappings`) expose internal configuration,
environment variables (potentially including secrets), and application structure — these should
never be exposed unauthenticated on a public network, and most teams restrict Actuator to an
internal-only port or gate it behind Spring Security entirely.

**Example:**
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, loggers
        # deliberately NOT included: env, beans, heapdump, mappings, shutdown
  endpoint:
    health:
      show-details: when-authorized
```

**Why it's a trap:** the default Spring Boot Actuator starter historically exposed only
`health` and `info` over HTTP, which lulls teams into thinking "the defaults are safe" — but the
moment someone adds `include: "*"` for convenience during debugging (and forgets to revert it),
`/actuator/env` can leak database passwords and API keys straight to the internet.

### Q16. What's the precedence order across the different ways to configure a Spring Boot application?
**Answer:** From highest to lowest priority (roughly): command-line arguments,
`SPRING_APPLICATION_JSON` environment property, JNDI attributes, Java system properties, OS
environment variables, profile-specific `application-{profile}.properties/yml`, the base
`application.properties/yml`, then `@PropertySource` annotations and defaults set in code. The
practical implication: an environment variable set on a container will override whatever is
baked into the jar's `application.yml`, which is exactly the mechanism used to inject
environment-specific secrets and config without rebuilding the artifact per environment.

**Example:**
```bash
$ SPRING_APPLICATION_JSON='{"app.timeout":"5000"}' \
  java -jar app.jar --app.timeout=9000
# --app.timeout=9000 (a command-line argument) wins over SPRING_APPLICATION_JSON,
# which in turn wins over whatever application.yml bakes into the jar.
```

**Why it's a trap:** "I changed the value in `application.yml` and it's still using the old
one" is one of the most common config-debugging complaints, and the actual cause is almost
always a higher-priority source silently overriding the file someone edited — the fix is
knowing the order well enough to check the right layer first instead of guessing.

### Q17. How do you handle exceptions globally in a Spring Boot REST API?
**Answer:** With `@ControllerAdvice` (or `@RestControllerAdvice`) plus `@ExceptionHandler`,
centralizing error handling instead of scattering try/catch blocks across controllers.

**Example:**
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(EntityNotFoundException.class)
  public ResponseEntity<ErrorBody> handleNotFound(EntityNotFoundException ex) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ErrorBody(ex.getMessage()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<ErrorBody> handleUnexpected(Exception ex) {
    log.error("unhandled exception", ex);           // full detail server-side
    return ResponseEntity.internalServerError()
        .body(new ErrorBody("Something went wrong")); // generic, safe message to the caller
  }
}
```

**Why it's a trap:** the senior-level point isn't knowing `@ExceptionHandler` exists, it's
mapping each exception type to the *correct* HTTP status and a consistent error body shape, and
never letting an unhandled generic `Exception` leak a stack trace or internal detail (a SQL
fragment, an internal class name) back to the client — a catch-all handler that returns
`ex.getMessage()` directly to the caller is a common information-disclosure bug hiding behind
what looks like "proper" centralized error handling.

### Q18. How do you configure CORS correctly, and what's the trap with combining a wildcard origin and credentials?
**Answer:** Configure it globally via a `WebMvcConfigurer`, or per-controller with
`@CrossOrigin`. Browsers reject (and Spring itself rejects at config time) the combination of
`allowedOrigins("*")` with `allowCredentials(true)` — a wildcard origin plus cookies/credentials
would let any site make authenticated requests on a user's behalf, which is exactly what CORS
exists to prevent. If credentials are needed, origins must be an explicit allow-list, never a
wildcard.

**Example:**
```java
@Override
public void addCorsMappings(CorsRegistry registry) {
  registry.addMapping("/**")
    .allowedOrigins("https://app.example.com") // explicit allow-list, not "*"
    .allowedMethods("GET", "POST", "PUT", "DELETE")
    .allowCredentials(true);
}
// registry.addMapping("/**").allowedOrigins("*").allowCredentials(true);
// throws IllegalArgumentException at startup — Spring refuses this combination outright.
```

**Why it's a trap:** a developer under deadline pressure who hits a CORS error in the browser
console reaches for `allowedOrigins("*")` as the fastest fix — which is exactly the one
combination that either fails outright (with credentials) or silently opens the API to any
origin (without credentials, but with sensitive data returned regardless).

### Q19. How do you actually structure a hexagonal Spring Boot application in packages?
**Answer:** A common layout: a `domain` package with plain Java (no Spring, no JPA annotations)
holding entities and business rules; an `application` package with use-case/service classes and
the **port** interfaces they depend on (`OrderRepository`, `PaymentGateway`); and an
`infrastructure`/`adapter` package with the concrete implementations — a `@RestController`
adapting HTTP to a use case call, a `@Repository`-annotated JPA implementation of
`OrderRepository`, a message listener adapting a queue message to a use case call. The
enforcement mechanism that actually keeps this honest over time (not just at day one) is an
architecture test.

**Example:**
```
com.example.orders
├── domain          # plain Java: Order, OrderStatus, business rules — no Spring, no JPA
├── application     # OrderService (use case) + ports: OrderRepository, PaymentGateway
└── infrastructure
    ├── web         # OrderController — inbound adapter, translates HTTP to a use-case call
    ├── persistence # JpaOrderRepository implements OrderRepository — outbound adapter
    └── messaging   # OrderCreatedListener — inbound adapter, translates a queue message
```

**Why it's a trap:** the layout alone doesn't enforce anything — nothing stops a developer under
deadline pressure from importing `jakarta.persistence.Entity` directly into `domain.Order`
"just this once," and without an ArchUnit rule catching it in CI, that one exception quietly
becomes the new normal within a few sprints.

### Q20. Design the payment-type selection for a system supporting Credit Card, PayPal, and Bitcoin, without the client code knowing which concrete class to instantiate.
**Answer:** Use the Factory pattern: a `PaymentFactory` with a method like
`createPayment(String type)` that internally decides which concrete `Payment` subclass to
instantiate and return. The client just asks the factory for "the payment implementation it
needs" and stays decoupled from the concrete implementations — adding a fourth payment type
later means adding a new `Payment` subclass and one branch in the factory, not touching every
call site that creates a payment. In a Spring context, this is often implemented more
idiomatically by injecting a `Map<String, Payment>` (or `List<Payment>` filtered by a
discriminator method) and letting Spring's component scanning populate it from every
`@Component`-annotated `Payment` implementation, avoiding the factory's own `switch`/`if` chain
entirely.

**Example:**
```java
public interface Payment { void process(BigDecimal amount); }

@Component("CREDIT_CARD") class CreditCardPayment implements Payment { /* ... */ }
@Component("PAYPAL")      class PayPalPayment implements Payment { /* ... */ }
@Component("BITCOIN")     class BitcoinPayment implements Payment { /* ... */ }

@Service
class PaymentDispatcher {
    private final Map<String, Payment> payments; // Spring wires this by bean name automatically
    PaymentDispatcher(Map<String, Payment> payments) { this.payments = payments; }

    void pay(String type, BigDecimal amount) {
        payments.get(type).process(amount); // no factory class, no switch/if chain at all
    }
}
```

**Why it's a trap:** candidates who reach straight for a hand-written `PaymentFactory` with a
`switch` statement aren't wrong, but they're missing that Spring's own container already *is* a
registry of named/typed beans — the idiomatic Spring answer replaces a class you'd have to
maintain with a `Map` the container populates for free, and an interviewer asking "how would you
do this in Spring specifically" is checking for that recognition.

### Q21. When do you reach for the Strategy pattern with Spring beans versus a simple `if`/`switch`?
**Answer:** Strategy earns its complexity when the set of behaviors is expected to grow (new
payment providers, new pricing rules, new notification channels) and each behavior is
substantial enough to deserve its own class and tests — injecting `List<PricingStrategy>` and
selecting one by a predicate method keeps each strategy independently testable and lets a new
one be added without touching existing code (open/closed principle). A simple `if`/`switch` is
the right call when the branches are genuinely fixed, few, and unlikely to grow — introducing a
full Strategy hierarchy for two permanent branches is over-engineering that makes the code
harder to read, not easier.

**Example:**
```java
interface PricingStrategy { boolean supports(CustomerTier tier); BigDecimal price(Order o); }

@Service
class PricingService {
    private final List<PricingStrategy> strategies;
    PricingService(List<PricingStrategy> strategies) { this.strategies = strategies; }

    BigDecimal price(Order order, CustomerTier tier) {
        return strategies.stream()
            .filter(s -> s.supports(tier))
            .findFirst()
            .orElseThrow()
            .price(order);
    }
}
// Adding a new tier = a new @Component implementing PricingStrategy — PricingService
// itself never changes.
```

**Why it's a trap:** "always use Strategy over `if`/`switch`, it's more SOLID" is a
overcorrection — a senior answer names the actual criterion (does this set of branches grow
over time, and is each one substantial) instead of treating one pattern as universally superior
to a plain conditional.

### Q22. What's the circuit breaker pattern, and when does a service actually need one?
**Answer:** A circuit breaker wraps calls to a potentially-failing dependency and tracks their
failure rate; once failures exceed a threshold, it "opens" and fails fast (without even
attempting the call) for a cooldown period, then allows a limited number of trial calls
("half-open") to test recovery before fully closing again. It matters specifically when a slow
or failing downstream dependency would otherwise cause callers to pile up waiting on it
(exhausting their own thread pools, per S7/S8) and cascade the failure upstream — a service
calling one flaky downstream among several should fail fast on that one and keep serving
everything else, rather than let threads queue up waiting on a dependency that isn't coming back
soon. Resilience4j is the common Spring Boot integration (replacing the now-EOL Netflix
Hystrix).

**Example:**
```java
@CircuitBreaker(name = "inventoryService", fallbackMethod = "fallback")
public Stock checkStock(String sku) {
    return inventoryClient.getStock(sku); // fails fast once the breaker is open,
                                           // instead of blocking on a downstream that's down
}

private Stock fallback(String sku, Throwable t) {
    return Stock.unknown(sku); // degrade gracefully rather than propagate the failure
}
```

**Why it's a trap:** candidates often describe the pattern correctly but can't say *when* it's
warranted — adding a circuit breaker around every single downstream call regardless of blast
radius is cargo-culting resilience, while skipping it on the one call that genuinely can cascade
(a shared thread pool, per S8) leaves the actual risk unaddressed.

### Q23. What causes the N+1 query problem in JPA, and how do you detect and fix it?
**Answer:** Lazy-loaded JPA associations fetched inside a loop trigger one query per iteration
instead of one query total — the classic N+1: fetching N orders runs 1 query for the orders,
then N more queries, one per order, to lazily load each order's line items the first time
they're accessed. It's invisible in code review (nothing looks wrong — it's just
`order.getLineItems()`) and invisible against a dev/test dataset with a handful of rows; it only
becomes visible as N grows in production, where it shows up as a linear-in-N slowdown that looks
like a scaling problem rather than a query-count problem. Detect it by turning on SQL logging
(`spring.jpa.show-sql=true` plus a statement counter in tests, or a tool like Hibernate's
statistics/`SessionMetrics`) and watching query counts scale with result-set size instead of
staying constant.

**Example:**
```java
List<Order> orders = orderRepository.findAll();      // 1 query
for (Order order : orders) {
    order.getLineItems().size();                      // 1 extra lazy-load query PER order
}
// N orders -> N+1 total queries instead of 1.

// Fix: fetch the association in the same query with a query-specific JOIN FETCH.
@Query("select distinct o from Order o join fetch o.lineItems")
List<Order> findAllWithLineItems();
```

**Why it's a trap:** candidates who've only worked against small local datasets often haven't
seen this fail, so the answer they reach for is "just make it `@OneToMany(fetch =
FetchType.EAGER)`" — that fixes this one query path but silently makes *every* query that loads
an `Order` eagerly fetch line items too, including ones that never needed them, trading one
N+1 for unconditional over-fetching everywhere; the correct fix is a query-specific `JOIN FETCH`
or entity graph, not a blanket fetch-type change on the mapping itself.

### Q24. What's the trap with `@Cacheable` returning a mutable object?
**Answer:** `@Cacheable` stores whatever reference the method returns; if that's a mutable
object (a `List`, a mutable entity/DTO) and a caller mutates it, every subsequent cache hit
hands out that same corrupted object — the cache doesn't clone on read, so "reading from the
cache" and "getting your own private copy" are not the same thing unless the cached type is
immutable or the cache provider is configured to serialize/deserialize on access.

**Example:**
```java
@Cacheable("productLists")
public List<Product> findByCategory(String category) {
    return new ArrayList<>(repository.findByCategory(category));
}

List<Product> products = productService.findByCategory("books");
products.add(new Product("injected")); // mutates the cached list in place!

// Every later call to findByCategory("books") now returns the polluted list —
// including the injected product — even though nothing was ever persisted.
```

**Why it's a trap:** it doesn't fail where the mutation happens — it fails somewhere else
entirely, on a later, unrelated call that just happened to read the same cache key, which makes
it look like a data-corruption bug in a completely different code path rather than a caching
contract violation at the source.

### Q25. Why doesn't `@Valid` automatically validate nested objects, and what's the fix?
**Answer:** `@Valid` on a controller parameter validates that object's own fields, but
validation does **not** automatically cascade into a nested object field — a nested field also
needs its own `@Valid` annotation, or Bean Validation silently skips validating it entirely,
letting an invalid nested object straight through with no error and no warning.

**Example:**
```java
class OrderRequest {
    @NotNull String customerId;
    AddressRequest shippingAddress; // missing @Valid — this nested object is never validated
}
class AddressRequest {
    @NotBlank String street;
    @NotBlank String zipCode;
}

@PostMapping("/orders")
ResponseEntity<Order> create(@Valid @RequestBody OrderRequest request) {
    // request.shippingAddress.street == "" passes validation silently —
    // @NotBlank on AddressRequest's own fields never even runs.
}

// Fix: cascade explicitly.
class OrderRequest {
    @NotNull String customerId;
    @Valid AddressRequest shippingAddress; // now nested constraints are checked too
}
```

**Why it's a trap:** the top-level DTO looks fully annotated, compiles cleanly, and passes every
test that only exercises top-level fields — the gap only surfaces once bad nested data reaches
the database or a downstream system, past a validation layer everyone assumed had already
caught it.

## 🔴 Expert / Open

### Q26. How would you migrate an existing monolith to hexagonal architecture incrementally, without a big-bang rewrite?
Start at the seams that already exist naturally — pick one bounded, well-understood module
(often the one changing most often, since that's where the payoff compounds fastest) and define
its ports first: what does this module need from the outside world, and what does it offer? Move
its business logic behind those interfaces without changing behavior, backfill adapter
implementations for what's already there (the existing JPA repository becomes the first
implementation of a new port interface), and add a characterization test suite first if one
doesn't exist, so the refactor has a safety net. Repeat module by module; the mistake to avoid is
attempting to define the "final" domain model for the whole system up front — that's exactly the
kind of big design-up-front effort that stalls halfway through a migration and never ships. Use
an ArchUnit rule from day one on the *converted* modules to prevent regression, even while
unconverted modules still violate it.

### Q27. Design a plugin-style extension system in Spring so new behavior can be added without modifying existing code.
Define an interface (a port) representing the extension point — e.g. `NotificationChannel` with
`send(Notification)` and `supports(ChannelType)`. Let Spring's component scanning collect every
implementation automatically via `List<NotificationChannel>` injected into a dispatcher bean,
and have the dispatcher select the right one(s) by calling `supports()` rather than hard-coding a
type check. Adding email, SMS, and push notification support is then a matter of adding three
new `@Component`-annotated classes — the dispatcher code doesn't change, satisfying the
open/closed principle. If plugins need to be truly external (loaded from separate jars at
runtime, not compiled into the main artifact), Spring's own class scanning won't reach across
classloader boundaries cleanly — that's the point where `ServiceLoader` or an explicit plugin
framework (with its own classloader-per-plugin strategy) becomes necessary instead.

### Q28. How do you decide between an AOP-based cross-cutting concern (like `@Transactional`, `@Cacheable`, or a custom annotation) and writing it explicitly in the method body?
AOP earns its cost when the concern is genuinely orthogonal to business logic and applies
uniformly across many methods with the same rule — transactions, caching, and audit logging are
the textbook cases because the "how" is identical everywhere it's used and the annotation makes
the intent visible at the call site. The cost is real, though: AOP introduces the proxy
limitations from Q7/Q8/Q14 (self-invocation, private methods, `final` classes), makes the actual
execution flow less obvious from reading the method body alone, and can surprise a maintainer
who doesn't know the annotation triggers a whole aspect. Prefer explicit code when the concern
varies meaningfully case-by-case, when debuggability during an incident matters more than
DRY-ness, or when the team has already been burned by an AOP proxy gotcha in this exact codebase
— explicit code that says exactly what it does is sometimes the more senior choice, not the
less sophisticated one.

## 🎯 Real-world scenarios

### S1. A service works perfectly in local development but fails immediately after deployment
- **Symptoms:** All local and CI tests pass; the same jar fails to start, or starts but errors on
  first request, once deployed to a real environment.
- **Diagnosis:** Compare configuration first, not code — check active profile
  (`spring.profiles.active`), environment variables, and whichever `application-{profile}.yml`
  is actually being loaded in that environment (Q16's precedence order). Check for
  environment-specific resources assumed to exist (a database, a secrets file, a network path)
  that simply aren't reachable from the deployed environment the way they are from a developer's
  machine.
- **Example:**
  ```yaml
  # application.yml, checked into the repo — a "dev" profile pointing at an in-memory DB.
  spring:
    profiles:
      active: dev
  ---
  spring:
    config:
      activate:
        on-profile: dev
    datasource:
      url: jdbc:h2:mem:testdb   # fine for local dev, and silently still active if
                                 # SPRING_PROFILES_ACTIVE=prod is never set on deploy
  ```
- **Resolution:** Once the actual missing/different config or unreachable dependency is
  identified, fix the specific gap — usually a missing environment variable, an unresolved
  connection string, or a firewall/network policy blocking a call that worked locally.
- **Prevention:** Keep environments as close to identical as practical (same containerized
  runtime locally and in production via Docker, per module 6), and fail fast and loudly at
  startup (a health check or `@PostConstruct` sanity check) rather than on first user-facing
  request.

### S2. A REST API is slow, but only in production — the same endpoint is fast locally and in staging
- **Symptoms:** p99 latency in production is far worse than staging for an endpoint whose logic
  hasn't changed, and it's not consistently slow — it varies.
- **Diagnosis:** Production has data volume and concurrency staging doesn't — check whether the
  slow path involves a database query whose execution plan degrades with real data size (missing
  index that didn't matter on a small staging dataset), or whether it's contention (Q10, Q16's
  scenario S16 in module 1) only reproducible under production's actual concurrent load.
  Distributed tracing (S15) or an APM tool's flame graph will usually localize the slow span
  directly.
- **Example:**
  ```sql
  -- Fast in staging (10k rows) — a full scan there is invisible at that size.
  select * from orders where customer_id = ?;

  -- Same query in production (50M rows): explain confirms a sequential scan,
  -- because customer_id was never indexed.
  -- Seq Scan on orders (cost=0.00..812345.00 rows=1 width=128)

  create index idx_orders_customer_id on orders(customer_id); -- the actual fix
  ```
- **Resolution:** Add the missing index, fix the N+1 query (Q23), or address the specific
  contention point once identified from the trace — resist the urge to guess and optimize
  something the trace didn't actually implicate.
- **Prevention:** Load-test with production-scale data volume before shipping a new query path,
  and keep distributed tracing enabled by default in production so this diagnosis takes minutes,
  not a multi-day investigation.

### S3. Changes to `application.properties` don't seem to take effect after a config update
- **Symptoms:** A configuration value was changed and redeployed, but the running application
  still behaves according to the old value.
- **Diagnosis:** Check the precedence order (Q16) — a higher-priority source (an environment
  variable set on the container, a command-line argument baked into the startup script) may be
  overriding the file that was edited. Also check whether the *wrong profile* is active, so the
  edited file isn't even the one being loaded, or whether the deployment actually shipped the new
  config (a stale container image, a config baked in at build time rather than mounted at
  runtime).
- **Example:**
  ```bash
  # application.properties was edited and redeployed:
  # app.timeout=9000

  # ...but the container's own environment still sets the old value, which wins:
  $ env | grep APP_TIMEOUT
  APP_TIMEOUT=3000   # an OS env var beats the properties file every time (Q16)
  ```
- **Resolution:** Once the actual active source is identified, edit that one — or, if the design
  goal is "config should always come from this one file," remove the higher-priority override
  causing the conflict.
- **Prevention:** Log the active profile and a summary of key config values at startup, and
  standardize on one clear source of truth per environment (e.g. "container env vars always win,
  and that's the only place secrets/env-specific values are set") so this ambiguity doesn't
  recur.

### S4. A Spring Boot service crashes or becomes unresponsive under heavy traffic
- **Symptoms:** The service handles normal load fine but crashes, restarts, or stops responding
  entirely once traffic crosses some threshold.
- **Diagnosis:** Distinguish resource exhaustion (heap — module 1's OOM scenario; thread pool —
  Q7 in module 1, S7 below; connection pool — S7 below) from an actual bug that only triggers
  under concurrency (a race condition, Q10's singleton mutable-state trap). Metrics and a thread
  dump taken *during* the incident (not after restart, which loses the evidence) distinguish
  these quickly.
- **Example:**
  ```
  "http-nio-8080-exec-142" #142 waiting for monitor entry
     java.lang.Thread.State: BLOCKED (on object monitor)
     at com.example.ReportService.generate(ReportService.java:22)
     - waiting to lock <0x000000076ab62208> (a com.example.ReportService)
  # 140+ request threads BLOCKED on the same singleton's monitor — Q10's mutable-field
  # trap turning into a full request-handling stall under real concurrency.
  ```
- **Resolution:** Depends entirely on which resource is exhausted — scale the relevant pool/
  heap/instance count, or fix the concurrency bug if that's what a thread dump actually shows.
- **Prevention:** Load-test to find the actual breaking point before production traffic finds it,
  and put circuit breakers (Q22) and rate limiting in front of the service so a traffic spike
  degrades gracefully instead of crashing outright.

### S5. The application context fails to start with a "no unique bean" or bean conflict error
- **Symptoms:** Startup fails with `NoUniqueBeanDefinitionException` or similar, usually right
  after adding a second implementation of an interface that used to have exactly one.
- **Diagnosis:** Spring can't decide which bean to inject when more than one candidate matches
  an injection point's type with no further qualification — this is a design signal, not just a
  wiring bug, since it means the code was written assuming there'd only ever be one
  implementation.
- **Example:**
  ```
  Parameter 0 of constructor in com.example.OrderController required a single bean,
  but 2 were found:
      - creditCardPayment
      - payPalPayment
  ```
  ```java
  // Fix: be explicit about intent instead of leaving it ambiguous.
  @Primary
  @Component class CreditCardPayment implements Payment { }

  // or, if the consumer genuinely wants all of them (Q21's Strategy pattern):
  OrderController(List<Payment> payments) { ... }
  ```
- **Resolution:** If genuinely one should be the default, mark it `@Primary`. If the consumer
  needs a *specific* one, use `@Qualifier("beanName")`. If the consumer actually wants *all* of
  them, change the injection point from the interface type to `List<Interface>` instead of
  fighting the ambiguity.
- **Prevention:** When adding a second implementation of an existing interface, immediately
  check every injection point of that interface and decide deliberately (primary, qualified, or
  collected as a list) rather than letting the compiler/container error force a rushed fix.

### S6. An API endpoint intermittently returns `401 Unauthorized` for requests that should be authenticated
- **Symptoms:** The same client, same credentials, sometimes gets a successful response and
  sometimes gets `401`, with no obvious pattern from the client side.
- **Diagnosis:** Common causes in a Spring Security context: token expiry racing with request
  timing (a token that expires mid-session, especially short-lived JWTs without proper refresh
  handling); the security context not propagating across an async boundary (Q13's `@Async`
  scenario, if the endpoint does async work before the security check); or a load-balanced
  deployment where session-based auth isn't actually shared/sticky across instances, so a request
  landing on a different instance than the one that authenticated it appears unauthenticated.
- **Example:**
  ```java
  @Async
  public void enforceAndAudit(String userId) {
      // SecurityContextHolder is empty on this thread (Q13) — an authorization check
      // placed here fails unpredictably, only on requests that happen to hit this path.
      if (SecurityContextHolder.getContext().getAuthentication() == null) {
          throw new AccessDeniedException("no security context on async thread");
      }
  }
  ```
- **Resolution:** Fix token refresh logic and expiry buffers for the first cause; apply
  `DelegatingSecurityContextAsyncTaskExecutor` for the second; move to stateless
  (JWT-based, not session-based) authentication or shared session storage for the third.
- **Prevention:** Prefer stateless authentication for horizontally-scaled services specifically
  to avoid the sticky-session class of bug, and add explicit tests for auth behavior across
  async code paths.

### S7. Requests start failing with database connection pool exhaustion errors under moderate load
- **Symptoms:** Errors like "connection is not available, request timed out" from the connection
  pool (HikariCP by default), correlating with periods of higher-than-usual request volume that
  aren't extreme.
- **Diagnosis:** Check for connections being held longer than necessary — a common cause is a
  `@Transactional` method doing slow non-database work (an external API call) *inside* the
  transaction boundary, holding a connection the whole time it's waiting on something unrelated.
  Also check the pool size itself against actual concurrent demand, and check for leaked
  connections (a manually-managed `Connection` not closed in a `finally`/try-with-resources on
  an exception path).
- **Example:**
  ```java
  @Transactional
  public void placeOrder(Order order) {
      repository.save(order);          // DB connection acquired for the transaction
      shippingClient.notify(order);    // slow external HTTP call — the connection stays
                                        // checked out for its entire duration, for no reason
  }

  // Fix: move the external call outside the transactional boundary.
  public void placeOrder(Order order) {
      saveOrder(order);                // short transaction — connection released quickly
      shippingClient.notify(order);    // no DB connection held while waiting on the network
  }
  @Transactional
  void saveOrder(Order order) { repository.save(order); }
  ```
- **Resolution:** Move non-database work outside the transaction boundary so connections are held
  only as long as actually needed, fix any connection leak, and size the pool deliberately (not
  just to the largest number that "feels safe") against measured concurrent demand.
- **Prevention:** Keep `@Transactional` methods focused purely on database work, and monitor
  connection pool active/idle/pending metrics so exhaustion is visible as a trend before it
  becomes an outage.

### S8. Calls to a downstream microservice occasionally fail, and those failures cascade into unrelated parts of the system going down too
- **Symptoms:** One downstream dependency becomes slow or flaky, and shortly after, seemingly
  unrelated features in the calling service start failing or timing out too.
- **Diagnosis:** This is the classic cascading-failure pattern — callers block waiting on the
  slow dependency, exhausting a shared thread pool (Q7 in module 1) that other, healthy request
  paths also depend on, so one dependency's slowness takes down capacity for everything.
- **Example:**
  ```java
  // No timeout configured at all — a hung downstream can block this thread forever.
  public Inventory checkInventory(String sku) {
      return restTemplate.getForObject("/inventory/" + sku, Inventory.class);
  }

  // Fix: an explicit timeout plus a circuit breaker (Q22), so one flaky dependency
  // fails fast instead of exhausting the shared request-handling thread pool.
  RestTemplate client = restTemplateBuilder
      .setConnectTimeout(Duration.ofSeconds(2))
      .setReadTimeout(Duration.ofSeconds(2))
      .build();
  ```
- **Resolution:** Add a circuit breaker (Q22) around the specific call so failures there fail
  fast instead of piling up threads, add a sensible timeout (never call a downstream service with
  no timeout at all), add retry with backoff for transient failures specifically (not for every
  failure indiscriminately — retrying a genuinely down service just adds more load to it), and
  isolate the thread pool used for that call from the pool serving unrelated requests (bulkhead
  pattern) so its exhaustion can't starve everything else.
- **Prevention:** Treat "what happens when this downstream call is slow or down" as a required
  design question for every new external call, not an afterthought once it causes an incident.

### S9. Users report seeing old/stale behavior for a while after a new version is deployed
- **Symptoms:** A bug fix or feature change is deployed, but some users report the old behavior
  persisting for minutes to hours afterward.
- **Diagnosis:** Check for a rolling deployment where old and new instances briefly serve traffic
  simultaneously (expected, temporary, and usually fine) versus a genuine caching layer (CDN,
  HTTP cache headers, an application-level cache like `@Cacheable`) still serving pre-deploy
  responses well past when the rollout finished.
- **Example:**
  ```java
  @Cacheable("pricingRules")
  public PricingRule getRule(String sku) { return repository.findRule(sku); }
  // A fix to the pricing logic was deployed, but this cache has no TTL and nothing
  // evicts it on deploy — it keeps serving the pre-fix PricingRule for hours.

  // Fix: evict explicitly whenever the underlying rule changes.
  @CacheEvict(value = "pricingRules", allEntries = true)
  public void onPricingRulesChanged() { }
  ```
- **Resolution:** For rolling-deploy overlap, this is often expected and self-resolves — confirm
  the rollout actually completed. For a caching issue, either invalidate the relevant cache keys
  on deploy, shorten the TTL for data that changes with releases, or add a cache-busting
  mechanism (versioned URLs/ETags) tied to the deployed version.
- **Prevention:** Document expected propagation time for each caching layer in the stack so "is
  this actually a bug" has a fast answer, and prefer short TTLs plus explicit invalidation over
  long TTLs for anything that changes with deployments.

### S10. A secrets scanner (or a security review) flags database credentials committed in `application.properties`
- **Symptoms:** Database passwords, API keys, or other secrets are found in plaintext in a
  properties/YAML file checked into version control.
- **Diagnosis:** This is a straightforward but urgent finding — anyone with repository access
  (including, for a public repo, the entire internet, plus anyone who ever cloned it, since git
  history retains deleted content) has the credential.
- **Example:**
  ```properties
  # application.properties — committed to the repo, visible in every clone and every
  # past commit even after it's later "removed" from the latest revision.
  spring.datasource.password=Sup3rSecret!
  ```
  ```bash
  # Rotate immediately, then move it out of version control entirely.
  export SPRING_DATASOURCE_PASSWORD=$(vault kv get -field=password secret/db)
  ```
- **Resolution:** Rotate the exposed credential immediately — removing it from the current file
  is not sufficient, since it remains in git history. Move secrets to environment variables
  injected at deploy time, or a dedicated secrets manager (Vault, AWS Secrets Manager, or the
  orchestrator's native secrets mechanism), referenced from configuration rather than embedded in
  it. Scrub git history if the exposure is severe enough to warrant it (coordinate this
  carefully — rewriting history affects every clone).
- **Prevention:** Add a pre-commit or CI secrets scanner so this can't merge in the first place,
  and treat "secrets never live in version control, full stop" as a non-negotiable rule enforced
  by tooling, not just code review discipline.

### S11. A `@Transactional` method fails partway through — what actually happens to the changes already made?
- **Symptoms:** A multi-step operation inside a transaction (update A, then update B, then B
  fails) — the question is what state the database ends up in.
- **Diagnosis/explanation:** By default, Spring rolls back the *entire* transaction on an
  unchecked exception (any `RuntimeException`) — none of the changes persist, including the
  earlier successful update to A, because the whole block is atomic. Critically, Spring does
  **not** roll back by default on a *checked* exception — that requires explicitly configuring
  `@Transactional(rollbackFor = Exception.class)` or the specific checked type, which is a common
  and dangerous gotcha: a team assumes any exception rolls back the transaction, then a checked
  exception path silently commits a half-completed operation.
- **Example:**
  ```java
  @Transactional
  public void transfer(Account from, Account to, BigDecimal amount)
          throws InsufficientFundsException {
      from.debit(amount);
      to.credit(amount);
      if (from.getBalance().signum() < 0) {
          throw new InsufficientFundsException(); // a CHECKED exception
          // By default this does NOT roll back — the debit above silently commits,
          // leaving `from` overdrawn with no corresponding record of why.
      }
  }

  // Fix: be explicit about which exceptions must trigger a rollback.
  @Transactional(rollbackFor = InsufficientFundsException.class)
  public void transfer(...) throws InsufficientFundsException { /* ... */ }
  ```
- **Resolution:** Audit every `@Transactional` boundary that can throw a checked exception and
  confirm rollback behavior matches intent explicitly, rather than relying on the unchecked-only
  default.
- **Prevention:** Default new transactional methods to `rollbackFor = Exception.class` unless
  there's a specific, documented reason a checked exception should still commit — the
  unchecked-only default is a footgun best overridden deliberately every time.

### S12. During an incident, expected log output is missing or incomplete in production
- **Symptoms:** A team investigating an incident finds that the specific log lines they need
  (or any logs at all, for a window of time) simply aren't present in the log aggregation system.
- **Diagnosis:** Check the configured log level in that environment first — a common cause is
  production running at `WARN` or `ERROR` while the missing diagnostic detail was logged at
  `DEBUG`/`INFO` and never emitted. Also check for log shipping failures (the app logged locally
  fine, but the shipper/agent forwarding logs to the aggregator was itself down or backed up) and
  for asynchronous logging appenders that can drop or delay messages under load.
- **Example:**
  ```yaml
  # production logging config — the detail the incident needs was never emitted at all.
  logging:
    level:
      root: WARN
  ```
  ```bash
  # Bump the relevant logger live, without a redeploy, to capture the next occurrence:
  curl -X POST localhost:8080/actuator/loggers/com.example.orders \
    -H 'Content-Type: application/json' -d '{"configuredLevel": "DEBUG"}'
  ```
- **Resolution:** Use `/actuator/loggers` (Q15) to bump the relevant logger to `DEBUG` live,
  without a redeploy, to capture detail on the *next* occurrence if this one is already missed;
  fix the log-shipping pipeline if that's the actual gap.
- **Prevention:** Default to `INFO` in production (not `WARN`) for anything that could matter
  during an incident, and monitor the log pipeline itself (shipping lag, drop rate) as its own
  health metric — "logs exist locally but never arrived" is otherwise invisible until you need
  them.

### S13. Application startup time has crept up significantly, slowing down deployments and autoscaling
- **Symptoms:** A service that used to start in a few seconds now takes 30+ seconds, which
  matters directly for rolling deployments and for autoscaling responsiveness under a traffic
  spike.
- **Diagnosis:** Spring Boot exposes a startup report (`spring.application.admin.enabled` /
  the auto-configuration report, or just timestamped startup logs) showing which
  auto-configuration classes and beans took the longest to initialize — usually the actual
  culprit is component scanning across an unnecessarily broad package, an eager (non-lazy) bean
  doing slow I/O at startup (warming a cache, pinging every downstream dependency), or simply
  accumulated dependencies that pulled in auto-configuration nobody uses.
- **Example:**
  ```
  2026-09-16T10:00:01  Initializing ExecutorService 'applicationTaskExecutor'
  2026-09-16T10:00:14  Warming cache: PricingCacheWarmer  (+13.2s)   <-- the culprit
  2026-09-16T10:00:15  Tomcat started on port 8080
  ```
  ```java
  // Fix: don't block startup on a slow, non-essential warm-up.
  @EventListener(ApplicationReadyEvent.class)
  void warmCacheAfterStartup() { pricingCache.warm(); } // runs after the app is already serving
  ```
- **Resolution:** Narrow `@ComponentScan` base packages if scanning too broadly, defer genuinely
  slow initialization (move a cache warm-up to run after startup completes, not blocking it), and
  exclude unused auto-configuration classes explicitly.
- **Prevention:** Track startup time as a metric over time in CI, the same way you'd track build
  time or bundle size, so a regression is caught at the PR that introduced it rather than
  discovered months later as "it's always been kind of slow now."

### S14. A long-running background job occasionally gets killed mid-execution during a deployment
- **Symptoms:** A batch job or async task that takes minutes sometimes ends up in a
  half-completed state, correlating with deployment times.
- **Diagnosis:** This is a graceful-shutdown gap — the deploying orchestrator sends a termination
  signal to the old instance, and if the application doesn't wait for in-flight work to finish
  (or reject new work and drain first), a job mid-execution is simply killed along with the
  process.
- **Example:**
  ```java
  @Scheduled(fixedDelay = 60000)
  void runNightlyExport() { exportService.exportAll(); } // no checkpointing, no drain —
                                                            // a SIGTERM mid-run just kills it
  ```
  ```yaml
  server:
    shutdown: graceful
  spring:
    lifecycle:
      timeout-per-shutdown-phase: 60s
  ```
- **Resolution:** Enable graceful shutdown (`server.shutdown=graceful` in recent Spring Boot,
  with an appropriate `spring.lifecycle.timeout-per-shutdown-phase`), and for genuinely
  long-running jobs specifically, move them out of the request-handling process entirely into a
  dedicated job runner/queue consumer that can be drained independently, with checkpointing so a
  forced kill resumes rather than restarts from zero.
- **Prevention:** Treat "what happens to in-flight work during a deploy" as a required design
  question for anything long-running, the same way S8 treats downstream-call failure as a
  required question for anything calling out.

### S15. A bug spans multiple microservices, and it's unclear which service in the chain is actually responsible
- **Symptoms:** A user-facing error or latency issue clearly happens somewhere in a multi-service
  request chain, but each individual service's own logs look unremarkable in isolation.
- **Diagnosis:** Without a shared trace ID propagated across every hop, each service's logs are
  isolated islands with no way to correlate "this specific user request" across all of them —
  the diagnosis *is* the gap: distributed tracing isn't in place, or the trace context isn't
  being propagated across one specific hop (often a message queue boundary, where trace headers
  don't automatically carry over the way HTTP headers do with the right instrumentation).
- **Example:**
  ```
  service-a: traceId=abc123 spanId=001  -- HTTP call to service-b, headers propagated
  service-b: (no trace context)         -- consumed from a Kafka message instead,
                                            headers were never carried over into the payload
  # service-b's own logs look "clean" in isolation — the actual slow/broken hop is
  # invisible without a trace ID connecting the two services' logs together.
  ```
  ```java
  // Fix: propagate trace context through message metadata too, not just HTTP headers.
  record OrderEvent(String orderId, String traceId, String spanId) { }
  ```
- **Resolution:** Instrument the chain with a tracing standard (OpenTelemetry, propagating trace/
  span IDs through HTTP headers and, deliberately, through message metadata for async hops),
  ship traces to a backend (Jaeger, Zipkin, or a vendor APM), and use the resulting trace to
  pinpoint which specific hop introduced the latency or error.
- **Prevention:** Make distributed tracing part of the baseline for every new service from day
  one, not something retrofitted after the first cross-service incident that couldn't be
  diagnosed — retrofitting it consistently across every hop, including async ones, is far more
  work than building it in from the start.

### S16. A deployment causes a burst of failed requests for the few seconds around the old instance stopping
- **Symptoms:** Error rate spikes briefly, specifically during each rolling deployment, for
  requests that happened to be in flight when an old instance was terminated.
- **Diagnosis:** The orchestrator is likely sending `SIGTERM` and then a hard kill shortly after,
  with the application not given (or not using) time to stop accepting new connections, finish
  in-flight requests, and deregister from the load balancer *before* the process actually exits.
- **Example:**
  ```yaml
  server:
    shutdown: graceful
  # Kubernetes: give the app time to deregister from the service mesh/load balancer
  # BEFORE the SIGTERM that actually stops it is even sent.
  lifecycle:
    preStop:
      exec:
        command: ["sh", "-c", "sleep 5"]
  ```
- **Resolution:** Enable Spring Boot's graceful shutdown so in-flight requests are allowed to
  complete before the JVM exits, ensure the load balancer/service mesh deregisters the instance
  *before* traffic is cut (not simultaneously), and give the orchestrator's termination grace
  period enough margin for both steps to actually finish (a `preStop` hook adding a short delay
  before `SIGTERM` is a common Kubernetes-specific fix — see module 6).
- **Prevention:** Treat zero-downtime deployment as a tested property, not an assumption — a
  simple load test that keeps sending traffic through a deployment and asserts zero failed
  requests catches a graceful-shutdown regression immediately, rather than it being discovered as
  a recurring blip nobody investigated.

## 📌 Cheat-sheet

- **DI** = class declares needs, container supplies them → loose coupling, testability, no hand-rolled `new`.
- **Design patterns inside Spring**: DI/IoC (injection), Singleton (default scope), Factory (`ApplicationContext`), Strategy (multi-impl injection), Proxy (`@Transactional`, security, AOP), Template (`JdbcTemplate`).
- **`@Transactional` self-invocation and private methods** = silently no-op, because it's proxy-based — fix via self-injection, another bean, or AspectJ weaving.
- **`flush()` ≠ `commit()`** — flush syncs to DB early, doesn't end the transaction.
- **Bean scopes**: `singleton` = one shared instance (mutable instance fields = cross-request shared state bug); `prototype`/`request`/`session` scope differently.
- **Constructor injection > field injection**: immutable, explicit, testable without a container.
- **Circular deps**: resolvable for setter/field injection (early-reference cache), *not* for pure constructor injection — fails fast at startup instead.
- **`@Async` drops the security context** by default — use `DelegatingSecurityContextAsyncTaskExecutor`.
- **JDK proxy** needs an interface; **CGLIB** subclasses but can't proxy `final` classes/methods — AOP silently skipped either way if violated.
- **Actuator**: expose `health`/`info`/`metrics`/`loggers` externally if needed; never expose `env`/`beans`/`heapdump` publicly.
- **Config precedence** (high→low): CLI args → env vars → profile-specific file → base file → code defaults.
- **`@ControllerAdvice`** centralizes exception→HTTP-status mapping; never leak stack traces to clients.
- **CORS**: wildcard origin + `allowCredentials(true)` is rejected — must be an explicit allow-list.
- **Hexagonal layout**: `domain` (no framework deps) → `application` (use cases + ports) → `infrastructure` (adapters); enforce with ArchUnit.
- **Circuit breaker** (Resilience4j): fail fast on a flaky dependency instead of piling up threads waiting on it — prevents cascading failure.
- **`@Transactional` rolls back on unchecked exceptions by default, NOT checked ones** — set `rollbackFor` explicitly.
- **N+1 queries**: lazy associations fetched in a loop → 1+N queries; fix with a query-specific `JOIN FETCH`/entity graph, not a blanket `EAGER` fetch type.
- **`@Cacheable` + mutable return value**: the cache stores the reference, not a copy — a caller mutating a cached `List`/DTO corrupts every future cache hit.
- **`@Valid` doesn't cascade**: a nested object field needs its own `@Valid` annotation, or its constraints are silently never checked.
- **Graceful shutdown**: `server.shutdown=graceful` + orchestrator grace period, so in-flight requests finish and the LB deregisters before the process exits.
