# Elasticsearch & OpenSearch

Search engine questions: Lucene internals, mappings and analysis, shards, relevance, cluster operations, and the differences between the two products. Where search fits in an architecture is in System Design ([System Design Q10](system-design.md#search-feature-fit-design-just), [System Design R19](system-design.md#patients-search-dermatologist-near-earliest)). The second half of this page is a hands-on lab set for the Elastic Certified Engineer exam. The commands are in the [Elasticsearch notes](../notes/elasticsearch-opensearch.md).

## 🟢 Fundamentals

#### Q1. What is an inverted index, and what is a Lucene segment? {#inverted-index-lucene-segment}
**Answer:** An inverted index maps each **term** to the list of documents that contain it, so a search looks up terms instead of scanning documents. That is why `match` on a word is fast while `LIKE '%word%'` on a database is not. Lucene writes the index as immutable **segments**. New documents go into new segments, a delete only marks a document as deleted, and an update is a delete plus an insert. Background **merges** combine small segments and purge deleted documents. Immutability gives lock-free reads and good caching, at the cost of write amplification. Aggregations and sorting use a different structure, **doc values**, a column store on disk. Details: the stored term is the one **produced by the analyzer** (lowercased, accents stripped, stemmed), and the query must go through the same analyzer, otherwise it finds nothing. `LIKE '%term%'` cannot use a B-tree index (unknown prefix): full scan, no notion of relevance. To "why not just Postgres?": Postgres full-text (`tsvector`, GIN) is enough for simple search over a few million rows; Elasticsearch becomes relevant with fine relevance, facets, autocomplete, multilingual support and volume ([System design Q10](system-design.md#search-feature-fit-design-just)).

**Example:**

```text
Documents:                        Inverted index (after analysis):
1: "Folding electric bike"        electric   -> [1, 3]
2: "Carbon road bike"              bike       -> [1, 2]
3: "Electric scooter"              folding    -> [1]
                                  road       -> [2]
                                  carbon     -> [2]
                                  scooter    -> [3]
```

#### Q2. What are nodes, shards and replicas? {#nodes-shards-replicas}
**Answer:** A **cluster** is a set of nodes with one elected master. Roles separate the work: `master` (cluster state), `data_hot`/`data_warm`/`data_cold`/`data_frozen` (tiers), `ingest` (pipelines), and coordinating-only nodes. An index is split into **primary shards**, each one a full Lucene index. **Replicas** are copies that give failover and extra read capacity. The primary count is fixed at creation because routing uses `hash(_routing) % number_of_primary_shards`; changing it needs `_split`, `_shrink` or a reindex. The replica count can change at any time. A primary and its replica are never on the same node, so on one node a replica stays unassigned and the index is yellow.

#### Q3. What is the difference between `text` and `keyword`, and what does an analyzer do? {#text-keyword-analyzer}
**Answer:** A `text` field is **analyzed** into terms for full-text search. A `keyword` field is stored as one exact value, for filters, sorting and aggregations. An analyzer runs three stages: **character filters** (strip HTML, map characters), one **tokenizer** (split into tokens), and **token filters** (lowercase, stemming, synonyms). The classic bug is a `term` query on a `text` field: `term` does not analyze its input, so `"Blue Trainers"` never matches the stored terms `blue` and `trainers`. Use `match` on `text`, `term` on `keyword`, and **multi-fields** when you need both. Sorting on `text` fails, as the error says: `Fielddata is disabled on [title]`.

**Example:**

```text
POST products/_analyze
{ "analyzer": "standard", "text": "Blue Trainers!" }   # tokens: blue, trainers
```

#### Q4. What is the difference between query context and filter context? {#query-filter-context-bm25}
**Answer:** **Query context** answers "how well does this match?" and computes a `_score`. **Filter context** answers "does it match?", computes no score, and its results can be cached. In a `bool` query, `must` and `should` score, while `filter` and `must_not` do not. Put every exact condition (status, date range, tenant) in `filter`: it is faster and does not distort relevance. The default scoring is **BM25**: rare terms weigh more (IDF), repeated terms help with diminishing returns (TF saturation), and short fields rank higher (length normalization). Scores are computed per shard, so with few documents the same query can rank differently across shards. Score levers, from simplest to finest: field boost (`"fields": ["title^3", "description"]`), `bool` structure with `should` ([Q5](#match-vs-term-bool-query)), `function_score`/`script_score` (popularity, freshness via `gauss` on a date, margin, stock), `rescore` (expensive query applied to the top N), and as a last resort `k1` (≈ 1.2) / `b` (0.75) via `similarity`. For debugging, `"explain": true` details the computation, and `?search_type=dfs_query_then_fetch` (or a single shard for a small index) neutralizes the per-shard IDF. Never compare scores across two queries and never filter on an absolute score threshold. Relevance tuning is decided with the business, by measuring ([Q23](#relevance-tuning-hybrid)).

**`function_score` example:**

```text
GET products/_search
{
  "query": {
    "function_score": {
      "query": { "multi_match": { "query": "electric bike", "fields": ["title^3", "description"] } },
      "functions": [
        { "field_value_factor": { "field": "sales_30d", "modifier": "log1p", "factor": 0.5 } },
        { "gauss": { "published_at": { "origin": "now", "scale": "30d", "decay": 0.5 } } }
      ],
      "boost_mode": "multiply"
    }
  }
}
```

#### Q5. `match` vs `term`, and how do you structure a `bool` query? {#match-vs-term-bool-query}
**Answer:** `match` analyzes the query text (for `text` fields); `term` looks for the **exact** term with no analysis (`keyword`, numbers, dates). A `term` on a `text` field often fails silently: `term: {title: "Vélo"}` finds nothing because the index contains `velo`. `bool` combines `must` (must match, **counts toward the score**), `should` (boosts the score, or at least `minimum_should_match`), `filter` (must match, **no score**, **cached**) and `must_not` (exclusion, no score). Everything yes/no (category, price, stock, access rights) goes in `filter`: faster, and it does not distort relevance. In a `bool` that has a `must` or a `filter`, `should` clauses become optional: they only boost. For `multi_match`, `best_fields` (best field wins) differs from `most_fields` (sum) and `cross_fields` (terms may be spread across several fields, ideal for first name + last name). `query_string` exposes Lucene syntax to the user: an unclosed parenthesis returns a 400. For a public search box, prefer `simple_query_string` or `multi_match`.

**Example:**

```text
GET products/_search
{
  "query": {
    "bool": {
      "must":   [ { "multi_match": { "query": "electric folding bike",
                                     "fields": ["title^3", "description"],
                                     "type": "best_fields", "operator": "and",
                                     "fuzziness": "AUTO" } } ],
      "should": [ { "match_phrase": { "title": { "query": "electric bike", "boost": 2 } } } ],
      "filter": [ { "term":  { "brand": "decathlon" } },
                  { "range": { "price": { "gte": 300, "lte": 1500 } } },
                  { "term":  { "in_stock": true } } ],
      "must_not": [ { "term": { "status": "archived" } } ]
    }
  }
}
```

#### Q6. Why is search "near real time"? What do `refresh` and `flush` do? {#refresh-flush-translog}
**Answer:** An indexed document is first in an in-memory buffer and in the **translog**, a durable log on disk. It is not searchable yet. **Refresh** (every second by default on indices being searched) turns the buffer into a new searchable segment. **Flush** runs a Lucene commit and trims the translog. So a successful write is durable right away but only visible after the next refresh, while `GET _doc/<id>` is real time. Using `?refresh=true` on every write creates tiny segments and hurts throughput. If a caller must read its own write, prefer `?refresh=wait_for`. For bulk loads, raise `index.refresh_interval` to `30s` or more. Practical consequences: an update = delete + full reindex of the document (updating a counter 1,000 times per second in ES is a bad idea); for a bulk import, `refresh_interval: -1` and `number_of_replicas: 0` during loading, then restore `1s` and `1`, and possibly `_forcemerge` on an index that will no longer change; an integration test that indexes then searches must call `_refresh` (or `?refresh=wait_for`), otherwise it is flaky. On the storage side: **doc values** (on-disk columns, for sorting/aggregations/scripts) are on by default for `keyword`, numbers and dates but **absent on `text`** (hence `fielddata is disabled on text fields`); `_source` is the original JSON, returned in results and required by `_reindex` and `update` (disabling it saves space but rules them out).

## 🟡 Senior traps

#### Q7. What is a mapping explosion, and how do you control `dynamic`? {#mapping-explosion-dynamic}
**Answer:** With dynamic mapping, each new JSON key becomes a field in the cluster state. If the keys are data (user ids, metric names), the mapping grows without limit, slows every cluster state update and uses heap. At 1,000 fields the default `index.mapping.total_fields.limit` rejects documents. Options for `dynamic`: `true` adds fields, `false` keeps them in `_source` but does not index them, `strict` rejects the document, and `runtime` maps them as runtime fields. Use `strict` on domain indices, and model user-defined attributes as a `flattened` field or as a `nested` key/value list. Dynamic detection is a second trap: the first value decides the type forever, and a field type cannot be changed later. For an explicit mapping, combine the types: `keyword` with `normalizer: lowercase` for a brand, `scaled_float` (`scaling_factor: 100`) for a price, `flattened` for free-form attributes, `nested` for variants, and multi-fields (`title.raw` as `keyword`, `title.suggest` as `search_as_you_type`). Trap: if the first document has `"price": "12"`, the field becomes `text`: always define the mapping (or an index template) before indexing. See [Q3](#text-keyword-analyzer) and [Q11](#nested-object-join).

**Example:**

```text
PUT products/_mapping
{
  "dynamic": "strict",
  "properties": {
    "sku":       { "type": "keyword" },
    "title":     { "type": "text", "analyzer": "fr_text",
                   "fields": { "raw": { "type": "keyword" },
                               "suggest": { "type": "search_as_you_type" } } },
    "brand":     { "type": "keyword", "normalizer": "lowercase" },
    "price":     { "type": "scaled_float", "scaling_factor": 100 },
    "attributes":{ "type": "flattened" },
    "variants":  { "type": "nested",
                   "properties": { "color": { "type": "keyword" }, "size": { "type": "keyword" } } }
  }
}
```

#### Q8. What does an analyzer do, and how do you configure correct analysis for French? {#french-analysis-elision-stemming}
**Answer:** An analyzer = 0..n **char filters** (clean raw text, e.g. HTML) → 1 **tokenizer** → 0..n **token filters** (lowercase, elision, stop words, stemming, synonyms, ASCII folding). It applies at index time **and** at query time (unless a different `search_analyzer` is set). For French: `elision` (`l'avion` → `avion`), then `lowercase`, `stop`, `asciifolding` and a stemmer. Test before debating: `POST products/_analyze { "analyzer": "fr_text", "text": "L'électricité des vélos" }` → `electricit`, `velo`. Traps: filter order matters (`lowercase` before `stop`, because the list is lowercase; `elision` before the rest); aggressive stemmer (`french`) vs light (`light_french`): the aggressive one matches more words but creates false positives, the light one is usually the right default; changing an analyzer does **not** affect already indexed documents, you must **reindex** ([Q13](#reindex-zero-downtime-alias)); keep a `keyword` subfield (`title.raw`) for sorting, facets and exact equality. This is the question that separates someone who "used ES" from someone who configured it: make `_analyze` a reflex for any "why does this document not show up" debugging.

**Example:**

```text
PUT products
{
  "settings": {
    "analysis": {
      "filter": {
        "fr_elision": { "type": "elision", "articles_case": true,
                        "articles": ["l","m","t","qu","n","s","j","d","c","jusqu","quoiqu","lorsqu","puisqu"] },
        "fr_stop":    { "type": "stop", "stopwords": "_french_" },
        "fr_stemmer": { "type": "stemmer", "language": "light_french" }
      },
      "analyzer": {
        "fr_text": {
          "tokenizer": "standard",
          "char_filter": ["html_strip"],
          "filter": ["fr_elision", "lowercase", "fr_stop", "asciifolding", "fr_stemmer"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": { "type": "text", "analyzer": "fr_text",
                 "fields": { "raw": { "type": "keyword" } } }
    }
  }
}
```

#### Q9. How many shards should an index have? {#shard-sizing-oversharding}
**Answer:** Elastic's general guidance is to aim for shards between about **10 GB and 50 GB**, and below about 200M documents per shard. Each shard has fixed costs in heap, file handles and cluster state, and a search runs one task per shard. A thousand tiny shards is therefore slower than ten healthy ones. Oversharding usually comes from daily indices with low volume, so prefer rollover on size. Undersharding limits write parallelism and makes recovery slow. Measure with a realistic load test, then let **ILM rollover** with `max_primary_shard_size` keep the size stable instead of guessing a count up front. Complementary rules: node roles `master` (at least 3 eligible for quorum), `data` (`data_hot`/`data_warm`/`data_cold` for logs), `ingest`, `coordinating`; JVM heap ≤ 50% of RAM (the rest serves the OS file cache, crucial for Lucene) and under ~31 GB to keep compressed oops. Cluster states: `green` (everything allocated), `yellow` (a replica unassigned, e.g. a single-node cluster with `number_of_replicas: 1`: not an outage), `red` (a primary unassigned, data unavailable); diagnose with `GET _cluster/allocation/explain` ([S1](#red-cluster-unassigned-shards)).

#### Q10. How do you paginate deep into results? {#deep-pagination-search-after-pit}
**Answer:** `from`/`size` makes every shard build `from + size` results and the coordinating node merge them, so the cost grows with depth. The default `index.max_result_window` stops at 10,000. Raising it only moves the problem. For deep or full traversal use **`search_after`** with a **point in time** (PIT): the PIT pins a consistent view of the index, and each page passes the `sort` values of the last hit. Sort on a unique tiebreaker, otherwise documents with equal values can be skipped; `_shard_doc` comes free with a PIT. `scroll` still works but is no longer recommended for deep pagination. For users, `from`/`size` up to a few pages is fine, and nobody reads page 900. Lab: [S16](#lab-search-template-pagination). Full example: open the PIT with `POST products/_pit?keep_alive=2m` (response `{ "id": "46ToAwMDaWR..." }`), then `GET _search { "size": 1000, "pit": { "id": "46ToAwMDaWR...", "keep_alive": "2m" }, "sort": [ { "updated_at": "asc" }, { "_shard_doc": "asc" } ], "search_after": [ 1730700000000, 4294967298 ] }`. Close the PIT (`DELETE _pit`) when done: it retains segments that could otherwise have been merged. Same logic as in SQL: see [REST Q3 offset vs keyset](rest-api.md#offset-keyset-cursor-pagination).

#### Q11. `object`, `nested` or `join`: how do you model relationships? {#nested-object-join}
**Answer:** An array of `object` is **flattened**: `[{color: red, size: S}, {color: blue, size: L}]` becomes `color: [red, blue]`, `size: [S, L]`. The link between values is lost, so `red AND L` wrongly matches. **`nested`** indexes each item as a hidden document and keeps the link, but it needs `nested` queries, and updating one item reindexes the whole parent. **`join`** keeps parent and child as separate documents on the same shard, so children update cheaply, but queries are much slower. Default to **denormalizing**. Use `nested` for small, bounded arrays that are queried together, and use `join` only when children change far more often than parents.

**Example:**

```text
# One product: red/S and blue/L. Is there a "red in L"?
object field: bool filter on color=red and size=L   -> 1 hit (wrong)
nested field: nested query with the same filters    -> 0 hits (correct)
```

#### Q12. How do you index efficiently: Bulk API, batch size, partial errors? {#bulk-api-partial-errors}
**Answer:** Always index with **`_bulk`**: batches of **5 to 15 MB** (or a few thousand documents) to be measured, with a few requests in parallel. A bulk response is **200 even if documents failed**: read `errors` and every item, and do not confuse a transport error (exception) with per-document errors. `429` (`es_rejected_execution_exception`) = the write queue is full: exponential backoff, no immediate retry loop; `400` = invalid document, send it to a DLQ. Supplying a **business ID** (`sku`) makes indexing **idempotent**: replaying a batch overwrites instead of duplicating. For large volumes, the client's `BulkIngester` handles batch size, concurrency and periodic flush. See also [S5](#bulk-rejections-partial-failure).

**Example:**

```java
// Java API Client (co.elastic.clients:elasticsearch-java), ES 8.x/9.x
BulkRequest.Builder br = new BulkRequest.Builder();
for (Product p : batch) {
    br.operations(op -> op.index(idx -> idx.index("products").id(p.sku()).document(p)));
}
BulkResponse result = client.bulk(br.build());
if (result.errors()) {
    for (BulkResponseItem item : result.items()) {
        if (item.error() != null) {
            int status = item.status();             // 429 = overload → retry; 400 = invalid document → DLQ
            log.warn("Failed {}: {} ({})", item.id(), item.error().reason(), status);
        }
    }
}

// Large volume: BulkIngester
try (BulkIngester<Void> ingester = BulkIngester.of(b -> b
        .client(client)
        .maxOperations(5_000)
        .maxSize(10 * 1024 * 1024)
        .maxConcurrentRequests(2)
        .flushInterval(5, TimeUnit.SECONDS))) {
    products.forEach(p ->
        ingester.add(op -> op.index(i -> i.index("products").id(p.sku()).document(p))));
}   // close() sends the last batch
```

#### Q13. How do you change a mapping with zero downtime? {#reindex-zero-downtime-alias}
**Answer:** You can add fields, but you cannot change the type or analyzer of an existing field: `mapper [created] cannot be changed from type [date] to [keyword]`. So create a new index and copy the data. Applications must always use an **alias**, never the concrete index. The steps: create `sales-v2`, run `_reindex` with `wait_for_completion=false`, track the task until it is finished, catch up on writes made in the meantime, then swap the alias in **one atomic** `_aliases` call. Keep `sales-v1` until the new index is validated, because rollback is another alias swap. The catch-up is the hard part: dual-write during the migration, or replay from the source of truth ([Q20](#sync-index-with-database)). Catch-up details: write to both indices (dual write), replay changes from a timestamp (`updated_at > start`) after the switch, or replay from Kafka (known start offset). An alias pointing at several indices accepts writes only if `is_write_index` is set. **Index templates** (`_index_template`) apply mapping and settings to any index matching a pattern (`logs-*`), and **ILM** manages the lifecycle (rollover at 50 GB or 1 day, warm/cold, deletion): essential for time-based data ([Q22](#hot-warm-cold-ilm)).

**Example:**

```text
POST _aliases
{ "actions": [
  { "remove": { "index": "sales-v1", "alias": "sales" } },
  { "add":    { "index": "sales-v2", "alias": "sales" } } ] }
```

#### Q14. How do you build faceted navigation (aggregations)? {#faceted-navigation-aggregations}
**Answer:** Facets are **aggregations** computed over the documents matching the query: `terms` (brands, categories), `range` (price bands), `date_histogram`, `stats`/`avg`, nested as needed. They read **doc values**, so `keyword`/numeric fields. The tricky part is **multi-select**: when the user ticks "Decathlon", the Brand facet must still show the other brands. So facet filters go in `post_filter` (applied to the hits, not to the aggregations) and each aggregation applies the filters of the **other** facets. Traps: `terms` counts are approximate across shards ([Q15](#terms-aggregation-accuracy)); aggregating on a high-cardinality field (user ID) is expensive, use `cardinality` to count and `composite` to page through everything; aggregating on `nested` fields requires a `nested` aggregation (and `reverse_nested` to go back to the parent). Think about the JSON response you would return to the front end.

**Example:**

```text
GET products/_search
{
  "query": { "match": { "title": "bike" } },
  "post_filter": { "bool": { "filter": [
      { "terms": { "brand": ["decathlon"] } },
      { "terms": { "color": ["red"] } } ] } },
  "aggs": {
    "brand": {
      "filter": { "terms": { "color": ["red"] } },
      "aggs": { "values": { "terms": { "field": "brand", "size": 20 } } }
    },
    "color": {
      "filter": { "terms": { "brand": ["decathlon"] } },
      "aggs": { "values": { "terms": { "field": "color", "size": 20 } } }
    },
    "price": { "range": { "field": "price",
      "ranges": [ { "to": 300 }, { "from": 300, "to": 1000 }, { "from": 1000 } ] } }
  },
  "size": 24
}
```

#### Q15. Why are `terms` aggregation counts sometimes wrong? {#terms-aggregation-accuracy}
**Answer:** Each shard returns its local top terms, and the coordinating node merges them. A term that is just outside the top list on several shards can be missed, or undercounted, even if it is in the global top. The response reports this in `doc_count_error_upper_bound`. Raising `shard_size` improves accuracy at a memory cost. To list **every** bucket, use a `composite` aggregation and page with `after`, not a huge `size`. Likewise, `cardinality` is approximate (HyperLogLog++, tunable with `precision_threshold`), and `percentiles` is an estimate. An aggregation on a high-cardinality field also costs heap ([S3](#circuit-breaker-data-too-large)).

#### Q16. How do you implement autocomplete? {#autocomplete-search-as-you-type}
**Answer:** Three approaches, from simplest to most specialized. `search_as_you_type`: a field type that creates shingle and edge n-gram subfields, queried with `multi_match` `bool_prefix`; simple, handles word order and the middle of the title, but the index grows. **Edge n-gram analyzer** at index time (`bike` → `b`, `bi`, `bik`, `bike`) with the standard analyzer as `search_analyzer`: full control, normal filters and scoring, but a much bigger index and `min_gram`/`max_gram` to tune. **Completion suggester**: in-memory FST structure, strict prefix only, very fast, few filters (contexts only), separate data. Traps: forgetting `search_analyzer` with an edge n-gram (the query itself gets split into n-grams and everything matches); on the front end, **debounce** (~150 ms), cancel the previous request, limit to 5–10 suggestions, no query under 2 characters; suggest **popular queries** (index of past searches) rather than only product titles. At-scale version: [System design Q39 typeahead](system-design.md#design-typeahead-search-autocomplete-search).

**Example:**

```text
GET products/_search
{
  "size": 8,
  "_source": ["title"],
  "query": { "multi_match": {
      "query": "bik ele",
      "type": "bool_prefix",
      "fields": ["title.suggest", "title.suggest._2gram", "title.suggest._3gram"] } }
}
```

#### Q17. Typos, synonyms, plurals: how do you make search tolerant? {#fuzziness-synonyms-typo-tolerance}
**Answer:** **Typos:** `fuzziness: "AUTO"` (Levenshtein distance: 0 for 1–2 characters, 1 for 3–5, 2 beyond) with `prefix_length: 1` (the first letter is rarely wrong, and the cost drops sharply); offer a "Did you mean" with the `phrase` suggester. **Plurals and conjugations:** the stemmer ([Q8](#french-analysis-elision-stemming)). **Synonyms:** a `synonym_graph` filter **at query time** (`search_analyzer`), not at index time: you can change the list without reindexing (`reload_search_analyzers`, or the Synonyms API in 8.10+). Traps: fuzziness on a stemmed field or on codes/references gives absurd results, reserve it for text fields and disable it for SKUs; multi-word synonyms at index time with `synonym` (non-graph) give wrong positions and break phrase queries; `=>` (one-way rewrite) vs `,` (equivalence) is a business decision.

**Example:**

```text
"filter": {
  "fr_synonyms": { "type": "synonym_graph", "updateable": true,
                   "synonyms": [ "mtb, mountain bike", "tv, television, telly", "laptop pc => laptop computer" ] }
}
```

#### Q18. How do you highlight results and handle search in long documents? {#highlighting-long-documents}
**Answer:** `highlight` returns snippets with the matched terms wrapped in tags. The **unified highlighter** (default) is usually enough; for very large documents, storing offsets (`"index_options": "offsets"` or `term_vector: with_positions_offsets`) speeds up highlighting. Traps: the highlighted content comes from `_source`, so **escape the original HTML** (`"encoder": "html"`) to avoid XSS; for documents of several MB (PDFs extracted by Tika, see [Q29](#tika-text-extraction)), limit `index.highlight.max_analyzed_offset`, or split into passages (one document per page or section) to get relevant snippets.

**Example:**

```text
"highlight": {
  "pre_tags": ["<mark>"], "post_tags": ["</mark>"],
  "fields": { "content": { "fragment_size": 150, "number_of_fragments": 3 } }
}
```

#### Q19. How do you call Elasticsearch from Spring Boot: Java API Client or Spring Data Elasticsearch? {#spring-boot-java-client-vs-spring-data}
**Answer:** The **High Level REST Client** has been deprecated since 7.15; the official client is the **Java API Client** (typed, generated from the spec, lambda builders). **Spring Data Elasticsearch** (5.x) builds on it and provides repositories, annotation-based mapping and `ElasticsearchOperations`. The right tool: Spring Data repositories for CRUD, simple queries and prototyping; the Java API Client directly for real search queries (complex bool, facets, `function_score`, `search_after`), where you want to see and control the query sent; mapping managed outside annotations (versioned JSON file, applied at deployment), because it is the index contract. Traps: Spring Data derived methods generate queries you do not see, enable the client's `tracer` log or `org.springframework.data.elasticsearch.client.WIRE` to read them; in integration tests, use **Testcontainers** with the same Elasticsearch image version as production (see [Testing Q8](testing.md#h2-repository-tests)).

**Example:**

```java
@Document(indexName = "products", createIndex = false)   // mapping managed separately, versioned
public record Product(@Id String sku, String title, String brand, BigDecimal price, boolean inStock) {}

public interface ProductRepository extends ElasticsearchRepository<Product, String> {
    List<Product> findByBrandAndInStockTrue(String brand);
}

@Service
class ProductSearch {
    private final ElasticsearchClient es;
    ProductSearch(ElasticsearchClient es) { this.es = es; }

    List<Product> search(String text, String brand) throws IOException {
        SearchResponse<Product> r = es.search(s -> s
            .index("products")
            .query(q -> q.bool(b -> b
                .must(m -> m.multiMatch(mm -> mm.query(text).fields("title^3", "description")))
                .filter(f -> f.term(t -> t.field("brand").value(brand)))))
            .size(20), Product.class);
        return r.hits().hits().stream().map(Hit::source).toList();
    }
}
```

## 🔴 Expert / Open

#### Q20. How do you keep a search index in sync with the database? {#sync-index-with-database}
**Answer:** Treat the index as a **derived, rebuildable** read model and the database as the source of truth. A dual write from the application is the trap: if the second write fails the stores diverge, and there is no transaction across them. Use the **transactional outbox** or **CDC** (Debezium reads the WAL into Kafka), then a consumer indexes in batches with `_bulk`. Events can arrive out of order, so pass the row version with `version_type=external`: Elasticsearch rejects anything older with a `409`, which the consumer treats as success. Also keep a full rebuild path (reindex from the database into a new index, then swap the alias), because you will need it for mapping changes and for repairing drift.

**Example:**

```text
PUT orders/_doc/42?version=17&version_type=external   # 201
PUT orders/_doc/42?version=12&version_type=external   # 409: current version [17] is higher
```

#### Q21. Beats, Logstash, ingest pipelines, Elastic Agent: who does what? {#elastic-stack-beats-logstash-ingest}
**Answer:** **Beats** (Filebeat, Metricbeat…): lightweight agents that **collect** (log files, metrics) and ship. **Elastic Agent** + Fleet: a unified agent that is gradually replacing Beats, centrally managed. **Logstash**: a JVM `input → filter → output` pipeline for **heavy transformations** (grok, enrichment, several outputs, varied sources such as JDBC or Kafka), with a persistent queue. **Ingest pipelines**: transformations **inside the Elasticsearch node** (`grok`, `date`, `rename`, `geoip`, `enrich`, `script`), with no extra component. The right tool: simple transformation → ingest pipeline; multiple sources, complex enrichment, need for a buffer → Logstash (or Kafka in front); do not add Logstash "by default". **Kibana:** Discover (exploration), dashboards, Lens, Dev Tools (console), alerts. **X-Pack (Elastic license):** *Security* (TLS, authentication, roles with **document- and field-level security**, API keys for applications, enabled by default since 8.0); *Machine Learning* (anomaly detection on time series, NLP model inference such as embeddings); *Graph* (exploring relations between frequently associated terms: fraud, recommendations).

**Example:**

```text
# Logstash: application logs from Kafka to ES
input  { kafka { bootstrap_servers => "kafka:9092" topics => ["app-logs"] codec => json } }
filter {
  date { match => ["timestamp", "ISO8601"] }
  mutate { remove_field => ["password", "authorization"] }
}
output { elasticsearch { hosts => ["https://es:9200"] index => "logs-app-%{+YYYY.MM.dd}" } }
```

#### Q22. How do you run a hot/warm/cold architecture for logs? {#hot-warm-cold-ilm}
**Answer:** Time-series data loses value as it ages, so match the hardware to the age. **Hot** nodes have fast SSDs and take writes. **Warm** nodes hold read-only data on cheaper disks. **Cold** and **frozen** tiers use searchable snapshots, so the data sits in object storage: cold keeps a full local copy without replicas, and frozen keeps only a small cache and fetches on demand. **ILM** moves indices through the phases: rollover on size or age in hot, force merge in warm, searchable snapshot in cold, delete at the end. Use **data streams** for append-only data. In practice the retention period and the query pattern (how often do people search data older than 7 days?) drive the design. Note that `min_age` counts from **rollover**, not from index creation, once a rollover has happened.

#### Q23. How do you improve search relevance? {#relevance-tuning-hybrid}
**Answer:** Start by **measuring**: build a judgment list of real queries with expected results, and track it with the `_rank_eval` API or click data (zero-result rate, click position). Without this, tuning one query breaks ten others. Then go from cheap to expensive: analysis (stemming, synonyms, `asciifolding`), field boosts in `multi_match`, phrase boosts through `should`, and business signals through `function_score`. For meaning rather than words, add vectors (`dense_vector`, kNN search) and combine both result lists with **hybrid search**, usually **reciprocal rank fusion** (RRF), which avoids normalizing BM25 scores against vector scores. Lexical search still wins on part numbers and exact names, which is why hybrid beats pure vector for most e-commerce catalogs. Signal sources: search logs (**zero-result** queries, the best backlog; click-through by position; reformulations; abandonment) and A/B tests in production for major changes. Classic metrics: **precision@k**, **recall**, **MRR**, **nDCG**, via `_rank_eval` or Quepid; every tuning change is compared against the baseline. Trap: optimizing a flagship query while degrading all the others, which the judgment set prevents; do not forget **speed** (a more relevant search that is 800 ms slower can lower conversion). Learning to Rank (LTR plugin, or built in from 8.12+) only makes sense with a lot of clicks. See also [Q24](#semantic-vector-hybrid-search) for vectors.

#### Q24. Semantic search and vectors: what changes? {#semantic-vector-hybrid-search}
**Answer:** You compute an **embedding** (vector) per document and per query with a language model; Elasticsearch stores it as `dense_vector` and finds nearest neighbors (**kNN**, approximate HNSW index). This matches "bike to commute to the office" → "city bike" with no word in common. **Hybrid search** combines BM25 and kNN, often fused with **RRF** (Reciprocal Rank Fusion, see [Q23](#relevance-tuning-hybrid)). Traps: vector search is poor on exact references, codes and rare proper nouns, so BM25 stays essential; costs in memory (HNSW lives in RAM, `int8`/`bbq` quantization reduces it) and embedding computation at index time. Expected reasoned stance: first measure a well-tuned BM25, add hybrid where the judgment set shows a gain. See the [AI notes](../notes/ai.md) for vector databases.

**Example:**

```text
GET products/_search
{
  "retriever": { "rrf": { "retrievers": [
      { "standard": { "query": { "match": { "title": "bike to commute to the office" } } } },
      { "knn": { "field": "title_vector", "query_vector": [0.12, -0.03, ...], "k": 50, "num_candidates": 200 } }
  ] } }
}
```

#### Q25. What is split brain, and how does Elasticsearch prevent it? {#split-brain-quorum}
**Answer:** Split brain is two masters accepting conflicting cluster states after a network partition. Since 7.0 the cluster maintains its voting configuration automatically, and an election needs a **majority** of the master-eligible nodes, so the minority side cannot elect a master. The old manual `discovery.zen.minimum_master_nodes` setting is gone. Run **three** dedicated master-eligible nodes in three zones: two nodes cannot survive the loss of either one, and even numbers add no tolerance. `cluster.initial_master_nodes` is used only for the very first bootstrap, and leaving it in place on a cluster that later restarts with wiped data can create a second cluster. Replication is a separate question: writes go to the primary and then to all in-sync replicas.

#### Q26. Elasticsearch or OpenSearch: what differs, and how do you choose? {#elasticsearch-vs-opensearch}
**Answer:** In 2021 Elastic moved away from Apache 2.0, and AWS forked Elasticsearch 7.10.2 as **OpenSearch** (Apache 2.0, now under the Linux Foundation). Elastic added AGPLv3 as a licensing option in 2024. Since the fork the APIs have diverged, so do not assume compatibility. Query DSL basics, mappings and `_cat` are close, but operations differ: **ISM** instead of ILM, `_plugins/...` paths, a security plugin instead of native X-Pack security, and `knn_vector` instead of `dense_vector`. Recent official Elasticsearch clients refuse to talk to OpenSearch, so use `opensearch-java` or `opensearch-py`. Choose on constraints: Elastic for the newest search features, the Elastic Stack and the Elastic Cloud offer; OpenSearch for a permissive license or AWS OpenSearch Service. Run a proof of concept on your real queries instead of comparing feature lists. The [notes](../notes/elasticsearch-opensearch.md#elasticsearch-vs-opensearch-api-differences) have a command-level table.

#### Q27. Elasticsearch, OpenSearch, Solr, Algolia, Postgres full-text: how do you choose? {#search-tool-choice-es-solr-algolia-postgres}
**Answer:** All of them (except Postgres and Algolia) are built on Lucene; the difference is operations, ecosystem, license and cost. **Elasticsearch:** rich JSON API, aggregations, Stack (Kibana, Beats, Logstash), vector search, observability; limits: license (Elastic License/SSPL, AGPL added in 2024), cost of paid features, running a cluster. **OpenSearch:** Apache 2.0 fork of ES 7.10 run by AWS; the API has diverged since 2021; for a license constraint or an AWS environment ([Q26](#elasticsearch-vs-opensearch)). **Solr:** mature, Apache 2.0, highly configurable (SolrCloud), but a less dynamic ecosystem and heavier configuration; for an existing Solr estate. **Algolia:** SaaS, very low latency, ready-made search UX, but usage-based cost, little control, data at a third party; e-commerce, small team, time-to-market. **Exalead** (Dassault): enterprise search with connectors, proprietary, niche. **Postgres full-text:** already there, transactional, zero infrastructure, but limited relevance and facets, no advanced autocomplete; simple search over data already in the database. **Embedded Lucene:** Java library, no server, but everything is yours to build (distribution, API). Trap: answering "Elasticsearch" to everything. Start from the need (volume, latency, team, budget, sovereign hosting, license) and say what you **lose** with each option. A sentence to have ready: "The database stays the source of truth; the search index is a derived, rebuildable copy, fed by batch or by events" ([Q20](#sync-index-with-database)).

#### Q28. How does a crawler work, and how do you choose between Nutch, crawler4j, Scrapy or StormCrawler? {#crawler-nutch-scrapy-stormcrawler}
**Answer:** A crawler manages a **frontier** (queue of URLs to visit), downloads, **parses** (links + content), **deduplicates**, then re-injects the new links. It must be **polite**: respect `robots.txt` and `Crawl-delay`, limit requests per host, identify itself with a clear User-Agent. Choices: **Apache Nutch** (Java, batch on Hadoop: generate → fetch → parse → updatedb → index) for large web crawls into Solr/ES; **crawler4j** (Java, embedded multi-threaded library) for a small to medium crawl inside an application; **StormCrawler** (Java, Apache Storm streaming) for continuous large-scale recrawl; **Scrapy** (Python, async framework, one spider per site) for structured site-by-site extraction (prices, product pages). Points to cite: **incremental recrawl** (`If-Modified-Since` / `ETag`, 304 = nothing to redo; sitemap `lastmod`; adaptive frequency based on how fast a page changes); **deduplication** (canonical URL via `<link rel="canonical">` and parameter normalization, content fingerprint: exact hash or SimHash for near-duplicates); **crawl traps** (infinite calendars, session IDs in URLs, combinatorial facets: limit depth and pages per host); JavaScript-rendered pages: headless browser (Playwright), far more expensive, reserve it for sites that require it. Do not ignore the legal side: terms of use, GDPR for personal data, database rights. Mentioning it in an interview shows maturity.

#### Q29. How do you extract text from documents (PDF, Office, HTML) with Apache Tika? {#tika-text-extraction}
**Answer:** Tika **detects the type** (from the bytes, not the extension) and delegates to the right parser (PDFBox, POI, etc.) to output the **text** and **metadata** (author, dates, language). Usable as a Java library or as a server (`tika-server`, recommended to isolate crashes and memory leaks of some parsers). Traps: malicious or corrupted files, so a **timeout** and memory limit per document, in a separate process (`tika-server` or `ForkParser`), because a booby-trapped PDF must not kill the whole batch; scanned PDFs: no text, you need OCR (Tesseract via Tika), slow, on a dedicated queue; encodings: Tika detects them, but check accents on a French sample; on the Elasticsearch side, the **`attachment` ingest processor** (Tika embedded in the ingest node) is handy for a prototype but loads the cluster: for volume, extract in the application. For snippet rendering, see [Q18](#highlighting-long-documents).

**Example:**

```java
AutoDetectParser parser = new AutoDetectParser();
BodyContentHandler handler = new BodyContentHandler(10_000_000);   // bound: -1 = unlimited, dangerous
Metadata metadata = new Metadata();
try (InputStream in = Files.newInputStream(path)) {
    parser.parse(in, handler, metadata, new ParseContext());
}
String text = handler.toString();
String title = metadata.get(TikaCoreProperties.TITLE);
```

## 🎯 Real-world scenarios

### S1. The cluster turns red after a node is lost {#red-cluster-unassigned-shards}
- **Symptoms:** `_cluster/health` is `red`; searches return partial results with `_shards.failed > 0`; writes to some indices fail. A node was replaced an hour ago.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Red means at least one **primary** is unassigned. `_cat/shards?h=index,shard,prirep,state,unassigned.reason` finds it, and `_cluster/allocation/explain` gives the exact decider: a node left with no replica, a `filter` rule that no node matches, a disk watermark, or too many failed attempts.
- **Resolution:** Bring the node back if its data still exists; the shard recovers on its own. Fix the cause the decider reports, then run `POST _cluster/reroute?retry_failed=true`. If the data is lost, **restore that index from a snapshot**. `allocate_stale_primary` and `allocate_empty_primary` are the last resort, because they accept data loss.
- **Prevention:** At least one replica on production indices, allocation awareness across zones, tested snapshots, and an alert on `status != green` lasting more than a few minutes. Set `index.unassigned.node_left.delayed_timeout` for planned restarts.

</details>

### S2. Indexing stops with a `429` and "flood-stage watermark", yet searches still work {#disk-flood-stage-read-only}
- **Symptoms:** `cluster_block_exception`, `disk usage exceeded flood-stage watermark, index has read-only-allow-delete block`; new shards stay unassigned on some nodes.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Disk watermarks are set at **85% (low)**, **90% (high)** and **95% (flood stage)**. Above low, no new shards go to the node. Above high, shards move away. Above flood stage, every index with a shard on that node becomes read-only. `_cat/allocation?v` shows the disk usage per node. Often a stuck ILM policy or uneven shard sizes are the real cause.
- **Resolution:** Free disk: delete old indices, add nodes or increase the volume. The block is released automatically once usage falls below the high watermark; if needed, clear it with `PUT <index>/_settings {"index.blocks.read_only_allow_delete": null}`. Clearing the block without freeing disk only delays the next outage.
- **Prevention:** Alert at 75% disk, enforce retention through ILM, and alert on ILM errors (`GET */_ilm/explain?only_errors=true`).

</details>

### S3. A new dashboard triggers `circuit_breaking_exception` and nodes start dropping out {#circuit-breaker-data-too-large}
- **Symptoms:** `[parent] Data too large` with HTTP `429`; JVM heap stays above 85% with long GC pauses; nodes leave and rejoin the cluster right after a dashboard launch.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Circuit breakers stop a request before it causes an `OutOfMemoryError`. `_nodes/stats/breaker` shows which breaker trips. `_cat/fielddata?v` reveals `fielddata: true` on a `text` field, which loads every term onto the heap. Otherwise look for a `terms` aggregation with a huge `size`, or nested aggregations whose buckets multiply. `_tasks?detailed` and the slow log find the query.
- **Resolution:** Cancel the task (`POST _tasks/<id>/_cancel`), fix the dashboard, and aggregate on a `keyword` sub-field with doc values. Clear memory with `POST <index>/_cache/clear?fielddata=true`. Do not raise breaker limits: they are the safety net.
- **Prevention:** Keep the heap at no more than half of RAM (and below about 31 GB, to keep compressed pointers), leave the rest to the file system cache, limit `search.max_buckets`, and load test dashboards on real data.

</details>

### S4. Search got slow: p99 at 3 s {#slow-search-p99-investigation}
- **Symptoms:** Search p99 jumped to 3 s while the median is fine; users complain of intermittent slowness. Nothing changed in the code recently.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** First isolate: all queries or only some? Read the search **slow log** (`index.search.slowlog.threshold.query.warn: 1s`) and the **Profile** API (`"profile": true`) on a slow query. Frequent culprits in the query: leading wildcard (`*bike`), `regexp`, `fuzziness` without `prefix_length`, a heavy `script_score` over the whole index, a `terms` aggregation on a very high-cardinality field, deep pagination (`from: 9000`), `size: 10000`. On the cluster side: `GET _nodes/stats` (heap, GC, `search` pool rejections), `_cat/thread_pool/search`, `_cat/shards` (unbalanced or too many shards), disk and file cache (an oversized heap starves the OS cache).
- **Resolution:** Move criteria into `filter`, use n-grams at index time instead of a query-time wildcard, switch to `search_after`, precompute at index time what a script computes, review the shard count, and use `routing` if queries are always per customer.
- **Prevention:** Keep the slow log on permanently, alert on p99 and on `search` pool rejections, and load-test real queries before any mapping or query change.

</details>

### S5. A bulk import reports success, but thousands of documents are missing {#bulk-rejections-partial-failure}
- **Symptoms:** The importer logs show only HTTP `200`, but `_count` is short by 8%. `_cat/thread_pool/write?v&h=node_name,name,active,queue,rejected` shows `rejected` increasing during the import.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** `_bulk` returns `200` even when items fail. The real result is in `errors: true` and in the `status` of each item. Rejected items have status `429` (`es_rejected_execution_exception`), because the write queue is full. Others may be `400` for mapping errors, and those will never succeed on retry.
- **Resolution:** Read each item's status. Retry `429` with exponential backoff, and send permanent failures to a dead-letter store. Reduce concurrency, and size batches at about 5–15 MB. For a one-off load, set `refresh_interval` to `-1` and replicas to `0`, then restore them afterwards.
- **Prevention:** Use the client's bulk helper with retries, compare source and target counts at the end, and alert on `rejected`. Do not raise the queue size, which only hides the overload.

</details>

### S6. Logs stop arriving for one service after its release {#mapping-conflict-field-limit}
- **Symptoms:** Only the logs of `checkout` disappear. The shipper reports `document_parsing_exception`: `failed to parse field [response] of type [date]` or `Limit of total fields [1000] has been exceeded`.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Many teams share one index, and dynamic mapping fixed the type from the first value. The new release sends `response` as an object or a string, so documents are rejected. `GET <index>/_mapping/field/response` and `_field_caps` show the conflict across indices. With the second error, keys generated from data have filled the mapping ([Q7](#mapping-explosion-dynamic)).
- **Resolution:** Fix the producer, or rename the field in an ingest pipeline. A data stream can roll over to a new backing index with a corrected template, and old data stays as it is. Do not raise the field limit as a first move.
- **Prevention:** Declare the fields you depend on in the index template, use a shared schema such as ECS, separate data streams per service, and route failed documents to a dead-letter index through `on_failure` or the failure store.

</details>

### S7. Search shows the old status after an update, but only for some orders {#stale-search-after-db-update}
- **Symptoms:** The database says `SHIPPED`, while search shows `PAID` until the next nightly rebuild. It happens mostly during peaks. No errors in the indexer logs.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** A delay of about one second would be the refresh interval, but this lasts for hours, so an event was reordered or lost. Parallel consumers can index `SHIPPED` and then an older `PAID` event, and the last write wins. Compare `_version` or an `updated_at` field with the database for a broken order. A dual write that fails silently gives the same symptom.
- **Resolution:** Partition events by order id so that each order is processed in sequence, and index with `version_type=external` using the row version ([Q20](#sync-index-with-database)). Repair the drift by re-sending the affected ids.
- **Prevention:** Use the outbox or CDC instead of dual writes, run a periodic count and checksum comparison, and alert on consumer lag.

</details>

## 🏅 Elastic Certified Engineer labs

The exam is hands-on: you complete tasks on a live cluster, with no multiple-choice questions.

| Fact | Detail | Source |
|---|---|---|
| Version | Elasticsearch **9.3** | [Elastic FAQ](https://www.elastic.co/training/certification/faq) |
| Format | Timed, real-world tasks on a live cluster, with a remote proctor | Elastic FAQ |
| Allowed | The Elastic documentation. No Google or Stack Overflow | Elastic FAQ |
| Retake | 14-day wait and a new paid attempt | Elastic FAQ |
| Validity | 2 years | Elastic FAQ |
| Length | About 3 hours and about 10 tasks, partial credit | Candidate reports, mostly on older versions |

These labs are **original exercises in the exam's style, not real exam questions**, which are confidential. They are grouped by the domains of the published objectives: Data Management, Data Processing, Searching Data, Developing Search Applications and Cluster Management. Check the [exam page](https://www.elastic.co/training/elastic-certified-engineer-exam) for the current list before you book. All solutions were run on Elasticsearch 9.3.0. Searchable snapshots and cross-cluster replication need a trial or Enterprise license.

**Exam tactics, from candidate reports:**

- Read every task first, start with the quick ones, and come back to the hard ones.
- Do exactly what the task says, including names. Do not add requirements of your own.
- Verify each answer: `GET <index>/_mapping`, `_cat`, `_simulate`, then a real query.
- Learn the documentation's side navigation before the exam. It is often faster than its search.
- Attempt every task, because partial work can score.

**Practice data for the search labs:**

```text
PUT sales-v1
{ "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
  "mappings": { "properties": {
    "sold_at":     { "type": "date" },
    "sku":         { "type": "text" },
    "category":    { "type": "keyword" },
    "title":       { "type": "text" },
    "description": { "type": "text" },
    "price":       { "type": "double" },
    "quantity":    { "type": "integer" },
    "status":      { "type": "keyword" },
    "brand":       { "type": "keyword" } } } }

POST _bulk?refresh=true
{"index":{"_index":"sales-v1","_id":"1"}}
{"sold_at":"2026-01-10T09:00:00Z","sku":"RUN-001","category":"shoes","title":"Trail running shoes","description":"Light shoes for muddy trails","price":89.9,"quantity":2,"status":"PAID","brand":"north"}
{"index":{"_index":"sales-v1","_id":"2"}}
{"sold_at":"2026-01-20T12:30:00Z","sku":"RUN-002","category":"shoes","title":"Road running shoes","description":"Cushioned shoes for road running","price":120,"quantity":1,"status":"PAID","brand":"swift"}
{"index":{"_index":"sales-v1","_id":"3"}}
{"sold_at":"2026-02-03T18:15:00Z","sku":"JKT-001","category":"jackets","title":"Rain jacket","description":"Waterproof jacket for trail running","price":150,"quantity":1,"status":"PAID","brand":"north"}
{"index":{"_index":"sales-v1","_id":"4"}}
{"sold_at":"2026-02-14T08:45:00Z","sku":"RUN-003","category":"shoes","title":"Kids running shoes","description":"Running shoes for kids","price":45,"quantity":3,"status":"REFUNDED","brand":"swift"}
{"index":{"_index":"sales-v1","_id":"5"}}
{"sold_at":"2026-02-20T21:05:00Z","sku":"SCK-001","category":"socks","title":"Wool running socks","description":"Warm socks","price":15,"quantity":6,"status":"PAID"}
```

### Data Management

#### S8. Lab: index template with dynamic templates {#lab-index-dynamic-template}
- **Task:** Any new index matching `shop-orders-*` must have 1 shard and 0 replicas. `created_at` is a `date`. New strings become `keyword`, except fields ending in `_text`, which are `text` with the `english` analyzer. New integers ending in `_count` become `integer`.

<details markdown="1">
<summary>Show solution</summary>

```text
PUT _index_template/shop-orders
{
  "index_patterns": ["shop-orders-*"],
  "priority": 200,
  "template": {
    "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
    "mappings": {
      "dynamic_templates": [
        { "text_fields": {
            "match_mapping_type": "string", "match": "*_text",
            "mapping": { "type": "text", "analyzer": "english" } } },
        { "strings_as_keywords": {
            "match_mapping_type": "string",
            "mapping": { "type": "keyword", "ignore_above": 256 } } },
        { "counts": {
            "match_mapping_type": "long", "match": "*_count",
            "mapping": { "type": "integer" } } }
      ],
      "properties": { "created_at": { "type": "date" } }
    }
  }
}

# Verify
POST _index_template/_simulate_index/shop-orders-2026
POST shop-orders-2026/_doc?refresh=true
{ "created_at": "2026-01-15", "status": "PAID", "review_text": "Great running shoes", "item_count": 3 }
GET shop-orders-2026/_mapping
```

- **Trap:** The first matching dynamic template wins, so `*_text` must come before the catch-all string rule.
- **Trap:** A template only applies to **new** indices. JSON integers arrive as `long`, so match on `long`.

</details>

#### S9. Lab: data stream with an ILM policy {#lab-data-stream-ilm}
- **Task:** Create the data stream `app-events`. Roll over at 1 day or when a primary shard reaches 50 GB. After 7 days, force merge to one segment and shrink to one shard. Delete after 30 days.

<details markdown="1">
<summary>Show solution</summary>

```text
PUT _ilm/policy/app-events-policy
{ "policy": { "phases": {
  "hot":    { "actions": { "rollover": { "max_age": "1d", "max_primary_shard_size": "50gb" } } },
  "warm":   { "min_age": "7d", "actions": {
              "forcemerge": { "max_num_segments": 1 },
              "shrink": { "number_of_shards": 1 } } },
  "delete": { "min_age": "30d", "actions": { "delete": {} } } } } }

PUT _index_template/app-events
{
  "index_patterns": ["app-events*"],
  "data_stream": {},
  "priority": 200,
  "template": {
    "settings": { "index.lifecycle.name": "app-events-policy", "number_of_replicas": 0 },
    "mappings": { "properties": {
      "@timestamp": { "type": "date" },
      "service":    { "type": "keyword" },
      "message":    { "type": "text" } } }
  }
}

# The first document creates the data stream
POST app-events/_doc
{ "@timestamp": "2026-11-06T10:00:00Z", "service": "checkout", "message": "payment accepted" }

# Verify
GET _data_stream/app-events
GET app-events/_ilm/explain
POST app-events/_rollover
```

- **Trap:** Data streams are append-only: `PUT app-events/_doc/1` fails with `only write ops with an op_type of create are allowed`. Use `POST`, or `_create`.
- **Trap:** Avoid patterns such as `logs-*-*` in practice: they collide with built-in templates at priority 100, so yours needs a higher priority.

</details>

### Data Processing

#### S10. Lab: custom analyzer and multi-fields {#lab-custom-analyzer-multifields}
- **Task:** Create `products` with a `title` field that strips HTML, maps `&` to `and`, and ignores case and accents. At search time `sneakers` must find `trainers`, and `tv` must find `television`. Add `title.raw` for exact matches and sorting, and `title.autocomplete` for prefix search as you type.

<details markdown="1">
<summary>Show solution</summary>

```text
PUT products
{
  "settings": {
    "number_of_shards": 1, "number_of_replicas": 0,
    "analysis": {
      "char_filter": { "amp_to_and": { "type": "mapping", "mappings": ["& => and"] } },
      "filter": {
        "shop_synonyms": { "type": "synonym_graph", "synonyms": ["sneakers, trainers", "tv, television"] },
        "autocomplete_edge": { "type": "edge_ngram", "min_gram": 2, "max_gram": 15 }
      },
      "analyzer": {
        "shop_search": {
          "type": "custom", "char_filter": ["html_strip", "amp_to_and"],
          "tokenizer": "standard", "filter": ["lowercase", "asciifolding"] },
        "shop_search_syn": {
          "type": "custom", "char_filter": ["html_strip", "amp_to_and"],
          "tokenizer": "standard", "filter": ["lowercase", "asciifolding", "shop_synonyms"] },
        "autocomplete_index": {
          "type": "custom", "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding", "autocomplete_edge"] }
      }
    }
  },
  "mappings": { "properties": { "title": {
    "type": "text", "analyzer": "shop_search", "search_analyzer": "shop_search_syn",
    "fields": {
      "raw": { "type": "keyword" },
      "autocomplete": { "type": "text", "analyzer": "autocomplete_index", "search_analyzer": "shop_search" }
    } } } }
}

# Verify
POST products/_analyze
{ "analyzer": "shop_search", "text": "<b>Café</b> & Thé" }    # cafe, and, the
POST products/_doc/1?refresh=true
{ "title": "Blue Trainers" }
GET products/_search
{ "query": { "match": { "title": "sneakers" } } }
GET products/_search
{ "query": { "match": { "title.autocomplete": "trai" } } }
```

- **Trap:** `synonym_graph` belongs in the **search** analyzer only.
- **Trap:** `edge_ngram` goes in the index analyzer only. If it also runs at search time, `trai` matches anything that starts with `tr`.

</details>

#### S11. Lab: ingest pipeline with Painless {#lab-ingest-pipeline-painless}
- **Task:** Create `orders-enrich`. Lowercase `customer_email`, split the comma-separated `tags` and trim them, convert `quantity` and `unit_price` to numbers, compute `total` rounded to 2 decimals, set `size_class` to `big` when the total is at least 100, otherwise `small`, remove `debug`, and add `ingested_at`. Send failures to `failed-orders` with the error message. Apply the pipeline by default to `shop-orders-v1`.

<details markdown="1">
<summary>Show solution</summary>

```text
PUT _ingest/pipeline/orders-enrich
{
  "description": "Normalize orders",
  "processors": [
    { "lowercase": { "field": "customer_email" } },
    { "split":     { "field": "tags", "separator": "," } },
    { "trim":      { "field": "tags" } },
    { "convert":   { "field": "quantity", "type": "integer" } },
    { "convert":   { "field": "unit_price", "type": "double" } },
    { "script": {
        "lang": "painless",
        "source": "ctx.total = Math.round(ctx.quantity * ctx.unit_price * 100) / 100.0; ctx.size_class = ctx.total >= params.big ? 'big' : 'small';",
        "params": { "big": 100 } } },
    { "remove": { "field": "debug", "ignore_missing": true } },
    { "set":    { "field": "ingested_at", "value": "{{{_ingest.timestamp}}}" } }
  ],
  "on_failure": [
    { "set": { "field": "_index", "value": "failed-orders" } },
    { "set": { "field": "error", "value": "{{{_ingest.on_failure_message}}}" } }
  ]
}

# Verify before touching any index
POST _ingest/pipeline/orders-enrich/_simulate
{ "docs": [
  { "_source": { "customer_email": "Ann@Example.COM", "tags": "sale, new", "quantity": "3", "unit_price": "39.90", "debug": "x" } },
  { "_source": { "customer_email": "b@x.io", "tags": "a", "quantity": "oops", "unit_price": "1" } } ] }

PUT shop-orders-v1
{ "settings": { "number_of_shards": 1, "number_of_replicas": 0, "index.default_pipeline": "orders-enrich" } }
```

- **Check:** The first document gives `total: 119.7` and `size_class: big`. The second goes to `failed-orders`.
- **Trap:** In an ingest script, fields are read with `ctx.field`. `doc['field']` works in search and runtime scripts instead.

</details>

#### S12. Lab: `_update_by_query`, `_reindex` and an alias {#lab-reindex-update-by-query}
- **Task:** In `sales-v1`, set `brand` to `unknown` wherever it is missing. Then `sku` must become a `keyword`: copy only `PAID` documents to `sales-v2`, add `revenue` (price × quantity), and make the alias `sales` point to `sales-v2`.

<details markdown="1">
<summary>Show solution</summary>

```text
POST sales-v1/_update_by_query?conflicts=proceed&refresh=true
{
  "query": { "bool": { "must_not": { "exists": { "field": "brand" } } } },
  "script": { "lang": "painless", "source": "ctx._source.brand = params.brand", "params": { "brand": "unknown" } }
}

PUT sales-v2
{ "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
  "mappings": { "properties": {
    "sold_at": { "type": "date" }, "sku": { "type": "keyword" }, "category": { "type": "keyword" },
    "title": { "type": "text" }, "description": { "type": "text" }, "price": { "type": "double" },
    "quantity": { "type": "integer" }, "status": { "type": "keyword" }, "brand": { "type": "keyword" },
    "revenue": { "type": "double" } } } }

POST _reindex?refresh=true
{
  "source": { "index": "sales-v1", "query": { "term": { "status": "PAID" } } },
  "dest":   { "index": "sales-v2" },
  "script": { "lang": "painless", "source": "ctx._source.revenue = ctx._source.price * ctx._source.quantity" }
}

POST _aliases
{ "actions": [ { "add": { "index": "sales-v2", "alias": "sales", "is_write_index": true } } ] }

# Verify: 4 documents, and JKT-001 has revenue 150
GET sales/_count
GET sales/_search
{ "query": { "term": { "sku": "JKT-001" } } }
```

- **Trap:** Create the destination index **first**, or `_reindex` builds it with dynamic mappings.
- **Trap:** With `wait_for_completion=false`, the destination may not exist yet when the call returns. Wait for the task before you swap an alias.

</details>

### Searching Data

#### S13. Lab: `bool` query with sub-aggregations {#lab-bool-query-aggregations}
- **Task:** On `sales-v1`, find documents with both `running` and `shoes` across `title` (boost 3) and `description`. Keep only `PAID` sales in January and February 2026, and exclude `socks`. Rank the phrase `trail running` higher. In the same request, return the top 3 categories per month with the average price of each.

<details markdown="1">
<summary>Show solution</summary>

```text
GET sales-v1/_search
{
  "size": 3,
  "query": { "bool": {
    "must": [ { "multi_match": {
      "query": "running shoes", "fields": ["title^3", "description"], "operator": "and" } } ],
    "filter": [
      { "term":  { "status": "PAID" } },
      { "range": { "sold_at": { "gte": "2026-01-01", "lt": "2026-03-01" } } } ],
    "should":   [ { "match_phrase": { "title": "trail running" } } ],
    "must_not": [ { "term": { "category": "socks" } } ]
  } },
  "aggs": { "per_month": {
    "date_histogram": { "field": "sold_at", "calendar_interval": "month" },
    "aggs": { "top_categories": {
      "terms": { "field": "category", "size": 3 },
      "aggs": { "avg_price": { "avg": { "field": "price" } } } } } } }
}
```

- **Check:** Hits are ids `1` then `2`. January has `shoes` with an `avg_price` of `104.95`.
- **Trap:** Aggregations run on the **query's** results. For statistics over all documents, drop the query and use `"size": 0`.

</details>

#### S14. Lab: runtime fields {#lab-runtime-field}
- **Task:** Without reindexing, compute `revenue` and `day_of_week` at query time, return both, and sum revenue by day of the week. Then make `revenue` permanent in the mapping, and find sales of at least 150.

<details markdown="1">
<summary>Show solution</summary>

```text
GET sales-v1/_search
{
  "size": 1,
  "runtime_mappings": {
    "revenue": { "type": "double", "script": { "source": "emit(doc['price'].value * doc['quantity'].value)" } },
    "day_of_week": { "type": "keyword", "script": {
      "source": "emit(doc['sold_at'].value.dayOfWeekEnum.getDisplayName(TextStyle.FULL, Locale.ENGLISH))" } }
  },
  "fields": ["revenue", "day_of_week"],
  "aggs": { "by_day": {
    "terms": { "field": "day_of_week" },
    "aggs": { "revenue": { "sum": { "field": "revenue" } } } } }
}

PUT sales-v1/_mapping
{ "runtime": { "revenue": { "type": "double",
  "script": { "source": "emit(doc['price'].value * doc['quantity'].value)" } } } }

GET sales-v1/_search
{ "query": { "range": { "revenue": { "gte": 150 } } } }
```

- **Trap:** Runtime fields are not in `_source`, so request them through `fields`.
- **Trap:** They use `emit`, not `return`, and they cost CPU at query time. Move them to an indexed field if they become hot.

</details>

#### S15. Lab: async search {#lab-async-search}
- **Task:** Start a search that counts documents by `category`. Return straight away, keep the result for one hour, check its status, fetch the result, then delete it.

<details markdown="1">
<summary>Show solution</summary>

```text
POST sales-v1/_async_search?wait_for_completion_timeout=0ms&keep_on_completion=true&keep_alive=1h
{ "size": 0, "aggs": { "by_category": { "terms": { "field": "category" } } } }

GET _async_search/status/<id>
GET _async_search/<id>
DELETE _async_search/<id>
```

- **Check:** The first response has `is_running: true` and `is_partial: true`. Both become `false` when it completes.
- **Trap:** A search that finishes within the timeout is not stored unless `keep_on_completion=true`.

</details>

### Developing Search Applications

#### S16. Lab: search template, highlighting, sorting and pagination {#lab-search-template-pagination}
- **Task:** Store a search template `product-search` with a required `q` parameter, optional `status` (default `PAID`) and optional `size` (default 10). Highlight matches with `<mark>`, and sort by price, then date, both descending. Separately, walk through all results for `running` two at a time, without `from`.

<details markdown="1">
<summary>Show solution</summary>

```text
PUT _scripts/product-search
{ "script": { "lang": "mustache", "source": {
  "size": "{{size}}{{^size}}10{{/size}}",
  "query": { "bool": {
    "must":   [ { "match": { "title": "{{q}}" } } ],
    "filter": [ { "term": { "status": "{{status}}{{^status}}PAID{{/status}}" } } ] } },
  "highlight": { "pre_tags": ["<mark>"], "post_tags": ["</mark>"], "fields": { "title": {} } },
  "sort": [ { "price": "desc" }, { "sold_at": "desc" } ]
} } }

# Check the rendering, then run it
POST _render/template
{ "id": "product-search", "params": { "q": "running" } }
GET sales-v1/_search/template
{ "id": "product-search", "params": { "q": "running", "size": 2 } }

# Pagination: open a PIT, no index in the search path
POST sales-v1/_pit?keep_alive=2m
GET _search
{ "size": 2, "query": { "match": { "title": "running" } },
  "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "price": "desc" }, { "_shard_doc": "asc" } ] }

# Next page: pass the sort values of the last hit
GET _search
{ "size": 2, "query": { "match": { "title": "running" } },
  "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "price": "desc" }, { "_shard_doc": "asc" } ],
  "search_after": [89.9, 0] }     # copy these from your own last hit

DELETE _pit
{ "id": "<pit_id>" }
```

- **Check:** Page 1 returns ids `2` and `1`, and page 2 returns ids `4` and `5`.
- **Trap:** `{{^size}}…{{/size}}` is a Mustache inverted section: it renders when the value is missing.
- **Trap:** With a PIT, the index goes in the PIT, not in the URL. `GET sales-v1/_search` with a `pit` fails.

</details>

### Cluster Management

#### S17. Lab: repair a red cluster {#lab-repair-cluster-health}
- **Task:** After you run the setup below, the cluster is red. Find out why and return it to green, on a single-node cluster.

<details markdown="1">
<summary>Show solution</summary>

```text
# Setup
PUT broken-1
{ "settings": { "number_of_shards": 1, "number_of_replicas": 1,
  "index.routing.allocation.require.data_zone": "zone-z" } }

# Diagnose
GET _cat/health?v
GET _cat/shards/broken-1?v&h=index,shard,prirep,state,unassigned.reason
GET _cluster/allocation/explain
{ "index": "broken-1", "shard": 0, "primary": true }
# decider "filter": node does not match index setting [index.routing.allocation.require]

# Fix both causes: the bad rule, and a replica that can never be assigned on one node
PUT broken-1/_settings
{ "index.routing.allocation.require.data_zone": null, "index.number_of_replicas": 0 }

# Verify
GET _cluster/health?wait_for_status=green&timeout=5s
```

- **Trap:** Dropping the replica is only right here, because one node cannot host it. On a multi-node cluster, keep it.
- **Trap:** After repeated failures, a shard stops retrying. Fix the cause, then run `POST _cluster/reroute?retry_failed=true`.

</details>

#### S18. Lab: snapshot, restore and searchable snapshots {#lab-snapshot-restore-searchable}
- **Task:** Register an `fs` repository (`path.repo` must include its location). Snapshot only `sales-v1`, and restore it as `restored-sales-v1`. Schedule a daily snapshot with 30-day retention. Then mount the snapshot as `sales-archive` (full copy) and as `sales-frozen` (shared cache).

<details markdown="1">
<summary>Show solution</summary>

```text
PUT _snapshot/lab-repo
{ "type": "fs", "settings": { "location": "/snap/lab" } }
POST _snapshot/lab-repo/_verify

PUT _snapshot/lab-repo/snap-1?wait_for_completion=true
{ "indices": "sales-v1", "include_global_state": false }

POST _snapshot/lab-repo/snap-1/_restore?wait_for_completion=true
{ "indices": "sales-v1", "rename_pattern": "(.+)", "rename_replacement": "restored-$1", "include_aliases": false }

PUT _slm/policy/nightly
{ "schedule": "0 30 1 * * ?", "name": "<nightly-{now/d}>", "repository": "lab-repo",
  "config": { "indices": ["sales-*"], "include_global_state": false },
  "retention": { "expire_after": "30d", "min_count": 5, "max_count": 50 } }
POST _slm/policy/nightly/_execute

POST _snapshot/lab-repo/snap-1/_mount?wait_for_completion=true&storage=full_copy
{ "index": "sales-v1", "renamed_index": "sales-archive", "index_settings": { "index.number_of_replicas": 0 } }

POST _snapshot/lab-repo/snap-1/_mount?wait_for_completion=true&storage=shared_cache
{ "index": "sales-v1", "renamed_index": "sales-frozen" }

# Verify
GET _cat/snapshots/lab-repo?v
GET _cat/indices/sales-*,restored-*?v&h=index,health,docs.count&s=index
```

- **Trap:** You cannot restore over an open index of the same name: rename, or close or delete it first.
- **Trap:** `shared_cache` needs a node with the `data_frozen` role and a shared cache. Mounted indices are read-only: a write returns `403`.
- **ILM version:** `"cold": { "min_age": "30d", "actions": { "searchable_snapshot": { "snapshot_repository": "lab-repo" } } }`. The repository must exist before you create the policy.

</details>

#### S19. Lab: cross-cluster search and replication {#lab-cross-cluster-search-replication}
- **Task:** From `cluster_a`, connect to `cluster_b`. Run one aggregation over local `sales-v1` and remote `sales-eu`. Then replicate `sales-eu` to the local follower `sales-eu-copy`, and add an auto-follow pattern for future `sales-eu-*` indices.

<details markdown="1">
<summary>Show solution</summary>

```text
# On cluster_a
PUT _cluster/settings
{ "persistent": { "cluster": { "remote": { "cluster_b": {
  "mode": "sniff", "seeds": ["es-lab-b:9300"], "skip_unavailable": true } } } } }

GET _remote/info          # expect "connected": true

GET sales-v1,cluster_b:sales-eu/_search
{ "size": 0, "aggs": { "by_category": { "terms": { "field": "category" } } } }

PUT sales-eu-copy/_ccr/follow?wait_for_active_shards=1
{ "remote_cluster": "cluster_b", "leader_index": "sales-eu" }

GET sales-eu-copy/_ccr/stats

PUT _ccr/auto_follow/eu-sales
{ "remote_cluster": "cluster_b", "leader_index_patterns": ["sales-eu-*"],
  "follow_index_pattern": "{{leader_index}}-copy" }

# Promote the follower to a normal index (for example, after losing the leader)
POST sales-eu-copy/_ccr/pause_follow
POST sales-eu-copy/_close
POST sales-eu-copy/_ccr/unfollow
POST sales-eu-copy/_open
```

- **Trap:** Seeds use the **transport** port (9300), not the HTTP port.
- **Trap:** A follower is read-only: a direct write returns `403`. The follow request runs on the **follower** cluster.
- **Trap:** Auto-follow only covers indices created **after** the pattern exists.

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q1. What is an inverted index, and what is a Lucene segment?
2. Q3. What is the difference between `text` and `keyword`, and what does an analyzer do?
3. Q5. Why is search "near real time"? What do `refresh` and `flush` do?
4. Q7. How many shards should an index have?
5. Q8. How do you paginate deep into results?
6. Q9. `object`, `nested` or `join`: how do you model relationships?
7. Q10. How do you change a mapping with zero downtime?
8. Q12. How do you keep a search index in sync with the database?
9. Q16. Elasticsearch or OpenSearch: what differs, and how do you choose?
10. S1. The cluster turns red after a node is lost

## 📌 Cheat-sheet

- **Index** — inverted index for search, doc values for sort and aggregations. *Segments are immutable.*
- **Fields** — `text` is analyzed, `keyword` is exact. *`term` on `text` is the classic bug; use multi-fields.*
- **Queries** — scoring in `must`/`should`, exact conditions in `filter`. *Filters are cached and skip scoring.*
- **Writes** — durable at once, searchable after a refresh. *Avoid `?refresh=true` per write.*
- **Mappings** — types cannot change. *Alias + `_reindex` + atomic swap; `dynamic: strict` on domain indices.*
- **Shards** — about 10–50 GB. *Rollover on size; tiny shards cost more than they save.*
- **Paging** — `search_after` + PIT. *`from + size` stops at 10,000.*
- **Sync** — outbox or CDC with `version_type=external`. *The index is derived and rebuildable.*
- **Health** — red = primary missing, yellow = replica missing. *`_cluster/allocation/explain` first.*
- **Disk** — 85% / 90% / 95% watermarks. *Flood stage makes indices read-only.*
- **Bulk** — HTTP `200` can hide failures. *Check `errors` and each item, retry only `429`.*
- **Exam** — verify every task with `_simulate`, `_mapping`, `_cat`. *Docs are allowed, so know their navigation.*
