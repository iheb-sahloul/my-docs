# SQL


### EXPLAIN vs EXPLAIN ANALYZE

| Commande | Exécute la requête ? | Ce que vous obtenez |
|---|---|---|
| `EXPLAIN` | Non | Le plan et les coûts **estimés** par le planificateur |
| `EXPLAIN ANALYZE` | **Oui** | Estimations **+ réels** : lignes, temps, boucles |
| `EXPLAIN (ANALYZE, BUFFERS)` | **Oui** | Aussi les hits/reads des shared buffers (mémoire vs I/O disque) |

```sql
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42;
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS, FORMAT JSON) SELECT ...;  -- JSON : à coller dans explain.dalibo.com
```

`EXPLAIN ANALYZE` exécute réellement l'instruction. Pour `INSERT/UPDATE/DELETE`, faites un rollback :
```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) DELETE FROM orders WHERE created_at < now() - interval '2 years';
ROLLBACK;
```

Utilisez toujours `BUFFERS` ; le temps seul ne dit pas si vous étiez lent à cause du disque ou du CPU.

### Lire la sortie

```text
Index Scan using idx_orders_customer on orders  (cost=0.43..8.45 rows=1 width=64) (actual time=0.021..0.023 rows=3 loops=1)
  Index Cond: (customer_id = 42)
  Buffers: shared hit=4
Planning Time: 0.110 ms
Execution Time: 0.045 ms
```

| Partie | Signification |
|---|---|
| `Index Scan using ...` | Le **nœud** (opération). Les plans sont des arbres : l'indentation = les enfants ; les données remontent des nœuds les **plus internes/profonds** vers la racine |
| `cost=0.43..8.45` | Unités du planificateur (pas des ms). `démarrage..total` : démarrage = coût avant la première ligne, total = coût pour toutes les lignes. Le coût d'un nœud inclut ses enfants |
| `rows=1` | Lignes **estimées** en sortie de ce nœud |
| `width=64` | Taille moyenne estimée d'une ligne en octets |
| `actual time=0.021..0.023` | ms réelles : temps jusqu'à la première ligne..temps jusqu'à la dernière ligne, **par boucle** |
| `rows=3` (actual) | Lignes **réelles** produites, **par boucle** |
| `loops=1` | Nombre d'exécutions du nœud. Temps total réel = `actual time × loops` ; lignes totales réelles = `rows × loops` |
| `Index Cond` / `Filter` | `Index Cond` est appliqué *dans* l'index (bien). `Filter` est appliqué *après* la lecture des lignes (lignes lues puis jetées) |
| `Rows Removed by Filter: N` | Lignes lues puis écartées. Grand N = travail gaspillé, un index manque probablement ou est inadapté |
| `Buffers: shared hit=4 read=2` | `hit` = trouvé dans le cache Postgres, `read` = lu depuis l'OS/disque, `dirtied/written` = écritures |
| `Planning Time` / `Execution Time` | Parsing+planification vs exécution. Le temps d'exécution exclut le transfert réseau vers le client |

### Nœuds de scan (comment une table est lue)

| Nœud | Ce qu'il fait | Quand c'est acceptable |
|---|---|---|
| `Seq Scan` | Lit toute la table | Petites tables, ou vous avez besoin d'une grande fraction des lignes (> ~5-10 %) |
| `Index Scan` | Parcourt l'index, puis lit chaque ligne dans la table (heap) | Peu de lignes |
| `Index Only Scan` | Répond depuis l'index seul. Vérifiez `Heap Fetches: 0` (sinon la visibility map est périmée, lancez `VACUUM`) | Index couvrant |
| `Bitmap Index Scan` + `Bitmap Heap Scan` | Construit un bitmap des pages correspondantes, les lit dans l'ordre physique | Nombre moyen de lignes, ou combinaison de plusieurs index (`BitmapOr/And`) |

Un `Seq Scan` n'est **pas toujours mauvais**. Il l'est quand il écarte l'essentiel de ce qu'il lit (`Rows Removed by Filter` énorme) sur une grosse table.

### Nœuds de jointure

| Nœud | Comment | Bon quand |
|---|---|---|
| `Nested Loop` | Pour chaque ligne externe, sonde le côté interne | Côté externe petit **et** côté interne indexé |
| `Hash Join` | Construit une table de hachage sur le plus petit côté, sonde avec l'autre | Grandes entrées non triées, jointures d'égalité |
| `Merge Join` | Fusionne deux entrées triées | Les deux entrées déjà triées (ex. par index) |

Autres nœuds : `Sort` (surveillez `Sort Method: external merge Disk: ...` = débordement sur disque, augmentez `work_mem` ou ajoutez un index), `HashAggregate` / `GroupAggregate`, `Limit`, `Materialize`, `Gather` (workers parallèles).

### Checklist des signaux d'alerte

1. **Lignes estimées et réelles très éloignées** (`rows=1` estimé, `rows=200000` réel) : statistiques périmées ou insuffisantes. Lancez `ANALYZE table;`, augmentez avec `ALTER TABLE t ALTER COLUMN c SET STATISTICS 500;`, ou ajoutez des statistiques étendues pour les colonnes corrélées. Une mauvaise estimation pousse le planificateur à choisir le mauvais type et le mauvais ordre de jointure.
2. **`Rows Removed by Filter`** bien plus grand que les lignes renvoyées : index manquant ou inadapté.
3. **`Seq Scan` sur une grosse table** renvoyant peu de lignes.
4. **`Nested Loop` avec un `loops` élevé** et un nœud interne lent : l'interne s'exécute N fois.
5. **`Sort Method: external merge Disk`** ou `Hash Batches > 1` : pas assez de `work_mem`.
6. **`Heap Fetches` élevé sur un Index Only Scan** : il faut un `VACUUM`.
7. **`Buffers: read` élevé** : cache froid ou working set trop gros ; lancez deux fois pour comparer chaud vs froid.
8. **Temps caché dans un enfant** : trouvez toujours le nœud au plus gros temps **exclusif** (son temps moins celui de ses enfants × loops).

### Méthode de tuning

1. Récupérez la vraie requête lente (`pg_stat_statements`, log des requêtes lentes `log_min_duration_statement`, logs applicatifs).
2. `EXPLAIN (ANALYZE, BUFFERS)` sur un volume de données réaliste (une BD de dev vide ment).
3. Trouvez le nœud le plus coûteux, comparez lignes estimées et réelles.
4. Corrigez : statistiques, index, réécriture de la requête, ou schéma. Changez **une seule chose à la fois**.
5. Relancez et comparez. Lancez deux fois pour chauffer le cache.
6. Vérifiez que l'index ne pénalise pas les écritures et qu'il est réellement utilisé (`pg_stat_user_indexes.idx_scan`).

Jeu de test utilisé dans les exemples :
```sql
CREATE TABLE customers (id bigserial PRIMARY KEY, email text NOT NULL, country text);
CREATE TABLE orders (
  id bigserial PRIMARY KEY, customer_id bigint NOT NULL, status text NOT NULL,
  total numeric(10,2) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), note text);
-- ~10k clients, ~1M commandes
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

## Exemple 1 : index manquant (Seq Scan)

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
Lecture : 1M de lignes lues pour en renvoyer 98 (`Rows Removed by Filter: 333300` × 3 workers). Correction :
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
48 ms → 0,25 ms. En production, utilisez `CREATE INDEX CONCURRENTLY` pour ne pas bloquer les écritures.

## Exemple 2 : index composite, l'ordre des colonnes compte

```sql
SELECT * FROM orders WHERE status = 'PAID' AND created_at >= now() - interval '7 days' ORDER BY created_at DESC LIMIT 20;
```
Règle empirique : **colonnes d'égalité d'abord, puis la colonne de plage/tri**.
```sql
CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);
```
```text
Limit  (actual time=0.03..0.09 rows=20 loops=1)
  ->  Index Scan using idx_orders_status_created on orders  (actual time=0.03..0.08 rows=20 loops=1)
        Index Cond: ((status = 'PAID') AND (created_at >= ...))
```
Pas de nœud `Sort` : l'index fournit déjà les lignes dans l'ordre demandé, et `LIMIT` s'arrête après 20 lignes. Avec les colonnes inversées `(created_at, status)`, l'index ne pourrait pas être utilisé aussi efficacement : `status` ne serait qu'un filtre dans un scan de plage.
Un index composite `(a, b)` sert `WHERE a`, `WHERE a AND b`, mais **pas** `WHERE b` seul (règle du préfixe le plus à gauche).

## Exemple 3 : une fonction sur une colonne tue l'index (sargabilité)

```sql
SELECT * FROM customers WHERE lower(email) = 'user42@mail.com';
```
```text
Seq Scan on customers  (actual time=0.02..6.1 rows=1 loops=1)
  Filter: (lower(email) = 'user42@mail.com')
  Rows Removed by Filter: 9999
```
Un index simple sur `email` est inutilisable car la requête ne compare pas `email`, elle compare `lower(email)`. Deux corrections :
```sql
-- A) réécrire pour que la colonne soit nue (seulement si les données sont déjà normalisées)
WHERE email = 'user42@mail.com'
-- B) indexer l'expression
CREATE INDEX idx_customers_email_lower ON customers (lower(email));
```
Même piège : `WHERE created_at::date = '2026-01-01'` (utilisez `created_at >= '2026-01-01' AND created_at < '2026-01-02'`), `WHERE col + 1 = 10`, `WHERE col LIKE '%abc'` (joker en tête ; utilisez un index GIN `pg_trgm`), et les casts implicites (`WHERE varchar_col = 123`).

## Exemple 4 : index couvrant → Index Only Scan

```sql
SELECT customer_id, total FROM orders WHERE customer_id = 42;
```
Avec `idx_orders_customer`, le plan visite encore la table pour `total`. Ajoutez la colonne avec `INCLUDE` :
```sql
CREATE INDEX idx_orders_customer_total ON orders (customer_id) INCLUDE (total);
```
```text
Index Only Scan using idx_orders_customer_total on orders  (actual time=0.03..0.06 rows=98 loops=1)
  Index Cond: (customer_id = 42)
  Heap Fetches: 0
  Buffers: shared hit=4
```
Compromis : index plus gros, écritures plus lentes. À réserver aux chemins de lecture chauds. `SELECT *` l'annule, ne sélectionnez que les colonnes nécessaires.

## Exemple 5 : mauvaise stratégie de jointure à cause d'estimations erronées

```sql
SELECT c.email, sum(o.total)
FROM customers c JOIN orders o ON o.customer_id = c.id
WHERE c.country = 'TN' AND o.created_at >= now() - interval '30 days'
GROUP BY c.email;
```
Symptôme d'un mauvais plan :
```text
Nested Loop  (cost=... rows=5) (actual time=... rows=41000 loops=1)
  ->  Seq Scan on customers c  (rows=5) (actual rows=2500 ...)
  ->  Index Scan using idx_orders_customer on orders o  (actual time=0.02..0.30 rows=16 loops=2500)
```
`rows=5` estimé vs `rows=2500` réel = le planificateur s'est trompé, donc il a choisi un Nested Loop. Que faire, dans l'ordre :
```sql
ANALYZE customers;                                            -- 1. rafraîchir les stats
ALTER TABLE customers ALTER COLUMN country SET STATISTICS 500; -- 2. histogramme plus fin
CREATE STATISTICS s_cust (dependencies) ON country, id FROM customers; -- 3. colonnes corrélées
CREATE INDEX idx_orders_created ON orders (created_at, customer_id);   -- 4. aider le gros côté
```
Une fois les estimations correctes, le planificateur bascule généralement sur un `Hash Join`, bien meilleur quand les deux côtés sont grands. Ne forcez pas les types de jointure avec `SET enable_nestloop = off` en production, utilisez-le seulement comme diagnostic pour voir ce que coûte l'alternative.

## Exemple 6 : pagination, OFFSET vs keyset

```sql
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 500000;
```
```text
Limit  (actual time=95.0..95.1 rows=20 loops=1)
  ->  Index Scan using orders_pkey on orders  (actual time=0.02..80.0 rows=500020 loops=1)
```
`OFFSET` lit et jette 500 000 lignes. Le coût croît avec le numéro de page. Pagination keyset (seek) :
```sql
SELECT * FROM orders WHERE id > :last_seen_id ORDER BY id LIMIT 20;
```
```text
Limit  (actual time=0.02..0.05 rows=20 loops=1)
  ->  Index Scan using orders_pkey on orders  (actual time=0.02..0.04 rows=20 loops=1)
        Index Cond: (id > 500000)
```
95 ms → 0,05 ms, constant quelle que soit la page. Pour des colonnes de tri non uniques, utilisez un tuple : `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC` avec un index sur `(created_at DESC, id DESC)`.

## Exemple 7 : index partiel (n'indexer que ce que vous interrogez)

```sql
-- 95 % des lignes sont SHIPPED/CANCELLED, l'application ne scrute que les commandes NEW
CREATE INDEX idx_orders_new ON orders (created_at) WHERE status = 'NEW';
SELECT * FROM orders WHERE status = 'NEW' ORDER BY created_at LIMIT 50;
```
Index petit, peu coûteux à maintenir. Le `WHERE` de la requête doit impliquer le prédicat de l'index (même littéral `status = 'NEW'`, un paramètre lié peut l'empêcher avec des plans génériques).

## Exemple 8 : tri qui déborde sur le disque

```text
Sort  (actual time=1200..1450 rows=1000000 loops=1)
  Sort Key: created_at
  Sort Method: external merge  Disk: 61240kB
```
Options : ajouter un index qui fournit l'ordre, ajouter un `LIMIT`, réduire les colonnes, ou augmenter `work_mem` **pour cette session/transaction** :
```sql
SET LOCAL work_mem = '128MB';   -- dans une transaction, ne l'augmentez pas globalement (c'est par nœud de tri/hash et par connexion)
```
Objectif : `Sort Method: quicksort  Memory: 25kB` (ou `top-N heapsort` avec `LIMIT`).

## Exemple 9 : le N+1 vu depuis la base de données

Symptôme dans `pg_stat_statements` : la même minuscule requête avec `calls` = 100 000. Chaque plan est parfait (0,05 ms) mais le total est énorme (5 s). `EXPLAIN` ne peut pas corriger ça, corrigez l'appelant :
```sql
-- au lieu de : SELECT * FROM orders WHERE customer_id = ?   (× N)
SELECT * FROM orders WHERE customer_id = ANY(:ids);
```
En JPA/Hibernate : `JOIN FETCH`, `@EntityGraph`, ou `@BatchSize`.

---

### Requêtes utiles

```sql
-- top requêtes par temps total (nécessite CREATE EXTENSION pg_stat_statements)
SELECT calls, round(total_exec_time::numeric,0) AS total_ms, round(mean_exec_time::numeric,2) AS mean_ms, left(query,80)
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;

-- index inutilisés (coût en écriture sans bénéfice en lecture)
SELECT relname, indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;

-- stats périmées / lignes mortes
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
```

Diagnostic uniquement (ne le laissez jamais activé en prod) : `SET enable_seqscan = off;` montre si le planificateur *peut* utiliser votre index et ce que cela coûterait.

Outils : [explain.dalibo.com](https://explain.dalibo.com), [explain.depesz.com](https://explain.depesz.com) : collez un plan, obtenez le nœud le plus lent mis en évidence.
