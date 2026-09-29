# Java Best Practices



## 🛡️ Null safety & Optional

### Don't use `Optional` as a field or parameter
`Optional` is meant for return types only. It tells the caller "this method may have no result, handle it".

**Why it's a best practice:** `Optional` was designed as a return-type signal, not a general-purpose container.
As a parameter it doesn't help: the caller can still pass `null` instead of `Optional.empty()`, so you now have
three states to handle (value, empty, `null`), and every call site gets noisier with `Optional.of(...)`.
As a field, it's an extra object per instance, it isn't `Serializable` (so it breaks JPA entities, caches and
session replication), and most frameworks don't expect it. Keep the field nullable and wrap it only in the getter.

⛔ `void send(Optional<String> cc)`
✅ `void send(String cc)` + an overload, or `@Nullable String cc`

⛔ `private Optional<Address> address;`
✅ `public Optional<Address> getAddress() { return Optional.ofNullable(address); }`

### Don't call `Optional.get()` blindly
Use `orElseThrow`, `orElse`, `orElseGet`, `map` or `ifPresent` instead of `get()`.

**Why it's a best practice:** `get()` on an empty `Optional` throws `NoSuchElementException`, which is just a
`NullPointerException` with a different name: you've brought back the exact bug `Optional` was supposed to
prevent. `orElseThrow(() -> new UserNotFoundException(id))` makes the "absent" case explicit and turns it into a
domain error that carries context and can be mapped to a proper response (e.g. a 404).

⛔ `userRepository.findById(id).get()`
✅ `userRepository.findById(id).orElseThrow(() -> new UserNotFoundException(id))`

### Return empty collections, never `null`
A method that returns a collection should return an empty one when there's nothing to return.

**Why it's a best practice:** callers can then iterate, stream or call `size()` directly. Returning `null`
forces every caller to add a null check, and the one that forgets fails with an NPE, often far from the source
and only on the "no data" path, which is the least tested one. There's no performance excuse: `List.of()`,
`Set.of()` and `Map.of()` return shared immutable instances, so nothing gets allocated.

⛔ `return orders.isEmpty() ? null : orders;`
✅ `return List.of();`

### Fail fast on `null` at boundaries
Validate required arguments where they enter your object (constructors, public methods) instead of letting
`null` travel through the system.

**Why it's a best practice:** if a `null` is stored silently, the NPE shows up later, in another method or
thread, with a stack trace that points at the symptom and not the cause. `Objects.requireNonNull(x, "x")`
fails right away, at the line that received the bad value, with the parameter name in the message. It also
documents the contract: a reader can see the argument is mandatory.

```java
// ✅
public OrderService(OrderRepository repository) {
    this.repository = Objects.requireNonNull(repository, "repository");
}
```

## 🚨 Exceptions & logging

### Never swallow exceptions
Every `catch` block must either handle the error, or rethrow it (wrapped if needed) with the original cause.

**Why it's a best practice:** an empty `catch` turns a failure into silent data loss: the order wasn't saved,
but the caller thinks it was, and there's no log to find out why. When you wrap, pass the original exception as
the `cause` so the root stack trace is kept in the "Caused by:" chain. Wrapping also lets you translate a
low-level exception (`SQLException`) into one that makes sense at your layer and add useful context (the id).

```java
// ⛔
try { save(order); } catch (Exception e) { }

// ✅ handle it, or wrap and rethrow with the cause
try { save(order); } catch (SQLException e) {
    throw new OrderPersistenceException("Failed to save order " + order.id(), e);
}
```

### Catch specific exceptions, not `Exception`
Catch only the exceptions you expect and know how to handle. Don't use exceptions for control flow either.

**Why it's a best practice:** `catch (Exception e)` also catches the ones you didn't plan for:
`NullPointerException`, `IllegalStateException`, `ClassCastException`. Real bugs then get hidden behind the
fallback value, here a `0`. Catching the specific type documents which failure you're handling and lets every
other one propagate. Using exceptions for normal flow (e.g. to exit a loop) is slow, since creating an
exception captures the stack trace, and it hides intent: readers expect a `catch` to mean "something went wrong".

```java
// ⛔
try { return Integer.parseInt(input); } catch (Exception e) { return 0; }

// ✅
try { return Integer.parseInt(input); } catch (NumberFormatException e) { return 0; }
```

### Log with placeholders and pass the exception last
Use `{}` placeholders instead of string concatenation, and pass the exception itself as the last argument.

**Why it's a best practice:** with placeholders, the message is only built if the log level is enabled, so
`debug` calls in hot paths cost almost nothing in production. More importantly, SLF4J prints the stack trace
when the last argument is a `Throwable`. `e.getMessage()` only logs one line: you lose the stack trace, the
exception type and the whole "Caused by:" chain, which is usually where the real cause is. The message can even
be `null`.

⛔ `log.error("Failed to process order " + orderId + ": " + e.getMessage());`
✅ `log.error("Failed to process order {}", orderId, e);`

## 🔌 Resource management

### Close resources with try-with-resources
Anything that implements `AutoCloseable` (streams, JDBC connections, statements, result sets, HTTP clients)
should be opened in a `try (...)` block.

**Why it's a best practice:** a manual `close()` is skipped as soon as an exception is thrown before it. Each
leak holds a file handle or a pooled DB connection, until the pool is exhausted and the app hangs. A `finally`
block fixes that but is verbose and easy to get wrong (null checks, a `close()` that throws itself and hides the
original error). Try-with-resources closes on every path, in reverse order of opening, and keeps the exceptions
thrown by `close()` as *suppressed* exceptions attached to the original one, so nothing is lost.

```java
// ⛔ leaks the stream if read() throws
InputStream in = Files.newInputStream(path);
in.read();
in.close();

// ✅
try (InputStream in = Files.newInputStream(path)) {
    in.read();
}
```

## 🧱 Object design & immutability

### Prefer records for value objects
Use a `record` for classes that only carry data and are defined by their values (money, coordinates, DTOs,
ids).

**Why it's a best practice:** records give you `equals`, `hashCode` and `toString` for free, generated from the
components, so they can never drift apart when someone adds a field and forgets to update one of them. They are
also shallowly immutable (`final` fields, no setters), which removes a whole class of bugs. Validation still
fits in a compact constructor. The result: one line instead of ~50 lines of boilerplate that also has to be
maintained.

⛔ a class with a hand-written `equals` and no `hashCode`
✅ `record Money(BigDecimal amount, Currency currency) {}`

### Prefer immutability
Make fields `final`, don't expose setters, and make defensive copies of mutable inputs and outputs.

**Why it's a best practice:** an immutable object can be shared between threads without locks, since there's
nothing to race on. It's safe to use as a `HashMap` key or in a `HashSet`, and it can be cached and reused.
It's also easier to reason about: once it's built and valid, it stays valid, so you don't have to know who else
holds a reference. Without a defensive copy, the caller keeps a reference to the list and can change your object
from the outside, bypassing any validation. `List.copyOf` makes an unmodifiable copy (and doesn't copy again if
the list is already unmodifiable), so returning it directly is safe.

```java
// ⛔ caller can mutate the internal list
public Order(List<Line> lines) { this.lines = lines; }
public List<Line> lines() { return lines; }

// ✅
public Order(List<Line> lines) { this.lines = List.copyOf(lines); }
public List<Line> lines() { return lines; }
```

### Override `equals` and `hashCode` together
If two objects are `equals`, they must have the same `hashCode`.

**Why it's a best practice:** hash-based collections first use `hashCode` to find the bucket, then `equals`
inside it. If you override only `equals`, two "equal" objects land in different buckets: `set.contains(x)`
returns `false`, and `HashSet` stores duplicates. Nothing throws, it's just silently wrong. Never use mutable
fields in either: if a key changes after being inserted, its hash changes, the map looks in the wrong bucket,
and the entry is lost (still in memory, but unreachable). Simplest fix: use a record.

### Prefer static factories or builders over telescoping constructors
When a constructor has more than 3–4 parameters, or several of the same type, use a builder or named static
factory methods (`Money.of(...)`, `Duration.ofSeconds(...)`).

**Why it's a best practice:** `new Pizza("L", true, false, true, null)` can't be read without opening the class,
and swapping two `boolean`s compiles fine but is a bug. A builder names every argument, makes optional ones
really optional, and can validate the whole object in `build()`. Static factories have a name that explains
intent, can return cached instances or a subtype, and avoid having ten constructor overloads.

⛔ `new Pizza("L", true, false, true, null)`
✅ `Pizza.builder().size("L").cheese(true).ham(true).build()`

### Prefer composition over inheritance
Reuse behaviour by holding an instance of another class and delegating to it, instead of extending it.

**Why it's a best practice:** inheritance couples you to the parent's implementation details, not just its
API (the "fragile base class" problem). In the example, `HashSet.addAll()` calls `add()` internally, so
overriding both counts every element twice, and it would break again if a future JDK changed that internal
behaviour. The subclass also inherits every public method, including ones that bypass your logic. With
composition you expose only what you want, you control every call, and you can swap the delegate (e.g. for a
`TreeSet`).

Inheritance is still fine for a real "is-a" relationship, inside the same package or module, or when the parent
class is designed and documented for extension (abstract classes, template methods).

```java
// ⛔ inherits every HashSet method, and addAll() calls add() internally, counting twice
class CountingSet<E> extends HashSet<E> { ... }

// ✅ wrap and delegate
class CountingSet<E> {
    private final Set<E> delegate = new HashSet<>();
    private int added;

    boolean add(E e) { added++; return delegate.add(e); }
}
```

### Declare with interfaces, not implementations
Use the interface (`List`, `Map`, `Set`) as the type of variables, fields, parameters and return types. Use the
concrete class only after `new`.

**Why it's a best practice:** code then depends on *what* the object does, not *how*. You can switch from
`ArrayList` to `LinkedList`, or from `HashMap` to `LinkedHashMap`, by changing one line. Callers can also pass
any implementation (`List.of(...)`, `Arrays.asList(...)`, a Hibernate collection) instead of being forced to
convert. Returning `ArrayList` from a public method makes the implementation part of your API, and you can't
change it later without breaking callers.

⛔ `ArrayList<Order> orders = new ArrayList<>();`
✅ `List<Order> orders = new ArrayList<>();`

### Use enums instead of int / String constants
Represent a fixed set of values with an `enum`.

**Why it's a best practice:** with `int` or `String` constants, the compiler accepts any value: `update(42)`
compiles, and so does a typo like `"PIAD"`. An enum restricts the parameter to valid values at compile time.
You also get readable `toString()` in logs, `switch` expressions that the compiler can check for missing cases,
and `EnumMap` / `EnumSet`, which are faster and more compact than their hash-based versions. Enums can hold
fields and behaviour too (`Status.PAID.isFinal()`), which keeps related logic in one place.

```java
// ⛔
static final int STATUS_PAID = 1;
void update(int status) { ... }       // accepts 42

// ✅ type-safe, switchable, works with EnumMap / EnumSet
enum Status { PENDING, PAID, REFUNDED }
void update(Status status) { ... }
```

## 🧰 Standard library: the right type for the job

### Use `BigDecimal` for money
Never use `double` or `float` for amounts that must be exact.

**Why it's a best practice:** `double` is binary floating point, and most decimal fractions (0.1, 0.2) have no
exact binary representation. Tiny errors appear and add up over thousands of operations, and a total that's off
by a cent is a real accounting bug. `BigDecimal` stores the exact decimal value. It has its own traps, though:

- `new BigDecimal(0.1)` takes the already-wrong `double`, so build it from a `String` or with
  `BigDecimal.valueOf(double)` (which goes through `Double.toString`).
- Always set the scale and the `RoundingMode` explicitly. `HALF_EVEN` ("banker's rounding") avoids a
  systematic bias when rounding many values.
- `equals` compares the scale too, so `0.10` and `0.1` aren't equal. Use `compareTo` to compare values.

```java
// ⛔
double total = 0.1 + 0.2;                   // 0.30000000000000004
new BigDecimal(0.1);                        // 0.1000000000000000055511151231257827...

// ✅
BigDecimal total = new BigDecimal("0.10").add(BigDecimal.valueOf(0.2));
total = total.setScale(2, RoundingMode.HALF_EVEN);

// ⛔ equals compares the scale: 0.10 != 0.1
a.equals(b)
// ✅
a.compareTo(b) == 0
```

### Use `java.time`, not `Date` / `Calendar`
Use the `java.time` API (Java 8+). Store `Instant` (UTC), convert to a `ZonedDateTime` only for display.

**Why it's a best practice:** `Date` and `Calendar` are mutable (anyone holding a reference can change the
value), have confusing APIs (0-based months, years offset from 1900), and `SimpleDateFormat` isn't thread-safe:
sharing it as a `static` field gives corrupted dates under load. `java.time` types are immutable and thread-safe,
and each type says what it means: `Instant` is a point in time, `LocalDate` is a date without a time zone,
`ZonedDateTime` is a date and time in a region, `Duration` is an amount of time. Storing UTC avoids
daylight-saving bugs and confusion between servers in different zones. The user's time zone is a display
concern.

⛔ `new Date()`, `Calendar.getInstance()`, `SimpleDateFormat` (not thread-safe)
✅ `Instant.now()`, `DateTimeFormatter.ISO_INSTANT`

### Use `StringBuilder` in loops
Don't concatenate strings with `+` inside a loop.

**Why it's a best practice:** `String` is immutable, so each `+=` allocates a new string and copies everything
built so far. For n items that's O(n²) copying and a lot of garbage. The compiler optimizes `+` within a single
expression, but not across loop iterations. `StringBuilder` appends into one growing buffer, which is O(n).
For the simple "join with a separator" case, `String.join` or `Collectors.joining` is clearer and also avoids
the trailing-comma bug.

```java
// ⛔ creates a new String on each iteration
String csv = "";
for (String name : names) csv += name + ",";

// ✅ or just String.join(",", names)
StringBuilder csv = new StringBuilder();
for (String name : names) csv.append(name).append(',');
```

## 🌊 Streams & functional style

### No side effects in stream operations
Stream operations (`map`, `filter`, `forEach`...) shouldn't change external state. Build the result with a
terminal operation (`toList()`, `collect`, `reduce`) instead.

**Why it's a best practice:** a stream describes *what* result you want, and the pipeline decides how to
compute it. Adding to an external `ArrayList` from `forEach` works by chance: switch to `.parallel()` and it
becomes a data race (lost elements, `ArrayIndexOutOfBoundsException`), because `ArrayList` isn't thread-safe.
It's also harder to read: the reader has to find the mutable list to understand what the stream produces.
`.toList()` (Java 16+) returns an unmodifiable list, which is safe by default.

```java
// ⛔
List<String> result = new ArrayList<>();
orders.stream().filter(Order::isPaid).forEach(o -> result.add(o.id()));

// ✅
List<String> result = orders.stream().filter(Order::isPaid).map(Order::id).toList();
```

## 🧵 Concurrency

### Don't manage threads by hand
Use an `ExecutorService` (or virtual threads on Java 21+) instead of `new Thread()`, and concurrent
collections instead of `synchronized` wrappers.

**Why it's a best practice:** each `new Thread()` is an expensive OS thread, with no limit, no reuse, no
lifecycle management and no way to get a result or an exception back. Under load that means memory exhaustion
or thousands of competing threads. An executor limits concurrency, reuses threads, returns `Future`s, and can be
shut down cleanly. Virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`) make "one thread per task"
cheap for blocking I/O.

`Collections.synchronizedMap` locks the whole map for every call, and compound actions such as
"`get`, then `put`" still race because two threads can read the same old value. `ConcurrentHashMap` uses
fine-grained locking and offers atomic compound operations like `merge`, `compute` and `putIfAbsent`.

⛔ `new Thread(task).start();`, `Collections.synchronizedMap(new HashMap<>())`
✅ `ExecutorService` / virtual threads, `ConcurrentHashMap`

```java
// ✅ atomic check-then-act
counts.merge(key, 1, Integer::sum);
```

### Always clean up `ThreadLocal`
Call `remove()` in a `finally` block once the request or task is done.

**Why it's a best practice:** servlet containers and executors reuse pooled threads. A value left in a
`ThreadLocal` stays on the thread and is visible to the *next* request it handles. With a tenant id or a
security context, that means one user's request can run with another user's data or permissions. It also leaks
memory: the value (and in app servers, the whole application's classloader) can't be garbage-collected while
the thread is alive, which causes `OutOfMemoryError`s after redeploys. `finally` makes sure the cleanup runs
even when the handler throws.

```java
// ✅
CURRENT_TENANT.set(tenant);
try {
    handle(request);
} finally {
    CURRENT_TENANT.remove();
}
```

### Always shut down executors
An `ExecutorService` you create must be shut down. On Java 19+ open it in a try-with-resources block.

**Why it's a best practice:** the threads of a pool created with `Executors.newFixedThreadPool` aren't daemon
threads. If nobody calls `shutdown()`, they keep the JVM alive after `main` returns, and in a long-running app
every forgotten executor is a set of idle threads that never goes away. Since Java 19, `ExecutorService` is
`AutoCloseable`: `close()` stops accepting new tasks and waits for the submitted ones to finish, so the block
ends only when the work is done.

```java
// ⛔ threads leak, the JVM may never exit
ExecutorService pool = Executors.newFixedThreadPool(4);
pool.submit(task);

// ✅ waits for the tasks, then shuts the pool down
try (ExecutorService pool = Executors.newVirtualThreadPerTaskExecutor()) {
    pool.submit(task);
}
```

### Give `CompletableFuture` an executor and handle its errors
Pass your own executor to the `*Async` methods, and end the chain with `exceptionally` or `handle`.

**Why it's a best practice:** without an executor, `supplyAsync` runs on the shared `ForkJoinPool.commonPool()`,
which is sized for CPU work (number of cores minus one). Blocking I/O there starves every other user of the pool,
including parallel streams. And an exception inside an async stage doesn't show up anywhere unless someone calls
`join()` or adds a handler: the failure is stored in the future and silently dropped.

```java
// ⛔ blocks the common pool, errors vanish
CompletableFuture.supplyAsync(() -> client.fetch(id)).thenAccept(this::save);

// ✅
CompletableFuture.supplyAsync(() -> client.fetch(id), ioExecutor)
        .thenAccept(this::save)
        .exceptionally(e -> { log.error("Fetch failed for {}", id, e); return null; });
```

### Use atomics for simple shared state
For a shared counter or flag, use `AtomicInteger`, `AtomicLong`, `LongAdder` or `AtomicBoolean`. Use `volatile`
only for a single value written by one thread and read by others.

**Why it's a best practice:** `count++` is three operations (read, add, write). Two threads can read the same
value and both write `n + 1`, losing an increment. `volatile` doesn't fix that: it only guarantees visibility,
not atomicity. Atomics do the read-modify-write as one CPU instruction (compare-and-swap), with no lock.
`LongAdder` is even faster when many threads update the same counter, like request metrics.

⛔ `private volatile int count; ... count++;`
✅ `private final AtomicInteger count = new AtomicInteger(); ... count.incrementAndGet();`

### Always acquire locks in the same order
When code needs more than one lock, every thread must take them in the same global order.

**Why it's a best practice:** if thread A locks `from` then `to`, and thread B transfers the other way and locks
`to` then `from`, each ends up holding the lock the other one waits for. That's a deadlock: both threads block
forever, with no exception and no log. Ordering the locks by a stable key (an id) makes the cycle impossible.
`tryLock` with a timeout is the fallback when no natural order exists.

```java
// ⛔ transfer(a, b) and transfer(b, a) at the same time can deadlock
synchronized (from) { synchronized (to) { move(from, to, amount); } }

// ✅ always lock the smallest id first
Account first = from.id() < to.id() ? from : to;
Account second = first == from ? to : from;
synchronized (first) { synchronized (second) { move(from, to, amount); } }
```

### Don't block virtual threads inside `synchronized` (before Java 24)
On Java 21–23, use a `ReentrantLock` instead of `synchronized` around blocking calls run by virtual threads.

**Why it's a best practice:** a virtual thread is cheap because it gets unmounted from its carrier (OS) thread
when it blocks. Before Java 24 (JEP 491), a virtual thread that blocks while holding a monitor is *pinned*: the
carrier can't be reused. There are only as many carriers as CPU cores, so a few pinned threads doing slow I/O
freeze the whole application. `ReentrantLock` doesn't pin. Run with `-Djdk.tracePinnedThreads=full` to find
pinning.

```java
// ⛔ pins the carrier thread during the HTTP call (Java 21–23)
synchronized (this) { response = httpClient.send(request, ofString()); }

// ✅
lock.lock();
try { response = httpClient.send(request, ofString()); } finally { lock.unlock(); }
```

## 🧬 Generics & collections

### Never use raw types
Always give a generic type its parameter: `List<String>`, not `List`. Use `List<?>` when the type doesn't matter.

**Why it's a best practice:** a raw type turns off generic type checking. The compiler lets you add an `Integer`
to what is really a list of `String`s, with only a warning. The error shows up later as a `ClassCastException`
in the code that reads the list, far from the line that caused it. Raw types only exist for compatibility with
pre-Java 5 code.

```java
// ⛔ compiles, then throws ClassCastException at read time
List names = new ArrayList<String>();
names.add(42);
String first = (String) names.get(0);

// ✅
List<String> names = new ArrayList<>();
```

### Use bounded wildcards in APIs (PECS)
"Producer `extends`, consumer `super`": use `? extends T` for a parameter you read from, `? super T` for one you
write into.

**Why it's a best practice:** generics are invariant: a `List<Integer>` is *not* a `List<Number>`. A method
that takes `List<Number>` rejects a `List<Integer>` even though it only reads numbers from it. Wildcards make the
API accept every type that works, without casts. `Collections.copy(List<? super T> dest, List<? extends T> src)`
is the textbook example.

⛔ `double sum(List<Number> numbers)` — rejects `List<Integer>`
✅ `double sum(List<? extends Number> numbers)`

### Pick the right collection
Use `ArrayList` by default, `ArrayDeque` for stacks and queues, `EnumMap` / `EnumSet` for enum keys, and
`LinkedHashMap` when iteration order matters.

**Why it's a best practice:** `Stack` and `Vector` are legacy classes that synchronize every call for nothing.
`LinkedList` looks good for inserts on paper, but each node is a separate object: it uses much more memory,
misses the CPU cache on every step, and `get(i)` is O(n). `ArrayDeque` is faster for both stack and queue use.
`HashMap` iteration order is unspecified and can change between JDK versions, so tests that depend on it
break randomly.

⛔ `Stack<Task> stack = new Stack<>();`, `new LinkedList<>()` as a default list
✅ `Deque<Task> stack = new ArrayDeque<>();`, `new ArrayList<>()`

### Don't modify a collection while iterating over it
Use `removeIf`, an explicit `Iterator.remove()`, or build a new collection.

**Why it's a best practice:** removing from an `ArrayList` inside a for-each loop throws
`ConcurrentModificationException`, or worse, when the removed element is the second to last, silently skips the
last one: the loop ends early and no error is thrown. `removeIf` does it in one pass, correctly, and states the
intent.

```java
// ⛔ ConcurrentModificationException, or a skipped element
for (Order o : orders) if (o.isCancelled()) orders.remove(o);

// ✅
orders.removeIf(Order::isCancelled);
```

### Know that `List.of` and friends are immutable and reject `null`
`List.of`, `Set.of`, `Map.of`, `List.copyOf` and `Stream.toList()` return unmodifiable collections. `List.of`
and `copyOf` also throw on `null` elements.

**Why it's a best practice:** calling `add` on them throws `UnsupportedOperationException` at runtime, not at
compile time, because they implement the normal `List` interface. That's usually what you want, but a method
that receives one and tries to mutate it will fail in production. `Arrays.asList` is a different trap: it is
fixed-size, so `set` works but `add` throws. When a caller needs to modify the result, return
`new ArrayList<>(...)` and say so.

⛔ `List<String> tags = List.of("a"); tags.add("b");` — `UnsupportedOperationException`
✅ `List<String> tags = new ArrayList<>(List.of("a")); tags.add("b");`

## ✨ Modern Java

### Use `var` only when the type is obvious
Use `var` when the right-hand side already shows the type (`new`, a factory, a cast). Write the type when it
doesn't.

**Why it's a best practice:** `var` removes noise like `Map<String, List<Order>> map = new HashMap<>()`. But
with `var result = service.process(input);` the reader has to open another file to know what `result` is, and
code reviews happen without an IDE. It also infers the concrete type: `var list = new ArrayList<String>()` is an
`ArrayList`, not a `List`.

⛔ `var result = service.process(input);`
✅ `var orders = new ArrayList<Order>();`, `Order order = service.process(input);`

### Prefer switch expressions
Use `switch` as an expression with arrows (`->`), not the old statement with `break`.

**Why it's a best practice:** the old `switch` falls through to the next case when you forget a `break`, which
is a classic bug. The arrow form never falls through. As an expression, it must produce a value for every
input: with an enum or a sealed type, the compiler checks that all cases are covered, so adding a new enum
constant breaks the build instead of silently hitting a `default`.

```java
// ⛔ forgetting a break falls through
String label;
switch (status) {
    case PAID: label = "Paid"; break;
    case PENDING: label = "Pending";
    default: label = "Unknown";
}

// ✅ exhaustive, no default needed for an enum
String label = switch (status) {
    case PENDING -> "Pending";
    case PAID -> "Paid";
    case REFUNDED -> "Refunded";
};
```

### Use pattern matching instead of casts
Use `instanceof` with a binding variable, and record patterns to take a record apart.

**Why it's a best practice:** `if (o instanceof Order) { Order order = (Order) o; ... }` repeats the type, and
a copy-paste mistake between the check and the cast compiles fine and fails at runtime. Pattern matching tests
and casts in one step, and the variable is only in scope where the test succeeded.

⛔ `if (shape instanceof Circle) { double r = ((Circle) shape).radius(); }`
✅ `if (shape instanceof Circle c) { double r = c.radius(); }`
✅ `if (shape instanceof Circle(double r)) { ... }`

### Use sealed types for closed hierarchies
When a type has a fixed set of subtypes (payment methods, events, results), declare it `sealed` and list them
with `permits`.

**Why it's a best practice:** a sealed interface tells the compiler (and the reader) that no other
implementation exists. Combined with records and pattern matching in `switch`, you get exhaustiveness checks:
add a new subtype and every `switch` that doesn't handle it stops compiling. With an open interface you'd need a
`default` branch that throws, and you'd only find the missing case in production.

```java
// ✅
sealed interface Payment permits Card, Transfer {}
record Card(String number) implements Payment {}
record Transfer(String iban) implements Payment {}

String describe(Payment p) {
    return switch (p) {
        case Card c -> "Card " + c.number();
        case Transfer t -> "Transfer " + t.iban();
    };
}
```

### Use text blocks for multi-line strings
Write SQL, JSON and other multi-line strings as `"""` text blocks.

**Why it's a best practice:** concatenated lines with `"\n" +` and escaped quotes are hard to read and easy to
break: a missing space between two lines of SQL gives `FROM ordersWHERE`. A text block keeps the text as it
looks, handles indentation, and needs no escaping for `"`. Use `formatted(...)` for values, but never for SQL
parameters: those go in bind parameters.

```java
// ⛔
String json = "{\n" + "  \"name\": \"" + name + "\"\n" + "}";

// ✅
String json = """
        {
          "name": "%s"
        }
        """.formatted(name);
```

## 🧪 Testing & API design

### Inject dependencies and the clock
Take collaborators, and a `Clock` when time matters, as constructor parameters instead of creating them inside
the class or calling static methods.

**Why it's a best practice:** a class that calls `new EmailClient()` or `Instant.now()` can't be tested without
sending real emails or waiting for the right time. With the dependency injected, a test passes a fake, and with a
`Clock`, it passes `Clock.fixed(...)` and checks "expires in 30 days" deterministically. It also makes the
dependencies visible in the constructor: a constructor with 8 parameters is a sign the class does too much.

```java
// ⛔ untestable: depends on the real time
boolean isExpired() { return Instant.now().isAfter(expiresAt); }

// ✅
boolean isExpired(Clock clock) { return Instant.now(clock).isAfter(expiresAt); }
```

### Keep visibility as small as possible
Make classes and members `private` or package-private by default, and `public` only when another package needs
them.

**Why it's a best practice:** everything `public` is part of your API: someone will call it, and you can't
change it without breaking them. Package-private classes can be refactored freely. It also keeps each package
honest: if only the service is public, nobody can call the repository directly and skip your validation.
Tests in the same package can still reach package-private code.

⛔ `public class OrderMapper` used only by `OrderService` in the same package
✅ `class OrderMapper`

### Use unchecked exceptions for bugs, domain exceptions for business errors
Throw `IllegalArgumentException` / `IllegalStateException` for programming errors. Create specific exceptions
(`InsufficientFundsException`) for business rules the caller can react to.

**Why it's a best practice:** checked exceptions force every caller up the stack to declare or catch them, and
in lambdas they don't compose at all, so people end up wrapping or swallowing them. Most errors can't be
handled locally anyway and should go to a global handler. A named domain exception says what went wrong, can
carry data (the account, the missing amount), and can be mapped to a precise HTTP status. A generic
`RuntimeException("error")` can't.

⛔ `throw new RuntimeException("Not enough money");`
✅ `throw new InsufficientFundsException(accountId, missing);`

### Keep methods short and doing one thing
A method should do one thing at one level of abstraction. Extract a named method when a block needs a comment
to explain it.

**Why it's a best practice:** a 200-line method mixes validation, business rules, persistence and formatting,
so you can't test one without the others, and every change risks breaking an unrelated part. Small methods with
good names read like the steps of the algorithm. The name replaces the comment, and unlike a comment it can't
get out of date without someone noticing.

```java
// ⛔
void checkout(Cart cart) {
    // validate
    ... 30 lines ...
    // compute total
    ... 20 lines ...
}

// ✅
void checkout(Cart cart) {
    validate(cart);
    Money total = computeTotal(cart);
    charge(cart.customer(), total);
}
```

### Name things for what they mean
Use names that say what a value is in the domain, not its type. Avoid abbreviations and generic names like
`data`, `info`, `manager`, `tmp`.

**Why it's a best practice:** code is read far more often than it's written. `List<Order> list` tells you
nothing the type doesn't already say; `unpaidOrders` tells you what's in it and why it exists. Booleans read
best as questions (`isActive`, `hasDiscount`). Units belong in the name or the type: `timeout` is ambiguous,
`timeoutMs` or a `Duration` isn't.

⛔ `int d; // elapsed time in days`, `List<Order> list`, `long timeout`
✅ `int elapsedDays`, `List<Order> unpaidOrders`, `Duration timeout`
