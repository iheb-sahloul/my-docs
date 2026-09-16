# Java Core & JVM

## 🟡 Senior traps

### Q1. Walk through what actually happens inside `HashMap.put()` and `.get()`, and explain why a bad `hashCode()` is a real performance bug.
**Answer:** `put()` computes `hashCode()`, spreads it with an internal mix function
(`h ^ (h >>> 16)`, to fold high bits into the low bits so table sizes that are small powers of
two still get good distribution), and picks a bucket index from that hash modulo the table
capacity. If the bucket is empty, the entry goes there directly; if not, it's appended to that
bucket's collision chain (a linked list, or — since Java 8, once a bucket exceeds
`TREEIFY_THRESHOLD` (8) entries *and* the table has at least `MIN_TREEIFY_CAPACITY` (64)
buckets — converted to a balanced red-black tree keyed by hash then by a tie-break comparison)
and compared via `equals()` to detect duplicate keys. `get()` does the same hash computation to
jump to the right bucket, then walks/searches it — O(log n) in a treeified bucket, O(n) in a
list bucket. The tree also un-treeifies back to a list on removal once the bucket shrinks below
`UNTREEIFY_THRESHOLD` (6), so a bucket doesn't stay a tree forever if it was just a transient
spike. A `hashCode()` that returns the same value for many different objects (or worse, a
constant) forces every key into the same bucket, degrading lookups from average O(1) toward
O(log n) with treeification saving you somewhat — but a `hashCode()`/`equals()` contract
violation (two equal objects with different hashes) is worse than slow: it silently produces
*duplicate* entries for logically-equal keys, since `put()` never finds the existing one to
overwrite.

**Example:**
```java
class BadKey {
    final String id;
    BadKey(String id) { this.id = id; }

    @Override
    public boolean equals(Object o) {
        return o instanceof BadKey k && k.id.equals(id);
    }
    // hashCode() not overridden -> falls back to Object's identity hash.
    // equals() says two BadKeys with the same id are equal, but hashCode()
    // disagrees -> contract violation.
}

Map<BadKey, String> map = new HashMap<>();
map.put(new BadKey("42"), "first");
map.put(new BadKey("42"), "second"); // different identity hash -> different bucket
System.out.println(map.size()); // 2, not 1 — "duplicate" entries for an equal key
```

**Why it's a trap:** candidates recite "override `hashCode()` for performance" but miss that a
broken `equals()`/`hashCode()` contract isn't a slowdown — it's a correctness bug that silently
duplicates data.

### Q2. What causes `ConcurrentModificationException`, and what's the correct fix?
**Answer:** Java's collections use a fail-fast iterator backed by a `modCount` field; the
iterator snapshots `modCount` when created and checks it on every `next()`. Structurally
modifying the collection (add/remove, not just updating a value via `set()`) outside the
iterator's own `remove()` method — most commonly, calling `list.remove(x)` inside a
`for (x : list)` loop — bumps `modCount` and trips the check on the following `next()` call. The
check is deliberately *not* bulletproof: it's a best-effort detector, not a guarantee, so a
single-threaded remove-then-immediately-break loop can sometimes slip through without throwing,
which is why "it worked in my test" is not evidence of correctness here. The correct fix is to
use the iterator's own `Iterator.remove()`, or `Collection.removeIf(predicate)`, or (for
concurrent access) a concurrent collection like `CopyOnWriteArrayList` or `ConcurrentHashMap`,
which don't throw this exception because they don't track modifications the same way — they
instead offer weakly consistent iteration that may or may not reflect concurrent changes, which
is a different trade-off, not a strictly safer one.

**Example:**
```java
List<String> names = new ArrayList<>(List.of("Ann", "Bob", "Cid"));

for (String name : names) {
    if (name.equals("Bob")) {
        names.remove(name); // throws ConcurrentModificationException on next()
    }
}

// Fix: drive removal through the iterator itself.
Iterator<String> it = names.iterator();
while (it.hasNext()) {
    if (it.next().equals("Bob")) {
        it.remove(); // safe — updates modCount through the same iterator
    }
}
// Or, more idiomatically:
names.removeIf(n -> n.equals("Bob"));
```

**Why it's a trap:** it's easy to "fix" this by wrapping the loop in a `try/catch` or converting
to an index-based loop that skips an element after removal — both hide a real bug instead of
fixing it (the index-based version silently skips the element after the removed one).

### Q3. Name the thread-safe Singleton implementation strategies, and explain why Bill Pugh / static inner class is generally preferred.
**Answer:** Four common approaches: (1) eager initialization — a `static final` field,
instantiated at class-load time, simple and thread-safe but always pays the construction cost
even if unused; (2) synchronized `getInstance()` — correct but serializes every call forever,
even after the instance exists; (3) double-checked locking with a `volatile` field — lazy and
fast after the first call, but easy to get wrong without `volatile` (see Q4); (4) Bill Pugh's
static inner holder class — a private static nested class holds the `static final` instance, and
the JVM only loads (and thus initializes) that nested class the first time it's referenced,
giving lazy initialization with no synchronization at all, guaranteed by the JVM's class-loading
thread-safety. It's preferred over double-checked locking because it gets laziness and thread
safety for free, without the subtlety that pattern requires. An `enum` with a single value is the
other commonly cited approach, and it is *not* simply equivalent to Bill Pugh: it's also
thread-safe and lazy by construction, but it additionally protects against two attacks Bill Pugh
does not — reflection (a caller can force a private constructor to run twice via
`Constructor.setAccessible(true)`, but the JVM guarantees an enum constructor runs exactly once
per constant) and deserialization (a hand-written singleton that implements `Serializable` can be
deserialized into a brand-new second instance unless you explicitly add `readResolve()`; enums
handle this correctly with no extra code). So the real ranking for a senior answer isn't "Bill
Pugh and enum are both fine" — it's "enum is strictly more robust against adversarial or
accidental duplication; Bill Pugh is the right choice mainly when the singleton can't be an enum
(e.g. it needs to extend another class)."

**Example:**
```java
public class Registry {
    private Registry() { /* ... */ }

    private static class Holder {
        static final Registry INSTANCE = new Registry();
    }

    public static Registry getInstance() {
        return Holder.INSTANCE; // Holder class loads lazily, on first call, no lock needed
    }
}

// Reflection can still break Registry:
Constructor<Registry> c = Registry.class.getDeclaredConstructor();
c.setAccessible(true);
Registry second = c.newInstance(); // succeeds — a second, distinct instance

// An enum singleton closes that hole:
public enum EnumRegistry {
    INSTANCE;
}
// EnumRegistry.class.getDeclaredConstructor() throws NoSuchMethodException —
// enum constructors aren't invocable via reflection this way.
```

**Why it's a trap:** treating Bill Pugh and `enum` as interchangeably "the best" answer — an
interviewer probing further ("what about reflection?") is testing whether you actually know the
gap, not just the name of the pattern.

### Q4. What's the real difference between `synchronized` and `volatile`?
**Answer:** `synchronized` provides mutual exclusion (only one thread executes the block at a
time) **and** a happens-before edge: everything a thread did before releasing a lock is visible
to the next thread that acquires that same lock, including plain (non-volatile) writes made
earlier in the block. `volatile` provides *only* the visibility half of that — every read of a
volatile field sees the most recent write to it across threads, and the JVM is barred from
reordering other memory operations across a volatile read/write — with no mutual exclusion; two
threads can still race to increment a `volatile int` and lose an update, because `i++` is a
read-modify-write that isn't atomic even when the field is volatile. The senior trap is treating
them as interchangeable: use `volatile` for a single flag or reference where you need visibility
without contention (a shutdown flag, a double-checked-locking instance reference — see Q3), and
`synchronized` (or an explicit `Lock`, or an atomic class) when you need to protect a multi-step
invariant, i.e. more than one field/operation must be observed or updated as a unit.

**Example:**
```java
class Counter {
    private volatile int count = 0; // visibility only — no atomicity

    void increment() {
        count++; // read, add, write — three steps, not one; a lost update is possible
    }
}

class SafeCounter {
    private int count = 0; // plain field is fine — synchronized supplies visibility too

    synchronized void increment() {
        count++; // mutual exclusion makes the three steps effectively atomic
    }
}
```
Two threads calling `Counter.increment()` 100,000 times each can finish with a total noticeably
below 200,000 — `volatile` guarantees each thread eventually sees the latest value, not that no
other thread interleaves between the read and the write.

**Why it's a trap:** "volatile makes it thread-safe" is the single most common wrong answer to
this question — volatile only removes stale-read bugs, it does nothing about race conditions on
compound operations.

### Q5. Explain reachability analysis and GC roots, and name two garbage collection algorithms.
**Answer:** The JVM doesn't use reference counting; it periodically traces reachability from a
fixed set of **GC roots** — local variables and parameters on the stack of each live thread,
static fields, JNI references held by native code, and a few others (active monitors, JVM
internal references) — following every reference transitively. Anything not reachable from a
root is garbage, regardless of how many objects reference each other (which is why reference
cycles aren't a leak in Java, unlike naive reference counting — two objects that only reference
each other but that nothing else reaches are still collected together). Two named algorithms:
**G1 (Garbage First)**, the default since Java 9, which divides the heap into fixed-size regions
and collects the ones with the most garbage first, aiming for a configurable pause-time goal
rather than a fixed generation layout; and **ZGC**, a low-latency concurrent collector
(sub-millisecond target pauses even on very large heaps, using colored pointers and load barriers
to do marking and relocation concurrently with application threads) whose pause time stays
roughly flat regardless of heap size, unlike G1's pauses which still grow somewhat with live-set
size.

**Example:**
```java
class Node {
    Node other;
}

void demo() {
    Node a = new Node();
    Node b = new Node();
    a.other = b;
    b.other = a; // a and b reference each other — a reference-counting GC would leak this

    a = null;
    b = null;
    // Neither local variable is a GC root anymore, so the a<->b cycle
    // is unreachable as a whole and gets collected on the next cycle,
    // despite the objects still referencing each other.
}
```

**Why it's a trap:** candidates from a reference-counted-language background (Python, Swift,
Objective-C) sometimes assume Java has the same cycle-leak problem those languages have without
a cycle collector — Java's tracing GC never had that problem in the first place.

### Q6. What problem do virtual threads (Project Loom) actually solve, and where do they still fall over?
**Answer:** Platform threads are thin wrappers around OS threads — expensive to create
(megabyte-scale stacks) and limited in number (thousands, not millions), which is why
high-concurrency I/O-bound servers historically reached for reactive/async programming
(callbacks, `CompletableFuture` chains, WebFlux) to avoid blocking a scarce thread on a slow
network call. Virtual threads are JVM-managed, cheap (kilobytes, millions possible), and when a
virtual thread blocks on I/O, the JVM unmounts it from its carrier platform thread and frees that
platform thread to run other virtual threads — so you get to write ordinary blocking, sequential
code (`InputStream.read()`, JDBC calls) and still get reactive-style scalability under the hood,
without restructuring the code into callbacks. The two places this still bites in production: (1)
a virtual thread that blocks *inside* a `synchronized` block cannot be unmounted — it pins its
carrier thread instead, silently reproducing the old thread-starvation problem (see S11); and (2)
because virtual threads are so cheap that people spin up millions of them, any per-thread state
that used to be "free" at platform-thread scale — most commonly a `ThreadLocal` holding a large
object — stops being free, since it's now multiplied by orders of magnitude more threads, and
`ThreadLocal` was never designed with that cardinality in mind.

**Example:**
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (int i = 0; i < 100_000; i++) {
        executor.submit(() -> {
            // Ordinary blocking JDBC/HTTP call here — the JVM unmounts this
            // virtual thread from its carrier while it waits, instead of
            // parking a whole OS thread.
            Thread.sleep(Duration.ofMillis(50));
        });
    }
} // platform threads would never scale to 100,000 concurrent blocking tasks like this
```

**Why it's a trap:** "virtual threads make blocking code free" is only true until a
`synchronized` block or an oversized `ThreadLocal` is on the hot path — an interviewer asking
"what could go wrong?" is checking whether you know the two concrete failure modes, not just the
headline benefit.

### Q7. What's the difference between using `ExecutorService` and creating raw `Thread` objects, and what's a common pitfall with the common fork-join pool?
**Answer:** `ExecutorService` decouples task submission from thread management — you submit
`Runnable`s or `Callable`s to a pool with a bounded (or virtual-thread-per-task) size, get back
`Future`s, and the pool handles reuse, queuing, and shutdown; raw `Thread` creation gives you none
of that and doesn't scale past a handful of threads. The common pitfall: `parallelStream()` and
`CompletableFuture`'s default async methods (`thenApplyAsync` without an explicit executor, etc.)
both use the shared `ForkJoinPool.commonPool()`, sized by default to
`availableProcessors() - 1` — submitting a blocking I/O call into it (a JDBC query, an HTTP call)
can starve *every other* parallel stream and default-async `CompletableFuture` in the entire JVM
process, since they all share that one pool, including ones in unrelated libraries you don't
control. Blocking work belongs in its own dedicated executor, sized for the blocking workload
(often much larger than CPU count, since blocked threads aren't consuming CPU).

**Example:**
```java
// Dangerous: a slow HTTP call inside parallelStream() eats a commonPool thread
// that every other parallelStream() call in the JVM is also competing for.
List<String> results = urls.parallelStream()
    .map(url -> httpClient.get(url)) // blocking call on the shared commonPool
    .toList();

// Fix: give blocking work its own dedicated, sized-for-blocking pool.
ExecutorService ioPool = Executors.newFixedThreadPool(50);
List<Future<String>> futures = urls.stream()
    .map(url -> ioPool.submit(() -> httpClient.get(url)))
    .toList();
```

**Why it's a trap:** the bug doesn't show up in the code that has it — it shows up as an
unrelated, seemingly random slowdown in a completely different part of the application that also
happens to use `parallelStream()` or default-async `CompletableFuture`.

### Q8. Walk through `thenApply` vs `thenCompose` vs `thenCombine` on `CompletableFuture`, and name a common pitfall.
**Answer:** `thenApply` transforms the result with a plain function (`T -> U`) — use it when the
next step isn't itself async. `thenCompose` flattens a step that *returns* another
`CompletableFuture` (`T -> CompletableFuture<U>`) — the async equivalent of `flatMap`; using
`thenApply` here would give you a `CompletableFuture<CompletableFuture<U>>`, which almost always
means whoever consumes it forgot to unwrap a layer. `thenCombine` joins two *independent* futures
once both complete, running a `BiFunction` over both results. The common pitfall is calling
`.get()` or `.join()` on a future inside another future's callback (or worse, on a request
thread) — that blocks a thread waiting on async work, which defeats the purpose and, on the
common pool, risks the same starvation as Q7. Compose the chain instead of blocking mid-chain.

**Example:**
```java
CompletableFuture<User> userFuture = fetchUser(id);

// Wrong shape: thenApply on a step that returns a future -> nested future.
CompletableFuture<CompletableFuture<Order>> nested =
    userFuture.thenApply(user -> fetchLatestOrder(user)); // fetchLatestOrder returns a CF<Order>

// Correct: thenCompose flattens it.
CompletableFuture<Order> flat =
    userFuture.thenCompose(user -> fetchLatestOrder(user));

// Combining two independent futures:
CompletableFuture<Profile> profileFuture = fetchProfile(id);
CompletableFuture<Dashboard> dashboard =
    flat.thenCombine(profileFuture, (order, profile) -> new Dashboard(order, profile));
```

**Why it's a trap:** the compiler happily accepts the `thenApply` version with a nested future —
it's a type-shape bug, not a syntax error, so it only surfaces when a caller tries to use the
result and gets a `CompletableFuture` where they expected the actual value.

### Q9. Why is `String` immutable, and what is the string pool?
**Answer:** Once created, a `String`'s backing character storage is never mutated — every
"modifying" method (`concat`, `substring`, `replace`) returns a new `String`. This buys thread
safety without synchronization (safe to share across threads), lets `String` be safely used as a
`HashMap` key (its hash can be cached, computed once and stored in the object — see Q1's
performance discussion), and enables the **string pool** — literal strings (and interned strings)
are deduplicated in a shared pool, so `"abc" == "abc"` is `true` (same pooled reference) while
`new String("abc") == "abc"` is `false` (a distinct heap object bypasses the pool unless you call
`.intern()`). One historical nuance worth knowing: before Java 7, the string pool lived in
PermGen, a fixed-size metadata region — calling `.intern()` on many unique runtime strings (e.g.
interning every parsed token from user input) could exhaust PermGen and crash the JVM with
`OutOfMemoryError: PermGen space`. Since Java 7 the pool moved to the regular heap, so the same
misuse today just bloats heap usage instead of hitting a hard, separate ceiling — it's a smaller
problem than it used to be, but "interning every string I see" is still a bad habit that defeats
the pool's purpose of deduplicating a *bounded* set of recurring literals.

**Example:**
```java
String a = "hello";
String b = "hello";
String c = new String("hello");

System.out.println(a == b);           // true  — both resolve to the same pooled literal
System.out.println(a == c);           // false — c is a distinct heap object
System.out.println(a == c.intern());  // true  — intern() returns the pooled reference
```

**Why it's a trap:** candidates often say "strings are pooled" as a blanket statement without
the `new String(...)` caveat — an interviewer will immediately follow up with exactly that line
to see if the distinction is actually understood, not memorized as one fact.

### Q10. What's the autoboxing `==` trap with `Integer`?
**Answer:** The JVM caches boxed `Integer` values from -128 to 127 (`Integer.valueOf`'s internal
cache, populated at class-init time and guaranteed by the JLS, not just an implementation detail
you can't rely on), so `Integer a = 100; Integer b = 100; a == b` is `true` — both point at the
same cached object, per spec — while the identical code with `200` instead of `100` is `false`,
because values outside the cache range allocate a fresh object each time. This is a classic
interview trap precisely because it "works" in small examples and fails silently in production
once real data exceeds 127 — test fixtures and demo data are disproportionately likely to use
small numbers (ids, quantities, scores in a unit test), which is exactly why this bug survives
code review and passes tests before breaking in production with real values. The fix is
unconditional: use `.equals()` (or unbox to `int` and compare primitives) for boxed-type
comparison, never `==` — there's no threshold above which `==` becomes "safe enough."

**Example:**
```java
Integer a = 100, b = 100;
Integer x = 200, y = 200;

System.out.println(a == b); // true  — both in the cached [-128, 127] range
System.out.println(x == y); // false — outside the cache, two distinct objects

// The actual fix, independent of the value:
System.out.println(a.equals(b)); // true
System.out.println(x.equals(y)); // true
System.out.println(a.intValue() == b.intValue()); // true — unboxed primitive compare
```

**Why it's a trap:** it's one of the few Java bugs that is *specified* behavior, not a JVM
quirk — the JLS explicitly requires caching -128..127, which means relying on `==` "working" in
that range isn't even undefined behavior you got lucky with; it's guaranteed to keep working
right up until a real value crosses the boundary.

### Q11. What does `try-with-resources` actually guarantee, and what interface does it rely on?
**Answer:** Any resource implementing `AutoCloseable` (or `Closeable`, which extends it and
narrows `close()` to throw only `IOException`) declared in the `try(...)` parentheses has its
`close()` called automatically when the block exits — normally or via exception — in **reverse**
declaration order, without needing a `finally` block. If both the try block and `close()` throw,
the try block's exception is the one propagated, and the `close()` exception is attached to it as
a **suppressed** exception (retrievable via `getSuppressed()`), rather than one silently masking
the other the way a hand-written `try/finally` often does — a hand-written version that calls
`close()` in `finally` and lets that call throw will lose the original exception entirely if
`close()` also throws, which is a real and common bug in code written before Java 7.

**Example:**
```java
class Resource implements AutoCloseable {
    private final String name;
    Resource(String name) { this.name = name; System.out.println("open " + name); }
    @Override public void close() { System.out.println("close " + name); }
}

try (Resource r1 = new Resource("A"); Resource r2 = new Resource("B")) {
    System.out.println("using both");
}
// Output: open A, open B, using both, close B, close A — reverse declaration order.
```

**Why it's a trap:** candidates get the "automatic close" part right but rarely know the
suppressed-exception mechanism, which is exactly the detail that matters when debugging a
production stack trace that has a "Suppressed:" section a reader skipped past.

### Q12. Checked vs unchecked exceptions — what's the actual design trade-off?
**Answer:** Checked exceptions (subclasses of `Exception` but not `RuntimeException`) must be
declared or caught — the compiler forces the caller to acknowledge a specific, recoverable
failure mode (e.g. `IOException`). Unchecked exceptions (`RuntimeException` and its subclasses)
need no declaration and typically signal programming errors (`NullPointerException`,
`IllegalArgumentException`) that callers shouldn't be expected to recover from locally. The
trade-off in practice: checked exceptions document and enforce handling of genuinely recoverable
conditions, but overused (or used for things a caller can't meaningfully recover from) they push
teams toward `catch (Exception e) {}` boilerplate that swallows the exception's whole value —
which is why most modern Java frameworks (Spring's `DataAccessException` hierarchy included)
deliberately favor unchecked exceptions and reserve checked ones for truly recoverable,
caller-actionable failures. A related trap worth naming explicitly: `catch (Exception e) {}`
(or worse, `catch (Throwable t) {}`) also silently swallows unchecked exceptions and even
`Error`s that were never meant to be caught at all, so the "just catch everything" instinct
doesn't just hide checked-exception boilerplate — it can hide a real bug or even mask an
`OutOfMemoryError` that should have crashed the process loudly.

**Example:**
```java
// Checked: caller is forced to decide how to handle a recoverable failure.
void readConfig() throws IOException {
    Files.readString(Path.of("config.yml"));
}

// The lazy "fix" that defeats the point of checked exceptions:
try {
    readConfig();
} catch (Exception e) {
    // swallows IOException *and* any RuntimeException *and* would even
    // catch an AssertionError if the catch clause used Throwable instead
}
```

**Why it's a trap:** the "solution" candidates reach for under interview pressure —
`catch (Exception e) {}` — is the exact anti-pattern the question is probing for; a senior answer
names why that's worse than either checked or unchecked exceptions done properly.

### Q13. What is type erasure, and what does it actually break?
**Answer:** Generic type information (`List<String>` vs `List<Integer>`) exists only at compile
time for type-checking; the compiler erases it to raw types (`List`) with inserted casts, so at
runtime both are just `List`. This breaks: overloading two methods that differ only by generic
type parameter (`void f(List<String>)` and `void f(List<Integer>)` collide, same erasure);
creating a generic array (`new T[10]` doesn't compile, since the JVM needs a concrete component
type at the allocation site); and `instanceof` checks against a parameterized type
(`x instanceof List<String>` isn't allowed — only `x instanceof List<?>`). The concrete mechanism
the compiler uses to paper over one consequence of erasure is the **bridge method**: when a
subclass overrides a generic method with a more specific type
(`class IntBox extends Box<Integer> { void set(Integer v) { ... } }` overriding
`void set(T v)`), the compiler generates a synthetic bridge method `set(Object)` that casts and
delegates to `set(Integer)`, because at the bytecode level the erased superclass signature is
`set(Object)` and something has to satisfy it for polymorphism (virtual dispatch) to work
correctly. It's the same reason `List<String>.class` doesn't exist as a distinct object from
`List<Integer>.class` — there is exactly one `List.class` at runtime.

**Example:**
```java
class Box<T> {
    void set(T value) { }
}
class IntBox extends Box<Integer> {
    @Override void set(Integer value) { } // your source-level override
    // compiler also generates: void set(Object value) { set((Integer) value); }
    // — a synthetic bridge method, visible via IntBox.class.getDeclaredMethods()
}
```

**Why it's a trap:** candidates can usually name that erasure "removes generic type info at
runtime" but few can explain the bridge-method mechanism that makes polymorphism still work
correctly despite that — it's the difference between reciting the term and understanding what
the compiler had to do about it.

### Q14. What does a record's compact canonical constructor buy you that a Lombok `@Data` class doesn't structurally guarantee?
**Answer:** A record's compact constructor (`record Range(int lo, int hi) { Range { if (lo > hi)
throw new IllegalArgumentException(); } }`) runs validation *before* fields are assigned, as an
intrinsic part of the type's only way to be constructed — there's no setter, no second
constructor, no reflection-based builder that can bypass it, because a record's fields are
`private final` and there is exactly one canonical constructor path. `@Data` generates a mutable
class with setters by default; you can still get immutability from Lombok (`@Value`), but the
record gives you that guarantee as a language feature the compiler enforces, not a convention a
future maintainer can quietly violate by adding a setter or a second constructor that skips
validation.

**Example:**
```java
record Range(int lo, int hi) {
    Range { // compact constructor — runs before field assignment
        if (lo > hi) throw new IllegalArgumentException("lo > hi");
    }
}

Range r = new Range(5, 1); // throws immediately — no way to construct an invalid Range

@Data
class LombokRange {
    private int lo, hi; // mutable — setLo(999) after construction bypasses any validation
                          // that only lived in a constructor
}
```

**Why it's a trap:** "records and `@Data` classes are basically the same thing, just less
boilerplate" is the wrong mental model — the record's guarantee is structural (the compiler
enforces it), while `@Data`'s immutability (if you even remembered `@Value` instead) is a
convention that a later setter call or reflection-based framework can silently violate.

### Q15. How does pattern matching for `switch` combine with sealed types, and why does that matter for exhaustiveness?
**Answer:** Since Java 21, `switch` can pattern-match on a sealed type's permitted subtypes
directly: `switch (shape) { case Circle c -> ...; case Square s -> ...; case Triangle t -> ...; }`.
Because `Shape` is `sealed permits Circle, Square, Triangle`, the compiler knows the complete set
of possible subtypes and can verify every case is handled *without* a `default` branch — if a new
shape is added to `permits` later, every exhaustive switch over `Shape` across the codebase
becomes a compile error at the missing case, not a runtime gap. This turns what used to be a
runtime risk (forgetting to update a chain of `instanceof` checks, or a `default` branch in an
old-style switch that silently does the wrong thing for a case nobody thought to add) into a
compile-time guarantee. The trap version of this question asks what happens if you *do* add a
`default` branch "just in case" — doing so throws away the exhaustiveness check entirely, because
the compiler now considers the switch complete regardless of whether every permitted subtype has
its own case, so a newly added subtype silently falls into `default` instead of failing to
compile.

**Example:**
```java
sealed interface Shape permits Circle, Square, Triangle {}
record Circle(double r) implements Shape {}
record Square(double side) implements Shape {}
record Triangle(double base, double height) implements Shape {}

double area(Shape shape) {
    return switch (shape) {
        case Circle c -> Math.PI * c.r() * c.r();
        case Square s -> s.side() * s.side();
        case Triangle t -> 0.5 * t.base() * t.height();
        // no default needed — compiler proves every permitted subtype is handled
    };
}
// Adding `record Rectangle(...) implements Shape {}` to `permits` now makes
// this switch fail to compile until a Rectangle case is added.
```

**Why it's a trap:** adding a defensive `default -> throw new IllegalStateException()` feels
like good practice, but it silently reintroduces the exact runtime gap sealed types + exhaustive
switch were designed to eliminate at compile time.

### Q16. Java has garbage collection — how does a memory leak still happen?
**Answer:** GC only reclaims *unreachable* objects; a "leak" in Java is really unintentional
reachability — something still holds a reference to objects no one needs anymore, so they never
become eligible for collection. Classic causes: a `static` collection (cache, listener list) that
only grows and is never pruned; registered listeners/callbacks never unregistered, keeping the
whole object graph they close over alive; and `ThreadLocal` values not cleared before a thread is
returned to a pool — since pooled threads live indefinitely, anything left in their `ThreadLocal`
map lives with them, which is a particularly nasty leak in app-server thread pools because it's
invisible until the heap has been growing for days. Virtual threads (Q6) don't remove this risk;
they can make it worse in volume, since a `ThreadLocal` misuse that was bounded by "a few hundred
platform threads in the pool" is unbounded by "however many virtual threads happen to be alive
right now" if the value is never cleared.

**Example:**
```java
class RequestContext {
    private static final ThreadLocal<byte[]> BUFFER = ThreadLocal.withInitial(() -> new byte[1_000_000]);

    void handle() {
        BUFFER.get(); // do work with a per-thread scratch buffer
        // missing: BUFFER.remove();
        // On a pooled platform thread, this 1 MB buffer lives forever, tied to
        // that thread — multiply by pool size and it's a slow, steady leak.
    }
}
```

**Why it's a trap:** "GC handles memory for me" is the assumption that gets challenged here —
the interviewer wants to hear that a leak is a reachability bug the *application* owns, not
something a garbage collector could ever be expected to detect or fix.

### Q17. What's the difference between `StackOverflowError` and `OutOfMemoryError`, and where does each actually come from?
**Answer:** Both are `Error`s (not `Exception`s — the JVM is signaling something the application
generally shouldn't try to recover from), but they come from different memory regions.
`StackOverflowError` happens when a single thread's call stack exceeds its fixed size — almost
always unbounded or excessively deep recursion; increasing `-Xss` delays it but a genuine
infinite-recursion bug will still hit it eventually, just later. `OutOfMemoryError` happens on
the heap (`OutOfMemoryError: Java heap space`, when live objects plus garbage exceed the
configured heap and GC can't free enough), or in metaspace (`OutOfMemoryError: Metaspace`, from
loading too many classes — a classic classloader leak symptom, see S12), or even from too many
threads (`OutOfMemoryError: unable to create new native thread`, hitting an OS thread limit,
which is one more reason virtual threads (Q6) changed the failure mode of high-concurrency code —
that specific error becomes far less likely when threads are cheap) — the specific message after
the colon is the first thing to read, since the fix differs completely by region.

**Example:**
```java
// StackOverflowError — unbounded recursion, not a heap problem at all.
long factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1); // no base-case bug needed —
                                               // a large enough n alone overflows the stack
}

// OutOfMemoryError: Java heap space — a genuinely unbounded live set.
List<byte[]> leak = new ArrayList<>();
while (true) {
    leak.add(new byte[1_000_000]); // never removed, always reachable via `leak`
}
```

**Why it's a trap:** candidates sometimes reach for "increase the heap" or "increase the stack
size" as a universal fix for both — that treats the symptom, not the region-specific root cause,
and both errors keep recurring (just later) if the underlying algorithm is genuinely unbounded.

### Q18. Design a thread-safe, bounded, LRU cache from scratch. What are the real trade-offs?
**Answer:** A `LinkedHashMap` in access-order mode (`new LinkedHashMap<>(cap, 0.75f, true)`) with
`removeEldestEntry` overridden to evict past a size threshold gives you LRU semantics almost for
free, because access-order mode re-links an entry to the tail of the internal doubly-linked list
on every `get()`, so the head is always the least-recently-used entry — but it's not thread-safe
on its own, so you wrap access in a single lock (`synchronized` or a `ReentrantReadWriteLock`) or
use `Collections.synchronizedMap`. The trade-off at that point is a single global lock serializing
every read, which is fine for low-to-moderate contention but becomes the bottleneck under high
concurrency, since even a plain `get()` mutates the internal linked list (to record the access)
and therefore can't be a pure concurrent read. For higher throughput, the real answer is
segmenting the cache (striped locks, like old `ConcurrentHashMap` internals) or reaching for a
purpose-built library (Caffeine) that implements approximate LRU/LFU with lock-free reads via a
ring-buffer-based access log and sampling-based eviction — at that point you're trading perfect
LRU ordering for concurrency, which is almost always the right trade for a production cache. The
interview signal isn't reciting Caffeine's internals; it's recognizing *why* naive LRU and high
concurrency are in tension (every read is also a write to the ordering structure).

**Example:**
```java
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;

    LruCache(int capacity) {
        super(capacity, 0.75f, true); // true = access-order, not insertion-order
        this.capacity = capacity;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity; // evict the head once we exceed capacity
    }

    // Not thread-safe on its own — every public method must go through a lock:
    synchronized V getSafe(K key) { return get(key); }
    synchronized void putSafe(K key, V value) { put(key, value); }
}
```

**Why it's a trap:** candidates often stop at "use `LinkedHashMap` with `removeEldestEntry`" as
if that alone answers "thread-safe" — the question explicitly asked for thread-safe, and the
naive lock-everything fix is itself the setup for the follow-up about concurrency trade-offs.

### Q19. When would you choose virtual threads over a reactive stack (WebFlux) for a high-concurrency I/O-bound service, and vice versa?
**Answer:** Virtual threads (Q6) win when the codebase, its libraries, and its debugging tooling
assume blocking, synchronous code — most JDBC drivers, most existing business logic, stack traces
that read top-to-bottom — and you want reactive-scale concurrency without a full reactive
rewrite; you get that scalability essentially "for free" on unmodified blocking code, and thread
dumps stay readable. Reactive/WebFlux still wins when you need actual backpressure semantics (a
slow consumer explicitly signaling a fast producer to slow down — virtual threads don't give you
this, since each virtual thread still runs whatever synchronous code you wrote, with no signal to
the producer to slow down), or when your data sources are already fully non-blocking end-to-end
(R2DBC, reactive Mongo) and rewriting them as blocking would throw that away. In practice: default
to virtual threads for typical CRUD/proxy/orchestration services now that they're stable and
blocking libraries "just work" on them; reach for reactive specifically when backpressure or a
fully non-blocking pipeline is the actual requirement, not a default choice made because
"reactive is the modern way."

**Example:**
```java
// Virtual-thread style: ordinary blocking code, scales via cheap threads.
@GetMapping("/orders/{id}")
String getOrder(@PathVariable String id) {
    return jdbcTemplate.queryForObject(
        "select * from orders where id = ?", String.class, id); // blocks the virtual thread only
}

// Reactive style: explicit backpressure-aware pipeline, no thread blocks at all.
@GetMapping("/orders/{id}")
Mono<String> getOrderReactive(@PathVariable String id) {
    return r2dbcTemplate.selectOne(Query.query(where("id").is(id)), String.class);
}
```

**Why it's a trap:** "just use virtual threads everywhere, reactive is obsolete now" is an
overcorrection — it's right for the common CRUD case but wrong the moment backpressure or an
already-reactive downstream is a genuine requirement, and a senior answer names that boundary
instead of picking a universal winner.

### Q20. Walk through choosing between G1, ZGC, and Shenandoah for a latency-sensitive service.
**Answer:** Start from the actual constraint, not the collector name: G1 is the safe default —
mature, well-understood, region-based, tunable pause-time goals (`-XX:MaxGCPauseMillis`) — and is
fine for most services where "occasional tens-of-milliseconds pause" is acceptable. If the
service has a hard sub-10ms (or sub-millisecond) pause budget regardless of heap size — a trading
system, a real-time bidding path — ZGC and Shenandoah are the concurrent, low-pause collectors,
doing marking and compaction concurrently with application threads instead of stopping the world
for them; ZGC in particular scales pause time independently of heap size (via colored pointers
and load barriers, see Q5), so it stays flat even on very large (hundreds of GB) heaps, whereas
G1's stop-the-world pauses still creep up somewhat with a larger live set. The trade-off for both
concurrent collectors is somewhat higher CPU overhead (concurrent work competes with application
threads for cores) and, historically, a throughput cost versus G1 — though that gap has narrowed
significantly in recent JDK versions. The interview-worthy answer states the actual latency
requirement first (a number, in milliseconds, tied to an SLO), then picks the collector that fits
it, rather than defaulting to "ZGC is newer so it's better" — a batch ETL job with no user-facing
latency requirement gets nothing from ZGC's low pauses and pays its CPU overhead for no benefit.

**Example:**
```
# G1 — safe default, tunable pause goal:
-XX:+UseG1GC -XX:MaxGCPauseMillis=200

# ZGC — sub-millisecond pauses, flat regardless of heap size, more CPU overhead:
-XX:+UseZGC

# Choosing between them isn't a flag decision, it's an SLO decision:
# "p99 request latency must stay under 15ms" -> ZGC is a candidate.
# "occasional 100ms pause is acceptable, we care more about throughput" -> G1.
```

**Why it's a trap:** picking a collector by reputation ("ZGC is the fastest") instead of by the
service's actual latency SLO is a red flag — a batch job with no latency requirement gains
nothing from ZGC and pays its overhead for free, while a service with a genuine sub-10ms budget
that stays on G1 "because it's the default" is under-serving its own requirement.

## 🎯 Real-world scenarios

### S1. Production service throws `OutOfMemoryError: Java heap space` after a traffic spike
- **Symptoms:** The service was healthy for weeks, then during a marketing-driven traffic spike
  it starts throwing `OutOfMemoryError: Java heap space` and gets OOMKilled or restarted by the
  orchestrator.
- **Diagnosis:** Pull a heap dump on the next occurrence (`-XX:+HeapDumpOnOutOfMemoryError` should
  already be set in prod) and load it in a memory analyzer to find the dominator tree — what's
  retaining the most memory. Cross-check with monitoring: was this heap size always marginal and
  the spike just exposed it (scale the heap or add replicas), or did retained memory grow
  unboundedly with request volume (an actual leak, likely an unbounded cache or collection tied
  to request count)?
- **Example:**
  ```java
  // A classic accidental leak: caching per-request data in a static map that's
  // sized fine at low traffic but scales unboundedly with the traffic spike.
  static final Map<String, Response> responseCache = new HashMap<>(); // never evicted

  Response handle(Request req) {
      return responseCache.computeIfAbsent(req.key(), k -> compute(req));
  }
  ```
- **Resolution:** If it's genuinely undersized, raise `-Xmx` and/or add horizontal capacity. If
  it's a leak, fix the retaining reference (add eviction/bounding to the offending
  collection/cache, e.g. swap it for a bounded Caffeine cache) and redeploy; verify the heap now
  plateaus under sustained load instead of climbing.
- **Prevention:** Load-test with production-representative traffic before high-visibility events,
  alert on heap-usage trend (not just a threshold — a steady climb is the leak signature), and
  default new caches to a bounded implementation (Caffeine with a max size) rather than a plain
  `HashMap`.

### S2. The app freezes for several seconds at a time, seemingly at random
- **Symptoms:** No errors, no crashes, but latency graphs show periodic spikes where every
  request stalls for 2–5 seconds simultaneously, then recovers.
- **Diagnosis:** This pattern — everything pausing at once — is the signature of a stop-the-world
  GC pause, not application logic. Enable/check GC logs (`-Xlog:gc*`) and correlate pause
  timestamps against the latency spikes; if they line up, it's confirmed.
- **Example:**
  ```
  [12.481s][info][gc] GC(42) Pause Full (Allocation Failure) 1998M->1950M(2048M) 2412.331ms
  ```
  A `Pause Full` line at 2+ seconds lining up exactly with a request-latency spike on the same
  timestamp is the confirming evidence — not a coincidence to explain away.
- **Resolution:** Depending on what the GC log shows: if pauses correlate with full GCs, the
  young generation may be undersized (too many objects promoted too early) — tune generation
  sizing before switching collectors. If pauses are frequent but the pause-time goal itself is
  too loose, tighten `-XX:MaxGCPauseMillis`. If the service has a genuinely strict latency budget
  the current collector can't hit even tuned, that's the case for moving to ZGC/Shenandoah (Q20).
- **Prevention:** Ship GC pause metrics to the same dashboard as request latency so this
  correlation is a five-second check next time, not a fresh investigation; set a GC pause-time
  SLO alongside the request latency SLO.

### S3. `ConcurrentModificationException` appears intermittently in production logs
- **Symptoms:** A background job or request handler occasionally throws
  `ConcurrentModificationException`, but it's not reproducible locally and doesn't happen on
  every run.
- **Diagnosis:** Find every place the collection in the stack trace is iterated and every place
  it's structurally modified; intermittent means it only fails when a modification happens to
  land during an active iteration elsewhere — often a shared field iterated in one thread while
  another thread (a scheduled task, an event listener) adds/removes from it concurrently.
- **Example:**
  ```java
  class SubscriptionRegistry {
      private final List<Listener> listeners = new ArrayList<>();

      void notifyAll(Event e) {
          for (Listener l : listeners) l.onEvent(e); // thread A iterating
      }

      void unregister(Listener l) {
          listeners.remove(l); // thread B mutating concurrently — CME if they overlap
      }
  }
  ```
- **Resolution:** If it's genuinely single-threaded logic with a bad remove-during-iterate
  pattern, switch to `Iterator.remove()` or `removeIf` (Q2). If it's cross-thread access to shared
  mutable state, that's the real bug — either make access single-threaded (route through one
  executor), or move to a concurrent collection appropriate to the access pattern
  (`ConcurrentHashMap`, `CopyOnWriteArrayList` for read-heavy/write-light, which fits a listener
  list well since registration is rare and notification is frequent).
- **Prevention:** Treat any mutable collection reachable from more than one thread as a
  code-review flag; document ownership (which thread/component is allowed to mutate it) directly
  in the field's declaration.

### S4. A `HashMap`-backed lookup that used to be fast has gotten steadily slower over months
- **Symptoms:** A cache or index keyed by a custom object type was fast at launch; response times
  for that lookup have crept up as the dataset grew, disproportionately to the growth in entry
  count.
- **Diagnosis:** Check the key type's `hashCode()` implementation (Q1). A common bug:
  `hashCode()` was never overridden (falls back to `Object`'s identity hash, which is fine for
  distribution but breaks logical equality across separately-constructed instances) *or* was
  overridden incorrectly — e.g. based on a field that's constant or low-cardinality across most
  entries, collapsing most keys into a handful of buckets.
- **Example:**
  ```java
  class OrderKey {
      final String region; // only 4 possible values across millions of orders
      final String orderId;

      @Override public int hashCode() { return region.hashCode(); } // ignores orderId — bad!
      @Override public boolean equals(Object o) {
          return o instanceof OrderKey k && region.equals(k.region) && orderId.equals(k.orderId);
      }
  }
  // Every key in the same region collapses into the same bucket — O(n) lookups.
  ```
- **Resolution:** Fix `hashCode()` to incorporate all fields used in `equals()` with good
  distribution (`Objects.hash(region, orderId)` is the safe default), and make sure `equals()`
  and `hashCode()` stay consistent (equal objects must have equal hashes). Verify by checking
  bucket distribution before/after, or simply re-measuring lookup latency at the same data
  volume.
- **Prevention:** Generate `equals()`/`hashCode()` with the IDE or `record`/Lombok rather than
  hand-writing them, and add a test that asserts reasonable hash distribution for any custom key
  type used in a hot-path map.

### S5. Heap usage climbs steadily and never comes back down, even under light load
- **Symptoms:** Heap usage after each GC cycle trends upward over days, unrelated to current
  traffic — a classic sawtooth-that-never-resets pattern on the memory graph.
- **Diagnosis:** This is a leak, not a sizing problem (S1's spike scenario recovers between GCs;
  this doesn't). Heap dump plus dominator-tree analysis to find what's growing; the most common
  culprit is a `static` `Map`/`List` used as an ad-hoc cache with entries added on every request
  and never removed — check anything `static` first.
- **Example:**
  ```java
  static final Map<String, Session> activeSessions = new HashMap<>();

  void onLogin(String userId, Session session) {
      activeSessions.put(userId, session); // added on login...
      // ...but the logout handler was never wired up to remove it, so every
      // session that ever logged in stays reachable via this static map.
  }
  ```
- **Resolution:** Add bounding/eviction to the offending collection (size cap, TTL, or switch to
  a proper cache library), or fix the underlying logic if entries should have been removed on
  some lifecycle event that isn't firing (e.g. a listener never unregistered — see Q16).
- **Prevention:** Ban unbounded `static` mutable collections in code review as a default; require
  any intentional in-memory cache to state its bound and eviction policy explicitly.

### S6. CPU sits pegged near 100% with no proportional increase in request volume
- **Symptoms:** CPU utilization spikes and stays high even as request throughput stays flat or
  drops; the service is still technically responding, just slowly.
- **Diagnosis:** Take a thread dump (or several, a few seconds apart) and look for threads
  `RUNNABLE` in the same hot method across samples — that's a busy-wait or tight retry loop, not
  I/O wait (which would show `WAITING`/`TIMED_WAITING`). A common cause: a retry loop with no
  backoff spinning against a failing dependency, or a polling loop with too short an interval.
- **Example:**
  ```java
  while (true) {
      try {
          return call(dependency);
      } catch (Exception e) {
          // no backoff, no attempt cap — a failing dependency turns this into
          // a tight CPU-burning loop, retried thousands of times per second
      }
  }
  ```
- **Resolution:** Add exponential backoff (with jitter) to the retry/poll loop, and cap retry
  attempts; if it's a genuine algorithmic hot loop, profile it (async-profiler / JFR) to find the
  actual inefficiency rather than guessing.
- **Prevention:** Never ship a retry loop without backoff and a max-attempts limit; add a
  thread-dump-on-high-CPU runbook step so this diagnosis is routine, not a fire drill.

### S7. Under load, requests start timing out even though downstream dependencies are healthy
- **Symptoms:** Latency and error rate climb sharply past a certain concurrent-request threshold,
  even though the database/downstream services show normal response times on their own
  dashboards.
- **Diagnosis:** Thread dump during the slowdown; look for many threads `WAITING` on the executor
  queue rather than actively running — that's thread-pool exhaustion, requests queuing behind a
  fixed-size pool rather than a downstream being slow. Check the pool's configured size against
  actual concurrent demand, and check whether any handler is doing blocking work on a pool sized
  for something else (Q7's common-pool trap, or a web server's request-handling pool being used
  for a slow blocking call).
- **Example:**
  ```java
  @Async // uses a small default executor sized for lightweight tasks
  CompletableFuture<Report> generateReport() {
      return CompletableFuture.completedFuture(slowJdbcQuery()); // blocks that small pool's thread
  }
  ```
- **Resolution:** Size the pool to the actual concurrency need (with a queue and rejection
  policy, not unbounded), or move blocking work off the request-handling pool onto a dedicated
  one sized for it, or move to virtual threads where "pool size" stops being the constraint for
  I/O-bound work (Q6).
- **Prevention:** Expose executor queue depth and active-thread count as metrics, not just
  request latency — queue depth climbing while downstream latency is flat is the specific signal
  for this failure mode, and it's invisible without that metric.

### S8. Two services (or two code paths) occasionally deadlock and stop making progress
- **Symptoms:** A subset of requests simply hang forever — no error, no timeout fires, no
  crash — until the process is restarted.
- **Diagnosis:** Take a thread dump; the JVM explicitly detects and reports deadlocks in
  `jstack` output ("Found one Java-level deadlock"), naming the two threads and the locks each
  holds while waiting on the other.
- **Example:**
  ```java
  // Thread A:                          // Thread B:
  synchronized (accountA) {             synchronized (accountB) {
      synchronized (accountB) { ... }       synchronized (accountA) { ... } // opposite order -> deadlock
  }                                      }
  ```
- **Resolution:** Immediate mitigation is restarting the stuck instance (with alerting so it's
  not silent). The real fix is establishing a consistent lock acquisition order everywhere
  (always acquire lock A before lock B, never the reverse in any code path — e.g. always lock
  accounts in a fixed order such as by account id), or replacing multiple locks with one coarser
  lock, or using `tryLock()` with a timeout so a deadlock becomes a recoverable timeout instead of
  a permanent hang.
- **Prevention:** Keep lock ordering documented and enforced by convention (or a static analysis
  rule); prefer higher-level concurrency utilities (`java.util.concurrent` classes,
  `synchronized` on a single well-defined object) over hand-rolled multi-lock schemes.

### S9. A financial calculation is occasionally wrong by a small, inconsistent amount
- **Symptoms:** A comparison between two `Integer` values behaves correctly in testing (small
  values) but intermittently misbehaves in production with real (larger) numbers — logic that
  should be equivalent to a numeric comparison silently takes the wrong branch.
- **Diagnosis:** Grep the code path for `==` between boxed types (`Integer`, `Long`); this is the
  autoboxing cache trap from Q10 — values in `[-128, 127]` happen to be `==`-equal by
  specification, values outside that range aren't, and test data conveniently staying inside that
  range (small unit prices, small quantities) is exactly why it passed review and testing.
- **Example:**
  ```java
  class Invoice {
      Integer amountDue; // boxed — comes from a DB row mapper as an Integer
  }

  boolean isFullyPaid(Invoice invoice, Integer amountPaid) {
      return invoice.amountDue == amountPaid; // "works" in tests with small amounts like 50
                                               // silently wrong once a real invoice hits 200+
  }
  ```
- **Resolution:** Replace `==` with `.equals()` for boxed comparisons, or unbox to primitive
  `int`/`long` and compare those directly; add a regression test using a value outside the cache
  range specifically (e.g. an invoice amount of 500, not 50).
- **Prevention:** Enable a static-analysis rule (Error Prone, SonarQube) that flags `==` between
  boxed types — this bug class is common enough to be worth banning mechanically rather than
  relying on review.

### S10. A newly deployed feature crashes with `StackOverflowError` for a subset of users
- **Symptoms:** Errors appear only for certain inputs (e.g. deeply nested comment threads, large
  category trees) right after a feature ships that processes a tree or graph recursively.
- **Diagnosis:** The stack trace itself is the diagnosis tool — it shows the same few frames
  repeating hundreds of times, identifying exactly which recursive call is unbounded; correlate
  the failing inputs with unusually deep nesting.
- **Example:**
  ```java
  int countDescendants(Comment comment) {
      int total = comment.replies().size();
      for (Comment reply : comment.replies()) {
          total += countDescendants(reply); // no depth guard — a 50,000-deep reply
      }                                     // chain from one abusive thread overflows the stack
      return total;
  }
  ```
- **Resolution:** Add an explicit depth limit with a clear error before the JVM's own stack
  limit is hit (a controlled `400 Bad Request` beats an uncontrolled crash), or convert the
  recursion to an iterative approach with an explicit stack/queue data structure if arbitrary
  depth must be supported.
- **Prevention:** Any recursive algorithm over user-influenced data (comment trees, category
  hierarchies, JSON parsing) needs an explicit, tested depth bound as part of the original
  design, not an afterthought once it crashes.

### S11. After migrating a service to virtual threads, thread-pool-style throughput actually gets worse under load
- **Symptoms:** Post-migration to virtual threads, the service that was expected to scale better
  instead shows carrier-thread contention — throughput plateaus well below expectations, and
  thread dumps show many virtual threads stuck rather than progressing.
- **Diagnosis:** Look for `synchronized` blocks or methods on the hot path (Q6). Until pinning
  was substantially improved in recent JDKs, a virtual thread blocking *inside* a `synchronized`
  block can't be unmounted from its carrier platform thread — it pins the carrier, so a blocking
  I/O call inside `synchronized` blocks that carrier thread exactly like the old model, defeating
  the point. JFR's virtual thread pinning events (`jdk.VirtualThreadPinned`) will confirm it.
- **Example:**
  ```java
  synchronized void processOrder(Order order) {
      paymentClient.charge(order); // blocking network call while holding the monitor
      // this virtual thread pins its carrier platform thread for the whole
      // duration of the network call — no unmounting happens inside synchronized
  }
  ```
- **Resolution:** Replace `synchronized` with `java.util.concurrent.locks.ReentrantLock` around
  any section that also does blocking I/O — `ReentrantLock` doesn't pin the carrier thread the
  same way. Keep `synchronized` only for short, non-blocking critical sections.
  ```java
  private final ReentrantLock lock = new ReentrantLock();

  void processOrder(Order order) {
      lock.lock();
      try {
          paymentClient.charge(order); // no pinning — the carrier is free while this blocks
      } finally {
          lock.unlock();
      }
  }
  ```
- **Prevention:** When adopting virtual threads, audit `synchronized` usage on any path that also
  performs I/O as part of the migration, not after a regression shows up.

### S12. Metaspace usage grows every time the application is redeployed on a long-lived app server
- **Symptoms:** `OutOfMemoryError: Metaspace` after several redeploys on the same JVM instance
  (a hot-redeploy application server setup), even though the application code itself hasn't
  obviously grown.
- **Diagnosis:** This is a classloader leak — each redeploy should let the old application's
  classloader (and every class it loaded) become garbage once the new version is live, but
  something is still holding a reference to the old classloader, so none of its classes are ever
  unloaded and metaspace accumulates one full copy of the class metadata per redeploy. Usual
  suspects: a JDBC driver registered via `DriverManager` and never deregistered, a `ThreadLocal`
  holding an instance of an application class on a long-lived thread pool thread (Q16), or a
  static reference in a library that outlives the redeploy.
- **Example:**
  ```java
  // In a servlet context listener, on application shutdown:
  Enumeration<Driver> drivers = DriverManager.getDrivers();
  while (drivers.hasMoreElements()) {
      Driver d = drivers.nextElement();
      if (d.getClass().getClassLoader() == this.getClass().getClassLoader()) {
          DriverManager.deregisterDriver(d); // without this, the driver keeps the
      }                                      // old webapp classloader reachable forever
  }
  ```
- **Resolution:** Explicitly deregister JDBC drivers and clear `ThreadLocal`s in a shutdown hook,
  or — the pragmatic fix most teams actually take — stop doing hot redeploys and restart the JVM
  process per deployment instead, which is standard practice in container-based deployments
  anyway.
- **Prevention:** In a containerized world, avoid the hot-redeploy pattern entirely — one process
  per deployed version, replaced wholesale, sidesteps this entire class of leak.

### S13. Under load, a "singleton" service occasionally gets constructed more than once, causing duplicate side effects
- **Symptoms:** A component meant to be a single shared instance (e.g. initializing a metrics
  registry, opening a connection pool) occasionally logs its "initializing" message twice under
  concurrent startup load, and downstream duplicate-resource symptoms follow (double-registered
  metrics, doubled connection pool).
- **Diagnosis:** Check the singleton's implementation for the double-checked-locking pattern
  *without* a `volatile` field, or a lazy `getInstance()` with no synchronization at all — under
  concurrent first access, two threads can both see the field as `null`, both proceed to
  construct an instance, and the second write silently overwrites the first (or, without
  `volatile`, a thread can observe a partially-constructed object due to instruction reordering).
- **Example:**
  ```java
  class MetricsRegistry {
      private static MetricsRegistry instance; // missing volatile

      static MetricsRegistry getInstance() {
          if (instance == null) {
              synchronized (MetricsRegistry.class) {
                  if (instance == null) {
                      instance = new MetricsRegistry(); // reordering can publish a
                  }                                      // partially-constructed reference
              }
          }
          return instance;
      }
  }
  ```
- **Resolution:** Switch to the Bill Pugh static-holder-class pattern (Q3), which the JVM
  guarantees is thread-safe with no synchronization needed, or add `volatile` if double-checked
  locking must be kept for some reason.
- **Prevention:** Default to the static-holder pattern (or an `enum` singleton) for any
  hand-rolled singleton rather than double-checked locking — it's strictly simpler and removes
  this whole failure class.

### S14. GC pause times get noticeably worse right after a JDK/collector upgrade
- **Symptoms:** After upgrading the JDK version (or switching the default collector), p99 latency
  regresses even though throughput and CPU look similar to before.
- **Diagnosis:** Compare GC logs before and after; a common cause is that heap-sizing flags
  (`-Xmx`, `-Xms`, generation ratios) tuned for the old collector's behavior don't transfer
  cleanly to the new one's defaults — e.g. G1's region size and pause-time goal interact
  differently with a given heap size than the collector it replaced.
- **Example:**
  ```
  # Old flags, tuned for an older collector's defaults, carried over verbatim:
  -Xmx4g -XX:NewRatio=2 -XX:MaxGCPauseMillis=500
  # New collector's own recommended starting point, re-tuned instead of copied:
  -Xmx4g -XX:MaxGCPauseMillis=100
  ```
- **Resolution:** Re-tune from the collector's own recommended starting point rather than
  carrying over old flags verbatim; set an explicit `-XX:MaxGCPauseMillis` goal matching the
  actual SLO and let G1 (or the new collector) adapt region sizing to hit it, then measure again
  under representative load.
- **Prevention:** Treat a collector or major JDK version change as a performance-sensitive
  deployment requiring a load test and GC-log comparison before it reaches production, not a
  routine dependency bump.

### S15. `NullPointerException`s spike sharply right after a library dependency upgrade
- **Symptoms:** A previously stable service starts throwing `NullPointerException` in several
  unrelated call sites immediately after bumping a dependency version, with no application code
  changes.
- **Diagnosis:** Check the dependency's changelog for a method that used to return a sentinel
  (an empty collection, an empty string) and now returns `null` in some case, or — increasingly
  common — a method that changed its return type to `Optional<T>`, and callers that were doing a
  direct field/method access on the old return type are now calling straight through the
  `Optional` wrapper or unwrapping it incorrectly (`.get()` without checking `.isPresent()`).
- **Example:**
  ```java
  // Old library version: findById returned User, or null if not found.
  User user = repository.findById(id);
  user.getEmail(); // worked fine — call sites already null-checked `user` where needed

  // New library version: findById now returns Optional<User> instead.
  Optional<User> maybeUser = repository.findById(id);
  maybeUser.get().getEmail(); // .get() without .isPresent() throws NoSuchElementException,
                              // or a lazy caller casts/ignores the change and gets an NPE
                              // from treating the Optional itself as the User
  ```
- **Resolution:** Fix each call site to handle the new contract properly — `Optional` should be
  consumed with `.map()`/`.orElse()`/`.ifPresent()`, not called `.get()` on blindly; pin the
  dependency version pending the fix if the issue is spreading faster than it can be patched.
- **Prevention:** Pin dependency versions and review changelogs (especially return-type/nullability
  changes) before bumping, rather than auto-upgrading; enable a nullability-checking static
  analyzer where the codebase's conventions support it.

### S16. Throughput flattens under high concurrency even though CPU has headroom
- **Symptoms:** Adding more concurrent load doesn't increase throughput past a certain point, and
  CPU utilization stays well under 100% — the system isn't compute-bound, but it's also not
  scaling.
- **Diagnosis:** Thread dump under load; look for many threads `BLOCKED` (not `WAITING` on I/O,
  specifically `BLOCKED` on monitor entry) all queued on the same `synchronized` method — that's
  lock contention on an overly coarse-grained critical section, serializing work that didn't need
  to be serialized.
- **Example:**
  ```java
  class RequestCounter {
      private long total = 0;
      private final Map<String, Object> unrelatedCache = new HashMap<>();

      synchronized void recordRequest(String endpoint) { // the whole method is one lock
          total++;
          unrelatedCache.computeIfAbsent(endpoint, k -> loadMetadata(k)); // slow, unrelated work
      }                                                                   // serialized behind
  }                                                                       // the same monitor
  ```
- **Resolution:** Narrow the critical section to only the actually-shared mutable state (don't
  synchronize the whole method if only a counter update needs protecting), switch to a
  finer-grained or lock-free structure — here, an `AtomicLong` for `total` and a
  `ConcurrentHashMap` for the cache removes the shared lock entirely:
  ```java
  class RequestCounter {
      private final AtomicLong total = new AtomicLong();
      private final Map<String, Object> unrelatedCache = new ConcurrentHashMap<>();

      void recordRequest(String endpoint) {
          total.incrementAndGet();
          unrelatedCache.computeIfAbsent(endpoint, k -> loadMetadata(k));
      }
  }
  ```
  If the contended resource is genuinely a single shared sequential dependency, that's a real
  architectural bottleneck to redesign around (e.g. partitioning the workload so different
  requests don't contend on the same lock at all).
- **Prevention:** Keep `synchronized` blocks as small as possible by default, and load-test new
  shared-state code under realistic concurrency before it ships — this failure mode often doesn't
  show up until traffic reaches production scale.

## 📌 Cheat-sheet

- **`HashMap` collision chain** → tree once a bucket has >8 entries and table ≥64 buckets, un-trees back below 6 entries; bad `hashCode()` degrades O(1) toward O(log n) — but a broken `equals()`/`hashCode()` contract silently *duplicates* keys, which is worse than slow.
- **`ConcurrentModificationException`** → fail-fast iterator + `modCount`; fix with `Iterator.remove()`/`removeIf`, not manual remove-during-iterate or an index-based workaround.
- **Singleton, ranked:** `enum` (best — also blocks reflection/deserialization attacks) ≈ Bill Pugh static holder (best when it can't be an enum) > double-checked locking with `volatile` > synchronized accessor > eager `static final`.
- **`synchronized`** = mutual exclusion + a happens-before edge (visibility of everything before the lock release). **`volatile`** = visibility only, no atomicity for compound ops like `i++`.
- **GC roots**: stack locals, static fields, JNI refs — reachability, not reference counting; cycles aren't leaks.
- **Virtual threads** = cheap, JVM-managed, unmount on blocking I/O — but `synchronized` around I/O pins the carrier thread, and a `ThreadLocal` habit that was harmless at platform-thread scale isn't at virtual-thread scale.
- **Common pool trap**: `parallelStream()` and default-async `CompletableFuture` share one JVM-wide `ForkJoinPool.commonPool()` — a blocking call in either can starve unrelated code elsewhere in the process.
- **`thenCompose` vs `thenApply`**: use `thenCompose` when the next step itself returns a `CompletableFuture`, or you get a nested future by mistake.
- **`Integer` cache**: -128..127 is *specified*, not a coincidence — `==` "works" by contract in that range, breaks (also by contract) outside it; always use `.equals()` or unbox.
- **try-with-resources** closes in reverse order; try-block exception wins, `close()` exception is attached as suppressed — a hand-written `finally` block often loses one of the two silently.
- **Checked exceptions** = compiler-enforced recoverable conditions; **unchecked** = programming errors. `catch (Exception e) {}` is the anti-pattern both designs are trying to prevent.
- **Type erasure** breaks: overload-by-generic-parameter, generic array creation, `instanceof ParameterizedType` — the compiler patches polymorphism around it with synthetic bridge methods.
- **Sealed + switch pattern matching** = compiler-verified exhaustiveness — but adding a defensive `default` branch throws that guarantee away.
- **Leak despite GC** = unintended reachability: static collections, un-removed listeners, uncleared `ThreadLocal` on pooled threads (worse at virtual-thread scale).
- **`StackOverflowError`** = stack region, unbounded recursion. **`OutOfMemoryError`** = heap/metaspace/native-thread region — read the message after the colon; raising `-Xmx`/`-Xss` delays, doesn't fix, a genuinely unbounded algorithm.
- **Collectors:** G1 = safe default, tunable pause goal. ZGC/Shenandoah = concurrent, sub-ms pauses flat across heap size, some CPU/throughput cost — pick by the service's actual latency SLO, not by reputation.
