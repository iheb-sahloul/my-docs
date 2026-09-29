# Spring Boot Best Practices



## 💉 Dependency injection & configuration

### Use constructor injection
Inject dependencies through the constructor, into `final` fields. Don't use `@Autowired` on fields.

**Why it's a best practice:** with field injection, the class can't be created without Spring: a unit test has
to use reflection or start a context to set the fields. Fields can't be `final`, so the object can exist
half-initialized. The constructor makes the dependencies explicit and mandatory, and a class with too many of
them is visible at a glance. Since Spring 4.3, a single constructor doesn't even need `@Autowired`.

```java
// ⛔
@Service
class OrderService {
    @Autowired private OrderRepository repository;
}

// ✅
@Service
class OrderService {
    private final OrderRepository repository;

    OrderService(OrderRepository repository) { this.repository = repository; }
}
```

### Group settings with `@ConfigurationProperties`
Bind related settings to a typed, validated class (a record works) instead of scattering `@Value` annotations.

**Why it's a best practice:** `@Value("${payment.timeout}")` is a string key repeated wherever it's needed: a
typo only fails at startup, or silently uses the default. `@ConfigurationProperties` binds a whole prefix into one
object, converts types (`Duration`, `DataSize`, lists), supports `@Validated` so a missing value fails fast, and
gives IDE auto-completion through the metadata processor.

```java
// ⛔
@Value("${payment.url}") String url;
@Value("${payment.timeout:5000}") int timeout;

// ✅
@Validated
@ConfigurationProperties("payment")
record PaymentProperties(@NotNull URI url, Duration timeout) {}
```

### Never commit secrets in `application.yml`
Keep passwords, API keys and tokens out of the repository. Read them from environment variables, a mounted
secret, or a vault.

**Why it's a best practice:** anything pushed to Git stays in its history forever, even after you delete it,
and is copied to every clone and CI runner. Leaked credentials are one of the most common causes of breaches.
Spring Boot resolves `${DB_PASSWORD}` from the environment out of the box, so the file only holds the reference.
Use profiles (`application-dev.yml`) for non-secret differences between environments.

⛔ `spring.datasource.password: s3cr3t`
✅ `spring.datasource.password: ${DB_PASSWORD}`

## 🔁 Transactions

### Put `@Transactional` on public service methods
Declare transactions in the service layer, on public methods called from another bean.

**Why it's a best practice:** Spring applies `@Transactional` through a proxy around the bean. A call from
another method of the *same* class (`this.save()`) doesn't go through the proxy, so no transaction is started,
and on a `private` method the annotation is ignored. Nothing warns you: the code just runs without a
transaction. The service layer is also the right boundary: one use case, one transaction. Controllers shouldn't
know about transactions, and repositories are too fine-grained.

```java
// ⛔ self-invocation: saveAll() runs without a transaction
public void importAll(List<Order> orders) { saveAll(orders); }
@Transactional
public void saveAll(List<Order> orders) { ... }

// ✅ the caller (another bean) calls the transactional method
@Transactional
public void importAll(List<Order> orders) { ... }
```

### Keep transactions short, and mark reads `readOnly`
Don't call remote services, send emails or wait on anything slow inside a transaction. Use
`@Transactional(readOnly = true)` for queries.

**Why it's a best practice:** a transaction holds a database connection, and often row locks, until it ends.
An HTTP call that takes 10 seconds inside it keeps the connection busy for 10 seconds, and with a pool of 10
connections, a few slow calls block the whole app. If the transaction rolls back after the email was sent, you
can't un-send it: publish an event and act after commit instead (`@TransactionalEventListener`). `readOnly = true`
lets Hibernate skip dirty checking and lets the driver route to a replica.

⛔ `@Transactional void placeOrder() { repository.save(order); paymentClient.charge(order); }`
✅ save in the transaction, charge after commit via `@TransactionalEventListener(phase = AFTER_COMMIT)`

### Know what rolls back
By default, only unchecked exceptions (`RuntimeException`, `Error`) roll back. Use `rollbackFor` if you throw
checked ones.

**Why it's a best practice:** a checked exception thrown from a `@Transactional` method *commits* the
transaction by default. Half the work is saved while the caller thinks the operation failed. Catching an
exception inside the method and not rethrowing also commits. Be explicit when the default doesn't fit.

⛔ `@Transactional void transfer() throws TransferException` — commits on `TransferException`
✅ `@Transactional(rollbackFor = TransferException.class)`

### Turn off Open Session in View
Set `spring.jpa.open-in-view: false`.

**Why it's a best practice:** it's on by default, and it keeps the Hibernate session (and a DB connection) open
until the HTTP response is written. Lazy loading then "works" in controllers and JSON serialization, which
hides N+1 queries and runs SQL outside of any transaction. Under load, connections stay busy while the response
is rendered. With it off, a `LazyInitializationException` tells you to fetch what you need in the service.

⛔ default `open-in-view: true` (Spring logs a warning at startup)
✅ `spring.jpa.open-in-view: false`

## 🌐 REST API

### Return DTOs, not entities
Map entities to request/response DTOs (records) at the controller boundary.

**Why it's a best practice:** serializing a JPA entity exposes every field, including ones you didn't mean to
publish (password hashes, internal flags), triggers lazy loading during serialization, and can loop forever on
bidirectional relations. Accepting an entity as input lets clients set fields they shouldn't (`id`, `role`):
that's mass assignment. A DTO makes the API contract explicit, so you can refactor the database without breaking
clients.

⛔ `@GetMapping("/{id}") User get(@PathVariable Long id)`
✅ `@GetMapping("/{id}") UserResponse get(@PathVariable Long id)`

### Validate input with `@Valid`
Put Bean Validation constraints on request DTOs and add `@Valid` on the controller parameter.

**Why it's a best practice:** the controller is a trust boundary: any client can send anything. With
constraints on the DTO (`@NotBlank`, `@Email`, `@Positive`), Spring rejects bad input with a 400 before your
code runs, and all rules are declared in one place. Without `@Valid` on the parameter, the annotations are
ignored silently.

```java
// ✅
record CreateUserRequest(@NotBlank String name, @Email String email) {}

@PostMapping
UserResponse create(@Valid @RequestBody CreateUserRequest request) { ... }
```

### Handle errors in one place with `ProblemDetail`
Map exceptions to HTTP responses in a `@RestControllerAdvice`, and return RFC 9457 `ProblemDetail` bodies.

**Why it's a best practice:** try/catch in each controller duplicates the mapping and drifts: one endpoint
returns 404, another 500 for the same error. A global handler keeps it consistent, and services can throw
domain exceptions without knowing about HTTP. `ProblemDetail` (Spring 6+) is a standard format clients can
parse. Never return stack traces or exception messages from the database to the client.

```java
// ✅
@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(UserNotFoundException.class)
    ProblemDetail handle(UserNotFoundException e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }
}
```

### Paginate collection endpoints
Never return an unbounded list. Accept a `Pageable` (or a cursor) and cap the page size.

**Why it's a best practice:** `findAll()` works in dev with 50 rows and takes the service down in production
with 5 million: all rows are loaded into memory and serialized in one response. Set a maximum with
`spring.data.web.pageable.max-page-size` so a client can't ask for `size=1000000`.

⛔ `List<OrderResponse> list()` → `repository.findAll()`
✅ `Page<OrderResponse> list(Pageable pageable)` → `repository.findAll(pageable)`

## 📈 Operations

### Expose health, readiness and liveness with Actuator
Add `spring-boot-starter-actuator`, expose only the endpoints you need, and use the liveness / readiness groups
for Kubernetes probes.

**Why it's a best practice:** the orchestrator needs to know whether to restart the app (liveness) or stop
sending it traffic (readiness). Readiness should fail while the app is still starting or can't reach a required
dependency; liveness should only check the app itself, otherwise a database outage restarts every pod in a loop.
Don't expose `env`, `heapdump` or `beans` publicly: they leak configuration and memory contents.

```yaml
# ✅
management:
  endpoints.web.exposure.include: health,info,prometheus
  endpoint.health.probes.enabled: true   # /actuator/health/liveness and /readiness
```

### Shut down gracefully
Set `server.shutdown: graceful` and a `spring.lifecycle.timeout-per-shutdown-phase`.

**Why it's a best practice:** on a deploy, the old pod receives `SIGTERM`. Without graceful shutdown, requests in
progress are cut and clients get errors on every release. With it, the server stops accepting new requests and
waits for in-flight ones to finish, up to the timeout. (Graceful is the default since Spring Boot 3.4.)

✅ `server.shutdown: graceful`, `spring.lifecycle.timeout-per-shutdown-phase: 20s`

## 🧪 Testing

### Use slice tests, not `@SpringBootTest` everywhere
Use `@WebMvcTest` for controllers, `@DataJpaTest` for repositories, and plain unit tests for services. Keep
`@SpringBootTest` for a few end-to-end tests.

**Why it's a best practice:** `@SpringBootTest` starts the whole application for each different context
configuration: it's slow, and a `@MockitoBean` in one test class creates a new context. Slow tests get run less
often. A slice only loads the beans for one layer and starts in a fraction of the time. Services with
constructor injection don't need Spring at all: `new OrderService(fakeRepository)`.

⛔ `@SpringBootTest` to test a JSON mapping in a controller
✅ `@WebMvcTest(OrderController.class)` + `MockMvc`

### Test against a real database with Testcontainers
Run repository and integration tests against the same database engine as production, not H2.

**Why it's a best practice:** H2 accepts SQL that Postgres rejects and the other way around: different types
(`jsonb`, `timestamptz`), functions, locking and constraint behaviour. Tests pass on H2 and the query fails in
production. Testcontainers starts a real Postgres in Docker, and with `@ServiceConnection` (Boot 3.1+) Spring
configures the datasource automatically.

```java
// ✅
@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
@Testcontainers
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");
}
```
