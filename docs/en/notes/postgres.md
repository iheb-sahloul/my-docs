# PostgreSQL

## psql

### Connect
```bash
psql -h localhost -p 5432 -U app -d shop
psql "postgresql://app:secret@localhost:5432/shop?sslmode=require"
PGPASSWORD=secret psql -h db -U app shop -c 'select now()'
psql -f schema.sql shop                        # run a file
psql -At -c 'select count(*) from orders' shop # unaligned, tuples only: script-friendly
```

### Meta-commands

| Command | Does |
|---|---|
| `\l` | List databases |
| `\c shop` | Connect to a database |
| `\dt` / `\dt+` | List tables (with sizes) |
| `\d orders` | Describe table: columns, indexes, FKs |
| `\d+ orders` | ...plus storage and comments |
| `\di+` | List indexes with sizes |
| `\dn` | Schemas |
| `\du` | Roles |
| `\df` | Functions |
| `\dx` | Installed extensions |
| `\x auto` | Expanded output for wide rows |
| `\timing` | Show query time |
| `\e` | Edit the last query in `$EDITOR` |
| `\i file.sql` | Run a file |
| `\copy` | Client-side COPY |
| `\watch 2` | Re-run last query every 2 s |
| `\q` | Quit |

### ~/.psqlrc
```text
\set QUIET 1
\pset null '(null)'
\x auto
\timing on
\set HISTSIZE 5000
\set QUIET 0
```

### Import and export CSV
```sql
\copy orders TO 'orders.csv' WITH (FORMAT csv, HEADER)
\copy orders FROM 'orders.csv' WITH (FORMAT csv, HEADER)
\copy (select id, total from orders where status = 'PAID') TO 'paid.csv' CSV HEADER
```

---

## Databases, schemas, roles

### Create
```sql
CREATE DATABASE shop OWNER app ENCODING 'UTF8';
CREATE SCHEMA billing AUTHORIZATION app;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Roles and grants
```sql
CREATE ROLE app LOGIN PASSWORD 'secret';
CREATE ROLE readonly NOLOGIN;
GRANT CONNECT ON DATABASE shop TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;  -- future tables too
GRANT readonly TO alice;                       -- alice inherits the role
ALTER ROLE app SET statement_timeout = '30s';
REVOKE ALL ON DATABASE shop FROM PUBLIC;
```
```sql
\du
\dp orders                                     -- privileges on a table
```

### Session and settings
```sql
SHOW search_path;
SET search_path TO billing, public;
SHOW work_mem;
SET LOCAL work_mem = '256MB';                  -- this transaction only
ALTER SYSTEM SET max_connections = 300;        -- writes postgresql.auto.conf
SELECT pg_reload_conf();                       -- reload (restart needed for some settings)
SELECT name, setting, unit, context FROM pg_settings WHERE name LIKE '%mem%';
```

### Sizes
```sql
SELECT pg_size_pretty(pg_database_size('shop'));
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) AS total
FROM pg_class WHERE relkind = 'r' ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;
```

---

## Indexes

### Create
```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX CONCURRENTLY idx_orders_created ON orders (created_at DESC);   -- no write lock, slower
CREATE UNIQUE INDEX uq_users_email ON users (lower(email));                 -- expression index
CREATE INDEX idx_orders_open ON orders (customer_id) WHERE status = 'OPEN'; -- partial index
CREATE INDEX idx_orders_cover ON orders (customer_id) INCLUDE (total);      -- covering (index-only scans)
CREATE INDEX idx_docs_tags ON docs USING gin (tags);                        -- arrays, jsonb, full text
DROP INDEX CONCURRENTLY idx_orders_created;
REINDEX INDEX CONCURRENTLY idx_orders_customer;
```

`CREATE INDEX CONCURRENTLY` cannot run inside a transaction. If it fails it leaves an `INVALID` index: drop it and retry.

### Index types

| Type | Good for |
|---|---|
| `btree` (default) | `=`, `<`, `>`, `BETWEEN`, `ORDER BY`, `LIKE 'abc%'` |
| `hash` | Equality only |
| `gin` | `jsonb @>`, arrays, full-text search, `pg_trgm` |
| `gist` | Geometry, ranges, nearest-neighbour |
| `brin` | Huge append-only tables ordered by insertion (timestamps) |

Composite index order matters: `(a, b)` helps `WHERE a = ?` and `WHERE a = ? AND b = ?`, not `WHERE b = ?` alone.

### Find unused and duplicate indexes
```sql
SELECT schemaname, relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelid NOT IN (SELECT conindid FROM pg_constraint)
ORDER BY pg_relation_size(indexrelid) DESC;

-- foreign keys without a supporting index
SELECT c.conrelid::regclass AS tbl, c.conname
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]);
```

---

## EXPLAIN

### Basics
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
```
```text
Index Scan using idx_orders_customer on orders  (cost=0.43..8.45 rows=3 width=64) (actual time=0.021..0.023 rows=3 loops=1)
  Index Cond: (customer_id = 42)
  Buffers: shared hit=4
Execution Time: 0.045 ms
```

See the SQL note for a full explanation of each field. Checklist:

| Symptom | Likely cause / fix |
|---|---|
| `Seq Scan` + huge `Rows Removed by Filter` | Missing index on the filter column |
| `rows=1` estimated, `rows=50000` actual | Stale stats: `ANALYZE table;` or raise `default_statistics_target` |
| `Sort Method: external merge Disk` | `work_mem` too small for this sort |
| `Nested Loop` with large `loops` | Missing join index, or bad row estimate |
| `Buffers: read=` large | Cold cache, or reading far more than needed |
| Function on column in `WHERE` (`lower(x)`, `date(ts)`) | Index not usable: use an expression index or rewrite as a range |

### Planner stats
```sql
ANALYZE orders;
SELECT attname, n_distinct, correlation FROM pg_stats WHERE tablename = 'orders';
ALTER TABLE orders ALTER COLUMN customer_id SET STATISTICS 500;
```

### Test an index without building it (experiment only)
```sql
SET enable_seqscan = off;                      -- see if the planner CAN use an index
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;
RESET enable_seqscan;
```

---

## Activity, locks, slow queries

### What is running now
```sql
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - query_start AS runtime, left(query, 80) AS query
FROM pg_stat_activity
WHERE state <> 'idle' AND pid <> pg_backend_pid()
ORDER BY runtime DESC;
```
```text
  pid  | usename | state  | wait_event_type | wait_event |    runtime    | query
-------+---------+--------+-----------------+------------+---------------+------------------
 18422 | app     | active | Lock            | transactionid | 00:04:12   | UPDATE orders SET ...
```

### Cancel or kill
```sql
SELECT pg_cancel_backend(18422);               -- cancel the query, keep the connection
SELECT pg_terminate_backend(18422);            -- close the connection
-- idle in transaction for too long:
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle in transaction' AND now() - state_change > interval '10 min';
```

### Who blocks whom
```sql
SELECT blocked.pid AS blocked_pid, left(blocked.query, 60) AS blocked_query,
       blocking.pid AS blocking_pid, left(blocking.query, 60) AS blocking_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b(pid) ON true
JOIN pg_stat_activity blocking ON blocking.pid = b.pid;
```

The blocker is usually a session `idle in transaction` holding row locks. Fix the app (short transactions), and set:
```sql
ALTER ROLE app SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app SET lock_timeout = '5s';
```

### Table locks

| Statement | Lock | Blocks |
|---|---|---|
| `SELECT` | `ACCESS SHARE` | only `ACCESS EXCLUSIVE` |
| `UPDATE/DELETE/INSERT` | `ROW EXCLUSIVE` | schema changes, not other DML |
| `SELECT ... FOR UPDATE` | row locks | other writers of those rows |
| `CREATE INDEX` | `SHARE` | writes |
| `CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | nothing important |
| `ALTER TABLE`, `DROP`, `VACUUM FULL` | `ACCESS EXCLUSIVE` | everything, including reads |

```sql
SELECT locktype, relation::regclass, mode, granted, pid FROM pg_locks WHERE NOT granted;
```

Before a risky `ALTER TABLE`, set `SET lock_timeout = '3s';` so it fails fast instead of queueing behind a long transaction and blocking all traffic.

### Skip locked rows (job queues)
```sql
SELECT id FROM jobs WHERE status = 'NEW'
ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED;
```

### pg_stat_statements (top queries)
```sql
-- needs shared_preload_libraries = 'pg_stat_statements' + CREATE EXTENSION
SELECT calls, round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms, rows, left(query, 70) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 10;
SELECT pg_stat_statements_reset();
```

### Other useful stats views

| View | Answers |
|---|---|
| `pg_stat_activity` | Who is connected, running what, waiting on what |
| `pg_stat_database` | Commits, rollbacks, deadlocks, cache hits per DB |
| `pg_stat_user_tables` | Seq vs index scans, live/dead tuples, last vacuum/analyze |
| `pg_stat_user_indexes` | Index usage (`idx_scan`) |
| `pg_statio_user_tables` | Heap/index block hits vs reads |
| `pg_stat_replication` | Replicas and replay lag |
| `pg_stat_bgwriter` / `pg_stat_checkpointer` | Checkpoint pressure |
| `pg_locks` | Held and awaited locks |

### Cache hit ratio (aim for > 99% on OLTP)
```sql
SELECT round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS hit_pct
FROM pg_stat_database WHERE datname = current_database();
```

### Connections
```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
SHOW max_connections;
```

---

## Vacuum and bloat

### Why
`UPDATE`/`DELETE` leave dead row versions (MVCC). `VACUUM` reclaims them for reuse and updates the visibility map. Autovacuum normally does it.

```sql
VACUUM (VERBOSE, ANALYZE) orders;              -- no exclusive lock
VACUUM FULL orders;                            -- rewrites table, ACCESS EXCLUSIVE lock: avoid on live systems
ANALYZE orders;
```

### Check dead tuples and last vacuum
```sql
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

### Tune autovacuum for one hot table
```sql
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.02, autovacuum_analyze_scale_factor = 0.01);
```
Default scale factor is 0.2 (20% of the table must be dead), too lazy for large tables.

### Vacuum cannot clean up?
A long-running or `idle in transaction` session (or an unused replication slot / prepared transaction) holds back the cleanup horizon.
```sql
SELECT pid, state, now() - xact_start AS age, left(query, 60) FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 5;
SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;
```

### Rebuild a bloated table online
```bash
# extension pg_repack: no long exclusive lock
pg_repack -h localhost -U app -d shop --table orders
```

---

## Backup and restore

### Logical dump (pg_dump)
```bash
pg_dump -h localhost -U app -Fc shop > shop.dump          # custom format: compressed, selective restore
pg_dump -Fd -j 4 -f shop_dir shop                         # directory format, parallel dump
pg_dump -Fp shop > shop.sql                               # plain SQL
pg_dump -s shop > schema.sql                              # schema only
pg_dump -a -t orders shop > orders_data.sql               # data of one table
pg_dumpall --globals-only > globals.sql                   # roles and tablespaces
```

| Format | Flag | Restore with |
|---|---|---|
| Plain SQL | `-Fp` | `psql` |
| Custom | `-Fc` | `pg_restore` |
| Directory | `-Fd` | `pg_restore` (parallel with `-j`) |
| Tar | `-Ft` | `pg_restore` |

### Restore
```bash
createdb -U app shop_restored
pg_restore -h localhost -U app -d shop_restored --no-owner -j 4 shop.dump
pg_restore -d shop_restored -t orders shop.dump           # one table
pg_restore -l shop.dump                                   # list contents
pg_restore -d shop --clean --if-exists shop.dump          # drop objects first
psql -d shop_restored -f shop.sql                         # plain format
psql -v ON_ERROR_STOP=1 -1 -f shop.sql shop               # single transaction, stop on first error
```

### Copy a database between servers
```bash
pg_dump -Fc -h old-host -U app shop | pg_restore -h new-host -U app -d shop --no-owner
```

### Physical backup and PITR
```bash
pg_basebackup -h primary -U replicator -D /backups/base -Ft -z -P -X stream
```
```text
# postgresql.conf for point-in-time recovery
archive_mode = on
archive_command = 'test ! -f /wal_archive/%f && cp %p /wal_archive/%f'
```
```text
# restore: unpack base backup, then in postgresql.conf + empty recovery.signal file
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '2026-09-29 10:15:00'
```
For real setups use pgBackRest or Barman instead of hand-rolled scripts, and test restores regularly: an untested backup is not a backup.

---

## Handy SQL

### JSONB
```sql
SELECT data->>'name' AS name, data->'address'->>'city' AS city FROM users WHERE data @> '{"active": true}';
CREATE INDEX idx_users_data ON users USING gin (data jsonb_path_ops);
UPDATE users SET data = jsonb_set(data, '{address,city}', '"Paris"') WHERE id = 1;
```

### Upsert and returning
```sql
INSERT INTO stock (sku, qty) VALUES ('A1', 5)
ON CONFLICT (sku) DO UPDATE SET qty = stock.qty + EXCLUDED.qty
RETURNING *;
```

### Safe schema changes on big tables
```sql
SET lock_timeout = '3s';
ALTER TABLE orders ADD COLUMN note text;                          -- fast, no rewrite
ALTER TABLE orders ADD COLUMN flag boolean NOT NULL DEFAULT false; -- fast since PG 11
ALTER TABLE orders ADD CONSTRAINT fk_c FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT fk_c;                      -- validates without blocking writes
```

### Kill duplicates
```sql
DELETE FROM users a USING users b
WHERE a.ctid < b.ctid AND a.email = b.email;
```

### Sequences
```sql
SELECT setval(pg_get_serial_sequence('orders', 'id'), (SELECT max(id) FROM orders));   -- after a data import
```
