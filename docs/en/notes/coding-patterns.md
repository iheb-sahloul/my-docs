# Coding Patterns & Katas

A reference for live-coding rounds and kata sessions: how to **recognise** a pattern from the problem statement, a
**template** to adapt, and **worked examples** in Java 21. The interview Q&A version (method, Big-O, pitfalls,
scenarios) is in [Live Coding](../interviews/coding.md).

## Method

### The loop, in 60 seconds

1. **Clarify**: input size, empty/null, duplicates, negatives, sorted?, expected output for one example.
2. **Examples**: two or three by hand, one of them an edge case.
3. **Brute force**: say it with its complexity. It is your fallback if you get stuck.
4. **Pattern**: match the problem shape to a pattern below, state the better complexity.
5. **Code**: clear names, small helpers, talk while typing.
6. **Test**: trace one example line by line, then empty, single element, all equal, extremes.
7. **Complexity**: time and space, then what you would improve with more time.

The full version is [Live Coding Q1](../interviews/coding.md#approach-live-coding-exercise).

### Input size → target complexity

Ask for **n** first: it tells you which pattern the interviewer expects.

| n | Target | Typical patterns |
|---|---|---|
| ≤ 10–12 | O(n!) / O(2ⁿ·n) | Backtracking over permutations or subsets |
| ≤ 20–25 | O(2ⁿ) | Subsets, bitmask DP |
| ≤ 500 | O(n³) | Triple loop, interval DP |
| ≤ 5 000 | O(n²) | 2D DP, all pairs |
| ≤ 10⁶ | O(n log n) / O(n) | Sort + scan, heap, hashing, two pointers, sliding window |
| ≥ 10⁹ (value range) | O(log n) | Binary search, math |

### Pattern picker

| The problem says… | Try |
|---|---|
| "find a pair / count occurrences / seen before / duplicates" | [Hashing](#hashing) |
| "sorted array", "pair with sum", "in place", "palindrome" | [Two pointers](#two-pointers) |
| "contiguous subarray / substring", "longest / shortest / at most K" | [Sliding window](#sliding-window) |
| "subarray sum equals K" (with negatives) | [Prefix sums + hashing](#hashing) |
| "linked list cycle", "middle of list" | [Fast & slow pointers](#fast-slow-pointers) |
| "sorted", "minimum X such that…", "maximum X such that…" | [Binary search](#binary-search) |
| "matching brackets", "next greater / smaller", "undo" | [Stack / monotonic stack](#stack-monotonic-stack) |
| "intervals", "meetings", "bookings", "overlap" | [Intervals](#intervals) |
| "top K", "K closest", "K-th largest", "merge K sorted" | [Heap](#heap-top-k) |
| "grid", "islands", "shortest path (unweighted)", "dependencies" | [BFS / DFS / topological sort](#bfs-dfs-graphs-grids) |
| "all combinations / permutations / subsets", "generate every…" | [Backtracking](#backtracking) |
| "number of ways", "min / max cost", "longest subsequence" | [Dynamic programming](#dynamic-programming) |
| "minimum number of steps / intervals", local choice looks safe | [Greedy](#greedy) |
| "reverse / merge / reorder a list" | [Linked lists](#linked-lists) |
| "tree", "depth", "path", "BST", "level by level" | [Trees](#trees) |

## Patterns

### Hashing {#hashing}

**Recognise it when** the brute force is "for each element, scan the rest for a partner", or you need counts,
deduplication or grouping.

**Template:**

```java
Map<Integer, Integer> seen = new HashMap<>();      // what you'll need to look up -> what you need back
for (int i = 0; i < a.length; i++) {
    Integer hit = seen.get(complementOf(a[i]));    // 1. look up first
    if (hit != null) { /* found */ }
    seen.put(a[i], i);                              // 2. then record (avoids pairing an element with itself)
}
```

**Worked example: group anagrams.** `["eat","tea","tan","ate","nat","bat"]` → `[[eat,tea,ate],[tan,nat],[bat]]`.

```java
List<List<String>> groupAnagrams(String[] words) {
    Map<String, List<String>> groups = new HashMap<>();
    for (String w : words) {
        char[] k = w.toCharArray();
        Arrays.sort(k);                                         // canonical key
        groups.computeIfAbsent(new String(k), x -> new ArrayList<>()).add(w);
    }
    return new ArrayList<>(groups.values());
}
// O(n · m log m) time, O(n · m) space (m = word length)
```

**Worked example: subarray sum equals K (prefix sums).** Count contiguous subarrays summing to `k`; values may be
negative, so a sliding window does not work. `sum(i..j) = prefix[j] - prefix[i-1]`, so for each prefix count how many
earlier prefixes equal `prefix - k`.

```java
int subarraySum(int[] nums, int k) {
    Map<Integer, Integer> count = new HashMap<>();
    count.put(0, 1);                                  // empty prefix: subarrays starting at index 0
    int prefix = 0, result = 0;
    for (int x : nums) {
        prefix += x;
        result += count.getOrDefault(prefix - k, 0);
        count.merge(prefix, 1, Integer::sum);
    }
    return result;
}
// [1, 2, 3], k = 3 -> 2 ([1,2] and [3]). O(n) time, O(n) space
```

**Pitfalls:** forgetting the `count.put(0, 1)` seed; recording before looking up (pairs an element with itself);
mutable keys (a `List` key changed after insertion is lost); `int` prefix overflow (use `long` for big sums).

**Practice:** two sum, contains duplicate, longest consecutive sequence, valid anagram, first unique character.

### Two pointers {#two-pointers}

**Recognise it when** the input is **sorted** (or can be sorted), you look for a pair/triplet, compare both ends, or
must work **in place**.

**Template (opposite ends):**

```java
int lo = 0, hi = a.length - 1;
while (lo < hi) {
    if (good(a[lo], a[hi])) { /* record */ lo++; hi--; }
    else if (needBigger(a[lo], a[hi])) lo++;
    else hi--;
}
```

**Worked example: pair with target sum in a sorted array.**

```java
int[] pairSum(int[] sorted, int target) {
    int lo = 0, hi = sorted.length - 1;
    while (lo < hi) {
        int sum = sorted[lo] + sorted[hi];
        if (sum == target) return new int[] { lo, hi };
        if (sum < target) lo++; else hi--;
    }
    return new int[0];
}
// O(n) time, O(1) space; every step discards one candidate that can't be in any answer
```

**Worked example: remove duplicates in place (same-direction pointers).** Return the new length; `slow` marks the end
of the deduplicated prefix.

```java
int removeDuplicates(int[] sorted) {
    if (sorted.length == 0) return 0;
    int slow = 0;
    for (int fast = 1; fast < sorted.length; fast++)
        if (sorted[fast] != sorted[slow]) sorted[++slow] = sorted[fast];
    return slow + 1;
}
// [1,1,2,3,3] -> 3, array starts with [1,2,3]. O(n) time, O(1) space
```

**Worked example: container with most water.** Move the shorter wall: the area is capped by it, so keeping it can
never help.

```java
int maxArea(int[] h) {
    int lo = 0, hi = h.length - 1, best = 0;
    while (lo < hi) {
        best = Math.max(best, Math.min(h[lo], h[hi]) * (hi - lo));
        if (h[lo] < h[hi]) lo++; else hi--;
    }
    return best;
}
```

**Pitfalls:** using it on unsorted input without sorting first (and losing the original indices); `lo <= hi` vs
`lo < hi`; skipping duplicates in 3-sum (`while (lo < hi && a[lo] == a[lo + 1]) lo++`).

**Practice:** valid palindrome, 3-sum, sort colors (Dutch flag), squares of a sorted array, trapping rain water.

### Sliding window {#sliding-window}

**Recognise it when** the answer is a **contiguous** subarray or substring, with words like "longest", "shortest",
"at most K distinct", "of size K", and the condition is **monotonic** (growing the window only makes it "more" invalid).

**Template (variable size):**

```java
int left = 0, best = 0;
for (int right = 0; right < n; right++) {
    add(a[right]);                       // 1. expand
    while (!valid()) remove(a[left++]);  // 2. shrink until valid again
    best = Math.max(best, right - left + 1);  // 3. record
}
```

**Worked example: fixed size, max sum of K consecutive elements.**

```java
long maxSumOfK(int[] a, int k) {
    long window = 0;
    for (int i = 0; i < k; i++) window += a[i];
    long best = window;
    for (int i = k; i < a.length; i++) {
        window += a[i] - a[i - k];      // slide: add the new one, drop the oldest
        best = Math.max(best, window);
    }
    return best;
}
// O(n) instead of O(n·k)
```

**Worked example: longest substring with at most K distinct characters.**

```java
int longestKDistinct(String s, int k) {
    Map<Character, Integer> count = new HashMap<>();
    int left = 0, best = 0;
    for (int right = 0; right < s.length(); right++) {
        count.merge(s.charAt(right), 1, Integer::sum);
        while (count.size() > k) {
            char c = s.charAt(left++);
            if (count.merge(c, -1, Integer::sum) == 0) count.remove(c);
        }
        best = Math.max(best, right - left + 1);
    }
    return best;
}
// "eceba", k = 2 -> 3 ("ece"). O(n) time: each char enters and leaves the window once
```

**Worked example: minimum window containing all characters of `t`.** Shortest-window variant: shrink **while valid**
and record inside the loop.

```java
String minWindow(String s, String t) {
    int[] need = new int[128];
    for (char c : t.toCharArray()) need[c]++;
    int missing = t.length(), left = 0, bestStart = 0, bestLen = Integer.MAX_VALUE;
    for (int right = 0; right < s.length(); right++) {
        if (need[s.charAt(right)]-- > 0) missing--;
        while (missing == 0) {
            if (right - left + 1 < bestLen) { bestLen = right - left + 1; bestStart = left; }
            if (++need[s.charAt(left++)] > 0) missing++;
        }
    }
    return bestLen == Integer.MAX_VALUE ? "" : s.substring(bestStart, bestStart + bestLen);
}
// "ADOBECODEBANC", "ABC" -> "BANC". O(|s| + |t|)
```

**Pitfalls:** negative numbers break "sum ≤ K" windows (shrinking no longer lowers the sum: use prefix sums);
recording the best outside vs inside the shrink loop (longest = after, shortest = inside).

**Practice:** longest substring without repeating characters, longest repeating character replacement, permutation
in string, max consecutive ones III, fruit into baskets.

### Fast & slow pointers {#fast-slow-pointers}

**Recognise it when** you work on a linked list (or a function `next = f(x)`) and need a cycle, the middle, or the
K-th from the end, in O(1) space.

```java
// ListNode is defined in the Linked lists section below
boolean hasCycle(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) return true;   // fast gains one step per turn, so it must meet slow inside the cycle
    }
    return false;
}

ListNode middle(ListNode head) {        // 1-2-3-4-5 -> 3 ; 1-2-3-4 -> 3 (second middle)
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }
    return slow;
}
```

**Worked example: happy number** (no list, but the same cycle trick on `n -> sum of squared digits`).

```java
boolean isHappy(int n) {
    int slow = n, fast = next(n);
    while (fast != 1 && slow != fast) { slow = next(slow); fast = next(next(fast)); }
    return fast == 1;
}
int next(int n) { int s = 0; for (; n > 0; n /= 10) s += (n % 10) * (n % 10); return s; }
```

**Pitfalls:** checking `fast.next.next` without checking `fast.next`; a `HashSet<Node>` works too but costs O(n) space,
say so.

**Practice:** linked list cycle II (cycle start), remove N-th node from end, palindrome linked list, find the
duplicate number.

### Binary search {#binary-search}

**Recognise it when** the input is sorted, **or** the answer is a number in a range and a predicate `ok(x)` is
monotonic (false…false true…true): "minimum capacity", "smallest speed", "earliest day".

**Template (lower bound: first index where `ok` is true).** One template, no off-by-one guessing:

```java
int lowerBound(int lo, int hi) {         // search in [lo, hi); returns hi if never true
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;    // no (lo + hi) / 2 overflow
        if (ok(mid)) hi = mid;           // mid may be the answer: keep it
        else lo = mid + 1;               // mid is not: drop it
    }
    return lo;
}
```

**Worked example: first position of `target` in a sorted array with duplicates.**

```java
int firstIndexOf(int[] a, int target) {
    int lo = 0, hi = a.length;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] >= target) hi = mid; else lo = mid + 1;
    }
    return lo < a.length && a[lo] == target ? lo : -1;
}
```

**Worked example: binary search on the answer, ship packages within D days.** The capacity is between the heaviest
package and the total weight; "can ship in D days with capacity c" is monotonic in `c`.

```java
int shipWithinDays(int[] weights, int days) {
    int lo = Arrays.stream(weights).max().orElseThrow();
    int hi = Arrays.stream(weights).sum() + 1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (daysNeeded(weights, mid) <= days) hi = mid; else lo = mid + 1;
    }
    return lo;
}

int daysNeeded(int[] weights, int capacity) {
    int days = 1, load = 0;
    for (int w : weights) {
        if (load + w > capacity) { days++; load = 0; }
        load += w;
    }
    return days;
}
// [1..10], 5 days -> 15. O(n log(sum)) time, O(1) space
```

**Pitfalls:** `(lo + hi) / 2` overflow; infinite loop with `lo = mid` (only safe with an upper-mid); a predicate that
is not monotonic; forgetting to check the returned index is in range and actually matches.

**Practice:** search insert position, search in rotated sorted array, find minimum in rotated array, Koko eating
bananas, median of two sorted arrays (hard).

### Stack / monotonic stack {#stack-monotonic-stack}

**Recognise it when** the latest opened thing must be closed first (brackets, tags, undo), or you need the **next / previous
greater or smaller** element for each position.

**Worked example: balanced brackets.**

```java
boolean isBalanced(String s) {
    Deque<Character> stack = new ArrayDeque<>();
    Map<Character, Character> open = Map.of(')', '(', ']', '[', '}', '{');
    for (char c : s.toCharArray()) {
        if (open.containsValue(c)) stack.push(c);
        else if (open.containsKey(c) && (stack.isEmpty() || stack.pop() != open.get(c))) return false;
    }
    return stack.isEmpty();
}
// "([]{})" -> true, "(]" -> false, "((" -> false
```

**Template (monotonic stack: next greater element).** Keep **indices** of elements still waiting for their answer;
the stack stays decreasing.

```java
int[] nextGreater(int[] a) {
    int[] res = new int[a.length];
    Arrays.fill(res, -1);
    Deque<Integer> stack = new ArrayDeque<>();          // indices, values decreasing from bottom to top
    for (int i = 0; i < a.length; i++) {
        while (!stack.isEmpty() && a[stack.peek()] < a[i]) res[stack.pop()] = a[i];
        stack.push(i);
    }
    return res;
}
// [2, 1, 2, 4, 3] -> [4, 2, 4, -1, -1]. O(n): each index is pushed and popped once
```

**Worked example: daily temperatures** (days to wait for a warmer day): same loop, store `i - stack.pop()` instead
of `a[i]`.

**Pitfalls:** using `java.util.Stack` (synchronized, legacy: use `ArrayDeque`); `ArrayDeque` refuses `null`;
storing values when you need distances (store indices).

**Practice:** min stack, evaluate reverse Polish notation, largest rectangle in histogram, simplify path, decode
string.

### Intervals {#intervals}

**Recognise it when** you see ranges `[start, end]`: meetings, bookings, time slots. **Sort by start** first, almost
always.

**Worked example: merge overlapping intervals.**

```java
int[][] merge(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(iv -> iv[0]));
    List<int[]> out = new ArrayList<>();
    for (int[] iv : intervals) {
        if (out.isEmpty() || out.getLast()[1] < iv[0]) out.add(iv);       // gap: new interval
        else out.getLast()[1] = Math.max(out.getLast()[1], iv[1]);        // overlap: extend
    }
    return out.toArray(int[][]::new);
}
// [[1,3],[2,6],[8,10],[15,18]] -> [[1,6],[8,10],[15,18]]. O(n log n)
```

**Worked example: minimum number of meeting rooms.** Sort by start; a min-heap holds the end times of rooms in use.

```java
int minRooms(int[][] meetings) {
    Arrays.sort(meetings, Comparator.comparingInt(m -> m[0]));
    PriorityQueue<Integer> ends = new PriorityQueue<>();
    for (int[] m : meetings) {
        if (!ends.isEmpty() && ends.peek() <= m[0]) ends.poll();   // reuse the room that frees up first
        ends.offer(m[1]);
    }
    return ends.size();
}
// [[0,30],[5,10],[15,20]] -> 2
```

**Overlap test** for two half-open intervals `[a1, a2)` and `[b1, b2)`: `a1 < b2 && b1 < a2`.

**Pitfalls:** clarify **closed vs half-open** (does `[1,2]` touch `[2,3]`?); comparator `a[0] - b[0]` overflows (use
`Integer.compare` / `comparingInt`); mutating the input array when the caller still needs it.

**Practice:** insert interval, non-overlapping intervals (greedy), interval list intersections, employee free time,
find free slots in a calendar ([Live Coding Q21](../interviews/coding.md#given-practitioner-working-hours-existing)).

### Heap / top K {#heap-top-k}

**Recognise it when** you need the K largest/smallest/most frequent, the K-th element, to merge K sorted sources, or
always "the next smallest" in a changing set.

**Rule:** for the top K **largest**, keep a **min-heap of size K** and evict the smallest. O(n log K), not O(n log n).

**Worked example: top K frequent words**, ties broken alphabetically.

```java
List<String> topKFrequent(String[] words, int k) {
    Map<String, Integer> freq = new HashMap<>();
    for (String w : words) freq.merge(w, 1, Integer::sum);

    Comparator<String> worstFirst = Comparator.<String>comparingInt(freq::get)
            .thenComparing(Comparator.reverseOrder());          // lower count, then later alphabetically = worse
    PriorityQueue<String> heap = new PriorityQueue<>(worstFirst);
    for (String w : freq.keySet()) {
        heap.offer(w);
        if (heap.size() > k) heap.poll();                       // evict the worst
    }
    List<String> out = new ArrayList<>();
    while (!heap.isEmpty()) out.add(heap.poll());
    return out.reversed();                                       // best first
}
```

**Worked example: merge K sorted lists.**

```java
List<Integer> mergeK(List<List<Integer>> lists) {
    // heap entry: {value, list index, element index}
    PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(e -> e[0]));
    for (int i = 0; i < lists.size(); i++)
        if (!lists.get(i).isEmpty()) heap.offer(new int[] { lists.get(i).get(0), i, 0 });
    List<Integer> out = new ArrayList<>();
    while (!heap.isEmpty()) {
        int[] e = heap.poll();
        out.add(e[0]);
        int next = e[2] + 1;
        if (next < lists.get(e[1]).size()) heap.offer(new int[] { lists.get(e[1]).get(next), e[1], next });
    }
    return out;
}
// O(N log K) for N total elements
```

**Pitfalls:** iterating a `PriorityQueue` is **not** sorted order (only `poll` is); max-heap via `a - b` reversed
overflows (use `Comparator.reverseOrder()`); the alternative "sort everything" is fine for small n, say it.

**Practice:** K-th largest element, K closest points to origin, find median from data stream (two heaps), task
scheduler, reorganize string.

### BFS / DFS on graphs and grids {#bfs-dfs-graphs-grids}

**Recognise it when** you see a grid, a network, dependencies, "connected", "reachable", or "shortest path" with
equal edge weights.

- **BFS** (queue): shortest path in an **unweighted** graph, level by level.
- **DFS** (recursion or stack): connected components, cycle detection, exploring all paths.
- **Topological sort**: an order that respects dependencies.

**Template (grid BFS with distance):**

```java
static final int[][] DIRS = { {1, 0}, {-1, 0}, {0, 1}, {0, -1} };

int shortestPath(char[][] grid, int sr, int sc, int tr, int tc) {   // '#' = wall
    int rows = grid.length, cols = grid[0].length;
    int[][] dist = new int[rows][cols];
    for (int[] row : dist) Arrays.fill(row, -1);
    Deque<int[]> queue = new ArrayDeque<>();
    queue.offer(new int[] { sr, sc });
    dist[sr][sc] = 0;                                    // mark visited when enqueued, not when polled
    while (!queue.isEmpty()) {
        int[] cur = queue.poll();
        if (cur[0] == tr && cur[1] == tc) return dist[tr][tc];
        for (int[] d : DIRS) {
            int r = cur[0] + d[0], c = cur[1] + d[1];
            if (r < 0 || c < 0 || r >= rows || c >= cols || grid[r][c] == '#' || dist[r][c] != -1) continue;
            dist[r][c] = dist[cur[0]][cur[1]] + 1;
            queue.offer(new int[] { r, c });
        }
    }
    return -1;
}
// O(rows · cols) time and space
```

**Worked example: number of islands (DFS flood fill).**

```java
int numIslands(char[][] grid) {
    int count = 0;
    for (int r = 0; r < grid.length; r++)
        for (int c = 0; c < grid[0].length; c++)
            if (grid[r][c] == '1') { count++; sink(grid, r, c); }
    return count;
}

void sink(char[][] g, int r, int c) {
    if (r < 0 || c < 0 || r >= g.length || c >= g[0].length || g[r][c] != '1') return;
    g[r][c] = '0';                                       // mark visited by mutating (say so; copy if not allowed)
    sink(g, r + 1, c); sink(g, r - 1, c); sink(g, r, c + 1); sink(g, r, c - 1);
}
```

**Worked example: course schedule (topological sort, Kahn's algorithm).** Can all courses be finished given
`[course, prerequisite]` pairs? Return an order or an empty list if there is a cycle.

```java
List<Integer> courseOrder(int n, int[][] prereqs) {
    List<List<Integer>> next = new ArrayList<>();
    for (int i = 0; i < n; i++) next.add(new ArrayList<>());
    int[] indegree = new int[n];
    for (int[] p : prereqs) { next.get(p[1]).add(p[0]); indegree[p[0]]++; }

    Deque<Integer> ready = new ArrayDeque<>();
    for (int i = 0; i < n; i++) if (indegree[i] == 0) ready.offer(i);
    List<Integer> order = new ArrayList<>();
    while (!ready.isEmpty()) {
        int c = ready.poll();
        order.add(c);
        for (int d : next.get(c)) if (--indegree[d] == 0) ready.offer(d);
    }
    return order.size() == n ? order : List.of();      // leftovers = a cycle
}
// O(V + E)
```

**Pitfalls:** marking visited on poll in BFS (nodes get enqueued many times); deep recursion on a 1000×1000 grid
overflows the stack (switch to an explicit stack or BFS); weighted edges need Dijkstra, not BFS.

**Practice:** rotting oranges (multi-source BFS), clone graph, word ladder, Pacific Atlantic water flow, network
delay time (Dijkstra).

### Backtracking {#backtracking}

**Recognise it when** you must **generate all** combinations, permutations, subsets, or placements (N-queens,
sudoku), and n is small.

**Template: choose → explore → unchoose.**

```java
void backtrack(State state, List<Result> out) {
    if (isComplete(state)) { out.add(snapshot(state)); return; }
    for (Choice c : choices(state)) {
        if (!allowed(state, c)) continue;   // prune early
        apply(state, c);                     // choose
        backtrack(state, out);               // explore
        undo(state, c);                      // unchoose
    }
}
```

**Worked example: subsets.**

```java
List<List<Integer>> subsets(int[] nums) {
    List<List<Integer>> out = new ArrayList<>();
    collect(nums, 0, new ArrayList<>(), out);
    return out;
}

void collect(int[] nums, int start, List<Integer> current, List<List<Integer>> out) {
    out.add(new ArrayList<>(current));                   // copy! current keeps changing
    for (int i = start; i < nums.length; i++) {
        current.add(nums[i]);
        collect(nums, i + 1, current, out);
        current.removeLast();
    }
}
// [1,2,3] -> [], [1], [1,2], [1,2,3], [1,3], [2], [2,3], [3]. O(2ⁿ · n)
```

**Worked example: permutations.**

```java
List<List<Integer>> permutations(int[] nums) {
    List<List<Integer>> out = new ArrayList<>();
    permute(nums, new boolean[nums.length], new ArrayList<>(), out);
    return out;
}

void permute(int[] nums, boolean[] used, List<Integer> current, List<List<Integer>> out) {
    if (current.size() == nums.length) { out.add(new ArrayList<>(current)); return; }
    for (int i = 0; i < nums.length; i++) {
        if (used[i]) continue;
        used[i] = true; current.add(nums[i]);
        permute(nums, used, current, out);
        used[i] = false; current.removeLast();
    }
}
// O(n! · n)
```

**Worked example: combination sum** (reuse allowed, candidates sorted so we can stop early).

```java
void combine(int[] sortedCandidates, int start, int remaining, List<Integer> current, List<List<Integer>> out) {
    if (remaining == 0) { out.add(new ArrayList<>(current)); return; }
    for (int i = start; i < sortedCandidates.length && sortedCandidates[i] <= remaining; i++) {   // prune
        current.add(sortedCandidates[i]);
        combine(sortedCandidates, i, remaining - sortedCandidates[i], current, out);                // i, not i+1: reuse
        current.removeLast();
    }
}
```

**Pitfalls:** adding `current` instead of a copy (all results end up identical and empty); forgetting to undo;
duplicates in input (sort, then `if (i > start && a[i] == a[i - 1]) continue`).

**Practice:** letter combinations of a phone number, generate parentheses, word search, N-queens, palindrome
partitioning.

### Dynamic programming {#dynamic-programming}

**Recognise it when** the question is "how many ways", "minimum/maximum cost", "longest/shortest subsequence", "can
you reach", and the brute-force recursion **recomputes the same subproblems**.

**Recipe:**

1. **State**: what does `dp[i]` (or `dp[i][j]`) mean, in one sentence?
2. **Transition**: how is `dp[i]` built from smaller states?
3. **Base case** and **answer** location.
4. **Order**: fill so that dependencies are ready; then see if only the last row/values are needed (space O(1) or O(n)).

Start with the recursion + memo (top-down) if it is easier to explain, then convert to a table (bottom-up).

**Worked example: house robber (1D).** Max sum without taking two adjacent houses.
`dp[i] = max(dp[i-1], dp[i-2] + a[i])`.

```java
int rob(int[] a) {
    int prev2 = 0, prev1 = 0;                   // dp[i-2], dp[i-1]
    for (int x : a) {
        int cur = Math.max(prev1, prev2 + x);   // skip this house, or take it
        prev2 = prev1;
        prev1 = cur;
    }
    return prev1;
}
// [2,7,9,3,1] -> 12 (2 + 9 + 1). O(n) time, O(1) space
```

**Worked example: coin change** (min coins, unbounded). `dp[amount] = 1 + min(dp[amount - coin])`.

```java
int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, amount + 1);                // "infinity" that can't overflow on + 1
    dp[0] = 0;
    for (int a = 1; a <= amount; a++)
        for (int c : coins)
            if (c <= a) dp[a] = Math.min(dp[a], dp[a - c] + 1);
    return dp[amount] > amount ? -1 : dp[amount];
}
// coins [1,2,5], 11 -> 3 (5+5+1). O(amount · coins)
```

**Worked example: longest common subsequence (2D).** `dp[i][j]` = LCS of the first `i` chars of `a` and first `j`
of `b`.

```java
int lcs(String a, String b) {
    int[][] dp = new int[a.length() + 1][b.length() + 1];   // row/col 0 = empty prefix
    for (int i = 1; i <= a.length(); i++)
        for (int j = 1; j <= b.length(); j++)
            dp[i][j] = a.charAt(i - 1) == b.charAt(j - 1)
                    ? dp[i - 1][j - 1] + 1
                    : Math.max(dp[i - 1][j], dp[i][j - 1]);
    return dp[a.length()][b.length()];
}
// "abcde", "ace" -> 3. O(n · m)
```

**Top-down version** of the same idea, when the recursion is the natural explanation:

```java
Map<Integer, Long> memo = new HashMap<>();
long climbStairs(int n) {                       // ways to climb n steps by 1 or 2
    if (n <= 1) return 1;
    Long cached = memo.get(n);
    if (cached != null) return cached;
    long ways = climbStairs(n - 1) + climbStairs(n - 2);
    memo.put(n, ways);
    return ways;
}
```

**Pitfalls:** `computeIfAbsent` with a recursive lambda on a `HashMap` throws `ConcurrentModificationException`
(use get/put as above); an off-by-one between "first i items" and "index i"; `Integer.MAX_VALUE + 1` as infinity
overflows.

**Practice:** climbing stairs, maximum subarray (Kadane), longest increasing subsequence, word break, edit distance,
unique paths, 0/1 knapsack.

### Greedy {#greedy}

**Recognise it when** a local choice can be proven never to hurt ("take the interval that ends first", "go as far as
you can"). If you can't argue why, it is probably DP.

**Worked example: jump game.** Can you reach the last index (each value = max jump length)?

```java
boolean canJump(int[] nums) {
    int reach = 0;
    for (int i = 0; i < nums.length; i++) {
        if (i > reach) return false;            // stuck before i
        reach = Math.max(reach, i + nums[i]);
    }
    return true;
}
// [2,3,1,1,4] -> true, [3,2,1,0,4] -> false. O(n)
```

**Worked example: maximum non-overlapping intervals** (interval scheduling). Sort by **end**, take every interval that
starts after the last taken one ends.

```java
int maxNonOverlapping(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(iv -> iv[1]));
    int count = 0, lastEnd = Integer.MIN_VALUE;
    for (int[] iv : intervals)
        if (iv[0] >= lastEnd) { count++; lastEnd = iv[1]; }
    return count;
}
// Ending first leaves the most room for the rest: exchange argument
```

**Worked example: maximum subarray (Kadane).** Drop the running sum when it becomes a burden.

```java
int maxSubArray(int[] a) {
    int best = a[0], cur = a[0];
    for (int i = 1; i < a.length; i++) {
        cur = Math.max(a[i], cur + a[i]);
        best = Math.max(best, cur);
    }
    return best;
}
// [-2,1,-3,4,-1,2,1,-5,4] -> 6 ([4,-1,2,1])
```

**Pitfalls:** sorting by start instead of end for interval scheduling; coin change is **not** greedy for arbitrary
coins (`[1,3,4]`, 6 → greedy gives 4+1+1, optimal is 3+3).

**Practice:** best time to buy and sell stock, gas station, partition labels, assign cookies, minimum arrows to burst
balloons.

### Linked lists {#linked-lists}

**Recognise it when** the input is a `ListNode`. Draw the pointers; most bugs are a lost `next`.

```java
class ListNode { int val; ListNode next; ListNode(int v, ListNode n) { val = v; next = n; } }
```

**Worked example: reverse a list.** Three pointers: `prev`, `cur`, `next`.

```java
ListNode reverse(ListNode head) {
    ListNode prev = null, cur = head;
    while (cur != null) {
        ListNode next = cur.next;   // save before overwriting
        cur.next = prev;
        prev = cur;
        cur = next;
    }
    return prev;
}
// 1->2->3 -> 3->2->1. O(n) time, O(1) space
```

**Worked example: merge two sorted lists (dummy head trick).** A dummy node removes the "is the result empty yet?"
special case.

```java
ListNode mergeSorted(ListNode a, ListNode b) {
    ListNode dummy = new ListNode(0, null), tail = dummy;
    while (a != null && b != null) {
        if (a.val <= b.val) { tail.next = a; a = a.next; }
        else { tail.next = b; b = b.next; }
        tail = tail.next;
    }
    tail.next = a != null ? a : b;
    return dummy.next;
}
```

**Worked example: remove the N-th node from the end.** Move `fast` N steps ahead, then move both.

```java
ListNode removeNthFromEnd(ListNode head, int n) {
    ListNode dummy = new ListNode(0, head), fast = dummy, slow = dummy;
    for (int i = 0; i <= n; i++) fast = fast.next;
    while (fast != null) { fast = fast.next; slow = slow.next; }
    slow.next = slow.next.next;
    return dummy.next;
}
```

**Pitfalls:** losing the rest of the list by overwriting `next` first; forgetting the head can change (use a dummy);
null checks on `n` larger than the length.

**Practice:** reorder list, add two numbers, intersection of two lists, copy list with random pointer, LRU cache
([Live Coding Q17](../interviews/coding.md#implement-lru-cache-o-1)).

### Trees {#trees}

**Recognise it when** you see a binary tree, BST, depth, paths, ancestors. Most answers are a **recursive DFS** that
returns something from each subtree, or a **BFS** for level-by-level questions.

```java
record TreeNode(int val, TreeNode left, TreeNode right) {}
```

**Template (post-order: combine children's answers).**

```java
int maxDepth(TreeNode node) {
    if (node == null) return 0;                                   // base case
    return 1 + Math.max(maxDepth(node.left()), maxDepth(node.right()));
}
```

**Worked example: validate a BST.** Pass the allowed range down; checking only direct children is the classic bug.

```java
boolean isValidBst(TreeNode node, long min, long max) {   // call with Long.MIN_VALUE, Long.MAX_VALUE
    if (node == null) return true;
    if (node.val() <= min || node.val() >= max) return false;
    return isValidBst(node.left(), min, node.val()) && isValidBst(node.right(), node.val(), max);
}
```

**Worked example: level-order traversal (BFS).**

```java
List<List<Integer>> levels(TreeNode root) {
    List<List<Integer>> out = new ArrayList<>();
    if (root == null) return out;
    Deque<TreeNode> queue = new ArrayDeque<>(List.of(root));
    while (!queue.isEmpty()) {
        List<Integer> level = new ArrayList<>();
        for (int size = queue.size(); size > 0; size--) {   // freeze the level size first
            TreeNode n = queue.poll();
            level.add(n.val());
            if (n.left() != null) queue.offer(n.left());
            if (n.right() != null) queue.offer(n.right());
        }
        out.add(level);
    }
    return out;
}
```

**Worked example: diameter (answer ≠ return value).** The recursion returns the depth, but updates a global best
with "left depth + right depth" at each node.

```java
int best = 0;
int diameter(TreeNode root) { depth(root); return best; }
int depth(TreeNode n) {
    if (n == null) return 0;
    int l = depth(n.left()), r = depth(n.right());
    best = Math.max(best, l + r);
    return 1 + Math.max(l, r);
}
```

**Pitfalls:** BST validation with `int` bounds fails on `Integer.MIN_VALUE` nodes (use `long` or nullable bounds);
recursion depth on a degenerate (list-shaped) tree; mixing up pre/in/post-order (in-order of a BST is sorted).

**Practice:** invert binary tree, lowest common ancestor, path sum, serialize/deserialize, K-th smallest in a BST.

## Classic katas (TDD)

A kata is graded on **process**, not just the result: small red → green → refactor steps, test names that read as
specs, refactoring under green tests. Say "next simplest failing test" out loud. JUnit 5 + AssertJ below.

### FizzBuzz {#fizzbuzz}

**Rules:** for 1..100 print the number, but "Fizz" for multiples of 3, "Buzz" for 5, "FizzBuzz" for both.

**Test sequence:** `1 → "1"`, `2 → "2"`, `3 → "Fizz"`, `5 → "Buzz"`, `6 → "Fizz"`, `15 → "FizzBuzz"`.

```java
@ParameterizedTest
@CsvSource({ "1,1", "2,2", "3,Fizz", "5,Buzz", "6,Fizz", "10,Buzz", "15,FizzBuzz", "30,FizzBuzz" })
void says(int n, String expected) {
    assertThat(FizzBuzz.say(n)).isEqualTo(expected);
}

static String say(int n) {
    String s = (n % 3 == 0 ? "Fizz" : "") + (n % 5 == 0 ? "Buzz" : "");
    return s.isEmpty() ? String.valueOf(n) : s;
}
```

**Interviewer follow-up:** "add 7 → Whizz". The concatenation version extends by adding one rule; an `if/else` chain
explodes. A `LinkedHashMap<Integer, String>` of rules is the next refactoring, **only** once a third rule exists.

### String Calculator {#string-calculator}

**Rules (Roy Osherove):** `add("")` → 0, `"1"` → 1, `"1,2"` → 3, any count of numbers, newlines as separators
(`"1\n2,3"`), custom delimiter `"//;\n1;2"`, negatives throw with all of them listed, numbers > 1000 ignored.

**Test sequence:** one test per rule, in that order; refactor after each green.

```java
class StringCalculator {
    int add(String input) {
        if (input.isEmpty()) return 0;
        String delimiters = ",|\n";
        if (input.startsWith("//")) {
            int nl = input.indexOf('\n');
            delimiters = Pattern.quote(input.substring(2, nl));
            input = input.substring(nl + 1);
        }
        List<Integer> numbers = Arrays.stream(input.split(delimiters)).map(Integer::parseInt).toList();
        List<Integer> negatives = numbers.stream().filter(n -> n < 0).toList();
        if (!negatives.isEmpty()) throw new IllegalArgumentException("negatives not allowed: " + negatives);
        return numbers.stream().filter(n -> n <= 1000).mapToInt(Integer::intValue).sum();
    }
}

@Test void emptyIsZero()            { assertThat(calc.add("")).isZero(); }
@Test void sumsManyNumbers()        { assertThat(calc.add("1,2,3,4")).isEqualTo(10); }
@Test void newlineIsADelimiter()    { assertThat(calc.add("1\n2,3")).isEqualTo(6); }
@Test void customDelimiter()        { assertThat(calc.add("//;\n1;2")).isEqualTo(3); }
@Test void ignoresAbove1000()       { assertThat(calc.add("2,1001")).isEqualTo(2); }
@Test void listsAllNegatives() {
    assertThatThrownBy(() -> calc.add("1,-2,-3")).hasMessageContaining("[-2, -3]");
}
```

**What they watch:** `Pattern.quote` for delimiters like `*` or `.` (regex metacharacters); not writing the custom
delimiter code before its test exists.

### Roman Numerals {#roman-numerals}

**Rules:** convert 1..3999 to Roman numerals (1994 → "MCMXCIV").

**Test sequence:** 1 → I, 2 → II, 4 → IV, 5 → V, 9 → IX, 10 → X, 40 → XL… The trick appears after IV and IX: put
the **subtractive pairs in the table** instead of special-casing them.

```java
private static final int[] VALUES = { 1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1 };
private static final String[] SYMBOLS = { "M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I" };

static String toRoman(int n) {
    if (n < 1 || n > 3999) throw new IllegalArgumentException("out of range: " + n);
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < VALUES.length; i++)
        for (; n >= VALUES[i]; n -= VALUES[i]) sb.append(SYMBOLS[i]);   // greedy works for this table
    return sb.toString();
}

static int fromRoman(String s) {
    Map<Character, Integer> v = Map.of('I', 1, 'V', 5, 'X', 10, 'L', 50, 'C', 100, 'D', 500, 'M', 1000);
    int total = 0;
    for (int i = 0; i < s.length(); i++) {
        int cur = v.get(s.charAt(i));
        boolean subtract = i + 1 < s.length() && cur < v.get(s.charAt(i + 1));   // IV, IX, XL…
        total += subtract ? -cur : cur;
    }
    return total;
}
```

**Property test** worth mentioning: `fromRoman(toRoman(n)) == n` for all n in 1..3999.

### Bowling Game {#bowling-game}

**Rules (Uncle Bob):** 10 frames; a **spare** (10 pins in two rolls) scores 10 + next roll; a **strike** (10 on the
first roll) scores 10 + next two rolls; the 10th frame grants bonus rolls.

**Test sequence:** gutter game (all 0) → 0; all ones → 20; one spare; one strike; perfect game (12 strikes) → 300.

```java
class BowlingGame {
    private final List<Integer> rolls = new ArrayList<>();

    void roll(int pins) { rolls.add(pins); }

    int score() {
        int score = 0, i = 0;                        // i = first roll of the current frame
        for (int frame = 0; frame < 10; frame++) {
            if (rolls.get(i) == 10) {                // strike
                score += 10 + rolls.get(i + 1) + rolls.get(i + 2);
                i += 1;
            } else if (rolls.get(i) + rolls.get(i + 1) == 10) {   // spare
                score += 10 + rolls.get(i + 2);
                i += 2;
            } else {
                score += rolls.get(i) + rolls.get(i + 1);
                i += 2;
            }
        }
        return score;
    }
}

@Test void perfectGame() {
    for (int i = 0; i < 12; i++) game.roll(10);
    assertThat(game.score()).isEqualTo(300);
}
@Test void oneSpare() {
    game.roll(5); game.roll(5); game.roll(3);       // 10 + 3, then 3
    for (int i = 0; i < 17; i++) game.roll(0);
    assertThat(game.score()).isEqualTo(16);
}
```

**What they watch:** iterating by **frame**, not by roll (the key design insight); extracting `isStrike(i)`,
`isSpare(i)` once the tests are green; a `rollMany(n, pins)` test helper.

### Game of Life {#game-of-life}

**Rules:** a live cell with 2 or 3 live neighbours survives; a dead cell with exactly 3 becomes alive; everything
else dies or stays dead.

**Test sequence:** the rule function first (pure, table-driven), then the grid: a blinker oscillates, a block stays
still.

```java
static boolean nextState(boolean alive, int liveNeighbours) {
    return liveNeighbours == 3 || (alive && liveNeighbours == 2);
}

// Infinite board: store only live cells, so the grid never needs resizing
record Cell(int x, int y) {
    Stream<Cell> neighbours() {
        return IntStream.rangeClosed(-1, 1).boxed()
                .flatMap(dx -> IntStream.rangeClosed(-1, 1).mapToObj(dy -> new Cell(x + dx, y + dy)))
                .filter(c -> !c.equals(this));
    }
}

static Set<Cell> tick(Set<Cell> alive) {
    Map<Cell, Long> counts = alive.stream()
            .flatMap(Cell::neighbours)
            .collect(Collectors.groupingBy(c -> c, Collectors.counting()));
    return counts.entrySet().stream()
            .filter(e -> nextState(alive.contains(e.getKey()), e.getValue().intValue()))
            .map(Map.Entry::getKey)
            .collect(Collectors.toSet());
}

@Test void blinkerOscillates() {
    Set<Cell> horizontal = Set.of(new Cell(0, 1), new Cell(1, 1), new Cell(2, 1));
    Set<Cell> vertical = Set.of(new Cell(1, 0), new Cell(1, 1), new Cell(1, 2));
    assertThat(tick(horizontal)).isEqualTo(vertical);
    assertThat(tick(vertical)).isEqualTo(horizontal);
}
```

**What they watch:** never updating the board in place (the next generation is computed from the current one only);
separating the rule from the board; the sparse `Set<Cell>` model as a design talking point.

### Gilded Rose (refactoring kata) {#gilded-rose}

**Setup:** you get a legacy `updateQuality()` full of nested `if`s and must add "Conjured" items (degrade twice as
fast) without breaking existing behaviour. This is a **refactoring** exercise, not an algorithm.

**Steps:**

1. **Characterization tests first**: pin current behaviour. Fastest route: a golden-master test that runs every
   item type for ~30 days and compares the printed output with a stored snapshot (approval testing).
2. **Refactor in tiny steps** under green tests: extract per-item methods, invert conditions, remove duplication.
3. Introduce polymorphism **once the branches are isolated**: one updater per item kind.
4. **Then** add Conjured, test-first.

```java
interface Updater { void update(Item item); }

static Updater updaterFor(Item item) {
    return switch (item.name) {
        case "Aged Brie" -> i -> { i.sellIn--; i.quality = Math.min(50, i.quality + (i.sellIn < 0 ? 2 : 1)); };
        case "Sulfuras, Hand of Ragnaros" -> i -> { };                        // never changes
        case "Backstage passes to a TAFKAL80ETC concert" -> i -> {
            i.sellIn--;
            i.quality = i.sellIn < 0 ? 0
                    : Math.min(50, i.quality + (i.sellIn < 5 ? 3 : i.sellIn < 10 ? 2 : 1));
        };
        default -> degrading(item.name.startsWith("Conjured") ? 2 : 1);
    };
}

static Updater degrading(int rate) {
    return i -> { i.sellIn--; i.quality = Math.max(0, i.quality - rate * (i.sellIn < 0 ? 2 : 1)); };
}
```

**What they watch:** do you write tests **before** touching the code; do you commit at each green step; do you leave
the `Item` class alone (the kata forbids changing it, read the constraints).

### Bank Account {#bank-account}

**Rules:** `deposit(amount)`, `withdraw(amount)`, `printStatement()` with date, amount and running balance, newest
first. The kata is about **design**: value objects, injected clock, separating storage from formatting.

```java
record Transaction(LocalDate date, BigDecimal amount) {}

class Account {
    private final List<Transaction> transactions = new ArrayList<>();
    private final Clock clock;                       // injected: tests control "today"

    Account(Clock clock) { this.clock = clock; }

    void deposit(BigDecimal amount)  { record(requirePositive(amount)); }
    void withdraw(BigDecimal amount) {
        if (balance().compareTo(amount) < 0) throw new IllegalStateException("insufficient funds");
        record(requirePositive(amount).negate());
    }

    BigDecimal balance() {
        return transactions.stream().map(Transaction::amount).reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    String statement() {
        List<String> lines = new ArrayList<>();
        BigDecimal running = BigDecimal.ZERO;
        for (Transaction t : transactions) {
            running = running.add(t.amount());
            lines.add("%s | %s | %s".formatted(t.date(), t.amount(), running));
        }
        return "date | amount | balance\n" + String.join("\n", lines.reversed());
    }

    private void record(BigDecimal amount) { transactions.add(new Transaction(LocalDate.now(clock), amount)); }

    private static BigDecimal requirePositive(BigDecimal a) {
        if (a.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
        return a;
    }
}

@Test void statementIsNewestFirstWithRunningBalance() {
    Account account = new Account(Clock.fixed(Instant.parse("2026-01-10T10:00:00Z"), ZoneOffset.UTC));
    account.deposit(new BigDecimal("1000"));
    account.withdraw(new BigDecimal("400"));
    assertThat(account.statement()).isEqualTo("""
            date | amount | balance
            2026-01-10 | -400 | 600
            2026-01-10 | 1000 | 1000""");
}
```

**What they watch:** `BigDecimal` (never `double`) for money; an injected `Clock` instead of `LocalDate.now()`;
validation of negative amounts and overdraft; an outside-in acceptance test first, then unit tests.

### Other katas worth knowing

| Kata | What it trains |
|---|---|
| Prime factors | Tiny TDD steps where the algorithm "emerges" from tests |
| Word wrap | Choosing the next test so the code doesn't take a giant leap |
| Mars Rover | Commands, state machine, value objects (`Position`, `Direction`) |
| Tennis (refactoring) | Turning a tangled score function into readable code |
| Parking lot / vending machine | OOP design under evolving requirements |
| Mastermind | Counting exact and misplaced matches (hashing) |
| LRU cache | `LinkedHashMap(accessOrder=true)` + `removeEldestEntry`, or map + doubly linked list |

## Java toolbox for live coding

| Need | Use | Notes |
|---|---|---|
| Lookup, count, dedup | `HashMap`, `HashSet` | `merge(k, 1, Integer::sum)`, `getOrDefault`, `computeIfAbsent` |
| Stack and queue | `ArrayDeque` | `push/pop/peek` (stack), `offer/poll/peek` (queue); no `null` |
| Min/max heap | `PriorityQueue` | `new PriorityQueue<>(Comparator.reverseOrder())` for max |
| Sorted keys, floor/ceiling | `TreeMap`, `TreeSet` | `floorKey`, `ceilingKey`, `headMap`, `pollFirst` |
| Insertion order / LRU | `LinkedHashMap` | `accessOrder = true` + `removeEldestEntry` |
| Counts over a small alphabet | `int[26]`, `int[128]` | `count[c - 'a']++`, faster than a map |
| String building | `StringBuilder` | `reverse()`, `setLength(0)`, `deleteCharAt` |
| Sorting | `Arrays.sort`, `List.sort` | Comparators: `comparingInt(...).thenComparing(...)` |
| Java 21 sequenced | `getFirst()`, `getLast()`, `removeLast()`, `reversed()` | On `List`, `Deque`, `LinkedHashMap` |
| Big numbers | `long`, `Math.addExact`, `BigInteger` | Overflow is a classic follow-up question |

Collection internals and their complexities: [Java Q6](../interviews/java-core-jvm.md#arraylist-linkedlist-hashmap-treemap-linkedhashmap).

**Traps:** `Integer == Integer` above 127; `(a, b) -> a - b` comparators overflow; `Arrays.asList` is fixed-size;
`List.of` is immutable and refuses `null`; `char + int` is an `int`; `s.split(".")` needs `"\\."`; recursion depth
around 10⁴ frames by default.

## Practice plan

**Format:** 25 minutes per problem, out loud, timer on. If stuck after 10 minutes, write the brute force and move on;
then read the pattern above and redo the problem the next day.

| Week | Patterns | Problems |
|---|---|---|
| 1 | Hashing, two pointers, sliding window | Two sum, group anagrams, 3-sum, longest substring without repeats, min window |
| 2 | Binary search, stack, intervals | Search rotated array, ship within D days, valid brackets, daily temperatures, merge intervals |
| 3 | Heap, BFS/DFS, topological sort | Top K frequent, merge K lists, islands, rotting oranges, course schedule |
| 4 | Backtracking, DP, greedy | Subsets, combination sum, coin change, LCS, house robber, jump game |
| Katas | One per session, TDD, commit at each green | FizzBuzz → String Calculator → Roman → Bowling → Game of Life → Gilded Rose → Bank Account |

**Before the interview:** redo one problem per pattern from memory, and one kata end to end with tests.
