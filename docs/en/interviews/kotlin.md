# Kotlin for Java Developers

Kotlin on the backend (Spring Boot, coroutines) as asked of a senior who comes from Java. JVM internals (GC, memory model, threads) are in [Java Core & JVM](java-core-jvm.md#interface-abstract-class); Spring itself is in [Spring & Architecture](spring-architecture.md#dependency-injection-spring-advantages).

## 🟢 Fundamentals

#### Q1. How does Kotlin null safety work, and what is a platform type? {#kotlin-null-safety-platform-type}
**Answer:** Nullability is part of the type: `String` can never be null, `String?` can. The compiler forces you to handle `String?` with a safe call `?.`, the Elvis operator `?:`, a smart cast after `if (x != null)`, or `!!` (assert non-null, throws `NullPointerException`). Values coming from Java have **platform types** (`String!`): Kotlin does not know whether they can be null, so it lets you treat them either way and the check moves to runtime. Annotate the Java side (`@Nullable`/`@NonNull`, JSpecify) or declare the Kotlin type explicitly at the boundary.

**Example:**

```kotlin
fun greeting(name: String?): String =
    "Hello, ${name?.trim()?.ifEmpty { null } ?: "patient"}"

val header: String? = request.getHeader("X-Request-Id")   // Java API: declare String? explicitly
val id = header ?: UUID.randomUUID().toString()
```

#### Q2. When do you use a `data class`, a `sealed` class/interface and a `value class`? {#data-class-sealed-class-interface}
**Answer:** A **data class** is a value holder: the compiler generates `equals`/`hashCode`/`toString`/`copy`/`componentN` from the primary-constructor properties (the Kotlin equivalent of a Java `record`, but with `copy`). A **sealed** hierarchy is a closed set of subtypes known at compile time, so `when` over it is exhaustive without `else`, which is ideal for domain states and results. A **value class** (`@JvmInline value class`) wraps one value in a distinct type with no allocation in most cases: `PatientId` and `PractitionerId` can no longer be swapped by mistake.

**Example:**

```kotlin
@JvmInline value class PractitionerId(val value: Long)

sealed interface BookingResult {
    data class Booked(val appointmentId: Long) : BookingResult
    data object SlotTaken : BookingResult
    data class Rejected(val reason: String) : BookingResult
}

fun toHttp(r: BookingResult) = when (r) {            // exhaustive: adding a subtype breaks the build here
    is BookingResult.Booked -> 201
    BookingResult.SlotTaken -> 409
    is BookingResult.Rejected -> 422
}
```

#### Q3. What are extension functions, and what are their limits? {#extension-functions-limits}
**Answer:** An extension function `fun Type.name()` adds a method to an existing type without inheritance. It compiles to a static method that takes the receiver as its first parameter. So it is **resolved statically** (on the declared type, not the runtime type), it cannot access `private` members, and it cannot override a member function: a member with the same signature always wins. Use extensions for small, local helpers and mapping (`Entity.toDto()`), not to hide business logic in random files.

**Example:**

```kotlin
fun AppointmentEntity.toDto() = AppointmentDto(id = id, startsAt = startsAt, practitioner = practitionerName)

open class Shape; class Circle : Shape()
fun Shape.name() = "shape"
fun Circle.name() = "circle"
val s: Shape = Circle()
s.name()   // "shape": resolved on the declared type
```

#### Q4. How do you choose between `let`, `apply`, `also`, `run` and `with`? {#let-apply-also-run}
**Answer:** They differ on two things: how the object is referenced inside (`it` or `this`) and what they return (the lambda result or the object itself). `let` (it → result): transform a nullable value, `x?.let { … }`. `apply` (this → object): configure an object you are building. `also` (it → object): a side effect such as logging without breaking a chain. `run` (this → result) and `with(x)` (this → result): compute something from an object's members. Pick one by its return value, and avoid nesting them: three nested scope functions are unreadable.

**Example:**

```kotlin
val client = HttpClient.newBuilder().apply { connectTimeout(Duration.ofSeconds(2)) }.build()
val email = patient.email?.let { it.lowercase().trim() }
repository.save(appointment).also { log.info("booked {}", it.id) }
```

#### Q5. Collections vs sequences: when is `asSequence()` worth it? {#collections-sequences-assequence-worth}
**Answer:** Kotlin collection operators (`map`, `filter`) are **eager**: each step creates a full intermediate list. A `Sequence` is **lazy** and processes elements one by one through the whole chain, stopping early with `first`/`take`. Use sequences for long chains on large collections or when you short-circuit. For small lists, eager collections are simpler and often faster. It is the same idea as Java streams, but without parallelism.

**Example:**

```kotlin
val firstFree = slots.asSequence()
    .filter { it.start > now }
    .filterNot { it in booked }
    .firstOrNull()          // stops at the first match, no intermediate lists
```

## 🟡 Senior traps

#### Q6. What are coroutines and structured concurrency, and how do they compare to virtual threads? {#coroutines-structured-concurrency-compare-virtual}
**Answer:** A coroutine is a computation that can **suspend** (at a `suspend` call) without blocking its thread, and resume later, maybe on another thread. **Structured concurrency** means every coroutine runs in a `CoroutineScope`: a parent waits for its children, a failing child cancels its siblings and its parent (except under `supervisorScope`), and cancelling the scope cancels everything, so nothing leaks. `coroutineScope { async {…}; async {…} }` is the standard fan-out. Java 21 virtual threads also give cheap blocking-style concurrency, but with no built-in structured cancellation (`StructuredTaskScope` is still in preview). Coroutines additionally give `Flow`, cancellation and explicit dispatchers. In a Spring MVC app on Java 21, virtual threads are often enough. Coroutines shine with WebFlux or with many concurrent calls to fan out.

**Example:**

```kotlin
suspend fun practitionerPage(id: PractitionerId): Page = coroutineScope {
    val profile = async { profileClient.get(id) }
    val slots = async { availabilityClient.next(id, days = 7) }
    Page(profile.await(), slots.await())     // if one fails, the other is cancelled
}
```

**Why it's a trap:** `GlobalScope.launch` (or a hand-made `CoroutineScope(Job())` that nobody cancels) breaks structured concurrency: the work outlives the request, its errors are lost, and it leaks under load.

#### Q7. What do dispatchers do, and how do you call blocking code from a coroutine? {#dispatchers-call-blocking-code-coroutine}
**Answer:** A dispatcher decides which threads run a coroutine: `Dispatchers.Default` (CPU-bound work, about one thread per core), `Dispatchers.IO` (blocking I/O, a larger elastic pool, 64 threads by default), `Dispatchers.Main` (UI only). A `suspend` function is not automatically non-blocking: if it calls JDBC, `Thread.sleep` or a blocking HTTP client, it blocks its thread. Wrap blocking calls in `withContext(Dispatchers.IO) { … }`, and use `limitedParallelism(n)` to cap concurrency against a small resource such as a 10-connection pool.

**Example:**

```kotlin
private val db = Dispatchers.IO.limitedParallelism(10)   // matches the Hikari pool size

suspend fun findAppointments(id: PractitionerId): List<Appointment> =
    withContext(db) { jdbcTemplate.query(SQL, mapper, id.value) }
```

**Why it's a trap:** blocking inside `Dispatchers.Default` starves every other coroutine (only a few threads exist). Throughput falls apart under load while CPU looks idle. See [S1](kotlin.md#after-moving-endpoint-coroutines-throughput).

#### Q8. How does coroutine cancellation work, and what are the traps (`runBlocking`, `catch (e: Exception)`)? {#coroutine-cancellation-traps-runblocking-catch}
**Answer:** Cancellation is **cooperative**: a cancelled coroutine throws `CancellationException` at its next suspension point (`delay`, `yield`, a suspending call). A CPU loop with no suspension must check `isActive` or call `ensureActive()`. Three traps: (1) `catch (e: Exception)` also catches `CancellationException` and swallows the cancellation, so rethrow it or catch narrower exceptions; (2) cleanup in `finally` that needs to suspend must run in `withContext(NonCancellable)`; (3) `runBlocking` blocks the calling thread, so it is for `main` and tests, never inside a request thread or another coroutine (deadlock risk on a small pool). Use `withTimeout` to bound remote calls.

**Example:**

```kotlin
try {
    withTimeout(2.seconds) { smsGateway.send(reminder) }
} catch (e: CancellationException) {
    throw e                                  // never swallow cancellation (TimeoutCancellationException is one)
} catch (e: IOException) {
    log.warn("sms failed, will retry", e)
}
```

**Why it's a trap:** a generic `catch (e: Exception)` around a suspend call makes timeouts and request cancellation silently disappear. The coroutine keeps running after the client has gone.

#### Q9. What do you need to know to use Kotlin with Spring Boot and JPA? {#need-know-kotlin-spring-boot}
**Answer:** Spring proxies classes (`@Transactional`, `@Configuration`), but Kotlin classes are `final` by default. The **`kotlin-spring`** (all-open) compiler plugin opens classes annotated with Spring stereotypes. JPA needs a no-arg constructor and non-final entities: use **`kotlin-jpa`** (no-arg) plus all-open for `@Entity`. Add **`jackson-module-kotlin`** so Jackson understands constructors, default values and nullability. Prefer constructor injection (`class S(private val repo: Repo)`), `@ConfigurationProperties` on a data class, and Spring's coroutine support (`suspend` controller methods, `CoroutineCrudRepository` with R2DBC). Do **not** model JPA entities as data classes: generated `equals`/`hashCode` on all fields breaks with lazy loading, mutable ids and `Set`s, and `toString` can trigger lazy loads or recursion.

**Example:**

```kotlin
// build.gradle.kts
plugins { kotlin("plugin.spring"); kotlin("plugin.jpa") }

@Entity
class Appointment(
    @Id @GeneratedValue var id: Long? = null,
    var startsAt: Instant,
    @ManyToOne(fetch = FetchType.LAZY) var practitioner: Practitioner,
) {
    override fun equals(other: Any?) = other is Appointment && id != null && id == other.id
    override fun hashCode() = javaClass.hashCode()
}
```

**Why it's a trap:** without the all-open plugin, `@Transactional` on a final class or method is silently ignored (no proxy can be generated). The code compiles and runs, but with no transaction.

#### Q10. What breaks at the Java/Kotlin boundary? {#breaks-java-kotlin-boundary}
**Answer:** (1) **Platform types** from Java can be null at runtime even when you used them as non-null (see [Q1](kotlin.md#kotlin-null-safety-platform-type)). (2) Kotlin has no checked exceptions, so Java callers of a Kotlin function that throws `IOException` need `@Throws(IOException::class)` to be able to catch it. (3) Default arguments are invisible to Java without `@JvmOverloads`. (4) `companion object` members need `@JvmStatic` (methods) or `@JvmField`/`const` (fields) to look static from Java. (5) Top-level functions become `FileNameKt.fn()` unless you add `@file:JvmName`. (6) Kotlin `List` is read-only, not immutable: Java can still mutate it if the instance is an `ArrayList`. (7) `suspend` functions take an extra `Continuation` parameter and cannot be called from Java directly; expose a `CompletableFuture` with `future { }`.

**Example:**

```kotlin
class SlotService {
    @JvmOverloads
    fun next(practitionerId: Long, days: Int = 7, durationMin: Int = 20): List<Slot> = TODO()

    companion object {
        @JvmStatic fun create() = SlotService()
        const val MAX_DAYS = 28
    }
}
```

**Why it's a trap:** in a mixed codebase migrating from Java, most Kotlin NPEs come from unannotated Java APIs. Teams think "Kotlin has no NPE" and drop the checks at exactly the boundary that needs them.

## 🔴 Expert / Open

#### Q11. `Flow`, `suspend` functions or Reactor: how do you choose for an async backend? {#flow-suspend-functions-reactor-async}
**Answer:** A `suspend` function returns **one** value asynchronously. A `Flow` is a **cold** asynchronous stream of many values with backpressure by suspension. Operators are sequential and the code reads imperatively (`map`, `filter`, `buffer`, `flowOn`). `StateFlow`/`SharedFlow` are hot, for state and broadcasting. Reactor's `Mono`/`Flux` cover the same needs with a larger operator API, but stack traces and debugging are harder. With Spring WebFlux, Kotlin coroutines are a first-class alternative (`kotlinx-coroutines-reactor` bridges them: `awaitSingle()`, `asFlow()`). Decision: plain Spring MVC (with virtual threads) if the service is mostly CRUD on JDBC; coroutines when you need many concurrent remote calls or streaming; keep Reactor only where a library forces it. Do not mix reactive types and coroutines everywhere in the same service.

**Example:**

```kotlin
@GetMapping("/practitioners/{id}/slots", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun liveSlots(@PathVariable id: Long): Flow<Slot> =
    slotEvents.asFlow()                                   // Flux -> Flow
        .filter { it.practitionerId == id }
        .map { it.toSlot() }
```

**Why it's a trap:** choosing WebFlux and coroutines "for performance" on a service whose bottleneck is a blocking JDBC pool. You add complexity and get no gain until the database access is non-blocking (R2DBC) or isolated on `Dispatchers.IO`.

#### Q12. When do you use `inline`/`reified`, class delegation and property delegates? {#inline-reified-class-delegation-property}
**Answer:** **`inline`** copies a higher-order function's body and lambdas into the call site. That removes lambda allocation and allows **`reified`** type parameters (the type is known at runtime, so `T::class` works with no `Class<T>` argument), and non-local `return`. Keep it for small generic helpers, because it grows bytecode. **Class delegation** (`class A(b: B) : B by b`) implements an interface by forwarding to an instance: composition with no boilerplate, useful for decorators such as caching or metrics. **Property delegates**: `by lazy` (thread-safe lazy init by default), `Delegates.observable`, `by map`. The question is about restraint: these tools are useful when they remove repetition and harmful when they hide control flow.

**Example:**

```kotlin
inline fun <reified T> ObjectMapper.read(json: String): T = readValue(json, T::class.java)
val dto = mapper.read<AppointmentDto>(body)

class CachedAvailability(private val delegate: AvailabilityPort) : AvailabilityPort by delegate {
    private val cache = ConcurrentHashMap<Long, List<Slot>>()
    override fun next(id: Long) = cache.getOrPut(id) { delegate.next(id) }   // the rest is forwarded
}
```

**Why it's a trap:** marking big functions `inline` "for performance" makes bytecode grow at every call site for no measurable gain. The benefit only exists for lambdas and `reified`.

#### Q13. How do you test coroutine and Kotlin Spring code? {#test-coroutine-kotlin-spring-code}
**Answer:** Use `kotlinx-coroutines-test`: `runTest { }` runs a suspending test on a `TestScope` with **virtual time**, so `delay(10.minutes)` completes instantly and `advanceTimeBy`/`advanceUntilIdle` control the clock. Inject dispatchers (constructor parameter) instead of hard-coding `Dispatchers.IO`, so the test can pass a `StandardTestDispatcher`. For `Flow`, collect with `toList()` or use Turbine (`flow.test { awaitItem() }`). Use **MockK** instead of Mockito: it supports `final` classes, `coEvery`/`coVerify` for suspend functions and `object` mocking. For integration, use `@SpringBootTest` plus Testcontainers PostgreSQL (`@ServiceConnection`) exactly as in Java, and `WebTestClient` for coroutine controllers.

**Example:**

```kotlin
class ReminderServiceTest {
    private val sms = mockk<SmsGateway>(relaxed = true)

    @Test
    fun `sends reminder 24h before the appointment`() = runTest {
        val service = ReminderService(sms, dispatcher = StandardTestDispatcher(testScheduler))
        service.schedule(appointmentAt = currentTime.milliseconds + 25.hours)

        advanceTimeBy(1.hours + 1.seconds)        // virtual time: no real waiting
        coVerify(exactly = 1) { sms.send(any()) }
    }
}
```

**Why it's a trap:** testing with `runBlocking` and real `delay`s gives slow, flaky tests. Hard-coded dispatchers make the virtual clock useless because the work escapes to real threads.

## 🎯 Real-world scenarios

### S1. After moving an endpoint to coroutines, throughput collapses under load while CPU stays low {#after-moving-endpoint-coroutines-throughput}
- **Symptoms:** p99 latency jumps from 80 ms to several seconds at modest traffic, CPU around 20%, no errors, and thread dumps show the `DefaultDispatcher-worker` threads all in `RUNNABLE`/`WAITING` inside JDBC calls.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A `suspend` function calls the blocking JDBC repository directly, so it runs on `Dispatchers.Default`, which has only about one thread per core. A few slow queries occupy every worker and all other coroutines wait. Confirm with a thread dump (`jcmd <pid> Thread.print`) and the coroutine debug agent (`-Dkotlinx.coroutines.debug`).
- **Resolution:** Wrap blocking calls in `withContext(Dispatchers.IO.limitedParallelism(poolSize))`, or move to R2DBC for a truly non-blocking path. Keep CPU work on `Default`.
- **Prevention:** Code-review rule: a `suspend` function must not call blocking APIs without changing context. Add BlockHound in tests to fail on blocking calls in non-blocking threads, and run a load test before moving an endpoint to coroutines.

</details>

### S2. A Kotlin service throws `NullPointerException` on a value typed as non-null {#kotlin-service-throws-nullpointerexception-value}
- **Symptoms:** `NullPointerException: getHeader(...) must not be null` (or a crash inside a data class constructor) in production, on a code path where every Kotlin type is non-null.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A Java API (servlet header, legacy service, JSON deserialised by Jackson without the Kotlin module) returned `null` into a platform type that the code used as `String`. Kotlin inserts a null check at the boundary and fails there. The stack trace points at the first Kotlin line that uses the value.
- **Resolution:** Declare the boundary type as nullable (`val h: String? = ...`) and handle the missing case, register `jackson-module-kotlin` so missing JSON fields fail clearly or take their default value, and annotate the Java code with `@Nullable`.
- **Prevention:** Treat every Java call as a trust boundary, enable JSpecify/`-Xjsr305=strict` so annotated Java nullability is enforced, and add a test with the missing field or header.

</details>

### S3. `@Transactional` on a Kotlin service has no effect, and partial writes reach the database {#transactional-ignored-final-class}
- **Symptoms:** An exception halfway through `placeOrder()` leaves the order row saved without its lines; the same code in Java rolled back.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Kotlin classes and methods are `final` by default, so Spring's CGLIB proxy can't override them and the annotation is silently ignored. Check the build for the `kotlin-spring` (all-open) plugin; also check for self-invocation, which fails the same way in Java.
- **Example:**

  ```kotlin
  plugins {
      kotlin("plugin.spring") version "2.0.21"   // opens @Component/@Transactional/... classes
      kotlin("plugin.jpa") version "2.0.21"      // no-arg constructors for @Entity
  }
  ```

- **Resolution:** Add the `kotlin-spring` plugin (start.spring.io does by default), rebuild, and add an integration test that throws midway and asserts nothing was persisted.
- **Prevention:** Generate Kotlin projects from the Spring initializr, keep a rollback test per transactional use case, and an ArchUnit/Konsist rule that services are proxyable.

</details>

### S4. A JPA entity written as a `data class` causes duplicate rows in a `Set`, `StackOverflowError` in logs and lazy-loading storms {#data-class-entity-equals-breaks}
- **Symptoms:** Adding an entity to a `HashSet` before save then after save yields two elements; logging an order triggers dozens of SQL queries and sometimes a `StackOverflowError`.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** `data class` generates `equals`/`hashCode`/`toString` over all constructor properties: the hash changes when the ID is assigned, `toString` walks lazy associations (N queries) and bidirectional relations recurse forever.
- **Example:**

  ```kotlin
  @Entity
  class Order(
      @Id @GeneratedValue var id: Long? = null,
      @OneToMany(mappedBy = "order") val lines: MutableList<OrderLine> = mutableListOf(),
  ) {
      override fun equals(other: Any?) = other is Order && id != null && id == other.id
      override fun hashCode() = Order::class.hashCode()
      override fun toString() = "Order(id=$id)"
  }
  ```

- **Resolution:** Use a regular `class` for entities with ID-based `equals`, a constant `hashCode`, and a `toString` that doesn't touch associations. Keep `data class` for DTOs and value objects.
- **Prevention:** A static-analysis rule (detekt/Konsist) forbidding `data class` with `@Entity`, plus the `kotlin-jpa` plugin for no-arg constructors.

</details>

### S5. Under load, a Spring MVC service using coroutines stops answering, with all Tomcat threads stuck {#runblocking-in-request-thread}
- **Symptoms:** A thread dump shows all 200 `http-nio` threads parked in `BlockingCoroutine.joinBlocking`; health checks time out and pods get restarted.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Someone called a `suspend` function from a blocking controller with `runBlocking { ... }`. Each request pins a Tomcat thread while waiting, and if the coroutine needs a thread from the same exhausted pool (or `Dispatchers.IO` limit is hit) it deadlocks.
- **Example:**

  ```kotlin
  // before: blocks the request thread
  @GetMapping("/quote") fun quote() = runBlocking { pricing.fetch() }

  // after: Spring MVC and WebFlux both support suspend handlers
  @GetMapping("/quote") suspend fun quote() = pricing.fetch()
  ```

- **Resolution:** Make the handler `suspend` (supported by Spring MVC since 6 and by WebFlux) or stay fully blocking with a plain client; never bridge with `runBlocking` on a request path. On Java 21, virtual threads are a simpler alternative for blocking code.
- **Prevention:** A lint rule banning `runBlocking` outside `main` and tests, and a load test that checks thread-pool saturation metrics.

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q1. How does Kotlin null safety work, and what is a platform type?
2. Q2. When do you use a `data class`, a `sealed` class/interface and a `value class`?
3. Q4. How do you choose between `let`, `apply`, `also`, `run` and `with`?
4. Q6. What are coroutines and structured concurrency, and how do they compare to virtual threads?
5. Q7. What do dispatchers do, and how do you call blocking code from a coroutine?
6. Q8. How does coroutine cancellation work, and what are the traps?
7. Q9. What do you need to know to use Kotlin with Spring Boot and JPA?
8. Q10. What breaks at the Java/Kotlin boundary?
9. Q11. `Flow`, `suspend` functions or Reactor: how do you choose for an async backend?
10. S1. After moving an endpoint to coroutines, throughput collapses under load while CPU stays low

## 📌 Cheat-sheet

- **Null safety** — `?.`, `?:`, smart casts; `!!` is a code smell. *Java values are platform types: declare them `T?`.*
- **Types** — `data class` for values, `sealed` for closed states (exhaustive `when`), `value class` for typed ids. *Never a data class as a JPA entity.*
- **Scope functions** — choose by return value: `apply`/`also` return the object, `let`/`run`/`with` the result. *No nesting.*
- **Coroutines** — structured concurrency: `coroutineScope`, `async`/`await`, no `GlobalScope`. *`supervisorScope` when siblings must survive a failure.*
- **Dispatchers** — `Default` for CPU, `IO` for blocking, `limitedParallelism` to match a pool. *Blocking on `Default` starves everything.*
- **Cancellation** — cooperative; rethrow `CancellationException`; `withTimeout` on remote calls. *`runBlocking` only in `main` and tests.*
- **Spring** — `kotlin-spring` + `kotlin-jpa` plugins, `jackson-module-kotlin`, constructor injection. *Without all-open, `@Transactional` is silently ignored.*
- **Interop** — `@JvmOverloads`, `@JvmStatic`, `@Throws`, `@file:JvmName`. *`List` is read-only, not immutable.*
- **Testing** — `runTest` + virtual time, inject dispatchers, MockK `coEvery`, Turbine for `Flow`. *Testcontainers as in Java.*
