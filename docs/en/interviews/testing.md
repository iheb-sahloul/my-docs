# Testing

Rules and code-review checklists live in [Best practices › Testing](../best-practices/testing.md); this module is the interview Q&A.

## 🟢 Fundamentals

### Strategy

#### Q1. What is the test pyramid, and is it still the right shape? {#test-pyramid-right-shape}
**Answer:** The pyramid says: many fast, isolated unit tests at the base, fewer integration tests in the middle,
and a handful of slow end-to-end tests at the top. The reasoning is cost and feedback speed: a unit test runs in
milliseconds and points at one class, while an end-to-end test takes seconds to minutes, needs a full environment,
and when it fails it tells you "something is broken somewhere". The shape is a guideline, not a law. For a typical
CRUD-heavy Spring service, most bugs live in the SQL, the mapping and the wiring, not in the business logic, so a
"testing trophy" with a thicker integration layer (real database through Testcontainers, real HTTP through MockMvc)
often catches more for the same effort. The constant across both shapes: keep end-to-end tests few and focused on
critical user journeys.

**Example:**

```text
            /\        E2E: login → checkout → payment (5–20 tests, minutes)
           /  \
          /----\      Integration: repository + real Postgres, controller + MockMvc (hundreds, seconds)
         /      \
        /--------\    Unit: pricing rules, validators, mappers (thousands, milliseconds)
```

#### Q2. Unit, integration, end-to-end — where do you draw the boundaries? {#unit-integration-end-end-draw}
**Answer:** Draw them by what is real and what is replaced, not by the tool. A **unit test** exercises one unit of
behaviour (often one class, sometimes a small cluster) with every I/O dependency replaced: no network, no database,
no file system, no clock. An **integration test** puts at least one real external piece in the loop: a real
database, a real broker, the real Spring context, or real HTTP serialization. An **end-to-end test** drives the
deployed system the way a user or client would, through its public interface, with everything real. The useful
question for each test: "if this fails, how many places could the bug be?" The answer should grow as you go up.

#### Q3. Mock, stub, fake, spy — what is the difference, and when do you use each? {#mock-stub-fake-spy-each}
**Answer:** A **stub** returns canned answers so the code under test can run (`when(repo.findById(1)).thenReturn(...)`);
you don't assert on it. A **mock** is set up with expectations and you **verify interactions** with it
(`verify(mailer).send(...)`); use it when the interaction *is* the behaviour, such as "an email is sent". A **fake** is
a working lightweight implementation (an in-memory repository, a fake clock); it gives realistic behaviour without
infrastructure. A **spy** wraps a real object and records calls, letting you override some methods. Rule of thumb:
prefer real objects, then fakes, then stubs; use mocks only for outgoing commands whose side effect you must check.

**Example:**

```java
// Stub: provides data
when(rates.rateFor("EUR")).thenReturn(new BigDecimal("1.08"));
// Mock: verifies an outgoing command
verify(notifier).orderConfirmed(orderId);
// Fake: a working in-memory implementation
class InMemoryOrderRepository implements OrderRepository {
    private final Map<OrderId, Order> store = new HashMap<>();
    public void save(Order o) { store.put(o.id(), o); }
    public Optional<Order> findById(OrderId id) { return Optional.ofNullable(store.get(id)); }
}
```

#### Q4. What makes a unit test good? {#unit-test-good}
**Answer:** It tests **one behaviour**, through the public API, and its name says which (`rejectsOrderWhenStockIsEmpty`,
not `testProcess2`). It follows **Arrange–Act–Assert** with a visible separation. It is **F.I.R.S.T.**: fast,
independent (no order dependency, no shared mutable state), repeatable (no clock, randomness or network), self-validating
(asserts, no reading logs), and timely (written with the code). And it fails for one reason: when it goes red, the
name plus the assertion message tell you what broke without opening a debugger.

**Example:**

```java
@Test
void appliesTenPercentDiscountAboveThreshold() {
    var order = anOrder().withTotal("120.00").build();      // Arrange

    var price = pricing.finalPrice(order);                   // Act

    assertThat(price).isEqualByComparingTo("108.00");        // Assert
}
```

### Java tooling

#### Q5. Which JUnit 5 features do you rely on beyond `@Test`? {#junit-5-features-rely-beyond}
**Answer:** `@ParameterizedTest` with `@CsvSource`/`@MethodSource` to cover a table of cases without copy-pasted tests;
`@Nested` classes to group cases by context ("when the cart is empty"); `@DisplayName` for readable reports;
`assertThrows`/`assertAll` for exceptions and grouped assertions; extensions (`@ExtendWith`) for Mockito, Spring
and Testcontainers; and `@Tag` to split fast and slow suites in the build. Most teams pair JUnit with **AssertJ** for
fluent, well-reported assertions (`assertThat(list).extracting(Order::status).containsOnly(PAID)`).

**Example:**

```java
@ParameterizedTest
@CsvSource({ "99.99, 0", "100.00, 10", "500.00, 50" })
void discountByTotal(BigDecimal total, BigDecimal expectedDiscount) {
    assertThat(pricing.discount(total)).isEqualByComparingTo(expectedDiscount);
}
```

#### Q6. How do you use Mockito well, and what should you never mock? {#mockito-well-never-mock}
**Answer:** Use `@ExtendWith(MockitoExtension.class)` with `@Mock`/`@InjectMocks`, stub only what the test needs
(strict stubs flag unused stubbing), and use `ArgumentCaptor` when you must inspect what was passed. Don't mock:
**value objects and DTOs** (just build them), **the class under test**, **types you don't own** (mocking
`RestTemplate` or `JdbcTemplate` encodes your assumptions about a library; wrap it behind your own port and mock
that, or test the adapter against the real thing), and **everything by default**. A test where the setup is twenty
`when(...)` lines and the assertion is `verify(...)` is usually testing the implementation, not the behaviour.

**Example:**

```java
@Test
void publishesEventWithOrderTotal() {
    service.confirm(orderId);

    var captor = ArgumentCaptor.forClass(OrderConfirmed.class);
    verify(events).publish(captor.capture());
    assertThat(captor.getValue().total()).isEqualByComparingTo("108.00");
}
```

### Frontend

#### Q7. What is the React Testing Library philosophy, and how do you query elements? {#react-testing-library-philosophy-query}
**Answer:** "The more your tests resemble the way your software is used, the more confidence they give you." Render
the component, interact as a user would (`userEvent.click`, `userEvent.type`), and assert on what the user sees, not
on state or internal methods. Query in priority order: `getByRole` (with an accessible name), `getByLabelText`,
`getByText`, and only then `getByTestId`. Querying by role doubles as an accessibility check: if you can't find the
button by role and name, neither can a screen reader. Use `findBy*` for elements that appear asynchronously instead
of manual waits. Deeper React angle: [React Q30](react-typescript.md#test-react-component-per-react).

**Example:**

```tsx
test('shows an error when the email is invalid', async () => {
  const user = userEvent.setup();
  render(<SignupForm />);

  await user.type(screen.getByLabelText(/email/i), 'not-an-email');
  await user.click(screen.getByRole('button', { name: /sign up/i }));

  expect(await screen.findByRole('alert')).toHaveTextContent(/valid email/i);
});
```

## 🟡 Senior traps

### Questions

#### Q8. Why not use H2 for repository tests? {#h2-repository-tests}
**Answer:** Because H2 is a different database. Its SQL dialect, type system, locking and constraint behaviour differ
from PostgreSQL's, even in "PostgreSQL mode". Queries using `jsonb`, `ON CONFLICT`, window functions, partial indexes,
`citext` or specific date arithmetic either fail on H2 or, worse, pass on H2 and fail in production. Flyway migrations
written for Postgres often don't run on H2 at all, so teams end up maintaining a second schema. Use
**Testcontainers** to run the real engine and version in a container; with a reused container and Spring's context
cache, the cost is a few seconds per suite.

**Example:**

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");
    // ...
}
```

**Why it's a trap:** H2 makes the suite green and fast, which looks like success. The bugs it hides are exactly the
database-specific ones that integration tests exist to catch.

#### Q9. Why is a Spring test suite slow, and how do you make it fast again? {#spring-test-suite-slow-make}
**Answer:** The usual cause is **context churn**. Spring caches application contexts between test classes, keyed by
their configuration. Every distinct combination of `@MockitoBean` (formerly `@MockBean`), `@TestPropertySource`,
active profiles or `@DirtiesContext` creates a new context, and each one can take several seconds to start. Fixes:
use **slices** (`@WebMvcTest`, `@DataJpaTest`, `@JsonTest`) instead of `@SpringBootTest` everywhere; move the common
mocked beans into a shared base class or test configuration so classes share one cache key; remove
`@DirtiesContext` unless a test really corrupts the context; and run the plain unit tests outside Spring entirely.

**Example:**

```text
Spring test log:  "Storing ApplicationContext ... in cache"  x 37
37 contexts × ~6 s startup ≈ 4 minutes spent only booting Spring
After consolidating mocks into one base class: 4 contexts
```

**Why it's a trap:** each `@MockitoBean` looks harmless locally. The cost only shows when you count distinct contexts
across the whole suite.

#### Q10. How do you test a Spring service that calls an external HTTP API? {#test-spring-service-calls-external}
**Answer:** Test at three levels, and never call the real third party from an automated test. (1) **Unit test with a mock of
the client interface**: the service depends on a small port (`PatientDirectory.find(id)`), so Mockito returns canned
results and failures; this covers your branching logic fast. (2) **Component test of the HTTP adapter** against a fake HTTP
server: **WireMock** (or MockWebServer, or `MockRestServiceServer` for `RestTemplate`/`RestClient`) lets you stub real
responses and assert on the *request* you sent (path, headers, auth, body) and on the behaviour for 404, 500, slow
responses, malformed JSON, and connection resets, which is where timeouts, retries and the circuit breaker are actually
verified. (3) **Contract test** (Spring Cloud Contract / Pact) so the stub cannot silently drift from the provider's real
API (see [Testing Q19](testing.md#consumer-driven-contract-testing-worth)); optionally a few smoke tests against the provider's sandbox in a separate non-blocking
pipeline. Test what matters for resilience: the timeout actually fires, a retry happens only for idempotent calls and
stops after N attempts, the fallback returns the degraded response, and the error is mapped to your own exception rather
than leaking the vendor's.

**Example:**

```java
@SpringBootTest
@WireMockTest(httpPort = 8089)                       // starts WireMock for the test
class PatientDirectoryClientTest {
    @Autowired PatientDirectoryClient client;

    @Test void returnsPatient() {
        stubFor(get("/patients/42").willReturn(okJson("{\"id\":42,\"name\":\"Ada\"}")));
        assertThat(client.find(42).name()).isEqualTo("Ada");
        verify(getRequestedFor(urlEqualTo("/patients/42")).withHeader("Authorization", matching("Bearer .+")));
    }

    @Test void timesOutInsteadOfHanging() {
        stubFor(get("/patients/42").willReturn(ok().withFixedDelay(5_000)));   // slower than our 1 s timeout
        assertThrows(DirectoryUnavailableException.class, () -> client.find(42));
    }

    @Test void retriesTwiceOn503ThenFails() {
        stubFor(get("/patients/42").willReturn(serviceUnavailable()));
        assertThrows(DirectoryUnavailableException.class, () -> client.find(42));
        verify(3, getRequestedFor(urlEqualTo("/patients/42")));               // 1 call + 2 retries
    }
}
```

**Why it's a trap:** a Mockito mock of `RestTemplate` proves nothing about URLs, serialisation or timeouts: it tests that
you called a method you configured yourself. And stubs only returning `200` leave every failure path untested, which is
exactly where the external dependency hurts you (see also [Spring Q35](spring-architecture.md#circuit-breaker-pattern-service-need) on circuit breakers).

#### Q11. What is over-mocking, and how do you recognise it? {#mocking-recognise}
**Answer:** Over-mocking is replacing so many collaborators that the test only checks "method A calls method B with
these arguments", which is a restatement of the implementation. Symptoms: refactoring without changing behaviour
breaks many tests; tests pass while the feature is broken because the mocks returned what the author assumed;
setup is longer than the test. Fix by testing at a slightly larger unit (a service plus its real domain objects, with
only I/O replaced), using fakes for repositories, and asserting on outcomes (returned value, saved state, published
event) rather than on call sequences.

**Why it's a trap:** high coverage and many green tests suggest safety, yet the suite can't catch an integration
mistake and actively resists refactoring, the opposite of what tests are for.

#### Q12. How do you test code that depends on the current time? {#test-code-depends-current-time}
**Answer:** Never call `LocalDateTime.now()` or `Instant.now()` directly in business code. Inject a
`java.time.Clock` (a Spring bean in production, `Clock.fixed(...)` or a mutable test clock in tests) and call
`LocalDate.now(clock)`. The same applies to randomness (inject a `Supplier<UUID>` or `RandomGenerator`) and to
time zones (pass a `ZoneId` explicitly). For asynchronous waits, use Awaitility with a timeout instead of
`Thread.sleep`.

**Example:**

```java
class SubscriptionService {
    private final Clock clock;
    boolean isExpired(Subscription s) { return s.endsAt().isBefore(Instant.now(clock)); }
}

var clock = Clock.fixed(Instant.parse("2026-01-31T23:59:59Z"), ZoneOffset.UTC);
assertThat(new SubscriptionService(clock).isExpired(sub)).isFalse();
```

**Why it's a trap:** tests that use the real clock pass for months, then fail on 29 February, at midnight UTC, or
on the CI runner in another time zone.

#### Q13. Is 80% code coverage a good target? {#80-code-coverage-good-target}
**Answer:** Coverage is a useful **floor signal** and a poor **target**. Line coverage only proves code was
executed, not that its result was checked: a test with no assertion still covers every line. Once coverage becomes
a goal, people write tests that execute code without verifying it (Goodhart's law). Use it to find untested
areas, especially in critical modules. To measure test *quality*, use **mutation testing** (PIT for Java,
Stryker for JS/TS): it changes the code (flips a `>` to `>=`, removes a call) and checks whether a test fails. A
surviving mutant is a behaviour no test checks.

**Example:**

```text
PIT report, PricingService:
  line coverage 96%   mutation score 61%
  SURVIVED: changed conditional boundary  total > 100  →  total >= 100
  => no test checks an order of exactly 100.00
```

**Why it's a trap:** a team proudly at 90% can still ship an off-by-one at a pricing boundary, because nothing
asserted on the boundary value.

#### Q14. What makes tests flaky, and how do you deal with flaky tests as a team? {#tests-flaky-deal-flaky-tests}
**Answer:** Common causes: **time** (real clock, time zones, `Thread.sleep` for async work); **order dependency**
(shared static state, a database not cleaned between tests, test A creating data test B relies on); **concurrency**
(asserting before an async consumer has run); **external dependencies** (real network, third-party sandboxes);
and **resource limits** on CI (ports, slow containers, timeouts tuned on a fast laptop). Team process matters as much
as fixes: detect flakiness (rerun failures and track tests that pass on retry), **quarantine** a flaky test into a
non-blocking job with an owner and a deadline, fix the root cause, and never let "just rerun the build" become
normal.

**Example:**

```java
// ⛔ sleeps and hopes
Thread.sleep(2000);
assertThat(repo.findById(id)).isPresent();

// ✅ waits for the condition, fails with a clear timeout
await().atMost(Duration.ofSeconds(10))
       .untilAsserted(() -> assertThat(repo.findById(id)).isPresent());
```

**Why it's a trap:** automatic retries make the pipeline green but teach the team to ignore red, and real
intermittent production bugs (races) hide among the "known flaky" tests.

#### Q15. What is the risk of putting `@Transactional` on integration tests? {#risk-putting-transactional-integration-tests}
**Answer:** Spring rolls back a `@Transactional` test at the end, which is convenient for cleanup but changes
behaviour. The test, the service and the repository share **one transaction**, so: lazy loading works in the test
even though it throws `LazyInitializationException` in production; constraints and triggers checked at commit
(deferred constraints) never fire; `@TransactionalEventListener(AFTER_COMMIT)` handlers never run; and a bug where the
service forgot `@Transactional` is masked because the test supplied one. For tests that exercise transaction
boundaries, don't annotate the test; clean up explicitly (truncate tables, or a fresh container schema per class).

**Why it's a trap:** the test passes precisely because it wraps the code in a transaction production doesn't have.

#### Q16. How do you test that a transaction really rolls back? {#test-transaction-rolls-back}
**Answer:** You must assert on the *committed* state of the database after a failure, so the test must **not** run inside the
usual rollback-after-test transaction (see [Testing Q15](testing.md#risk-putting-transactional-integration-tests)): that wrapper makes everything look rolled back and also
hides the bug where nothing was transactional. Recipe: (1) call the service method with input that forces a failure
*after* a first write (a stubbed collaborator throws, or a constraint is violated); (2) assert the expected exception;
(3) then query through a **fresh transaction/connection** (repository call outside the service, or `JdbcTemplate`) and
assert the first write is **absent**. Run it against a real PostgreSQL via Testcontainers, as H2 differs on locking and DDL
(see [Testing Q8](testing.md#h2-repository-tests)). Use `@Transactional(propagation = NOT_SUPPORTED)` or no `@Transactional` on the test, and
clean data in `@AfterEach`. Cover the rules from [Spring Q16](spring-architecture.md#transactional-propagation-rollback-rules-interact): a checked exception does not roll back
unless `rollbackFor` is set, `REQUIRES_NEW` work commits even if the outer transaction rolls back, and a swallowed exception
commits. For `@TransactionalEventListener(AFTER_COMMIT)` side effects, assert they are *not* triggered after a rollback.

**Example:**

```java
@SpringBootTest
@Testcontainers
class BookingRollbackTest {
    @Autowired BookingService service;
    @Autowired AppointmentRepository appointments;
    @Autowired AuditRepository audits;
    @MockitoBean NotificationClient notifications;          // MockBean on Spring Boot < 3.4

    @Test
    void bookingIsRolledBackWhenNotificationFails() {       // no @Transactional on the test
        doThrow(new IllegalStateException("smtp down")).when(notifications).confirm(any());

        assertThrows(IllegalStateException.class, () -> service.bookAndNotify(command()));

        assertThat(appointments.count()).isZero();           // first write was undone
        assertThat(audits.count()).isEqualTo(1);             // REQUIRES_NEW audit row survives, by design
    }
}
```

**Why it's a trap:** with `@Transactional` on the test the assertion passes even when the service has no transaction at all
(the test's own transaction rolls everything back and the persistence context returns unflushed entities). A rollback test
that cannot fail is worthless: temporarily remove `@Transactional` from the service and check the test goes red.

#### Q17. How do you mock HTTP calls in frontend tests? {#mock-http-calls-frontend-tests}
**Answer:** Mock at the **network boundary**, not the module boundary. Mock Service Worker (MSW) intercepts `fetch`
and XHR and returns responses from handlers you define, so your component, data-fetching library (React Query,
SWR) and serialization all run for real. Mocking `fetch` or your API module by hand skips that code and tends to
drift from the real contract. Define handlers per scenario (success, 500, slow response, empty list) and reuse the
same handlers in Storybook and in local development.

**Example:**

```ts
server.use(
  http.get('/api/orders', () => HttpResponse.json([], { status: 200 })),
);
render(<OrdersPage />);
expect(await screen.findByText(/no orders yet/i)).toBeInTheDocument();
```

**Why it's a trap:** `jest.mock('../api')` tests that the component calls a function, not that it handles the real
response shape, loading state and errors.

#### Q18. How do you load-test a REST API with Gatling, and how do you read the results? {#load-test-rest-api-gatling}
**Answer:** A load test answers "how does latency and error rate behave as concurrent load rises, and where does it break?",
so it needs a **realistic scenario, realistic data and an explicit goal**. Gatling (a code-first tool: Scala/Java/Kotlin DSL,
HTML reports) models a user journey (log in, search slots, book, cancel) with feeders for test data (unique patients, tokens),
checks on each response (status, JSON field, response time) and an **injection profile** that sets the load shape. Prefer an
**open model** (`constantUsersPerSec`, `rampUsersPerSec`: new users arrive at a fixed rate regardless of how slow the system
is, as in real life) over a **closed model** (`atOnceUsers`, `constantConcurrentUsers`: a fixed number of users wait for each
response), because the closed model slows its own arrivals when the server slows down and hides the tail (*coordinated
omission*, see [Full Stack Q8](fullstack-devops-k8s.md#p50-p95-p99-latency-average)). Typical test types: **smoke** (1 user, validate the script),
**load** (expected peak, steady), **stress** (ramp past the limit to find the breaking point and how it fails), **soak**
(hours at moderate load to reveal leaks and pool exhaustion), **spike** (sudden 10x). Define **assertions** as pass/fail
criteria (`p95 < 300 ms`, `failed < 1%`) so the build can fail automatically. Read the report by looking at: response-time
percentiles over time (not the mean), requests/s vs active users, the error breakdown, and then **correlate with server-side
metrics** (CPU, GC, connection pool, DB) to find the saturated resource. Run it against a production-like environment, never
the laptop that also hosts the app, and warm up the JVM first.

**Example:**

```java
public class BookingSimulation extends Simulation {
    HttpProtocolBuilder http = http.baseUrl("https://staging.api.example.com").acceptHeader("application/json");
    FeederBuilder<String> patients = csv("patients.csv").circular();

    ScenarioBuilder book = scenario("search and book")
        .feed(patients)
        .exec(http("search slots").get("/slots?doctor=#{doctorId}&day=2026-11-02")
            .check(status().is(200), jsonPath("$[0].id").saveAs("slotId")))
        .pause(1, 3)                                          // think time
        .exec(http("book").post("/appointments")
            .header("Idempotency-Key", "#{randomUuid()}")
            .body(StringBody("{\"slotId\":\"#{slotId}\",\"patientId\":\"#{patientId}\"}")).asJson()
            .check(status().in(201, 409)));                   // 409 = lost the race, an expected outcome

    { setUp(book.injectOpen(
            rampUsersPerSec(5).to(50).during(120),            // ramp
            constantUsersPerSec(50).during(600)))             // steady peak
        .protocols(http)
        .assertions(global().responseTime().percentile(95).lt(300),
                    global().failedRequests().percent().lt(1.0)); }
}
```

**Why it's a trap:** a green test against an empty database, with one hot cached record and a closed model, proves nothing
about production. Test data volume, cache state, and think times change the answer as much as the code does, and the
numbers from a shared CI runner are only good for *relative* comparison between builds. See
[Full Stack Q36](fullstack-devops-k8s.md#reducing-endpoint-p95-latency-9) for how to use the results to fix a bottleneck.

## 🔴 Expert / Open

### Questions

#### Q19. What is consumer-driven contract testing, and when is it worth it? {#consumer-driven-contract-testing-worth}
**Answer:** Each **consumer** writes tests that record what it actually needs from a provider's API (request, and the
fields of the response it reads). That produces a **contract** (Pact file) published to a broker. The **provider**
verifies every consumer's contract in its own pipeline against the real implementation. If the provider removes a
field a consumer reads, the provider's build fails before deployment. It replaces most cross-service end-to-end
tests for API compatibility. Worth it with several teams owning services that call each other over HTTP or
messaging and deploying independently. Not worth it for a single team deploying everything together, or for a public
API with unknown consumers (use OpenAPI schema diffing and versioning instead). Spring Cloud Contract is the
provider-driven alternative in the Spring ecosystem.

**Example:**

```text
order-ui (consumer)    -> pact: GET /orders/42 returns { id, status, total }
order-service (provider) CI: verify pact against real controller -> ✅
Developer removes `total` from the response -> provider CI fails: "order-ui expects total"
can-i-deploy order-service --to prod -> ❌ blocked
```

#### Q20. Design the testing strategy for a system of ten microservices. What runs where? {#design-testing-strategy-system-ten}
**Answer:** Per service, on every commit: unit tests and integration tests against real dependencies in containers
(database, broker), plus **contract tests** for each API it provides or consumes. That gives fast, owner-local
feedback and catches most bugs. On merge to main, deploy to a shared environment and run a **small smoke suite**
(health, one critical path per service). Keep a **thin end-to-end suite** (10–20 journeys: sign-up, checkout,
refund) running on the integrated environment, owned by the teams, not a separate QA silo. In production, use
**synthetic monitoring** on the same critical journeys, plus canary releases with automatic rollback on SLO
breach. What to avoid: a huge shared end-to-end suite that gates every deploy, takes an hour, and fails for reasons
nobody owns; it recreates the coupling microservices were meant to remove.

#### Q21. When does TDD help, and when do you not use it? {#tdd-help}
**Answer:** TDD (red → green → refactor) helps most where behaviour is well defined and logic-heavy: pricing,
validation, parsing, state machines, bug fixes (write the failing test that reproduces the bug first). It drives a
testable design with small units and explicit dependencies, and it gives a regression net for free. It helps less
during exploratory spikes, when you don't yet know what to build (spike, throw away, then test-drive the real
version), and for thin glue code where an integration test is the meaningful check. **Outside-in** TDD starts from an
acceptance test and mocks downward (London school); **inside-out** starts from the domain and builds up (Chicago
school). A senior answer is pragmatic: the goal is fast, trustworthy feedback, and TDD is one way to get it.

#### Q22. How do you test asynchronous messaging (Kafka/RabbitMQ consumers and producers)? {#test-asynchronous-messaging-kafka-rabbitmq}
**Answer:** Split it in layers. **Unit-test the handler** as a plain method: given this message, it produces this
state change or this outgoing event, with no broker. **Integration-test the wiring** with a real broker in
Testcontainers: publish a message and assert the effect with Awaitility, which checks serialization, topic
names, consumer group config and error handling. Test the **failure paths** explicitly: a poison message lands in the
DLQ after the configured retries; a **duplicate delivery** of the same message leaves state unchanged (idempotency,
see [Messaging Q13](messaging-rabbitmq-kafka.md#consumer-idempotent-even-messaging-system)); a crash after processing but before commit replays the message
safely. For schemas, add a compatibility check (Schema Registry) in CI.

**Example:**

```java
kafkaTemplate.send("orders", orderId, payload);
kafkaTemplate.send("orders", orderId, payload);           // duplicate delivery

await().atMost(Duration.ofSeconds(10)).untilAsserted(() ->
    assertThat(paymentRepo.countByOrderId(orderId)).isEqualTo(1));
```

#### Q23. How do you keep a Playwright/Cypress end-to-end suite fast and reliable? {#keep-playwright-cypress-end-end}
**Answer:** Cover only critical user journeys; push everything else down to component and API tests. Make each test
**independent**: create its own data through the API (not the UI) and don't depend on what another test left behind.
Use **resilient selectors** (role and accessible name, or `data-testid`), never CSS paths. Rely on the tool's
auto-waiting assertions instead of fixed timeouts. Stub third parties you don't control (payment sandbox, email) at
the network layer. Run tests in parallel with isolated accounts, record traces and videos on failure, and track
flakiness per test. Limit retries to one and treat a pass-on-retry as a flaky signal to fix.

**Example:**

```ts
test('checkout with a saved card', async ({ page, request }) => {
  const user = await createUserWithCart(request);          // setup via API, not UI
  await loginAs(page, user);
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
});
```

## 🎯 Real-world scenarios

### S1. The backend test suite takes 25 minutes, and developers have stopped running it locally {#backend-test-suite-takes-25}
- **Symptoms:** CI is the only place tests run; PRs wait half an hour for feedback; people push "fix test" commits in
  a loop.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Measure before guessing. Get per-class timings from the build report and count Spring context starts
  in the logs. The usual findings: dozens of distinct contexts caused by varying `@MockitoBean` sets and
  `@DirtiesContext`; `@SpringBootTest` used for logic that needs no Spring; a fresh database container per class;
  and tests running sequentially.
- **Example:**

  ```text
  grep -c "Started .* in" build/test-output.log   -> 41 context starts
  top 10 slowest classes: all @SpringBootTest, all with different @MockitoBean sets
  ```

- **Resolution:** Convert pure logic tests to plain JUnit; use slices for web and persistence; consolidate mocks into
  shared test configuration; reuse one Testcontainers instance per JVM (static container or `@ServiceConnection` in a
  shared config); enable parallel test execution in Gradle/Maven forks.
- **Prevention:** Track suite duration as a metric with a budget (for example 5 minutes for the PR gate), and review
  new `@SpringBootTest` and `@DirtiesContext` usages in code review.

</details>

### S2. A test passes locally and on rerun, but fails on CI about once in ten runs {#test-passes-locally-rerun-but}
- **Symptoms:** The failure is always the same assertion, never reproducible on a laptop, and "rerun" fixes it.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Look for what differs on CI: **test order** (run the class alone vs with the full suite; JUnit's random
  `MethodOrderer` exposes order coupling), **time zone and locale** of the runner, **speed** (slower CPU makes async
  assertions race), and **shared state** (static caches, a database not cleaned, a fixed port).
- **Example:**

  ```text
  CI runner TZ=UTC, laptop TZ=Europe/Paris
  test builds LocalDate.now() at 23:30 UTC -> date differs from the expected "today" in Paris
  ```

- **Resolution:** Fix the root cause: inject a fixed `Clock` and `ZoneId`, replace sleeps with Awaitility, isolate data
  per test (unique ids, truncation between tests), use random ports.
- **Prevention:** Run CI with a non-default time zone and random test order on purpose, quarantine new flaky tests
  with an owner, and report the pass-on-retry rate.

</details>

### S3. All tests are green, but a query fails in production with a syntax error {#all-tests-green-but-query}
- **Symptoms:** A new search endpoint returns 500 in production with a PostgreSQL error; the repository test for it
  passes.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check which database the tests use. The repository tests run on H2 in compatibility mode, which
  accepted a function or syntax that PostgreSQL rejects (or the reverse behaviour for case sensitivity, `ILIKE`,
  `jsonb` operators, or date functions).
- **Example:**

  ```text
  test profile: spring.datasource.url=jdbc:h2:mem:test;MODE=PostgreSQL
  prod error:   ERROR: function datediff(unknown, timestamp) does not exist
  ```

- **Resolution:** Fix the query, then switch repository tests to PostgreSQL in Testcontainers with the same major
  version as production, running the real Flyway migrations.
- **Prevention:** Ban the in-memory database for persistence tests (an ArchUnit rule or a dependency check that
  fails the build if H2 is on the test classpath).

</details>

### S4. A pure refactoring breaks 200 tests while the application still works {#pure-refactoring-breaks-200-tests}
- **Symptoms:** A developer extracts a class and renames two methods; behaviour is unchanged (manual and end-to-end
  checks pass), but hundreds of unit tests fail and the PR stalls.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The tests are coupled to the implementation: they mock every collaborator, verify internal call
  sequences, and test private helpers made package-visible "for testing".
- **Example:**

  ```java
  verify(validator).validate(order);
  verify(mapper).toEntity(order);
  verify(repo).save(any());
  verifyNoMoreInteractions(validator, mapper, repo);
  // asserts *how* it works, not *what* it does
  ```

- **Resolution:** Rewrite the worst offenders at a larger unit: real domain objects and mappers, a fake repository,
  and assertions on the returned value and saved state. Delete tests that only restate the implementation.
- **Prevention:** Agree on a team rule in code review: mock only I/O boundaries and outgoing side effects; test
  through public APIs; `verifyNoMoreInteractions` needs a justification.

</details>

### S5. The end-to-end suite fails 10% of the time, and the team now ignores its failures {#end-end-suite-fails-10}
- **Symptoms:** Nightly end-to-end runs are red most mornings; reruns usually pass; a real regression shipped last
  week because its failure was dismissed as "flaky again".

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classify the last 30 failures from traces: timing (fixed waits, animations), shared test data
  (two tests using the same account), environment instability (a dependency down), and selectors broken by UI
  changes. Usually two or three causes explain most failures.
- **Example:**

  ```text
  12 failures: shared user "e2e@test.com" modified by a parallel test
   8 failures: waitForTimeout(2000) too short on CI
   5 failures: payment sandbox timeout
   5 failures: real bugs
  ```

- **Resolution:** Give each test its own data created through the API, replace fixed waits with web-first assertions,
  stub the payment sandbox, and move non-critical journeys down to component tests.
- **Prevention:** Publish a per-test flakiness dashboard, quarantine with an owner and deadline, cap the suite size,
  and make a red end-to-end run block the release until someone triages it.

</details>

### S6. A test passes alone but fails when the whole suite runs, in a different order each time {#test-passes-alone-but-fails}
- **Symptoms:** Failures change from run to run and disappear when you re-run the one test.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Almost always shared state between tests: a static field or singleton, a database not cleaned, a shared clock or file, or tests that depend on execution order. Run with a fixed random order and bisect.
- **See also:** [Design Patterns S1](design-patterns.md#integration-tests-pass-isolation-but), the hand-rolled Singleton version of this bug.
- **Resolution:** Make each test own its data (create in setup, roll back or truncate after), reset static state, inject a `Clock`, remove ordering dependencies. Quarantine, do not delete, the test while fixing.
- **Prevention:** Run the suite in random order in CI; fail the build on tests that touch shared global state.

</details>

### S7. Every test is green, but the integration with the billing service breaks in production after their deploy {#mocks-green-provider-changed}
- **Symptoms:** `400 Bad Request: field 'currency' is required` from the billing service; our unit tests mock the client and still pass.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Our mocks encode our assumption of the provider's API, not the real one. The provider added a required field (or renamed one) and nothing on their side knew we depended on its absence.
- **Resolution:** Hotfix by sending the field; then add consumer-driven contract tests (Pact or Spring Cloud Contract): our tests generate the contract, the provider's pipeline verifies it before deploying, and `can-i-deploy` blocks incompatible releases.
- **Prevention:** Contract tests for every synchronous cross-team dependency, mocks generated from the provider's published OpenAPI rather than hand-written, and a smoke test in staging against the real service.

</details>

### S8. A visual bug ships even though snapshot tests cover the component, because the snapshot was just updated {#snapshot-tests-rubber-stamped}
- **Symptoms:** The checkout button disappears on mobile; the PR contained a 900-line `__snapshots__` diff that the reviewer approved with "snapshots updated".

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Large snapshots fail on every change, so the team runs `-u` by reflex. They assert 'nothing changed', not 'the behavior is correct', and nobody reads a 900-line DOM diff.
- **Resolution:** Replace big component snapshots with behavior assertions (Testing Library: `getByRole('button', { name: /pay/i })` is visible and enabled), keep small inline snapshots only for stable serialized output, and add visual regression screenshots (Playwright) for key pages reviewed as images.
- **Prevention:** Review rule: a snapshot update must be explained in the PR; lint rule capping snapshot size; CI that fails if snapshots are updated without the `snapshot-update` label.

</details>

## 🗣️ Commonly asked questions

Questions that come up often in interviews on this topic (a typical set, not tied to one specific interview). Each has a short model answer: expand it with the sections above and say it aloud.

#### R1. Unit vs integration vs end-to-end tests. {#unit-integration-end-end-tests}
**Answer:** Unit: one class in isolation, fast, no I/O. Integration: several real components together (repository + real database via Testcontainers, a Spring slice). End-to-end: the whole system through its public entry point, slowest and most brittle. Keep many unit tests, fewer integration tests, very few E2E (the test pyramid).

#### R2. `@Mock` vs `@MockBean` (`@MockitoBean`). {#mock-mockbean-mockitobean}
**Answer:** `@Mock` is plain Mockito: a mock for a unit test with no Spring context. `@MockBean` replaces a bean in the Spring context (deprecated in Spring Boot 3.4 in favour of `@MockitoBean`), which dirties the context cache and slows the suite. Prefer constructor injection with `@Mock`, and mock beans only in slice tests.

#### R3. How do you test a private method? {#test-private-method}
**Answer:** Do not test it directly: test it through the public behaviour that uses it. If the private logic is complex enough to need its own tests, it is probably a separate class with its own public API: extract it. Reflection to call private methods couples tests to the implementation.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. What is the test pyramid, and is it still the right shape?
2. Q3. Mock, stub, fake, spy — what is the difference, and when do you use each?
3. Q8. Why not use H2 for repository tests?
4. Q9. Why is a Spring test suite slow, and how do you make it fast again?
5. Q13. Is 80% code coverage a good target?
6. Q14. What makes tests flaky, and how do you deal with flaky tests as a team?
7. Q19. What is consumer-driven contract testing, and when is it worth it?
8. Q18. How do you load-test a REST API with Gatling, and how do you read the results?
9. S1. The backend test suite takes 25 minutes, and developers have stopped running it locally
10. S4. A pure refactoring breaks 200 tests while the application still works

## 📌 Cheat-sheet

### Strategy

> **Start here:** many fast tests, few slow ones; replace only I/O; assert on behaviour, not on calls.

- **Pyramid vs trophy** — pyramid = mostly unit; trophy = thicker integration layer. *For CRUD-heavy services, integration tests on a real database catch more.*
- **Boundaries** — unit = all I/O replaced; integration = at least one real external piece; E2E = everything real. *Ask "where could the bug be if this fails?".*
- **Test doubles** — stub supplies data, mock verifies an outgoing command, fake is a working light implementation, spy wraps a real object. *Prefer real > fake > stub > mock.*
- **Good unit test** — one behaviour, AAA, descriptive name, F.I.R.S.T. *Fails for one reason.*
- **TDD** — great for logic and bug fixes, weak for spikes and glue. *Outside-in (London) vs inside-out (Chicago).*

### Java & Spring

> **Start here:** real database in a container, slices over full contexts, a fixed clock.

- **Testcontainers over H2** — same engine and version as production, real migrations. *`@ServiceConnection` wires it in Spring Boot 3.1+.*
- **Context cache** — every distinct `@MockitoBean`/property/profile set boots a new context. *Consolidate; avoid `@DirtiesContext`.*
- **Slices** — `@WebMvcTest`, `@DataJpaTest`, `@JsonTest`. *`@SpringBootTest` for a few end-to-end wiring tests only.*
- **`@Transactional` tests** — rollback is handy but hides lazy loading, commit-time constraints and after-commit events.
- **Time** — inject `Clock`; Awaitility instead of `Thread.sleep`.
- **Mockito** — don't mock value objects, the class under test, or types you don't own.

### Quality signals

> **Start here:** coverage finds untested code; mutation testing tells you whether tests actually check anything.

- **Coverage** — a floor, not a goal. *Executed ≠ asserted.*
- **Mutation testing** — PIT (Java), Stryker (JS/TS). *Surviving mutant = unchecked behaviour.*
- **Flaky tests** — time, order, async, shared data, external services. *Quarantine with owner and deadline; track pass-on-retry.*

### Frontend & cross-service

> **Start here:** test like a user, mock at the network, keep E2E for critical journeys.

- **RTL** — query by role/label/text; `userEvent`; `findBy*` for async. *Role queries double as accessibility checks.*
- **MSW** — mock HTTP at the network layer; reuse handlers in Storybook and dev.
- **Playwright/Cypress** — few journeys, own data via API, resilient selectors, auto-waiting, max one retry.
- **Contract tests (Pact)** — consumer records needs, provider verifies in CI, `can-i-deploy` gates release. *Replaces most cross-service E2E.*
- **Load tests** — open model (arrival rate), realistic data volume and think time, steady-state window, assert on p95/p99 not the average. *409/429 can be expected outcomes; CI numbers are for relative comparison only.*
- **Messaging tests** — handler as plain unit; wiring with a containerised broker; test duplicates, DLQ and replay.
