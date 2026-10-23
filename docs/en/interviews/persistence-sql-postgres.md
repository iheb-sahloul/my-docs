# Persistence & SQL

## 🟢 Fundamentals

### ORM & access choices

#### Q1. What is an ORM, and what problem does it actually solve? {#orm-problem-solve}
**Answer:** An ORM (Object-Relational Mapper) bridges the "impedance mismatch" between the relational model
(tables, rows, foreign keys) and the object model (classes, references, inheritance) — mapping
rows to objects, foreign keys to object references/collections, and translating object-graph
navigation into SQL joins or additional queries. It solves the tedium and error-proneness of
hand-writing that mapping code for every entity, at the cost of sometimes generating SQL that's
less efficient than a hand-written query for a specific case (see the N+1 problem, Q29).

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
are precisely where the N+1 problem (Q29) is born.

#### Q2. When would you choose JPA/Hibernate, plain JDBC, or MyBatis? {#jpa-hibernate-plain-jdbc-mybatis}
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

### Relational basics

#### Q3. What's the difference between a primary key, a unique constraint, and an index? {#primary-key-unique-constraint-index}
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

#### Q4. Walk through normalizing a table from 1NF to 3NF. {#normalizing-table-1nf-3nf}
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
changes, is exactly the case where deliberate denormalization (Q45) is the more senior call.

#### Q5. What do the ACID properties actually guarantee? {#acid-properties-guarantee}
**Answer:** **Atomicity**: a transaction's operations all succeed or all roll back together, no partial
application. **Consistency**: a transaction moves the database from one valid state to another,
respecting constraints (foreign keys, unique constraints, check constraints). **Isolation**:
concurrent transactions don't see each other's uncommitted intermediate state, to a degree
controlled by the isolation level (Q25). **Durability**: once committed, a transaction's changes
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

### SQL

#### Q6. What's the difference between `INNER JOIN` and `LEFT JOIN`, and why can a `WHERE` clause silently turn a `LEFT JOIN` into an inner one? {#inner-join-left-join-clause}
**Answer:** `INNER JOIN` returns only the rows that have a match on both sides. `LEFT JOIN` returns
*every* row of the left table and fills the right table's columns with `NULL` where no match
exists — the tool for questions like "all customers, including those with no orders". The subtle
part is where the filter goes. A condition in the `ON` clause is applied *while matching*, so
unmatched left rows survive with `NULL`s. A condition on a right-table column in the `WHERE`
clause is applied *after* the join, and since `NULL = 'PAID'` is not true, the unmatched rows are
filtered out — the query quietly behaves like an inner join. (Filtering on the *left* table in
`WHERE` is always fine; and `WHERE o.id IS NULL` is the deliberate anti-join idiom for "customers
with no orders".)

**Example:**

```sql
-- Goal: every customer with their number of PAID orders, including customers with none (0).

-- Wrong: the WHERE removes customers who have no orders -> they vanish from the report.
select c.id, count(o.id)
from customers c
left join orders o on o.customer_id = c.id
where o.status = 'PAID'
group by c.id;

-- Right: the condition belongs in ON, so unmatched customers are kept with count = 0.
select c.id, count(o.id)
from customers c
left join orders o on o.customer_id = c.id and o.status = 'PAID'
group by c.id;
```

**Why it's a trap:** the wrong query returns plausible data with no error — a report that
"just" omits customers with zero orders, discovered weeks later when totals don't reconcile.
Note also `count(o.id)` rather than `count(*)`: `count(*)` would count the `NULL`-padded row as 1.

#### Q7. What's the difference between `UNION` and `UNION ALL`, and which should be your default? {#union-union-all-default}
**Answer:** Both stack the results of two queries with the same number and compatible types of
columns. `UNION` additionally **removes duplicate rows** from the combined result, which the
database implements with a sort or a hash aggregate over the *entire* output — extra CPU, memory
(possibly spilling to disk) and no rows returned until that step finishes. `UNION ALL` just
concatenates and streams. So `UNION ALL` is the right default, and `UNION` is a deliberate
choice for when the same row genuinely can come from both sides and you need it once. Two related
points: the column *names* come from the first query, and `INTERSECT`/`EXCEPT` are the set
operators for "in both" and "in the first but not the second" (also de-duplicating unless `ALL`
is given).

**Example:**

```sql
-- Live and archived orders live in two tables with disjoint ids: no duplicates are possible.
select id, customer_id, total from orders
union all                                   -- cheap: no de-duplication pass
select id, customer_id, total from orders_archive;

-- Same customer may appear in both lists and we want each once -> UNION is deliberate here.
select customer_id from newsletter_subscribers
union
select customer_id from recent_buyers;
```

**Why it's a trap:** writing `UNION` "because that's the one everybody knows" quietly adds a
sort over millions of rows and — worse — can *change results*: it collapses legitimately
repeated rows (two identical sales lines) that a report meant to add up.

## 🟡 Senior traps

### SQL semantics

#### Q8. What is the logical execution order of a SQL query's clauses — and why can't you filter on a `SELECT` alias in `WHERE`? {#logical-execution-order-sql-query}
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
rule rarely know *why* — and the same underlying order is what makes `HAVING` (Q9) work where
`WHERE` can't, and why a window function can't appear in `WHERE` either. It's one mental model,
not three unrelated syntax rules to memorize separately.

#### Q9. Why can you filter on an aggregate function in `HAVING` but not in `WHERE`? {#filter-aggregate-function-having-but}
**Answer:** Because `WHERE` is evaluated before grouping/aggregation happens (per Q8's order), so aggregate
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

#### Q10. What are the classic `NULL` traps in SQL, and how do you avoid each? {#classic-null-traps-sql-avoid}
**Answer:** SQL uses three-valued logic: a comparison involving `NULL` is neither true nor false but
*unknown*, and a `WHERE` clause keeps only rows where the condition is *true*. Consequences:
(1) `col = NULL` and `col <> NULL` never match anything — use `IS NULL` / `IS NOT NULL`, or
`IS DISTINCT FROM` for a `NULL`-safe comparison. (2) `col <> 'X'` silently **excludes** rows
where `col` is `NULL`, so "everything except X" isn't everything. (3) `x NOT IN (subquery)`
returns **no rows at all** if the subquery yields even one `NULL`, because `x <> NULL` is
unknown for every `x`; use `NOT EXISTS`, which is `NULL`-safe. (4) Aggregates ignore `NULL`s:
`count(col)` counts non-null values while `count(*)` counts rows, and `avg(col)` divides by the
non-null count only. (5) In `ORDER BY`, PostgreSQL sorts `NULL`s *last* ascending and *first*
descending — use `NULLS FIRST/LAST` explicitly. (6) A `UNIQUE` constraint treats `NULL`s as
distinct, so many rows with `NULL` are allowed; PostgreSQL 15+ offers `UNIQUE NULLS NOT DISTINCT`
when you want at most one. `COALESCE` supplies a default when you truly want `NULL` treated as a
value.

**Example:**

```sql
-- customers: 1, 2, 3        orders.customer_id: 1, NULL   (a guest checkout with no customer)

select id from customers where id not in (select customer_id from orders);
-- returns NO rows (expected 2 and 3): 2 <> NULL is unknown, so the NOT IN is never true

select id from customers c
where not exists (select 1 from orders o where o.customer_id = c.id);   -- returns 2, 3

select count(*), count(customer_id) from orders;      -- 2, 1
select * from tickets where status <> 'CLOSED';       -- misses tickets whose status IS NULL
select * from tickets where status is distinct from 'CLOSED';  -- includes them
```

**Why it's a trap:** every one of these returns wrong data with no error, and `NOT IN` is
correct on test data that has no `NULL`s — it breaks the day a nullable column gets its first
`NULL` in production (see S17).

#### Q11. Why does `OFFSET` pagination get slower — and less correct — the deeper you go, and what's the alternative? {#offset-pagination-get-slower-less}
**Answer:** `OFFSET n LIMIT m` cannot jump to row `n`: the database must produce and discard the
first `n` rows in the requested order, so page 20,000 costs 20,000 × page-size rows of work even
though only `m` are returned — latency grows linearly with depth and load on the database grows
with every bot that crawls to the last page. It is also **unstable**: if rows are inserted or
deleted between two requests, everything shifts and the client sees duplicates or misses rows
entirely. **Keyset (seek) pagination** fixes both: the client sends the *last row it saw* and the
query says "give me rows after this key", which an index satisfies directly in O(page size)
regardless of depth. The requirements are a **deterministic total order** — a unique
tie-breaker such as `id` appended to the sort column, otherwise rows with equal timestamps are
skipped or repeated — a matching composite index, and acceptance of the trade-off: you can move
next/previous but can't jump to "page 137", and a `count(*)` for "1–50 of 4,231,987" is a
separate (and itself expensive) query, often replaced by "has more" or an approximate count.

**Example:**

```sql
-- Offset: reads and throws away 1,000,000 rows to return 50.
select id, created_at, payload
from events
order by created_at desc, id desc
offset 1000000 limit 50;

-- Keyset: the client passes the last (created_at, id) it received.
create index events_seek_idx on events (created_at desc, id desc);

select id, created_at, payload
from events
where (created_at, id) < (:last_created_at, :last_id)   -- row-value comparison
order by created_at desc, id desc
limit 50;
```

**Why it's a trap:** offset pagination is fast on a developer's 500-row table and the default of
every framework (`Pageable`), so it ships. The failure arrives as *both* a performance problem
and silent duplicate/missing rows in an export or infinite scroll — and the "just add an index"
instinct doesn't help the offset case (S18).

### SQL query patterns (the classics asked live)

These are the queries interviewers ask you to write on a whiteboard or in a shared editor. All examples use
one small schema, so you can paste them into any PostgreSQL:

```sql
customers  (id, name, email, country, created_at)
orders     (id, customer_id, status, total, created_at)
order_items(order_id, product_id, quantity, unit_price)
products   (id, name, category_id, price)
departments(id, name)
employees  (id, name, salary, department_id, manager_id)
logins     (user_id, login_date)
```

Say the approach out loud first (which rows, grouped how, ordered how), then write the query, then name
the edge case (ties, `NULL`s, empty groups). That order is what gets scored.

#### Q12. Explain window functions: `row_number` vs `rank` vs `dense_rank`, running totals, `lag`, and the default frame trap. {#window-functions-row-number-rank}
**Answer:** A window function computes a value *per row* over a set of related rows (the window) **without
collapsing rows** the way `GROUP BY` does. `PARTITION BY` defines the groups, `ORDER BY` the order inside
each, and the optional frame (`ROWS`/`RANGE BETWEEN …`) the rows used for each calculation. Ranking
functions differ only on ties: with salaries 100, 100, 90 → `row_number` = 1,2,3 (always unique, arbitrary
among ties), `rank` = 1,1,3 (ties share a rank, then a gap), `dense_rank` = 1,1,2 (no gap). `lag(x, n)` /
`lead(x, n)` read the previous/next row; `sum(x) over (order by …)` gives a running total;
`first_value` / `last_value` / `ntile(4)` cover "first of the group" and quartiles. Because windows run
after `WHERE`/`GROUP BY`/`HAVING` (Q8), you cannot filter on them directly — wrap the query in a subquery
or CTE and filter outside.

**Example:**

```sql
-- Rank inside each department; the named window avoids repeating the clause.
select name, department_id, salary,
       row_number() over w as rn,
       rank()       over w as rnk,
       dense_rank() over w as drnk
from employees
window w as (partition by department_id order by salary desc);

-- Daily revenue, running total, and change versus the previous day.
with daily as (
    select created_at::date as day, sum(total) as revenue
    from orders group by 1
)
select day, revenue,
       sum(revenue) over (order by day rows unbounded preceding) as running_revenue,
       revenue - lag(revenue) over (order by day)                as delta_vs_yesterday
from daily;
```

**Why it's a trap:** with `ORDER BY` and no explicit frame, the default is `RANGE BETWEEN UNBOUNDED
PRECEDING AND CURRENT ROW`, which includes all *peer* rows (equal order values) — so a running total over a
non-unique column jumps by the whole tie group, and `last_value()` returns the current row rather than the
last of the partition. Write `rows unbounded preceding` (or `rows between unbounded preceding and unbounded
following` for `last_value`) explicitly.

#### Q13. Write "the Nth highest salary" and "top 3 earners per department". How do ties change the answer? {#write-nth-highest-salary-top}
**Answer:** First clarify the **tie semantics** — "second highest *distinct* salary" and "second row in
salary order" are different questions. For a distinct Nth value, `dense_rank()` in a subquery is the general
and readable answer; `distinct … order by … offset n-1 limit 1` is a short one that returns *no row* (not
`NULL`) when there are fewer than N values. For top-N per group, `row_number()` gives exactly N rows
per group (arbitrary among ties), `dense_rank()` gives *everyone* tied inside the top N. For a large
table with few groups, `CROSS JOIN LATERAL (… order by … limit N)` is often faster: with an index on
`(department_id, salary desc)` it reads only N index entries per group, whereas the window version
numbers every row of the table first.

**Example:**

```sql
-- 2nd highest distinct salary, NULL-safe when it doesn't exist (scalar subquery returns NULL).
select (select salary
        from (select salary, dense_rank() over (order by salary desc) as r from employees) t
        where r = 2
        limit 1) as second_highest;

-- Top 3 distinct salary levels per department (ties all included).
select *
from (select e.*, dense_rank() over (partition by department_id order by salary desc) as r
      from employees e) t
where r <= 3;

-- Same idea with LATERAL: exactly 3 rows per department, index-friendly.
create index on employees (department_id, salary desc);
select d.name as department, top.name, top.salary
from departments d
cross join lateral (
    select e.name, e.salary
    from employees e
    where e.department_id = d.id
    order by e.salary desc
    limit 3
) top;
```

**Why it's a trap:** reaching for `limit 1 offset 1` or `max(salary) where salary < max` and
declaring victory — the first fails on ties and on "fewer than N", the second doesn't generalize to N. And
`row_number()` for "top 3" silently drops the fourth employee who earns exactly the same as the third.

#### Q14. How do you find and delete duplicate rows, and how do you stop them coming back? {#find-delete-duplicate-rows-stop}
**Answer:** Find them with `GROUP BY … HAVING count(*) > 1`. Delete them by numbering the rows inside each
duplicate group with `row_number()` and removing every row except the one you decided to keep (oldest,
newest, most complete) — decide that rule explicitly, it is the business question. If the table has no
usable key, PostgreSQL's physical row id `ctid` identifies a row. Before deleting, check what points at
the doomed rows: foreign keys from child tables must be re-pointed to the survivor first. Finally add the
constraint that makes the problem impossible — a unique index (on `lower(email)` if "same" means
case-insensitive) built `CONCURRENTLY`; without it the duplicates return (S7).

**Example:**

```sql
-- 1. Find
select lower(email), count(*) from customers group by 1 having count(*) > 1;

-- 2. Delete, keeping the oldest row of each group.
delete from customers c
using (select id,
              row_number() over (partition by lower(email) order by created_at, id) as rn
       from customers) d
where c.id = d.id and d.rn > 1;

-- 3. Prevent
create unique index concurrently uq_customers_email on customers (lower(email));
```

**Why it's a trap:** deleting duplicates without a deterministic "which one survives" rule (`order by`
with a unique tie-breaker) makes the result arbitrary — and skipping step 3 means the next race condition
(two simultaneous sign-ups) re-creates the exact mess you just cleaned.

#### Q15. What is a CTE, when is a recursive CTE the right tool, and what changed in PostgreSQL 12? {#cte-recursive-cte-right-tool}
**Answer:** A CTE (`WITH name AS (…)`) names a sub-query so a complex query reads top to bottom. Before
PostgreSQL 12 every CTE was an **optimization fence** — computed once and materialized, with outer filters
never pushed inside. Since 12, a side-effect-free CTE referenced once is **inlined** like a subquery, and
you choose explicitly with `AS MATERIALIZED` (force the fence — useful when the CTE is expensive and
referenced twice) or `AS NOT MATERIALIZED`. A **recursive** CTE is the SQL answer to hierarchies and
graphs — org charts, category trees, bill of materials, "all reports of this manager": an anchor member
seeds the result, the recursive member joins the previous iteration to the table until no new rows appear.
Always protect against **cycles** (a path array, or `CYCLE` in PostgreSQL 14+) and prefer `UNION ALL`
(`UNION` de-duplicates every iteration at a cost). CTEs can also contain `INSERT/UPDATE/DELETE …
RETURNING`, which lets you move rows between tables atomically in one statement.

**Example:**

```sql
-- All direct and indirect reports of employee 1, with depth and a cycle guard.
with recursive tree as (
    select id, name, manager_id, 1 as depth, array[id] as path
    from employees where id = 1
  union all
    select e.id, e.name, e.manager_id, t.depth + 1, t.path || e.id
    from employees e
    join tree t on e.manager_id = t.id
    where e.id <> all (t.path)               -- stop if the data contains a loop
)
select repeat('  ', depth - 1) || name as org_chart, depth
from tree order by path;

-- Archive and delete in one atomic statement.
with moved as (delete from orders where created_at < now() - interval '2 years' returning *)
insert into orders_archive select * from moved;
```

**Why it's a trap:** "CTEs are always materialized, so they're a performance trick" is pre-2019 folklore;
on PostgreSQL 12+ it is usually the opposite. And a recursive CTE over data that contains a cycle (a
manager who reports to their own report) loops forever — a guard is part of the answer, not an extra.

#### Q16. How do you find consecutive sequences — "users who logged in 3+ days in a row" or the gaps in an id column ("gaps and islands")? {#find-consecutive-sequences-users-logged}
**Answer:** The island trick: within each partition, subtract a `row_number()` from the value. For
consecutive values the difference is **constant**, so it labels each island; group by that label to get
start, end and length. Works for dates (`date - integer` gives a date), integers, and timestamps truncated
to the day. To list *gaps* instead, compare each row with the next one using `lead()` and keep rows where
the distance is greater than one. De-duplicate first: two logins on the same day would break the constant
difference.

**Example:**

```sql
-- Streaks of 3+ consecutive login days per user.
with d as (select distinct user_id, login_date from logins),
g as (
    select user_id, login_date,
           login_date - (row_number() over (partition by user_id order by login_date))::int as island
    from d
)
select user_id, min(login_date) as streak_start, max(login_date) as streak_end, count(*) as days
from g
group by user_id, island
having count(*) >= 3
order by days desc;

-- Gaps in an id sequence (1,2,3,7,8 -> gap 4..6).
select id + 1 as gap_start, next_id - 1 as gap_end
from (select id, lead(id) over (order by id) as next_id from tickets) t
where next_id - id > 1;
```

**Why it's a trap:** skipping the `distinct` (duplicate days) or ordering by a non-unique column makes the
streak arithmetic wrong without any error. Also, the "gap" in a generated id column is usually *not* a bug
(rolled-back inserts consume sequence values — S21).

#### Q17. `EXISTS` vs `IN` vs `JOIN`: how do you write "customers with no orders" and "customers who bought *every* product in a category"? {#exists-join-write-customers-orders}
**Answer:** A **semi-join** ("has at least one matching row") is best written `EXISTS`: it stops at the
first match and can never multiply rows. An **anti-join** ("has none") is `NOT EXISTS` (or `LEFT JOIN … WHERE
right.id IS NULL`) — never `NOT IN (subquery)`, which breaks on `NULL` (Q10, S17). A plain `JOIN` used as a
filter returns a customer once *per matching order*, so you end up adding `DISTINCT` to hide the bug. In
modern PostgreSQL `IN (subquery)` and `EXISTS` usually get the same semi-join plan, so choose by
readability and `NULL` safety, and confirm with `EXPLAIN`. **Relational division** ("*all* of a set") is
solved by counting: join, filter to the set, group by the entity, and compare the distinct count to the
size of the set.

**Example:**

```sql
-- Semi-join: customers with at least one PAID order (each customer once).
select c.id, c.name from customers c
where exists (select 1 from orders o where o.customer_id = c.id and o.status = 'PAID');

-- Anti-join: customers who never ordered (NULL-safe).
select c.id, c.name from customers c
where not exists (select 1 from orders o where o.customer_id = c.id);

-- Division: customers who bought EVERY product of category 5.
select o.customer_id
from orders o
join order_items i on i.order_id = o.id
join products p    on p.id = i.product_id
where p.category_id = 5
group by o.customer_id
having count(distinct p.id) = (select count(*) from products where category_id = 5);
```

**Why it's a trap:** `select distinct c.* from customers c join orders o …` "works" on the demo data and then
sorts/de-duplicates millions of rows in production; and the division query is wrong if you count rows
instead of `count(distinct …)` — buying the same product twice would qualify.

#### Q18. How do you build a pivot or a conditional report in one pass — `FILTER`, `CASE`, `ROLLUP`? {#build-pivot-conditional-report-one}
**Answer:** Instead of running one query per metric (or joining the same table to itself five times),
aggregate **once** and put the condition *inside* the aggregate: `count(*) FILTER (WHERE status =
'CANCELLED')` (PostgreSQL syntax; `sum(case when … then … end)` is the portable form). One scan of the table
yields every column of the report. `GROUPING SETS`, `ROLLUP` and `CUBE` add subtotal and grand-total rows
in the same pass. Guard ratios against division by zero with `nullif(denominator, 0)`, and remember that
aggregates ignore `NULL`s (Q10) — `avg(x) filter (…)` over zero matching rows is `NULL`, not `0`.

**Example:**

```sql
select date_trunc('month', created_at)::date                                   as month,
       count(*)                                                                as orders,
       count(*) filter (where status = 'CANCELLED')                            as cancelled,
       round(100.0 * count(*) filter (where status = 'CANCELLED')
                   / nullif(count(*), 0), 1)                                   as cancel_pct,
       sum(total) filter (where status = 'PAID')                               as paid_revenue
from orders
group by 1
order by 1;

-- Subtotals per country and a grand total in the same pass.
select coalesce(c.country, 'ALL') as country, coalesce(o.status, 'ALL') as status, count(*)
from orders o join customers c on c.id = o.customer_id
group by rollup (c.country, o.status);
```

**Why it's a trap:** running N separate `count(*)` queries (or N self-joins) multiplies the I/O by N and
produces numbers read at slightly different moments (Q25, S13); a single conditional aggregate is both faster
and consistent.

#### Q19. Show self-joins, correlated subqueries and "latest row per group" — and how you'd avoid the per-row re-execution. {#show-self-joins-correlated-subqueries}
**Answer:** A **self-join** compares rows of the same table: "employees who earn more than their manager"
joins `employees e` to `employees m` on `m.id = e.manager_id`. A **correlated subquery** references the
outer row and is conceptually re-run for each of them ("above their department's average") — readable, but
on a big table you usually rewrite it as a join to a pre-aggregated set or as a window function, so the
aggregate is computed once per group instead of once per row. For **"latest row per group"** PostgreSQL has
`DISTINCT ON`, which keeps the first row of each group according to `ORDER BY` — the shortest and usually
fastest form (with an index on `(customer_id, created_at desc)` it can walk the index); the portable
alternative is `row_number() = 1`.

**Example:**

```sql
-- Self-join: employees earning more than their manager.
select e.name, e.salary, m.name as manager, m.salary as manager_salary
from employees e join employees m on m.id = e.manager_id
where e.salary > m.salary;

-- Above their department's average: correlated subquery vs a window (one pass over the data).
select name from employees e
where salary > (select avg(salary) from employees where department_id = e.department_id);

select name from (select name, salary, avg(salary) over (partition by department_id) as dept_avg
                  from employees) t
where salary > dept_avg;

-- Latest order of every customer.
select distinct on (customer_id) customer_id, id as order_id, total, created_at
from orders
order by customer_id, created_at desc, id desc;
```

**Why it's a trap:** with `DISTINCT ON`, the `ORDER BY` must *start with* the `DISTINCT ON` expressions, and
without a unique tie-breaker (`id desc`) two orders at the same timestamp make the "latest" arbitrary — a
flaky result that only shows up when data is imported in bulk.

#### Q20. Write an upsert, return the affected row, and explain where `ON CONFLICT` and `MERGE` differ. {#write-upsert-return-affected-row}
**Answer:** `INSERT … ON CONFLICT (cols) DO UPDATE SET …` is PostgreSQL's atomic "insert or update": the
unique index arbitrates the race, so two concurrent statements cannot both insert (the very bug of S7). Use
`EXCLUDED.col` to refer to the proposed row, and `RETURNING` to get the final row (or generated id) back
without a second query. `DO NOTHING` skips silently — and then **returns no row** for the conflicting
case, so "insert if absent and give me the id" needs a small `UNION ALL` fallback. `MERGE` (PostgreSQL 15+)
is the SQL-standard multi-branch statement (`WHEN MATCHED … WHEN NOT MATCHED …`, including `DELETE`
branches) suited to set-based synchronisation from a staging table, but unlike `ON CONFLICT` it does not
guarantee insertion under concurrency: a concurrent insert can still raise a unique violation that you must
retry.

**Example:**

```sql
-- Atomic counter: insert the first hit, increment afterwards, no read-then-write race.
insert into page_views (page_id, day, views)
values (7, current_date, 1)
on conflict (page_id, day) do update set views = page_views.views + 1
returning views;

-- "Insert if absent, always give me the id" (DO NOTHING returns nothing on conflict).
with ins as (
    insert into tags (name) values ('sql') on conflict (name) do nothing returning id
)
select id from ins
union all
select id from tags where name = 'sql'
limit 1;

-- MERGE (PG 15+): sync stock from a staging table in one statement.
merge into stock s
using incoming i on s.sku = i.sku
when matched     then update set qty = s.qty + i.qty
when not matched then insert (sku, qty) values (i.sku, i.qty);
```

**Why it's a trap:** `ON CONFLICT` still consumes a sequence value for every attempt (so gaps appear),
a single statement cannot update the same target row twice (`cannot affect row a second time` when the
input contains duplicates), and `DO UPDATE` always writes a new row version even if nothing changed — add a
`WHERE` clause to skip no-op updates on hot tables (bloat, S14).

### Indexing & query plans

#### Q21. What index types does PostgreSQL offer beyond the default B-tree, and when do you reach for each? {#index-types-postgresql-offer-beyond}
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

#### Q22. Why does column order matter in a composite (multi-column) index? {#column-order-matter-composite-multi}
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

#### Q23. When can adding an index make performance worse? {#adding-index-make-performance-worse}
**Answer:** An index is a second data structure the database must keep consistent, so it trades **write cost and space for
read speed**, and the trade is not always worth it. It hurts when: (1) **the table is write-heavy**: every `INSERT`/`UPDATE`/
`DELETE` must update every index (and an `UPDATE` of an indexed column defeats HOT updates in PostgreSQL), so ten indexes
make writes roughly ten times more expensive and generate more WAL and vacuum work; (2) **the column has low selectivity**
(a boolean or a `status` with 3 values where one value is 95% of rows): the planner correctly prefers a sequential scan
because following an index to most of the table is slower than reading it in order; (3) **the table is small**: it fits in a
few pages and a scan is cheaper than an index lookup; (4) **the index is never used** (wrong column order, a function on the
column such as `WHERE lower(email) = ...` without an expression index, an implicit cast, a leading wildcard `LIKE '%x'`),
so you pay maintenance for nothing; (5) **it is redundant** (`(a)` next to `(a, b)`); (6) **it bloats memory**: indexes
compete with table data for `shared_buffers`/page cache, evicting useful pages. Fixes: partial indexes
(`WHERE status = 'PENDING'`), covering `INCLUDE` columns, dropping unused indexes found via
`pg_stat_user_indexes.idx_scan = 0`, and always validating with `EXPLAIN (ANALYZE, BUFFERS)` before and after (see
[Persistence Q24](persistence-sql-postgres.md#read-analyze-output-diagnose-slow)). Create indexes in production with `CREATE INDEX CONCURRENTLY` to avoid
blocking writes.

**Example:**

```sql
-- Index on a 3-value column: planner ignores it for the common value.
CREATE INDEX idx_appt_status ON appointment(status);
EXPLAIN SELECT * FROM appointment WHERE status = 'CONFIRMED';   -- Seq Scan (95% of rows)

-- Better: index only the rare, interesting rows.
CREATE INDEX CONCURRENTLY idx_appt_pending ON appointment(start_at) WHERE status = 'PENDING';

-- Find indexes that cost you writes but are never read:
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;
```

**Why it's a trap:** "slow query? add an index" is a reflex, and each extra index silently slows every write and every
migration. Decide from the query plan and from the read/write ratio, not from habit
(see also [Persistence Q22](persistence-sql-postgres.md#column-order-matter-composite-multi) on composite-index column order).

#### Q24. How do you read `EXPLAIN ANALYZE` output to diagnose a slow query? {#read-analyze-output-diagnose-slow}
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

```text
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

### Transactions & concurrency

#### Q25. Name the transaction isolation levels and the anomalies each one prevents. {#name-transaction-isolation-levels-anomalies}
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

#### Q26. Explain optimistic vs. pessimistic locking in terms of actual contention, not just the definitions. {#optimistic-pessimistic-locking-terms-contention}
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

#### Q27. How can PostgreSQL itself act as a work queue with `SELECT ... FOR UPDATE SKIP LOCKED`, and what are the limits? {#postgresql-itself-act-queue-select}
**Answer:** Several workers polling a `jobs` table would normally either process the same row
twice or block on each other's row locks. `FOR UPDATE SKIP LOCKED` makes each worker's query
take the first rows *nobody else currently holds* and silently skip locked ones, so N workers
claim disjoint batches concurrently with no coordination service. The correct shape is
**claim-then-process**: in one short transaction, select-and-mark rows (`status = 'RUNNING'`, a
`locked_at`/lease timestamp, a worker id), commit, do the slow work *outside* any transaction,
then mark done. Holding the row lock open for the whole job would pin a connection and a
transaction (blocking vacuum, S19), so it is not a substitute. Because the claim is committed, a
crashed worker leaves a row stuck in `RUNNING` — you need a **reaper** that re-queues rows whose
lease expired, which means jobs run *at least once* and handlers must be idempotent ([Messaging Q13](messaging-rabbitmq-kafka.md#consumer-idempotent-even-messaging-system)). Other limits: ordering is only approximate under concurrency, there is no built-in retry
backoff, dead-letter or fan-out, polling adds latency and load (mitigate with `LISTEN/NOTIFY`), and
throughput tops out well below a real broker. It is an excellent fit for modest volumes where
you want the job and its business data in the *same transaction* (a lightweight outbox, module
4 Q38) and a poor fit as a general event bus.

**Example:**

```sql
-- Claim up to 10 jobs atomically; concurrent workers never receive the same row.
with next as (
    select id
    from jobs
    where status = 'PENDING' and run_at <= now()
    order by run_at, id
    limit 10
    for update skip locked
)
update jobs j
set status = 'RUNNING', locked_at = now(), attempts = attempts + 1
from next
where j.id = next.id
returning j.*;

-- Reaper (run periodically): give back jobs whose worker died.
update jobs set status = 'PENDING'
where status = 'RUNNING' and locked_at < now() - interval '10 minutes';
```

**Why it's a trap:** candidates either dismiss it ("use a broker") or over-trust it. The
interview-worthy points are the claim/lease split, the reaper, and the resulting at-least-once
semantics — without them the queue works in a demo and stalls or double-processes after the
first worker crash.

#### Q28. How do you prevent two concurrent requests from booking the same appointment slot? {#prevent-two-concurrent-requests-booking}
**Answer:** The invariant ("one confirmed appointment per doctor and time slot") must be enforced **by the database**, because
application checks (`if (!exists) insert`) are check-then-act races: two requests both see the slot as free, both insert.
Options, from strongest and simplest to heaviest: (1) **Unique constraint** on `(doctor_id, slot_start)` (a partial unique
index `WHERE status = 'CONFIRMED'` lets cancelled rows coexist): the second `INSERT` fails with a unique violation that you
translate to `409 Conflict`. It needs no lock, scales well and cannot be bypassed by a bug in another service. For
variable-length appointments use a PostgreSQL **exclusion constraint** (`EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_at, end_at) WITH &&)`)
which rejects any overlapping range. (2) **Pessimistic lock**: `SELECT ... FROM slot WHERE id = ? FOR UPDATE` inside the
transaction serialises writers on that row; simple to reason about but holds a connection and can deadlock or queue under
a hot slot (`FOR UPDATE SKIP LOCKED`, `NOWAIT` help). (3) **Optimistic lock**: a `@Version` column on the slot row; the
loser's `UPDATE ... WHERE version = ?` affects 0 rows and Hibernate throws `OptimisticLockException`, which you map to 409
or retry. Best when conflicts are rare. (4) **Serializable isolation** with retry on serialization failure: correct but
costly and needs retry logic everywhere. Pair the database guard with an **idempotency key** so a client retry after a
timeout returns the same booking instead of a second attempt (see [Full Stack Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need)). Cache
availability for browsing if you like, but never use the cache as the source of truth for the booking decision.

**Example:**

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE appointment ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_at, end_at) WITH &&)
  WHERE (status = 'CONFIRMED');
```

```java
@Transactional
public Appointment book(BookCommand c) {
    try {
        return repo.saveAndFlush(new Appointment(c.doctorId(), c.start(), c.end(), c.patientId()));
    } catch (DataIntegrityViolationException e) {          // unique/exclusion violation from PostgreSQL
        throw new SlotAlreadyTakenException(c.doctorId(), c.start()); // -> 409 Conflict via @ControllerAdvice
    }
}
```

**Why it's a trap:** `saveAndFlush` matters: with a plain `save` the violation only surfaces at commit, outside your
`try/catch`, and the client gets a 500. Also, `SERIALIZABLE`/`REPEATABLE READ` do not help with an application-level
`exists` check across two statements unless you retry; the constraint is the reliable answer
(see [Persistence Q25](persistence-sql-postgres.md#name-transaction-isolation-levels-anomalies) for isolation levels and
[Persistence Q26](persistence-sql-postgres.md#optimistic-pessimistic-locking-terms-contention) for optimistic vs pessimistic locking; the end-to-end design is in
[System Design Q45](system-design.md#design-ticket-seat-booking-system)).

### ORM & Hibernate

#### Q29. What's the N+1 query problem, and name two ways to fix it. {#n-1-query-problem-name}
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

#### Q30. Name the four Hibernate entity states, with a usage example for each. {#name-four-hibernate-entity-states}
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
`merge()` silently discards that newer write with no conflict detection, unless `@Version` (Q26)
is also in play to catch it.

#### Q31. Why are ORM-generated inserts/updates often slow in bulk, and how do you fix it? {#orm-generated-inserts-updates-often}
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

#### Q32. How does MyBatis's approach to persistence differ from JPA/Hibernate's, and when is that difference the deciding factor? {#mybatis-approach-persistence-differ-jpa}
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

#### Q33. What does calling `flush()` on a persistence context actually do, and how does it differ from `commit()`? {#calling-flush-persistence-context-differ}
**Answer:** `flush()` pushes all pending changes to the database immediately but does **not**
commit the transaction — it just synchronizes the persistence context (the first-level cache)
with the database early, which is sometimes necessary before running a query that needs to see
those uncommitted changes (e.g. a native query bypassing the persistence context). `commit()`
ends the transaction, making the changes permanent (and, depending on isolation level, visible
to other transactions) — a flush without a commit can still be rolled back.

**Example:**

```java
entityManager.persist(order);
entityManager.flush();       // INSERT is sent to the DB now, but the transaction is still open

Integer count = (Integer) entityManager
    .createNativeQuery("select count(*) from orders where id = :id")
    .setParameter("id", order.getId())
    .getSingleResult();      // sees the flushed row, because a native query bypasses
                              // the first-level cache and hits the DB directly

// entityManager.getTransaction().rollback(); // still fully reversible at this point —
                                                // the flushed INSERT is undone with everything else
```

**Why it's a trap:** candidates conflate "the data hit the database" with "the data is
permanent." Flushing early is sometimes necessary, but a flush is not a commit — the change is
still fully reversible until the transaction actually ends.

### Connections & topology

#### Q34. How do you size a HikariCP connection pool, and what's the common sizing mistake? {#size-hikaricp-connection-pool-common}
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

#### Q35. How do you configure and safely route to multiple data sources in one Spring application? {#configure-safely-route-multiple-data}
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

#### Q36. What breaks when you naively add a read replica for scaling reads? {#breaks-naively-add-read-replica}
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

*See also:* [System Design Q21](system-design.md#read-own-writes-break-under) for read-your-own-writes strategies across the whole architecture.

### Schema & modeling

#### Q37. What's the safe process for a schema migration in a production database, and what tools manage this? {#safe-process-schema-migration-production}
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

-- V2: backfill in batches (see Q31/S12), not one giant UPDATE.
-- Application deploy: reads switch to email_normalized.

-- V3, once fully cut over:
alter table users drop column email;
```

**Why it's a trap:** the "obvious" single migration — add the `NOT NULL` column directly in one
step — often runs fine against a small staging database with light load, then locks or fails
against production simply because production has orders of magnitude more rows and concurrent
traffic staging never had; the multi-step pattern isn't extra caution, it's the only version that
scales to production's actual size and concurrency.

#### Q38. When should a column be `JSONB` versus a properly normalized set of tables? {#column-jsonb-properly-normalized-set}
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

#### Q39. Soft deletes vs. hard deletes — what's the actual trade-off? {#soft-deletes-hard-deletes-trade}
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

### Schema & indexing design

#### Q40. Auto-increment `bigint`, random UUID (v4) or time-ordered UUID (v7) for primary keys — how do you choose? {#auto-increment-bigint-random-uuid}
**Answer:** Each option optimizes something different. A **`bigint` identity/sequence** is small (8 bytes), the
index is dense and inserts always go to the right-most B-tree page (excellent locality and cache
behaviour), and joins are fast; the downsides are that ids are guessable (enumeration attacks
unless authorization is correct, [Spring Q41](spring-architecture.md#authorization-live-url-rules-method)), they leak volume ("we have 4,231 orders"),
they need a central sequence, and merging data from several databases collides. A **random UUIDv4**
can be generated anywhere without coordination and is unguessable, but it is 16 bytes and
*uniformly random*, so every insert lands on a random leaf page of the primary key index: page
splits, a much larger working set that no longer fits in cache, write amplification (WAL
full-page images), and noticeably worse insert throughput and index size at hundreds of millions
of rows. A **UUIDv7** keeps the 16-byte, globally unique property but puts a millisecond timestamp
in the high bits, so new keys are roughly increasing — insert locality similar to a sequence —
while staying distributed-friendly (PostgreSQL 18 ships a built-in `uuidv7()`; earlier versions
need an extension or generate it in the application). Two further considerations: the timestamp
in a v7 key leaks *creation time*, and secondary indexes and every foreign key column repeat the
key, so 16 vs 8 bytes multiplies through the schema. With Hibernate, use a
`SEQUENCE` generator with `allocationSize` matching the DB increment (the `IDENTITY` strategy
disables JDBC insert batching, Q31). My default recommendation: an internal `bigint` primary key
for joins plus, if externally visible identifiers are required, a separate random public id (or
UUIDv7 as the primary key when ids are generated in many services or clients); avoid v4 as a
clustered-insert hot path on large tables, and decide once — changing primary key types later is
one of the most expensive migrations there is.

**Example:**

```sql
create table orders (
    id         bigint generated always as identity primary key,  -- 8 bytes, insert-local, internal joins
    public_id  uuid not null default uuidv7() unique,           -- exposed in URLs/APIs (PG 18; earlier: generate in the app)
    created_at timestamptz not null default now()
);
-- 8 vs 16 bytes repeats in every FK column and secondary index (100M rows x 3 indexes ~ GBs)
```

**Why it's a trap:** "UUIDs are better because they're modern/distributed" ignores that a random v4 key
turns every insert into a random page write on a big index — fine at 1M rows, painful at 500M — and
that the key type is almost impossible to change later.

#### Q41. Design the schema and indexing strategy for a high-write, append-heavy feed/event table expected to reach billions of rows. {#design-schema-indexing-strategy-high}
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

#### Q42. Design the indexing for a search screen that filters orders by status and date, looks customers up by e-mail case-insensitively, and supports "contains" text search. Which index features do you use? {#design-indexing-search-screen-filters}
**Answer:** This is a toolkit question: match each query shape to the smallest index that serves it, since every
index costs write throughput, disk and vacuum work. (1) **Composite B-tree** for the main
list — equality columns first, range/sort column last (Q22): `(customer_id, status, created_at desc)`.
(2) **Partial index** when queries touch a small hot subset: if 95% of rows are `DELIVERED` but the
screen reads `PENDING`, `create index on orders (created_at) where status = 'PENDING'` is tiny,
cheap to maintain and exactly as selective as needed; the query's `WHERE` must imply the index
predicate. (3) **Covering index** with `INCLUDE (total, customer_name)` lets PostgreSQL answer
from the index alone — an *index-only scan* — avoiding heap fetches; it only works if the
visibility map is current (regular vacuum) and every extra included column widens the index. (4)
**Expression index** for functions: `where lower(email) = lower(:e)` cannot use a plain index on
`email`; `create index on customers (lower(email))` (or the `citext` type) can, and the query must
use the *same expression*. (5) **`LIKE '%term%'`** and `ILIKE` can't use a B-tree at all (no
fixed prefix), so a leading-wildcard search scans the table; the fix is a **trigram GIN/GiST index**
(`pg_trgm`, `create index ... using gin (name gin_trgm_ops)`), or real full-text search
(`tsvector` + GIN) if it is linguistic search, or an external search engine when relevance, facets
and typo-tolerance matter. (6) Always build on a live table with `CREATE INDEX CONCURRENTLY` (it
takes longer and can't run in a transaction, and a failed run leaves an `INVALID` index to drop),
and periodically remove indexes that `pg_stat_user_indexes.idx_scan` shows are never used —
each one still slows every `INSERT`/`UPDATE`, and an update that touches an indexed column
loses PostgreSQL's cheap HOT-update path. Prove each choice with `EXPLAIN (ANALYZE, BUFFERS)` (Q24)
on production-sized data rather than intuition.

**Example:**

```sql
create index idx_orders_pending on orders (created_at) where status = 'PENDING';   -- partial
create index idx_orders_list on orders (customer_id, status, created_at desc)
    include (total);                                                                 -- covering
create index idx_customers_email on customers (lower(email));                        -- expression
create extension if not exists pg_trgm;
create index idx_customers_name_trgm on customers using gin (name gin_trgm_ops);    -- LIKE '%term%'
create index concurrently idx_x on orders (created_at);                              -- never block writes
```

**Why it's a trap:** answering "add an index on every filtered column" — each index taxes every write,
and the wrong shape (wrong column order, `lower()` mismatch, leading wildcard) is silently ignored by the planner.

#### Q43. When is table partitioning the right answer in PostgreSQL, and what does it cost you? {#table-partitioning-right-answer-postgresql}
**Answer:** Declarative partitioning (`PARTITION BY RANGE (created_at)`, or `LIST`/`HASH`) splits one
logical table into physical child tables. It pays off in three situations: **retention** (dropping
or detaching an old partition is an instant metadata operation, whereas `DELETE`-ing 200 million
old rows generates the same amount of WAL, dead tuples and vacuum work — the append-heavy table in
Q41 is the textbook case), **partition pruning** (a query with a filter on the partition key only
touches the relevant partitions, so "last 7 days" scans one or two children instead of a
multi-year index), and **maintenance granularity** (vacuum, reindex and backups run per partition
rather than on one 2 TB object). The costs are real and are why it is not the first thing to
try. Pruning only happens when the query *filters on the partition key* — a query without a
`created_at` predicate scans every partition and is slower than before. Every primary key or
unique constraint must **include the partition key**, so there is no cheap global uniqueness on
`id` alone. Too many partitions (thousands) make planning slow and use memory, so pick a
granularity that yields tens to low hundreds — daily for very high volume, monthly otherwise.
Partitions must be created *ahead of time* (a job or `pg_partman`), or inserts fail the day
nobody created next month's — always keep a `DEFAULT` partition or an alert on it. Foreign keys
*to* a partitioned table have restrictions, and schema changes must be applied consistently to
all children. My decision rule: don't partition until the table is large enough that vacuum,
index size or retention deletes actually hurt (often hundreds of millions of rows or hundreds of
GB), and the dominant queries already filter on time; before that, a good composite/partial index
(Q42) and archiving are simpler. If retention is the *only* reason, a partitioned table's
`DROP PARTITION` is the strongest argument. Test with `EXPLAIN` that pruning really occurs
(`Subplans Removed`/only relevant partitions listed) and monitor row count per partition to spot skew.

**Example:**

```sql
create table events (
    id bigint generated always as identity, created_at timestamptz not null, payload jsonb,
    primary key (id, created_at)                        -- PK must include the partition key
) partition by range (created_at);
create table events_2026_10 partition of events for values from ('2026-10-01') to ('2026-11-01');
create table events_default partition of events default;

alter table events detach partition events_2026_01;   -- instant retention, no 200M-row DELETE
drop table events_2026_01;

explain select * from events where created_at >= now() - interval '7 days';  -- expect only recent partitions listed
```

**Why it's a trap:** partitioning "for performance" on a table that is not yet painful, with queries that don't filter
on the partition key — you pay planning overhead and lose global uniqueness for no pruning benefit.

### Evolution & trade-offs

#### Q44. How do you safely add a `NOT NULL` column to a 50-million-row table with zero downtime? {#safely-add-null-column-50}
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
concurrently with normal operations); (4) finish with `SET NOT NULL`: since PostgreSQL 12 it skips the full-table scan when a
validated `CHECK (col IS NOT NULL)` already proves the rule, so it is instant; then drop the now-redundant
check. Deploy the application code that always writes the new column *before* step 3 so no new `NULL`
can appear while the constraint is being validated. The pattern
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

-- Step 4: PG12+ sees the validated CHECK and skips the scan; then drop the redundant check.
alter table orders alter column region set not null;
alter table orders drop constraint orders_region_not_null;
```

**Why it's a trap:** the migration that "just works" in a staging environment with a few thousand
rows and no concurrent traffic is exactly the one that locks production for the duration of a
full-table validation — the difference only shows up at production's actual scale, which is
precisely why this has to be a deliberate, tested pattern rather than something discovered the
hard way during a deploy.

#### Q45. When do you deliberately denormalize, and how do you keep the denormalized copy consistent? {#deliberately-denormalize-keep-denormalized-copy}
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

#### Q46. Walk me through optimizing a slow, complex query step by step. {#optimizing-slow-complex-query-step}
**Answer:** Follow a fixed loop and change **one thing at a time**, re-measuring after each: (1) get the real
plan — `EXPLAIN (ANALYZE, BUFFERS)` on production-sized data (Q24); (2) find the *dominant* node (the one
with most time, or loops × per-loop cost), not the first suspicious one; (3) check estimates vs actuals —
a large gap means statistics, not SQL, is the problem; (4) fix in order of cheapness and safety: make
predicates **sargable** (no function or cast on the indexed column), cut the rows early (filter, aggregate
and `LIMIT` *before* joining wide tables), remove per-row work (correlated subqueries), then add or reshape
**an index** (Q22, Q42), then give the sort/hash enough `work_mem`, and only last pre-compute (summary
table, materialized view). Stop when you reach the target — each step below also costs complexity.

The case study: *"top 10 customers by revenue in the last 90 days, with their most recent order date"* on
2M `customers`, 20M `orders` (2 years), 80M `order_items`. Numbers are **illustrative** (typical of this
kind of workload, not a benchmark) — reproduce them on your own data; the shape of the gains is the point.

**Step 0 — baseline (≈ 38 s).**

```sql
select c.id, c.name,
       (select sum(oi.quantity * oi.unit_price)
        from orders o join order_items oi on oi.order_id = o.id
        where o.customer_id = c.id
          and date_trunc('day', o.created_at) >= current_date - 90
          and o.status <> 'CANCELLED')                    as revenue,
       (select max(o.created_at) from orders o where o.customer_id = c.id) as last_order_at
from customers c
where c.id in (select customer_id from orders
               where date_trunc('day', created_at) >= current_date - 90)
order by revenue desc nulls last
limit 10;
```

```text
Limit  (actual time=38112..38112 rows=10)
  ->  Sort (Sort Method: top-N heapsort)
        ->  Hash Semi Join (actual rows=612000)
              ->  Seq Scan on customers
              ->  Hash -> Seq Scan on orders   Filter: (date_trunc('day', created_at) >= ...)
                           Rows Removed by Filter: 17,540,000
        SubPlan 1  (actual time=0.041..0.052 rows=1 loops=612000)    <- ~31 s of the total
        SubPlan 2  (actual time=0.004..0.005 rows=1 loops=612000)
Execution Time: 38125 ms
```

Read it: the dominant cost is `SubPlan 1` with **`loops=612000`** — a tiny per-row cost executed 612,000
times — and the filter wraps `created_at` in `date_trunc`, so no index on that column could be used.

**Step 1 — make the predicate sargable (≈ 35 s, no big gain yet).** `date_trunc('day', created_at) >=
current_date - 90` is equivalent to `created_at >= current_date - 90`, with the column left bare. By itself
this saves little (there is still no index on `created_at`) but it is the **prerequisite** for step 4 —
a good lesson: some steps do not pay off alone.

**Step 2 — remove the per-row subqueries: aggregate once, then join (≈ 6 s).**

```sql
with recent as (
    select o.customer_id,
           sum(oi.quantity * oi.unit_price) as revenue
    from orders o
    join order_items oi on oi.order_id = o.id
    where o.created_at >= current_date - 90
      and o.status <> 'CANCELLED'
    group by o.customer_id
)
select c.id, c.name, r.revenue
from recent r join customers c on c.id = r.customer_id
order by r.revenue desc
limit 10;
```

612,000 correlated executions became one hash join and one hash aggregate: `Parallel Seq Scan on orders`
(2.4M rows kept), `Hash Join` on `order_items`, `HashAggregate`. The rewrite also lets the planner
drop the useless `customers` scan, and we only join `customers` for rows that survive. **Check the semantics**
when rewriting: `last_order_at` was dropped from this version on purpose — see step 3.

**Step 3 — `LIMIT` before the wide join, fetch the extras only for the winners (≈ 5.5 s).**

```sql
with top as (
    select o.customer_id, sum(oi.quantity * oi.unit_price) as revenue
    from orders o join order_items oi on oi.order_id = o.id
    where o.created_at >= current_date - 90 and o.status <> 'CANCELLED'
    group by o.customer_id
    order by revenue desc
    limit 10                                           -- cut to 10 rows BEFORE anything else joins
)
select c.id, c.name, t.revenue, lo.created_at as last_order_at
from top t
join customers c on c.id = t.customer_id
cross join lateral (select created_at from orders
                    where customer_id = c.id order by created_at desc limit 1) lo
order by t.revenue desc;
```

"Most recent order" is now computed for 10 customers (10 index lookups on `orders(customer_id,
created_at desc)`), not 612,000, and it keeps the original meaning (last order *ever*).

**Step 4 — index for the filter, covering what the query reads (≈ 2.4 s).**

```sql
create index concurrently orders_recent_idx
    on orders (created_at) include (customer_id, status);   -- sargable range + index-only scan
create index concurrently orders_cust_created_idx on orders (customer_id, created_at desc);
```

```text
->  Index Only Scan using orders_recent_idx on orders
      Index Cond: (created_at >= (CURRENT_DATE - 90))   Heap Fetches: 0
      Buffers: shared hit=9412 read=2216      (was: read=1,380,000 by the Seq Scan)
```

The 90-day slice is read straight from the index (`Heap Fetches: 0` requires a recent vacuum — Q42) instead
of scanning 20M rows. Reasoning for the shape: range column first because the only index predicate is a
range; `INCLUDE` keeps `customer_id`/`status` out of the sort key.

**Step 5 — stop the spill and fix the estimate (≈ 1.5 s).**

```text
HashAggregate  Batches: 17  Memory Usage: 4145kB  Disk Usage: 381MB     <- spilling
```

`work_mem` (4 MB default) is too small for 600k groups, so the hash aggregate writes batches to disk.
Raise it **for this role or transaction only** (`set local work_mem = '128MB'`), not globally ×
`max_connections`. If the plan shows `rows=2400` estimated vs `2,460,000` actual after a data load, run
`ANALYZE orders` (S22) before touching anything else.

**Step 6 — only if 1.5 s is still too slow: pre-compute (≈ 40 ms).**

```sql
create materialized view customer_revenue_daily as
select o.customer_id, o.created_at::date as day, sum(oi.quantity * oi.unit_price) as revenue
from orders o join order_items oi on oi.order_id = o.id
where o.status <> 'CANCELLED'
group by 1, 2;
create unique index on customer_revenue_daily (customer_id, day);       -- required for CONCURRENTLY
refresh materialized view concurrently customer_revenue_daily;           -- schedule hourly/nightly
```

The dashboard then sums ≤ 90 small rows per customer. The price: data is as fresh as the last refresh and
you now own a refresh job (Q45 — name how staleness is detected).

| Step | Change | Time | Why it helped |
|---|---|---|---|
| 0 | baseline | 38 s | 612k correlated sub-plans, function on column |
| 1 | sargable predicate | 35 s | prerequisite only |
| 2 | aggregate once, join | 6 s | 612,000 executions → 1 hash agg |
| 3 | `LIMIT` first, `LATERAL` for extras | 5.5 s | fewer rows through every later node |
| 4 | covering range index | 2.4 s | 20M-row scan → 2.4M index entries |
| 5 | `work_mem` / `ANALYZE` | 1.5 s | no disk spill, right join method |
| 6 | materialized view | 0.04 s | pre-aggregated, at the cost of freshness |

**Why it's a trap:** the junior reflex is "add an index on every column in the `WHERE`" — here that would
have changed almost nothing, because the cost was 612,000 correlated executions and a function wrapped around the
column. The senior habit is to read the plan first, name the dominant node, and change one variable at a
time; the equally tempting wrong moves are `set enable_seqscan = off` in production, or raising `work_mem`
globally, or stopping at step 6 before checking whether step 2 was enough.

## 🎯 Real-world scenarios

### S1. A query that used to be fast has become steadily slower as the table has grown {#query-used-fast-has-become}
- **Symptoms:** A specific query's latency has crept up over months in proportion to table
  growth, well beyond what row-count growth alone should cause.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Run `EXPLAIN ANALYZE` (Q24) and check for a `Seq Scan` where an `Index Scan`
  would be expected, or a large mismatch between the planner's estimated and actual row counts
  (stale statistics).
- **Example:**

  ```text
  Seq Scan on orders (actual time=0.02..812.40 rows=1200000 loops=1)
    Filter: (status = 'PENDING')
  Planning Time: 0.10 ms
  Execution Time: 815.02 ms
  ```

  No index exists on `status`, so every query filtering on it scans the whole table — and that
  scan gets linearly slower as the table grows.

- **Resolution:** Add the missing index (checking column order for composite cases, Q22), or run
  `ANALYZE` to refresh statistics if the plan itself is simply wrong due to stale stats, or
  rewrite the query if a function wrapped around the filtered column is preventing index use.
- **Prevention:** Set up `EXPLAIN`-based query review for new hot-path queries before they ship,
  and monitor slow-query logs continuously rather than discovering degradation from user reports.

</details>

### S2. An APM tool flags dozens of near-identical queries firing for a single page load {#apm-tool-flags-dozens-near}
- **Symptoms:** A page that lists 50 items triggers 51+ database queries — one for the list, and
  one per item for an associated collection.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classic N+1 (Q29) — confirm by checking the entity's association fetch type and
  whether the code iterates the collection and accesses a lazy association inside the loop.
- **Example:**

  ```text
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

</details>

### S3. Two concurrent transactions deadlock, and one is aborted by the database {#two-concurrent-transactions-deadlock-one}
- **Symptoms:** Postgres logs a `deadlock detected` error, naming the two conflicting processes
  and the locks each held while waiting on the other; one transaction is automatically rolled
  back to break the cycle.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The log message itself names the exact queries and lock types involved — the
  usual cause is two transactions updating the same two rows (or tables) in opposite order (A
  then B in one transaction, B then A in another).
- **Example:**

  ```text
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

</details>

### S4. Requests fail with the database's own "too many connections" error, independent of the application-level pool size {#requests-fail-database-own-too}
- **Symptoms:** The application's HikariCP pool isn't exhausted (metrics show headroom), but the
  database itself rejects new connections.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check the database server's `max_connections` against the *sum* of every
  application instance's pool size, plus any other clients (admin tools, other services sharing
  the database) — a fleet of instances each sized generously can collectively exceed the
  server's actual limit even though no single instance's pool looks maxed out.
- **Example:**

  ```text
  FATAL: sorry, too many clients already
  ```

  ```text
  show max_connections; -- 100
  -- 12 application instances x maximum-pool-size: 15 each = 180 possible connections,
  -- already over the server's limit even before any admin tooling connects.
  ```

- **Resolution:** Reduce per-instance pool size using the sizing guidance in Q34, or introduce a
  connection pooler (PgBouncer) in front of the database to multiplex many application
  connections over fewer actual database connections.
- **Prevention:** Track total connections across the fleet as a first-class metric against the
  database's configured limit, not just per-instance pool utilization.

</details>

### S5. A schema migration locks a production table and causes a brief outage {#schema-migration-locks-production-table}
- **Symptoms:** A deployment's migration step causes a spike in request latency or outright
  timeouts for the duration the migration ran, on a table under active read/write traffic.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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
  the multi-step pattern from Q44 for anything that would otherwise require a full-table
  rewrite or scan.
- **Prevention:** Require every migration against a large, live table to state explicitly which
  lock it takes and for how long, as part of review — and test migrations against a
  production-sized dataset in staging, not just an empty or small dev database, since lock
  duration scales with table size.

</details>

### S6. A user submits a form, is redirected to a confirmation page, and sees their submission is missing {#user-submits-form-redirected-confirmation}
- **Symptoms:** Intermittent, and specifically tied to write-then-immediate-read flows — the same
  user reloading a moment later sees the data correctly.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classic read-after-write inconsistency from a naive read-replica setup (Q36) —
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

</details>

### S7. Two near-simultaneous requests both create a row for what should be a unique entity, resulting in duplicates {#two-near-simultaneous-requests-both}
- **Symptoms:** Under concurrent load (e.g. a user double-clicking submit, or a retried request
  racing the original), two rows exist for what the business logic assumed could only ever be
  one (two accounts for one email, two orders for one idempotency key).

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S8. `SELECT COUNT(*)` on a large table is unexpectedly slow and shows up as a hot query {#select-count-large-table-unexpectedly}
- **Symptoms:** A dashboard or pagination feature calling `COUNT(*)` on a multi-million-row table
  takes seconds, disproportionate to how simple the query looks.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S9. Optimistic-locking failures spike sharply during a specific high-traffic period {#optimistic-locking-failures-spike-sharply}
- **Symptoms:** `OptimisticLockException` (or equivalent version-conflict error) rates climb
  during a known high-concurrency window (a flash sale, a popular event), causing a wave of
  failed updates that the application surfaces as user-facing errors or silent retries.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** This confirms Q26's point in practice — optimistic locking's failure rate rises
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

</details>

### S10. After an application crash mid-operation, the database is left in an inconsistent state {#after-application-crash-mid-operation}
- **Symptoms:** A multi-step business operation (debit account A, credit account B) is found
  partially applied after a crash — one side happened, the other didn't.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S11. Queries filtering on a `JSONB` column get slower as the table grows, despite the column being indexed {#queries-filtering-jsonb-column-get}
- **Symptoms:** A query like `WHERE metadata @> '{"status": "active"}'` on a `JSONB` column
  degrades with table growth even though "there's an index."

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check the actual index type — a plain B-tree index on a `JSONB` column supports
  only equality on the *whole* JSON value, not containment (`@>`) or key-existence queries; only
  a GIN index (Q21) actually accelerates those operators. A B-tree index existing on the column
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

</details>

### S12. A nightly batch job that updates millions of rows one at a time starts timing out or overwhelming the database {#nightly-batch-job-updates-millions}
- **Symptoms:** A batch job that loops through rows and issues one `UPDATE` per row takes
  increasingly long as data volume grows, and during its run other queries against the same
  table slow down noticeably.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Row-by-row updates in a loop (Q31's pattern, but for updates rather than
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

</details>

### S13. A report occasionally shows numbers that don't add up, only under concurrent write activity {#report-occasionally-shows-numbers-don}
- **Symptoms:** A multi-query report (e.g. sum several tables' values that should reconcile) is
  correct when the system is idle but occasionally inconsistent when generated while writes are
  happening concurrently.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Check the isolation level the report's queries run under — at the default Read
  Committed level (Q25), each individual statement within the report's transaction sees the
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

</details>

### S14. Table and index sizes keep growing even though the row count is roughly stable {#table-index-sizes-keep-growing}
- **Symptoms:** Disk usage for a frequently-updated table climbs steadily, disproportionate to
  its actual (stable or slowly growing) live row count, and query performance degrades alongside
  it.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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

</details>

### S15. Deleting one row unexpectedly deletes a large number of related rows across several tables {#deleting-one-row-unexpectedly-deletes}
- **Symptoms:** Removing what looked like a single, contained entity (e.g. deleting a user)
  cascades into deleting orders, payment records, or audit history that the team assumed would
  be preserved.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

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
  usually also the trigger to introduce soft deletes (Q39) instead of ever hard-deleting them at
  all.
- **Prevention:** Treat `ON DELETE CASCADE` as a deliberate, reviewed decision per relationship,
  not a default reached for convenience — document explicitly, for every foreign key, what should
  happen to the child rows when the parent is deleted.

</details>

### S16. Immediately after a deployment that includes a schema migration, the application starts throwing errors about a missing or unexpected column {#immediately-after-deployment-includes-schema}
- **Symptoms:** Errors like "column does not exist" or a mapping failure appear right after
  deploy, but only on some instances, or only briefly.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Migration and application code deployment aren't atomic together — during a
  rolling deployment, old application instances (expecting the old schema) can still be running
  against a database that's already been migrated to the new schema, or a migration was run
  *after* new application code already started expecting it, briefly exposing a gap.
- **Example:**

  ```text
  ERROR: column "region" of relation "orders" does not exist
  ```

  A new application instance, already deployed and expecting `orders.region`, started receiving
  traffic before the migration that adds that column had actually run against the database — or
  the reverse: old instances still running the previous version choke on a renamed/dropped column
  a migration already applied.

- **Resolution:** Reorder deployment strictly so the migration always completes fully before any
  new application code that depends on it starts receiving traffic, and ensure the migration
  itself is backward-compatible with the *old* application version for the duration old instances
  are still running (this is exactly why Q44's multi-step, additive-first migration pattern
  matters — it's designed so both old and new code work against the in-between schema state).
- **Prevention:** Never ship a migration that both adds a requirement (a new `NOT NULL` column, a
  renamed column) and requires the new code in the same atomic step — always split into an
  additive, backward-compatible migration first, deployed and verified, before a later cleanup
  migration removes what the old code needed.

</details>

### S17. A "customers who never ordered" report suddenly returns zero rows {#customers-never-ordered-report-suddenly}
- **Symptoms:** A marketing query that has listed ~12,000 customers with no orders every week
  now returns an empty result. Nobody changed the query and there were no errors; the customer
  and order counts look normal.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** An empty result from a query that *should* return rows, right after a data
  change, points at `NOT IN` and `NULL` (Q10). Look at what changed in the data: a new "guest
  checkout" feature started inserting orders with `customer_id IS NULL`. Confirm with
  `select count(*) from orders where customer_id is null;` — and check the plan, which shows a
  `NOT (hashed SubPlan)` filter. One `NULL` in the subquery makes `id <> NULL` unknown for every
  customer, so `NOT IN` rejects them all.
- **Example:**

  ```sql
  select id, email
  from customers
  where id not in (select customer_id from orders);   -- 0 rows once any customer_id is NULL
  ```

- **Resolution:** Rewrite as a `NULL`-safe anti-join and re-run the report to confirm the
  ~12,000 rows return:

  ```sql
  select c.id, c.email
  from customers c
  where not exists (select 1 from orders o where o.customer_id = c.id);
  -- or:  left join orders o on o.customer_id = c.id  where o.id is null
  ```

  Also decide whether `orders.customer_id` *should* be nullable; if guest orders are legitimate,
  model them explicitly rather than with a `NULL` foreign key.

- **Prevention:** Team rule: no `NOT IN (subquery)` — use `NOT EXISTS`. Add a lint/review check for
  it; add a test fixture that includes `NULL`s in every nullable column used in a subquery; and
  enforce `NOT NULL` on columns that are never meant to be empty.

</details>

### S18. An infinite-scroll feed and a CSV export get slower each week, and users see repeated or missing rows {#infinite-scroll-feed-csv-export}
- **Symptoms:** The admin "audit events" screen and a nightly export both use paging. Loading
  the last pages now takes 8+ seconds and the database shows periodic CPU spikes whenever a
  crawler or export walks the list. Separately, the export file contains some rows twice and is
  missing others.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** `EXPLAIN (ANALYZE, BUFFERS)` of the slow page query shows an index scan (or a
  sort) that returns ~1,000,050 rows and a `Limit` node discarding all but 50 — the cost is
  proportional to the offset (Q11). The duplicates/misses are the instability half: new events
  were inserted at the top while the export was paging, shifting every later page by the number of
  new rows. Both symptoms come from the same `offset` design.
- **Example:**

  ```sql
  explain (analyze, buffers)
  select id, created_at, action from audit_events
  order by created_at desc, id desc
  offset 1000000 limit 50;
  -- Limit  (actual rows=50)
  --   -> Index Scan ... (actual rows=1000050)   <- work grows with the offset
  ```

- **Resolution:** Move to keyset pagination with a composite index that matches the sort, and
  return an opaque cursor (the last `(created_at, id)`) to the client:

  ```sql
  create index concurrently audit_events_seek_idx on audit_events (created_at desc, id desc);

  select id, created_at, action from audit_events
  where (created_at, id) < (:c_at, :c_id)
  order by created_at desc, id desc
  limit 50;
  ```

  For the export, page by keyset (or use a server-side cursor / `COPY`) so a concurrent insert
  can't shift pages. Verify with `EXPLAIN` that latency is flat between page 1 and page 20,000 and
  re-run the export against a live insert load, comparing row counts and checking for duplicates.

- **Prevention:** Cap `page`/`size` in the API, prefer cursor-based pagination for any
  unbounded list, and put a load test of the *deepest* page in the pipeline. For UIs that must
  offer page numbers, limit the reachable depth (e.g. first 100 pages) and steer users to search filters.

</details>

### S19. `ALTER TABLE` hangs, deploys stall and the app slows, with dozens of sessions "idle in transaction" {#alter-table-hangs-deploys-stall}
- **Symptoms:** A routine migration waits indefinitely and the whole `orders` table becomes
  unresponsive behind it. `pg_stat_activity` shows connections in state `idle in transaction`,
  some for hours. Connection-pool usage is high although CPU and I/O are low, and table bloat
  keeps growing (S14).

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A session that began a transaction and then went quiet keeps the locks it took
  (and holds back the vacuum horizon). The migration needs an `ACCESS EXCLUSIVE` lock, queues behind
  such a session, and then every *new* query queues behind the migration — hence the total stall.
  Find the culprits and who is blocking whom:

  ```sql
  select pid, state, now() - xact_start as tx_age, left(query, 80) as last_query
  from pg_stat_activity
  where state = 'idle in transaction'
  order by xact_start;

  select pid, pg_blocking_pids(pid) as blocked_by, wait_event_type, left(query, 60)
  from pg_stat_activity where cardinality(pg_blocking_pids(pid)) > 0;
  ```

  Map the oldest `last_query` to code: typically a `@Transactional` method that makes a slow
  HTTP call or waits on user input after its first query, or a connection leaked without
  `commit`/`rollback` ([Spring Q18](spring-architecture.md#open-view-osiv-default-many) for the OSIV variant).

- **Example:**

  ```java
  @Transactional                                     // transaction opens at the first query
  public void checkout(long orderId) {
      Order o = orders.findById(orderId).orElseThrow();   // takes a row lock later on update
      paymentGateway.charge(o);                            // 20 s HTTP call INSIDE the transaction
      o.markPaid();
  }
  ```

- **Resolution:** Immediate: terminate the oldest offenders (`select pg_terminate_backend(pid)`),
  which lets the queued migration proceed. Root fix: keep transactions short — do the remote call
  *outside* the transaction (or use an outbox), and run migrations with a `lock_timeout` so they
  fail fast instead of blocking everyone (Q37). Verify that the `idle in transaction`
  count returns to ~0 under load.
- **Prevention:** Set `idle_in_transaction_session_timeout` (e.g. 30 s) at role level as a safety
  net, `lock_timeout` in migration tooling, alert on transaction age and on `idle in transaction`
  count, and ban network calls inside `@Transactional` methods in review.

</details>

### S20. Two workers process the same queued job, and sometimes one worker sits blocked waiting for the other {#two-workers-process-same-queued}
- **Symptoms:** A `jobs`-table-based worker fleet occasionally sends the same invoice twice.
  After adding more workers, throughput barely improves and some workers show long waits, while
  others process nothing.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Read the claim query. A plain `select ... where status = 'PENDING' limit 10`
  followed by an `update` is a check-then-act race: two workers read the same rows before either
  updates them. Adding `for update` without `skip locked` fixes the double read but makes the
  second worker *wait* on the first's row locks — serializing the whole fleet (Q27). Confirm in
  `pg_stat_activity` (`wait_event_type = 'Lock'`, waiting on `transactionid`).
- **Example:**

  ```sql
  -- Race: both workers get the same 10 ids.
  select id from jobs where status = 'PENDING' order by id limit 10;
  update jobs set status = 'RUNNING' where id = any(:ids);
  ```

- **Resolution:** Claim atomically with `FOR UPDATE SKIP LOCKED` in a single statement (see
  Q27), commit the claim, process outside the transaction, and add a reaper for expired leases.
  Since delivery is now at-least-once, make the handler idempotent by recording the invoice id with
  a unique constraint before sending. Verify with a test that starts 8 workers against 10,000
  jobs and asserts each job id was processed exactly once and that total time scales down with
  more workers.
- **Prevention:** Put the claim query behind one tested repository method; load-test with
  concurrent workers before adding the second one; at higher volume, move to a real broker
  ([Messaging](messaging-rabbitmq-kafka.md)) instead of growing the table-queue's responsibilities.

</details>

### S21. Inserts start failing with `duplicate key value violates unique constraint "orders_pkey"` after a data import {#inserts-start-failing-duplicate-key}
- **Symptoms:** After restoring a subset of production into staging (or loading a legacy CSV),
  the app fails on the first few new orders: `ERROR: duplicate key value violates unique
  constraint "orders_pkey" — Key (id)=(10001) already exists`. It fails intermittently, then
  succeeds once ids "catch up" — but only after several failed requests.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The sequence behind the `id` default is independent of the table contents.
  Importing rows with *explicit* ids (or a data-only restore) inserts them without advancing the
  sequence, so `nextval()` hands out values that already exist. Compare
  `select last_value from orders_id_seq;` with `select max(id) from orders;` — sequence behind max
  confirms it. (Separately: gaps in ids are normal and *not* a bug — rolled-back inserts still
  consume sequence values.)
- **Example:**

  ```sql
  insert into orders (id, customer_id, total) values (10001, 7, 99.90);   -- explicit id
  insert into orders (customer_id, total) values (8, 15.00);
  -- -> nextval() returns 1, 2, 3 ... until it collides with 10001
  ```

- **Resolution:** Realign the sequence to the data:

  ```sql
  select setval(pg_get_serial_sequence('orders', 'id'), (select coalesce(max(id), 1) from orders));
  ```

  Verify by inserting a new row and checking it receives an id above the imported maximum; run the
  same check for every table that was imported.

- **Prevention:** End every import/migration script that supplies ids with a `setval` step
  (or don't supply ids); include a post-import sanity query that compares each sequence with
  `max(id)`; don't rely on gap-free ids for business meaning (invoice numbers need their own
  gapless numbering scheme).

</details>

### S22. A report that took 2 seconds all week takes 20 minutes on Monday morning, with no code change {#report-took-2-seconds-all}
- **Symptoms:** After the weekend's bulk load (~20 million rows imported into `transactions`),
  the same dashboard query is suddenly 500x slower and saturates CPU. A colleague's `EXPLAIN` a
  few hours later shows a fast plan.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Compare estimated vs actual rows in `EXPLAIN (ANALYZE)` (Q24). Here the planner
  estimated `rows=1` for a filter that really returned 2,000,000 and chose a nested loop that ran
  2 million index lookups, where a hash join would have been right. Cause: the bulk load
  changed the data distribution but autovacuum's auto-analyze hadn't yet refreshed the table
  statistics (it triggers after ~10% of rows change *and* completes on its own schedule). The
  fast plan later appeared because auto-analyze finally ran. Check
  `select last_autoanalyze, n_mod_since_analyze from pg_stat_user_tables where relname = 'transactions';`.
- **Example:**

  ```sql
  explain (analyze)
  select * from transactions t join accounts a on a.id = t.account_id
  where t.batch_id = 991;
  -- Nested Loop (rows=1) (actual rows=2000000) -> planner misestimate by 6 orders of magnitude
  ```

- **Resolution:** Run `ANALYZE transactions;` immediately — the plan flips to a hash join within
  seconds — and re-check the query time. If misestimates persist for correlated columns (e.g.
  `country` and `currency`), create extended statistics
  (`create statistics tx_corr (dependencies) on country, currency from transactions;`) and/or
  raise `default_statistics_target` for skewed columns.
- **Prevention:** Make `ANALYZE` the last step of every bulk-load job; lower
  `autovacuum_analyze_scale_factor` for very large tables; add an alert for large gaps between
  estimated and actual rows in slow-query logs (`auto_explain` with `log_analyze`), and compare
  plans in staging with production-scale data.

</details>

### S23. A revenue report is suddenly 3× too high after someone "just added one more join" {#revenue-report-suddenly-3-too}
- **Symptoms:** Finance notices monthly revenue on the dashboard no longer matches the accounting
  export. Order counts also look inflated, but only for orders that have several line items *and*
  several payments. No error, no failing test.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Join **fan-out**. `orders` was joined to two independent one-to-many tables, so each
  order row is repeated `items × payments` times before `sum(total)` runs. Prove it by comparing
  `count(*)` to `count(distinct o.id)` in the joined result, or by running the same sum without the new join.
- **Example:**

  ```sql
  -- order 1: 3 items x 2 payments = 6 rows, so its total is added 6 times
  select sum(o.total)
  from orders o
  join order_items i on i.order_id = o.id
  join payments p    on p.order_id = o.id;
  ```

- **Resolution:** Aggregate each many-side to one row per order **before** joining (or use
  `exists`/a lateral subquery when you only need a flag), so the join is one-to-one:

  ```sql
  select sum(o.total)
  from orders o
  join (select order_id, sum(amount) as paid from payments group by order_id) p on p.order_id = o.id;
  ```

  Do not "fix" it with `sum(distinct o.total)` — two different orders with the same total collapse into one.

- **Prevention:** Rule of thumb: never join two one-to-many relations in the same level of a query that
  aggregates. Add a reconciliation test (`sum` from the report == `sum` from the base table) on a fixture with
  multi-row children.

</details>

### S24. Two concurrent checkouts both succeed and the stock goes negative (or a balance loses an update) {#two-concurrent-checkouts-both-succeed}
- **Symptoms:** Under load the `inventory` quantity ends at −3, or a wallet balance is lower than the sum of
  its transactions. It never reproduces in a single-user test, and no exception is logged.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A read-modify-write cycle at the default Read Committed level (Q25): both transactions read
  `qty = 1`, both pass the "enough stock" check in the application, both write `qty = 0` (or the second
  overwrites the first). This is a **lost update**; neither isolation level nor `@Transactional` alone
  prevents it, because nothing told the database that the two rows read were related.
- **Example:**

  ```sql
  -- T1 and T2 interleave:
  select qty from inventory where sku = 'A';       -- both see 1
  update inventory set qty = 0 where sku = 'A';    -- both succeed (second overwrites first)
  ```

- **Resolution:** Pick the cheapest correct tool: (a) one **atomic statement** that carries the condition —
  `update inventory set qty = qty - 1 where sku = 'A' and qty >= 1` and check the affected-row count (S9);
  (b) `select … for update` to serialize on that row when you need to read, compute, then write; (c)
  `@Version` optimistic locking if contention is low (Q26); (d) `SERIALIZABLE` with retry for multi-row
  invariants. A `CHECK (qty >= 0)` constraint is the safety net that turns the silent corruption into a
  loud error.

  ```sql
  alter table inventory add constraint qty_non_negative check (qty >= 0);
  ```

- **Prevention:** Treat any "read a number, compute in Java, write it back" as a review flag; add a
  concurrency test that fires 50 parallel decrements at 10 units of stock and asserts exactly 10 succeed.

</details>

### S25. The search box is instant on staging and takes 12 s in production {#search-box-instant-staging-takes}
- **Symptoms:** Searching customers by e-mail or by "contains" text uses 100% of a CPU core and times out.
  There *is* an index on `email`, and `EXPLAIN` still shows a sequential scan.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The index exists but the *predicate shape* cannot use it (Q42): `lower(email) = …` wraps the
  column in a function, `ilike '%term%'` has a leading wildcard, and a `varchar` column compared to a numeric
  parameter forces an implicit cast. Staging has 20k rows, so the seq scan hides it.
- **Example:**

  ```sql
  explain analyze select * from customers where lower(email) = 'ann@example.com';
  --  Seq Scan on customers (actual time=0.03..4120 rows=1)   Rows Removed by Filter: 2,999,999

  explain analyze select * from customers where name ilike '%anderson%';
  --  Seq Scan on customers  Filter: (name ~~* '%anderson%')
  ```

- **Resolution:** Create the index that matches the *expression* and the *operator*, then re-run `EXPLAIN`:

  ```sql
  create index concurrently idx_customers_email_lower on customers (lower(email));
  create extension if not exists pg_trgm;
  create index concurrently idx_customers_name_trgm on customers using gin (name gin_trgm_ops);
  ```

  Normalizing at write time (store `email_normalized`) or using `citext` is an alternative for the first case.

- **Prevention:** Load realistic data volumes in staging and run the 10 slowest-expected search shapes through
  `EXPLAIN` as part of review; alert on sequential scans of large tables (`pg_stat_user_tables.seq_scan` growth).

</details>

### S26. A "delete old rows" job runs for hours, the replicas fall behind, and the table doesn't get smaller {#delete-old-rows-job-runs}
- **Symptoms:** A retention job executes `delete from events where created_at < now() - interval '90 days'`
  (≈ 150 million rows). Replication lag climbs to minutes, disk usage *grows*, and queries on `events` get
  slower after the job — even though the row count dropped.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** One giant `DELETE` is a huge transaction: it writes every row to the WAL (hence replica
  lag and disk growth), holds locks, and only *marks* the rows dead — space is not returned until vacuum runs
  (S14), and the work competes with the application. Check `pg_stat_replication` lag, `n_dead_tup`, and the
  transaction's age in `pg_stat_activity`.
- **Example:**

  ```sql
  delete from events where created_at < now() - interval '90 days';   -- 150M rows, one transaction
  ```

- **Resolution:** Short term: delete in **batches** with a pause, each batch its own small transaction, using
  an index on `created_at`:

  ```sql
  delete from events where id in (
      select id from events where created_at < now() - interval '90 days' order by id limit 10000
  );  -- repeat until 0 rows; sleep between rounds; watch replica lag
  ```

  Real fix: **partition by time** and drop whole partitions (Q43) — a metadata operation with no WAL volume
  and no dead tuples.

- **Prevention:** Design retention before the table is big: time partitions + a scheduled `drop`/`detach`;
  alert on replication lag and on transaction age; never run unbounded deletes in business hours.

</details>

### S27. Hibernate logs `firstResult/maxResults specified with collection fetch; applying in memory` {#hibernate-logs-firstresult-maxresults-specified}
- **Symptoms:** A paginated list endpoint (`PageRequest.of(0, 20)`) over orders with their items started
  to use gigabytes of heap and take seconds, though the page only shows 20 rows. The warning
  `HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory` is in the log.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The N+1 fix from Q29 (`join fetch o.items`) combined with pagination. A join to a collection
  multiplies the rows, so SQL `LIMIT` would cut in the middle of an order; Hibernate therefore **loads every
  matching order with its items and paginates in the JVM**. No `LIMIT` appears in the generated SQL —
  confirm with SQL logging.
- **Example:**

  ```java
  @Query("select o from Order o join fetch o.items where o.status = :s")
  Page<Order> findByStatus(String s, Pageable p);     // applying in memory
  ```

- **Resolution:** Two queries. First page the **ids** (or entities without the collection) in SQL, then fetch
  the collections for just those ids:

  ```java
  List<Long> ids = em.createQuery(
      "select o.id from Order o where o.status = :s order by o.id", Long.class)
      .setParameter("s", status).setMaxResults(20).getResultList();   // real LIMIT 20

  List<Order> page = em.createQuery(
      "select distinct o from Order o join fetch o.items where o.id in :ids order by o.id", Order.class)
      .setParameter("ids", ids).getResultList();
  ```

  Alternatives: `@BatchSize` on the collection (one extra query per page, no join), or a DTO projection
  that aggregates in SQL (Q18).

- **Prevention:** Treat the `HHH90003004` warning as a build-breaking log in tests; never combine
  `join fetch` on a collection with `Pageable`.

</details>

### S28. The daily report is off by one around midnight, and again twice a year {#daily-report-off-one-around}
- **Symptoms:** "Orders per day" for yesterday changes when the report is re-run from another server or
  region; a few orders created at 23:30 appear on the next day; counts are wrong on the two days a year the
  clocks change.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A time-zone mismatch. `timestamp without time zone` stores a wall-clock time with no
  meaning attached; `created_at::date` and `date_trunc('day', …)` on a `timestamptz` use the **session**
  time zone, so the same query returns different days for a UTC server and a Paris server. On DST days a
  "day" has 23 or 25 hours, so `created_at + interval '24 hours'` is also wrong. Check
  `show timezone;` in the reporting connection and the column's type.
- **Example:**

  ```sql
  select count(*) from orders where created_at::date = current_date - 1;   -- depends on session TZ
  ```

- **Resolution:** Store instants as **`timestamptz`** (always UTC internally), and compute day boundaries in
  the business time zone *explicitly*, using a half-open range that stays sargable:

  ```sql
  select count(*) from orders
  where created_at >= (date_trunc('day', now() at time zone 'Europe/Paris') - interval '1 day') at time zone 'Europe/Paris'
    and created_at <  (date_trunc('day', now() at time zone 'Europe/Paris'))                    at time zone 'Europe/Paris';
  ```

  Migrate legacy `timestamp` columns with `alter column … type timestamptz using created_at at time zone 'UTC'`
  (after confirming which zone those values were written in; run it as a staged migration, Q44).

- **Prevention:** Convention: `timestamptz` everywhere, JVM/DB in UTC, convert only at the edge; use
  `Instant`/`OffsetDateTime` rather than `LocalDateTime` in entities; test boundaries at 23:59, 00:00 and a DST day.

</details>

### S29. Long reports on the read replica get cancelled with "conflict with recovery" {#long-reports-read-replica-get}
- **Symptoms:** Analytics queries that run for minutes on the streaming replica sometimes die with
  `ERROR: canceling statement due to conflict with recovery — User query might have needed to see row versions that must be removed`.
  The same query succeeds on the primary or when retried at night.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** On the primary, vacuum removed dead row versions that the replica's long-running query
  still needed; replaying that WAL on the replica would break the query's snapshot, so the standby has to
  choose: pause replication (lag grows) or cancel the query. After `max_standby_streaming_delay`
  (default 30 s) it cancels. See `pg_stat_database_conflicts` on the replica.
- **Example:**

  ```sql
  select datname, confl_snapshot, confl_lock from pg_stat_database_conflicts;  -- on the replica
  ```

- **Resolution:** Pick the trade-off deliberately: (a) a dedicated **analytics replica** with a large
  `max_standby_streaming_delay` (accept lag there, keep the HA replica strict); (b) `hot_standby_feedback = on`
  so the primary delays vacuum for those rows (accept bloat on the primary, S14); (c) make the report
  shorter or run it from a pre-aggregated table (Q46 step 6). Add retry logic on SQLSTATE `40001`/`40P01`
  for read-only jobs.
- **Prevention:** Don't mix OLTP failover replicas and long reporting queries on the same node; monitor
  replication lag and conflict counters; budget a maximum report runtime.

</details>

### S30. The same query takes 5 ms in `psql` but 4 s from the application, only after it has been running a while {#same-query-takes-5-ms}
- **Symptoms:** `select * from orders where customer_id = ?` is fast for most customers. After a few
  requests per connection, certain customers (those with millions of orders) become very slow from the Java
  app, while the identical SQL pasted into `psql` stays fast.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** **Prepared statements and the generic plan.** The JDBC driver switches to a server-side
  prepared statement after `prepareThreshold` (default 5) executions; PostgreSQL then plans with the
  literal-free *generic* plan after trying five custom plans, choosing the plan that is best *on average*.
  With skewed data (one customer owns 40% of the table) the generic plan can be a nested-loop-and-index plan
  that is fine for small customers and terrible for the giant one — or the reverse. `psql` pastes a literal,
  so it gets a custom plan. Reproduce with `prepare` and `explain (analyze) execute`:

  ```sql
  prepare q(bigint) as select * from orders where customer_id = $1;
  explain (analyze) execute q(42);        -- small customer
  explain (analyze) execute q(1);         -- the giant customer; compare plan and time
  ```

- **Resolution:** For skewed columns set `plan_cache_mode = force_custom_plan` for that role/session (or
  per-statement via the pgJDBC `prepareThreshold=0`), accepting more planning time; or give the planner better
  statistics (`alter table orders alter column customer_id set statistics 1000; analyze orders;`) and, if the
  skew is by design, route "giant" tenants to a different query path. Verify with `auto_explain` that the plan
  in production now matches the fast one.
- **Prevention:** Include a skewed-key case (the biggest tenant/customer) in load tests; log plans of slow
  queries with `auto_explain.log_min_duration`; when a query is fast by hand and slow from the app, compare
  **custom vs generic plans** before blaming the network or the pool.

</details>

## 🗣️ Reported interview questions

Questions reported from real interviews, grouped by topic. Each has a short model answer: expand it with the detailed questions and scenarios above, and say the answer aloud.

### Performance & troubleshooting

#### R1. A query that used to take 50 ms now takes 10 seconds. How do you troubleshoot it? {#query-used-take-50-ms}
**Answer:** `EXPLAIN (ANALYZE, BUFFERS)` and compare with the old plan: seq scan instead of index, bad row estimates, join order change. Check stale statistics (`ANALYZE`), table/index bloat, data growth, a new parameter value (skewed data, generic plan), a dropped/unused index, lock waits (`pg_stat_activity`), or a changed ORM query (N+1, `LIKE '%x'`, function on indexed column). Fix at the root: index, rewrite, statistics, partition.

#### R2. Your database CPU reaches 100% during peak hours. What steps would you take? {#database-cpu-reaches-100-during}
**Answer:** Find the top consumers with `pg_stat_statements` (total time, calls) and fix the worst few: missing indexes, N+1, unbounded queries. Check connection storms (pool sizes, pgbouncer) and autovacuum. Then reduce load: cache reads, read replicas, batch writes. Scale up/out only after the queries are healthy.

#### R3. How would you identify and resolve a database bottleneck? {#identify-resolve-database-bottleneck}
**Answer:** Classify it: CPU, I/O, memory (cache hit ratio), locks, or connections. Use metrics plus `pg_stat_statements`, `pg_locks`, slow-query log and `EXPLAIN`. Resolve by the class: indexes/rewrites for CPU and I/O, shorter transactions and consistent lock ordering for locks, pooling for connections, then replicas/partitioning/sharding. Verify with before/after latency percentiles.

#### R4. A table has grown to hundreds of millions of rows. How do you improve performance? {#table-has-grown-hundreds-millions}
**Answer:** Index for the actual access patterns (composite, partial, covering), keyset instead of `OFFSET` pagination, **partition** by time/tenant so old partitions are pruned or dropped, archive cold data, keep stats fresh, tune autovacuum, use `BRIN` for append-only time series, pre-aggregate heavy reports, and move analytics to a replica or warehouse.

### Concurrency

#### R5. Two transactions update the same row simultaneously. How do you handle concurrency? {#two-transactions-update-same-row}
**Answer:** The database serialises row writes: the second waits for the first to commit. To avoid *lost updates* on read-modify-write, use an atomic `UPDATE`, `SELECT … FOR UPDATE`, optimistic `@Version`, or `SERIALIZABLE`/`REPEATABLE READ` with retry. Keep transactions short and lock rows in a consistent order to avoid deadlocks.

#### R6. Would you choose optimistic or pessimistic locking for an inventory system? Why? {#optimistic-pessimistic-locking-inventory-system}
**Answer:** Depends on contention. Low conflict (many different items): **optimistic** (`@Version`, retry), no locks held, scales well. A hot item (flash sale): **pessimistic** (`FOR UPDATE`) or an atomic guarded update `UPDATE stock SET qty = qty - :n WHERE id = :id AND qty >= :n`, which is often the best of both. Never check stock in Java then write.

### JPA / Hibernate

#### R7. What is the N+1 problem in Hibernate/JPA and how do you solve it? {#n-1-problem-hibernate-jpa}
**Answer:** One query loads N parents, then one extra query per parent loads a lazy association (1 + N queries). Detect with SQL logging or a query counter in tests. Fix with `JOIN FETCH`, `@EntityGraph`, `@BatchSize`/`default_batch_fetch_size`, or a DTO projection. Beware pagination with collection fetch (use two queries).

#### R8. The appointments table has billions of rows. How do you keep queries and maintenance fast? {#appointments-table-has-billions-rows}
**Answer:** First check the indexes match the access paths (`(practitioner_id, start_at)` for calendars, `(patient_id, start_at)` for a patient's history). Then **partition**: by range on `start_at` (monthly) when most queries are time-bounded, so old partitions can be detached and archived instead of deleted row by row, and autovacuum works on smaller tables. Partition pruning only happens when the query filters on the partition key. Unique and exclusion constraints on a partitioned table must include the partition key, which conflicts with the no-overlap rule on a time range ([Q28](persistence-sql-postgres.md#prevent-two-concurrent-requests-booking)). Options: hash-partition by `practitioner_id` instead (exclusion constraints on partitioned tables need PostgreSQL 17+), or keep a smaller "upcoming appointments" table with the constraint and move past rows to a partitioned history table.

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q23. When can adding an index make performance worse?
2. Q8. What is the logical execution order of a SQL query's clauses — and why can't you filter on a `SELECT` alias in `WHERE`?
3. Q29. What's the N+1 query problem, and name two ways to fix it.
4. Q39. Soft deletes vs. hard deletes — what's the actual trade-off?
5. Q40. Auto-increment `bigint`, random UUID (v4) or time-ordered UUID (v7) for primary keys — how do you choose?
6. Q45. When do you deliberately denormalize, and how do you keep the denormalized copy consistent?
7. Q12. Explain window functions: `row_number` vs `rank` vs `dense_rank`, running totals, `lag`, and the default frame trap.
8. Q16. How do you find consecutive sequences — "users who logged in 3+ days in a row" (gaps and islands)?
9. Q46. Walk me through optimizing a slow, complex query step by step.
10. S22. A report that took 2 seconds all week takes 20 minutes on Monday morning, with no code change

## 📌 Cheat-sheet

### Java persistence layer (JPA / Hibernate)

*Start here:* (1) N+1 is the #1 ORM performance bug; (2) know the entity states; (3) batch bulk writes; (4) never paginate a `join fetch` directly.

- **JPA vs JDBC vs MyBatis** — JPA = full ORM (maps objects to tables); JDBC = low-level, manual; MyBatis = you write the SQL, it does the mapping. *Pick by how much control over the exact SQL you need.*
- **N+1 problem** — 1 query for the parents, then 1 more per parent when lazy-loaded collections are touched in a loop (N+1 total). *Fix with `JOIN FETCH`, `@EntityGraph` or batch fetching, not a blanket `FetchType.EAGER`.*
- **Hibernate entity states** — transient (new, unknown to Hibernate) → persistent (managed, changes auto-tracked) → detached (changes untracked) → removed. *`merge()` on a detached entity can silently overwrite newer data.*
- **Optimistic vs pessimistic locking** — optimistic = no lock held, detect conflicts at write time (e.g. a `@Version` column); pessimistic = lock the row up front. *Optimistic wins at low contention; pessimistic wins at high contention on the same hot rows (avoids retry storms).*
- **Multi-datasource `@Transactional`** — one annotation does not span two databases atomically without JTA/XA (distributed transactions). *Design around a single source of truth per write instead.*
- **Bulk writes** — batch inserts/updates (JDBC batch API, multi-row `VALUES`, or `COPY`); never row-by-row in a loop. *`hibernate.jdbc.batch_size` alone isn't enough without `order_inserts`/`order_updates`.*
- **`join fetch` + `Pageable`** — Hibernate paginates in memory (warning `HHH90003004`). *Page the ids first, then fetch the entities.*
- **Primary keys** — `bigint` = compact and insert-local; UUIDv4 = random page splits (slow inserts); UUIDv7 = distributed *and* roughly time-ordered. *`IDENTITY` generation disables Hibernate insert batching.*

### Writing SQL correctly

*Start here:* (1) SQL runs `FROM` before `SELECT`; (2) `NULL` means "unknown", not a value; (3) prefer `UNION ALL`; (4) use `EXISTS`, never `NOT IN`, for "not in other table".

- **SQL logical order** — `FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT`. *`WHERE` can't see a `SELECT` alias; `HAVING` can filter aggregates because it runs after grouping.*
- **`LEFT JOIN` + `WHERE` on the right table** — turns it into an inner join. *Put the condition in `ON`; use `WHERE right.id IS NULL` for anti-joins (rows with no match).*
- **`UNION ALL` by default** — `UNION` adds a sort/hash de-duplication pass. *It can also collapse legitimately repeated rows.*
- **`NULL` is "unknown"** — `= NULL` never matches (use `IS NULL`); `<>` drops `NULL` rows; `count(col)` ≠ `count(*)` (it skips `NULL`s).

  ```sql
  WHERE x NOT IN (SELECT y FROM t)   -- returns nothing if any y is NULL
  WHERE NOT EXISTS (SELECT 1 FROM t WHERE t.y = x)   -- safe
  ```

- **`NULL` and uniqueness / `NOT IN`** — `NOT IN (subquery with NULL)` returns nothing (use `NOT EXISTS`). *`UNIQUE` allows many `NULL`s (PG15 `NULLS NOT DISTINCT` changes that).*
- **Semi/anti-join** — `EXISTS` / `NOT EXISTS` (never `NOT IN`). *A `JOIN` used as a filter duplicates rows; "for all" = `having count(distinct …) = (size of set)`.*
- **Join fan-out** — two one-to-many joins multiply rows. *Pre-aggregate each side; `sum(distinct)` is not a fix.*
- **Window functions** — compute over related rows without collapsing them. `row_number` (unique) / `rank` (gaps after ties) / `dense_rank` (no gaps). *Default frame with `ORDER BY` is `RANGE … CURRENT ROW` (peers/ties included!): write `rows unbounded preceding`. You can't filter on them in `WHERE`.*
- **Top-N per group / Nth value** — clarify ties first, then `dense_rank`/`row_number` in a subquery. *For big tables with few groups: `LATERAL … limit N` + a composite index.*
- **Latest row per group** — `DISTINCT ON` picks one row per key. *Needs a unique tie-breaker in `ORDER BY`.*
- **One-pass reports** — `count(*) filter (where …)`, `rollup` (subtotals), `nullif` to avoid divide-by-zero in ratios.
- **CTEs (`WITH` queries)** — PG12+ inlines single-use CTEs (`MATERIALIZED` to force a separate step). *A recursive CTE = hierarchy: needs an anchor + `UNION ALL` + a cycle guard.*
- **Gaps and islands** — `value - row_number()` is constant per run of consecutive values (islands); `lead()` finds gaps. *`distinct` first.* *(advanced)*
- **Duplicates** — `row_number() over (partition by key order by …)` and delete `rn > 1`. *Repoint FKs (foreign keys) first, then add a unique index `CONCURRENTLY`.*
- **Upsert** — `ON CONFLICT DO UPDATE … RETURNING` is race-safe. *`DO NOTHING` returns no row; `MERGE` (PG15) doesn't prevent unique races.*
- **Time zones** — use `timestamptz` + explicit business-zone day boundaries as half-open ranges (`>= start AND < next_start`). *The session time zone changes `::date`.*

### Indexes and query performance

*Start here:* (1) read the plan with `EXPLAIN ANALYZE`; (2) index the columns you filter and join on; (3) column order in a composite index matters; (4) stale statistics = bad plans.

- **`EXPLAIN ANALYZE`** — shows the real plan with timings. *Watch for `Seq Scan` (full table read) on a big table and estimated-vs-actual row mismatches (stale stats → run `ANALYZE`). Plain `EXPLAIN` is only an estimate; it never runs the query.*
- **Postgres index types** — B-tree (default, equality/range) · GIN (JSONB containment, full-text, arrays) · GiST (geometric/range overlap) · partial index (small, filtered subset).
- **Composite index column order** — equality/high-selectivity columns first. *Otherwise the index silently doesn't serve the query.*
- **Index toolkit** — composite (equality first, range last), partial (hot subset), `INCLUDE` covering (index-only scan needs a fresh visibility map), expression (`lower(email)`), trigram GIN for `LIKE '%x%'`. *Build with `CONCURRENTLY`; drop unused ones.* *(advanced)*
- **JSONB** — fine for sparse/variable data. *Normalize anything frequently filtered, joined or constraint-checked.*
- **Pagination** — `OFFSET` costs O(offset) and shifts under concurrent writes. *Use keyset pagination (`where (created_at, id) < (...)`) with a matching composite index and a unique tie-breaker.*
- **Plan flip after a bulk load** — stale statistics. *`ANALYZE` at the end of batch jobs; use extended statistics for correlated columns; compare estimated vs actual rows.*
- **Generic vs custom plans** — fast in `psql` but slow in the app? *Compare custom vs generic plan (`plan_cache_mode`).* *(advanced)*
- **Optimize a query, in order** — real `EXPLAIN (ANALYZE, BUFFERS)` → dominant node (loops × cost) → estimates vs actuals → sargable predicate (one an index can use) → aggregate/`LIMIT` before joining → remove per-row subqueries → index → `work_mem`/`ANALYZE` → pre-compute last. *One change at a time.*

### Transactions and concurrency

*Start here:* (1) Read Committed is the default and allows lost updates; (2) make read-modify-write atomic; (3) never hold a transaction open while calling remote services.

- **Isolation levels** — Read Committed (default, prevents dirty reads only) < Repeatable Read (also prevents non-repeatable/phantom reads in Postgres) < Serializable (fully serial-equivalent, more retries).
- **Lost update** — two sessions read-modify-write the same row at Read Committed and one overwrite wins. *Use atomic `update … where qty >= 1`, `FOR UPDATE`, `@Version`, plus a `CHECK` constraint.*
- **`FOR UPDATE SKIP LOCKED`** — turns a Postgres table into a work queue: claim short, process outside the transaction, add a lease reaper (frees abandoned claims). *At-least-once delivery, so handlers must be idempotent.* *(advanced)*
- **`idle in transaction` sessions** — hold locks and the vacuum horizon, so they stall migrations. *Set `idle_in_transaction_session_timeout` and `lock_timeout`; keep remote calls out of transactions.*
- **HikariCP sizing** — smaller than intuition suggests. *Total connections across the whole fleet must fit the DB's `max_connections`, not just one instance's pool.*
- **Read replicas** — naive routing breaks read-after-write (you write, then read stale data). *Pin write-sensitive reads to the primary.*
- **Replica conflicts** — `max_standby_streaming_delay` vs `hot_standby_feedback` trade off cancelled queries against primary bloat. *(advanced)*

### Schema changes and operations

*Start here:* (1) never one blocking step on a huge live table; (2) additive first, backfill, then clean up; (3) watch dead tuples and long transactions.

- **Zero-downtime schema changes** — additive/nullable first → backfill → enforce/cleanup. *Each step must work with both old and new app code.*
- **Big migrations** — `NOT VALID` + `VALIDATE CONSTRAINT`, `CREATE INDEX CONCURRENTLY`, additive-then-backfill-then-cleanup. *Never one blocking step on a huge live table.*
- **`ON DELETE CASCADE`** — a deliberate per-relationship decision, not a default. *Review the full cascade chain.*
- **Soft deletes** (a `deleted_at` flag instead of removing the row) — risks forgotten `deleted_at is null` filters and unique constraints blocking on "deleted" rows. *Scope uniqueness to live rows with a partial index.*
- **Table/index bloat** — `n_dead_tup` (dead rows) growing despite stable `n_live_tup` means autovacuum isn't keeping up. *Tune per-table settings or find the blocking long-running transaction.*
- **Partitioning** — pays for retention (drop a partition) and pruning (skipping partitions). *PK must include the partition key, queries must filter on it, create partitions ahead; don't partition before it hurts.*
- **Big deletes** — batch them or drop partitions. *One giant `DELETE` = WAL (write-ahead log) flood, replica lag, bloat.*
- **Sequences** — explicit ids don't advance the sequence: `setval` after imports. *Id gaps are normal.*
- **Index that hurts** — every index slows writes and takes space; it can also mislead the planner or be ignored (low selectivity, function on the column, type mismatch). *Check `EXPLAIN (ANALYZE)` and `pg_stat_user_indexes`; drop unused ones.*
