# Live Coding & Algorithms

Senior full-stack interviews rarely ask for exotic algorithms. They check that you can turn a problem into clean, tested code while talking, pick the right data structure, and reason about complexity. Java collection internals are in [Java Q6](java-core-jvm.md#arraylist-linkedlist-hashmap-treemap-linkedhashmap) and [Java Q18](java-core-jvm.md#happens-inside-hashmap-put-get).

## 🟢 Fundamentals

### Method

#### Q1. How do you approach a live-coding exercise? {#approach-live-coding-exercise}
**Answer:** Follow a visible process, because the interviewer grades it as much as the result.

1. **Clarify** (2–3 min): restate the problem, ask about input size, empty or null input, duplicates, negative
   numbers, sorted or not, and the expected output for one example.
2. **Examples**: write two or three small cases, including an edge case.
3. **Brute force first**: say it out loud with its complexity, then improve it if needed.
4. **Plan** the better approach in a sentence or two before typing.
5. **Code** with clear names and small helper methods; talk while you type.
6. **Test** by walking through your examples by hand, then edge cases; fix bugs calmly.
7. **Analyse** time and space complexity and mention what you'd do with more time.

**Example:**

```text
"So the input is an unsorted array of up to 10^5 ints, possibly negative, and I return the indices
of two numbers summing to target, exactly one answer guaranteed? Brute force is O(n²) pairs; with a
HashMap of value → index I can do it in one pass, O(n) time and O(n) space. Let me code that."
```

#### Q2. How do you explain Big-O, and what are the complexities you must know by heart? {#big-o-complexities-know-heart}
**Answer:** Big-O describes how time or memory **grows with input size** in the worst case, ignoring constants. The
ones to know: O(1) hash lookup and array index; O(log n) binary search and balanced-tree operations (`TreeMap`); O(n)
one pass; O(n log n) comparison sort (`List.sort`, `Arrays.sort` on objects); O(n²) nested loops over the same input;
O(2ⁿ) all subsets. Translate to input size: for n = 10⁵, O(n²) is 10¹⁰ operations, too slow; O(n log n) is about
1.7 million, instant. Also state **space** complexity and amortized costs (`ArrayList.add` is amortized O(1)).

**Example:**

```text
n = 1,000,000
O(n)        1e6 ops    ✅ ~ms
O(n log n)  2e7 ops    ✅
O(n²)       1e12 ops   ⛔ hours
```

#### Q3. Which Java data structures do you reach for in coding exercises? {#java-data-structures-coding-exercises}
**Answer:** `HashMap`/`HashSet` for O(1) lookup, counting and deduplication; `ArrayList` for indexed lists;
`ArrayDeque` as both stack (`push`/`pop`) and queue (`offer`/`poll`); `PriorityQueue` as a min-heap (pass
`Comparator.reverseOrder()` for a max-heap); `TreeMap`/`TreeSet` for sorted order and floor/ceiling queries;
`int[]`/`boolean[]` for fixed-size counts and visited flags (faster than boxed collections); `StringBuilder` for
string building in loops. Know the handy methods: `getOrDefault`, `merge`, `computeIfAbsent`, `Arrays.fill`,
`Collections.swap`.

**Example:**

```java
Map<Character, Integer> freq = new HashMap<>();
for (char c : s.toCharArray()) freq.merge(c, 1, Integer::sum);

Map<String, List<String>> groups = new HashMap<>();
groups.computeIfAbsent(key, k -> new ArrayList<>()).add(word);
```

### Core patterns

#### Q4. When do you use a hash map to turn O(n²) into O(n)? Solve "two sum". {#hash-map-turn-o-n2}
**Answer:** Whenever the brute force is "for each element, search the rest for a partner", store what you've already
seen in a hash map keyed by what you'll need to look up. For two sum, for each number check whether `target - x` was
seen, then record `x`. One pass, O(n) time, O(n) space.

**Example:**

```java
int[] twoSum(int[] nums, int target) {
    Map<Integer, Integer> seen = new HashMap<>();          // value -> index
    for (int i = 0; i < nums.length; i++) {
        Integer j = seen.get(target - nums[i]);
        if (j != null) return new int[] { j, i };
        seen.put(nums[i], i);
    }
    throw new IllegalArgumentException("no solution");
}
```

#### Q5. Find the duplicate elements in a list. {#find-duplicate-elements-list}
**Answer:** Clarify first: return every value that appears more than once (each once), or just the first duplicate? Keep input
order? The standard solution is a **`HashSet`**: iterate once, `add` returns `false` when the value was already seen. That is
O(n) time and O(n) space, against O(n²) for comparing every pair. Use a second set (or a `LinkedHashSet`) for the duplicates so
each is reported once and in first-seen order. If you may not use extra memory and the list can be sorted, sorting first
(O(n log n)) makes duplicates adjacent. If values are `1..n` you can mark visited indices in place. With streams,
`Collectors.groupingBy(identity(), counting())` is readable but builds a full count map. Edge cases: empty list, `null`
elements (`HashSet` accepts one null; `List.of` rejects it), and whether `equals`/`hashCode` are correct for custom types.

**Example:**

```java
static <T> Set<T> duplicates(Collection<T> items) {
    Set<T> seen = new HashSet<>();
    Set<T> dups = new LinkedHashSet<>();                 // keeps first-duplicate order
    for (T item : items) {
        if (!seen.add(item)) dups.add(item);            // add() == false -> seen before
    }
    return dups;
}
// duplicates(List.of(3, 1, 3, 2, 1, 3))  ->  [3, 1]      O(n) time, O(n) space
```

**Why it's a trap:** the nested-loop version works on the sample and fails on a million rows, and using a `List.contains`
inside the loop is the same O(n²) in disguise. Mutable keys with a bad `hashCode` silently break the set (see
[Java Q19](java-core-jvm.md#mutable-object-field-based-hashcode)).

#### Q6. Find the first non-repeating character in a string. {#find-first-non-repeating-character}
**Answer:** Two passes with a frequency map: pass 1 counts each character, pass 2 returns the first character whose count is
1. Time O(n), space O(k) where k is the alphabet size (O(1) for ASCII with an `int[256]`, larger for Unicode). A single pass is
possible with a `LinkedHashMap` that keeps insertion order, then you scan the map for the first count of 1, but the
two-pass version is simpler and just as fast. Clarify the contract before coding: case sensitivity, what to return when
none exists (`Optional<Character>`, `-1` index, or `null`), and Unicode: `char` is a UTF-16 code unit, so emojis and some
accented letters are surrogate pairs; iterate `codePoints()` if that matters. Test: empty string, all repeating (`"aabb"`),
single character, the unique character at the very end.

**Example:**

```java
static OptionalInt firstUniqueIndex(String s) {
    Map<Integer, Integer> count = new HashMap<>();
    s.codePoints().forEach(cp -> count.merge(cp, 1, Integer::sum));       // pass 1: frequencies

    int i = 0;
    for (int cp : s.codePoints().toArray()) {                              // pass 2: first with count == 1
        if (count.get(cp) == 1) return OptionalInt.of(i);
        i += Character.charCount(cp);                                      // index in chars, not code points
    }
    return OptionalInt.empty();
}
// "swiss" -> index 1 ('w');  "aabb" -> empty;  "" -> empty
```

**Why it's a trap:** using `s.indexOf(c) == s.lastIndexOf(c)` for each character is O(n²), and an `int[26]` fails as soon as
the input has capitals, digits or accents. Also, returning a magic `' '` or `0` for "not found" is ambiguous when the
string may contain it.

#### Q7. What are the two-pointer and sliding-window patterns? Solve "longest substring without repeating characters". {#two-pointer-sliding-window-patterns}
**Answer:** **Two pointers** move from both ends (sorted arrays, palindromes) or at different speeds (cycle detection).
A **sliding window** keeps a range `[left, right]` that satisfies a condition: extend `right`, and when the condition
breaks, move `left` until it holds again. Each index enters and leaves once, so it's O(n). For the longest substring
without repeats, keep the last index of each character and jump `left` past a repeat.

**Example:**

```java
int lengthOfLongestSubstring(String s) {
    Map<Character, Integer> last = new HashMap<>();
    int best = 0;
    for (int left = 0, right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        if (last.containsKey(c) && last.get(c) >= left) left = last.get(c) + 1;
        last.put(c, right);
        best = Math.max(best, right - left + 1);
    }
    return best;   // "abcabcbb" -> 3
}
```

#### Q8. How do you write a binary search without off-by-one bugs? {#write-binary-search-off-one}
**Answer:** Use one consistent template: a half-open or closed interval, a loop condition that matches it, and
`mid = lo + (hi - lo) / 2` to avoid overflow. The most reusable form searches for the **first index where a condition
becomes true** (lower bound), which also covers "search insert position", "first bad version" and binary search on
the answer (minimum capacity, minimum speed).

**Example:**

```java
// first index i in [0, n] with a[i] >= target (n if none)
int lowerBound(int[] a, int target) {
    int lo = 0, hi = a.length;               // half-open [lo, hi)
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] >= target) hi = mid; else lo = mid + 1;
    }
    return lo;
}
```

#### Q9. BFS vs DFS — when do you use each? Solve "number of islands". {#bfs-dfs-each-solve-number}
**Answer:** **BFS** (queue) explores level by level, so it finds the **shortest path in an unweighted graph** (minimum
moves, degrees of separation). **DFS** (recursion or explicit stack) goes deep first, suited to exploring connected
components, detecting cycles, topological sort and backtracking. Both are O(V + E). For a grid, each cell is a node
with up to four neighbours; mark cells as visited to avoid infinite loops. For deep inputs, prefer an explicit stack
or BFS in Java to avoid `StackOverflowError`.

**Example:**

```java
int numIslands(char[][] grid) {
    int count = 0;
    int[][] dirs = { {1,0}, {-1,0}, {0,1}, {0,-1} };
    for (int r = 0; r < grid.length; r++)
        for (int c = 0; c < grid[0].length; c++) {
            if (grid[r][c] != '1') continue;
            count++;
            Deque<int[]> queue = new ArrayDeque<>(List.of(new int[] { r, c }));
            grid[r][c] = '0';
            while (!queue.isEmpty()) {
                int[] cell = queue.poll();
                for (int[] d : dirs) {
                    int nr = cell[0] + d[0], nc = cell[1] + d[1];
                    if (nr >= 0 && nr < grid.length && nc >= 0 && nc < grid[0].length && grid[nr][nc] == '1') {
                        grid[nr][nc] = '0';
                        queue.offer(new int[] { nr, nc });
                    }
                }
            }
        }
    return count;
}
```

#### Q10. When is a heap the right tool? Solve "top K frequent elements". {#heap-right-tool-solve-top}
**Answer:** Use a heap when you repeatedly need the smallest or largest item of a changing set: top K, K-way merge,
scheduling, Dijkstra. For top K out of n, keep a **min-heap of size K**: push each candidate and pop when the size
exceeds K. That's O(n log K) time and O(K) heap space, better than sorting everything (O(n log n)) when K is small.

**Example:**

```java
List<Integer> topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int n : nums) freq.merge(n, 1, Integer::sum);

    PriorityQueue<Map.Entry<Integer, Integer>> heap =
        new PriorityQueue<>(Map.Entry.comparingByValue());          // min-heap by count
    for (var e : freq.entrySet()) {
        heap.offer(e);
        if (heap.size() > k) heap.poll();
    }
    return heap.stream().map(Map.Entry::getKey).toList();
}
```

## 🟡 Senior traps

### Questions

#### Q11. Which Java pitfalls cost candidates points in live coding? {#java-pitfalls-cost-candidates-points}
**Answer:** **Integer overflow** (`(lo + hi) / 2`, sums of large ints: use `long`); comparing boxed numbers with
`==` (`Integer` above 127, see [Java Q9](java-core-jvm.md#autoboxing-trap-integer)); a comparator written as `a - b`, which overflows (use
`Integer.compare`); string concatenation in a loop (O(n²); use `StringBuilder`); modifying a collection while iterating
over it with for-each; `Arrays.asList` returning a fixed-size list; recursion depth on large inputs; forgetting to
handle empty input; and `char` arithmetic (`c - 'a'` is fine, `c + 1` is an `int`).

**Example:**

```java
// ⛔ overflows for large values of opposite sign
list.sort((a, b) -> a - b);
// ✅
list.sort(Integer::compare);
```

**Why it's a trap:** the algorithm is right and the test case passes; the interviewer then asks "what if the values
are near `Integer.MAX_VALUE`?", and the bug is in the one-liner you didn't think about.

#### Q12. Group appointments by doctor and by date with streams. {#group-appointments-doctor-date-streams}
**Answer:** `Collectors.groupingBy` with a *downstream* collector does it in one pass. For two-level grouping, nest the
collectors: doctor → date → list. Pick the map type deliberately: `TreeMap` for sorted keys (dates in order), `LinkedHashMap`
to keep encounter order, and sort the lists inside (`Comparator.comparing(Appointment::start)`) because `groupingBy` keeps
input order only within each group. Use `mapping` to collect only IDs, `counting()` for totals and `summingInt` for durations;
use `toUnmodifiableList` for read-only results. Model the key explicitly (a small `record DoctorDay(String doctorId, LocalDate
day)`) when you need a single flat map. Time O(n log n) if sorting, O(n) without; memory proportional to the data. Time-zone
trap: derive the date from the instant *in the practitioner's time zone*, not the server's default, or late-evening
appointments land on the wrong day. Edge cases: empty input (empty map, not `null`), `null` fields, and cancelled appointments
(filter first). A parallel stream here needs `groupingByConcurrent`, and is rarely worth it.

**Example:**

```java
record Appointment(String id, String doctorId, Instant start, Duration length, boolean cancelled) {}

Map<String, Map<LocalDate, List<Appointment>>> byDoctorAndDay = appointments.stream()
    .filter(a -> !a.cancelled())
    .collect(Collectors.groupingBy(
        Appointment::doctorId,
        TreeMap::new,                                                    // doctors sorted
        Collectors.groupingBy(
            a -> a.start().atZone(ZoneId.of("Europe/Paris")).toLocalDate(),
            TreeMap::new,                                                // days sorted
            Collectors.collectingAndThen(Collectors.toList(), list -> {
                list.sort(Comparator.comparing(Appointment::start));     // order within the day
                return List.copyOf(list);
            }))));

// Variant: minutes booked per doctor
Map<String, Long> minutes = appointments.stream().filter(a -> !a.cancelled())
    .collect(groupingBy(Appointment::doctorId, summingLong(a -> a.length().toMinutes())));
```

**Why it's a trap:** forgetting the time zone, assuming `groupingBy` returns sorted keys (it returns a `HashMap`), and
mutating a list from inside the stream. Also see the stream pitfalls in [Java Q14](java-core-jvm.md#common-ways-stream-pipeline-goes).

#### Q13. Detect overlapping bookings. {#detect-overlapping-bookings}
**Answer:** Two time ranges overlap exactly when `a.start < b.end && b.start < a.end`. Treat ranges as **half-open**
`[start, end)` so back-to-back appointments (10:00–10:30 and 10:30–11:00) do *not* conflict; this one decision causes most
off-by-one bugs, so say it out loud. For one new booking against an existing list, check the condition against each
existing booking, O(n), or O(log n) if the bookings are kept in a `TreeMap<Instant, Booking>` keyed by start: look at
`floorEntry(start)` (previous booking must end by `start`) and `ceilingEntry(start)` (next must start at or after `end`). To
find *all* conflicts in a batch, **sort by start and sweep**: keep the latest end seen so far and report a conflict whenever the
next start is before it. O(n log n) time, O(1) extra space. Use `Instant` or `ZonedDateTime`, never `LocalDateTime` across
time zones or DST changes, and validate `start < end`. In production the check must be enforced by the database
(exclusion constraint, see [Persistence Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)), because an in-memory check races with other
requests.

**Example:**

```java
record Booking(String id, Instant start, Instant end) {
    boolean overlaps(Booking o) { return start.isBefore(o.end) && o.start.isBefore(end); }
}

static List<Booking[]> conflicts(List<Booking> bookings) {
    List<Booking> sorted = bookings.stream().sorted(Comparator.comparing(Booking::start)).toList();
    List<Booking[]> result = new ArrayList<>();
    Booking latest = null;                                   // booking with the furthest end so far
    for (Booking b : sorted) {
        if (latest != null && b.start().isBefore(latest.end())) result.add(new Booking[]{latest, b});
        if (latest == null || b.end().isAfter(latest.end())) latest = b;
    }
    return result;                                           // each booking is compared with the one reaching furthest
}
// A 10:00-11:00, B 10:30-10:45, C 10:50-11:30: reports (A,B) and (A,C); B inside A is not missed.
```

**Why it's a trap:** using `<=` instead of `<` flags back-to-back slots, a nested containment case (one booking inside a
long one) is missed by comparing only neighbours, and comparing `LocalDateTime`s ignores time zones. Test the three shapes:
partial overlap, containment and touching ends.

#### Q14. What is dynamic programming, and how do you spot a DP problem? {#dynamic-programming-spot-dp-problem}
**Answer:** DP applies when a problem has **overlapping subproblems** and **optimal substructure**: the best answer is
built from best answers to smaller versions, and the same smaller versions are needed again and again. Signals:
"number of ways", "minimum cost", "longest/shortest ... subsequence", choices at each step. Method: define the
**state** (what `dp[i]` means), the **transition** (how `dp[i]` comes from smaller states), and the **base cases**.
Start with recursion plus memoization (top-down), then convert to a table (bottom-up) and often reduce space to a few
variables.

**Example:**

```java
// Min coins to make amount; dp[a] = min coins for amount a
int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, Integer.MAX_VALUE);
    dp[0] = 0;
    for (int a = 1; a <= amount; a++)
        for (int c : coins)
            if (c <= a && dp[a - c] != Integer.MAX_VALUE)
                dp[a] = Math.min(dp[a], dp[a - c] + 1);
    return dp[amount] == Integer.MAX_VALUE ? -1 : dp[amount];
}
```

**Why it's a trap:** a greedy "take the biggest coin first" passes on `{1, 5, 10}` and fails on `{1, 3, 4}` for amount
6 (greedy gives 3 coins, the optimum is 2). Always test greedy ideas against a counter-example.

#### Q15. Implement a thread-safe counter. {#implement-thread-safe-counter}
**Answer:** `count++` is three steps (read, add, write), so two threads can both read 5 and both write 6: a lost update. Options,
from simplest to most scalable: (1) **`synchronized`** methods or a `ReentrantLock`: correct, but threads queue on every call;
(2) **`AtomicLong`/`AtomicInteger`**: `incrementAndGet()` uses a hardware compare-and-swap, lock-free and the right default
for a counter that is also read for its value; under very high contention the CAS loop retries a lot; (3) **`LongAdder`**:
spreads updates across internal cells and sums them on `sum()`, much faster under heavy write contention (metrics, request
counts), but `sum()` is not an atomic snapshot and it does not offer compare-and-set, so it is wrong for "increment *only if*
below a limit". (4) Not sharing at all: per-thread counters merged at the end. `volatile long` alone is **not** enough: it
guarantees visibility but not atomicity of `++` (see [Java Q23](java-core-jvm.md#real-synchronized-volatile)). For a bounded counter (a rate limit, "max 3
bookings"), use a CAS loop with `updateAndGet`/`compareAndSet` so the check and the increment are one atomic step. Test with
many threads and assert the exact total; a single-threaded test proves nothing.

**Example:**

```java
class Counter {
    private final AtomicLong value = new AtomicLong();
    long increment() { return value.incrementAndGet(); }
    long get()       { return value.get(); }
}

class BoundedCounter {                                    // check-and-increment must be one atomic step
    private final AtomicInteger value = new AtomicInteger();
    boolean tryIncrement(int max) {
        int cur;
        do { cur = value.get(); if (cur >= max) return false; }
        while (!value.compareAndSet(cur, cur + 1));
        return true;
    }
}

// Test: 100 threads x 10_000 increments must give exactly 1_000_000
ExecutorService pool = Executors.newFixedThreadPool(100);
Counter c = new Counter();
List<Future<?>> fs = IntStream.range(0, 100).mapToObj(i -> pool.submit(() -> { for (int j = 0; j < 10_000; j++) c.increment(); })).toList();
for (Future<?> f : fs) f.get();
assertEquals(1_000_000, c.get());
```

**Why it's a trap:** `volatile` and `ConcurrentHashMap<String, Integer>` with `map.put(k, map.get(k) + 1)` look thread-safe
and are not; use `merge(k, 1, Integer::sum)` or a `LongAdder` value. Also, an atomic counter protects one number, not an
invariant spanning two fields.

#### Q16. Implement retry logic with a maximum number of attempts. {#implement-retry-logic-maximum-number}
**Answer:** A retry helper takes an operation, a maximum number of attempts, a delay policy and a predicate for which failures
are retryable. Decisions to state: (1) **only retry transient errors** (timeouts, `503`, connection reset, deadlock victim),
never validation errors or `4xx`, and **only idempotent operations**, or ones protected by an idempotency key, otherwise a
retry after a lost response duplicates a payment or a booking (see [Full Stack Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need)); (2) **bound
it**: a max attempts (e.g. 3) and an overall deadline; (3) **back off exponentially with jitter** (100 ms, 200 ms, 400 ms,
randomised) so many clients do not retry in lock-step and hammer a recovering service (*retry storm*); (4) **rethrow the last
failure with earlier ones attached** (`addSuppressed`) so nothing is lost; (5) **restore the interrupt flag** if the sleep is
interrupted and stop; (6) retries multiply across layers (3 retries at 3 layers = 27 calls), so retry at one layer and combine with
a circuit breaker. In Spring, `@Retryable`/Spring Retry (or Resilience4j `Retry`) do this declaratively, but writing it by
hand is the live-coding question. Test with a fake that fails N times: assert exactly `max` attempts, no retry on a
non-retryable exception, and that delays grow (inject the sleeper so tests don't actually wait).

**Example:**

```java
static <T> T retry(int maxAttempts, Duration baseDelay, Predicate<Exception> retryable,
                   Callable<T> op, LongConsumer sleeper) throws Exception {
    if (maxAttempts < 1) throw new IllegalArgumentException("maxAttempts must be >= 1");
    Exception last = null;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return op.call();
        } catch (Exception e) {
            if (!retryable.test(e)) throw e;                           // permanent failure: don't retry
            if (last != null) e.addSuppressed(last);
            last = e;
            if (attempt == maxAttempts) break;
            long exp = baseDelay.toMillis() << (attempt - 1);          // 100, 200, 400 ...
            long jitter = ThreadLocalRandom.current().nextLong(exp / 2 + 1);
            try { sleeper.accept(exp / 2 + jitter); }                  // "equal jitter"
            catch (RuntimeException ie) { Thread.currentThread().interrupt(); throw e; }
        }
    }
    throw last;
}
// usage: retry(3, Duration.ofMillis(100), e -> e instanceof IOException, () -> client.call(), Thread::sleep-wrapper)
```

**Why it's a trap:** retrying non-idempotent calls, retrying forever, no jitter, and swallowing the original exception
are the four classic mistakes. Also remember a retry is not free: with a slow dependency it keeps threads and connections
busy longer, so pair it with timeouts and a circuit breaker (see [Spring Q35](spring-architecture.md#circuit-breaker-pattern-service-need)).

#### Q17. Implement an LRU cache with O(1) `get` and `put`. {#implement-lru-cache-o-1}
**Answer:** You need O(1) lookup (a hash map) and O(1) "move to most recent" and "evict the oldest" (a doubly linked
list). In Java, `LinkedHashMap` with `accessOrder = true` and an overridden `removeEldestEntry` provides exactly that
in a few lines. Interviewers often then ask you to build it by hand (map from key to node, plus a doubly linked list
with sentinel head and tail), so be ready for both. Thread safety and bounded-memory trade-offs are discussed in
[Java Q21](java-core-jvm.md#design-thread-safe-bounded-lru).

**Example:**

```java
class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;
    LruCache(int capacity) { super(16, 0.75f, true); this.capacity = capacity; }   // access order
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) { return size() > capacity; }
}
```

**Why it's a trap:** using a plain `LinkedList` plus `remove(Object)` to move a key looks right but is O(n) per access.

#### Q18. How do you test your code during the interview? {#test-code-during-interview}
**Answer:** Don't just say "looks right". Trace one normal example line by line, tracking the variables out loud. Then
run edge cases: empty input, a single element, all elements equal, the answer at the first or last position,
negative numbers, and the largest input for performance. If the environment can run code, write a tiny `main` or a
couple of JUnit-style assertions. When you find a bug, explain the cause before fixing it: the interviewer is looking
for that debugging reflex.

**Example:**

```java
assert lengthOfLongestSubstring("") == 0;
assert lengthOfLongestSubstring("bbbb") == 1;
assert lengthOfLongestSubstring("abba") == 2;      // catches "left moves backwards" bug
```

**Why it's a trap:** most failed exercises are not wrong algorithms but untested edge cases the candidate could have
found in one minute.

## 🔴 Expert / Open

### Questions

#### Q19. Design and code a rate limiter class for a single service instance. {#design-code-rate-limiter-class}
**Answer:** Clarify first: per user or global, limit and window, behaviour when limited, and whether it needs to be
thread-safe. A **token bucket** is the usual answer: each key has a bucket with capacity C refilled at R tokens per
second; a request takes a token or is rejected. Store per-key state in a `ConcurrentHashMap` and update it atomically
(`compute`, or synchronize on the bucket). Use a `Clock` or nanoTime supplier so tests can control time. Then discuss
the limits: memory for many keys (evict idle buckets), and distributed limiting, which needs Redis (see
[System Design Q15](system-design.md#compare-rate-limiting-algorithms-one)).

**Example:**

```java
class TokenBucketLimiter {
    private record Bucket(double tokens, long lastNanos) {}
    private final ConcurrentHashMap<String, Bucket> buckets = new ConcurrentHashMap<>();
    private final double capacity, refillPerNano;
    private final LongSupplier nanoTime;

    TokenBucketLimiter(double capacity, double refillPerSecond, LongSupplier nanoTime) {
        this.capacity = capacity; this.refillPerNano = refillPerSecond / 1e9; this.nanoTime = nanoTime;
    }

    boolean tryAcquire(String key) {
        boolean[] allowed = new boolean[1];
        buckets.compute(key, (k, b) -> {
            long now = nanoTime.getAsLong();
            double tokens = b == null ? capacity : Math.min(capacity, b.tokens() + (now - b.lastNanos()) * refillPerNano);
            allowed[0] = tokens >= 1;
            return new Bucket(allowed[0] ? tokens - 1 : tokens, now);
        });
        return allowed[0];
    }
}
```

#### Q20. Merge overlapping intervals, and how would the solution change for a stream of intervals? {#merge-overlapping-intervals-solution-change}
**Answer:** For a list, **sort by start** (O(n log n)), then scan: if the next interval starts before or at the current
end, extend the end; otherwise close the current interval and start a new one. For a **stream** (intervals arriving
one by one, such as calendar bookings), keep the merged intervals in a `TreeMap<start, end>` and on each insert look
at `floorEntry` and the following entries to merge in O(log n + merged). This is a good example of the follow-up
interviewers like: "now the data doesn't fit in one call".

**Example:**

```java
int[][] merge(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(i -> i[0]));
    List<int[]> out = new ArrayList<>();
    for (int[] cur : intervals) {
        if (!out.isEmpty() && cur[0] <= out.getLast()[1])
            out.getLast()[1] = Math.max(out.getLast()[1], cur[1]);
        else out.add(cur);
    }
    return out.toArray(int[][]::new);
}
```

#### Q21. Given a practitioner's working hours and their existing appointments, find the available slots. {#given-practitioner-working-hours-existing}
**Answer:** This is "interval subtraction": start from the free intervals, remove the busy ones, then cut what is left into
bookable slots. Algorithm: (1) validate and **normalise** the busy list: drop cancelled ones, sort by start, and **merge
overlapping or touching intervals** (see [Coding Q20](coding.md#merge-overlapping-intervals-solution-change)) so the sweep is simple; (2) keep a cursor at the start of
the working day; for each busy interval clamped to the working window, if `busy.start > cursor` then `[cursor, busy.start)` is a free
gap; move the cursor to `max(cursor, busy.end)`; after the loop add the trailing gap `[cursor, dayEnd)`; (3) for each gap,
emit slots of the requested length (e.g. 20 min) every `step` minutes, as long as `slotEnd <= gap.end`, optionally respecting
buffers and a minimum notice. Time O(n log n) for the sort plus O(n + s) for the sweep (s = slots produced). Decisions to
state: half-open intervals so back-to-back appointments are fine, **time zones and DST** (compute in the practitioner's
zone: a spring-forward day has a missing hour, a fall-back day has a repeated one, so use `ZonedDateTime`), lunch breaks as
extra busy intervals, and behaviour when appointments fall partly outside working hours. Also say how this scales: precompute
per day and cache briefly, but re-validate at booking time (see [Persistence Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)).

**Example:**

```java
record Interval(Instant start, Instant end) {}

static List<Interval> freeSlots(Interval workDay, List<Interval> busy, Duration slot, Duration step) {
    List<Interval> merged = merge(busy.stream()
        .filter(b -> b.end().isAfter(workDay.start()) && b.start().isBefore(workDay.end()))
        .sorted(Comparator.comparing(Interval::start)).toList());

    List<Interval> gaps = new ArrayList<>();
    Instant cursor = workDay.start();
    for (Interval b : merged) {
        if (b.start().isAfter(cursor)) gaps.add(new Interval(cursor, min(b.start(), workDay.end())));
        cursor = max(cursor, b.end());
    }
    if (cursor.isBefore(workDay.end())) gaps.add(new Interval(cursor, workDay.end()));

    List<Interval> slots = new ArrayList<>();
    for (Interval g : gaps)
        for (Instant s = g.start(); !s.plus(slot).isAfter(g.end()); s = s.plus(step))
            slots.add(new Interval(s, s.plus(slot)));
    return slots;
}
// Work 09:00-12:00, busy 09:00-10:00 and 10:00-10:30 (merged to 09:00-10:30), 20-min slots every 20 min:
// -> 10:30-10:50, 10:50-11:10, 11:10-11:30, 11:30-11:50
```

**Why it's a trap:** forgetting to merge busy intervals (the sweep then moves the cursor backwards), ignoring time zones,
off-by-one at the day boundaries, and returning slots that overlap the next appointment because the end check was `<` instead
of `<=`. Test: no appointments, fully booked, appointment starting before the day or ending after it, back-to-back appointments.

#### Q22. Process a very large stream of events (more than fits in memory) and compute statistics or the top K. {#process-very-large-stream-events}
**Answer:** The constraint is memory, so the answer is **never load it all**: read incrementally and keep only aggregates.
State the questions first: what is computed (counts per key, distinct count, top K, percentiles, deduplication)? Is order
guaranteed? Is it a one-off file or an unbounded live stream? Techniques: (1) **streaming read**: `Files.lines(path)` or a
`BufferedReader` (lazy, close it with try-with-resources), a Kafka consumer, or a JDBC `ResultSet` with a fetch size / server-side cursor,
never `readAllLines()`; (2) **running aggregates** in O(1) memory per item: count, sum, min, max, mean/variance
(Welford); (3) **bounded structures**: top K with a min-heap of size K (O(n log K) time, O(K) memory, see
[Coding Q10](coding.md#heap-right-tool-solve-top)); (4) **cardinality-bound maps**: counting per user is fine if the number of users fits in memory; if
not, **partition by hash** (external grouping into N files, process each) or use approximate sketches (HyperLogLog for distinct
counts, Count-Min Sketch for heavy hitters, t-digest for percentiles) trading accuracy for fixed memory; (5) **dedup with an
unbounded key space** needs a Bloom filter (false positives, no false negatives) or a time window; (6) **parallelise by
partition**, not by sharing one map (per-partition aggregates merged at the end); (7) **backpressure** for live streams
(bounded queues) and **checkpointing** so a crash does not restart from zero; (8) **external sort/merge** when you truly
need a global order. Say the complexity in terms of n (events) and k (distinct keys). Test with a generated large file and a
small `-Xmx` to prove memory stays flat.

**Example:**

```java
// Top 3 customers by number of events from a huge CSV: O(n) time, O(distinct customers + K) memory.
static List<Map.Entry<String, Long>> topK(Path file, int k) throws IOException {
    Map<String, Long> counts = new HashMap<>();
    try (Stream<String> lines = Files.lines(file)) {                 // lazy: one line in memory at a time
        lines.skip(1)
             .map(l -> l.split(",", -1)[0])                          // customer id
             .forEach(id -> counts.merge(id, 1L, Long::sum));
    }
    PriorityQueue<Map.Entry<String, Long>> heap = new PriorityQueue<>(Map.Entry.comparingByValue());
    for (var e : counts.entrySet()) {
        heap.offer(e);
        if (heap.size() > k) heap.poll();                            // evict the smallest
    }
    List<Map.Entry<String, Long>> result = new ArrayList<>(heap);
    result.sort(Map.Entry.<String, Long>comparingByValue().reversed());
    return result;
}
```

**Why it's a trap:** `Files.readAllLines`, collecting to a list "just to sort it", or `parallel()` over a shared `HashMap`
all fail at scale (OOM or wrong counts). Also, a stream from `Files.lines` must be closed, or the file handle leaks.

#### Q23. How do you approach a practical "refactor this code" or "review this pull request" exercise? {#approach-practical-refactor-code-review}
**Answer:** Senior loops increasingly replace puzzles with realistic code. Read the whole thing first and state what
it does. Then rank issues by impact: **correctness** (bugs, race conditions, missing transaction, wrong equality),
**security** (injection, missing authorization, secrets), **reliability** (resource leaks, unbounded queries, no
timeouts), then **design and readability** (long methods, mixed concerns, naming). Propose small, safe steps: add a
test that pins the current behaviour, then refactor. For a review, write comments as you would to a colleague:
the issue, why it matters, and a concrete suggestion, separating "must fix" from "nit".

#### Q24. Compute a practitioner's availabilities for the next 7 days from recurring weekly openings and booked appointments. {#compute-practitioner-availabilities-next-7}
**Answer:** This is the classic booking-platform kata, often given as a take-home or pair-programming exercise. The input is a list of events: **openings** (one-off, or recurring every week from their start date) and **appointments**. The output is, for each of the 7 days from a start date, the list of free 30-minute slots. Algorithm per day: (1) keep the openings that **occur on that day**: a one-off opening on that date, or a weekly opening with the same weekday whose first occurrence is not after the day; (2) expand each opening into slots `[t, t + 30 min)` while `t + 30 min <= end`; (3) remove every slot that **overlaps** an appointment that day (`slot.start < appt.end && slot.end > appt.start`, half-open intervals); (4) deduplicate and sort. Complexity O(D × (O + S × A)) for D days, O openings, S slots, A appointments. That is fine for one calendar. Mention the faster version (sort appointments and sweep, see [Coding Q21](coding.md#given-practitioner-working-hours-existing)) only if asked. In pair programming, start with the test cases, write the simplest version, then refactor: they watch your method more than the final code.

**Example:**

```java
enum Kind { OPENING, APPOINTMENT }
record Event(Kind kind, LocalDateTime start, LocalDateTime end, boolean weeklyRecurring) {}
record DayAvailability(LocalDate date, List<LocalTime> slots) {}

static boolean occursOn(Event e, LocalDate day) {
    return e.start().toLocalDate().equals(day) ||
        (e.weeklyRecurring() && e.start().getDayOfWeek() == day.getDayOfWeek() && !e.start().toLocalDate().isAfter(day));
}

static List<DayAvailability> availabilities(LocalDate from, List<Event> events, int days, Duration slot) {
    List<DayAvailability> result = new ArrayList<>();
    for (int offset = 0; offset < days; offset++) {
        LocalDate day = from.plusDays(offset);
        List<Event> booked = events.stream()
            .filter(e -> e.kind() == Kind.APPOINTMENT && e.start().toLocalDate().equals(day)).toList();
        TreeSet<LocalDateTime> free = new TreeSet<>();                       // dedup + sort
        for (Event o : events) {
            if (o.kind() != Kind.OPENING || !occursOn(o, day)) continue;
            LocalDateTime end = day.atTime(o.end().toLocalTime());
            for (LocalDateTime s = day.atTime(o.start().toLocalTime()); !s.plus(slot).isAfter(end); s = s.plus(slot)) {
                LocalDateTime start = s, stop = s.plus(slot);               // LocalDateTime: no wrap at midnight
                if (booked.stream().noneMatch(b -> start.isBefore(b.end()) && stop.isAfter(b.start()))) free.add(start);
            }
        }
        result.add(new DayAvailability(day, free.stream().map(LocalDateTime::toLocalTime).toList()));
    }
    return result;
}

// Weekly opening every Monday 09:00-11:00 since 2026-10-05; appointment Monday 2026-10-19 09:30-10:00.
List<Event> events = List.of(
    new Event(Kind.OPENING, LocalDateTime.parse("2026-10-05T09:00"), LocalDateTime.parse("2026-10-05T11:00"), true),
    new Event(Kind.APPOINTMENT, LocalDateTime.parse("2026-10-19T09:30"), LocalDateTime.parse("2026-10-19T10:00"), false));
assert availabilities(LocalDate.parse("2026-10-19"), events, 7, Duration.ofMinutes(30)).getFirst().slots()
    .equals(List.of(LocalTime.of(9, 0), LocalTime.of(10, 0), LocalTime.of(10, 30)));
```

**Why it's a trap:** the usual bugs are applying a recurring opening to dates **before** it started, `<` instead of `<=` so the last slot of the day disappears, ignoring appointments that only partially overlap a slot, and using `LocalTime` arithmetic, which wraps at midnight and makes the loop never end. Say which tests you would write: empty week, opening with no appointment, appointment covering several slots, appointment at the exact end of an opening, recurring opening that starts mid-week, and a DST change (in production, compute in the practitioner's `ZoneId`).

## 🎯 Real-world scenarios

### S1. You are stuck halfway through the problem, and the interviewer is silent {#stuck-halfway-problem-interviewer-silent}
- **Symptoms:** Your approach fails on an example, ten minutes are left, and you don't see the fix.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Silence is the worst signal for the interviewer; they can't help or give credit for reasoning they
  can't hear. The usual cause is a wrong assumption about the input or a missing invariant.
- **Example:**

  ```text
  "My window approach breaks on 'abba' because left moves backwards when I see the second 'a'.
   The invariant should be: left only increases. So left = max(left, last[c] + 1)."
  ```

- **Resolution:** Say where you are, go back to the failing example and trace it out loud, and state the invariant you
  expected. If still stuck, offer the brute-force version working first, then optimize. Accept hints gracefully:
  using a hint well is a positive signal.
- **Prevention:** Practise out loud with a timer, always state invariants for windows and pointers, and keep a
  brute-force fallback ready.

</details>

### S2. Your solution passes the examples, but the interviewer says it's too slow for the real input size {#solution-passes-examples-but-interviewer}
- **Symptoms:** The code is correct on small inputs; the interviewer mentions n = 10⁶.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Compute the current complexity explicitly and find the repeated work: a nested loop that searches,
  a `list.contains` or `list.remove(0)` inside a loop, string concatenation, or recomputation of the same
  subproblem.
- **Example:**

  ```text
  for each element: if (list.contains(x))   -> O(n) inside O(n) = O(n²) = 1e12 at n = 1e6
  replace with HashSet                      -> O(n)
  ```

- **Resolution:** Name the bottleneck, pick the structure that makes it O(1) or O(log n) (hash set, heap, sorted order
  plus binary search, prefix sums, memoization), and re-state the new complexity.
- **Prevention:** Ask for the input size at the start and choose the target complexity from it before coding.

</details>

### S3. A take-home assignment: what does a senior submission look like? {#take-home-assignment-senior-submission}
- **Symptoms:** You receive a 4-hour take-home ("build a small REST API with a React page") and want it to stand out
  without over-engineering.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Reviewers check that it runs in one command, that the core logic is correct and tested, and how you
  make and document trade-offs. Extra features rarely score; a broken setup always loses.
- **Example:**

  ```text
  README: how to run (docker compose up), decisions & trade-offs, what I'd do next, time spent
  tests:  domain unit tests + one API integration test with Testcontainers + one RTL test
  git:    small commits with clear messages
  ```

- **Resolution:** Do the required scope well: clean layering, validation and error handling, meaningful tests, a
  README with decisions and known limits. Mention but don't build what you'd add for production (auth, pagination,
  observability).
- **Prevention:** Time-box, clarify ambiguous requirements by email early, and run the project from a fresh clone
  before submitting.

</details>

### S4. The interviewer changes the requirement after you finished the first version {#interviewer-changes-requirement-after-finished}
- **Symptoms:** You have 10 minutes left and your solution assumes the original constraints.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A changed requirement is a test of how you adapt, not a sign you failed. Check which assumption (sorted input, positive values, in-memory) the new constraint breaks, and whether only one function depends on it.
- **Resolution:** Say the impact out loud, restate the new requirement, adapt the smallest part (e.g. swap a sort for a heap, or process in a stream), and re-run your examples. If time is short, describe the approach and its complexity rather than half-coding it.
- **Prevention:** Isolate assumptions in small functions from the start and state them when you clarify; changes then touch one place.

</details>

### S5. Your solution works, then the interviewer says: "Now the input is a 200 GB log file" {#input-no-longer-fits-memory}
- **Symptoms:** Your `HashMap<String, Integer>` word/IP counter passes the examples; the follow-up makes it impossible to load the file or hold every key in memory.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The interviewer is testing whether you can change the model, not the code: streaming vs loading, bounded memory, and approximate vs exact answers. Ask what the output must be (exact top-10? approximate is fine?) and what hardware is available.
- **Example:**

  ```java
  // stream line by line, never load the file
  try (var lines = Files.lines(path)) {
      lines.map(l -> l.split(" ")[0]).forEach(ip -> counts.merge(ip, 1, Integer::sum));
  }
  // too many distinct keys? hash-partition into N files by ip.hashCode() % N,
  // count each partition in memory, keep a size-k min-heap across partitions
  ```

- **Resolution:** Walk the ladder out loud: stream the input (`Files.lines`); if distinct keys still don't fit, partition by hash to disk and process each partition; for top-k keep a bounded min-heap; if approximate is acceptable, mention Count-Min Sketch / HyperLogLog; at larger scale, it's a MapReduce/Spark job.
- **Prevention:** For every exercise, prepare the three standard follow-ups: bigger input (streaming/partitioning), concurrent access (thread safety), and distributed (sharding, merge step).

</details>

## 🗣️ Commonly asked questions

Questions that come up often in interviews on this topic (a typical set, not tied to one specific interview). Each has a short model answer: expand it with the sections above and say it aloud.

#### R1. Reverse a singly linked list. {#reverse-singly-linked-list}
**Answer:** Iterate with three pointers: `prev = null`, `cur = head`; in the loop save `next = cur.next`, set `cur.next = prev`, advance `prev = cur`, `cur = next`; return `prev`. O(n) time, O(1) space. The recursive version is O(n) stack, so mention the depth risk.

#### R2. Are the brackets in a string balanced (`()[]{}`)? {#brackets-string-balanced}
**Answer:** Use a `Deque<Character>` as a stack: push openers; on a closer, the stack must be non-empty and its top must match, else `false`. At the end the stack must be empty. O(n). Edge cases: empty string, only closers, odd length.

#### R3. Is a string a palindrome, ignoring case and non-alphanumeric characters? {#string-palindrome-ignoring-case-non}
**Answer:** Two pointers `i`, `j` from both ends; skip characters where `!Character.isLetterOrDigit`, compare lower-cased, move inward. O(n) time, O(1) space; do not build a cleaned copy unless asked.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q1. How do you approach a live-coding exercise?
2. Q21. Given a practitioner's working hours and their existing appointments, find the available slots.
3. Q4. When do you use a hash map to turn O(n²) into O(n)? Solve "two sum".
4. Q7. What are the two-pointer and sliding-window patterns? Solve "longest substring without repeating characters".
5. Q9. BFS vs DFS — when do you use each? Solve "number of islands".
6. Q11. Which Java pitfalls cost candidates points in live coding?
7. Q14. What is dynamic programming, and how do you spot a DP problem?
8. Q17. Implement an LRU cache with O(1) `get` and `put`.
9. Q19. Design and code a rate limiter class for a single service instance.
10. S2. Your solution passes the examples, but the interviewer says it's too slow for the real input size

## 📌 Cheat-sheet

### Process

> **Start here:** clarify → examples → brute force → plan → code → test → complexity, all out loud.

- **Clarify** — size, empty/null, duplicates, negatives, sorted? *Ask n first, it sets the target complexity.*
- **Test** — trace one example, then empty, single, all equal, extremes.
- **Stuck** — say it, trace the failing case, state the invariant, fall back to brute force.

### Patterns

> **Start here:** match the problem shape to a pattern before writing code.

- **Lookup/pairs/counts** — `HashMap`/`HashSet`, O(n).
- **Contiguous range** — sliding window; **sorted pairs** — two pointers.
- **Sorted or monotonic answer** — binary search (lower-bound template).
- **Shortest path, unweighted** — BFS; **components, cycles, backtracking** — DFS.
- **Top K, merge K, scheduling** — heap (`PriorityQueue`).
- **Ways/min cost/subsequence** — DP: state, transition, base case.
- **Intervals** — sort by start, then merge; `TreeMap` for streams.

### Java

> **Start here:** use the right collection and avoid the classic overflows.

- **Collections** — `ArrayDeque` (stack/queue), `PriorityQueue`, `TreeMap` (floor/ceiling), `int[]` for counts.
- **Idioms** — `merge`, `getOrDefault`, `computeIfAbsent`, `Integer.compare`, `StringBuilder`.
- **Traps** — `int` overflow, `Integer ==`, `a - b` comparators, recursion depth, `Arrays.asList` is fixed-size.
- **Free slots** — sort bookings by start, sweep from the start of working hours and emit each gap `>=` slot length; clamp to working hours. *O(n log n); ask about time zones, overlaps and adjacency.*
