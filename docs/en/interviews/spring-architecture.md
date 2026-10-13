# Spring & Architecture

## 🟢 Fundamentals

### Core & configuration

#### Q1. What is Dependency Injection in Spring, and what are its advantages?

DI means a class declares what it needs (via constructor, setter, or field) and the Spring
container supplies (injects) that dependency instead of the class creating it itself.
Advantages: loose coupling between classes, much easier unit testing (you can inject mocks
without touching production wiring), more flexible configuration (swap an implementation
without touching the consumer), and container-managed object lifecycles instead of hand-rolled
`new` calls scattered through the codebase.

**Example:**

```java
// Without DI: the class builds (and is welded to) its collaborator.
class InvoiceService {
    private final Mailer mailer = new SmtpMailer("smtp.corp");
}

// With DI: the container supplies it; a test passes a fake.
@Service
class InvoiceService {
    private final Mailer mailer;
    InvoiceService(Mailer mailer) { this.mailer = mailer; }
}
new InvoiceService(msg -> {});   // unit test: no container, no SMTP
```

#### Q2. What's the difference between `@Component`, `@Service`, and `@Repository`?

All three register a class as a Spring-managed bean via component scanning. `@Component` is
the generic form; `@Service` and `@Repository` are semantic specializations — `@Service` marks
a service-layer bean (mostly documentation/intent), and `@Repository` additionally enables
Spring's exception translation for the data-access layer, converting driver-specific exceptions
into Spring's unchecked `DataAccessException` hierarchy so callers don't need to catch
vendor-specific SQL exceptions.

**Example:**

```java
@Repository   // registers PersistenceExceptionTranslationPostProcessor's proxy around this bean
class UserDao {
    @PersistenceContext EntityManager em;

    void insert(User u) {
        em.persist(u);
        em.flush();
        // duplicate key: Hibernate's PersistenceException/ConstraintViolationException reaches the
        // caller as Spring's DataIntegrityViolationException (a DataAccessException) -- no vendor code to catch.
    }
}
```

With `@Component` instead, the class is still a bean but the translation proxy is not applied, so raw
JPA/Hibernate exceptions leak out. (`JdbcTemplate` and Spring Data repositories translate on their own.)

#### Q3. What's the difference between a `@Configuration` class and a `@Component` class that declares `@Bean` methods?

Both can hold `@Bean` methods and both are picked up by component scanning, but they behave
differently when one `@Bean` method calls another. A `@Configuration` class runs in **full
mode**: Spring subclasses it with CGLIB, and that subclass intercepts every `@Bean` method call so
that `jdbcTemplate(dataSource())` returns the *same singleton* `DataSource` bean the container
already created instead of executing the method body again. A plain `@Component` (or a
`@Configuration(proxyBeanMethods = false)`) runs in **lite mode**: no subclass, so an
inter-`@Bean` call is an ordinary Java method call and silently builds a *second, unmanaged*
instance — two connection pools, two caches, two "singletons" — with no error. Rule of thumb:
use `@Configuration` when `@Bean` methods call each other; use `proxyBeanMethods = false` (Spring
Boot's own auto-configurations do) when they don't, since it skips the CGLIB subclass and
speeds startup; or sidestep the whole question by taking the dependency as a method parameter
(`JdbcTemplate jdbcTemplate(DataSource ds)`), which works in both modes.

**Example:**

```java
@Configuration            // full mode: CGLIB intercepts dataSource()
class FullCfg {
    @Bean DataSource dataSource() { return new HikariDataSource(); }
    @Bean JdbcTemplate jdbc()     { return new JdbcTemplate(dataSource()); } // same singleton
}

@Component                // lite mode: plain Java call -> a SECOND HikariDataSource, unmanaged
class LiteCfg {
    @Bean DataSource dataSource() { return new HikariDataSource(); }
    @Bean JdbcTemplate jdbc()     { return new JdbcTemplate(dataSource()); }
}

@Bean JdbcTemplate jdbc(DataSource ds) { return new JdbcTemplate(ds); }  // safe in both modes
```

#### Q4. What is Spring Boot, and how does it differ from plain Spring?

Spring Boot is an opinionated layer on top of the Spring Framework that removes most manual
setup. Where plain Spring needs extensive XML or Java configuration and a separately
provisioned server, Spring Boot auto-configures beans based on the dependencies on the
classpath, ships an embedded server (Tomcat, Jetty, or Undertow) so the app runs as a
standalone jar, and bundles production-ready features (metrics, health checks, externalized
configuration) out of the box — which is also why it's the default choice for microservices.

**Example:**

```xml
<!-- pom.xml: one starter replaces a dozen version-matched dependencies -->
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

```java
@SpringBootApplication
public class App {
    public static void main(String[] args) { SpringApplication.run(App.class, args); }
}
// ./mvnw package && java -jar target/app.jar  -> embedded Tomcat on :8080, no WAR, no external server
```

#### Q5. What does `@SpringBootApplication` actually do?

It's a convenience annotation bundling three others on the main class: `@Configuration` (marks
the class as a source of bean definitions), `@EnableAutoConfiguration` (turns on
classpath-based auto-configuration), and `@ComponentScan` (scans the current package and
sub-packages for components). Understanding it as three separate annotations matters the
moment you need to customize just one of them — e.g. excluding a specific auto-configuration
class without giving up component scanning.

**Example:**

```java
// @SpringBootApplication is shorthand for these three:
@Configuration
@EnableAutoConfiguration
@ComponentScan                       // scans com.acme.shop and below -- put the class at the root package
class App {}

// Customize only one part, e.g. drop an auto-configuration but keep the rest:
@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)
class App {}
// Debug what was applied: java -jar app.jar --debug   (prints the conditions evaluation report)
```

#### Q6. `@Value` vs `@ConfigurationProperties` — when do you use which?

`@Value("${app.timeout}")` injects one property into one field and is fine for a single
isolated value or for a SpEL expression. Once you have a *group* of related settings,
`@ConfigurationProperties(prefix = "app.payment")` bound onto a class (or, better, an immutable
`record`) is the better tool: the whole group is bound to one typed object, **relaxed binding**
maps `app.payment.max-retries`, `APP_PAYMENT_MAXRETRIES` and `maxRetries` to the same field,
values are converted to real types (`Duration`, `DataSize`, enums, lists, nested objects),
`@Validated` plus Bean Validation annotations makes the application **fail at startup** on a
missing or invalid setting instead of at first use, and Spring Boot generates IDE metadata for
autocompletion. The trade-offs of `@Value`: strings scattered across the codebase with no
single place to see what an application accepts, no fail-fast validation, and stricter matching
of property names. Practical point: a typo'd or missing `@ConfigurationProperties` value is
caught at boot, while a typo'd `@Value` default can quietly ship a wrong value to production.

**Example:**

```java
@ConfigurationProperties(prefix = "app.payment")
@Validated
record PaymentProps(@NotBlank String url,
                    @DefaultValue("3") @Min(1) int maxRetries,
                    @DefaultValue("2s") Duration timeout) {}
// @EnableConfigurationProperties(PaymentProps.class) or @ConfigurationPropertiesScan on the app class
```

```yaml
app.payment:
  url: https://pay.example.com
  max-retries: 5        # APP_PAYMENT_MAXRETRIES=5 works too; omit url -> startup fails, not first call
```

### Architecture

#### Q7. What is hexagonal (ports & adapters) architecture, and what problem does it solve?

Hexagonal architecture puts the domain/business logic at the center, exposing **ports**
(interfaces) that describe what the domain needs or offers, with **adapters** implementing
those ports for specific technologies — a REST controller and a message listener might both be
inbound adapters calling the same use case; a JPA repository and an in-memory fake might both
be outbound adapters implementing the same persistence port. The problem it solves: without
this boundary, business logic tends to accumulate framework and infrastructure dependencies
(JPA annotations on domain entities, `HttpServletRequest` leaking into business rules), which
makes the core logic harder to test in isolation and harder to change infrastructure without
touching business rules.

**Example:**

```java
// domain/application: no Spring, no JPA
public interface OrderRepository { Optional<Order> byId(OrderId id); void save(Order o); }  // outbound port
public class PlaceOrder {                                                                  // use case (inbound port)
    private final OrderRepository orders;
    public PlaceOrder(OrderRepository orders) { this.orders = orders; }
    public void handle(Cart cart) { orders.save(Order.from(cart)); }
}

// infrastructure: adapters
@Repository class JpaOrderRepository implements OrderRepository { /* Spring Data / EntityManager */ }
class InMemoryOrderRepository implements OrderRepository { /* HashMap, used in unit tests */ }
@RestController class OrderController { /* inbound adapter: HTTP -> PlaceOrder.handle(...) */ }
```

## 🟡 Senior traps

### Bean container & lifecycle

#### Q8. Why is constructor injection generally preferred over field injection?

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

#### Q9. What are Spring bean scopes, and what's the thread-safety implication of getting one wrong?

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

#### Q10. Walk through the Spring bean lifecycle, and how does Spring resolve circular dependencies?

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

#### Q11. What happens, step by step, when a Spring Boot application starts?

**Answer:** `SpringApplication.run()` does roughly this: (1) picks the application type (servlet, reactive, none) from the
classpath and loads the `ApplicationContextInitializer`s and `ApplicationListener`s declared in
`META-INF/spring.factories`; (2) prepares the `Environment`: reads `application.yml`, profiles, environment variables and
command-line arguments in precedence order (see [Spring Q25](spring-architecture.md)); (3) prints the banner and creates
the `ApplicationContext`; (4) **loads bean definitions**: `@ComponentScan` finds `@Component`/`@Service`/`@Repository`
classes, `@Configuration` classes are parsed, and auto-configuration classes listed in
`META-INF/spring/...AutoConfiguration.imports` are evaluated against `@Conditional...` rules (a `DataSource` bean appears
only if a driver is on the classpath and you did not define your own); (5) `BeanFactoryPostProcessor`s run, then beans are
instantiated, injected and post-processed (`BeanPostProcessor`s create the `@Transactional`/`@Async` proxies, see
[Spring Q10](spring-architecture.md)); (6) for a web app the embedded Tomcat is created and started; (7) `SmartLifecycle`
beans start, `ContextRefreshedEvent` fires, then `CommandLineRunner`/`ApplicationRunner` beans execute and
`ApplicationReadyEvent` is published; only then is the readiness probe `UP`. Shutdown mirrors it: stop accepting traffic,
drain in-flight requests (`server.shutdown=graceful`), destroy beans in reverse dependency order.
A slow startup is almost always step 4 or 5: classpath scanning, eager heavy beans (connection pools, cache warm-up) or a
`@PostConstruct` that calls a remote service.

**Example:**

```java
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);          // steps 1-7
    }
    @Bean ApplicationRunner warmUp(SlotCache cache) {    // step 7: after the context is ready
        return args -> cache.preload();
    }
}
// See what auto-config decided:  java -jar app.jar --debug     (conditions evaluation report)
// Measure startup:               --spring.main.lazy-initialization=true  vs  Actuator /startup endpoint
```

**Why it's a trap:** putting remote calls in `@PostConstruct` makes the app fail to start (or never become ready) when a
dependency is down, and a Kubernetes liveness probe that starts before step 7 completes will kill the pod in a loop
(see [Full Stack Q19](fullstack-devops-k8s.md)). Use readiness for "ready to receive traffic", not liveness.

#### Q12. What design patterns show up naturally in how Spring itself works?

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
safe for mutable instance state (Q9), or that a CGLIB proxy behaves identically to the real
object it wraps (Q13). Reciting "Spring uses Singleton, Factory, Proxy..." without being able to
name a concrete failure mode for at least one of them is a shallow answer.

### Proxies, AOP & transactions

#### Q13. What's the practical difference between JDK dynamic proxies and CGLIB proxies in Spring AOP, and why does it matter?

**Answer:** Spring uses JDK dynamic proxies (interface-based) when the target bean implements at
least one interface, and CGLIB (subclass-based bytecode generation) when it doesn't, or when
explicitly configured to always use CGLIB. The practical trap: a JDK dynamic proxy can only
intercept calls made *through the interface type* — if you inject the concrete class and call a
method not on the interface, or self-invoke (Q15), it's bypassed. CGLIB subclasses the target
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

**Why it's a trap:** the failure mode is identical to Q15/Q14 (silent no-op, no error anywhere),
but the root cause here is a class modifier that has nothing to do with the transaction code
itself — a `final` added for unrelated "good practice" reasons quietly disables AOP.

#### Q14. Since `@Transactional` relies on the Proxy pattern, what does that tell you about calling it on a private method?

**Answer:** A private method can't be proxied the way a public method can — the dynamic proxy
overrides/wraps the method from *outside* the class, and a private method isn't visible outside
the class to override in the first place. So `@Transactional` on a private method has the same
practical failure mode as self-invocation (Q15): it's silently ignored, no transaction ever
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

#### Q15. Can you call a `@Transactional` method from another method in the same class?

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

#### Q16. How do `@Transactional` propagation and rollback rules interact, and what does `readOnly = true` really do?

**Answer:** The default propagation, `REQUIRED`, means "join the caller's transaction if one
exists, otherwise start one" — so the outer and inner methods share **one** physical transaction
and one commit/rollback decision. That has a sharp consequence: when the inner `@Transactional`
method (called through a proxy, so not a self-invocation, Q15) throws a runtime exception, the
proxy marks the shared transaction **rollback-only** *before* the exception even reaches the
caller. If the outer method catches that exception and carries on, nothing is undone right
away — but at commit time the transaction manager sees the rollback-only flag and throws
`UnexpectedRollbackException: Transaction silently rolled back because it has been marked as
rollback-only`, and *all* the outer work is lost. `REQUIRES_NEW` suspends the outer transaction
and starts an independent one (a second connection from the pool), so the inner work commits or
rolls back on its own — the right tool for audit/outbox-style records that must survive an outer
failure, at the cost of holding two connections at once (a pool-exhaustion risk, see S7).
`NESTED` uses savepoints and only works with JDBC transaction managers, not with JPA in
general. Rollback rules are a separate axis: only unchecked exceptions and `Error` trigger
rollback by default (see the cheat-sheet), so add `rollbackFor` for checked ones. Finally,
`readOnly = true` is a **hint**, not a guard: Spring/Hibernate use it to skip dirty checking
(flush mode `MANUAL`), some drivers set the connection read-only, and routing data sources can
send it to a replica — but whether a stray `UPDATE` is actually rejected depends on the driver
and database, so never rely on it as a security boundary.

**Example:**

```java
@Service
class OrderService {
    private final OrderRepository orders;
    private final AuditService audit;              // a different bean -> goes through the proxy

    @Transactional
    public void place(Order o) {
        orders.save(o);
        try {
            audit.record(o);                        // throws -> tx is marked rollback-only NOW
        } catch (RuntimeException e) {
            log.warn("audit failed, continuing", e); // swallowed...
        }
    }                                                // ...commit -> UnexpectedRollbackException,
}                                                    // the order is rolled back too

@Service
class AuditService {
    @Transactional                                   // REQUIRED: joins the caller's transaction
    public void record(Order o) { /* throws IllegalStateException */ }

    // Fix if the audit must be independent of the caller's outcome:
    // @Transactional(propagation = Propagation.REQUIRES_NEW)
}
```

**Why it's a trap:** "I caught the exception, so the transaction is fine" is the intuitive —
and wrong — belief. The failure also appears *far* from the cause (at the outer method's
closing brace), and `REQUIRES_NEW` looks like a free fix while quietly doubling connection use.

#### Q17. "My `@Transactional` doesn't work" — what are the usual causes, in the order you check them?

**Answer:** Spring implements `@Transactional` with a proxy around the bean, so nearly every failure is "the call never went
through the proxy" or "the proxy did not do what you assumed". Checklist: (1) **Self-invocation**: `this.save()` from another
method of the same class bypasses the proxy, so no transaction starts (see [Spring Q15](spring-architecture.md)); move the
method to another bean, or inject the bean into itself/use `TransactionTemplate`. (2) **Visibility and `final`**: with CGLIB
the method must be `public` (or at least not `private`; private is silently ignored, see
[Spring Q14](spring-architecture.md)) and not `final`/`static`. (3) **Not a Spring bean**: `new OrderService()` has no proxy;
the class needs to be component-scanned and injected. (4) **Rollback rules**: by default only unchecked exceptions
(`RuntimeException`, `Error`) roll back; a checked exception commits, so use `rollbackFor = Exception.class`; and if you
catch the exception inside the method, the proxy never sees it and commits (see [Spring Q16](spring-architecture.md)).
(5) **Propagation**: `REQUIRED` joins the caller's transaction, so an inner failure marks the *whole* transaction
rollback-only (`UnexpectedRollbackException` at commit), while `REQUIRES_NEW` suspends it and commits independently, with
its own connection. (6) **Wrong `@Transactional`**: the `jakarta.transaction` one has different defaults, and the right
annotation must be on the *implementation* or a CGLIB-proxied class, not only on an interface method with a JDK proxy.
(7) **Threads and async**: the transaction is bound to the current thread (`ThreadLocal`), so work in `@Async`, a
`CompletableFuture` or a parallel stream runs outside it. (8) **Multiple transaction managers / no manager** on the
datasource used, and `readOnly = true` writes that are silently ignored by some drivers. Debug quickly with
`logging.level.org.springframework.transaction.interceptor=TRACE` or `TransactionSynchronizationManager.isActualTransactionActive()`.

**Example:**

```java
@Service
class BookingService {
    @Transactional
    public void bookAndNotify(Booking b) {
        save(b);              // self-invocation: save()'s own @Transactional is ignored, but we are already in one
        notify(b);            // if notify() throws a checked IOException -> COMMITS (default rule)
    }
    @Transactional(rollbackFor = Exception.class)   // fix: checked exceptions roll back too
    public void bookSafely(Booking b) throws IOException { save(b); notify(b); }
}
// Cheap self-invocation fix:
@Service class Audit { @Transactional(propagation = REQUIRES_NEW) public void log(Event e) { ... } }
// BookingService injects Audit and calls audit.log(e): goes through the proxy, new transaction.
```

**Why it's a trap:** the code compiles, the tests with an in-memory happy path pass, and the failure (half-saved data, no
rollback) only shows up on an error path in production. Write a test that forces an exception and asserts nothing was
persisted (see [Testing Q16](testing.md) for how).

#### Q18. What is Open-in-View (OSIV), why is it on by default, and why do many teams turn it off?

**Answer:** With `spring.jpa.open-in-view=true` (the Spring Boot default — it logs a startup
warning about it), an `OpenEntityManagerInViewInterceptor` binds a JPA `EntityManager` to the
request thread for the *whole HTTP request*, from the controller through JSON serialization. The
benefit is convenience: lazy associations can still be loaded after the `@Transactional` service
method returned, so a controller or a Jackson serializer walking `order.getLines()` doesn't
throw `LazyInitializationException`. The costs are real. The persistence context — and,
once the first query runs, typically a **pooled database connection** — stays open until the
response is written, so a controller that does a slow HTTP call, or a client with a slow
connection, holds a connection it isn't using and drains the pool under load (S7). It also
hides N+1 queries (Q19): the lazy loads that fire during serialization happen outside any
service method and are easy to overlook in review, so 1 + N statements go out with no
transaction boundary around them. Turning it off (`spring.jpa.open-in-view=false`) forces the
right design: services fetch exactly what the response needs (`JOIN FETCH`, `@EntityGraph`, or DTO
projections) inside the transaction, and controllers return DTOs, never entities. The migration
cost is a wave of `LazyInitializationException`s that each point at a missing fetch — which is
the point.

**Example:**

```java
// OSIV on: compiles, works, and hides a slow, connection-holding N+1 during serialization.
@GetMapping("/orders/{id}")
Order get(@PathVariable long id) {
    return orders.findById(id).orElseThrow();   // returns an entity; lines load lazily while
}                                               // Jackson serializes it — outside any tx

// OSIV off: the service loads what the view needs, in one query, inside the transaction.
@Transactional(readOnly = true)
public OrderView get(long id) {
    return orders.findViewById(id);             // @Query("select new ...OrderView(...) ...")
}
// application.yml:  spring.jpa.open-in-view: false
```

**Why it's a trap:** "OSIV is on by default, so it must be fine" — the default exists for
convenience and demo-friendliness. Interviewers use it to check whether you understand that a
lazy-loading exception is a *design signal*, not an annoyance to be silenced by keeping the
session open longer.

### Data & caching

#### Q19. What causes the N+1 query problem in JPA, and how do you detect and fix it?

**Answer:** Covered in [Persistence Q29](persistence-sql-postgres.md) (causes and fixes) and [Persistence S2](persistence-sql-postgres.md) (spotting it in production).
Spring angle: detect it in tests with `spring.jpa.show-sql=true` plus Hibernate statistics, and assert the query count. Fix it with a query-specific `JOIN FETCH` or `@EntityGraph`, never with a blanket `FetchType.EAGER` on the mapping.

#### Q20. What's the trap with `@Cacheable` returning a mutable object?

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

#### Q21. Spring Data derived queries, `@Query` and projections — when do you use each?

**Answer:** **Derived queries** (`findByStatusAndCreatedAtAfter`) are fine for one or two simple conditions; past
that the method name becomes unreadable, so switch to **`@Query`** (JPQL or native) or **Specifications/Querydsl** for
dynamic filters. **Projections** return only the columns you need instead of full entities: an **interface
projection** (getters matching properties), a **DTO/record projection** (`select new com.acme.OrderSummary(o.id,
o.total) ...` or a record type as the return type), or a **dynamic projection** (`<T> List<T> findByStatus(Status s,
Class<T> type)`). Use projections for read-only lists and APIs: they avoid loading associations, skip dirty
checking, and keep entities out of the web layer. Use entities when you are going to modify and save them.

**Example:**

```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByCustomerIdAndStatus(long customerId, Status status);          // derived

    record OrderSummary(Long id, BigDecimal total, Instant createdAt) {}
    @Query("select new com.acme.order.OrderRepository$OrderSummary(o.id, o.total, o.createdAt) "
         + "from Order o where o.customerId = :customerId order by o.createdAt desc")
    Page<OrderSummary> summaries(long customerId, Pageable page);                    // DTO projection
}
```

**Why it's a trap:** an **open interface projection** using SpEL (`@Value("#{target.firstName + ' ' + target.lastName}")`)
loads the full entity anyway, so you lose the benefit while thinking you have it.

### Async & threading

#### Q22. Why do `@Async` methods lose the Spring Security context?

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

#### Q23. What are the default thread-pool behaviours of `@Async` and `@Scheduled`, and what do they get wrong for production?

**Answer:** Both annotations look like "just run this elsewhere" but come with sharp defaults.
`@Scheduled` methods run on a scheduler with a **single thread** by default
(`spring.task.scheduling.pool.size=1`): one slow job — or a `fixedRate` job that takes longer
than its rate — delays *every other* scheduled job in the application, so the nightly
report can start an hour late because a five-second job was running back to back. `@Async` needs
`@EnableAsync` (without it, the annotation is silently ignored and the method just runs
synchronously), and which executor it uses depends on your setup: Spring Boot auto-configures a
`ThreadPoolTaskExecutor` (core size 8 and an **effectively unbounded queue**, so a slow
consumer builds an unbounded backlog — the same failure as an unbounded `ExecutorService`, module
1 S17), whereas plain Spring without an executor bean falls back to `SimpleAsyncTaskExecutor`,
which starts a **new thread per task** with no cap. Failure handling is the third gap: an
exception thrown from a `void @Async` method never reaches the caller (it is only logged by the
default `AsyncUncaughtExceptionHandler`), and the caller's `SecurityContext` and transaction do
not propagate (Q22). Production setup: declare a named, **bounded** executor
(core/max/queue/`CallerRunsPolicy`) for `@Async`, size the scheduler pool to the number of
concurrent jobs, return a `CompletableFuture` when the caller needs to observe failure, and
register an `AsyncConfigurer` exception handler that raises an alert.

**Example:**

```java
@Scheduled(fixedRate = 1_000)
void slowJob() throws InterruptedException { Thread.sleep(5_000); }   // occupies the only thread

@Scheduled(cron = "0 0 2 * * *")
void nightlyReport() { /* starts late, or is skipped-then-bunched, while slowJob() runs */ }

// Fix: bounded executor for @Async, larger scheduler pool.
@Configuration @EnableAsync
class AsyncConfig {
    @Bean("mailExecutor")
    ThreadPoolTaskExecutor mailExecutor() {
        var ex = new ThreadPoolTaskExecutor();
        ex.setCorePoolSize(4); ex.setMaxPoolSize(8); ex.setQueueCapacity(200);
        ex.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        ex.setThreadNamePrefix("mail-");
        return ex;
    }
}

@Async("mailExecutor")
public CompletableFuture<Void> sendWelcome(User u) { /* failure is observable by the caller */ }
// application.yml:  spring.task.scheduling.pool.size: 4
```

**Why it's a trap:** it all *works* in a demo — jobs fire, mails are sent. The defaults only
hurt with a slow job, a burst of work or a failure, i.e. in production, and the symptoms
(late jobs, growing memory, vanishing exceptions) point away from the annotations that
caused them.

#### Q24. What is WebFlux's execution model, and what happens if you call blocking code inside it?

**Answer:** WebFlux runs on a small number of **event-loop threads** (Netty, about one per CPU core). A request is a
pipeline of `Mono`/`Flux` operators; nothing runs until something subscribes, and while waiting for I/O no thread is
held. That lets a few threads serve many concurrent connections, with **backpressure** so a slow consumer can limit a
fast producer. The rule that follows: **never block an event-loop thread**. A JDBC call, `RestTemplate`,
`Thread.sleep` or `.block()` on a Netty thread stalls every request sharing that loop. Use reactive drivers (R2DBC,
`WebClient`, reactive Mongo/Redis), or isolate unavoidable blocking calls with `subscribeOn(Schedulers.boundedElastic())`.
**BlockHound** detects blocking calls in tests. With virtual threads, many teams now keep Spring MVC instead; see
[Java Q34](java-core-jvm.md) for that trade-off.

**Example:**

```java
// ⛔ blocks the event loop
return Mono.just(jdbcTemplate.queryForObject(SQL, Long.class, id));
// ✅ isolate the blocking call
return Mono.fromCallable(() -> jdbcTemplate.queryForObject(SQL, Long.class, id))
           .subscribeOn(Schedulers.boundedElastic());
```

**Why it's a trap:** it works perfectly in a low-load test; under real traffic, latency jumps for every endpoint at
once because four event-loop threads are stuck in JDBC.

### Configuration & operations

#### Q25. What's the precedence order across the different ways to configure a Spring Boot application?

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

#### Q26. Which Actuator endpoints matter in production, and what should you be careful about exposing?

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

#### Q27. How should you use Spring profiles, and what are the common misuses?

**Answer:** Profiles switch **configuration** per environment or capability: `application-{profile}.yml` files,
`spring.config.activate.on-profile` documents, and `@Profile` on beans for genuinely different implementations
(for example a fake payment gateway in `local`). Activate them with `SPRING_PROFILES_ACTIVE`, and use **profile groups**
(`spring.profiles.group.prod=postgres,kafka,json-logs`) to compose capabilities. Misuses: `if (profile == "prod")` in
business code; dozens of profiles combined in subtle ways; **environment-specific values baked into the image** (URLs,
credentials) instead of injected through environment variables or a config server; and different bean graphs in test
and prod so the tested wiring isn't the deployed one. Good rule: profiles describe *capabilities*, environment
variables carry *values*, and the same artifact runs everywhere.

**Example:**

```yaml
spring:
  profiles:
    group:
      prod: [postgres, kafka, json-logs]
---
spring.config.activate.on-profile: json-logs
logging.structured.format.console: ecs
```

**Why it's a trap:** a `@Profile("!prod")` bean that disables security or seeds data is one wrong environment variable
away from production.

#### Q28. How do you instrument a Spring Boot service with Micrometer, and what's the cardinality trap?

**Answer:** Spring Boot Actuator auto-configures **Micrometer**: HTTP server and client timings, JVM, pool, cache and
Kafka metrics, exported to Prometheus, Datadog or OTLP. Add business metrics with `Counter`, `Timer` and
`DistributionSummary` (or `@Timed`/`@Counted`), and use the **Observation API** (`@Observed`, `ObservationRegistry`) to
produce a metric **and** a trace span from one instrumentation point; Micrometer Tracing propagates trace ids into
logs. Every distinct **tag combination is a separate time series**, so tags must have bounded values: status, method,
URI *template*, tenant tier. Never use user ids, order ids, raw URLs or exception messages as tags. Use histograms or
SLO buckets for latency percentiles that can be aggregated across instances.

**Example:**

```java
Counter.builder("orders.created")
       .tag("channel", order.channel().name())        // ✅ few values
       // .tag("customerId", id)                      // ⛔ one series per customer
       .register(registry).increment();

Timer.builder("payment.authorize").publishPercentileHistogram().register(registry)
     .record(() -> gateway.authorize(request));
```

**Why it's a trap:** a single high-cardinality tag can create millions of series, crash the metrics backend or
multiply its bill, and it usually shows up weeks after the deploy as traffic grows.

### Web API

#### Q29. How do you handle exceptions globally in a Spring Boot REST API?

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

#### Q30. How do you configure CORS correctly, and what's the trap with combining a wildcard origin and credentials?

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

*See also:* [Full Stack Q12](fullstack-devops-k8s.md) for the browser side: preflights, `SameSite` cookies, and why curl never sees CORS.

#### Q31. Why doesn't `@Valid` automatically validate nested objects, and what's the fix?

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

### Design & resilience

#### Q32. How do you actually structure a hexagonal Spring Boot application in packages?

**Answer:** A common layout: a `domain` package with plain Java (no Spring, no JPA annotations)
holding entities and business rules; an `application` package with use-case/service classes and
the **port** interfaces they depend on (`OrderRepository`, `PaymentGateway`); and an
`infrastructure`/`adapter` package with the concrete implementations — a `@RestController`
adapting HTTP to a use case call, a `@Repository`-annotated JPA implementation of
`OrderRepository`, a message listener adapting a queue message to a use case call. The
enforcement mechanism that actually keeps this honest over time (not just at day one) is an
architecture test.

**Example:**

```text
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

#### Q33. Design the payment-type selection for a system supporting Credit Card, PayPal, and Bitcoin, without the client code knowing which concrete class to instantiate.

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

#### Q34. When do you reach for the Strategy pattern with Spring beans versus a simple `if`/`switch`?

**Answer:** The pattern-level criterion (does the set of branches grow, and is each branch substantial?) is covered in [Design Patterns Q17](design-patterns.md).
Spring angle: inject `List<Strategy>` and pick one with a `supports()` predicate, or inject `Map<String, Strategy>` keyed by bean name (Q33). A new behaviour is then a new `@Component`, and the dispatcher never changes.

#### Q35. What's the circuit breaker pattern, and when does a service actually need one?

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

*See also:* [System Design Q29](system-design.md) (backpressure, load shedding) and [System Design S14](system-design.md) (retry storm after a slow dependency).

## 🔴 Expert / Open

### Architecture & extensibility

#### Q36. How would you migrate an existing monolith to hexagonal architecture incrementally, without a big-bang rewrite?

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

**Example:**

```java
// Step 1: characterization test pins current behaviour before touching anything.
@Test void invoiceTotalsUnchanged() { assertEquals(new BigDecimal("118.00"), billing.total(sampleCart())); }

// Step 2: extract a port; the existing JPA code becomes its first adapter.
interface InvoiceStore { Invoice load(long id); }                 // new port in billing.application
@Repository class JpaInvoiceStore implements InvoiceStore { /* old repository code, moved */ }

// Step 3: lock the converted module with ArchUnit; unconverted modules are not checked yet.
@ArchTest static final ArchRule billingIsClean = noClasses().that().resideInAPackage("..billing.domain..")
    .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta.persistence..");
```

#### Q37. Design a plugin-style extension system in Spring so new behavior can be added without modifying existing code.

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

**Example:**

```java
interface NotificationChannel {
    boolean supports(ChannelType type);
    void send(Notification n);
}
@Component class EmailChannel implements NotificationChannel { /* supports(EMAIL) ... */ }
@Component class SmsChannel   implements NotificationChannel { /* supports(SMS)   ... */ }

@Service
class Notifier {
    private final List<NotificationChannel> channels;          // Spring injects every implementation
    Notifier(List<NotificationChannel> channels) { this.channels = channels; }

    void notify(Notification n) {
        channels.stream().filter(c -> c.supports(n.type())).forEach(c -> c.send(n));
    }
}
// Adding PushChannel = one new @Component; Notifier is untouched.
```

*See also:* [Design Patterns Q21](design-patterns.md) for the framework-agnostic Strategy + Factory + registry design.

#### Q38. How do you decide between an AOP-based cross-cutting concern (like `@Transactional`, `@Cacheable`, or a custom annotation) and writing it explicitly in the method body?

AOP earns its cost when the concern is genuinely orthogonal to business logic and applies
uniformly across many methods with the same rule — transactions, caching, and audit logging are
the textbook cases because the "how" is identical everywhere it's used and the annotation makes
the intent visible at the call site. The cost is real, though: AOP introduces the proxy
limitations from Q15/Q14/Q13 (self-invocation, private methods, `final` classes), makes the actual
execution flow less obvious from reading the method body alone, and can surprise a maintainer
who doesn't know the annotation triggers a whole aspect. Prefer explicit code when the concern
varies meaningfully case-by-case, when debuggability during an incident matters more than
DRY-ness, or when the team has already been burned by an AOP proxy gotcha in this exact codebase
— explicit code that says exactly what it does is sometimes the more senior choice, not the
less sophisticated one.

**Example:**

```java
// Good AOP fit: identical rule everywhere, intent visible at the call site.
@Cacheable("rates") BigDecimal rate(String ccy) { return client.fetch(ccy); }

// Better explicit: the rule varies per case and must be debuggable during an incident.
BigDecimal price(Order o) {
    var cached = cache.get(o.id());
    if (cached != null && !o.isVip()) return cached;      // VIP orders always recomputed
    var p = pricing.compute(o);
    if (!o.isVip()) cache.put(o.id(), p);
    return p;
}
// Annotation form would hide the VIP exception in a SpEL `condition = "!#o.vip"` that few will find.
```

#### Q39. How do you use application events inside a Spring monolith, and what's the catch with `@TransactionalEventListener`?

`ApplicationEventPublisher` lets a service announce "OrderPlaced" without knowing who cares
(email, inventory, analytics), which decouples modules inside a monolith and is the natural
stepping-stone toward hexagonal ports (Q32, Q36) and, later, messaging. A plain `@EventListener`
runs *synchronously, on the publisher's thread, inside its transaction* — so a listener
failure rolls back the order, and a slow listener slows the request. That is rarely what you
want for side effects. `@TransactionalEventListener` (default phase `AFTER_COMMIT`) fixes the
first half: the listener runs only if the transaction actually committed, so no confirmation
email goes out for an order that rolled back. Its catch is the mirror image: by
`AFTER_COMMIT` the original transaction is over, so a listener that writes to the database is
**not** covered by any transaction — `@Transactional` on it is ignored unless it is
`REQUIRES_NEW` — and if the listener fails, or the JVM dies between commit and dispatch, the
event is **lost**, because it lived only in memory. If the side effect must not be lost (billing,
an integration event to another service), persist the intent in the same transaction and deliver
it separately: the **outbox pattern** ([Messaging Q27](messaging-rabbitmq-kafka.md)) — or, in a modular monolith, Spring
Modulith's event publication registry, which stores events until their listeners complete. My
guideline: `@EventListener` for in-transaction, must-succeed-together reactions; 
`@TransactionalEventListener(AFTER_COMMIT)` for best-effort side effects (cache eviction,
notifications); an outbox for anything with a durability requirement. Add `@Async` (with a
bounded executor, Q23) if the listener is slow, accepting that ordering and the security context
are no longer guaranteed.

**Example:**

```java
record OrderPlaced(long orderId) {}

@Service
class OrderService {
    private final ApplicationEventPublisher events;
    @Transactional
    void place(Order o) { orders.save(o); events.publishEvent(new OrderPlaced(o.getId())); }
}

@Component
class Mailer {
    @TransactionalEventListener            // phase = AFTER_COMMIT by default
    void on(OrderPlaced e) { /* runs only if the order committed; lost if the JVM dies right now */ }

    @TransactionalEventListener
    @Transactional(propagation = Propagation.REQUIRES_NEW)   // needed to write to the DB from here
    void audit(OrderPlaced e) { auditRepo.save(new AuditRow(e.orderId())); }
}
```

### Multi-tenancy & security

#### Q40. How would you design multi-tenancy in a Spring Boot / JPA application, and what are the traps?

There are three isolation models, and the choice is a business decision before it is a technical
one. **Database-per-tenant** gives the strongest isolation, per-tenant backup/restore and
noisy-neighbour control, but costs one connection pool per tenant and an operational burden that
grows linearly (hundreds of tenants = hundreds of pools and migrations to run). **Schema-per-tenant**
(PostgreSQL schemas) shares the server but still isolates data and lets you `SET search_path`
per connection; it is a good middle ground until the number of tenants reaches the thousands
and schema migrations become the bottleneck. **Shared schema with a `tenant_id` discriminator**
is the cheapest and scales to many small tenants, but isolation is only as strong as every
query's `WHERE tenant_id = ?` — one forgotten filter is a cross-tenant data leak — so back it
with database-level protection: PostgreSQL **row-level security** with the tenant set per
transaction, and Hibernate's `@TenantId` (6.x) or a filter so application code cannot forget it.
In Spring the plumbing is the same for the first two: resolve the tenant early (a servlet filter
reading a JWT claim or subdomain), store it in a request-scoped holder, and use an
`AbstractRoutingDataSource` or Hibernate's `CurrentTenantIdentifierResolver` +
`MultiTenantConnectionProvider` to pick the connection. The traps: (1) **context propagation** —
the tenant lives in a `ThreadLocal`, so `@Async`, scheduled jobs and message consumers lose it
just like the `SecurityContext` (Q22); a background job must set the tenant explicitly and clear
it in `finally`. (2) **Caches** — `@Cacheable` keys must include the tenant id or tenant A reads
tenant B's cached value (see Q20 for the related cached-object pitfall). (3) **Pool sizing** with
per-tenant pools. (4) **Migrations** must be run across all schemas/databases and be re-runnable
(Flyway per tenant, [Persistence Q37](persistence-sql-postgres.md)). (5) **Tests**: an automated test that requests the same
resource as two tenants and asserts isolation is the only reliable regression net. I would start
with the shared-schema + RLS design unless a customer contract demands physical isolation, and
keep the tenant resolver behind one interface so a large customer can later be moved to its own
database without touching business code.

**Example:**

```java
// Shared schema + Hibernate 6 discriminator: tenant_id is added to every query/insert automatically.
@Entity class Invoice {
    @Id Long id;
    @TenantId String tenantId;
}
@Component class TenantResolver implements CurrentTenantIdentifierResolver<String> {
    public String resolveCurrentTenantIdentifier() { return TenantContext.get(); }   // ThreadLocal holder
    public boolean validateExistingCurrentSessions() { return true; }
}
// Background job: set and ALWAYS clear the tenant.
TenantContext.set(tenantId);
try { job.run(); } finally { TenantContext.clear(); }
```

```sql
-- Defence in depth (PostgreSQL row-level security), tenant set per transaction:
ALTER TABLE invoice ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoice USING (tenant_id = current_setting('app.tenant'));
-- per transaction: SELECT set_config('app.tenant', 'acme', true);
```

#### Q41. Should authorization live in URL rules, in method security, or both?

Both, because they defend against different mistakes. URL rules in the
`SecurityFilterChain` (`authorizeHttpRequests`) are coarse, centralized and evaluated *before*
any controller runs: "everything under `/admin/**` needs `ROLE_ADMIN`", "`/actuator/**` is
internal only". Their weakness is that they are keyed on paths, so a new endpoint under an
unexpected path, a path-normalization quirk (trailing slash, encoded characters), or the same
service reached through a different entry point (a message listener, a scheduled job, another
controller) is unprotected. Rules are evaluated **in order, first match wins**, so a broad
`permitAll()` above a specific rule silently wins — and `anyRequest().authenticated()` (or
`denyAll()`) must be last, making "deny by default" the baseline. Method security
(`@EnableMethodSecurity`, `@PreAuthorize`) puts the rule next to the code it protects and can
express **business-level** decisions that URLs can't: "only the owner of the order, or a
support agent, may read it" (`@PreAuthorize("@orderAccess.canRead(#id, authentication)")`,
`@PostAuthorize` on the returned object). That last category — **object-level authorization** —
is the OWASP #1 issue (broken access control / IDOR), and it *cannot* be done with URL rules:
`GET /orders/123` and `GET /orders/124` are the same path. Method security is implemented with
AOP proxies, so the limitations from Q15/Q14/Q13 apply: a `@PreAuthorize` on a method called from
within the same class, or on a `private` method, is silently not enforced — the classic reason a
security test passes in isolation and the hole exists in production. My default: URL rules for
coarse, deny-by-default perimeter rules; `@PreAuthorize` on the *service* layer (where every
entry point converges) for role and ownership checks; and a test per protected use case that
proves the negative case (a wrong user gets a 403/404).

**Example:**

```java
@Bean
SecurityFilterChain chain(HttpSecurity http) throws Exception {
    return http.authorizeHttpRequests(a -> a
            .requestMatchers("/actuator/**").denyAll()               // specific rules first
            .requestMatchers("/admin/**").hasRole("ADMIN")
            .anyRequest().authenticated())                           // deny-by-default LAST
        .build();
}

@Service
class OrderService {
    @PreAuthorize("hasRole('SUPPORT') or @orderAccess.isOwner(#id, authentication)")
    Order read(long id) { return orders.findById(id).orElseThrow(); }  // GET /orders/123 vs /124: same URL
}
// @EnableMethodSecurity on a @Configuration class turns this on.
```

## 🎯 Real-world scenarios

### S1. A service works perfectly in local development but fails immediately after deployment

- **Symptoms:** All local and CI tests pass; the same jar fails to start, or starts but errors on
  first request, once deployed to a real environment.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Compare configuration first, not code — check active profile
  (`spring.profiles.active`), environment variables, and whichever `application-{profile}.yml`
  is actually being loaded in that environment (Q25's precedence order). Check for
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
  runtime locally and in production via Docker, see [Full Stack & DevOps](fullstack-devops-k8s.md)), and fail fast and loudly at
  startup (a health check or `@PostConstruct` sanity check) rather than on first user-facing
  request.

</details>

### S2. A REST API is slow, but only in production — the same endpoint is fast locally and in staging

- **Symptoms:** p99 latency in production is far worse than staging for an endpoint whose logic
  hasn't changed, and it's not consistently slow — it varies.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Production has data volume and concurrency staging doesn't — check whether the
  slow path involves a database query whose execution plan degrades with real data size (missing
  index that didn't matter on a small staging dataset), or whether it's contention (Q9, [Java S16](java-core-jvm.md)) only reproducible under production's actual concurrent load.
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

- **Resolution:** Add the missing index, fix the N+1 query (Q19), or address the specific
  contention point once identified from the trace — resist the urge to guess and optimize
  something the trace didn't actually implicate.
- **Prevention:** Load-test with production-scale data volume before shipping a new query path,
  and keep distributed tracing enabled by default in production so this diagnosis takes minutes,
  not a multi-day investigation.

</details>

### S3. Changes to `application.properties` don't seem to take effect after a config update

- **Symptoms:** A configuration value was changed and redeployed, but the running application
  still behaves according to the old value.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check the precedence order (Q25) — a higher-priority source (an environment
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
  APP_TIMEOUT=3000   # an OS env var beats the properties file every time (Q25)
  ```

- **Resolution:** Once the actual active source is identified, edit that one — or, if the design
  goal is "config should always come from this one file," remove the higher-priority override
  causing the conflict.
- **Prevention:** Log the active profile and a summary of key config values at startup, and
  standardize on one clear source of truth per environment (e.g. "container env vars always win,
  and that's the only place secrets/env-specific values are set") so this ambiguity doesn't
  recur.

</details>

### S4. A Spring Boot service crashes or becomes unresponsive under heavy traffic

- **Symptoms:** The service handles normal load fine but crashes, restarts, or stops responding
  entirely once traffic crosses some threshold.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Distinguish resource exhaustion (heap — [Java S1](java-core-jvm.md); thread pool —   [Java Q30](java-core-jvm.md), S7 below; connection pool — S7 below) from an actual bug that only triggers
  under concurrency (a race condition, Q9's singleton mutable-state trap). Metrics and a thread
  dump taken *during* the incident (not after restart, which loses the evidence) distinguish
  these quickly.
- **Example:**

  ```text
  "http-nio-8080-exec-142" #142 waiting for monitor entry
     java.lang.Thread.State: BLOCKED (on object monitor)
     at com.example.ReportService.generate(ReportService.java:22)
     - waiting to lock <0x000000076ab62208> (a com.example.ReportService)
  # 140+ request threads BLOCKED on the same singleton's monitor — Q9's mutable-field
  # trap turning into a full request-handling stall under real concurrency.
  ```

- **Resolution:** Depends entirely on which resource is exhausted — scale the relevant pool/
  heap/instance count, or fix the concurrency bug if that's what a thread dump actually shows.
- **Prevention:** Load-test to find the actual breaking point before production traffic finds it,
  and put circuit breakers (Q35) and rate limiting in front of the service so a traffic spike
  degrades gracefully instead of crashing outright.

</details>

### S5. The application context fails to start with a "no unique bean" or bean conflict error

- **Symptoms:** Startup fails with `NoUniqueBeanDefinitionException` or similar, usually right
  after adding a second implementation of an interface that used to have exactly one.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Spring can't decide which bean to inject when more than one candidate matches
  an injection point's type with no further qualification — this is a design signal, not just a
  wiring bug, since it means the code was written assuming there'd only ever be one
  implementation.
- **Example:**

  ```text
  Parameter 0 of constructor in com.example.OrderController required a single bean,
  but 2 were found:
      - creditCardPayment
      - payPalPayment
  ```

  ```java
  // Fix: be explicit about intent instead of leaving it ambiguous.
  @Primary
  @Component class CreditCardPayment implements Payment { }

  // or, if the consumer genuinely wants all of them (Q34's Strategy pattern):
  OrderController(List<Payment> payments) { ... }
  ```

- **Resolution:** If genuinely one should be the default, mark it `@Primary`. If the consumer
  needs a *specific* one, use `@Qualifier("beanName")`. If the consumer actually wants *all* of
  them, change the injection point from the interface type to `List<Interface>` instead of
  fighting the ambiguity.
- **Prevention:** When adding a second implementation of an existing interface, immediately
  check every injection point of that interface and decide deliberately (primary, qualified, or
  collected as a list) rather than letting the compiler/container error force a rushed fix.

</details>

### S6. An API endpoint intermittently returns `401 Unauthorized` for requests that should be authenticated

- **Symptoms:** The same client, same credentials, sometimes gets a successful response and
  sometimes gets `401`, with no obvious pattern from the client side.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Common causes in a Spring Security context: token expiry racing with request
  timing (a token that expires mid-session, especially short-lived JWTs without proper refresh
  handling); the security context not propagating across an async boundary (Q22's `@Async`
  scenario, if the endpoint does async work before the security check); or a load-balanced
  deployment where session-based auth isn't actually shared/sticky across instances, so a request
  landing on a different instance than the one that authenticated it appears unauthenticated.
- **Example:**

  ```java
  @Async
  public void enforceAndAudit(String userId) {
      // SecurityContextHolder is empty on this thread (Q22) — an authorization check
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

</details>

### S7. Requests start failing with database connection pool exhaustion errors under moderate load

- **Symptoms:** Errors like "connection is not available, request timed out" from the connection
  pool (HikariCP by default), correlating with periods of higher-than-usual request volume that
  aren't extreme.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

*See also:* [Persistence Q34](persistence-sql-postgres.md) (pool sizing) and [Persistence S4](persistence-sql-postgres.md) (the database's own connection limit).

</details>

### S8. Calls to a downstream microservice occasionally fail, and those failures cascade into unrelated parts of the system going down too

- **Symptoms:** One downstream dependency becomes slow or flaky, and shortly after, seemingly
  unrelated features in the calling service start failing or timing out too.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** This is the classic cascading-failure pattern — callers block waiting on the
  slow dependency, exhausting a shared thread pool ([Java Q30](java-core-jvm.md)) that other, healthy request
  paths also depend on, so one dependency's slowness takes down capacity for everything.
- **Example:**

  ```java
  // No timeout configured at all — a hung downstream can block this thread forever.
  public Inventory checkInventory(String sku) {
      return restTemplate.getForObject("/inventory/" + sku, Inventory.class);
  }

  // Fix: an explicit timeout plus a circuit breaker (Q35), so one flaky dependency
  // fails fast instead of exhausting the shared request-handling thread pool.
  RestTemplate client = restTemplateBuilder
      .setConnectTimeout(Duration.ofSeconds(2))
      .setReadTimeout(Duration.ofSeconds(2))
      .build();
  ```

- **Resolution:** Add a circuit breaker (Q35) around the specific call so failures there fail
  fast instead of piling up threads, add a sensible timeout (never call a downstream service with
  no timeout at all), add retry with backoff for transient failures specifically (not for every
  failure indiscriminately — retrying a genuinely down service just adds more load to it), and
  isolate the thread pool used for that call from the pool serving unrelated requests (bulkhead
  pattern) so its exhaustion can't starve everything else.
- **Prevention:** Treat "what happens when this downstream call is slow or down" as a required
  design question for every new external call, not an afterthought once it causes an incident.

</details>

### S9. Users report seeing old/stale behavior for a while after a new version is deployed

- **Symptoms:** A bug fix or feature change is deployed, but some users report the old behavior
  persisting for minutes to hours afterward.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S10. A secrets scanner (or a security review) flags database credentials committed in `application.properties`

- **Symptoms:** Database passwords, API keys, or other secrets are found in plaintext in a
  properties/YAML file checked into version control.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

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

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Resolution:** Audit every `@Transactional` boundary that can throw a checked exception and
  confirm rollback behavior matches intent explicitly, rather than relying on the unchecked-only
  default.
- **Prevention:** Default new transactional methods to `rollbackFor = Exception.class` unless
  there's a specific, documented reason a checked exception should still commit — the
  unchecked-only default is a footgun best overridden deliberately every time.

</details>

### S12. During an incident, expected log output is missing or incomplete in production

- **Symptoms:** A team investigating an incident finds that the specific log lines they need
  (or any logs at all, for a window of time) simply aren't present in the log aggregation system.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

- **Resolution:** Use `/actuator/loggers` (Q26) to bump the relevant logger to `DEBUG` live,
  without a redeploy, to capture detail on the *next* occurrence if this one is already missed;
  fix the log-shipping pipeline if that's the actual gap.
- **Prevention:** Default to `INFO` in production (not `WARN`) for anything that could matter
  during an incident, and monitor the log pipeline itself (shipping lag, drop rate) as its own
  health metric — "logs exist locally but never arrived" is otherwise invisible until you need
  them.

</details>

### S13. Application startup time has crept up significantly, slowing down deployments and autoscaling

- **Symptoms:** A service that used to start in a few seconds now takes 30+ seconds, which
  matters directly for rolling deployments and for autoscaling responsiveness under a traffic
  spike.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Spring Boot exposes a startup report (`spring.application.admin.enabled` /
  the auto-configuration report, or just timestamped startup logs) showing which
  auto-configuration classes and beans took the longest to initialize — usually the actual
  culprit is component scanning across an unnecessarily broad package, an eager (non-lazy) bean
  doing slow I/O at startup (warming a cache, pinging every downstream dependency), or simply
  accumulated dependencies that pulled in auto-configuration nobody uses.
- **Example:**

  ```text
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

</details>

### S14. A long-running background job occasionally gets killed mid-execution during a deployment

- **Symptoms:** A batch job or async task that takes minutes sometimes ends up in a
  half-completed state, correlating with deployment times.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S15. A bug spans multiple microservices, and it's unclear which service in the chain is actually responsible

- **Symptoms:** A user-facing error or latency issue clearly happens somewhere in a multi-service
  request chain, but each individual service's own logs look unremarkable in isolation.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Without a shared trace ID propagated across every hop, each service's logs are
  isolated islands with no way to correlate "this specific user request" across all of them —
  the diagnosis *is* the gap: distributed tracing isn't in place, or the trace context isn't
  being propagated across one specific hop (often a message queue boundary, where trace headers
  don't automatically carry over the way HTTP headers do with the right instrumentation).
- **Example:**

  ```text
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

</details>

### S16. A deployment causes a burst of failed requests for the few seconds around the old instance stopping

- **Symptoms:** Error rate spikes briefly, specifically during each rolling deployment, for
  requests that happened to be in flight when an old instance was terminated.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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
  before `SIGTERM` is a common Kubernetes-specific fix — see [Full Stack & DevOps S5](fullstack-devops-k8s.md)).
- **Prevention:** Treat zero-downtime deployment as a tested property, not an assumption — a
  simple load test that keeps sending traffic through a deployment and asserts zero failed
  requests catches a graceful-shutdown regression immediately, rather than it being discovered as
  a recurring blip nobody investigated.

</details>

### S17. `LazyInitializationException` appears in production right after a "harmless" cleanup

- **Symptoms:** After a release that set `spring.jpa.open-in-view=false` (to fix a pool-exhaustion
  warning, Q18), several endpoints start returning `500` with
  `org.hibernate.LazyInitializationException: failed to lazily initialize a collection of role
  Order.lines: could not initialize proxy - no Session`. Tests that call the service directly
  all pass.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The message is precise: something touched a lazy association after the session
  was closed. Read the stack trace bottom-up: the access happens in the controller layer or in Jackson's
  `BeanSerializer` — code that ran only because OSIV used to keep the session open for the whole
  request. Unit tests of the service pass because they never serialize the result. List every
  entity that leaves a service method and every lazy collection it exposes; each one is either a
  missing fetch or a design leak.
- **Example:**

  ```java
  @Transactional(readOnly = true)
  public Order find(long id) { return orders.findById(id).orElseThrow(); } // lines = lazy proxy

  @GetMapping("/orders/{id}")
  Order get(@PathVariable long id) {
      return service.find(id);        // Jackson walks order.getLines() -> no Session -> boom
  }
  ```

- **Resolution:** Do **not** re-enable OSIV or switch the association to `EAGER` (that just
  hardcodes an N+1, Q19). Load what the response needs *inside* the service, and return a DTO:

  ```java
  @Query("select new com.acme.OrderView(o.id, o.status, l.sku, l.qty) " +
         "from Order o join o.lines l where o.id = :id")
  List<OrderRow> findRows(long id);          // or @EntityGraph(attributePaths = "lines")
  ```

  Verify with a controller-level test (`@WebMvcTest`/`MockMvc` or `@SpringBootTest`) that asserts
  the JSON body and counts SQL statements (Hibernate statistics or a datasource-proxy) — the
  count should be constant, not proportional to `lines`.

- **Prevention:** Never return entities from controllers; add an integration test per endpoint
  (serialization included); keep OSIV off from the start of a project — retrofitting is far more
  painful than beginning without it.

</details>

### S18. Every scheduled job runs once per replica, so customers get duplicate emails and double charges

- **Symptoms:** After scaling from 1 to 3 pods, the nightly "send invoices" job emails each
  customer three times; a monthly billing job charges some accounts twice. Logs show the same
  job starting at the same second on every pod.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** `@Scheduled` is *local to a JVM*: each instance has its own scheduler and knows
  nothing about the others, so N replicas means N executions. Confirm by grepping logs for the
  job's start line across pods with identical timestamps. It went unnoticed before because there
  was exactly one instance (or because the job was accidentally idempotent).
- **Example:**

  ```java
  @Scheduled(cron = "0 0 2 * * *")
  void sendInvoices() { invoiceService.sendAllPending(); }   // runs on EVERY pod at 02:00
  ```

- **Resolution:** Make exactly one instance win each run. Options, in order of preference: a
  Kubernetes `CronJob` (the platform guarantees one run; the job is a separate process), a
  distributed lock with **ShedLock** (a row in an existing table or Redis key acquired per run),
  or a PostgreSQL advisory lock. With ShedLock:

  ```java
  @Scheduled(cron = "0 0 2 * * *")
  @SchedulerLock(name = "sendInvoices", lockAtMostFor = "30m", lockAtLeastFor = "1m")
  void sendInvoices() { invoiceService.sendAllPending(); }
  ```

  `lockAtMostFor` protects against a crashed holder keeping the lock forever;
  `lockAtLeastFor` stops a fast job being re-run by a replica whose clock is a bit behind.
  Also make the job itself **idempotent** (mark each invoice `SENT` in the same transaction, or
  use a unique key) since a lock timeout or a pod restart can still cause a rare double run
  ([Messaging Q13](messaging-rabbitmq-kafka.md)). Verify by running three replicas locally and asserting one execution per
  trigger.

- **Prevention:** Treat "how many instances run this?" as a required question for every
  `@Scheduled` method in code review; keep a scheduled-job inventory with lock name, max
  duration and idempotency notes.

</details>

### S19. Orders vanish although the code "handled" the exception and returned success

- **Symptoms:** Support reports customers who got a confirmation page but have no order. Logs
  show `WARN audit failed, continuing` followed a few milliseconds later by
  `UnexpectedRollbackException: Transaction silently rolled back because it has been marked as
  rollback-only`. Sometimes the user sees a `500` and sometimes a success — depending on whether
  something upstream swallowed the exception too.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Find the outer `@Transactional` method and look for a `try/catch` around a call
  into *another* `@Transactional` bean. The inner method threw, its proxy marked the shared
  (`REQUIRED`) transaction rollback-only, the outer method caught the exception and returned
  normally, and the commit refused to proceed (Q16). Turn on
  `logging.level.org.springframework.transaction=DEBUG` (or `TRACE`) to see "Participating in
  existing transaction" followed by "Setting JPA transaction on EntityManager rollback-only".
- **Example:**

  ```java
  @Transactional
  public void place(Order o) {
      orders.save(o);
      try { notifier.publish(o); }               // notifier.publish is @Transactional (REQUIRED)
      catch (RuntimeException e) { log.warn("audit failed, continuing", e); }
  }   // commit -> UnexpectedRollbackException, order gone
  ```

- **Resolution:** Decide what the *business* wants. If the side effect must not affect the
  order, run it independently: `@Transactional(propagation = REQUIRES_NEW)` on the inner method,
  or better move it *after* commit with a `@TransactionalEventListener` (Q39) — an outbox if it
  must not be lost. If it *is* part of the order, don't catch the exception. Add a test that
  makes the collaborator throw and asserts the order's final state matches the intended
  semantics.
- **Prevention:** Team rule: never catch a runtime exception thrown from a call that crosses a
  transactional bean boundary without knowing whether the transaction is now rollback-only;
  prefer explicit propagation attributes on side-effect services over relying on the default.

</details>

### S20. Threads pile up and the service stops answering because one dependency stopped answering

- **Symptoms:** A downstream inventory API starts hanging (accepting connections but never
  responding). Within a minute all Tomcat threads (200 by default) are busy, `/actuator/health`
  times out, the pod is restarted by the liveness probe, and the new pod dies the same way.
  CPU is idle; the dependency dashboard shows no errors — only *no responses*.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A thread dump (`jcmd <pid> Thread.print`) shows the request threads all parked
  in `SocketInputStream.socketRead0` / `SocketOrChannelRead` under `RestTemplate.exchange` or
  `WebClient` blocking calls. Check the client configuration: a `RestTemplate` built with
  `new RestTemplate()` uses `SimpleClientHttpRequestFactory` with **no** connect or read timeout,
  and Reactor Netty's `WebClient` has no default response timeout, so a hung peer holds the thread
  as long as it likes. One unbounded dependency has consumed the whole servlet thread pool,
  which is why unrelated endpoints failed too.
- **Example:**

  ```java
  RestTemplate rt = new RestTemplate();                 // no timeouts at all
  Stock s = rt.getForObject("http://inventory/stock/{sku}", Stock.class, sku); // may block forever
  ```

- **Resolution:** Set explicit timeouts on every outbound client, sized from the dependency's
  latency SLO, and wrap the call in a circuit breaker with a bulkhead so one dependency can't
  take all threads (Q35, S8):

  ```java
  var f = new SimpleClientHttpRequestFactory();
  f.setConnectTimeout(2_000);   // ms
  f.setReadTimeout(3_000);
  RestTemplate rt = new RestTemplate(f);

  // WebClient: HttpClient.create().responseTimeout(Duration.ofSeconds(3)) + .timeout(...) on the Mono
  ```

  Verify with a fault-injection test (a stub that sleeps 30 s): the caller must fail in ~3 s,
  the breaker must open, and unrelated endpoints must stay healthy. Also separate liveness from
  readiness so a slow dependency doesn't get the pod killed.

- **Prevention:** Central `RestTemplate`/`WebClient` builder beans with mandatory timeouts (ban
  `new RestTemplate()` via ArchUnit), a per-dependency bulkhead, and a dashboard of in-flight
  outbound calls and their p99.

</details>

### S21. A WebFlux service performs worse than the old MVC one, and latency spikes for everyone at once

- **Symptoms:** After migrating a service to Spring WebFlux "for scalability", throughput is
  lower than before; under moderate load *all* requests stall together for hundreds of milliseconds.
  Only a handful of threads exist, and they are all busy.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** WebFlux runs on a tiny fixed set of event-loop threads (about one per CPU
  core). A single blocking call — JDBC, a blocking HTTP client, `Thread.sleep`, `.block()`,
  heavy CPU work — stops that event loop from serving *every* other connection assigned to it. A
  thread dump shows the `reactor-http-nio-*` threads inside JDBC or socket-read code. Use
  BlockHound in a test or staging (`BlockHound.install()`), which throws at the exact blocking
  call.
- **Example:**

  ```java
  @GetMapping("/users/{id}")
  Mono<User> get(@PathVariable long id) {
      return Mono.just(jdbcTemplate.queryForObject(SQL, mapper, id)); // blocks the event loop
  }
  ```

- **Resolution:** Either go fully reactive (R2DBC, `WebClient`) or explicitly move the
  unavoidable blocking work off the event loop:

  ```java
  return Mono.fromCallable(() -> jdbcTemplate.queryForObject(SQL, mapper, id))
             .subscribeOn(Schedulers.boundedElastic());
  ```

  Then ask whether WebFlux was the right choice at all: with a blocking JDBC stack, Spring MVC
  on virtual threads gives you the concurrency without the reactive programming model ([Java Q34](java-core-jvm.md)). Verify with a load test comparing p99 before/after and BlockHound green in CI.

- **Prevention:** Only choose reactive when the *whole* path (driver included) is non-blocking;
  run BlockHound in the integration-test suite; document which thread each layer runs on.

</details>

### S22. "Welcome" emails silently stop being sent, and memory creeps up, while the API returns success

- **Symptoms:** The signup endpoint returns `201` as always, but a growing share of new users
  never receive the welcome email; nothing shows in dashboards or on-call. Heap usage on the pods
  climbs steadily over several days.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Sending is a `void @Async` method, so its outcome is invisible to the caller.
  Searching the logs for `Unexpected exception occurred invoking async method` finds thousands of
  `MailSendException`s — the mail provider had been rejecting requests for days, and the
  default `AsyncUncaughtExceptionHandler` only logs. The heap growth is the executor's
  effectively unbounded queue filling with retry-less tasks (Q23); a heap histogram shows
  `ThreadPoolExecutor$Worker` queues full of `Runnable`s referencing `User` objects.
- **Example:**

  ```java
  @Async
  public void sendWelcome(User user) { mailClient.send(user.email(), template); } // failure -> log line
  ```

- **Resolution:** Make failure visible and bounded. Use a named, bounded executor with a
  rejection policy; return `CompletableFuture<Void>` and attach `exceptionally` handlers, or (for
  a "must send" email) don't send inline at all — write a row to an outbox table in the signup
  transaction and let a worker deliver with retry/backoff and a dead-letter state ([Messaging Q23](messaging-rabbitmq-kafka.md), [Messaging Q25](messaging-rabbitmq-kafka.md)). Register an `AsyncConfigurer#getAsyncUncaughtExceptionHandler` that increments a
  metric and pages. Verify by pointing the mail client at a stub that fails: the failure counter
  must alert, the queue must stay bounded, and no signup request should be affected.
- **Prevention:** Metrics for every asynchronous boundary (queued, running, failed, rejected);
  an alert on the failure rate; an explicit choice, per side effect, between "best effort" and
  "must not lose".

</details>

## 🗣️ Reported interview questions

Questions reported from real interviews, grouped by topic. Each has a short model answer: expand it with the detailed questions and scenarios above, and say the answer aloud.

### Spring Boot in production

#### R1. Startup time increased from 15 seconds to 2 minutes. How do you investigate?

**Answer:** Find the cause before tuning: enable `--debug`/`ApplicationStartup` (Actuator `/startup` with `BufferingApplicationStartup`) to see time per bean; check slow `@PostConstruct`, eager DB/HTTP calls, Flyway migrations, large component scans, new auto-configurations, DNS or network timeouts. Compare with the previous build via `git bisect`. Fixes: lazy init, narrower scans, move work after startup, CDS/AOT/native if startup matters.

#### R2. A circular dependency error appears after deployment. How do you resolve it?

**Answer:** Boot 2.6+ forbids circular references by default. The real fix is **design**: extract the shared logic into a third bean, invert the dependency with an event or interface, or move the call out of the constructor. `@Lazy` on one injection point is a pragmatic patch, and `spring.main.allow-circular-references=true` hides the smell.

#### R3. One API works locally but fails in production with `LazyInitializationException`. What could be the reason?

**Answer:** A lazy association is touched after the Hibernate session closed. Locally `open-in-view` or a different data set/profile masks it; in production the session/transaction boundary is different (`spring.jpa.open-in-view=false`, DTO mapping in a controller, async thread, serialization outside `@Transactional`). Fix: fetch what the use case needs in the transaction (`JOIN FETCH`, `@EntityGraph`) or map to a DTO inside the service.

#### R4. A transaction partially updates data although you expected a rollback. Why might this happen?

**Answer:** Classic causes: a checked exception (rollback only on `RuntimeException`/`Error` by default); self-invocation or a `private`/`final` method so the proxy is bypassed; the exception is caught and swallowed; `REQUIRES_NEW`/another propagation commits independently; non-transactional resources (HTTP call, message sent); `@Transactional` from the wrong package (`javax` vs Spring) or on a non-Spring-managed bean.

#### R5. The application suddenly throws `OutOfMemoryError`. How do you debug it?

**Answer:** Read the message (heap space, Metaspace, direct memory, unable to create native thread).

Capture a heap dump (`-XX:+HeapDumpOnOutOfMemoryError`) and analyse it in Eclipse MAT/VisualVM: dominator tree, leak suspects (unbounded cache, `ThreadLocal`, static collections, big result sets). Correlate with GC logs and a recent deploy/traffic change.

Fix the leak or bound the structure; raising `-Xmx` only delays it. In containers check the cgroup limit vs `-Xmx`.

### Spring MVC

#### R6. Explain the flow of Spring MVC from request to response.

**Answer:** Servlet container → filters (security, CORS) → `DispatcherServlet` → `HandlerMapping` finds the controller method → `HandlerAdapter` binds arguments (`HttpMessageConverter`, validation, `@PathVariable`) and applies interceptors → controller/service runs → return value written by a converter (JSON) or resolved to a view → exceptions go through `@ControllerAdvice`/`HandlerExceptionResolver` → response back through filters.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. What is Dependency Injection in Spring, and what are its advantages?
2. Q4. What is Spring Boot, and how does it differ from plain Spring?
3. Q7. What is hexagonal (ports & adapters) architecture, and what problem does it solve?
4. Q8. Why is constructor injection generally preferred over field injection?
5. Q20. What's the trap with `@Cacheable` returning a mutable object?
6. Q35. What's the circuit breaker pattern, and when does a service actually need one?
7. Q36. How would you migrate an existing monolith to hexagonal architecture incrementally, without a big-bang rewrite?
8. Q41. Should authorization live in URL rules, in method security, or both?
9. S1. A service works perfectly in local development but fails immediately after deployment
10. S22. "Welcome" emails silently stop being sent, and memory creeps up, while the API returns success

## 📌 Cheat-sheet

### Core Spring concepts

> **Start here:** (1) DI = the container gives your class what it needs; (2) prefer constructor injection; (3) beans are singletons by default, so keep them stateless; (4) many Spring features are proxies; (5) config precedence: CLI > env > profile file > base file.

- **DI** (dependency injection) — the class declares what it needs and the container supplies it. *Gives loose coupling, testability, and no hand-rolled `new`.*
- **Constructor injection > field injection** — immutable, explicit, testable without a container. *Example: `public OrderService(PaymentPort p) { this.p = p; }`.*
- **Bean scopes** — `singleton` (default) = one shared instance; `prototype`/`request`/`session` have narrower lifetimes. *Mutable instance fields in a singleton = cross-request shared-state bug.*
- **Circular deps** *(advanced)* — A needs B and B needs A. Resolvable with setter/field injection (via an early-reference cache), *not* with pure constructor injection, which fails fast at startup instead.
- **Design patterns inside Spring** — DI/IoC (injection), Singleton (default scope), Factory (`ApplicationContext`), Strategy (injecting multiple implementations), Proxy (`@Transactional`, security, AOP), Template (`JdbcTemplate`).
- **JDK proxy vs CGLIB** — a proxy is a wrapper Spring puts around your bean to add behavior. JDK proxy needs an interface; CGLIB subclasses the class but can't proxy `final` classes/methods. *AOP is silently skipped either way if violated.*
- **Config precedence** (high → low) — CLI args → env vars → profile-specific file → base file → code defaults. *Example: `SERVER_PORT=9000` beats `server.port` in `application.yml`.*
- **`@ConfigurationProperties` over `@Value`** — for grouped settings: typed, relaxed binding (`my-prop`/`myProp`/`MY_PROP` all match), `@Validated` fail-fast at startup, IDE metadata.
- **`@Configuration` vs `@Component` with `@Bean`** *(advanced)* — full mode (CGLIB) makes calls between `@Bean` methods return the singleton; lite mode / `proxyBeanMethods = false` creates a fresh instance on each call. *Take dependencies as method parameters.*

### Transactions and persistence

> **Start here:** (1) `@Transactional` is a proxy, so self-calls and `private` methods are ignored; (2) it rolls back on unchecked exceptions only; (3) beware N+1 queries; (4) turn Open-in-View off; (5) `flush` is not `commit`.

- **`@Transactional` self-invocation and private methods** — silently a no-op, because it is proxy-based (a call from inside the same class bypasses the proxy). *Fix via self-injection, another bean, or AspectJ weaving.*
- **Rollback rules** — `@Transactional` rolls back on unchecked exceptions by default, NOT on checked ones. *Set `rollbackFor` explicitly, e.g. `@Transactional(rollbackFor = Exception.class)`.*
- **`flush()` ≠ `commit()`** — flush sends pending changes to the DB early; it doesn't end the transaction.
- **Propagation: `REQUIRED`** — shares one transaction. *An inner runtime exception marks it rollback-only even if the caller catches it (`UnexpectedRollbackException`).*
- **Propagation: `REQUIRES_NEW`** — an independent transaction. *Costs a second pooled connection.*
- **`readOnly = true`** — a hint, not a write guard.
- **N+1 queries** — lazy associations fetched in a loop give 1 + N queries. *Fix with a query-specific `JOIN FETCH`/entity graph, not a blanket `EAGER` fetch type.*
- **Open-in-View** — a convenience that holds a persistence context (and often a connection) for the whole request and hides N+1. *Turn it off: fetch in the service, return DTOs.*
- **`@TransactionalEventListener(AFTER_COMMIT)`** — runs only on commit, but outside the transaction and not durable. *Use an outbox (event row saved in the same transaction) for events that must not be lost.*
- **`@Cacheable` + mutable return value** — the cache stores the reference, not a copy. *A caller mutating a cached `List`/DTO corrupts every future cache hit.*
- **Multi-tenancy** *(advanced)* — DB-per-tenant (isolation) → schema-per-tenant → `tenant_id` + row-level security (density). *Propagate the tenant like the `SecurityContext`, include it in cache keys, migrate every tenant.*

### Web, security and validation

> **Start here:** (1) use `@ControllerAdvice` for errors and never leak stack traces; (2) `@Valid` needs repeating on nested objects; (3) CORS needs an explicit allow-list with credentials; (4) authorize at the URL and the method level; (5) never expose `env`/`beans`/`heapdump`.

- **`@ControllerAdvice`** — centralizes exception → HTTP-status mapping. *Never leak stack traces to clients.*
- **`@Valid` doesn't cascade** — a nested object field needs its own `@Valid`. *Otherwise its constraints are silently never checked.*
- **CORS** — wildcard origin + `allowCredentials(true)` is rejected. *It must be an explicit allow-list.*
- **Authorization (URL level)** — URL rules for the perimeter: first match wins, deny-by-default goes last.
- **Authorization (method level)** — `@PreAuthorize` on services for role/ownership checks (IDOR = accessing someone else's object by changing an ID). *Proxy limits apply (self-invocation, `private`).*
- **Actuator** — expose `health`/`info`/`metrics`/`loggers` externally if needed. *Never expose `env`/`beans`/`heapdump` publicly.*
- **Graceful shutdown** — `server.shutdown=graceful` + the orchestrator's grace period. *In-flight requests finish and the LB deregisters before the process exits.*

### Async, scheduling and resilience

> **Start here:** (1) always set timeouts on outbound calls; (2) use a circuit breaker for flaky dependencies; (3) `@Async` and `@Scheduled` have surprising defaults; (4) `@Scheduled` on N replicas runs N times; (5) never block in WebFlux.

- **Outbound timeouts** — `new RestTemplate()` / a default `WebClient` can block forever and drain the servlet thread pool. *Set connect/read timeouts, add a breaker + bulkhead.*
- **Circuit breaker** (Resilience4j) — fail fast on a flaky dependency instead of piling up threads waiting on it. *Prevents cascading failure.*
- **`@Async` drops the security context** by default. *Use `DelegatingSecurityContextAsyncTaskExecutor`.*
- **`@Scheduled`/`@Async` defaults** — one scheduler thread; Boot's `@Async` executor has an unbounded queue (plain Spring: a new thread per task).
- **`void @Async` failures** never reach the caller. *Use a named, bounded executor + a failure handler.*
- **`@Scheduled` on N replicas = N runs** — use a K8s `CronJob`, ShedLock or an advisory lock, and make the job idempotent.
- **WebFlux + blocking call** — stalls the event loop. *Use BlockHound (detects blocking calls), `boundedElastic`, or stay on MVC + virtual threads.*

### Architecture

> **Start here:** (1) keep `domain` free of framework code; (2) dependencies point inward; (3) enforce the rules with a test.

- **Hexagonal layout** — `domain` (no framework deps) → `application` (use cases + ports) → `infrastructure` (adapters). *Enforce with ArchUnit (tests that fail when a layer rule is broken).*
