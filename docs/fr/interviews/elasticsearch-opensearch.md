# Elasticsearch & OpenSearch

Questions sur les moteurs de recherche : internes de Lucene, mappings et analyse, shards, pertinence, exploitation d'un cluster, et différences entre les deux produits. La place de la recherche dans une architecture est traitée en System Design ([System Design Q10](system-design.md#search-feature-fit-design-just), [System Design R19](system-design.md#patients-search-dermatologist-near-earliest)). La seconde moitié de cette page est une série de labs pratiques pour l'examen Elastic Certified Engineer. Les commandes sont dans les [notes Elasticsearch](../notes/elasticsearch-opensearch.md).

## 🟢 Fondamentaux

#### Q1. Qu'est-ce qu'un index inversé, et qu'est-ce qu'un segment Lucene ? {#inverted-index-lucene-segment}
**Réponse :** Un index inversé associe chaque **terme** à la liste des documents qui le contiennent : une recherche consulte donc des termes au lieu de parcourir les documents. C'est pourquoi `match` sur un mot est rapide alors que `LIKE '%mot%'` sur une base de données ne l'est pas. Lucene écrit l'index sous forme de **segments** immuables. Les nouveaux documents vont dans de nouveaux segments, une suppression ne fait que marquer un document comme supprimé, et une mise à jour est une suppression plus une insertion. Des **merges** en arrière-plan combinent les petits segments et purgent les documents supprimés. L'immuabilité permet des lectures sans verrou et un bon cache, au prix d'une amplification d'écriture. Les agrégations et le tri utilisent une autre structure, les **doc values**, un stockage en colonnes sur disque.

#### Q2. Que sont les nœuds, les shards et les réplicas ? {#nodes-shards-replicas}
**Réponse :** Un **cluster** est un ensemble de nœuds avec un master élu. Les rôles séparent le travail : `master` (état du cluster), `data_hot`/`data_warm`/`data_cold`/`data_frozen` (tiers), `ingest` (pipelines), et les nœuds de coordination seuls. Un index est découpé en **shards primaires**, chacun étant un index Lucene complet. Les **réplicas** sont des copies qui assurent le failover et ajoutent de la capacité de lecture. Le nombre de primaires est fixé à la création, car le routage utilise `hash(_routing) % number_of_primary_shards` ; le changer demande `_split`, `_shrink` ou un reindex. Le nombre de réplicas peut changer à tout moment. Un primaire et son réplica ne sont jamais sur le même nœud : sur un seul nœud, un réplica reste non assigné et l'index est jaune.

#### Q3. Quelle est la différence entre `text` et `keyword`, et que fait un analyzer ? {#text-keyword-analyzer}
**Réponse :** Un champ `text` est **analysé** en termes pour la recherche plein texte. Un champ `keyword` est stocké comme une seule valeur exacte, pour les filtres, le tri et les agrégations. Un analyzer exécute trois étapes : **character filters** (retirer le HTML, remplacer des caractères), un **tokenizer** (découper en tokens) et des **token filters** (minuscules, stemming, synonymes). Le bug classique est une requête `term` sur un champ `text` : `term` n'analyse pas son entrée, donc `"Blue Trainers"` ne correspond jamais aux termes stockés `blue` et `trainers`. Utilisez `match` sur `text`, `term` sur `keyword`, et les **multi-fields** quand il vous faut les deux. Le tri sur `text` échoue, comme le dit l'erreur : `Fielddata is disabled on [title]`.

**Exemple :**

```text
POST products/_analyze
{ "analyzer": "standard", "text": "Blue Trainers!" }   # tokens : blue, trainers
```

#### Q4. Quelle est la différence entre query context et filter context ? {#query-filter-context-bm25}
**Réponse :** Le **query context** répond à « à quel point cela correspond-il ? » et calcule un `_score`. Le **filter context** répond à « est-ce que cela correspond ? », ne calcule aucun score, et ses résultats peuvent être mis en cache. Dans une requête `bool`, `must` et `should` comptent dans le score, alors que `filter` et `must_not` n'y comptent pas. Mettez toute condition exacte (statut, plage de dates, tenant) dans `filter` : c'est plus rapide et cela ne fausse pas la pertinence. Le scoring par défaut est **BM25** : les termes rares pèsent plus (IDF), les termes répétés aident avec des rendements décroissants (saturation du TF), et les champs courts sont mieux classés (normalisation par la longueur). Les scores sont calculés par shard : avec peu de documents, une même requête peut donc classer différemment selon les shards.

#### Q5. Pourquoi la recherche est-elle « near real time » ? Que font `refresh` et `flush` ? {#refresh-flush-translog}
**Réponse :** Un document indexé est d'abord dans un buffer en mémoire et dans le **translog**, un journal durable sur disque. Il n'est pas encore cherchable. Le **refresh** (toutes les secondes par défaut sur les index recherchés) transforme le buffer en un nouveau segment cherchable. Le **flush** exécute un commit Lucene et réduit le translog. Une écriture réussie est donc durable tout de suite, mais visible seulement après le refresh suivant, alors que `GET _doc/<id>` est temps réel. Utiliser `?refresh=true` à chaque écriture crée de minuscules segments et nuit au débit. Si un appelant doit relire sa propre écriture, préférez `?refresh=wait_for`. Pour les chargements en masse, montez `index.refresh_interval` à `30s` ou plus.

## 🟡 Pièges seniors

#### Q6. Qu'est-ce qu'une explosion de mapping, et comment contrôler `dynamic` ? {#mapping-explosion-dynamic}
**Réponse :** Avec le mapping dynamique, chaque nouvelle clé JSON devient un champ dans l'état du cluster. Si les clés sont des données (ids d'utilisateurs, noms de métriques), le mapping grandit sans limite, ralentit chaque mise à jour de l'état du cluster et consomme du heap. À 1 000 champs, la limite par défaut `index.mapping.total_fields.limit` rejette les documents. Options de `dynamic` : `true` ajoute les champs, `false` les garde dans `_source` sans les indexer, `strict` rejette le document, et `runtime` les mappe comme runtime fields. Utilisez `strict` sur les index métier, et modélisez les attributs définis par l'utilisateur avec un champ `flattened` ou une liste clé/valeur `nested`. La détection dynamique est un second piège : la première valeur fixe le type pour toujours, et le type d'un champ ne peut pas changer ensuite.

#### Q7. Combien de shards un index doit-il avoir ? {#shard-sizing-oversharding}
**Réponse :** La recommandation générale d'Elastic est de viser des shards d'environ **10 Go à 50 Go**, et moins d'environ 200 millions de documents par shard. Chaque shard a un coût fixe en heap, en descripteurs de fichiers et en état du cluster, et une recherche exécute une tâche par shard. Mille shards minuscules sont donc plus lents que dix shards sains. L'oversharding vient souvent d'index quotidiens à faible volume : préférez le rollover sur la taille. L'undersharding limite le parallélisme d'écriture et ralentit la récupération. Mesurez avec un test de charge réaliste, puis laissez le **rollover ILM** avec `max_primary_shard_size` stabiliser la taille au lieu de deviner un nombre à l'avance.

#### Q8. Comment paginer loin dans les résultats ? {#deep-pagination-search-after-pit}
**Réponse :** `from`/`size` oblige chaque shard à produire `from + size` résultats et le nœud coordinateur à les fusionner : le coût grandit avec la profondeur. Le réglage par défaut `index.max_result_window` s'arrête à 10 000. L'augmenter ne fait que déplacer le problème. Pour un parcours profond ou complet, utilisez **`search_after`** avec un **point in time** (PIT) : le PIT fige une vue cohérente de l'index, et chaque page passe les valeurs de `sort` du dernier hit. Triez sur un critère unique de départage, sinon des documents de même valeur peuvent être sautés ; `_shard_doc` est fourni avec un PIT. `scroll` fonctionne encore mais n'est plus recommandé pour la pagination profonde. Pour les utilisateurs, `from`/`size` sur quelques pages suffit, et personne ne lit la page 900. Lab : [S15](#lab-search-template-pagination).

#### Q9. `object`, `nested` ou `join` : comment modéliser les relations ? {#nested-object-join}
**Réponse :** Un tableau d'`object` est **aplati** : `[{color: red, size: S}, {color: blue, size: L}]` devient `color: [red, blue]`, `size: [S, L]`. Le lien entre les valeurs est perdu, donc `red AND L` correspond à tort. **`nested`** indexe chaque élément comme un document caché et garde le lien, mais il exige des requêtes `nested`, et modifier un élément réindexe tout le parent. **`join`** garde parent et enfant comme documents séparés sur le même shard : les enfants se mettent à jour à faible coût, mais les requêtes sont bien plus lentes. Par défaut, **dénormalisez**. Utilisez `nested` pour de petits tableaux bornés interrogés ensemble, et `join` uniquement quand les enfants changent bien plus souvent que les parents.

**Exemple :**

```text
# Un produit : red/S et blue/L. Existe-t-il un « red en L » ?
champ object : filtre bool sur color=red et size=L   -> 1 hit (faux)
champ nested : requête nested avec les mêmes filtres -> 0 hit (correct)
```

#### Q10. Comment changer un mapping sans interruption ? {#reindex-zero-downtime-alias}
**Réponse :** Vous pouvez ajouter des champs, mais pas changer le type ou l'analyzer d'un champ existant : `mapper [created] cannot be changed from type [date] to [keyword]`. Créez donc un nouvel index et copiez les données. Les applications doivent toujours passer par un **alias**, jamais par l'index concret. Les étapes : créer `sales-v2`, lancer `_reindex` avec `wait_for_completion=false`, suivre la tâche jusqu'à sa fin, rattraper les écritures faites entre-temps, puis basculer l'alias en **un seul** appel `_aliases` **atomique**. Gardez `sales-v1` jusqu'à la validation du nouvel index, car le rollback est une autre bascule d'alias. Le rattrapage est la partie difficile : écrivez en double pendant la migration, ou rejouez depuis la source de vérité ([Q12](#sync-index-with-database)).

**Exemple :**

```text
POST _aliases
{ "actions": [
  { "remove": { "index": "sales-v1", "alias": "sales" } },
  { "add":    { "index": "sales-v2", "alias": "sales" } } ] }
```

#### Q11. Pourquoi les comptes d'une agrégation `terms` sont-ils parfois faux ? {#terms-aggregation-accuracy}
**Réponse :** Chaque shard renvoie ses meilleurs termes locaux, et le nœud coordinateur les fusionne. Un terme juste hors de la liste sur plusieurs shards peut être manqué ou sous-compté, même s'il fait partie du top global. La réponse le signale dans `doc_count_error_upper_bound`. Augmenter `shard_size` améliore la précision, au prix de la mémoire. Pour lister **tous** les buckets, utilisez une agrégation `composite` et paginez avec `after`, pas un `size` énorme. De même, `cardinality` est approximatif (HyperLogLog++, réglable avec `precision_threshold`), et `percentiles` est une estimation. Une agrégation sur un champ à forte cardinalité coûte aussi du heap ([S3](#circuit-breaker-data-too-large)).

## 🔴 Expert / Ouvert

#### Q12. Comment garder un index de recherche synchronisé avec la base de données ? {#sync-index-with-database}
**Réponse :** Traitez l'index comme un modèle de lecture **dérivé et reconstructible**, et la base de données comme la source de vérité. La double écriture depuis l'application est le piège : si la seconde écriture échoue, les stores divergent, et aucune transaction ne les couvre tous les deux. Utilisez le **transactional outbox** ou le **CDC** (Debezium lit le WAL vers Kafka), puis un consumer indexe par lots avec `_bulk`. Les événements peuvent arriver dans le désordre : passez donc la version de la ligne avec `version_type=external`. Elasticsearch rejette alors toute version plus ancienne avec un `409`, que le consumer traite comme un succès. Gardez aussi un chemin de reconstruction complète (reindex depuis la base vers un nouvel index, puis bascule de l'alias), car il servira pour les changements de mapping et pour réparer les écarts.

**Exemple :**

```text
PUT orders/_doc/42?version=17&version_type=external   # 201
PUT orders/_doc/42?version=12&version_type=external   # 409 : la version courante [17] est plus élevée
```

#### Q13. Comment exploiter une architecture hot/warm/cold pour des logs ? {#hot-warm-cold-ilm}
**Réponse :** Les données temporelles perdent de la valeur en vieillissant : adaptez le matériel à leur âge. Les nœuds **hot** ont des SSD rapides et reçoivent les écritures. Les nœuds **warm** gardent les données en lecture seule sur des disques moins chers. Les tiers **cold** et **frozen** utilisent des searchable snapshots, les données étant dans un stockage objet : cold garde une copie locale complète sans réplicas, et frozen garde seulement un petit cache et lit à la demande. **ILM** fait passer les index par les phases : rollover sur la taille ou l'âge en hot, force merge en warm, searchable snapshot en cold, suppression à la fin. Utilisez des **data streams** pour les données en ajout seul. En pratique, la durée de rétention et le profil des requêtes (à quelle fréquence cherche-t-on des données de plus de 7 jours ?) guident la conception. Notez que `min_age` compte depuis le **rollover**, et non depuis la création de l'index, dès qu'un rollover a eu lieu.

#### Q14. Comment améliorer la pertinence de la recherche ? {#relevance-tuning-hybrid}
**Réponse :** Commencez par **mesurer** : construisez une liste de jugements à partir de vraies requêtes et de résultats attendus, et suivez-la avec l'API `_rank_eval` ou des données de clics (taux de zéro résultat, position du clic). Sans cela, régler une requête en casse dix autres. Allez ensuite du moins cher au plus cher : analyse (stemming, synonymes, `asciifolding`), boosts de champs dans `multi_match`, boosts de phrase avec `should`, et signaux métier avec `function_score`. Pour le sens plutôt que les mots, ajoutez des vecteurs (`dense_vector`, recherche kNN) et combinez les deux listes par **recherche hybride**, en général avec la **reciprocal rank fusion** (RRF), qui évite de normaliser les scores BM25 par rapport aux scores vectoriels. La recherche lexicale reste meilleure sur les références et les noms exacts, ce qui explique pourquoi l'hybride bat le tout-vectoriel sur la plupart des catalogues e-commerce.

#### Q15. Qu'est-ce que le split brain, et comment Elasticsearch l'évite-t-il ? {#split-brain-quorum}
**Réponse :** Le split brain, ce sont deux masters qui acceptent des états de cluster contradictoires après une partition réseau. Depuis la 7.0, le cluster gère sa configuration de vote automatiquement, et une élection demande une **majorité** des nœuds éligibles master : le côté minoritaire ne peut donc pas élire de master. L'ancien réglage manuel `discovery.zen.minimum_master_nodes` a disparu. Exécutez **trois** nœuds dédiés éligibles master sur trois zones : deux nœuds ne survivent à la perte d'aucun des deux, et un nombre pair n'ajoute aucune tolérance. `cluster.initial_master_nodes` sert uniquement au tout premier démarrage ; le laisser en place sur un cluster qui redémarre plus tard avec des données effacées peut créer un second cluster. La réplication est une question distincte : les écritures vont au primaire, puis à tous les réplicas in-sync.

#### Q16. Elasticsearch ou OpenSearch : qu'est-ce qui diffère, et comment choisir ? {#elasticsearch-vs-opensearch}
**Réponse :** En 2021, Elastic a quitté Apache 2.0, et AWS a forké Elasticsearch 7.10.2 sous le nom d'**OpenSearch** (Apache 2.0, désormais sous la Linux Foundation). Elastic a ajouté l'AGPLv3 comme option de licence en 2024. Depuis le fork, les API ont divergé : ne supposez pas la compatibilité. Les bases du Query DSL, les mappings et `_cat` sont proches, mais l'exploitation diffère : **ISM** au lieu d'ILM, chemins `_plugins/...`, un plugin de sécurité au lieu de la sécurité native X-Pack, et `knn_vector` au lieu de `dense_vector`. Les clients Elasticsearch officiels récents refusent de parler à OpenSearch : utilisez `opensearch-java` ou `opensearch-py`. Choisissez selon vos contraintes : Elastic pour les fonctionnalités de recherche les plus récentes, l'Elastic Stack et l'offre Elastic Cloud ; OpenSearch pour une licence permissive ou AWS OpenSearch Service. Faites un proof of concept sur vos vraies requêtes plutôt que de comparer des listes de fonctionnalités. Les [notes](../notes/elasticsearch-opensearch.md#elasticsearch-vs-opensearch-api-differences) contiennent un tableau au niveau des commandes.

## 🎯 Scénarios réels

### S1. Le cluster passe au rouge après la perte d'un nœud {#red-cluster-unassigned-shards}
- **Symptômes :** `_cluster/health` indique `red` ; les recherches renvoient des résultats partiels avec `_shards.failed > 0` ; les écritures échouent sur certains index. Un nœud a été remplacé il y a une heure.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Rouge signifie qu'au moins un **primaire** n'est pas assigné. `_cat/shards?h=index,shard,prirep,state,unassigned.reason` le trouve, et `_cluster/allocation/explain` donne le decider exact : un nœud parti sans réplica, une règle `filter` qu'aucun nœud ne satisfait, un watermark disque, ou trop de tentatives échouées.
- **Résolution :** Ramenez le nœud si ses données existent encore ; le shard se rétablit tout seul. Corrigez la cause indiquée par le decider, puis lancez `POST _cluster/reroute?retry_failed=true`. Si les données sont perdues, **restaurez cet index depuis un snapshot**. `allocate_stale_primary` et `allocate_empty_primary` sont le dernier recours, car ils acceptent une perte de données.
- **Prévention :** Au moins un réplica sur les index de production, allocation awareness entre zones, snapshots testés, et une alerte sur `status != green` qui dure plus de quelques minutes. Réglez `index.unassigned.node_left.delayed_timeout` pour les redémarrages prévus.

</details>

### S2. L'indexation s'arrête avec un `429` et « flood-stage watermark », mais les recherches fonctionnent {#disk-flood-stage-read-only}
- **Symptômes :** `cluster_block_exception`, `disk usage exceeded flood-stage watermark, index has read-only-allow-delete block` ; les nouveaux shards restent non assignés sur certains nœuds.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les watermarks disque sont fixés à **85 % (low)**, **90 % (high)** et **95 % (flood stage)**. Au-dessus de low, aucun nouveau shard ne va sur le nœud. Au-dessus de high, des shards en partent. Au-dessus de flood stage, tout index ayant un shard sur ce nœud passe en lecture seule. `_cat/allocation?v` montre l'usage disque par nœud. La vraie cause est souvent une politique ILM bloquée ou des tailles de shards inégales.
- **Résolution :** Libérez du disque : supprimez d'anciens index, ajoutez des nœuds ou agrandissez le volume. Le blocage est levé automatiquement quand l'usage repasse sous le watermark high ; au besoin, levez-le avec `PUT <index>/_settings {"index.blocks.read_only_allow_delete": null}`. Lever le blocage sans libérer de disque ne fait que retarder la prochaine panne.
- **Prévention :** Alerte à 75 % de disque, rétention imposée par ILM, et alerte sur les erreurs ILM (`GET */_ilm/explain?only_errors=true`).

</details>

### S3. Un nouveau dashboard déclenche `circuit_breaking_exception` et des nœuds décrochent {#circuit-breaker-data-too-large}
- **Symptômes :** `[parent] Data too large` avec un HTTP `429` ; le heap JVM reste au-dessus de 85 % avec de longues pauses GC ; des nœuds quittent et rejoignent le cluster juste après le lancement d'un dashboard.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les circuit breakers stoppent une requête avant qu'elle ne provoque un `OutOfMemoryError`. `_nodes/stats/breaker` montre quel breaker se déclenche. `_cat/fielddata?v` révèle `fielddata: true` sur un champ `text`, qui charge tous les termes sur le heap. Sinon, cherchez une agrégation `terms` avec un `size` énorme, ou des agrégations imbriquées dont les buckets se multiplient. `_tasks?detailed` et le slow log trouvent la requête.
- **Résolution :** Annulez la tâche (`POST _tasks/<id>/_cancel`), corrigez le dashboard, et agrégez sur un sous-champ `keyword` avec doc values. Libérez la mémoire avec `POST <index>/_cache/clear?fielddata=true`. N'augmentez pas les limites des breakers : c'est le filet de sécurité.
- **Prévention :** Gardez le heap à la moitié de la RAM au maximum (et sous environ 31 Go, pour conserver les compressed pointers), laissez le reste au cache du système de fichiers, limitez `search.max_buckets`, et testez les dashboards en charge sur des données réelles.

</details>

### S4. Un import bulk indique un succès, mais des milliers de documents manquent {#bulk-rejections-partial-failure}
- **Symptômes :** Les logs de l'importeur ne montrent que des HTTP `200`, mais `_count` est inférieur de 8 %. `_cat/thread_pool/write?v&h=node_name,name,active,queue,rejected` montre `rejected` qui augmente pendant l'import.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** `_bulk` renvoie `200` même quand des éléments échouent. Le vrai résultat est dans `errors: true` et dans le `status` de chaque élément. Les éléments rejetés ont le statut `429` (`es_rejected_execution_exception`), car la file d'écriture est pleine. D'autres peuvent être en `400` pour des erreurs de mapping, et ceux-là ne réussiront jamais en réessayant.
- **Résolution :** Lisez le statut de chaque élément. Réessayez les `429` avec un backoff exponentiel, et envoyez les échecs permanents vers un dead-letter store. Réduisez la concurrence, et visez des lots d'environ 5 à 15 Mo. Pour un chargement ponctuel, passez `refresh_interval` à `-1` et les réplicas à `0`, puis rétablissez-les ensuite.
- **Prévention :** Utilisez le bulk helper du client avec retries, comparez les comptes source et cible à la fin, et alertez sur `rejected`. N'augmentez pas la taille de la file, cela ne fait que masquer la surcharge.

</details>

### S5. Les logs d'un service cessent d'arriver après sa release {#mapping-conflict-field-limit}
- **Symptômes :** Seuls les logs de `checkout` disparaissent. Le shipper signale `document_parsing_exception` : `failed to parse field [response] of type [date]` ou `Limit of total fields [1000] has been exceeded`.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Plusieurs équipes partagent un index, et le mapping dynamique a fixé le type à partir de la première valeur. La nouvelle release envoie `response` sous forme d'objet ou de chaîne, et les documents sont rejetés. `GET <index>/_mapping/field/response` et `_field_caps` montrent le conflit entre index. Avec la seconde erreur, des clés générées à partir des données ont rempli le mapping ([Q6](#mapping-explosion-dynamic)).
- **Résolution :** Corrigez le producteur, ou renommez le champ dans un ingest pipeline. Un data stream peut faire un rollover vers un nouvel index de support avec un template corrigé, et les anciennes données restent telles quelles. N'augmentez pas la limite de champs en premier réflexe.
- **Prévention :** Déclarez dans l'index template les champs dont vous dépendez, utilisez un schéma partagé comme ECS, séparez les data streams par service, et routez les documents en échec vers un index dead-letter avec `on_failure` ou le failure store.

</details>

### S6. La recherche montre l'ancien statut après une mise à jour, mais pour certaines commandes seulement {#stale-search-after-db-update}
- **Symptômes :** La base indique `SHIPPED`, alors que la recherche montre `PAID` jusqu'à la reconstruction de la nuit suivante. Cela arrive surtout pendant les pics. Aucune erreur dans les logs de l'indexeur.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un délai d'environ une seconde serait l'intervalle de refresh, mais ici cela dure des heures : un événement a donc été réordonné ou perdu. Des consumers parallèles peuvent indexer `SHIPPED` puis un événement `PAID` plus ancien, et la dernière écriture gagne. Comparez `_version` ou un champ `updated_at` avec la base pour une commande fautive. Une double écriture qui échoue silencieusement donne le même symptôme.
- **Résolution :** Partitionnez les événements par id de commande pour traiter chaque commande dans l'ordre, et indexez avec `version_type=external` en utilisant la version de la ligne ([Q12](#sync-index-with-database)). Réparez l'écart en renvoyant les ids concernés.
- **Prévention :** Utilisez l'outbox ou le CDC plutôt que la double écriture, lancez une comparaison périodique des comptes et des checksums, et alertez sur le lag des consumers.

</details>

## 🏅 Labs Elastic Certified Engineer

L'examen est pratique : vous réalisez des tâches sur un cluster réel, sans QCM.

| Point | Détail | Source |
|---|---|---|
| Version | Elasticsearch **9.3** | [FAQ Elastic](https://www.elastic.co/training/certification/faq) |
| Format | Tâches réelles chronométrées sur un cluster réel, avec surveillance à distance | FAQ Elastic |
| Autorisé | La documentation Elastic. Ni Google ni Stack Overflow | FAQ Elastic |
| Nouvelle tentative | Attente de 14 jours et nouvelle tentative payante | FAQ Elastic |
| Validité | 2 ans | FAQ Elastic |
| Durée | Environ 3 heures et environ 10 tâches, crédit partiel | Témoignages de candidats, surtout sur d'anciennes versions |

Ces labs sont des **exercices originaux dans le style de l'examen, pas de vraies questions d'examen**, qui sont confidentielles. Ils sont regroupés selon les domaines des objectifs publiés : Data Management, Data Processing, Searching Data, Developing Search Applications et Cluster Management. Vérifiez la liste actuelle sur la [page de l'examen](https://www.elastic.co/training/elastic-certified-engineer-exam) avant de vous inscrire. Toutes les solutions ont été exécutées sur Elasticsearch 9.3.0. Les searchable snapshots et la réplication inter-clusters exigent une licence d'essai ou Enterprise.

**Tactiques d'examen, d'après des témoignages de candidats :**

- Lisez toutes les tâches d'abord, commencez par les rapides, et revenez aux difficiles.
- Faites exactement ce que la tâche demande, noms compris. N'ajoutez pas d'exigences de votre cru.
- Vérifiez chaque réponse : `GET <index>/_mapping`, `_cat`, `_simulate`, puis une vraie requête.
- Apprenez la navigation latérale de la documentation avant l'examen. Elle est souvent plus rapide que sa recherche.
- Tentez chaque tâche, car un travail partiel peut rapporter des points.

**Données d'entraînement pour les labs de recherche :**

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

#### S7. Lab : index template avec dynamic templates {#lab-index-dynamic-template}
- **Tâche :** Tout nouvel index correspondant à `shop-orders-*` doit avoir 1 shard et 0 réplica. `created_at` est une `date`. Les nouvelles chaînes deviennent `keyword`, sauf les champs finissant par `_text`, qui sont `text` avec l'analyzer `english`. Les nouveaux entiers finissant par `_count` deviennent `integer`.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Vérifier
POST _index_template/_simulate_index/shop-orders-2026
POST shop-orders-2026/_doc?refresh=true
{ "created_at": "2026-01-15", "status": "PAID", "review_text": "Great running shoes", "item_count": 3 }
GET shop-orders-2026/_mapping
```

- **Piège :** Le premier dynamic template qui correspond gagne : `*_text` doit donc précéder la règle générale sur les chaînes.
- **Piège :** Un template ne s'applique qu'aux **nouveaux** index. Les entiers JSON arrivent en `long` : il faut donc matcher sur `long`.

</details>

#### S8. Lab : data stream avec une politique ILM {#lab-data-stream-ilm}
- **Tâche :** Créez le data stream `app-events`. Faites un rollover à 1 jour ou quand un shard primaire atteint 50 Go. Après 7 jours, faites un force merge à un segment et un shrink à un shard. Supprimez après 30 jours.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Le premier document crée le data stream
POST app-events/_doc
{ "@timestamp": "2026-11-06T10:00:00Z", "service": "checkout", "message": "payment accepted" }

# Vérifier
GET _data_stream/app-events
GET app-events/_ilm/explain
POST app-events/_rollover
```

- **Piège :** Les data streams sont en ajout seul : `PUT app-events/_doc/1` échoue avec `only write ops with an op_type of create are allowed`. Utilisez `POST` ou `_create`.
- **Piège :** Évitez en pratique les patterns comme `logs-*-*` : ils entrent en collision avec les templates intégrés de priorité 100, et le vôtre doit alors avoir une priorité plus élevée.

</details>

### Data Processing

#### S9. Lab : analyzer personnalisé et multi-fields {#lab-custom-analyzer-multifields}
- **Tâche :** Créez `products` avec un champ `title` qui retire le HTML, remplace `&` par `and`, et ignore la casse et les accents. À la recherche, `sneakers` doit trouver `trainers`, et `tv` doit trouver `television`. Ajoutez `title.raw` pour les correspondances exactes et le tri, et `title.autocomplete` pour la recherche par préfixe à la frappe.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Vérifier
POST products/_analyze
{ "analyzer": "shop_search", "text": "<b>Café</b> & Thé" }    # cafe, and, the
POST products/_doc/1?refresh=true
{ "title": "Blue Trainers" }
GET products/_search
{ "query": { "match": { "title": "sneakers" } } }
GET products/_search
{ "query": { "match": { "title.autocomplete": "trai" } } }
```

- **Piège :** `synonym_graph` se place uniquement dans l'analyzer de **recherche**.
- **Piège :** `edge_ngram` se place uniquement dans l'analyzer d'indexation. S'il s'exécute aussi à la recherche, `trai` correspond à tout ce qui commence par `tr`.

</details>

#### S10. Lab : ingest pipeline avec Painless {#lab-ingest-pipeline-painless}
- **Tâche :** Créez `orders-enrich`. Mettez `customer_email` en minuscules, découpez `tags` séparés par des virgules et retirez les espaces, convertissez `quantity` et `unit_price` en nombres, calculez `total` arrondi à 2 décimales, mettez `size_class` à `big` si le total est d'au moins 100, sinon `small`, retirez `debug`, et ajoutez `ingested_at`. Envoyez les échecs vers `failed-orders` avec le message d'erreur. Appliquez le pipeline par défaut à `shop-orders-v1`.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Vérifier avant de toucher à un index
POST _ingest/pipeline/orders-enrich/_simulate
{ "docs": [
  { "_source": { "customer_email": "Ann@Example.COM", "tags": "sale, new", "quantity": "3", "unit_price": "39.90", "debug": "x" } },
  { "_source": { "customer_email": "b@x.io", "tags": "a", "quantity": "oops", "unit_price": "1" } } ] }

PUT shop-orders-v1
{ "settings": { "number_of_shards": 1, "number_of_replicas": 0, "index.default_pipeline": "orders-enrich" } }
```

- **Contrôle :** Le premier document donne `total: 119.7` et `size_class: big`. Le second va dans `failed-orders`.
- **Piège :** Dans un script d'ingestion, les champs se lisent avec `ctx.field`. `doc['field']` s'utilise dans les scripts de recherche et de runtime.

</details>

#### S11. Lab : `_update_by_query`, `_reindex` et un alias {#lab-reindex-update-by-query}
- **Tâche :** Dans `sales-v1`, mettez `brand` à `unknown` là où il manque. Ensuite, `sku` doit devenir un `keyword` : copiez uniquement les documents `PAID` vers `sales-v2`, ajoutez `revenue` (prix × quantité), et faites pointer l'alias `sales` vers `sales-v2`.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Vérifier : 4 documents, et JKT-001 a un revenue de 150
GET sales/_count
GET sales/_search
{ "query": { "term": { "sku": "JKT-001" } } }
```

- **Piège :** Créez **d'abord** l'index de destination, sinon `_reindex` le construit avec des mappings dynamiques.
- **Piège :** Avec `wait_for_completion=false`, la destination peut ne pas encore exister au retour de l'appel. Attendez la fin de la tâche avant de basculer un alias.

</details>

### Searching Data

#### S12. Lab : requête `bool` avec sous-agrégations {#lab-bool-query-aggregations}
- **Tâche :** Sur `sales-v1`, trouvez les documents contenant à la fois `running` et `shoes` dans `title` (boost 3) et `description`. Gardez uniquement les ventes `PAID` de janvier et février 2026, et excluez `socks`. Classez plus haut la phrase `trail running`. Dans la même requête, renvoyez les 3 meilleures catégories par mois avec le prix moyen de chacune.

<details markdown="1">
<summary>Afficher la solution</summary>

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

- **Contrôle :** Les hits sont les ids `1` puis `2`. Janvier a `shoes` avec un `avg_price` de `104.95`.
- **Piège :** Les agrégations portent sur les résultats de la **requête**. Pour des statistiques sur tous les documents, retirez la requête et utilisez `"size": 0`.

</details>

#### S13. Lab : runtime fields {#lab-runtime-field}
- **Tâche :** Sans réindexer, calculez `revenue` et `day_of_week` à la requête, renvoyez les deux, et sommez le revenu par jour de la semaine. Rendez ensuite `revenue` permanent dans le mapping, et trouvez les ventes d'au moins 150.

<details markdown="1">
<summary>Afficher la solution</summary>

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

- **Piège :** Les runtime fields ne sont pas dans `_source` : demandez-les avec `fields`.
- **Piège :** Ils utilisent `emit`, pas `return`, et coûtent du CPU à la requête. Passez-les en champ indexé s'ils deviennent très utilisés.

</details>

#### S14. Lab : async search {#lab-async-search}
- **Tâche :** Lancez une recherche qui compte les documents par `category`. Rendez la main tout de suite, gardez le résultat une heure, vérifiez son état, récupérez le résultat, puis supprimez-le.

<details markdown="1">
<summary>Afficher la solution</summary>

```text
POST sales-v1/_async_search?wait_for_completion_timeout=0ms&keep_on_completion=true&keep_alive=1h
{ "size": 0, "aggs": { "by_category": { "terms": { "field": "category" } } } }

GET _async_search/status/<id>
GET _async_search/<id>
DELETE _async_search/<id>
```

- **Contrôle :** La première réponse a `is_running: true` et `is_partial: true`. Les deux passent à `false` à la fin.
- **Piège :** Une recherche terminée avant le timeout n'est pas stockée sans `keep_on_completion=true`.

</details>

### Developing Search Applications

#### S15. Lab : search template, surlignage, tri et pagination {#lab-search-template-pagination}
- **Tâche :** Stockez un search template `product-search` avec un paramètre obligatoire `q`, un `status` optionnel (par défaut `PAID`) et un `size` optionnel (par défaut 10). Surlignez les correspondances avec `<mark>`, et triez par prix, puis par date, tous deux en ordre décroissant. Séparément, parcourez tous les résultats pour `running` deux par deux, sans `from`.

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Contrôler le rendu, puis l'exécuter
POST _render/template
{ "id": "product-search", "params": { "q": "running" } }
GET sales-v1/_search/template
{ "id": "product-search", "params": { "q": "running", "size": 2 } }

# Pagination : ouvrir un PIT, sans index dans le chemin de recherche
POST sales-v1/_pit?keep_alive=2m
GET _search
{ "size": 2, "query": { "match": { "title": "running" } },
  "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "price": "desc" }, { "_shard_doc": "asc" } ] }

# Page suivante : passer les valeurs de tri du dernier hit
GET _search
{ "size": 2, "query": { "match": { "title": "running" } },
  "pit": { "id": "<pit_id>", "keep_alive": "2m" },
  "sort": [ { "price": "desc" }, { "_shard_doc": "asc" } ],
  "search_after": [89.9, 0] }     # à copier depuis votre dernier hit

DELETE _pit
{ "id": "<pit_id>" }
```

- **Contrôle :** La page 1 renvoie les ids `2` et `1`, et la page 2 les ids `4` et `5`.
- **Piège :** `{{^size}}…{{/size}}` est une section inversée Mustache : elle s'affiche quand la valeur manque.
- **Piège :** Avec un PIT, l'index se place dans le PIT, pas dans l'URL. `GET sales-v1/_search` avec un `pit` échoue.

</details>

### Cluster Management

#### S16. Lab : réparer un cluster rouge {#lab-repair-cluster-health}
- **Tâche :** Après l'exécution de la mise en place ci-dessous, le cluster est rouge. Trouvez pourquoi et ramenez-le au vert, sur un cluster à un seul nœud.

<details markdown="1">
<summary>Afficher la solution</summary>

```text
# Mise en place
PUT broken-1
{ "settings": { "number_of_shards": 1, "number_of_replicas": 1,
  "index.routing.allocation.require.data_zone": "zone-z" } }

# Diagnostic
GET _cat/health?v
GET _cat/shards/broken-1?v&h=index,shard,prirep,state,unassigned.reason
GET _cluster/allocation/explain
{ "index": "broken-1", "shard": 0, "primary": true }
# decider "filter": node does not match index setting [index.routing.allocation.require]

# Corriger les deux causes : la mauvaise règle, et un réplica jamais assignable sur un seul nœud
PUT broken-1/_settings
{ "index.routing.allocation.require.data_zone": null, "index.number_of_replicas": 0 }

# Vérifier
GET _cluster/health?wait_for_status=green&timeout=5s
```

- **Piège :** Retirer le réplica n'est correct qu'ici, car un seul nœud ne peut pas l'héberger. Sur un cluster multi-nœuds, gardez-le.
- **Piège :** Après des échecs répétés, un shard cesse de réessayer. Corrigez la cause, puis lancez `POST _cluster/reroute?retry_failed=true`.

</details>

#### S17. Lab : snapshot, restauration et searchable snapshots {#lab-snapshot-restore-searchable}
- **Tâche :** Enregistrez un dépôt `fs` (`path.repo` doit inclure son emplacement). Faites un snapshot de `sales-v1` uniquement, et restaurez-le sous le nom `restored-sales-v1`. Planifiez un snapshot quotidien avec une rétention de 30 jours. Montez ensuite le snapshot en `sales-archive` (copie complète) et en `sales-frozen` (cache partagé).

<details markdown="1">
<summary>Afficher la solution</summary>

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

# Vérifier
GET _cat/snapshots/lab-repo?v
GET _cat/indices/sales-*,restored-*?v&h=index,health,docs.count&s=index
```

- **Piège :** Vous ne pouvez pas restaurer sur un index ouvert de même nom : renommez, fermez ou supprimez-le d'abord.
- **Piège :** `shared_cache` exige un nœud avec le rôle `data_frozen` et un cache partagé. Les index montés sont en lecture seule : une écriture renvoie `403`.
- **Version ILM :** `"cold": { "min_age": "30d", "actions": { "searchable_snapshot": { "snapshot_repository": "lab-repo" } } }`. Le dépôt doit exister avant de créer la politique.

</details>

#### S18. Lab : cross-cluster search et réplication {#lab-cross-cluster-search-replication}
- **Tâche :** Depuis `cluster_a`, connectez-vous à `cluster_b`. Lancez une agrégation sur `sales-v1` en local et `sales-eu` à distance. Répliquez ensuite `sales-eu` vers le follower local `sales-eu-copy`, et ajoutez un pattern d'auto-follow pour les futurs index `sales-eu-*`.

<details markdown="1">
<summary>Afficher la solution</summary>

```text
# Sur cluster_a
PUT _cluster/settings
{ "persistent": { "cluster": { "remote": { "cluster_b": {
  "mode": "sniff", "seeds": ["es-lab-b:9300"], "skip_unavailable": true } } } } }

GET _remote/info          # attendu : "connected": true

GET sales-v1,cluster_b:sales-eu/_search
{ "size": 0, "aggs": { "by_category": { "terms": { "field": "category" } } } }

PUT sales-eu-copy/_ccr/follow?wait_for_active_shards=1
{ "remote_cluster": "cluster_b", "leader_index": "sales-eu" }

GET sales-eu-copy/_ccr/stats

PUT _ccr/auto_follow/eu-sales
{ "remote_cluster": "cluster_b", "leader_index_patterns": ["sales-eu-*"],
  "follow_index_pattern": "{{leader_index}}-copy" }

# Promouvoir le follower en index normal (par exemple, après la perte du leader)
POST sales-eu-copy/_ccr/pause_follow
POST sales-eu-copy/_close
POST sales-eu-copy/_ccr/unfollow
POST sales-eu-copy/_open
```

- **Piège :** Les seeds utilisent le port **transport** (9300), pas le port HTTP.
- **Piège :** Un follower est en lecture seule : une écriture directe renvoie `403`. La requête de follow s'exécute sur le cluster **follower**.
- **Piège :** L'auto-follow ne couvre que les index créés **après** le pattern.

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q1. Qu'est-ce qu'un index inversé, et qu'est-ce qu'un segment Lucene ?
2. Q3. Quelle est la différence entre `text` et `keyword`, et que fait un analyzer ?
3. Q5. Pourquoi la recherche est-elle « near real time » ? Que font `refresh` et `flush` ?
4. Q7. Combien de shards un index doit-il avoir ?
5. Q8. Comment paginer loin dans les résultats ?
6. Q9. `object`, `nested` ou `join` : comment modéliser les relations ?
7. Q10. Comment changer un mapping sans interruption ?
8. Q12. Comment garder un index de recherche synchronisé avec la base de données ?
9. Q16. Elasticsearch ou OpenSearch : qu'est-ce qui diffère, et comment choisir ?
10. S1. Le cluster passe au rouge après la perte d'un nœud

## 📌 Cheat-sheet

- **Index** — index inversé pour la recherche, doc values pour le tri et les agrégations. *Les segments sont immuables.*
- **Champs** — `text` est analysé, `keyword` est exact. *`term` sur `text` est le bug classique ; utilisez les multi-fields.*
- **Requêtes** — le score dans `must`/`should`, les conditions exactes dans `filter`. *Les filtres sont mis en cache et ne calculent pas de score.*
- **Écritures** — durables tout de suite, cherchables après un refresh. *Évitez `?refresh=true` à chaque écriture.*
- **Mappings** — les types ne changent pas. *Alias + `_reindex` + bascule atomique ; `dynamic: strict` sur les index métier.*
- **Shards** — environ 10–50 Go. *Rollover sur la taille ; les shards minuscules coûtent plus qu'ils ne rapportent.*
- **Pagination** — `search_after` + PIT. *`from + size` s'arrête à 10 000.*
- **Synchro** — outbox ou CDC avec `version_type=external`. *L'index est dérivé et reconstructible.*
- **Santé** — rouge = primaire manquant, jaune = réplica manquant. *`_cluster/allocation/explain` d'abord.*
- **Disque** — watermarks à 85 % / 90 % / 95 %. *Le flood stage passe les index en lecture seule.*
- **Bulk** — un HTTP `200` peut cacher des échecs. *Vérifiez `errors` et chaque élément, ne réessayez que les `429`.*
- **Examen** — vérifiez chaque tâche avec `_simulate`, `_mapping`, `_cat`. *La doc est autorisée : connaissez sa navigation.*
