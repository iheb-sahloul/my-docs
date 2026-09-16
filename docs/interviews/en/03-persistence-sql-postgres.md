# Persistence & SQL

## 🟢 Fundamentals

### Q1. When would you choose JPA/Hibernate, plain JDBC, or MyBatis?
**Answer:** JPA/Hibernate is the default for typical CRUD-heavy applications: you get object-relational
mapping, a repository abstraction, derived query methods, and don't hand-write SQL for common
cases. Plain JDBC (via `JdbcTemplate`) is lower-level but avoids ORM machinery entirely — useful
for simple, high-performance paths or when the ORM's generated SQL is the problem, not the
solution. MyBatis sits between the two: you write the SQL yourself (full control over the exact
query, easy to tune) but MyBatis handles parameter binding and mapping the result set back to
objects — it's the common choice when queries are complex, performance-critical, or need to use
database-specific features the ORM abstracts away.

**Example:**
```java
// JPA/Hibernate: derived query, no SQL written at all.
public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByCustomerIdAndStatus(Long customerId, String status);
}

// Plain JDBC via JdbcTemplate: full control, minimal abstraction.
List<Order> orders = jdbcTemplate.query(
    "select * from orders where customer_id = ? and status = ?",
    (rs, rowNum) -> mapOrder(rs), customerId, status);

// MyBatis: SQL you write, mapping MyBatis handles.
@Select("select * from orders where customer_id = #{customerId} and status = #{status}")
List<Order> findByCustomerAndStatus(@Param("customerId") Long customerId, @Param("status") String status);
```

**Why it's a trap:** "always use JPA, it's the standard" skips the case that actually shows up in
practice — a reporting query with a window function, a database-specific hint, or a hand-tuned
join that Hibernate would never generate on its own. Knowing when to *not* reach for the ORM is
part of the answer, not a concession.

### Q2. What is an ORM, and what problem does it actually solve?
**Answer:** An ORM (Object-Relational Mapper) bridges the "impedance mismatch" between the relational model
(tables, rows, foreign keys) and the object model (classes, references, inheritance) — mapping
rows to objects, foreign keys to object references/collections, and translating object-graph
navigation into SQL joins or additional queries. It solves the tedium and error-proneness of
hand-writing that mapping code for every entity, at the cost of sometimes generating SQL that's
less efficient than a hand-written query for a specific case (see the N+1 problem, Q8).

**Example:**
```java
@Entity
class Order {
    @Id Long id;
    @ManyToOne Customer customer;       // foreign key -> object reference
    @OneToMany(mappedBy = "order") List<LineItem> items; // join -> collection navigation
}

order.getCustomer().getName();  // looks like a field access...
order.getItems().size();        // ...but each of these can silently trigger its own SQL query
```

**Why it's a trap:** treating the ORM as "no SQL knowledge required" is the surface-level answer —
the abstraction is real, but it leaks exactly where performance matters, and the two lines above
are precisely where the N+1 problem (Q8) is born.

### Q3. What's the difference between a primary key, a unique constraint, and an index?
**Answer:** A primary key uniquely identifies each row, is implicitly `NOT NULL`, and a table has at most
one; it also implicitly creates an index to enforce and speed up that uniqueness. A unique
constraint enforces uniqueness on one or more columns but allows `NULL` (and typically allows
multiple `NULL`s, since `NULL` isn't considered equal to another `NULL`) — a table can have
several. An index is purely a data structure for fast lookup on a column (or columns) and
doesn't enforce anything by itself; primary keys and unique constraints happen to create indexes
as a side effect of enforcing their constraint, but you can also create an index with no
uniqueness constraint at all, purely for query speed.

**Example:**
```sql
create table users (
    id bigint primary key,               -- unique + NOT NULL, index created automatically
    email varchar(255) unique,           -- unique, but NULL allowed (and more than one NULL)
    last_login timestamp
);

create index idx_users_last_login on users(last_login); -- pure lookup speed, no constraint at all

insert into users (id, email) values (1, null); -- ok
insert into users (id, email) values (2, null); -- also ok — two NULLs don't violate uniqueness
```

**Why it's a trap:** assuming a unique constraint behaves exactly like a primary key including
`NULL` handling — if the business rule actually needs "at most one row with a *missing* email"
to be enforced too, a plain unique constraint won't do it; that needs an explicit condition or a
different modeling choice, not blind reliance on the constraint's default `NULL` semantics.

### Q4. Walk through normalizing a table from 1NF to 3NF.
**Answer:** Given a flat `Orders` table with columns `order_id, customer_name, customer_email, product_name,
product_price, quantity`: **1NF** requires atomic values and no repeating groups — if a column
stored a comma-separated list of products per order, splitting it into one row per product line
item is the 1NF step. **2NF** requires every non-key column to depend on the *whole* primary
key, not part of it — if the key is `(order_id, product_id)` but `customer_name` only depends on
`order_id`, that's a partial dependency; move customer data to its own `Customers` table keyed
by `customer_id`. **3NF** requires removing transitive dependencies — if `product_price` in the
order line depends on `product_id`, which depends on the order line's key only transitively
through the product, move `product_name`/`product_price` to their own `Products` table too. The
end state: `Orders`, `Customers`, `Products`, and an `OrderItems` junction table, each column
depending only on its own table's full key.

**Example:**
```sql
-- Before (1NF violation): products stored as a repeating group in one column.
-- order_id | customer_name | customer_email | products
-- 1        | Ann           | ann@x.com      | "Widget,Gadget"

-- After 3NF:
create table customers (customer_id bigint primary key, name text, email text);
create table products  (product_id  bigint primary key, name text, price numeric);
create table orders    (order_id    bigint primary key, customer_id bigint references customers);
create table order_items (
    order_id   bigint references orders,
    product_id bigint references products,
    quantity   int,
    primary key (order_id, product_id)
);
```

**Why it's a trap:** "more tables is always better" is the wrong takeaway — normalization exists to
remove update/insert/delete anomalies, not as a goal in itself; a read-heavy path that pays for a
four-table join on every request because of textbook normalization, when the data barely
changes, is exactly the case where deliberate denormalization (Q25) is the more senior call.

### Q5. What do the ACID properties actually guarantee?
**Answer:** **Atomicity**: a transaction's operations all succeed or all roll back together, no partial
application. **Consistency**: a transaction moves the database from one valid state to another,
respecting constraints (foreign keys, unique constraints, check constraints). **Isolation**:
concurrent transactions don't see each other's uncommitted intermediate state, to a degree
controlled by the isolation level (Q15). **Durability**: once committed, a transaction's changes
survive a crash — typically via a write-ahead log flushed before the commit is acknowledged.

**Example:**
```sql
begin;
update accounts set balance = balance - 100 where id = 1;
update accounts set balance = balance + 100 where id = 2;
-- If the process crashes here, atomicity guarantees neither update survives on restart.
commit; -- durability guarantees both updates survive any crash from this point on.
```

**Why it's a trap:** the "C" is the one candidates misstate — it doesn't mean "my business logic
is correct," it means the database enforces the constraints it was explicitly told about
(foreign keys, checks, uniqueness). A transaction can be fully ACID-compliant and still leave
data in a state that violates an invariant the schema never declared — that gap is an
application bug, not something ACID was ever promising to catch.

## 🟡 Senior traps

### Q6. What is the logical execution order of a SQL query's clauses — and why can't you filter on a `SELECT` alias in `WHERE`?
**Answer:** `FROM`/`JOIN` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `DISTINCT` → `ORDER BY` →
`LIMIT`/`OFFSET`. This is the logical processing order the engine reasons about, not the order
you physically type the clauses in. The trap: trying to filter on a column alias defined in
`SELECT` from within `WHERE` fails in most databases, precisely because `WHERE` is logically
evaluated *before* `SELECT` — the alias doesn't exist yet at that point in logical execution.
`ORDER BY`, by contrast, runs after `SELECT` and so *can* reference a `SELECT` alias.

**Example:**
```sql
select price * quantity as line_total
from order_items
where line_total > 100;   -- ERROR: column "line_total" does not exist — WHERE runs before SELECT

select price * quantity as line_total
from order_items
order by line_total desc; -- fine — ORDER BY runs after SELECT, the alias already exists

select price * quantity as line_total
from order_items
where price * quantity > 100; -- the actual fix: repeat the expression, don't rely on the alias
```

**Why it's a trap:** candidates who've memorized "you can't use a `SELECT` alias in `WHERE`" as a
rule rarely know *why* — and the same underlying order is what makes `HAVING` (Q7) work where
`WHERE` can't, and why a window function can't appear in `WHERE` either. It's one mental model,
not three unrelated syntax rules to memorize separately.

### Q7. Why can you filter on an aggregate function in `HAVING` but not in `WHERE`?
**Answer:** Because `WHERE` is evaluated before grouping/aggregation happens (per Q6's order), so aggregate
values like `COUNT(*)` or `SUM(x)` don't exist yet at that stage of processing — there's nothing
to filter on. `HAVING` runs after `GROUP BY`, once aggregates have actually been computed per
group, so it's the correct place to filter on them (`HAVING COUNT(*) > 5`). `WHERE` still filters
individual rows before grouping; `HAVING` filters groups after grouping — using the wrong one
either fails outright or, worse, silently computes something different from what was intended.

**Example:**
```sql
select customer_id, count(*) as order_count
from orders
where count(*) > 5   -- ERROR: aggregate functions are not allowed in WHERE
group by customer_id;

select customer_id, count(*) as order_count
from orders
group by customer_id
having count(*) > 5; -- correct: filters groups, evaluated after the aggregate is computed
```

**Why it's a trap:** the failure isn't always a clean syntax error a candidate can just fix and
move on — mixing up which clause narrows *rows* versus which narrows *groups* can produce a query
that runs and returns a plausible-looking but silently wrong number, which is a much worse
production bug than one that fails loudly at query time.

### Q8. What's the N+1 query problem, and name two ways to fix it.
**Answer:** Fetching a list of N parent entities, then lazily triggering one additional query *per* parent
to fetch an associated collection (e.g. loading 50 orders, then triggering 50 separate queries
to fetch each order's line items) — 1 query becomes N+1, and it scales linearly with result set
size in the worst possible way. Fixes: (1) a JOIN FETCH in JPQL (or an explicit join in MyBatis/
JDBC) to pull the association in the same query as the parent; (2) `@EntityGraph` in Spring Data
JPA to declare which associations to eagerly fetch for a specific query method, without changing
the entity's default fetch type globally. Batch fetching (`@BatchSize` / Hibernate's default
batch fetch config) is a third, coarser fix — it doesn't eliminate the extra queries but groups
them into far fewer round trips.

**Example:**
```java
// N+1: one query for orders, then one more query per order for its items.
List<Order> orders = orderRepository.findAll();
orders.forEach(o -> o.getItems().size()); // triggers a lazy-load query, once per order

// Fix 1: JOIN FETCH pulls items in the same query as the parent.
@Query("select o from Order o join fetch o.items")
List<Order> findAllWithItems();

// Fix 2: @EntityGraph scopes the eager fetch to this query method only.
@EntityGraph(attributePaths = "items")
List<Order> findAll();
```

**Why it's a trap:** the tempting "fix" is flipping the association to `FetchType.EAGER` on the
entity itself — that resolves this one query, but now *every* other query touching that entity
eagerly pulls the association too, and stacking two eager collections on the same entity produces
a cartesian-product join that can be far worse than the N+1 it replaced.

### Q9. Explain optimistic vs. pessimistic locking in terms of actual contention, not just the definitions.
**Answer:** Pessimistic locking acquires a database-level lock (`SELECT ... FOR UPDATE`) the moment a row is
read for update, blocking any other transaction from modifying (sometimes even reading) it until
the first transaction commits or rolls back — correct under high contention on the same rows,
but it serializes access and can create lock waits or deadlocks under load. Optimistic locking
adds a version column (`@Version`) and checks at commit time whether the row's version still
matches what was read — if another transaction updated it in between, the commit fails with an
`OptimisticLockException` instead of blocking anyone. It scales much better under *low*
contention (no locks held at all while the user is "thinking"), but under genuinely high
contention on the same rows, it just moves the cost from blocking to a high rate of failed
commits that must be retried — at some contention level, pessimistic locking is actually the
better throughput choice, not the naively "worse" option.

**Example:**
```java
// Pessimistic: blocks any other transaction from touching this row until commit/rollback.
Account acct = em.createQuery("select a from Account a where a.id = :id", Account.class)
    .setParameter("id", id)
    .setLockMode(LockModeType.PESSIMISTIC_WRITE)
    .getSingleResult();

// Optimistic: no lock held; fails at commit if the version changed underneath it.
@Entity
class Account {
    @Version private long version;
    private BigDecimal balance;
}
// ... read, mutate, save — on flush, an OptimisticLockException means someone else won the race
```

**Why it's a trap:** candidates recite "optimistic is better because it doesn't block" as a
universal rule — a senior answer names the crossover point: under genuinely high contention on a
small set of hot rows (see S9), optimistic locking's retry storm can cost more than the blocking
pessimistic locking would have, and picking one over the other should follow from the actual
access pattern, not a blanket preference.

### Q10. Name the four Hibernate entity states, with a usage example for each.
**Answer:** **Transient**: a plain `new Entity()`, not associated with any persistence context and not
represented in the database — `new Order()` before `save()`. **Persistent** (managed): attached
to an active persistence context; changes to it are automatically tracked and flushed to the DB
at commit/flush time without an explicit `save()` call — an entity returned by
`entityManager.find()` inside an open session. **Detached**: was persistent, but its persistence
context has closed (e.g. the transaction ended, or it was explicitly `.detach()`ed) — its
identity still maps to a DB row, but changes to it are no longer tracked; re-attaching it via
`merge()` is a common source of subtle bugs if the caller doesn't realize a stale detached copy
is being merged over newer data. **Removed**: marked for deletion within the current persistence
context via `entityManager.remove()`, deleted from the DB on flush/commit, but the Java object
itself still exists in memory until garbage collected.

**Example:**
```java
Order order = new Order();          // transient — not tracked, not in the DB
em.persist(order);                  // persistent — now managed, dirty-checked automatically
order.setStatus("SHIPPED");         // no explicit save() needed — flushed at commit

em.close();                         // order is now detached — changes no longer tracked
order.setStatus("CANCELLED");       // silently untracked; nothing happens until merge()
Order merged = em.merge(order);     // re-attaches — but overwrites the DB row with this object's
                                     // field values, even if the DB row changed since detach

em.remove(merged);                  // removed — deleted on flush/commit, object still exists in JVM
```

**Why it's a trap:** the state candidates get wrong is **detached** — assuming `merge()` safely
"syncs" the object, when it actually overwrites the current DB row with the detached object's
field values wholesale. If another transaction updated that row after this object was detached,
`merge()` silently discards that newer write with no conflict detection, unless `@Version` (Q9)
is also in play to catch it.

### Q11. How does MyBatis's approach to persistence differ from JPA/Hibernate's, and when is that difference the deciding factor?
**Answer:** JPA/Hibernate is a full ORM: you declare entity mappings and let Hibernate generate SQL, manage
a persistence context with dirty-checking, and handle caching/lazy-loading transparently — which
is powerful but means the actual SQL executed is somewhat indirect and can surprise you (N+1,
unexpected joins). MyBatis is a SQL mapper, not a full ORM: you write the SQL (or a fairly thin
XML/annotation-based template of it) explicitly, and MyBatis's job is purely binding parameters
in and mapping result columns back to objects — there's no persistence context, no automatic
dirty-checking, no hidden queries. The deciding factor in practice: reach for MyBatis when
queries are complex, need database-specific tuning, or when a team explicitly wants to see and
control every SQL statement executed (common in performance-sensitive or legacy-schema
environments where the ORM's generated SQL would be a liability, not a convenience).

**Example:**
```java
// JPA: the actual SQL is generated by Hibernate — dirty-checking happens for free.
Order order = em.find(Order.class, id);
order.setStatus("SHIPPED"); // no explicit update statement written anywhere — flushed at commit

// MyBatis: the SQL is explicit and visible; no hidden dirty-checking or session cache.
@Update("update orders set status = #{status} where id = #{id}")
void updateStatus(@Param("id") Long id, @Param("status") String status);
```

**Why it's a trap:** "MyBatis has no ORM overhead so it's always faster" oversimplifies the
comparison — much of what a JPA persistence context buys you for free (dirty-checking, avoiding a
duplicate query for an entity already loaded in this transaction) is work a MyBatis-based
codebase has to hand-roll if the use case genuinely needs it. The right choice is about how much
control over the exact SQL the team needs, not a blanket performance verdict.

### Q12. How do you configure and safely route to multiple data sources in one Spring application?
**Answer:** Define each `DataSource` as its own `@Bean`, mark the default one `@Primary`, bind each to its
own configuration prefix, and — critically for correctness, not just wiring — configure separate
`EntityManagerFactory`/`TransactionManager` beans per data source if they're genuinely
independent databases, since a single `@Transactional` boundary can't atomically span two
physically separate databases (no distributed 2-phase-commit by default). The senior trap here is
assuming `@Transactional` gives atomicity across both data sources the way it does within one —
it doesn't, unless a distributed transaction manager (JTA/XA) is explicitly configured, which
most teams avoid due to its operational cost and instead design around the constraint (e.g. only
one data source is ever the "source of truth" for a given write).

**Example:**
```java
@Bean @Primary
DataSource ordersDataSource() { return DataSourceBuilder.create().build(); }

@Bean
DataSource billingDataSource() { return DataSourceBuilder.create().build(); }

@Transactional // this boundary only covers ONE of the two data sources' work at a time
void processOrder() {
    ordersRepository.save(order);      // committed against ordersDataSource's transaction manager
    billingRepository.save(invoice);   // a SEPARATE, independently-committed transaction —
                                        // if this throws, the order above is not rolled back
}
```

**Why it's a trap:** assuming `@Transactional` gives cross-database atomicity the same way it
does within a single data source — without an explicit JTA/XA transaction manager, a failure on
the second write leaves the first one committed, and no annotation in this code silently fixes
that; the fix is a design decision (idempotent retries, a saga, or a single source of truth), not
a missing configuration flag.

### Q13. What index types does PostgreSQL offer beyond the default B-tree, and when do you reach for each?
**Answer:** B-tree (the default) handles equality and range queries (`=`, `<`, `>`, `BETWEEN`, sorting) and
covers the large majority of cases. GIN (Generalized Inverted Index) indexes composite/multi-
valued data — full-text search `tsvector` columns, array containment (`@>`), and specifically
`JSONB` columns for containment/key-existence queries (`jsonb_column @> '{"key": "value"}'`),
which a B-tree can't usefully index. GiST supports geometric/range-overlap queries. A **partial
index** (`CREATE INDEX ... WHERE status = 'active'`) indexes only rows matching a condition —
much smaller and faster than a full index when queries always filter to a small, well-defined
subset of a large table (e.g. only "active" rows out of a mostly-archived table).

**Example:**
```sql
create index idx_orders_created_at on orders(created_at);                 -- B-tree: default
create index idx_products_attrs   on products using gin (attributes);     -- GIN: JSONB containment
create index idx_bookings_period  on bookings using gist (during);        -- GiST: range overlap
create index idx_orders_active    on orders(customer_id) where status = 'active'; -- partial
```

**Why it's a trap:** reaching for a GIN index on every `JSONB` column "just in case" ignores that
GIN indexes are notably more expensive to maintain on writes than a B-tree — blanket-applying one
without checking the actual query pattern trades away write throughput for a lookup speed nobody
asked for on that column.

### Q14. How do you read `EXPLAIN ANALYZE` output to diagnose a slow query?
**Answer:** `EXPLAIN ANALYZE` actually runs the query and shows the real execution plan with actual row
counts and timing per step, nested innermost-first. The first thing to check: `Seq Scan` (full
table scan) on a large table where an `Index Scan` was expected — usually means a missing index,
a function applied to the indexed column preventing index use (`WHERE lower(email) = ...`
without a matching functional index), or the planner's cost estimate genuinely favoring a scan
(common when selectivity is poor — the filter doesn't actually narrow down many rows). Second:
compare the planner's estimated row count against the actual row count at each step — a large
mismatch means outdated table statistics (`ANALYZE` needs to run) misleading the planner into a
bad plan choice. Third: look for `Nested Loop` over a large outer set — often the plan shape
behind an N+1-like problem at the SQL level itself.

**Example:**
```
Seq Scan on orders  (cost=0.00..48123.00 rows=1 width=64) (actual time=0.02..412.55 rows=980000 loops=1)
  Filter: (customer_id = 42)
  Rows Removed by Filter: 19020000
Planning Time: 0.15 ms
Execution Time: 415.10 ms
```
A `Seq Scan` scanning 20 million rows to return 980,000 that match a single `customer_id`, with
the planner having estimated only 1 row — that estimate-vs-actual gap points straight at stale
statistics, and the full scan itself points at a missing index on `customer_id`.

**Why it's a trap:** `EXPLAIN` without `ANALYZE` shows only the planner's *estimated* cost and row
counts — it never actually runs the query. Quoting those numbers as if they were real measured
timings is the giveaway that a candidate hasn't actually run and read a real `ANALYZE` plan
against production-scale data.

### Q15. Name the transaction isolation levels and the anomalies each one prevents.
**Answer:** From loosest to strictest: **Read Uncommitted** prevents nothing (dirty reads possible; rarely
used, PostgreSQL treats it identically to Read Committed). **Read Committed** (PostgreSQL's
default) prevents dirty reads (never sees another transaction's uncommitted changes) but allows
non-repeatable reads (re-reading the same row within a transaction can see a different, now-
committed value) and phantom reads (a repeated range query can return different rows).
**Repeatable Read** additionally prevents non-repeatable reads by taking a consistent snapshot
for the whole transaction — in PostgreSQL specifically, this also prevents phantom reads (unlike
the SQL standard's minimum guarantee), though at the cost of possible serialization failures
under write conflicts that must be retried. **Serializable** guarantees the outcome is
equivalent to *some* serial (one-at-a-time) execution of all concurrent transactions — the
strongest guarantee, at the highest cost in contention and retry rate.

**Example:**
```sql
-- Session A (Read Committed, PostgreSQL's default)
begin;
select balance from accounts where id = 1; -- returns 100

-- Session B, commits concurrently
update accounts set balance = 50 where id = 1;
commit;

-- back in Session A, same transaction:
select balance from accounts where id = 1; -- returns 50 — a non-repeatable read
commit;
```

**Why it's a trap:** treating "higher isolation is strictly safer" as the rule ignores the
throughput cost — defaulting every transaction to `SERIALIZABLE` "to be safe" trades a specific,
understood anomaly for a much higher rate of serialization failures that now every code path must
retry, which is often a worse production outcome than the anomaly it was meant to avoid.

### Q16. How do you size a HikariCP connection pool, and what's the common sizing mistake?
**Answer:** The common mistake is sizing the pool far larger than needed, on the intuition that "more
connections = more throughput" — in reality, past a certain point (roughly tied to the database
server's own CPU core count and its ability to context-switch between active queries), adding
more connections adds contention on the database side and *reduces* throughput, not increases
it. HikariCP's own guidance, based on the PostgreSQL wiki's formula, is roughly
`connections = ((core_count * 2) + effective_spindle_count)` as a starting point for the
*database server's total* connection budget, divided across however many application instances
share it — not per-instance. The practical rule: start smaller than intuition suggests, load-test
to find the actual throughput-maximizing pool size, and remember every application instance's
pool competes for the same database-side connection budget.

**Example:**
```yaml
# The reflexive "fix" for a timeout complaint — often makes things worse, not better:
spring.datasource.hikari.maximum-pool-size: 200  # on a DB with 8 cores

# Right-sized starting point per instance, derived from the DB's actual core count
# and divided across the number of instances sharing that database:
spring.datasource.hikari.maximum-pool-size: 10
```

**Why it's a trap:** "just raise `maximum-pool-size`" is the reflexive fix for any
slow-query-under-load complaint — past the database's actual concurrency sweet spot, adding
connections adds context-switching and lock contention on the server, making latency *worse*, not
better, which is the opposite of what the change was meant to achieve.

### Q17. What's the safe process for a schema migration in a production database, and what tools manage this?
**Answer:** Flyway and Liquibase are the standard tools — each migration is a versioned, tracked script
(SQL or, for Liquibase, also XML/YAML) applied in order and recorded in a migrations-history
table, so the schema's current state is always derivable and repeatable across environments. The
safe process for a breaking-shaped change (renaming a column, adding a `NOT NULL` constraint)
is to break it into multiple deployable, backward-compatible steps rather than one migration:
add the new column nullable, deploy application code that writes to both old and new, backfill
existing rows, deploy code that reads only from the new column, then drop the old column in a
final migration — at every intermediate step, both the old and new application version can run
against the current schema, which is what makes a zero-downtime rolling deployment possible.

**Example:**
```sql
-- V1: additive, safe on a live table with any Postgres version
alter table users add column email_normalized text;

-- Application deploy: writes email_normalized on every write, reads still use the old column.

-- V2: backfill in batches (see Q20/S12), not one giant UPDATE.
-- Application deploy: reads switch to email_normalized.

-- V3, once fully cut over:
alter table users drop column email;
```

**Why it's a trap:** the "obvious" single migration — add the `NOT NULL` column directly in one
step — often runs fine against a small staging database with light load, then locks or fails
against production simply because production has orders of magnitude more rows and concurrent
traffic staging never had; the multi-step pattern isn't extra caution, it's the only version that
scales to production's actual size and concurrency.

### Q18. Why does column order matter in a composite (multi-column) index?
**Answer:** A B-tree composite index on `(a, b)` is physically sorted by `a` first, then `b` within each `a`
value — so it can efficiently serve a query filtering on `a` alone, or on `a` and `b` together,
but it's largely useless for a query filtering on `b` alone (the index has no useful ordering by
`b` in isolation, forcing a full scan of the index or the table). The rule of thumb: put the
column with equality filters and highest selectivity (narrows results the most) first, and
columns used for range filters or that are frequently queried without the other columns should
generally come later or get their own separate index — and always check with `EXPLAIN` rather
than assuming, since the right order also depends on actual query patterns.

**Example:**
```sql
create index idx_orders_customer_status on orders(customer_id, status);

-- Uses the index efficiently — filters on the leading column:
select * from orders where customer_id = 42;
select * from orders where customer_id = 42 and status = 'PENDING';

-- Can't use this index efficiently — status is not the leading column:
select * from orders where status = 'PENDING';
```

**Why it's a trap:** "just add a composite index on every column the query filters on" without
checking column order against the actual query shape produces an index that silently doesn't
serve the query it was added for — `EXPLAIN` still shows a `Seq Scan`, and the index just sits
there paying its write cost for nothing.

### Q19. When should a column be `JSONB` versus a properly normalized set of tables?
**Answer:** `JSONB` is appropriate for genuinely semi-structured, sparse, or schema-varying data — a
"custom attributes" bag on a product that varies wildly by category, or an audit log's payload
that isn't queried structurally, only stored and occasionally retrieved whole. It's a poor fit
for data with a stable, well-known structure that's frequently queried, filtered, joined, or
aggregated by individual fields — at that point, normalized columns are both faster (a proper
B-tree on a real column beats even a GIN-indexed JSONB key lookup for most access patterns) and
give you real referential integrity (foreign keys, `NOT NULL`, `CHECK` constraints) that JSONB
can't enforce at the database level. The trap to watch for in review: reaching for JSONB because
it's convenient during early development, then still having it in a hot, frequently-filtered
path a year later with a GIN index papering over what should have been a normalized column from
the start.

**Example:**
```sql
-- Fine: genuinely sparse, schema-varying, rarely filtered structurally.
create table products (
    id bigint primary key,
    custom_attributes jsonb -- varies wildly per category, mostly just stored/retrieved whole
);

-- Poor fit: stable structure, filtered/joined constantly — should be real columns instead.
select * from orders where payload @> '{"status": "SHIPPED", "region": "EU"}'; -- vs:
select * from orders where status = 'SHIPPED' and region = 'EU'; -- normalized, indexable, constrained
```

**Why it's a trap:** reaching for `JSONB` because it's convenient during early development, and
never revisiting that decision once the field becomes a stable, frequently-filtered column, is
how a GIN index ends up papering over what should have been a normalized column with a real
foreign key and `NOT NULL` constraint from the start.

### Q20. Why are ORM-generated inserts/updates often slow in bulk, and how do you fix it?
**Answer:** By default, most ORMs issue one `INSERT`/`UPDATE` statement per entity, in a loop — for a batch
of 10,000 rows, that's 10,000 round trips (or 10,000 statements even if pipelined), each paying
per-statement overhead. Fixes: enable Hibernate's batch settings
(`hibernate.jdbc.batch_size`, plus `order_inserts`/`order_updates` so same-table statements are
grouped for the batch to actually apply), which coalesces multiple statements into fewer network
round trips using JDBC's batch API; or bypass the ORM for genuinely bulk operations and use a
native multi-row `INSERT ... VALUES (...), (...), (...)` or Postgres's `COPY` command, which is
dramatically faster than even a well-batched ORM insert for large volumes.

**Example:**
```properties
# Enabling batch_size alone is not enough:
hibernate.jdbc.batch_size=50
# Without these, interleaved entity types in the persistence context break up the batches:
hibernate.order_inserts=true
hibernate.order_updates=true
```
```sql
-- Fastest path for genuinely bulk loads, bypassing the ORM entirely:
copy orders (id, customer_id, status) from stdin with (format csv);
```

**Why it's a trap:** setting `hibernate.jdbc.batch_size` alone and assuming that's the whole fix —
without `order_inserts`/`order_updates`, Hibernate still won't actually coalesce statements if
different entity types are interleaved in the persistence context (e.g. saving an `Order` then a
`Payment` then another `Order`), so the "batched" insert silently reverts to one-at-a-time
statements without the missing flag.

### Q21. What breaks when you naively add a read replica for scaling reads?
**Answer:** The obvious failure mode: **read-after-write inconsistency** — a client writes to the primary,
then immediately reads from a replica that hasn't received (or applied) that write yet due to
replication lag, and sees stale data, which is especially jarring for a user who just submitted
a form and reloads to see their own change missing. This shows up specifically in flows like
"create a resource, then redirect to its detail page" if the detail read is routed to a lagging
replica. Fixes: route reads that must be immediately consistent with a just-completed write back
to the primary (or to the same replica the write's session is pinned to), accept and design
around eventual consistency for reads that can tolerate it, or monitor replication lag and
route reads away from a replica that's fallen too far behind.

**Example:**
```java
Long orderId = orderService.create(request);  // write goes to the primary
return "redirect:/orders/" + orderId;

// The redirected GET, if routed to a lagging replica:
Order order = orderRepository.findById(orderId); // 404 or stale — replica hasn't caught up yet
```

**Why it's a trap:** "add a read replica" is treated as a purely upside scaling win with no
consistency cost attached — the first production incident from this is almost always exactly the
create-then-redirect flow above, discovered by a confused user rather than caught in review.

### Q22. Soft deletes vs. hard deletes — what's the actual trade-off?
**Answer:** Soft deletes (a `deleted_at` timestamp or `is_deleted` flag, with rows never physically removed)
preserve audit history, support "undo," and avoid foreign-key cascade surprises (see S15) —
but every single query in the codebase now must remember to filter out soft-deleted rows
(easy to forget, causing a soft-deleted row to leak back into results), unique constraints get
complicated (can a new row reuse an email that a soft-deleted row still holds?), and the table
grows unboundedly since nothing is ever actually removed. Hard deletes keep the table and its
constraints simple and enforce real space reclamation, at the cost of losing history and needing
a separate audit/archive mechanism if that history is actually required for compliance or
support. Many production systems land on a hybrid: soft delete for a retention window (supports
undo and audit for recent changes), followed by a scheduled job that hard-deletes rows past that
window.

**Example:**
```sql
-- Forgotten filter: a soft-deleted user leaks back into results.
select * from users where email = 'ann@example.com'; -- returns the "deleted" row too

-- A plain unique constraint blocks a new signup from reusing that email:
alter table users add constraint uq_users_email unique (email); -- still holds the deleted row's email

-- The actual fix for both: filter deleted rows explicitly, and scope uniqueness to live rows only.
create unique index uq_users_email_active on users(email) where deleted_at is null;
```

**Why it's a trap:** soft delete is often assumed to be the strictly "safer" default — but it
trades a class of bug a hard delete structurally can't have (forgetting the `deleted_at is null`
filter and leaking deleted data back into a query) for the audit/undo benefit, and a naive unique
constraint on an email column will silently block a legitimate re-signup unless it's explicitly
scoped to non-deleted rows.

## 🔴 Expert / Open

### Q23. Design the schema and indexing strategy for a high-write, append-heavy feed/event table expected to reach billions of rows.
**Answer:** Favor an append-only insert pattern (avoid updates where possible — updates on a huge table
fight with vacuum and bloat, see S14) and partition the table by time (native PostgreSQL range
partitioning on a timestamp column) so that queries scoped to a recent time window only touch
recent partitions, and old partitions can be dropped wholesale (instant, versus a slow `DELETE`
scanning billions of rows) once a retention policy expires them. Index deliberately and sparingly
— every additional index adds write cost on every insert, which matters enormously at this write
volume — typically just the columns actually used to filter feeds (`user_id`, `created_at`)
rather than every column that might theoretically be queried. Consider whether the read pattern
genuinely needs relational query flexibility at all, or whether a purpose-built time-series or
wide-column store is a better fit once relational indexing overhead becomes the bottleneck — the
senior-level answer recognizes that "keep scaling Postgres" and "the data model doesn't fit a
relational database at this shape anymore" are both legitimate answers depending on the actual
query patterns, not just the row count.

**Example:**
```sql
create table events (
    id bigint generated always as identity,
    user_id bigint not null,
    created_at timestamptz not null,
    payload jsonb
) partition by range (created_at);

create table events_2026_01 partition of events
    for values from ('2026-01-01') to ('2026-02-01');

create index on events (user_id, created_at); -- only the columns feeds are actually filtered by

-- Retention: instant, versus a DELETE that would scan billions of rows.
drop table events_2025_01;
```

**Why it's a trap:** over-indexing "just to be safe" on a table at this write volume is a genuine
mistake, not caution — every additional index is write-amplification paid on every single insert,
and at billions of rows, indexes that were never actually used by a real query pattern are pure
cost with no offsetting benefit.

### Q24. How do you safely add a `NOT NULL` column to a 50-million-row table with zero downtime?
**Answer:** Never add `NOT NULL` directly in one migration on a huge table under concurrent write load — in
older Postgres versions this would rewrite the entire table under an exclusive lock; even with
modern Postgres's improvements (adding a column with a constant default no longer rewrites the
table), adding `NOT NULL` still requires validating every existing row, which briefly locks the
table if done as one blocking step. Safe sequence: (1) add the column as nullable; (2) backfill
existing rows in small batches (to avoid one giant long-running transaction and to avoid
overwhelming replication/vacuum), with the application still working fine since the column
allows `NULL`; (3) add the `NOT NULL` constraint using `NOT VALID` plus a separate `VALIDATE
CONSTRAINT` step (Postgres-specific: `NOT VALID` adds the constraint instantly without
validating existing rows, and `VALIDATE CONSTRAINT` then checks them with a much lighter lock,
concurrently with normal operations); (4) deploy application code that always writes a value
for the new column, timed so it happens before the constraint is enforced. The pattern
generalizes: any schema change on a huge, live table gets split into a nullable/loose step, a
backfill, and a strict-enforcement step, each independently deployable and each safe to run
without blocking concurrent traffic.

**Example:**
```sql
-- Step 1: instant, no table rewrite.
alter table orders add column region text;

-- Step 2: backfill in batches, not one giant transaction (see S12).
update orders set region = 'UNKNOWN' where id between 1 and 10000 and region is null;
-- ... repeat in chunks ...

-- Step 3: instant constraint add, no validation yet — then validate with a lighter lock.
alter table orders add constraint orders_region_not_null check (region is not null) not valid;
alter table orders validate constraint orders_region_not_null;
```

**Why it's a trap:** the migration that "just works" in a staging environment with a few thousand
rows and no concurrent traffic is exactly the one that locks production for the duration of a
full-table validation — the difference only shows up at production's actual scale, which is
precisely why this has to be a deliberate, tested pattern rather than something discovered the
hard way during a deploy.

### Q25. When do you deliberately denormalize, and how do you keep the denormalized copy consistent?
**Answer:** Denormalize when a read pattern is both extremely hot and expensive to compute from normalized
data on every request — a running total, a frequently-displayed aggregate (comment count on a
post, follower count on a profile), or data joined so often that the join cost itself is the
bottleneck. The trade-off is explicit: you're accepting a consistency-maintenance burden in
exchange for read speed, and that burden needs a deliberate mechanism, not "just remember to
update it everywhere" — options include updating the denormalized value transactionally
alongside the source-of-truth write (same transaction, so it can never drift, but couples the
two writes), an async event/queue-driven update (eventually consistent, decoupled, but needs
monitoring for drift and a reconciliation job to catch missed events), or a materialized view
refreshed on a schedule (simple, but only as fresh as the last refresh). The interview-worthy
answer names the specific mechanism chosen and its specific failure mode — "I'd cache it" without
naming how staleness or drift is detected and corrected is an incomplete answer at senior level.

**Example:**
```sql
-- Denormalized counter, updated in the same transaction as the source-of-truth write:
begin;
insert into comments (post_id, body) values (42, 'nice post');
update posts set comment_count = comment_count + 1 where id = 42;
commit; -- can never drift — both writes succeed or fail together

-- A reconciliation job to catch drift from an async-updated denormalized value:
select p.id, p.comment_count, c.actual
from posts p
join (select post_id, count(*) actual from comments group by post_id) c on c.post_id = p.id
where p.comment_count <> c.actual; -- flags any row that has drifted from the source of truth
```

**Why it's a trap:** "I'd just cache it" sounds like an answer but doesn't survive the obvious
follow-up — what happens when an update event is missed, and how would anyone find out? Naming
the reconciliation mechanism up front is what separates a senior answer from a plausible-sounding
one that hasn't been tested against a real failure mode.

## 🎯 Real-world scenarios

### S1. A query that used to be fast has become steadily slower as the table has grown
- **Symptoms:** A specific query's latency has crept up over months in proportion to table
  growth, well beyond what row-count growth alone should cause.
- **Diagnosis:** Run `EXPLAIN ANALYZE` (Q14) and check for a `Seq Scan` where an `Index Scan`
  would be expected, or a large mismatch between the planner's estimated and actual row counts
  (stale statistics).
- **Example:**
  ```
  Seq Scan on orders (actual time=0.02..812.40 rows=1200000 loops=1)
    Filter: (status = 'PENDING')
  Planning Time: 0.10 ms
  Execution Time: 815.02 ms
  ```
  No index exists on `status`, so every query filtering on it scans the whole table — and that
  scan gets linearly slower as the table grows.
- **Resolution:** Add the missing index (checking column order for composite cases, Q18), or run
  `ANALYZE` to refresh statistics if the plan itself is simply wrong due to stale stats, or
  rewrite the query if a function wrapped around the filtered column is preventing index use.
- **Prevention:** Set up `EXPLAIN`-based query review for new hot-path queries before they ship,
  and monitor slow-query logs continuously rather than discovering degradation from user reports.

### S2. An APM tool flags dozens of near-identical queries firing for a single page load
- **Symptoms:** A page that lists 50 items triggers 51+ database queries — one for the list, and
  one per item for an associated collection.
- **Diagnosis:** Classic N+1 (Q8) — confirm by checking the entity's association fetch type and
  whether the code iterates the collection and accesses a lazy association inside the loop.
- **Example:**
  ```
  select * from orders limit 50
  select * from line_items where order_id = 1
  select * from line_items where order_id = 2
  -- ... 48 more, one per order in the page
  ```
- **Resolution:** Add a `JOIN FETCH` / `@EntityGraph` for that specific query path, or configure
  batch fetching if eager-joining everywhere isn't appropriate.
- **Prevention:** Add a query-count assertion to integration tests for list-rendering endpoints
  (many test frameworks support asserting a maximum query count per test) so a regression fails
  CI instead of shipping.

### S3. Two concurrent transactions deadlock, and one is aborted by the database
- **Symptoms:** Postgres logs a `deadlock detected` error, naming the two conflicting processes
  and the locks each held while waiting on the other; one transaction is automatically rolled
  back to break the cycle.
- **Diagnosis:** The log message itself names the exact queries and lock types involved — the
  usual cause is two transactions updating the same two rows (or tables) in opposite order (A
  then B in one transaction, B then A in another).
- **Example:**
  ```
  ERROR: deadlock detected
  DETAIL: Process 1234 waits for ShareLock on transaction 5678; blocked by process 5678.
          Process 5678 waits for ShareLock on transaction 1234; blocked by process 1234.
  Process 1234: UPDATE accounts SET balance = balance - 100 WHERE id = 2;
  Process 5678: UPDATE accounts SET balance = balance - 50  WHERE id = 1;
  ```
  Transaction 1234 updated `id = 1` then wanted `id = 2`; transaction 5678 updated `id = 2` first
  then wanted `id = 1` — a classic opposite-order lock acquisition.
- **Resolution:** Standardize a consistent lock/update order across every code path that touches
  both resources (always update in the same order, e.g. by primary key ascending), or shrink
  transaction scope so locks are held for less time, reducing the window for the conflict.
- **Prevention:** Handle the deadlock exception with a retry (the aborted transaction is safe to
  retry — nothing committed), and document the required lock ordering for any multi-row
  operation that's genuinely prone to this pattern.

### S4. Requests fail with the database's own "too many connections" error, independent of the application-level pool size
- **Symptoms:** The application's HikariCP pool isn't exhausted (metrics show headroom), but the
  database itself rejects new connections.
- **Diagnosis:** Check the database server's `max_connections` against the *sum* of every
  application instance's pool size, plus any other clients (admin tools, other services sharing
  the database) — a fleet of instances each sized generously can collectively exceed the
  server's actual limit even though no single instance's pool looks maxed out.
- **Example:**
  ```
  FATAL: sorry, too many clients already
  ```
  ```
  show max_connections; -- 100
  -- 12 application instances x maximum-pool-size: 15 each = 180 possible connections,
  -- already over the server's limit even before any admin tooling connects.
  ```
- **Resolution:** Reduce per-instance pool size using the sizing guidance in Q16, or introduce a
  connection pooler (PgBouncer) in front of the database to multiplex many application
  connections over fewer actual database connections.
- **Prevention:** Track total connections across the fleet as a first-class metric against the
  database's configured limit, not just per-instance pool utilization.

### S5. A schema migration locks a production table and causes a brief outage
- **Symptoms:** A deployment's migration step causes a spike in request latency or outright
  timeouts for the duration the migration ran, on a table under active read/write traffic.
- **Diagnosis:** Identify the specific migration statement — adding a column with a non-constant
  default (pre-recent-Postgres-versions, this rewrote the whole table under an exclusive lock),
  adding a foreign key without `NOT VALID` (validates all existing rows under lock), or creating
  an index without `CONCURRENTLY` (blocks writes for the duration of the build).
- **Example:**
  ```sql
  -- Blocks writes to `orders` for however long the index build takes:
  create index idx_orders_email on orders(customer_email);

  -- Non-blocking equivalent:
  create index concurrently idx_orders_email on orders(customer_email);
  ```
- **Resolution:** Rewrite the migration using the non-blocking equivalents: `NOT VALID` +
  separate `VALIDATE CONSTRAINT` for constraints, `CREATE INDEX CONCURRENTLY` for indexes, and
  the multi-step pattern from Q24 for anything that would otherwise require a full-table
  rewrite or scan.
- **Prevention:** Require every migration against a large, live table to state explicitly which
  lock it takes and for how long, as part of review — and test migrations against a
  production-sized dataset in staging, not just an empty or small dev database, since lock
  duration scales with table size.

### S6. A user submits a form, is redirected to a confirmation page, and sees their submission is missing
- **Symptoms:** Intermittent, and specifically tied to write-then-immediate-read flows — the same
  user reloading a moment later sees the data correctly.
- **Diagnosis:** Classic read-after-write inconsistency from a naive read-replica setup (Q21) —
  the write landed on the primary, and the confirmation page's read was routed to a replica that
  hadn't caught up yet.
- **Example:**
  ```java
  Long id = orderService.create(request);       // write -> primary
  return "redirect:/orders/" + id;               // client immediately follows the redirect

  // GET /orders/{id} handler, routed by the load balancer/read-router to a replica:
  Order order = orderRepository.findById(id);    // replica hasn't replicated the insert yet -> 404
  ```
- **Resolution:** Route reads that must reflect a just-completed write back to the primary (or a
  replica known to be caught up for that session), at least for that specific flow.
- **Prevention:** Identify every read-after-write-sensitive flow explicitly during design (don't
  assume every read can safely go to a replica), and monitor replication lag with alerting so a
  lagging replica is caught before it causes user-visible inconsistency broadly.

### S7. Two near-simultaneous requests both create a row for what should be a unique entity, resulting in duplicates
- **Symptoms:** Under concurrent load (e.g. a user double-clicking submit, or a retried request
  racing the original), two rows exist for what the business logic assumed could only ever be
  one (two accounts for one email, two orders for one idempotency key).
- **Diagnosis:** Check-then-insert logic at the application level ("check if it exists, if not,
  insert") has a race window between the check and the insert — two concurrent requests can both
  pass the check before either has inserted.
- **Example:**
  ```java
  // Both requests execute this concurrently and both pass the check before either inserts:
  if (userRepository.findByEmail(email).isEmpty()) {
      userRepository.save(new User(email)); // race window between the check and this insert
  }
  ```
- **Resolution:** Add a database-level unique constraint (the check-then-insert pattern is never
  sufficient alone at the database's actual concurrency level — the constraint is the real
  guarantee) and handle the resulting unique-violation exception as an expected "already exists"
  case, using `ON CONFLICT DO NOTHING`/`DO UPDATE` (Postgres upsert) where the intent is
  idempotent creation rather than a hard error.
  ```sql
  insert into users (email) values ('ann@example.com')
  on conflict (email) do nothing; -- idempotent under the exact race that broke check-then-insert
  ```
- **Prevention:** Never rely on application-level check-then-act for uniqueness that must
  actually hold — always back it with a database constraint, since the database is the only
  component that can see and serialize truly concurrent attempts.

### S8. `SELECT COUNT(*)` on a large table is unexpectedly slow and shows up as a hot query
- **Symptoms:** A dashboard or pagination feature calling `COUNT(*)` on a multi-million-row table
  takes seconds, disproportionate to how simple the query looks.
- **Diagnosis:** Postgres's MVCC design means `COUNT(*)` can't use an index alone to answer the
  question — it generally must check row visibility for the requesting transaction, which for
  large tables means a real scan of a large portion of the table (or the index, for an
  index-only-scan-eligible case, but still proportional to row count either way).
- **Example:**
  ```sql
  explain analyze select count(*) from orders;
  -- Aggregate (actual time=1120.44..1120.44 rows=1 loops=1)
  --   ->  Seq Scan on orders (actual time=0.01..980.22 rows=18000000 loops=1)

  -- Approximate count from table statistics — near-instant, good enough for most UIs:
  select reltuples::bigint from pg_class where relname = 'orders';
  ```
- **Resolution:** If exact real-time counts aren't actually required (most pagination UIs don't
  need an exact "10,482,393 results"), use an approximate count from table statistics
  (`pg_class.reltuples`, refreshed by `ANALYZE`/autovacuum) or cap and label large counts ("10,000+
  results") instead of computing the exact number. If an exact count genuinely is required
  frequently, maintain it incrementally (a counter column updated transactionally, or via a
  materialized aggregate) rather than recomputing it from scratch on every request.
- **Prevention:** Treat "do we need an exact count on every page load" as a design question for
  any paginated UI over a large or fast-growing table, not a default to reach for unquestioned.

### S9. Optimistic-locking failures spike sharply during a specific high-traffic period
- **Symptoms:** `OptimisticLockException` (or equivalent version-conflict error) rates climb
  during a known high-concurrency window (a flash sale, a popular event), causing a wave of
  failed updates that the application surfaces as user-facing errors or silent retries.
- **Diagnosis:** This confirms Q9's point in practice — optimistic locking's failure rate rises
  with contention on the same rows, and at flash-sale-level contention on a small number of hot
  rows (e.g. limited inventory counts), the failure rate can become the dominant user experience
  problem rather than an edge case.
- **Example:**
  ```java
  // Read-then-write race under high contention — every retry re-reads, re-checks, re-fails:
  Inventory inv = inventoryRepository.findById(skuId); // read version N
  if (inv.getQty() > 0) { inv.setQty(inv.getQty() - 1); inventoryRepository.save(inv); }
  // save() throws OptimisticLockException if another request updated this row in between

  // Fix for this specific hot path: a single atomic statement, no read-then-write race at all.
  ```
  ```sql
  update inventory set qty = qty - 1 where sku_id = ? and qty >= 1;
  -- affected rows == 0 means "out of stock", with no lock held and no retry storm possible
  ```
- **Resolution:** For genuinely hot, high-contention rows specifically, switch that access path
  to pessimistic locking (or an atomic `UPDATE ... SET qty = qty - 1 WHERE qty >= 1` single
  statement, which sidesteps optimistic-locking's read-then-write race entirely for this simple
  case), while leaving optimistic locking in place for the vast majority of low-contention rows
  where it performs better.
- **Prevention:** Identify hot-row contention patterns before they're discovered in production
  under real flash-sale load — load-test the specific high-contention path deliberately, since
  it behaves qualitatively differently from average-case traffic.

### S10. After an application crash mid-operation, the database is left in an inconsistent state
- **Symptoms:** A multi-step business operation (debit account A, credit account B) is found
  partially applied after a crash — one side happened, the other didn't.
- **Diagnosis:** The operation's multiple statements weren't wrapped in a single database
  transaction — each executed and committed independently, so a crash between them left a
  genuinely inconsistent, non-atomic result; this is an application-code bug, not a database
  failure, since the database did exactly what it was told for each individual statement.
- **Example:**
  ```java
  // Bug: two independent auto-committing statements, no shared transaction boundary.
  jdbcTemplate.update("update accounts set balance = balance - 100 where id = 1");
  // <-- crash here leaves account 1 debited with account 2 never credited
  jdbcTemplate.update("update accounts set balance = balance + 100 where id = 2");

  // Fix: one transaction, atomic by construction.
  @Transactional
  void transfer(long fromId, long toId, BigDecimal amount) {
      jdbcTemplate.update("update accounts set balance = balance - ? where id = ?", amount, fromId);
      jdbcTemplate.update("update accounts set balance = balance + ? where id = ?", amount, toId);
  }
  ```
- **Resolution:** Wrap the entire multi-step operation in one transaction (`@Transactional` at
  the correct granularity, or an explicit `BEGIN`/`COMMIT`) so atomicity (Q5) actually holds —
  either both statements commit or, on any failure including a crash before commit, neither does.
  Reconcile the specific inconsistent rows found by this incident manually, since the historical
  damage isn't automatically fixed by the code change.
- **Prevention:** Treat "is this operation wrapped in one transaction" as a required review
  question for any code touching more than one write, and add a reconciliation/audit job that
  periodically checks for exactly this class of drift (e.g. debits not matching credits) as a
  safety net independent of getting every code path right the first time.

### S11. Queries filtering on a `JSONB` column get slower as the table grows, despite the column being indexed
- **Symptoms:** A query like `WHERE metadata @> '{"status": "active"}'` on a `JSONB` column
  degrades with table growth even though "there's an index."
- **Diagnosis:** Check the actual index type — a plain B-tree index on a `JSONB` column supports
  only equality on the *whole* JSON value, not containment (`@>`) or key-existence queries; only
  a GIN index (Q13) actually accelerates those operators. A B-tree index existing on the column
  doesn't mean the specific query pattern is using it — `EXPLAIN` confirms this directly.
- **Example:**
  ```sql
  create index idx_orders_metadata on orders(metadata); -- B-tree — useless for @>

  explain select * from orders where metadata @> '{"status": "active"}';
  -- Seq Scan on orders -- the B-tree index above is never even considered for this operator

  create index idx_orders_metadata_gin on orders using gin (metadata); -- the actual fix
  ```
- **Resolution:** Add a GIN index specifically (`CREATE INDEX ... USING GIN (metadata)`, or
  `jsonb_path_ops` variant for containment-only queries, which is smaller and faster for that
  narrower use case).
- **Prevention:** When a column's query pattern involves containment/key lookups rather than
  whole-value equality, choose the index type deliberately for that operator from the start,
  rather than adding "an index" generically and assuming it covers every access pattern.

### S12. A nightly batch job that updates millions of rows one at a time starts timing out or overwhelming the database
- **Symptoms:** A batch job that loops through rows and issues one `UPDATE` per row takes
  increasingly long as data volume grows, and during its run other queries against the same
  table slow down noticeably.
- **Diagnosis:** Row-by-row updates in a loop (Q20's pattern, but for updates rather than
  inserts) pay per-statement round-trip overhead multiplied by row count, and if each update
  commits individually, it also generates far more write-ahead-log/vacuum churn than necessary;
  if it's all one giant transaction instead, that creates a long-running transaction holding
  locks and bloating the table (since Postgres can't vacuum rows a long-running transaction might
  still need to see).
- **Example:**
  ```java
  // One round trip per row, and — if wrapped in one giant transaction — one long-lived
  // transaction blocking autovacuum for its entire duration.
  for (Long id : millionsOfIds) {
      jdbcTemplate.update("update prices set updated = true where id = ?", id);
  }
  ```
  ```sql
  -- Fix: a single bulk statement instead of a million round trips.
  update prices set updated = true
  from (values (1), (2), (3) /* ... a chunk's worth of ids ... */) as t(id)
  where prices.id = t.id;
  ```
- **Resolution:** Batch the updates — either a single bulk `UPDATE ... FROM (VALUES ...)`
  statement for the whole set, or chunked batches of a few thousand rows each, committed
  incrementally rather than one all-or-nothing transaction, with a short pause between batches if
  the goal is to avoid saturating the database during business hours.
- **Prevention:** Default any bulk data-modification job to a chunked, batched pattern from the
  start, with the chunk size and pacing configurable — "loop and update one row at a time" should
  be a code-review flag for anything operating on more than a few hundred rows.

### S13. A report occasionally shows numbers that don't add up, only under concurrent write activity
- **Symptoms:** A multi-query report (e.g. sum several tables' values that should reconcile) is
  correct when the system is idle but occasionally inconsistent when generated while writes are
  happening concurrently.
- **Diagnosis:** Check the isolation level the report's queries run under — at the default Read
  Committed level (Q15), each individual statement within the report's transaction sees the
  latest committed data *at the time that specific statement runs*, so two queries a few
  milliseconds apart within the same "report" can see different snapshots if a write commits in
  between — that's a non-repeatable read, not a bug in the report's arithmetic.
- **Example:**
  ```sql
  -- Report, run at the default Read Committed level:
  select sum(amount) from debits;   -- sees $10,000 total

  -- A write commits here, in between the report's two statements:
  -- insert into credits (amount) values (500);

  select sum(amount) from credits;  -- now includes the new $500 -- the two sums no longer reconcile
  ```
- **Resolution:** Run the whole report inside a single transaction at Repeatable Read isolation
  (Postgres's Repeatable Read takes one consistent snapshot for the entire transaction), so every
  query within it sees the exact same point-in-time view of the data.
  ```sql
  begin transaction isolation level repeatable read;
  select sum(amount) from debits;
  select sum(amount) from credits; -- guaranteed to see the same snapshot as the first query
  commit;
  ```
- **Prevention:** Any multi-query operation that requires a single consistent view of the data
  across several statements needs an explicit isolation-level decision, not the implicit default
  — this is a case where naming the isolation level in code review matters as much as naming the
  index strategy.

### S14. Table and index sizes keep growing even though the row count is roughly stable
- **Symptoms:** Disk usage for a frequently-updated table climbs steadily, disproportionate to
  its actual (stable or slowly growing) live row count, and query performance degrades alongside
  it.
- **Diagnosis:** This is table/index bloat — Postgres's MVCC keeps old row versions (dead tuples)
  around after an `UPDATE`/`DELETE` until vacuum reclaims them; if autovacuum isn't keeping up
  (too infrequent for the table's write rate, or blocked by a long-running transaction holding
  back the horizon it can clean up to), dead tuples accumulate and both bloat the table on disk
  and degrade every scan that has to skip over them.
- **Example:**
  ```sql
  select relname, n_live_tup, n_dead_tup
  from pg_stat_user_tables
  where relname = 'sessions';
  --  relname  | n_live_tup | n_dead_tup
  --  sessions |    500000  |   4200000   -- 8x more dead tuples than live rows
  ```
- **Resolution:** Tune autovacuum settings more aggressively for this specific table
  (`autovacuum_vacuum_scale_factor`/`cost_limit` per-table overrides for high-churn tables rather
  than the global default), identify and fix any long-running transaction preventing vacuum from
  making progress, and run a manual `VACUUM (VERBOSE, ANALYZE)` to assess current bloat and
  recover disk space (or `VACUUM FULL`/`pg_repack` for severe cases, understanding `VACUUM FULL`
  takes an exclusive lock).
- **Prevention:** Monitor dead-tuple count and autovacuum run frequency per table as an ongoing
  metric for any high-write table, not just overall table size — bloat is a trend that's cheap to
  catch early and expensive to unwind once severe.

### S15. Deleting one row unexpectedly deletes a large number of related rows across several tables
- **Symptoms:** Removing what looked like a single, contained entity (e.g. deleting a user)
  cascades into deleting orders, payment records, or audit history that the team assumed would
  be preserved.
- **Diagnosis:** Check the foreign key constraints' `ON DELETE` behavior — `ON DELETE CASCADE`
  was set (perhaps for a different, genuinely-dependent relationship, like line items belonging
  to an order) and it's now propagating further than intended through a chain of cascading
  foreign keys, or was applied to a relationship that should have been `ON DELETE RESTRICT`
  (block the delete) or `SET NULL` instead.
- **Example:**
  ```sql
  -- users -> orders -> payments, CASCADE at every link:
  alter table orders add constraint fk_orders_user
      foreign key (user_id) references users(id) on delete cascade;
  alter table payments add constraint fk_payments_order
      foreign key (order_id) references orders(id) on delete cascade;

  delete from users where id = 42; -- silently also deletes every order AND every payment record
  ```
- **Resolution:** Review every `ON DELETE CASCADE` on the affected chain and change it to
  `RESTRICT` (force an explicit decision at delete time) or `SET NULL` wherever cascading isn't
  actually the intended business behavior; for entities requiring historical retention, this is
  usually also the trigger to introduce soft deletes (Q22) instead of ever hard-deleting them at
  all.
- **Prevention:** Treat `ON DELETE CASCADE` as a deliberate, reviewed decision per relationship,
  not a default reached for convenience — document explicitly, for every foreign key, what should
  happen to the child rows when the parent is deleted.

### S16. Immediately after a deployment that includes a schema migration, the application starts throwing errors about a missing or unexpected column
- **Symptoms:** Errors like "column does not exist" or a mapping failure appear right after
  deploy, but only on some instances, or only briefly.
- **Diagnosis:** Migration and application code deployment aren't atomic together — during a
  rolling deployment, old application instances (expecting the old schema) can still be running
  against a database that's already been migrated to the new schema, or a migration was run
  *after* new application code already started expecting it, briefly exposing a gap.
- **Example:**
  ```
  ERROR: column "region" of relation "orders" does not exist
  ```
  A new application instance, already deployed and expecting `orders.region`, started receiving
  traffic before the migration that adds that column had actually run against the database — or
  the reverse: old instances still running the previous version choke on a renamed/dropped column
  a migration already applied.
- **Resolution:** Reorder deployment strictly so the migration always completes fully before any
  new application code that depends on it starts receiving traffic, and ensure the migration
  itself is backward-compatible with the *old* application version for the duration old instances
  are still running (this is exactly why Q24's multi-step, additive-first migration pattern
  matters — it's designed so both old and new code work against the in-between schema state).
- **Prevention:** Never ship a migration that both adds a requirement (a new `NOT NULL` column, a
  renamed column) and requires the new code in the same atomic step — always split into an
  additive, backward-compatible migration first, deployed and verified, before a later cleanup
  migration removes what the old code needed.

## 📌 Cheat-sheet

- **JPA vs JDBC vs MyBatis**: full ORM / low-level manual / SQL-you-write-plus-mapping — pick by how much control over the exact SQL you need.
- **SQL logical order**: `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`. `WHERE` can't see a `SELECT` alias; `HAVING` can filter aggregates because it runs after grouping.
- **N+1**: 1 query becomes N+1 via lazy-loaded collections in a loop — fix with `JOIN FETCH`/`@EntityGraph`/batch fetching, not a blanket `FetchType.EAGER`.
- **Optimistic vs pessimistic**: optimistic wins at low contention (no locks held); pessimistic wins at high contention on the same hot rows (avoids retry storms).
- **Hibernate entity states**: transient → persistent (managed, auto-tracked) → detached (changes untracked — `merge()` can silently overwrite newer data) → removed.
- **Multi-datasource `@Transactional`** doesn't span both DBs atomically without JTA/XA — design around a single source of truth per write instead.
- **Postgres index types**: B-tree (default, equality/range) · GIN (JSONB containment, full-text, arrays) · GiST (geometric/range overlap) · partial index (small, filtered subset).
- **`EXPLAIN ANALYZE`**: watch for `Seq Scan` on a big table, and estimated-vs-actual row mismatches (stale stats → run `ANALYZE`) — plain `EXPLAIN` is only an estimate, it never actually runs the query.
- **Isolation levels**: Read Committed (default, prevents dirty reads only) < Repeatable Read (also prevents non-repeatable/phantom reads in Postgres) < Serializable (fully serial-equivalent, more retries).
- **HikariCP sizing**: smaller than intuition suggests; total connections across the whole fleet must fit the DB's `max_connections`, not just one instance's pool.
- **Big migrations**: `NOT VALID` + `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`, additive-then-backfill-then-cleanup — never one blocking step on a huge live table.
- **Composite index column order** matters: equality/high-selectivity columns first, or the index silently doesn't serve the query.
- **JSONB**: fine for sparse/variable data; normalize anything frequently filtered, joined, or constraint-checked.
- **Bulk writes**: batch inserts/updates (JDBC batch API, multi-row `VALUES`, or `COPY`) — never row-by-row in a loop; `hibernate.jdbc.batch_size` alone isn't enough without `order_inserts`/`order_updates`.
- **Read replicas**: naive routing breaks read-after-write — pin write-sensitive reads to the primary.
- **`ON DELETE CASCADE`**: a deliberate per-relationship decision, not a default — review the full cascade chain.
- **Soft deletes**: prevent forgotten `deleted_at is null` filters and unique constraints from leaking/blocking on "deleted" rows — scope uniqueness to live rows with a partial index.
- **Table/index bloat**: `n_dead_tup` growing despite stable `n_live_tup` means autovacuum isn't keeping up — tune per-table settings or find the blocking long-running transaction.
- **Zero-downtime schema changes**: additive/nullable first → backfill → enforce/cleanup, each step compatible with both old and new app code.
