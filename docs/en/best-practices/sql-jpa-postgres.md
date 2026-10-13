# SQL, JPA & Postgres Best Practices

## 🗺️ Entity mapping

### Make every association `LAZY`

Set `fetch = FetchType.LAZY` on `@ManyToOne` and `@OneToOne`. (`@OneToMany` and `@ManyToMany` are already lazy.)

**Why it's a best practice:** `@ManyToOne` and `@OneToOne` are `EAGER` by default. Every time you load an
`Order`, Hibernate also loads its `Customer`, the customer's `Address`, and so on, often with one extra query
per row. You can't turn eager fetching off for a single query, but you can always turn lazy fetching on when you
need it (fetch join, entity graph). Lazy by default, fetch explicitly per use case.

⛔ `@ManyToOne private Customer customer;`
✅ `@ManyToOne(fetch = FetchType.LAZY) private Customer customer;`

### Prefer `SEQUENCE` over `IDENTITY` for ids

Use `@GeneratedValue(strategy = GenerationType.SEQUENCE)` with an `allocationSize` matching the sequence
increment.

**Why it's a best practice:** with `IDENTITY`, the id is only known after the `INSERT`, so Hibernate must run
each insert immediately and can't batch them: saving 10 000 rows is 10 000 round-trips. With a sequence,
Hibernate fetches ids in blocks (`allocationSize = 50` → one sequence call per 50 rows) and sends the inserts in
JDBC batches (`hibernate.jdbc.batch_size`). Postgres sequences are cheap and made for this.

⛔ `@GeneratedValue(strategy = GenerationType.IDENTITY)`
✅ `@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "order_seq")` + `@SequenceGenerator(name = "order_seq", allocationSize = 50)`

Enable JDBC batching so the ids you pre-allocated actually pay off:

```yaml
spring.jpa.properties.hibernate:
  jdbc.batch_size: 50
  order_inserts: true
  order_updates: true
```

The database side must match, or ids collide: `CREATE SEQUENCE order_seq INCREMENT BY 50;`

### Implement `equals` / `hashCode` carefully on entities

Base them on a natural business key, or on the id with a constant `hashCode`. Never use Lombok `@Data` on an
entity.

**Why it's a best practice:** a generated id is `null` until the entity is persisted. If `hashCode` uses the id,
it changes after `save()`, and an entity added to a `HashSet` before saving can no longer be found in it. Lombok
`@Data` / `@EqualsAndHashCode` includes every field, including lazy collections: calling `hashCode` triggers
loading, or a `StackOverflowError` on bidirectional relations. Its `toString` has the same problem.

```java
// ✅ id-based, stable across the entity lifecycle
@Override public boolean equals(Object o) {
    return o instanceof Order other && id != null && id.equals(other.id);
}
@Override public int hashCode() { return getClass().hashCode(); }
```

### Use optimistic locking with `@Version`

Add a `@Version` column to entities that can be edited concurrently.

**Why it's a best practice:** without it, two users load the same row, both edit it, and the second save
silently overwrites the first: a lost update. With `@Version`, Hibernate adds `WHERE version = ?` to the update;
if someone else changed the row in between, 0 rows match and an `OptimisticLockException` is thrown, so you can
ask the user to reload. It costs one integer column and no locks.

✅ `@Version private long version;`

Catch the conflict where you can tell the user something useful:

```java
try {
    orderService.update(id, command);          // save() flushes UPDATE ... WHERE version = ?
} catch (ObjectOptimisticLockingFailureException e) {
    throw new ResponseStatusException(HttpStatus.CONFLICT, "Modified by someone else, reload");
}
```

## ⚡ Queries & performance

### Avoid N+1 queries

When you need an association for a list of entities, fetch it in the same query with a `JOIN FETCH` or an
`@EntityGraph`.

**Why it's a best practice:** loading 100 orders and then calling `order.getCustomer().getName()` in a loop
runs 1 query for the orders plus 100 for the customers. It's invisible in code and in tests with 3 rows, and
turns a 10 ms page into a 2 s one in production. Turn on SQL logging or use a query-count assertion in tests to
catch it. For collections, `@BatchSize` or `hibernate.default_batch_fetch_size` reduces the N to N / batch size.

```java
// ⛔ 1 + N queries
List<Order> orders = orderRepository.findAll();
orders.forEach(o -> print(o.getCustomer().getName()));

// ✅ one query
@Query("select o from Order o join fetch o.customer")
List<Order> findAllWithCustomer();
```

Same result without writing JPQL, and it composes with derived queries:

```java
@EntityGraph(attributePaths = "customer")
List<Order> findByStatus(Status status);
```

Don't join-fetch two collections at once (`MultipleBagFetchException`, or a cartesian product): fetch one, and use `@BatchSize` for the other.

### Read with projections, not entities

For read-only screens and APIs, select only the columns you need into a DTO or interface projection.

**Why it's a best practice:** loading entities means selecting every column, creating managed objects, keeping
a snapshot of each for dirty checking, and flushing at the end. For a list page that only shows 3 fields, that's
wasted memory and CPU. A projection runs a narrower query and returns plain objects Hibernate doesn't track.

⛔ `List<Order> findByStatus(Status s)` then map 3 fields
✅ `@Query("select new com.acme.OrderSummary(o.id, o.total, o.createdAt) from Order o where o.status = :s")`

### Use keyset pagination for large tables

For deep pagination or infinite scroll, paginate with `WHERE id > :lastId ORDER BY id LIMIT n` instead of a big
`OFFSET`.

**Why it's a best practice:** `OFFSET 100000` makes Postgres read and throw away 100 000 rows before returning
the page, so each page is slower than the previous one. Rows inserted or deleted between two requests also shift
the pages, giving duplicates or missing items. Keyset pagination uses the index to jump straight to the next
row: constant time whatever the page, and stable.

```sql
-- ⛔ gets slower as the offset grows
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100000;

-- ✅ uses the index, constant time
SELECT * FROM orders WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```

### Index foreign keys and filtered columns, and check with `EXPLAIN`

Create indexes for columns used in `WHERE`, `JOIN` and `ORDER BY`, including foreign keys. Verify the plan with
`EXPLAIN (ANALYZE, BUFFERS)`.

**Why it's a best practice:** Postgres indexes primary keys and unique constraints automatically, but *not*
foreign keys. A join on `order_line.order_id` or a `DELETE` on the parent table then does a full scan of the child
table. Guessing is unreliable: `EXPLAIN ANALYZE` shows whether the index is used (`Index Scan`) or not
(`Seq Scan`) and where the time goes. Don't index everything either: each index slows down writes.

⛔ `order_line.order_id` with no index
✅ `CREATE INDEX idx_order_line_order_id ON order_line (order_id);`

Reading the plan:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM order_line WHERE order_id = 42;

⛔ Seq Scan on order_line  (cost=0.00..18334.00 rows=5 ...) (actual time=0.02..95.4 rows=5 loops=1)
     Filter: (order_id = 42)   Rows Removed by Filter: 1000000

✅ Index Scan using idx_order_line_order_id  (cost=0.42..8.44 rows=5 ...) (actual time=0.03..0.05 rows=5 loops=1)
```

Red flags: `Seq Scan` on a big table, `Rows Removed by Filter` far above rows returned, and estimated `rows` far from `actual rows` (stale statistics: run `ANALYZE`).

### Always use bind parameters

Pass values as parameters (`?`, `:name`), never by concatenating them into the SQL string.

**Why it's a best practice:** concatenation is SQL injection: `name = "x' OR '1'='1"` returns every row, and
worse payloads drop tables or read other users' data. Bind parameters are sent separately from the SQL text, so
they're always treated as values. They also let the database reuse the query plan. This applies to JPQL and
native queries too.

⛔ `em.createQuery("from User where name = '" + name + "'")`
✅ `em.createQuery("from User where name = :name").setParameter("name", name)`

### Keep transactions short

Open a transaction, do the database work, commit. No user input, remote calls or long computations in between.

**Why it's a best practice:** a long transaction holds its row locks, blocking other writers, and prevents
Postgres `VACUUM` from cleaning up dead rows it might still need to see, so tables and indexes bloat. A
connection left `idle in transaction` holds everything open indefinitely. Set
`idle_in_transaction_session_timeout` as a safety net.

⛔ call a payment API inside the transaction
✅ commit first, then call the API, then record the result in a second short transaction

## 🐘 Postgres types & schema

### Use `timestamptz`, `numeric` and `text`

Store instants in `timestamptz`, money in `numeric(p, s)`, and strings in `text` (or `varchar(n)` only when the
limit is a real rule).

**Why it's a best practice:** `timestamp` (without time zone) stores a wall-clock time with no zone: the same
value means different instants on servers configured differently, and DST changes create duplicates.
`timestamptz` stores an absolute instant (in UTC) and maps to `Instant` / `OffsetDateTime`. `real` / `double
precision` have the same rounding errors as Java `double`; `numeric` is exact and maps to `BigDecimal`. In
Postgres, `text` and `varchar` perform the same, so an arbitrary `varchar(255)` only adds a limit that breaks later.

⛔ `created_at timestamp`, `amount double precision`
✅ `created_at timestamptz`, `amount numeric(19, 4)`

### Put integrity rules in the database

Declare `NOT NULL`, `UNIQUE`, `FOREIGN KEY` and `CHECK` constraints in the schema, not only in application code.

**Why it's a best practice:** application checks race: two requests both check "email not taken" and both
insert. A `UNIQUE` constraint can't be bypassed, whatever the code path (a batch job, a manual fix in `psql`,
another service). Constraints also document the model for anyone reading the schema, and the planner uses them.

⛔ `if (!repository.existsByEmail(email)) repository.save(user);` alone
✅ `ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);` + handle the violation

## 🚚 Migrations

### Version the schema with Flyway or Liquibase

Every schema change is a migration file in the repository. Never use `ddl-auto=update` (or `create`) outside
local development.

**Why it's a best practice:** `ddl-auto=update` guesses the changes from your entities: it never drops or renames
anything, can't migrate data, and runs different SQL depending on the state of each database. Environments drift
apart and nobody knows what production looks like. Migrations are reviewed, repeatable, run in order, and
recorded in a history table. Set `ddl-auto=validate` so the app fails at startup if entities and schema don't
match.

⛔ `spring.jpa.hibernate.ddl-auto: update`
✅ `db/migration/V12__add_order_status.sql` + `ddl-auto: validate`

### Write migrations that don't lock production

Create indexes with `CREATE INDEX CONCURRENTLY`, add columns as nullable (or with a constant default), and split
breaking changes into expand / contract steps.

**Why it's a best practice:** a plain `CREATE INDEX` blocks all writes to the table for the whole build, which
can take minutes on a big table. `CONCURRENTLY` doesn't (it can't run inside a transaction, so configure the
migration tool for it). Renaming or dropping a column that the running version still uses breaks it during the
rolling deploy: add the new column, deploy code that writes both, backfill, switch reads, then drop the old one.

⛔ `CREATE INDEX idx_orders_status ON orders (status);`
✅ `CREATE INDEX CONCURRENTLY idx_orders_status ON orders (status);`

Full expand / contract example: renaming `orders.state` to `orders.status` without downtime, one release per step.

```sql
-- V20 (release 1, expand): add the new column; old code keeps working
ALTER TABLE orders ADD COLUMN status text;

-- release 1 code writes both columns; V21 backfills in small batches
UPDATE orders SET status = state WHERE status IS NULL AND id BETWEEN 1 AND 50000;

-- V22 (release 2): reads switch to status; add the constraint without a long lock
ALTER TABLE orders ADD CONSTRAINT orders_status_nn CHECK (status IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_status_nn;

-- V23 (release 3, contract): nothing reads `state` anymore
ALTER TABLE orders DROP COLUMN state;
```
