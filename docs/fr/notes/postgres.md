# PostgreSQL

## psql

### Connexion
```bash
psql -h localhost -p 5432 -U app -d shop
psql "postgresql://app:secret@localhost:5432/shop?sslmode=require"
PGPASSWORD=secret psql -h db -U app shop -c 'select now()'
psql -f schema.sql shop                        # exécuter un fichier
psql -At -c 'select count(*) from orders' shop # non aligné, tuples uniquement : adapté aux scripts
```

### Méta-commandes

| Commande | Effet |
|---|---|
| `\l` | Liste les bases de données |
| `\c shop` | Se connecte à une base |
| `\dt` / `\dt+` | Liste les tables (avec les tailles) |
| `\d orders` | Décrit une table : colonnes, index, clés étrangères |
| `\d+ orders` | ...plus stockage et commentaires |
| `\di+` | Liste les index avec leurs tailles |
| `\dn` | Schémas |
| `\du` | Rôles |
| `\df` | Fonctions |
| `\dx` | Extensions installées |
| `\x auto` | Affichage étendu pour les lignes larges |
| `\timing` | Affiche la durée des requêtes |
| `\e` | Édite la dernière requête dans `$EDITOR` |
| `\i file.sql` | Exécute un fichier |
| `\copy` | COPY côté client |
| `\watch 2` | Relance la dernière requête toutes les 2 s |
| `\q` | Quitter |

### ~/.psqlrc
```text
\set QUIET 1
\pset null '(null)'
\x auto
\timing on
\set HISTSIZE 5000
\set QUIET 0
```

### Importer et exporter du CSV
```sql
\copy orders TO 'orders.csv' WITH (FORMAT csv, HEADER)
\copy orders FROM 'orders.csv' WITH (FORMAT csv, HEADER)
\copy (select id, total from orders where status = 'PAID') TO 'paid.csv' CSV HEADER
```

---

## Bases, schémas, rôles

### Créer
```sql
CREATE DATABASE shop OWNER app ENCODING 'UTF8';
CREATE SCHEMA billing AUTHORIZATION app;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Rôles et droits
```sql
CREATE ROLE app LOGIN PASSWORD 'secret';
CREATE ROLE readonly NOLOGIN;
GRANT CONNECT ON DATABASE shop TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;  -- aussi pour les tables futures
GRANT readonly TO alice;                       -- alice hérite du rôle
ALTER ROLE app SET statement_timeout = '30s';
REVOKE ALL ON DATABASE shop FROM PUBLIC;
```
```sql
\du
\dp orders                                     -- droits sur une table
```

### Session et paramètres
```sql
SHOW search_path;
SET search_path TO billing, public;
SHOW work_mem;
SET LOCAL work_mem = '256MB';                  -- cette transaction uniquement
ALTER SYSTEM SET max_connections = 300;        -- écrit postgresql.auto.conf
SELECT pg_reload_conf();                       -- recharger (redémarrage nécessaire pour certains paramètres)
SELECT name, setting, unit, context FROM pg_settings WHERE name LIKE '%mem%';
```

### Tailles
```sql
SELECT pg_size_pretty(pg_database_size('shop'));
SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) AS total
FROM pg_class WHERE relkind = 'r' ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;
```

---

## Index

### Créer
```sql
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX CONCURRENTLY idx_orders_created ON orders (created_at DESC);   -- sans verrou en écriture, plus lent
CREATE UNIQUE INDEX uq_users_email ON users (lower(email));                 -- index d'expression
CREATE INDEX idx_orders_open ON orders (customer_id) WHERE status = 'OPEN'; -- index partiel
CREATE INDEX idx_orders_cover ON orders (customer_id) INCLUDE (total);      -- couvrant (index-only scans)
CREATE INDEX idx_docs_tags ON docs USING gin (tags);                        -- tableaux, jsonb, recherche plein texte
DROP INDEX CONCURRENTLY idx_orders_created;
REINDEX INDEX CONCURRENTLY idx_orders_customer;
```

`CREATE INDEX CONCURRENTLY` ne peut pas s'exécuter dans une transaction. En cas d'échec, il laisse un index `INVALID` : supprimez-le et réessayez.

### Types d'index

| Type | Adapté pour |
|---|---|
| `btree` (par défaut) | `=`, `<`, `>`, `BETWEEN`, `ORDER BY`, `LIKE 'abc%'` |
| `hash` | Égalité uniquement |
| `gin` | `jsonb @>`, tableaux, recherche plein texte, `pg_trgm` |
| `gist` | Géométrie, intervalles, plus proche voisin |
| `brin` | Très grandes tables en ajout seul, ordonnées par insertion (timestamps) |

L'ordre d'un index composite compte : `(a, b)` aide `WHERE a = ?` et `WHERE a = ? AND b = ?`, mais pas `WHERE b = ?` seul.

### Trouver les index inutilisés et en double
```sql
SELECT schemaname, relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelid NOT IN (SELECT conindid FROM pg_constraint)
ORDER BY pg_relation_size(indexrelid) DESC;

-- clés étrangères sans index de support
SELECT c.conrelid::regclass AS tbl, c.conname
FROM pg_constraint c
WHERE c.contype = 'f'
  AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]);
```

---

## EXPLAIN

### Bases
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
```
```text
Index Scan using idx_orders_customer on orders  (cost=0.43..8.45 rows=3 width=64) (actual time=0.021..0.023 rows=3 loops=1)
  Index Cond: (customer_id = 42)
  Buffers: shared hit=4
Execution Time: 0.045 ms
```

Voir la note SQL pour une explication complète de chaque champ. Liste de contrôle :

| Symptôme | Cause probable / correctif |
|---|---|
| `Seq Scan` + énorme `Rows Removed by Filter` | Index manquant sur la colonne filtrée |
| `rows=1` estimé, `rows=50000` réel | Statistiques périmées : `ANALYZE table;` ou augmenter `default_statistics_target` |
| `Sort Method: external merge Disk` | `work_mem` trop petit pour ce tri |
| `Nested Loop` avec un grand `loops` | Index de jointure manquant, ou mauvaise estimation du nombre de lignes |
| `Buffers: read=` élevé | Cache froid, ou lecture bien supérieure au nécessaire |
| Fonction sur une colonne dans le `WHERE` (`lower(x)`, `date(ts)`) | Index inutilisable : utiliser un index d'expression ou réécrire en intervalle |

### Statistiques du planificateur
```sql
ANALYZE orders;
SELECT attname, n_distinct, correlation FROM pg_stats WHERE tablename = 'orders';
ALTER TABLE orders ALTER COLUMN customer_id SET STATISTICS 500;
```

### Tester un index sans le construire (expérimentation uniquement)
```sql
SET enable_seqscan = off;                      -- voir si le planificateur PEUT utiliser un index
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;
RESET enable_seqscan;
```

---

## Activité, verrous, requêtes lentes

### Ce qui s'exécute en ce moment
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

### Annuler ou tuer
```sql
SELECT pg_cancel_backend(18422);               -- annule la requête, garde la connexion
SELECT pg_terminate_backend(18422);            -- ferme la connexion
-- idle in transaction depuis trop longtemps :
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle in transaction' AND now() - state_change > interval '10 min';
```

### Qui bloque qui
```sql
SELECT blocked.pid AS blocked_pid, left(blocked.query, 60) AS blocked_query,
       blocking.pid AS blocking_pid, left(blocking.query, 60) AS blocking_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b(pid) ON true
JOIN pg_stat_activity blocking ON blocking.pid = b.pid;
```

Le bloqueur est généralement une session `idle in transaction` qui détient des verrous de lignes. Corrigez l'application (transactions courtes) et configurez :
```sql
ALTER ROLE app SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE app SET lock_timeout = '5s';
```

### Verrous de table

| Instruction | Verrou | Bloque |
|---|---|---|
| `SELECT` | `ACCESS SHARE` | uniquement `ACCESS EXCLUSIVE` |
| `UPDATE/DELETE/INSERT` | `ROW EXCLUSIVE` | les changements de schéma, pas les autres DML |
| `SELECT ... FOR UPDATE` | verrous de lignes | les autres écrivains de ces lignes |
| `CREATE INDEX` | `SHARE` | les écritures |
| `CREATE INDEX CONCURRENTLY` | `SHARE UPDATE EXCLUSIVE` | rien d'important |
| `ALTER TABLE`, `DROP`, `VACUUM FULL` | `ACCESS EXCLUSIVE` | tout, y compris les lectures |

```sql
SELECT locktype, relation::regclass, mode, granted, pid FROM pg_locks WHERE NOT granted;
```

Avant un `ALTER TABLE` risqué, exécutez `SET lock_timeout = '3s';` pour qu'il échoue vite au lieu de faire la queue derrière une longue transaction et de bloquer tout le trafic.

### Ignorer les lignes verrouillées (files de jobs)
```sql
SELECT id FROM jobs WHERE status = 'NEW'
ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED;
```

### pg_stat_statements (requêtes les plus coûteuses)
```sql
-- nécessite shared_preload_libraries = 'pg_stat_statements' + CREATE EXTENSION
SELECT calls, round(total_exec_time::numeric, 1) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms, rows, left(query, 70) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 10;
SELECT pg_stat_statements_reset();
```

### Autres vues de statistiques utiles

| Vue | Répond à |
|---|---|
| `pg_stat_activity` | Qui est connecté, exécute quoi, attend quoi |
| `pg_stat_database` | Commits, rollbacks, deadlocks, hits de cache par base |
| `pg_stat_user_tables` | Scans séquentiels vs par index, tuples vivants/morts, dernier vacuum/analyze |
| `pg_stat_user_indexes` | Utilisation des index (`idx_scan`) |
| `pg_statio_user_tables` | Hits vs lectures de blocs heap/index |
| `pg_stat_replication` | Réplicas et retard de rejeu |
| `pg_stat_bgwriter` / `pg_stat_checkpointer` | Pression des checkpoints |
| `pg_locks` | Verrous détenus et attendus |

### Taux de succès du cache (viser > 99 % en OLTP)
```sql
SELECT round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS hit_pct
FROM pg_stat_database WHERE datname = current_database();
```

### Connexions
```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
SHOW max_connections;
```

---

## Vacuum et bloat

### Pourquoi
`UPDATE`/`DELETE` laissent des versions de lignes mortes (MVCC). `VACUUM` les récupère pour réutilisation et met à jour la visibility map. L'autovacuum s'en charge normalement.

```sql
VACUUM (VERBOSE, ANALYZE) orders;              -- pas de verrou exclusif
VACUUM FULL orders;                            -- réécrit la table, verrou ACCESS EXCLUSIVE : à éviter en production
ANALYZE orders;
```

### Vérifier les tuples morts et le dernier vacuum
```sql
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

### Régler l'autovacuum pour une table très sollicitée
```sql
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.02, autovacuum_analyze_scale_factor = 0.01);
```
Le scale factor par défaut est 0,2 (20 % de la table doit être morte), trop paresseux pour les grosses tables.

### Le vacuum ne peut pas nettoyer ?
Une session longue ou `idle in transaction` (ou un slot de réplication inutilisé / une transaction préparée) retient l'horizon de nettoyage.
```sql
SELECT pid, state, now() - xact_start AS age, left(query, 60) FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 5;
SELECT slot_name, active, pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS lag
FROM pg_replication_slots;
```

### Reconstruire une table gonflée en ligne
```bash
# extension pg_repack : pas de long verrou exclusif
pg_repack -h localhost -U app -d shop --table orders
```

---

## Sauvegarde et restauration

### Dump logique (pg_dump)
```bash
pg_dump -h localhost -U app -Fc shop > shop.dump          # format custom : compressé, restauration sélective
pg_dump -Fd -j 4 -f shop_dir shop                         # format répertoire, dump parallèle
pg_dump -Fp shop > shop.sql                               # SQL brut
pg_dump -s shop > schema.sql                              # schéma uniquement
pg_dump -a -t orders shop > orders_data.sql               # données d'une table
pg_dumpall --globals-only > globals.sql                   # rôles et tablespaces
```

| Format | Option | Restaurer avec |
|---|---|---|
| SQL brut | `-Fp` | `psql` |
| Custom | `-Fc` | `pg_restore` |
| Répertoire | `-Fd` | `pg_restore` (parallèle avec `-j`) |
| Tar | `-Ft` | `pg_restore` |

### Restauration
```bash
createdb -U app shop_restored
pg_restore -h localhost -U app -d shop_restored --no-owner -j 4 shop.dump
pg_restore -d shop_restored -t orders shop.dump           # une table
pg_restore -l shop.dump                                   # lister le contenu
pg_restore -d shop --clean --if-exists shop.dump          # supprimer d'abord les objets
psql -d shop_restored -f shop.sql                         # format brut
psql -v ON_ERROR_STOP=1 -1 -f shop.sql shop               # transaction unique, arrêt à la première erreur
```

### Copier une base entre serveurs
```bash
pg_dump -Fc -h old-host -U app shop | pg_restore -h new-host -U app -d shop --no-owner
```

### Sauvegarde physique et PITR
```bash
pg_basebackup -h primary -U replicator -D /backups/base -Ft -z -P -X stream
```
```text
# postgresql.conf pour la restauration à un instant donné (PITR)
archive_mode = on
archive_command = 'test ! -f /wal_archive/%f && cp %p /wal_archive/%f'
```
```text
# restauration : décompresser la sauvegarde de base, puis dans postgresql.conf + un fichier recovery.signal vide
restore_command = 'cp /wal_archive/%f %p'
recovery_target_time = '2026-09-29 10:15:00'
```
Pour un vrai déploiement, utilisez pgBackRest ou Barman plutôt que des scripts maison, et testez régulièrement les restaurations : une sauvegarde non testée n'est pas une sauvegarde.

---

## SQL pratique

### JSONB
```sql
SELECT data->>'name' AS name, data->'address'->>'city' AS city FROM users WHERE data @> '{"active": true}';
CREATE INDEX idx_users_data ON users USING gin (data jsonb_path_ops);
UPDATE users SET data = jsonb_set(data, '{address,city}', '"Paris"') WHERE id = 1;
```

### Upsert et returning
```sql
INSERT INTO stock (sku, qty) VALUES ('A1', 5)
ON CONFLICT (sku) DO UPDATE SET qty = stock.qty + EXCLUDED.qty
RETURNING *;
```

### Changements de schéma sûrs sur de grosses tables
```sql
SET lock_timeout = '3s';
ALTER TABLE orders ADD COLUMN note text;                          -- rapide, sans réécriture
ALTER TABLE orders ADD COLUMN flag boolean NOT NULL DEFAULT false; -- rapide depuis PG 11
ALTER TABLE orders ADD CONSTRAINT fk_c FOREIGN KEY (customer_id) REFERENCES customers (id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT fk_c;                      -- valide sans bloquer les écritures
```

### Éliminer les doublons
```sql
DELETE FROM users a USING users b
WHERE a.ctid < b.ctid AND a.email = b.email;
```

### Séquences
```sql
SELECT setval(pg_get_serial_sequence('orders', 'id'), (SELECT max(id) FROM orders));   -- après un import de données
```
