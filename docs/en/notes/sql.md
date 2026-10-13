# SQL Query Tuning

## Reading a plan

### EXPLAIN vs EXPLAIN ANALYZE

| Command | Runs the query? | Gives you |
|---|---|---|
| `EXPLAIN` | No | The planner's **estimated** plan and costs |
| `EXPLAIN ANALYZE` | **Yes** | Estimates **+ actual** rows, time, loops |
| `EXPLAIN (ANALYZE, BUFFERS)` | **Yes** | Also shared buffer hits/reads (memory vs disk I/O) |

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS, FORMAT JSON) SELECT ...;  -- JSON: paste into explain.dalibo.com
```

`EXPLAIN ANALYZE` really executes the statement. For `INSERT/UPDATE/DELETE`, roll back:

```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) DELETE FROM orders WHERE created_at < now() - interval '2 years';
ROLLBACK;
```

Always use `BUFFERS`; the time alone hides whether you were slow because of disk or CPU.

### Reading the output

```text
Index Scan using idx_orders_customer on orders  (cost=0.43..8.45 rows=1 width=64) (actual time=0.021..0.023 rows=3 loops=1)
  Index Cond: (customer_id = 42)
  Buffers: shared hit=4
Planning Time: 0.110 ms
Execution Time: 0.045 ms
```

| Part | Meaning |
|---|---|
| `Index Scan using ...` | The **node** (operation). Plans are trees: indentation = children; data flows from the **innermost/deepest** nodes up to the root |
| `cost=0.43..8.45` | Planner units (not ms). `startup..total`: startup = cost before the first row, total = cost for all rows. A node's cost includes its children |
| `rows=1` | **Estimated** rows out of this node |
| `width=64` | Estimated average row size in bytes |
| `actual time=0.021..0.023` | Real ms: time to first row..time to last row, **per loop** |
| `rows=3` (actual) | **Real** rows produced, **per loop** |
| `loops=1` | Times the node ran. Real total time = `actual time × loops`; real total rows = `rows × loops` |
| `Index Cond` / `Filter` | `Index Cond` is applied *inside* the index (good). `Filter` is applied *after* reading rows (rows read then thrown away) |
| `Rows Removed by Filter: N` | Rows read then discarded. Big N = wasted work, an index is probably missing or wrong |
| `Buffers: shared hit=4 read=2` | `hit` = found in Postgres cache, `read` = fetched from OS/disk, `dirtied/written` = writes |
| `Planning Time` / `Execution Time` | Parse+plan vs run. Execution time excludes network transfer to the client |

### Scan nodes (how a table is read)

| Node | What it does | When it is fine |
|---|---|---|
| `Seq Scan` | Reads the whole table | Small tables, or you need a large fraction of rows (> ~5-10%) |
| `Index Scan` | Walks the index, then fetches each row from the table (heap) | Few rows |
| `Index Only Scan` | Answers from the index alone. Check `Heap Fetches: 0` (else the visibility map is stale, run `VACUUM`) | Covering index |
| `Bitmap Index Scan` + `Bitmap Heap Scan` | Builds a bitmap of matching pages, reads them in physical order | Medium number of rows, or combining several indexes (`BitmapOr/And`) |

A `Seq Scan` is **not always bad**. It is bad when it discards most of what it reads (`Rows Removed by Filter` huge) on a big table.

### Join nodes

| Node | How | Good when |
|---|---|---|
| `Nested Loop` | For each outer row, probe the inner side | Outer side small **and** inner side indexed |
| `Hash Join` | Build a hash table on the smaller side, probe with the other | Large unsorted inputs, equality joins |
| `Merge Join` | Merge two sorted inputs | Both inputs already sorted (e.g. by index) |

Other nodes: `Sort` (watch `Sort Method: external merge Disk: ...` = spilled to disk, raise `work_mem` or add an index), `HashAggregate` / `GroupAggregate`, `Limit`, `Materialize`, `Gather` (parallel workers).

### Red flags checklist

1. **Estimated vs actual rows far apart** (`rows=1` estimated, `rows=200000` actual): stale or insufficient statistics. Run `ANALYZE table;`, raise `ALTER TABLE t ALTER COLUMN c SET STATISTICS 500;`, or add extended statistics for correlated columns. A wrong estimate makes the planner choose the wrong join type and order.
2. **`Rows Removed by Filter`** much larger than rows returned: missing or non-matching index.
3. **`Seq Scan` on a big table** returning few rows.
4. **`Nested Loop` with a large `loops`** and a slow inner node: the inner runs N times.
5. **`Sort Method: external merge Disk`** or `Hash Batches > 1`: not enough `work_mem`.
6. **`Heap Fetches` high on Index Only Scan**: needs `VACUUM`.
7. **`Buffers: read` high**: cold cache or working set too big; run twice to compare warm vs cold.
8. **Time hidden in a child**: always find the node with the biggest **exclusive** time (its time minus its children's time × loops).

### Tuning workflow

1. Get the real slow query (`pg_stat_statements`, slow query log `log_min_duration_statement`, app logs).
2. `EXPLAIN (ANALYZE, BUFFERS)` on realistic data volume (an empty dev DB lies).
3. Find the most expensive node, check estimated vs actual rows.
4. Fix: statistics, index, rewrite the query, or schema. Change **one thing at a time**.
5. Re-run and compare. Run twice to warm the cache.
6. Verify the index is not hurting writes and is actually used (`pg_stat_user_indexes.idx_scan`).

Test setup used in the examples:

```sql
CREATE TABLE customers (id bigserial PRIMARY KEY, email text NOT NULL, country text);
CREATE TABLE orders (
  id bigserial PRIMARY KEY, customer_id bigint NOT NULL, status text NOT NULL,
  total numeric(10,2) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), note text);
-- ~10k customers, ~1M orders
INSERT INTO customers (email, country)
  SELECT 'user' || g || '@mail.com', (ARRAY['FR','TN','DE','US'])[1 + g % 4] FROM generate_series(1, 10000) g;
INSERT INTO orders (customer_id, status, total, created_at)
  SELECT 1 + (random() * 9999)::int,
         (ARRAY['NEW','PAID','SHIPPED','CANCELLED'])[1 + (random() * 3)::int],
         (random() * 500)::numeric(10,2),
         now() - (random() * interval '730 days')
  FROM generate_series(1, 1000000);
ANALYZE;
```

---

## Worked examples

### Example 1: Missing index (Seq Scan)

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
```

```text
Gather  (cost=1000.00..15200.00 rows=100 width=60) (actual time=0.5..48.2 rows=98 loops=1)
  Workers Planned: 2
  ->  Parallel Seq Scan on orders  (cost=0.00..14190.00 rows=42 width=60) (actual time=8.1..44.0 rows=33 loops=3)
        Filter: (customer_id = 42)
        Rows Removed by Filter: 333300
        Buffers: shared hit=8200
Execution Time: 48.4 ms
```

Reading: 1M rows read to return 98 (`Rows Removed by Filter: 333300` × 3 workers). Fix:

```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);
```

```text
Bitmap Heap Scan on orders  (cost=5.2..380.0 rows=100 width=60) (actual time=0.05..0.19 rows=98 loops=1)
  Recheck Cond: (customer_id = 42)
  ->  Bitmap Index Scan on idx_orders_customer  (actual time=0.03..0.03 rows=98 loops=1)
        Index Cond: (customer_id = 42)
Execution Time: 0.25 ms
```

48 ms → 0.25 ms. In production use `CREATE INDEX CONCURRENTLY` to avoid blocking writes.

### Example 2: Composite index, column order matters

```sql
SELECT * FROM orders WHERE status = 'PAID' AND created_at >= now() - interval '7 days' ORDER BY created_at DESC LIMIT 20;
```

Rule of thumb: **equality columns first, then the range/sort column**.

```sql
CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);
```

```text
Limit  (actual time=0.03..0.09 rows=20 loops=1)
  ->  Index Scan using idx_orders_status_created on orders  (actual time=0.03..0.08 rows=20 loops=1)
        Index Cond: ((status = 'PAID') AND (created_at >= ...))
```

No `Sort` node: the index already delivers rows in the requested order, and `LIMIT` stops after 20 rows. With the columns reversed `(created_at, status)` the index could not be used this efficiently: `status` would only be a filter inside a range scan.
A composite index `(a, b)` serves `WHERE a`, `WHERE a AND b`, but **not** `WHERE b` alone (leftmost-prefix rule).

### Example 3: Function on a column kills the index (sargability)

```sql
SELECT * FROM customers WHERE lower(email) = 'user42@mail.com';
```

```text
Seq Scan on customers  (actual time=0.02..6.1 rows=1 loops=1)
  Filter: (lower(email) = 'user42@mail.com')
  Rows Removed by Filter: 9999
```

A plain index on `email` cannot be used because the query does not compare `email`, it compares `lower(email)`. Two fixes:

```sql
-- A) rewrite so the column is bare (only if the data is already normalised)
WHERE email = 'user42@mail.com'
-- B) index the expression
CREATE INDEX idx_customers_email_lower ON customers (lower(email));
```

Same trap: `WHERE created_at::date = '2026-01-01'` (use `created_at >= '2026-01-01' AND created_at < '2026-01-02'`), `WHERE col + 1 = 10`, `WHERE col LIKE '%abc'` (leading wildcard; use `pg_trgm` GIN index), and implicit casts (`WHERE varchar_col = 123`).

### Example 4: Covering index → Index Only Scan

```sql
SELECT customer_id, total FROM orders WHERE customer_id = 42;
```

With `idx_orders_customer` the plan still visits the table for `total`. Add the column with `INCLUDE`:

```sql
CREATE INDEX idx_orders_customer_total ON orders (customer_id) INCLUDE (total);
```

```text
Index Only Scan using idx_orders_customer_total on orders  (actual time=0.03..0.06 rows=98 loops=1)
  Index Cond: (customer_id = 42)
  Heap Fetches: 0
  Buffers: shared hit=4
```

Tradeoff: bigger index, slower writes. Do it for hot read paths only. `SELECT *` defeats this, select only the columns you need.

### Example 5: Wrong join strategy from bad estimates

```sql
SELECT c.email, sum(o.total)
FROM customers c JOIN orders o ON o.customer_id = c.id
WHERE c.country = 'TN' AND o.created_at >= now() - interval '30 days'
GROUP BY c.email;
```

Bad plan symptom:

```text
Nested Loop  (cost=... rows=5) (actual time=... rows=41000 loops=1)
  ->  Seq Scan on customers c  (rows=5) (actual rows=2500 ...)
  ->  Index Scan using idx_orders_customer on orders o  (actual time=0.02..0.30 rows=16 loops=2500)
```

`rows=5` estimated vs `rows=2500` actual = the planner was wrong, so it picked a Nested Loop. What to do, in order:

```sql
ANALYZE customers;                                            -- 1. refresh stats
ALTER TABLE customers ALTER COLUMN country SET STATISTICS 500; -- 2. finer histogram
CREATE STATISTICS s_cust (dependencies) ON country, id FROM customers; -- 3. correlated columns
CREATE INDEX idx_orders_created ON orders (created_at, customer_id);   -- 4. help the big side
```

Once estimates are correct the planner typically switches to `Hash Join`, which is far better when both sides are large. Do not force join types with `SET enable_nestloop = off` in production, only use it as a diagnostic to see what the alternative costs.

### Example 6: Pagination, OFFSET vs keyset

```sql
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 500000;
```

```text
Limit  (actual time=95.0..95.1 rows=20 loops=1)
  ->  Index Scan using orders_pkey on orders  (actual time=0.02..80.0 rows=500020 loops=1)
```

`OFFSET` reads and discards 500 000 rows. Cost grows with the page number. Keyset (seek) pagination:

```sql
SELECT * FROM orders WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```

```text
Limit  (actual time=0.02..0.05 rows=20 loops=1)
  ->  Index Scan using orders_pkey on orders  (actual time=0.02..0.04 rows=20 loops=1)
        Index Cond: (id > 500000)
```

95 ms → 0.05 ms, constant for any page. For non-unique sort columns use a tuple: `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC` with an index on `(created_at DESC, id DESC)`.

### Example 7: Partial index (index only what you query)

```sql
-- 95% of rows are SHIPPED/CANCELLED, the app only polls NEW orders
CREATE INDEX idx_orders_new ON orders (created_at) WHERE status = 'NEW';
SELECT * FROM orders WHERE status = 'NEW' ORDER BY created_at LIMIT 50;
```

Small index, cheap to maintain. The query's `WHERE` must imply the index predicate (same literal `status = 'NEW'`, a bind parameter may prevent it with generic plans).

### Example 8: Sort spilling to disk

```text
Sort  (actual time=1200..1450 rows=1000000 loops=1)
  Sort Key: created_at
  Sort Method: external merge  Disk: 61240kB
```

Options: add an index that provides the order, add a `LIMIT`, reduce columns, or raise `work_mem` **for that session/transaction**:

```sql
SET LOCAL work_mem = '128MB';   -- inside a transaction, don't raise it globally (it is per sort/hash node per connection)
```

Goal: `Sort Method: quicksort  Memory: 25kB` (or `top-N heapsort` with `LIMIT`).

### Example 9: N+1 seen from the database

Symptom in `pg_stat_statements`: the same tiny query with `calls` = 100 000. Each plan is perfect (0.05 ms) but the total is huge (5 s). `EXPLAIN` cannot fix this, fix the caller:

```sql
-- instead of: SELECT * FROM orders WHERE customer_id = ?   (× N)
SELECT * FROM orders WHERE customer_id = ANY(:ids);
```

In JPA/Hibernate: `JOIN FETCH`, `@EntityGraph`, or `@BatchSize`.

---

### Useful companions

```sql
-- top queries by total time (needs CREATE EXTENSION pg_stat_statements)
SELECT calls, round(total_exec_time::numeric,0) AS total_ms, round(mean_exec_time::numeric,2) AS mean_ms, left(query,80)
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;

-- unused indexes (write cost with no read benefit)
SELECT relname, indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;

-- stale stats / dead rows
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
```

Diagnostics only (never leave on in prod): `SET enable_seqscan = off;` shows whether the planner *can* use your index and what it would cost.

Tools: [explain.dalibo.com](https://explain.dalibo.com), [explain.depesz.com](https://explain.depesz.com): paste a plan, get the slowest node highlighted.
