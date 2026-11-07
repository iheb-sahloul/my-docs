# Elasticsearch & OpenSearch

Examples use Kibana Dev Tools syntax, for Elasticsearch 9.3. The concepts and exam labs are in the [Elasticsearch & OpenSearch interview module](../interviews/elasticsearch-opensearch.md).

## Connect

### curl

```bash
export ES=https://localhost:9200
curl -u elastic:$ES_PASSWORD --cacert http_ca.crt "$ES"
curl -H "Authorization: ApiKey $ES_API_KEY" "$ES/_cluster/health?pretty"
curl -s "$ES/_cat/indices?v&s=index"                         # local cluster, security off
curl -X POST "$ES/orders/_search" -H 'Content-Type: application/json' -d @query.json
curl -X POST "$ES/_bulk" -H 'Content-Type: application/x-ndjson' --data-binary @bulk.ndjson
```

### Useful URL parameters

| Parameter | Does |
|---|---|
| `?v` | `_cat`: show column headers |
| `?h=index,health` | `_cat`: choose columns |
| `?s=store.size:desc` | `_cat`: sort |
| `?help` | `_cat`: list available columns |
| `?format=json` | `_cat`: JSON output |
| `?pretty` | Readable JSON |
| `?filter_path=hits.hits._id` | Trim the response |
| `?human` | Readable sizes and durations |

---

## Cluster health

### Daily `_cat`

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

### Status meaning

| Status | Means | First step |
|---|---|---|
| Green | All shards assigned | Nothing to do |
| Yellow | A replica is unassigned | Normal on one node; otherwise run allocation explain |
| Red | A primary is unassigned, so data is unavailable | Allocation explain, then fix or restore |

### Diagnose

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

## Shard troubleshooting

### Why is a shard unassigned?

```text
GET _cluster/allocation/explain
{ "index": "orders", "shard": 0, "primary": true }
```

| Decider | Likely cause | Fix |
|---|---|---|
| `same_shard` | One node cannot hold a primary and its replica | Add a node, or set replicas to 0 |
| `filter` | `index.routing.allocation.*` matches no node | Correct or remove the rule |
| `disk_threshold` | Disk above the watermark | Free disk or add capacity |
| `max_retry` | Too many failed attempts | Fix the cause, then retry |
| `data_tier` | No node in the requested tier | Add one, or change `_tier_preference` |

### Repair

```text
POST _cluster/reroute?retry_failed=true

PUT orders/_settings
{ "index.routing.allocation.require.data_zone": null }

PUT orders/_settings
{ "index.number_of_replicas": 0 }
```

### Disk watermarks

| Default | Effect |
|---|---|
| 85% (low) | No new shards on the node |
| 90% (high) | Shards move away from the node |
| 95% (flood stage) | Indices on the node become read-only |

```text
GET _cluster/settings?include_defaults=true&filter_path=defaults.cluster.routing.allocation.disk.watermark
PUT orders/_settings
{ "index.blocks.read_only_allow_delete": null }    # after freeing disk
```

### Rolling restart

```text
PUT _cluster/settings
{ "persistent": { "cluster.routing.allocation.enable": "primaries" } }
POST _flush
# restart the node, wait for it to rejoin
PUT _cluster/settings
{ "persistent": { "cluster.routing.allocation.enable": null } }
```

---

## Indices and mappings

### Create and inspect

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

### Field types

| Type | Use it for |
|---|---|
| `text` | Full-text search, analyzed |
| `keyword` | Exact values, filters, sort, aggregations |
| `date`, `long`, `double`, `boolean` | Typed values, ranges |
| `scaled_float` | Prices with fixed precision |
| `nested` | Arrays of objects queried together |
| `flattened` | Arbitrary keys without a mapping explosion |
| `geo_point` | Coordinates |
| `dense_vector` | Embeddings, kNN |

### Change an index

```text
PUT orders/_mapping                       # add a field; existing types cannot change
{ "properties": { "channel": { "type": "keyword" } } }

PUT orders/_settings
{ "index.refresh_interval": "30s" }

POST orders/_refresh
POST orders/_forcemerge?max_num_segments=1    # only on read-only indices
PUT orders/_block/write
POST orders/_clone/orders-copy
POST orders/_close
POST orders/_open
DELETE orders
```

### Test analysis

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
POST orders/_doc                          # generated id
{ "status": "PAID" }
PUT orders/_doc/1                         # create or replace
PUT orders/_create/1                      # fail if it exists
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

HTTP `200` does not mean success: check `errors` and each item's `status`. Each line ends with a newline, including the last one.

---

## Search

### Common queries

| Need | Query |
|---|---|
| Full text | `match` |
| Several fields | `multi_match` |
| Exact phrase | `match_phrase` |
| Exact value | `term`, `terms` |
| Numbers and dates | `range` |
| Field is present | `exists` |
| Typos | `match` with `"fuzziness": "AUTO"` |
| Combine | `bool` |
| Business scoring | `function_score` |

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

### Sort, highlight, collapse

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

| Method | Use it for | Limit |
|---|---|---|
| `from` + `size` | First pages shown to users | `from + size` ≤ 10,000 by default |
| `search_after` + PIT | Deep or full traversal | Needs a stable sort |
| `scroll` | Older code | No longer recommended for deep pagination |

```text
POST orders/_pit?keep_alive=2m
GET _search
{ "size": 100, "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "created_at": "desc" }, { "_shard_doc": "asc" } ],
  "search_after": ["<last sort values>"] }
DELETE _pit
{ "id": "<pit_id>" }
```

### Understand a query

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

### Hybrid search

```text
GET products/_search
{ "retriever": { "rrf": {
  "retrievers": [
    { "standard": { "query": { "match": { "title": "running" } } } },
    { "knn": { "field": "embedding", "query_vector": [0.1, 0.2, 0.3], "k": 5, "num_candidates": 20 } } ],
  "rank_window_size": 50 } } }
```

---

## Aggregations

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

| Family | Examples |
|---|---|
| Metric | `avg`, `sum`, `min`, `max`, `stats`, `cardinality`, `percentiles` |
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

### Painless: where the data lives

| Context | Read a field | Output |
|---|---|---|
| Ingest pipeline | `ctx.price` | Assign to `ctx.total` |
| Update, `_update_by_query`, `_reindex` | `ctx._source.price` | Assign to `ctx._source.total` |
| Runtime field | `doc['price'].value` | `emit(value)` |

---

## Reindex and aliases

```text
POST _reindex?wait_for_completion=false&slices=auto
{ "source": { "index": "orders-v1" }, "dest": { "index": "orders-v2" } }
GET _tasks/<task_id>                     # wait until it completes

POST orders-v1/_update_by_query?conflicts=proceed
{ "query": { "term": { "status": "NEW" } },
  "script": { "source": "ctx._source.status = 'OPEN'" } }

POST orders-v1/_delete_by_query?conflicts=proceed
{ "query": { "term": { "status": "TEST" } } }

POST _aliases                            # atomic swap
{ "actions": [
  { "remove": { "index": "orders-v1", "alias": "orders" } },
  { "add":    { "index": "orders-v2", "alias": "orders" } } ] }

POST _aliases                            # filtered alias
{ "actions": [ { "add": { "index": "orders-v2", "alias": "orders-paid",
  "filter": { "term": { "status": "PAID" } } } } ] }
```

Create the destination index first, otherwise `_reindex` uses dynamic mappings.

---

## Data streams and ILM

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
{ "type": "fs", "settings": { "location": "/mnt/backups" } }    # path.repo must allow it
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

POST _snapshot/backups/snap-1/_mount?storage=shared_cache    # searchable snapshot, read-only
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

PUT orders-eu/_ccr/follow?wait_for_active_shards=1      # run on the follower cluster
{ "remote_cluster": "eu", "leader_index": "orders" }
GET orders-eu/_ccr/stats
GET _ccr/stats
```

---

## Elasticsearch vs OpenSearch: API differences {#elasticsearch-vs-opensearch-api-differences}

Paths checked on Elasticsearch 9.3.0 and OpenSearch 3.9.0. The security, UI and Java client rows were not run.

| Topic | Elasticsearch | OpenSearch |
|---|---|---|
| Lifecycle | `_ilm/policy/<name>` | `_plugins/_ism/policies/<name>` (states and transitions) |
| Lifecycle status | `<index>/_ilm/explain` | `_plugins/_ism/explain/<index>` |
| Vector field | `dense_vector` with `dims` | `knn_vector` with `dimension`, and `index.knn: true` |
| Vector query | `knn` retriever or top-level `knn` | `knn` query inside `query` |
| Point in time | `POST <index>/_pit` | `POST <index>/_search/point_in_time` |
| Async search | `<index>/_async_search` | `_plugins/_asynchronous_search` |
| Query-time fields | `runtime_mappings` | `derived` |
| Replication | `_ccr/...` | `_plugins/_replication/...` |
| Security API | `_security/...` | `_plugins/_security/api/...` |
| SQL | `_sql` | `_plugins/_sql` |
| Master node | `_cat/master`, `master` role | `_cat/cluster_manager`, `cluster_manager` role |
| UI | Kibana | OpenSearch Dashboards |
| Java client | `co.elastic.clients:elasticsearch-java` | `org.opensearch.client:opensearch-java` |

Still close in both: `_cat`, `_bulk`, `_index_template`, Query DSL basics, aggregations, ingest pipelines and data streams.
