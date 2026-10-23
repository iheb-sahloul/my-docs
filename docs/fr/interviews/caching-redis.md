# Cache & Redis

Questions de cache approfondies : structures de données Redis, éviction, stampede, pièges de Spring Cache, verrous et topologie de cluster. Les bases sont dans Conception de systèmes ([System Design Q7](system-design.md#caching-basic-idea-behind-cache), [System Design Q17](system-design.md#invalidate-cached-entry-race-hides), [System Design Q26](system-design.md#cache-aside-write-write-behind)), avec les scénarios d'incident [System Design S1](system-design.md#after-deploy-every-cache-entry) (expiration massive), [System Design S7](system-design.md#cache-expiring-hot-key-causes) (expiration d'une clé chaude) et [System Design S15](system-design.md#one-redis-key-receives-most) (shard chaud).

## 🟢 Fondamentaux

#### Q1. Pourquoi mettre en cache, et à quelle couche ? {#why-cache-which-layer}
**Réponse :** Un cache échange de la fraîcheur contre de la latence et de la charge : il est rentable quand les lectures dominent, que les mêmes clés sont relues et qu'une donnée légèrement périmée est acceptable. Les couches, de la plus proche de l'utilisateur : navigateur (`Cache-Control`), CDN, reverse proxy, en mémoire du processus (Caffeine), distribué (Redis), puis le buffer cache de la base. Mettez en cache aussi près de l'utilisateur que la confidentialité et la fraîcheur des données le permettent. Mesurez le **taux de hit** et la charge retirée à la base. Un taux de hit de 30 % sur une requête peu coûteuse ajoute un saut réseau et un problème de cohérence pour peu de gain.

#### Q2. Quelles structures de données Redis utilisez-vous, et pour quoi ? {#redis-data-structures-use-what}
**Réponse :** **String** : JSON en cache, compteurs (`INCR`), drapeaux avec TTL. **Hash** : un objet dont on met à jour les champs séparément (`HINCRBY`), économe en mémoire pour les petits objets. **List** : files simples, N derniers éléments (`LPUSH` + `LTRIM`). **Set** : appartenance, visiteurs uniques par jour, tags. **Sorted set** : classements, rate limit en fenêtre glissante, jobs différés triés par timestamp. **Stream** : journal en ajout seul avec groupes de consommateurs, alternative légère à Kafka. **HyperLogLog** : comptage approximatif de valeurs distinctes en 12 Ko. **Bitmap** : drapeaux quotidiens par utilisateur. Choisir la bonne structure transforme une logique en une seule commande atomique, au lieu d'un lire-modifier-écrire côté application.

**Exemple :**

```text
ZADD leaderboard 1520 user:42          # mise à jour du score, O(log n)
ZREVRANGE leaderboard 0 9 WITHSCORES   # top 10
```

#### Q3. Comment fonctionnent TTL et éviction dans Redis, et quelle `maxmemory-policy` choisir ? {#ttl-eviction-maxmemory-policy}
**Réponse :** Un TTL supprime une clé après un délai fixe ; l'éviction supprime des clés quand `maxmemory` est atteint. La politique par défaut est `noeviction`, qui **refuse les écritures** avec une erreur OOM quand la mémoire est pleine. C'est le bon choix pour Redis utilisé comme datastore, et le mauvais pour un pur cache. Pour un cache, prenez `allkeys-lru` ou `allkeys-lfu` (LFU garde mieux les clés souvent lues lors des scans). Les politiques `volatile-*` n'évincent que les clés avec TTL : un cache plein de clés sans TTL se comporte donc comme `noeviction`. Le LRU/LFU de Redis est approximatif (échantillonné), ce qui suffit en pratique. Fixez toujours `maxmemory` sous la limite du conteneur, avec une marge pour la persistance par fork.

## 🟡 Pièges seniors

#### Q4. Cache-aside, read-through, write-through ou write-behind : qu'est-ce que ça change en pratique ? {#cache-aside-read-write-through}
**Réponse :** Les compromis sont dans [System Design Q26](system-design.md#cache-aside-write-write-behind). En pratique : le **cache-aside** (l'application lit le cache, se rabat sur la base puis remplit le cache) est le défaut avec Redis, car Redis n'a pas de loader. Le **read-through** est ce que donnent le `LoadingCache` de Caffeine ou `@Cacheable` de Spring en mémoire. Le **write-through** garde le cache chaud mais écrit des données que personne ne lira peut-être. Le **write-behind** risque une perte de données en cas de crash et exige des flushs idempotents. À l'écriture, préférez **supprimer la clé après le commit** plutôt que la mettre à jour : sinon deux mises à jour concurrentes peuvent laisser l'ancienne valeur en cache.

#### Q5. Qu'est-ce qu'un cache stampede, et comment l'éviter ? {#cache-stampede-prevent}
**Réponse :** Quand une clé populaire expire, toutes les requêtes concurrentes ratent le cache et la recalculent en même temps, envoyant N requêtes identiques à la base. Défenses : **jitter sur le TTL** (`ttl ± 10 %`) pour que des clés écrites ensemble n'expirent pas ensemble ; **single-flight** (une requête recalcule, les autres attendent ou servent du périmé), avec un verrou en mémoire ou un `SET lock NX PX` court dans Redis ; **rafraîchissement anticipé ou en arrière-plan** (avant expiration, de façon probabiliste ou planifiée, pour les clés chaudes connues) ; **servir du périmé en cas d'erreur**. `refreshAfterWrite` de Caffeine fait le rafraîchissement anticipé en mémoire. Voir [System Design S7](system-design.md#cache-expiring-hot-key-causes) pour l'incident.

**Exemple :**

```java
Cache<String, Price> prices = Caffeine.newBuilder()
    .expireAfterWrite(Duration.ofMinutes(10))
    .refreshAfterWrite(Duration.ofMinutes(8))   // rafraîchissement async, les appelants gardent l'ancienne valeur
    .build(key -> priceRepository.load(key));
```

#### Q6. Quels sont les pièges classiques de Spring Cache (`@Cacheable`) ? {#spring-cacheable-pitfalls}
**Réponse :** (1) **Auto-invocation** : un appel depuis la même classe contourne le proxy, donc rien n'est mis en cache. (2) **Clés** : la clé par défaut est formée des paramètres ; deux méthodes partageant un nom de cache avec les mêmes paramètres entrent en collision, et un paramètre sans `equals`/`hashCode` ne fait jamais de hit. Utilisez une clé explicite `key = "#id"`. (3) **Pas de TTL par défaut** : configurez-le par cache dans le `RedisCacheManager`. (4) **Cache des null** : actif par défaut avec Redis, utile contre la pénétration mais masque les données créées ensuite ; ajustez avec `unless = "#result == null"` ou un TTL court. (5) **Objets mutables en cache** avec un cache local : les appelants modifient l'instance partagée ([Spring Q20](spring-architecture.md#trap-cacheable-returning-mutable-object)). (6) **Sérialisation** : la sérialisation JDK casse quand la classe change ; préférez JSON avec un préfixe de cache versionné. (7) `@CacheEvict` s'exécute après la méthode, mais **avant le commit de la transaction** si la méthode y participe : un lecteur concurrent peut alors remettre l'ancienne valeur en cache.

#### Q7. Quand combiner un cache local et Redis, et comment les garder cohérents ? {#local-cache-plus-redis}
**Réponse :** Un cache local (L1) Caffeine évite le saut réseau (moins d'une microseconde contre environ 0,5 ms) et protège Redis des clés chaudes. Redis (L2) est partagé par tous les pods et survit aux redémarrages. Le prix : chaque pod a sa propre copie, donc une mise à jour laisse N copies L1 périmées. Options : un **TTL L1 court** (quelques secondes) si un peu de périmé est acceptable, le plus simple ; une **diffusion d'invalidation** via Redis Pub/Sub ou le client-side caching (`CLIENT TRACKING`), rapide mais au mieux, car les messages sont perdus si un pod est déconnecté : gardez un TTL comme filet de sécurité. Réservez le L1 aux données petites, chaudes et rarement modifiées (configuration, référentiels, feature flags).

#### Q8. Redis est-il durable ? Quand peut-on l'utiliser comme datastore principal ? {#redis-durability-rdb-aof}
**Réponse :** **RDB** prend des snapshots périodiques par fork : on perd tout depuis le dernier snapshot. **AOF** journalise chaque écriture ; avec `appendfsync everysec`, on perd jusqu'à environ une seconde. La réplication est **asynchrone** : un failover peut perdre des écritures acquittées (`WAIT` réduit le risque sans en faire un système à consensus). Traitez Redis comme un cache (perdable, reconstructible) par défaut. Ne l'utilisez comme source de vérité que pour des données dont la perte est tolérable ou reconstructible : sessions, compteurs de rate limit, classements. Sinon, prenez une offre managée aux garanties plus fortes et assumez les compromis explicitement. Prévoyez aussi le cas où Redis est complètement indisponible : [System Design R17](system-design.md#redis-cache-crashes-unexpectedly-application).

## 🔴 Expert / Ouvert

#### Q9. Comment construire un verrou avec Redis, et pourquoi Redlock fait-il débat ? {#redis-lock-redlock-debate}
**Réponse :** Instance unique : `SET lock:job42 <jeton-aléatoire> NX PX 30000` pour acquérir, et libération par un script Lua qui ne supprime que si la valeur est encore votre jeton. Sinon, vous risquez de supprimer un verrou pris par quelqu'un d'autre après l'expiration du vôtre. Le bail expire : une pause GC ou un blocage réseau plus long que le TTL laisse deux détenteurs travailler en même temps. **Redlock** acquiert sur une majorité de N maîtres indépendants. La critique de Kleppmann : il suppose une dérive d'horloge et des pauses bornées, et ne peut pas empêcher un détenteur en pause d'écrire. Le remède est un **jeton de fencing** (un numéro monotone vérifié par la ressource elle-même), que Redis ne fournit pas. Conclusion : un verrou Redis convient pour l'**efficacité** (éviter du travail en double). Pour la **correction**, utilisez la base (verrou de ligne, contrainte d'unicité, colonne de version) ou un système à consensus avec fencing. Voir [System Design Q30](system-design.md#isn-distributed-lock-redis-set).

**Exemple :**

```lua
-- ne libère que si on possède encore le verrou
if redis.call("GET", KEYS[1]) == ARGV[1] then return redis.call("DEL", KEYS[1]) else return 0 end
```

#### Q10. Sentinel ou Cluster : comment Redis passe-t-il à l'échelle et bascule-t-il ? {#redis-sentinel-cluster-scaling}
**Réponse :** **Sentinel** assure la haute disponibilité d'un primaire et de ses réplicas : il surveille, élit et promeut, et les clients lui demandent le primaire courant. Il ne fait pas monter les écritures en charge. **Cluster** découpe l'espace de clés en 16 384 **hash slots** répartis sur plusieurs primaires, chacun avec ses réplicas : il fait monter en charge la mémoire et les écritures. Le piège : les commandes multi-clés, transactions et scripts Lua ne fonctionnent que si toutes les clés sont dans le même slot. On l'impose avec des **hash tags** (`{user:42}:cart`, `{user:42}:profile`), au risque de créer un slot chaud. Les clients doivent gérer les redirections `MOVED`/`ASK` (Lettuce le fait). Les services managés (ElastiCache, MemoryDB) proposent les deux modes. Ne lisez sur les réplicas que si des lectures périmées sont acceptables.

#### Q11. Comment implémenter atomiquement un rate limiter, un classement ou un store de sessions avec Redis ? {#redis-atomic-patterns}
**Réponse :** L'essentiel est d'éviter le lire-modifier-écrire en plusieurs allers-retours. **Fenêtre fixe** : `INCR key` puis `EXPIRE key 60` au premier hit (dans un bloc `MULTI` ou en Lua, sinon un crash entre les deux laisse un compteur qui n'expire jamais). **Fenêtre glissante** : un sorted set de timestamps (`ZREMRANGEBYSCORE`, `ZADD`, `ZCARD`) dans un seul script Lua. **Token bucket** : un script Lua stockant jetons et dernière recharge dans un hash. **Classement** : `ZINCRBY` / `ZREVRANK`. **Sessions** : un hash par session avec un TTL glissant (`EXPIRE` à chaque accès), comme Spring Session. Les scripts Lua s'exécutent atomiquement mais bloquent le serveur : gardez-les courts. `MULTI` donne une exécution atomique, pas de rollback.

#### Q12. Comment garder le cache cohérent avec la base à grande échelle ? {#cache-db-consistency-scale}
**Réponse :** Acceptez que le cache-aside soit **cohérent à terme** et bornez la péremption. Les patterns, du plus simple : un **TTL** comme borne supérieure de péremption ; la **suppression après commit** (dans un hook `afterCommit` ou `@TransactionalEventListener(phase = AFTER_COMMIT)`) plutôt que pendant la transaction ; la **double suppression différée** pour couvrir un lecteur concurrent qui a remis l'ancienne valeur ; l'**invalidation pilotée par CDC** (Debezium lit le WAL et supprime les clés), qui capte les écritures de tous les services et le SQL manuel ; les **clés versionnées** (`product:42:v17`) : une nouvelle version est une nouvelle clé et les anciennes expirent d'elles-mêmes. Pour les données qui ne doivent jamais être périmées (soldes, stock au paiement), ne les cachez pas, ou revérifiez en base au moment de la décision.

## 🎯 Scénarios réels

### S1. Après une mise à jour de prix, certains utilisateurs voient l'ancien prix pendant des heures {#stale-price-after-update}
- **Symptômes :** L'admin modifie un prix ; la base est correcte, mais certaines pages produit affichent l'ancien prix jusqu'à l'expiration du TTL de 6 heures. Cela n'arrive que sous charge.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une race du cache-aside. `@CacheEvict` s'exécute dans la transaction de mise à jour, avant le commit. Un lecteur concurrent rate le cache, lit l'**ancienne** ligne commitée et la réécrit dans Redis. Puis le commit arrive, et la valeur périmée reste pendant tout le TTL. Confirmez en comparant l'heure d'écriture de la clé (`OBJECT IDLETIME` ou un timestamp journalisé) avec l'heure du commit.
- **Résolution :** Évincez après commit (`@TransactionalEventListener(phase = AFTER_COMMIT)`), ajoutez une seconde suppression différée par sécurité et raccourcissez le TTL des prix.
- **Prévention :** Règle d'équipe : l'invalidation du cache se fait après commit, jamais dans la transaction. Ajoutez un test d'intégration qui lit en concurrence pendant une mise à jour, et envisagez une invalidation par CDC ([Q12](#cache-db-consistency-scale)).

</details>

### S2. Les écritures dans Redis échouent avec `OOM command not allowed` {#redis-oom-noeviction}
- **Symptômes :** `OOM command not allowed when used memory > 'maxmemory'` dans les logs ; les connexions échouent car les sessions ne peuvent plus être écrites ; `used_memory` est bloqué à la limite.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** `INFO memory` et `CONFIG GET maxmemory-policy` montrent `noeviction` (ou `volatile-lru` avec des clés sans TTL). `INFO keyspace` montre `expires` bien en dessous de `keys` ; `redis-cli --bigkeys` / `--memkeys` trouve le préfixe qui grossit, souvent un cache écrit sans TTL.
- **Résolution :** Supprimez ou ajoutez un TTL au préfixe fautif (`SCAN` + `UNLINK`, par lots), augmentez temporairement `maxmemory` et séparez le cache des sessions : une instance en `allkeys-lru` pour le cache, une autre en `noeviction` pour les données à ne pas perdre.
- **Prévention :** Chaque écriture de cache a un TTL (imposé par un wrapper commun), alerte sur `used_memory / maxmemory > 80 %` et sur les évictions ou écritures refusées, et suivi du nombre de clés par préfixe.

</details>

### S3. La latence de Redis monte à plusieurs secondes pour tous les clients, quelques fois par jour {#redis-blocked-keys-command}
- **Symptômes :** Tous les services signalent des timeouts Redis en même temps pendant 2 à 5 secondes ; le CPU de Redis est à 100 % sur un cœur ; aucun pic de trafic.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Redis exécute les commandes sur un seul thread : une commande lente bloque tout le monde. `SLOWLOG GET 20` montre un `KEYS user:*` lancé par un job d'admin, ou `HGETALL`/`SMEMBERS`/`DEL` sur une clé de plusieurs millions d'éléments. `LATENCY DOCTOR` et le temps de fork dans `INFO persistence` écartent un snapshot RDB comme cause.
- **Résolution :** Remplacez `KEYS` par `SCAN` (avec curseur), utilisez `UNLINK` au lieu de `DEL` pour les grosses clés, découpez les grosses collections et paginez avec `HSCAN`/`SSCAN`.
- **Prévention :** Désactivez les commandes dangereuses (`rename-command KEYS ""` ou ACL), alertez sur les entrées du slowlog et vérifiez toute commande O(n) en revue de code.

</details>

### S4. Un bot demande des ids produit aléatoires et la base s'effondre malgré un taux de hit de 95 % {#cache-penetration-missing-ids}
- **Symptômes :** CPU de la base à 100 % ; presque toutes les requêtes sont des `SELECT … WHERE id = ?` qui renvoient zéro ligne ; le taux de hit des vrais utilisateurs est inchangé.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** **Pénétration du cache** : les ratés sur des clés inexistantes ne sont jamais mis en cache, donc chaque requête pour un faux id va en base. Les access logs montrent beaucoup d'ids distincts venant de quelques IP ou jetons.
- **Résolution :** Mettez en cache les résultats négatifs avec un TTL court (`product:999999 → NULL`, 60 s), validez le format de l'id en bordure et limitez le débit de l'appelant. Pour de très grands espaces d'ids, placez devant un **filtre de Bloom** des ids existants (RedisBloom `BF.EXISTS`).
- **Prévention :** Surveillez séparément le taux de ratés et le taux de « non trouvé », et appliquez un rate limit par client à la passerelle.

</details>

### S5. Un job nocturne « qui ne peut tourner qu'une fois » tourne deux fois et facture les clients en double {#redis-lock-two-holders}
- **Symptômes :** Deux pods journalisent `acquired lock billing-run` à environ 40 secondes d'écart ; le job dure 2 minutes ; le TTL du verrou est de 30 secondes.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le bail a expiré alors que le premier pod travaillait encore (job plus long que le TTL, ou pause GC). Le second pod a acquis le verrou légitimement. Un verrou Redis n'assure l'exclusion mutuelle que tant que le bail tient ([Q9](#redis-lock-redlock-debate)).
- **Résolution :** Remboursez les doublons. Rendez la facturation idempotente au niveau de la ressource : une contrainte d'unicité sur `(customer_id, billing_period)` pour que la seconde insertion échoue. Renouvelez le bail pendant le travail (un watchdog, comme Redisson) ou utilisez un verrou en base (`SELECT … FOR UPDATE SKIP LOCKED`, ShedLock sur une table).
- **Prévention :** Ne comptez jamais sur un verrou à bail seul pour la correction ; l'opération protégée doit être idempotente ou protégée par fencing. Alertez quand la durée du job approche le TTL du verrou.

</details>

### S6. Après un déploiement, chaque lecture du cache lève une `SerializationException` et le trafic retombe sur la base {#cache-serialization-after-deploy}
- **Symptômes :** `SerializationException` / `ClassCastException` sur les `GET` du cache juste après la mise en production ; la charge de la base triple ; le rollback « corrige », mais tout recasse au déploiement suivant.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** La classe mise en cache a changé de forme (champ renommé, package déplacé, `serialVersionUID` de la sérialisation JDK) et le nouveau code lit des entrées écrites par l'ancienne version. Pendant un déploiement progressif, les deux versions écrasent aussi les entrées l'une de l'autre.
- **Résolution :** Traitez une erreur de désérialisation comme un raté (éviction et rechargement) au lieu de faire échouer la requête, et incrémentez un **préfixe de version** dans le nom du cache (`v2:product:42`) pour que la nouvelle version utilise des clés neuves pendant que les anciennes expirent.
- **Prévention :** Utilisez JSON (Jackson avec `FAIL_ON_UNKNOWN_PROPERTIES` désactivé) plutôt que la sérialisation JDK, versionnez les préfixes de cache avec le schéma et préchauffez les clés chaudes au déploiement pour éviter un stampede à froid ([System Design S1](system-design.md#after-deploy-every-cache-entry)).

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q2. Quelles structures de données Redis utilisez-vous, et pour quoi ?
2. Q3. Comment fonctionnent TTL et éviction dans Redis, et quelle `maxmemory-policy` choisir ?
3. Q5. Qu'est-ce qu'un cache stampede, et comment l'éviter ?
4. Q6. Quels sont les pièges classiques de Spring Cache (`@Cacheable`) ?
5. Q7. Quand combiner un cache local et Redis, et comment les garder cohérents ?
6. Q8. Redis est-il durable ? Quand peut-on l'utiliser comme datastore principal ?
7. Q9. Comment construire un verrou avec Redis, et pourquoi Redlock fait-il débat ?
8. Q10. Sentinel ou Cluster : comment Redis passe-t-il à l'échelle et bascule-t-il ?
9. Q12. Comment garder le cache cohérent avec la base à grande échelle ?
10. S1. Après une mise à jour de prix, certains utilisateurs voient l'ancien prix pendant des heures

## 📌 Cheat-sheet

- **Où** — cachez aussi près de l'utilisateur que la confidentialité le permet. *Mesurez le taux de hit ; s'il est bas, c'est juste de la latence en plus.*
- **Éviction** — `allkeys-lru`/`lfu` pour un cache, `noeviction` pour des données. *Chaque clé de cache a un TTL.*
- **Écritures** — supprimez la clé **après commit**, ne la mettez pas à jour. *CDC ou clés versionnées à grande échelle.*
- **Stampede** — jitter du TTL, single-flight, rafraîchissement anticipé, servir du périmé. *Caffeine `refreshAfterWrite`.*
- **Pénétration** — cachez les résultats négatifs, filtre de Bloom. *Limitez le débit de l'appelant.*
- **Spring** — clés explicites, TTL par cache, sérialiseur JSON, pas d'auto-invocation. *`@CacheEvict` avant commit est une race.*
- **Exploitation** — mono-thread : pas de `KEYS`, pas de grosses clés, `UNLINK`, surveillez le `SLOWLOG`. *Séparez les instances cache et données.*
- **Verrous** — `SET NX PX` + jeton, libération en Lua. *Efficacité seulement ; la correction exige du fencing ou la base.*
- **Cluster** — 16 384 slots, hash tags pour le multi-clés. *Sentinel = HA, Cluster = montée en charge.*
