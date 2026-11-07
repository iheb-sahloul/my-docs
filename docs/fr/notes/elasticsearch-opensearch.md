# Elasticsearch & OpenSearch

Les exemples utilisent la syntaxe de Kibana Dev Tools, pour Elasticsearch 9.3. Les concepts et les labs d'examen sont dans le [module d'entretien Elasticsearch & OpenSearch](../interviews/elasticsearch-opensearch.md).

## Connexion

### curl

```bash
export ES=https://localhost:9200
curl -u elastic:$ES_PASSWORD --cacert http_ca.crt "$ES"
curl -H "Authorization: ApiKey $ES_API_KEY" "$ES/_cluster/health?pretty"
curl -s "$ES/_cat/indices?v&s=index"                         # cluster local, sécurité désactivée
curl -X POST "$ES/orders/_search" -H 'Content-Type: application/json' -d @query.json
curl -X POST "$ES/_bulk" -H 'Content-Type: application/x-ndjson' --data-binary @bulk.ndjson
```

### Paramètres d'URL utiles

| Paramètre | Effet |
|---|---|
| `?v` | `_cat` : affiche les en-têtes de colonnes |
| `?h=index,health` | `_cat` : choisit les colonnes |
| `?s=store.size:desc` | `_cat` : trie |
| `?help` | `_cat` : liste les colonnes disponibles |
| `?format=json` | `_cat` : sortie JSON |
| `?pretty` | JSON lisible |
| `?filter_path=hits.hits._id` | Réduit la réponse |
| `?human` | Tailles et durées lisibles |

---

## Santé du cluster

### `_cat` au quotidien

```text
GET _cat/health?v
GET _cat/nodes?v&h=name,node.role,master,heap.percent,ram.percent,cpu,load_1m,disk.used_percent
GET _cat/indices?v&s=store.size:desc&h=health,index,pri,rep,docs.count,store.size
GET _cat/shards?v&s=store:desc&h=index,shard,prirep,state,store,node,unassigned.reason
GET _cat/allocation?v
GET _cat/thread_pool/write,search?v&h=node_name,name,active,queue,rejected
GET _cat/recovery?v&active_only=true
GET _cat/segments/orders?v&h=index,segment,docs.count,size
GET _cat/fielddata?v
GET _cat/aliases?v
GET _cat/templates?v
```

### Signification des statuts

| Statut | Signification | Première action |
|---|---|---|
| Vert | Tous les shards sont assignés | Rien à faire |
| Jaune | Un réplica n'est pas assigné | Normal sur un nœud ; sinon, lancer allocation explain |
| Rouge | Un primaire n'est pas assigné, donc des données sont indisponibles | Allocation explain, puis corriger ou restaurer |

### Diagnostiquer

```text
GET _health_report
GET _cluster/health?level=indices
GET _cluster/pending_tasks
GET _nodes/hot_threads
GET _nodes/stats/breaker
GET _nodes/stats/jvm,fs,thread_pool
GET _tasks?detailed
GET _tasks?actions=*reindex&detailed
POST _tasks/<task_id>/_cancel
```

---

## Dépannage des shards

### Pourquoi un shard n'est-il pas assigné ?

```text
GET _cluster/allocation/explain
{ "index": "orders", "shard": 0, "primary": true }
```

| Decider | Cause probable | Correction |
|---|---|---|
| `same_shard` | Un nœud ne peut pas héberger un primaire et son réplica | Ajouter un nœud, ou passer les réplicas à 0 |
| `filter` | `index.routing.allocation.*` ne correspond à aucun nœud | Corriger ou retirer la règle |
| `disk_threshold` | Disque au-dessus du watermark | Libérer du disque ou ajouter de la capacité |
| `max_retry` | Trop de tentatives échouées | Corriger la cause, puis réessayer |
| `data_tier` | Aucun nœud dans le tier demandé | En ajouter un, ou changer `_tier_preference` |

### Réparer

```text
POST _cluster/reroute?retry_failed=true

PUT orders/_settings
{ "index.routing.allocation.require.data_zone": null }

PUT orders/_settings
{ "index.number_of_replicas": 0 }
```

### Watermarks disque

| Défaut | Effet |
|---|---|
| 85 % (low) | Aucun nouveau shard sur le nœud |
| 90 % (high) | Des shards quittent le nœud |
| 95 % (flood stage) | Les index du nœud passent en lecture seule |

```text
GET _cluster/settings?include_defaults=true&filter_path=defaults.cluster.routing.allocation.disk.watermark
PUT orders/_settings
{ "index.blocks.read_only_allow_delete": null }    # après avoir libéré du disque
```

### Redémarrage progressif

```text
PUT _cluster/settings
{ "persistent": { "cluster.routing.allocation.enable": "primaries" } }
POST _flush
# redémarrer le nœud, attendre qu'il revienne
PUT _cluster/settings
{ "persistent": { "cluster.routing.allocation.enable": null } }
```

---

## Index et mappings

### Créer et inspecter

```text
PUT orders
{
  "settings": { "number_of_shards": 1, "number_of_replicas": 1 },
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "created_at": { "type": "date" },
      "status":     { "type": "keyword" },
      "title":      { "type": "text", "fields": { "raw": { "type": "keyword" } } },
      "price":      { "type": "scaled_float", "scaling_factor": 100 },
      "lines":      { "type": "nested" }
    }
  }
}

GET orders
GET orders/_mapping
GET orders/_mapping/field/status
GET orders/_settings
GET orders/_field_caps?fields=status
GET orders/_stats/docs,store
```

### Types de champs

| Type | Usage |
|---|---|
| `text` | Recherche plein texte, analysé |
| `keyword` | Valeurs exactes, filtres, tri, agrégations |
| `date`, `long`, `double`, `boolean` | Valeurs typées, plages |
| `scaled_float` | Prix à précision fixe |
| `nested` | Tableaux d'objets interrogés ensemble |
| `flattened` | Clés arbitraires sans explosion du mapping |
| `geo_point` | Coordonnées |
| `dense_vector` | Embeddings, kNN |

### Modifier un index

```text
PUT orders/_mapping                       # ajouter un champ ; les types existants ne changent pas
{ "properties": { "channel": { "type": "keyword" } } }

PUT orders/_settings
{ "index.refresh_interval": "30s" }

POST orders/_refresh
POST orders/_forcemerge?max_num_segments=1    # uniquement sur des index en lecture seule
PUT orders/_block/write
POST orders/_clone/orders-copy
POST orders/_close
POST orders/_open
DELETE orders
```

### Tester l'analyse

```text
POST _analyze
{ "tokenizer": "standard", "filter": ["lowercase", "asciifolding"], "text": "Café Crème" }

POST orders/_analyze
{ "field": "title", "text": "Blue Trainers" }
```

---

## Templates

```text
PUT _component_template/base-settings
{ "template": { "settings": { "number_of_replicas": 1 } } }

PUT _index_template/orders
{
  "index_patterns": ["orders-*"],
  "composed_of": ["base-settings"],
  "priority": 200,
  "template": { "mappings": { "properties": { "created_at": { "type": "date" } } } }
}

POST _index_template/_simulate_index/orders-2026
GET _index_template/orders
```

---

## Documents

```text
POST orders/_doc                          # id généré
{ "status": "PAID" }
PUT orders/_doc/1                         # créer ou remplacer
PUT orders/_create/1                      # échoue s'il existe
GET orders/_doc/1
GET orders/_source/1
POST orders/_mget
{ "ids": ["1", "2"] }
POST orders/_update/1
{ "doc": { "status": "SHIPPED" } }
POST orders/_update/1
{ "script": { "source": "ctx._source.quantity += params.n", "params": { "n": 1 } } }
DELETE orders/_doc/1
```

### Bulk

```text
POST _bulk
{"index":{"_index":"orders","_id":"1"}}
{"status":"PAID"}
{"update":{"_index":"orders","_id":"1"}}
{"doc":{"status":"SHIPPED"}}
{"delete":{"_index":"orders","_id":"2"}}
```

Un HTTP `200` ne veut pas dire succès : vérifiez `errors` et le `status` de chaque élément. Chaque ligne se termine par un saut de ligne, y compris la dernière.

---

## Recherche

### Requêtes courantes

| Besoin | Requête |
|---|---|
| Plein texte | `match` |
| Plusieurs champs | `multi_match` |
| Phrase exacte | `match_phrase` |
| Valeur exacte | `term`, `terms` |
| Nombres et dates | `range` |
| Champ présent | `exists` |
| Fautes de frappe | `match` avec `"fuzziness": "AUTO"` |
| Combiner | `bool` |
| Score métier | `function_score` |

### `bool`

```text
GET orders/_search
{
  "query": { "bool": {
    "must":     [ { "match": { "title": "running shoes" } } ],
    "filter":   [ { "term": { "status": "PAID" } },
                  { "range": { "created_at": { "gte": "now-30d/d" } } } ],
    "should":   [ { "match_phrase": { "title": "trail running" } } ],
    "must_not": [ { "term": { "category": "socks" } } ]
  } },
  "_source": ["title", "price"],
  "track_total_hits": true
}
```

### Tri, surlignage, collapse

```text
GET orders/_search
{
  "query": { "match": { "title": "running" } },
  "sort": [ { "brand": { "order": "asc", "missing": "_last" } }, "_score" ],
  "highlight": { "fields": { "title": {} } },
  "collapse": { "field": "brand" }
}
```

### Pagination

| Méthode | Usage | Limite |
|---|---|---|
| `from` + `size` | Premières pages affichées aux utilisateurs | `from + size` ≤ 10 000 par défaut |
| `search_after` + PIT | Parcours profond ou complet | Demande un tri stable |
| `scroll` | Code ancien | N'est plus recommandé pour la pagination profonde |

```text
POST orders/_pit?keep_alive=2m
GET _search
{ "size": 100, "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "created_at": "desc" }, { "_shard_doc": "asc" } ],
  "search_after": ["<last sort values>"] }
DELETE _pit
{ "id": "<pit_id>" }
```

### Comprendre une requête

```text
POST orders/_validate/query?explain=true
{ "query": { "match": { "title": "running shoes" } } }

POST orders/_explain/1
{ "query": { "match": { "title": "running" } } }

GET orders/_search
{ "profile": true, "query": { "match": { "title": "running" } } }

POST orders/_termvectors/1
{ "fields": ["title"] }
```

### Recherche hybride

```text
GET products/_search
{ "retriever": { "rrf": {
  "retrievers": [
    { "standard": { "query": { "match": { "title": "running" } } } },
    { "knn": { "field": "embedding", "query_vector": [0.1, 0.2, 0.3], "k": 5, "num_candidates": 20 } } ],
  "rank_window_size": 50 } } }
```

---

## Agrégations

```text
GET orders/_search
{
  "size": 0,
  "aggs": {
    "per_month": {
      "date_histogram": { "field": "created_at", "calendar_interval": "month" },
      "aggs": {
        "revenue": { "sum": { "field": "price" } },
        "running_total": { "cumulative_sum": { "buckets_path": "revenue" } }
      }
    },
    "best_month": { "max_bucket": { "buckets_path": "per_month>revenue" } },
    "by_category": {
      "terms": { "field": "category", "size": 5, "order": { "avg_price": "desc" } },
      "aggs": { "avg_price": { "avg": { "field": "price" } } }
    },
    "price_bands": { "range": { "field": "price",
      "ranges": [ { "to": 50 }, { "from": 50, "to": 100 }, { "from": 100 } ] } },
    "paid_only": { "filter": { "term": { "status": "PAID" } },
      "aggs": { "total": { "sum": { "field": "price" } } } },
    "brands": { "cardinality": { "field": "brand" } },
    "latency": { "percentiles": { "field": "price", "percents": [50, 95] } }
  }
}
```

| Famille | Exemples |
|---|---|
| Métrique | `avg`, `sum`, `min`, `max`, `stats`, `cardinality`, `percentiles` |
| Bucket | `terms`, `date_histogram`, `histogram`, `range`, `filter`, `composite` |
| Pipeline | `cumulative_sum`, `derivative`, `max_bucket`, `bucket_sort` |

---

## Ingest pipelines

```text
PUT _ingest/pipeline/normalize
{
  "processors": [
    { "lowercase": { "field": "email" } },
    { "set": { "field": "ingested_at", "value": "{{{_ingest.timestamp}}}" } },
    { "script": { "source": "ctx.total = ctx.quantity * ctx.unit_price" } }
  ],
  "on_failure": [ { "set": { "field": "_index", "value": "failed-orders" } } ]
}

POST _ingest/pipeline/normalize/_simulate
{ "docs": [ { "_source": { "email": "A@B.C", "quantity": 2, "unit_price": 5 } } ] }

POST orders/_doc?pipeline=normalize
{ "email": "A@B.C", "quantity": 2, "unit_price": 5 }

PUT orders/_settings
{ "index.default_pipeline": "normalize" }
```

### Painless : où sont les données

| Contexte | Lire un champ | Sortie |
|---|---|---|
| Ingest pipeline | `ctx.price` | Affecter à `ctx.total` |
| Update, `_update_by_query`, `_reindex` | `ctx._source.price` | Affecter à `ctx._source.total` |
| Runtime field | `doc['price'].value` | `emit(valeur)` |

---

## Reindex et alias

```text
POST _reindex?wait_for_completion=false&slices=auto
{ "source": { "index": "orders-v1" }, "dest": { "index": "orders-v2" } }
GET _tasks/<task_id>                     # attendre la fin

POST orders-v1/_update_by_query?conflicts=proceed
{ "query": { "term": { "status": "NEW" } },
  "script": { "source": "ctx._source.status = 'OPEN'" } }

POST orders-v1/_delete_by_query?conflicts=proceed
{ "query": { "term": { "status": "TEST" } } }

POST _aliases                            # bascule atomique
{ "actions": [
  { "remove": { "index": "orders-v1", "alias": "orders" } },
  { "add":    { "index": "orders-v2", "alias": "orders" } } ] }

POST _aliases                            # alias filtré
{ "actions": [ { "add": { "index": "orders-v2", "alias": "orders-paid",
  "filter": { "term": { "status": "PAID" } } } } ] }
```

Créez d'abord l'index de destination, sinon `_reindex` utilise des mappings dynamiques.

---

## Data streams et ILM

```text
PUT _ilm/policy/logs-30d
{ "policy": { "phases": {
  "hot":    { "actions": { "rollover": { "max_age": "1d", "max_primary_shard_size": "50gb" } } },
  "warm":   { "min_age": "7d",  "actions": { "forcemerge": { "max_num_segments": 1 } } },
  "delete": { "min_age": "30d", "actions": { "delete": {} } } } } }

PUT _index_template/app-events
{ "index_patterns": ["app-events*"], "data_stream": {}, "priority": 200,
  "template": { "settings": { "index.lifecycle.name": "logs-30d" } } }

GET _data_stream/app-events
GET _data_stream/_stats
POST app-events/_rollover
GET app-events/_ilm/explain
GET */_ilm/explain?only_errors=true
GET _ilm/status
```

---

## Snapshots

```text
PUT _snapshot/backups
{ "type": "fs", "settings": { "location": "/mnt/backups" } }    # path.repo doit l'autoriser
POST _snapshot/backups/_verify

PUT _snapshot/backups/snap-1?wait_for_completion=true
{ "indices": "orders-*", "include_global_state": false }
GET _cat/snapshots/backups?v
GET _snapshot/_status

POST _snapshot/backups/snap-1/_restore
{ "indices": "orders-v1", "rename_pattern": "(.+)", "rename_replacement": "restored-$1" }

PUT _slm/policy/nightly
{ "schedule": "0 30 1 * * ?", "name": "<nightly-{now/d}>", "repository": "backups",
  "config": { "indices": ["*"] },
  "retention": { "expire_after": "30d", "min_count": 5, "max_count": 50 } }
POST _slm/policy/nightly/_execute
GET _slm/stats

POST _snapshot/backups/snap-1/_mount?storage=shared_cache    # searchable snapshot, lecture seule
{ "index": "orders-v1", "renamed_index": "orders-frozen" }
```

---

## Cross-cluster

```text
PUT _cluster/settings
{ "persistent": { "cluster": { "remote": { "eu": {
  "mode": "sniff", "seeds": ["es-eu:9300"], "skip_unavailable": true } } } } }
GET _remote/info
GET orders,eu:orders/_search

PUT orders-eu/_ccr/follow?wait_for_active_shards=1      # à lancer sur le cluster follower
{ "remote_cluster": "eu", "leader_index": "orders" }
GET orders-eu/_ccr/stats
GET _ccr/stats
```

---

## Elasticsearch vs OpenSearch : différences d'API {#elasticsearch-vs-opensearch-api-differences}

Chemins vérifiés sur Elasticsearch 9.3.0 et OpenSearch 3.9.0. Les lignes sécurité, UI et client Java n'ont pas été exécutées.

| Sujet | Elasticsearch | OpenSearch |
|---|---|---|
| Cycle de vie | `_ilm/policy/<name>` | `_plugins/_ism/policies/<name>` (états et transitions) |
| État du cycle de vie | `<index>/_ilm/explain` | `_plugins/_ism/explain/<index>` |
| Champ vectoriel | `dense_vector` avec `dims` | `knn_vector` avec `dimension`, et `index.knn: true` |
| Requête vectorielle | Retriever `knn` ou `knn` au niveau racine | Requête `knn` dans `query` |
| Point in time | `POST <index>/_pit` | `POST <index>/_search/point_in_time` |
| Recherche asynchrone | `<index>/_async_search` | `_plugins/_asynchronous_search` |
| Champs à la requête | `runtime_mappings` | `derived` |
| Réplication | `_ccr/...` | `_plugins/_replication/...` |
| API de sécurité | `_security/...` | `_plugins/_security/api/...` |
| SQL | `_sql` | `_plugins/_sql` |
| Nœud master | `_cat/master`, rôle `master` | `_cat/cluster_manager`, rôle `cluster_manager` |
| UI | Kibana | OpenSearch Dashboards |
| Client Java | `co.elastic.clients:elasticsearch-java` | `org.opensearch.client:opensearch-java` |

Encore proches dans les deux : `_cat`, `_bulk`, `_index_template`, les bases du Query DSL, les agrégations, les ingest pipelines et les data streams.
