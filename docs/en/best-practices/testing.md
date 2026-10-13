# Testing Best Practices

## 🔺 Strategy

### Follow the test pyramid

Write many fast unit tests, fewer integration tests, and only a handful of end-to-end tests.

**Why it's a best practice:** a unit test runs in milliseconds, an integration test with a database in seconds,
and a browser test in tens of seconds. A suite of 2,000 end-to-end tests at 20 s each takes 11 hours serial, so
people stop running it and merge on hope. End-to-end tests also fail for reasons unrelated to your change
(network, timing, test data), which trains the team to ignore red builds. Push each check to the cheapest level
that can catch the bug.

```text
// ⛔ ice-cream cone: everything through the UI
E2E: 800   Integration: 60   Unit: 40   -> 45 min build, 1 in 10 runs red for no reason

// ✅ pyramid
Unit: 1500 (< 30 s)   Integration: 200 (~ 3 min)   E2E: 15 critical journeys
```

### Test behavior, not implementation

Assert on results and observable side effects, not on which private methods or internal calls happened.

**Why it's a best practice:** a test coupled to the implementation breaks on every refactor even though the
behavior is unchanged, so people stop refactoring or delete the tests. Verifying that `repository.save` was
called twice tells you nothing about whether the right data was stored.

```java
// ⛔ verifies how it works
verify(pricing, times(1)).applyVat(any());
verify(pricing, times(1)).applyDiscount(any());

// ✅ verifies what it produces
assertThat(service.total(cart)).isEqualByComparingTo("119.00");
```

### Write a failing test before fixing a bug

Reproduce the bug in a test first, watch it fail, then fix it.

**Why it's a best practice:** a fix without a test is a bug waiting to come back, and you can't prove your test
would have caught it unless you saw it fail. Regression tests are the most valuable tests you own: each one
comes from a real production failure.

```java
// ✅ red first: this failed with a NullPointerException before the fix
@Test
void total_isZero_whenCartHasNoItems() {
    assertThat(service.total(new Cart(List.of()))).isEqualByComparingTo("0");
}
```

## 🧱 Structure & naming

### Use Arrange-Act-Assert

Split each test into setup, one action, and assertions, separated by a blank line.

**Why it's a best practice:** when a test mixes setup and checks in a loop, nobody can tell what is being
tested or which line failed. One action per test means a failure points to one behavior. Tests with several
"act" steps hide which call broke.

```java
// ⛔
@Test
void test1() {
    var s = new CartService();
    s.add(item); assertEquals(1, s.size());
    s.add(item); assertEquals(2, s.size());
    s.clear();   assertEquals(0, s.size());
}

// ✅
@Test
void add_increasesSize() {
    // Arrange
    var cart = new Cart();
    // Act
    cart.add(item);
    // Assert
    assertThat(cart.size()).isEqualTo(1);
}
```

### Name tests after the behavior

Name a test `method_expectedResult_whenCondition` or use `@DisplayName` with a full sentence.

**Why it's a best practice:** when CI reports `test1 FAILED`, you have to open the file to learn what broke.
`withdraw_throws_whenBalanceIsInsufficient FAILED` is a bug report on its own. Names also serve as living
documentation of the rules of the domain.

```java
// ⛔
@Test void testWithdraw() { ... }

// ✅
@Test
@DisplayName("withdraw rejects amounts greater than the balance")
void withdraw_throws_whenBalanceIsInsufficient() { ... }
```

### Test one behavior per test

Each test should have one reason to fail. Several assertions are fine if they describe the same outcome.

**Why it's a best practice:** with ten unrelated assertions in one method, the first failure hides the other
nine, and the name can't describe them. Small tests fail independently and tell you exactly what is broken.

```java
// ⛔ create, update and delete in one test
@Test void userLifecycle() { ... }

// ✅ one test per behavior
@Test void create_assignsId() { ... }
@Test void update_changesEmail() { ... }
@Test void delete_removesUser() { ... }
```

### Use parameterized tests for input tables

Replace copy-pasted tests that differ only by data with `@ParameterizedTest`.

**Why it's a best practice:** five near-identical tests get out of sync, and boundary cases get skipped because
adding one means more boilerplate. A table makes missing cases visible, and every row is reported separately.

```java
// ⛔
@Test void blank() { assertFalse(validator.isValid("")); }
@Test void spaces() { assertFalse(validator.isValid("  ")); }

// ✅
@ParameterizedTest
@ValueSource(strings = {"", "  ", "a@", "@b.com", "a b@c.com"})
void isValid_returnsFalse_forMalformedEmails(String email) {
    assertThat(validator.isValid(email)).isFalse();
}
```

## 🎭 Test doubles

### Prefer fakes over mocks for collaborators with state

Use an in-memory fake for repositories and gateways. Keep mocks for verifying interactions that matter.

**Why it's a best practice:** stubbing `when(repo.findById(1)).thenReturn(...)` in 40 tests means 40 places to
change when the signature changes, and the test only proves the stub returns what you told it. A fake
(`Map`-backed) behaves like the real thing: save then find works, so tests read like real usage and survive
refactoring.

```java
// ⛔
when(repo.findById(1L)).thenReturn(Optional.of(user));
when(repo.save(any())).thenReturn(user);

// ✅
class InMemoryUserRepository implements UserRepository {
    private final Map<Long, User> store = new HashMap<>();
    public User save(User u) { store.put(u.id(), u); return u; }
    public Optional<User> findById(long id) { return Optional.ofNullable(store.get(id)); }
}
```

### Mock only what you own or what is slow

Mock the boundary (HTTP client, clock, message broker), not value objects or the class under test.

**Why it's a best practice:** mocking a `List` or a DTO gives you a test of Mockito, not your code. Mocking
too deeply (mocks returning mocks) means the test rebuilds the implementation line by line. Inject a
`Clock` so time-dependent code is deterministic instead of sleeping.

```java
// ⛔ real time, real sleep
Thread.sleep(1000);
assertTrue(token.isExpired());

// ✅ controlled time
var clock = Clock.fixed(Instant.parse("2026-01-01T10:00:00Z"), ZoneOffset.UTC);
var token = new Token(Instant.parse("2026-01-01T09:00:00Z"), Duration.ofMinutes(30));
assertThat(token.isExpired(clock)).isTrue();
```

### Use Mockito strictly and verify with intent

Use `@ExtendWith(MockitoExtension.class)` (strict stubs) and use `ArgumentCaptor` when you must check what was sent.

**Why it's a best practice:** strict stubs fail the test on unused stubbings, so dead setup gets removed
instead of accumulating. `verify(x).send(any())` passes even if the message content is wrong; a captor checks
the actual payload.

```java
// ⛔ passes even if the email body is empty
verify(mailer).send(any());

// ✅
var captor = ArgumentCaptor.forClass(Email.class);
verify(mailer).send(captor.capture());
assertThat(captor.getValue().to()).isEqualTo("ann@example.com");
```

## 🐳 Integration tests

### Use Testcontainers, not H2, for database tests

Run tests against the same database engine you use in production, in a throwaway container.

**Why it's a best practice:** H2 in "PostgreSQL mode" still differs: no `jsonb`, different locking, different
`ON CONFLICT` and window function behavior. Tests pass, production fails at the first native query. Containers
start in a few seconds, and with `@ServiceConnection` (Spring Boot 3.1+) there is no manual URL wiring.

```java
// ⛔ spring.datasource.url=jdbc:h2:mem:test;MODE=PostgreSQL

// ✅
@Testcontainers
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest {
    @Container @ServiceConnection
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");
}
```

### Share containers across tests

Declare the container `static`, or in a shared base or config class, so it starts once per JVM.

**Why it's a best practice:** starting a container per test class costs 3 to 10 s each; 50 classes add up to
minutes. Reusing the container and the Spring context keeps the suite fast. Isolate data with transactions
that roll back, or clean tables between tests, not with new containers.

```java
// ⛔ a new container for every class
class A { @Container PostgreSQLContainer<?> pg = ...; }

// ✅ one container for the whole suite
@TestConfiguration(proxyBeanMethods = false)
class ContainersConfig {
    @Bean @ServiceConnection
    PostgreSQLContainer<?> postgres() { return new PostgreSQLContainer<>("postgres:16"); }
}
```

### Use test slices instead of `@SpringBootTest` everywhere

Pick `@WebMvcTest`, `@DataJpaTest` or `@JsonTest` for the layer you test. Use `@SpringBootTest` only for a few full flows.

**Why it's a best practice:** `@SpringBootTest` loads the whole application: 5 to 15 s startup for a typical
service, and every different `@MockBean` set creates a new cached context. A slice loads only the beans of one
layer and starts in about a second, which is what makes running tests on every save realistic.

```java
// ⛔ full context to test one controller
@SpringBootTest @AutoConfigureMockMvc
class UserControllerTest { ... }

// ✅
@WebMvcTest(UserController.class)
class UserControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean UserService service;

    @Test
    void get_returns404_whenUserIsMissing() throws Exception {
        when(service.find(9L)).thenReturn(Optional.empty());
        mvc.perform(get("/users/9")).andExpect(status().isNotFound());
    }
}
```

### Test external HTTP calls with WireMock or MockWebServer

Stub the remote service at the HTTP level, including failures and slow responses.

**Why it's a best practice:** hitting a real sandbox makes tests slow, flaky and dependent on someone else's
uptime. Mocking your own `PaymentClient` skips serialization, headers and error mapping, where most integration
bugs live. An HTTP stub lets you test a 500, a timeout, or malformed JSON, which a sandbox can't produce on demand.

```java
// ✅
wm.stubFor(get("/rates/EUR").willReturn(aResponse().withStatus(503)));
assertThatThrownBy(() -> client.rate("EUR")).isInstanceOf(RateUnavailableException.class);
```

## 🎯 Assertions & reliability

### Use AssertJ fluent assertions

Prefer `assertThat(...)` over JUnit's `assertEquals` for collections, objects and exceptions.

**Why it's a best practice:** `assertEquals(expected, actual)` gets its arguments swapped constantly, giving
confusing failure messages. AssertJ reads left to right, autocompletes, and prints a useful diff of what
differed in a list or record.

```java
// ⛔
assertTrue(names.contains("ann") && names.size() == 2);

// ✅
assertThat(names).containsExactlyInAnyOrder("ann", "bob");
assertThatThrownBy(() -> service.withdraw(acc, 500))
    .isInstanceOf(InsufficientFundsException.class)
    .hasMessageContaining("balance");
```

### Never use `Thread.sleep` to wait for async work

Use Awaitility with a timeout, or make the code injectable and synchronous in tests.

**Why it's a best practice:** a fixed sleep is either too short (flaky on a loaded CI machine) or too long
(each test wastes seconds). Awaitility polls and returns as soon as the condition holds, and fails with a clear
message on timeout.

```java
// ⛔
publisher.send(event);
Thread.sleep(2000);
assertThat(repo.count()).isEqualTo(1);

// ✅
publisher.send(event);
await().atMost(Duration.ofSeconds(5)).untilAsserted(() ->
    assertThat(repo.count()).isEqualTo(1));
```

### Make tests independent and deterministic

No shared mutable state, no dependency on execution order, no random data without a seed, no real clock.

**Why it's a best practice:** a test that passes only after another one is a flaky test in waiting: run one
alone, or JUnit reorders them, and the build turns red. Flaky tests cost more than no tests: a suite that fails
1 run in 20 gets re-run instead of investigated, and real failures get lost. Quarantine or fix a flaky test the
day it appears.

```java
// ⛔ static state leaks between tests
static List<User> users = new ArrayList<>();

// ✅ fresh state per test
private List<User> users;
@BeforeEach void setUp() { users = new ArrayList<>(); }
```

### Build test data with builders

Use small factory methods or builders with sensible defaults and override only what the test cares about.

**Why it's a best practice:** a 12-argument constructor repeated in 80 tests breaks all 80 when a field is
added, and hides which value matters. A builder makes the relevant detail stand out.

```java
// ⛔
new User(1L, "ann", "ann@x.com", "pw", true, false, null, 0, "FR", null, null, 0);

// ✅
var user = aUser().withCountry("FR").build();
```

### Enforce coverage as a signal, not a goal

Track coverage and fail on drops in changed code, but review test quality as well (mutation testing with PIT).

**Why it's a best practice:** a test with no assertions gives 100% line coverage and zero safety. Chasing 100%
produces tests for getters. Mutation testing changes your code (`>` to `>=`) and checks that a test fails; a
survivor is a real gap that line coverage can't show. About 80% on business logic with strong assertions beats
95% with weak ones.

```java
// ⛔ executes the code, proves nothing
@Test void coverage() { service.process(order); }

// ✅
@Test
void process_marksOrderPaid() {
    service.process(order);
    assertThat(order.status()).isEqualTo(Status.PAID);
}
```

### Run tests in CI on every pull request

Run the full suite on every push and block merging on a red build.

**Why it's a best practice:** tests that only run on a developer laptop go stale, and a broken main branch
blocks the whole team. A 10-minute feedback loop catches the bug while the author still remembers the change;
a nightly run finds it three commits later. Keep the suite under about 10 minutes, and split slow tests into a
separate stage if needed.

```yaml
# ✅ .github/workflows/ci.yml
- run: ./mvnw -B verify
```
