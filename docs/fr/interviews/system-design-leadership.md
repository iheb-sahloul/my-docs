# System Design & Leadership

## 🟢 Fondamentaux

### Approche de conception

#### Q1. Quelles deux questions posez-vous avant de commencer toute conception de système, et pourquoi passent-elles avant tout diagramme ?
« Que doit-il faire ? » (exigences fonctionnelles — s'inscrire, téléverser une photo, suivre un utilisateur, faire défiler un
fil, aimer/commenter) et « avec quel niveau de qualité doit-il le faire ? » (exigences non fonctionnelles — rapidité,
durabilité, échelle, disponibilité, coût). Elles viennent en premier parce que chaque décision d'architecture
ultérieure est un compromis fait *au service d'*une exigence non fonctionnelle précise —
on ne peut pas choisir de façon pertinente entre cohérence forte et cohérence à terme, ou entre un monolithe et
des microservices, sans connaître d'abord l'échelle réelle, le budget de latence et l'objectif de disponibilité ;
sauter directement au diagramme produit une conception optimisée pour des hypothèses que personne n'a demandées.

#### Q2. Quelle est la différence entre la conception de haut niveau (HLD) et la conception de bas niveau (LLD) ?
La HLD est la vue d'ensemble — les grandes pièces du système (serveurs d'application, base de données, cache, file, CDN)
et la façon dont les requêtes circulent entre elles. Concevoir Instagram au niveau HLD revient à se demander : où va la requête
d'un utilisateur, où les données sont-elles stockées, que se passe-t-il quand le trafic augmente, qu'est-ce qui casse en premier et
comment ce composant est-il mis à l'échelle ou rendu résilient. La LLD zoome sur une fonctionnalité précise et pose les
questions au niveau de l'implémentation : pour une fonctionnalité « like » en particulier — que se passe-t-il quand l'utilisateur
appuie sur like, quelle fonction/quel service le traite, comment vérifie-t-on que l'utilisateur a déjà aimé
le post, comment le like est-il persisté, comment le compteur de likes est-il mis à jour sans compter deux fois
le même utilisateur. Un entretien (et un vrai design doc) passe généralement de la HLD à une analyse approfondie d'un
ou deux composants au niveau LLD, plutôt que de rester entièrement à un seul niveau du début à la fin.

### Briques de base

#### Q3. Qu'est-ce qu'un load balancer, et quel problème précis résout-il ?
Quand un serveur unique manque de CPU/RAM pour absorber un trafic croissant, ajouter un autre serveur
n'aide que si les requêtes sont réellement réparties entre les deux — un load balancer se place devant
plusieurs serveurs et décide lequel traite chaque requête entrante (round-robin, least-
connections, ou des algorithmes plus sophistiqués), transformant « un serveur désormais surchargé » en
« N serveurs qui se partagent la charge », et retirant aussi de la rotation un serveur défaillant pour que le trafic ne
continue pas d'affluer vers quelque chose d'hors service. C'est le premier composant que la plupart des conceptions à mise à l'échelle horizontale
introduisent, car sans lui, ajouter des serveurs n'aide pas vraiment — rien n'y route le trafic.

#### Q4. Que signifie pour un service d'être stateless, et pourquoi est-ce important pour la mise à l'échelle et la résilience ?
Un service stateless ne conserve aucun état propre à une requête ou à un utilisateur **dans sa mémoire ou sur son disque local entre
les requêtes** : tout ce qui est nécessaire pour traiter une requête arrive avec elle (paramètres, un token) ou est récupéré depuis un store externe (une
base de données, un cache comme Redis, un stockage objet). N'importe quelle instance peut alors servir n'importe quelle requête, donc un load balancer peut répartir le trafic en
simple round-robin (Q3) — sans sticky sessions — et l'on peut ajouter des instances pour scale out, remplacer une instance plantée sans
perdre les données de personne, déployer avec des rolling updates et faire de l'autoscaling à la hausse comme à la baisse librement. L'état ne disparaît pas ; il migre vers la
couche conçue pour le conserver, là où la réplication, les sauvegardes et la cohérence sont gérées délibérément. Endroits typiques
où le statefulness s'infiltre : les sessions HTTP stockées dans la mémoire du serveur d'application (les déplacer vers un session store partagé ou utiliser un token signé), les fichiers écrits sur le disque
local (utiliser un stockage objet), les caches in-process qui diffèrent d'une instance à l'autre (l'accepter, ou utiliser un cache partagé), les jobs planifiés qui s'exécutent sur chaque réplique (S18
du module 2) et les connexions WebSocket, intrinsèquement stateful et qui nécessitent un backplane pub/sub partagé pour router les messages vers la bonne instance.
Le statelessness est une propriété à préserver partout où c'est peu coûteux, pas un absolu : les caches, les connection pools et l'état préchauffé sont acceptables tant que leur perte ne coûte que de la performance,
jamais de la correction.

#### Q5. Qu'est-ce que le caching, et quelle est l'idée de base de l'invalidation du cache ?
Le caching conserve une copie de données fréquemment demandées ou coûteuses à calculer dans une couche
d'accès plus rapide (en mémoire, plus proche du client) pour que les requêtes répétées sur les mêmes données ne répètent pas
à chaque fois le travail sous-jacent coûteux (une requête lente, un calcul lourd, un appel réseau).
L'invalidation en est la moitié la plus difficile : dès que des données en cache sont servies à la place de la source de vérité, le
cache doit être mis à jour ou expiré quand les données sous-jacentes changent, sinon les clients reçoivent des données périmées
indéfiniment — les stratégies de base (expiration par TTL, invalidation explicite à l'écriture, et les
patterns de lecture/écriture de la Q16) existent toutes parce que « on le met en cache et on l'oublie » sacrifie silencieusement
la correction au profit de la vitesse tant que l'invalidation n'est pas délibérément conçue.

#### Q6. Comment choisit-on entre une base relationnelle (SQL) et un store NoSQL lors de la conception d'un système ?
Partir des **patterns d'accès et des besoins de cohérence**, pas de l'effet de mode. Une base relationnelle est le choix par défaut pour
les données avec relations et invariants — commandes, paiements, inventaire — car elle offre des transactions ACID,
des contraintes, des jointures et des requêtes ad hoc que l'on n'avait pas prévues, et PostgreSQL moderne gère une très grande
échelle avec un primaire et des réplicas (Q13, Q10). NoSQL est une famille, et chaque type répond à une pression précise : un store
**clé-valeur/document** (DynamoDB, MongoDB, Redis) pour des lookups simples par clé à très grande échelle et une latence
prévisible, avec un schéma flexible ; un store **wide-column** (Cassandra) pour un très haut débit d'écriture sur plusieurs régions avec
une cohérence ajustable ; un **moteur de recherche** (Elasticsearch/OpenSearch) pour la recherche plein texte et à facettes ; un store **graphe** pour des données
fortement connectées ; un store **time-series** pour les métriques. Ce à quoi l'on renonce, c'est généralement la possibilité d'interroger autrement
que par le chemin d'accès prévu, les transactions multi-lignes et l'intégrité référentielle, et il faut modéliser les données *autour des
requêtes* (dénormaliser, dupliquer) et gérer soi-même l'incohérence qui en résulte. Une réponse pragmatique : commencer avec une base
relationnelle comme système de référence, ajouter un store spécialisé (un cache, un index de recherche, une base time-series) comme copie *dérivée* quand une exigence
mesurée l'impose, et ne choisir un NoSQL comme base principale que lorsqu'on peut nommer la raison précise — un volume d'écriture ou une taille de données qu'un
seul cluster relationnel ne peut pas porter, un pattern d'accès par clé qui n'aura jamais besoin de jointures, ou des écritures multi-régions globales. « Schema-less » n'est pas
un avantage en soi : le schéma existe toujours, dans le code de l'application, et c'est désormais là qu'on le fait respecter.

### Leadership

#### Q7. Qu'est-ce qui rend le feedback technique et le mentorat réellement efficaces, et pas seulement corrects ?
Un feedback efficace est spécifique (il pointe la ligne/la décision réelle, pas une impression générale),
opportun (donné près du moment où le travail a été fait, pas regroupé dans un vague commentaire trimestriel),
centré sur le travail et son impact plutôt que sur la personne, et — point crucial pour le mentorat
en particulier — il explique le *pourquoi* de la suggestion pour que la personne puisse la généraliser à la
situation suivante, et pas seulement corriger ce cas précis. La distinction avec « simplement correct » compte : un
commentaire techniquement exact, délivré d'une façon qui semble dédaigneuse ou purement critique, peut
être juste et pourtant échouer à son véritable objectif, qui est d'aider quelqu'un à développer un meilleur jugement au fil
du temps, pas seulement de faire corriger cette PR-là.

## 🟡 Pièges seniors

### Cohérence & réplication

#### Q8. Expliquez le théorème CAP avec un exemple concret — pourquoi un système distribué ne peut-il pas avoir les trois ?
**Réponse :** CAP énonce que pendant une partition réseau (P — une défaillance de communication entre
des nœuds, qui dans tout système distribué réel *finira* par arriver), un système doit choisir
entre Consistency (chaque lecture voit l'écriture la plus récente, ou une erreur) et Availability (chaque
requête reçoit une réponse, même si elle ne reflète pas forcément la dernière écriture) — on ne peut pas avoir les deux
pendant la partition, bien qu'on puisse avoir l'une des deux plus la tolérance au partitionnement. Un système CP (p. ex.
un store de configuration fortement cohérent comme ZooKeeper/etcd) refuse de servir une lecture/écriture du côté
minoritaire plutôt que de risquer de renvoyer des données périmées ou conflictuelles — il sacrifie la disponibilité à la
cohérence. Un système AP (p. ex. Cassandra dans sa configuration typique, ou un service de panier d'achat)
continue de servir des requêtes des deux côtés pendant la partition, en acceptant que les deux côtés puissent
brièvement diverger, pour être réconciliés une fois la partition résorbée — il sacrifie la cohérence stricte à la
disponibilité. Le point de niveau senior : c'est un compromis délibéré, fait système par système selon le mode de
défaillance qui est réellement le pire pour ce cas d'usage précis (un grand livre bancaire penche CP ; un bouton « ajouter au panier »
penche AP), et non une réponse « correcte » universelle.

**Exemple :**
```
Network link between region A and region B drops for 90 seconds.

CP system (etcd-style):
  region B (minority side) -> write request -> "unavailable: no quorum" (fails loudly)
  region A (majority side) -> keeps serving, single source of truth preserved

AP system (Cassandra-style, quorum relaxed to ONE):
  region A -> accepts writes locally
  region B -> also accepts writes locally
  partition heals -> both sides' writes get reconciled/merged, possibly with conflicts
```

**Pourquoi c'est un piège :** les candidats récitent « CAP signifie en choisir deux sur trois » comme une règle générale, mais
la tolérance au partitionnement n'est pas optionnelle dans un vrai système distribué — le choix réellement fait,
à chaque fois, est C contre A pendant la partition précisément, et une réponse senior nomme *quel mode de
défaillance précis* (une lecture périmée ou une requête rejetée) est le pire pour *ce* système, pas seulement le nom du
théorème.

#### Q9. Donnez un exemple concret et pratique où l'on choisit la cohérence à terme plutôt que la cohérence forte, et expliquez pourquoi c'est le bon choix dans ce cas.
**Réponse :** Un « nombre de likes » ou « nombre d'abonnés » sur un réseau social est le cas d'école : afficher un compteur
périmé de quelques secondes est tout à fait acceptable pour les utilisateurs, et l'alternative — une cohérence forte,
exigeant une lecture/écriture coordonnée sur chaque réplique pour chaque like — ajouterait une vraie latence et réduirait la disponibilité pour une donnée dont la péremption n'a
pratiquement aucun coût dans le monde réel. À l'inverse d'un solde de compte ou d'un stock au moment du paiement, où la même
péremption pourrait signifier une double dépense ou une survente d'un article en stock limité — ces opérations
justifient le coût en latence/disponibilité d'une cohérence plus forte (ou au minimum une vérification de cohérence
au moment exact de la transaction) précisément parce que le coût d'une erreur y est réel
et immédiat, contrairement à un compteur de likes.

**Exemple :**
```
Like count:       read from any replica, cached, off by a few -> nobody notices
Checkout balance:  read must reflect the latest committed write, or two concurrent
                    checkouts can both succeed against the same last unit of stock
```

**Pourquoi c'est un piège :** « cohérence à terme partout pour l'échelle » et « cohérence forte
partout par sécurité » sont tous deux de mauvais choix par défaut — la réponse senior choisit par type de donnée selon
le coût réel de la péremption pour ce champ précis, pas une politique uniforme pour tout le système.

#### Q10. Quelle est la différence entre la réplication de base de données synchrone et asynchrone, et que sacrifie chacune ?
**Réponse :** La réplication synchrone attend que la ou les répliques confirment avoir reçu et
appliqué une écriture avant de l'acquitter auprès du client — elle garantit que la réplique n'est jamais en retard sur le
primaire, au prix d'une latence d'écriture accrue (bornée par la réplique la plus lente) et d'une disponibilité réduite
(si la réplique est injoignable, l'écriture se bloque-t-elle ou échoue-t-elle ?). La réplication asynchrone
acquitte l'écriture dès que le primaire l'a, sans attendre les répliques — latence d'écriture plus faible, meilleure disponibilité, mais elle introduit
un replication lag : une réplique peut être sensiblement
en retard sur le primaire, et un failover vers cette réplique après la mort du primaire peut perdre les écritures les plus
récentes, non encore répliquées. La plupart des systèmes à grande échelle choisissent l'async par défaut pour le
bénéfice en latence/disponibilité, en acceptant le lag comme un compromis connu et surveillé, et réservent
la réplication synchrone aux données pour lesquelles perdre ne serait-ce que quelques secondes d'écritures récentes lors d'un
failover est réellement inacceptable.

**Exemple :**
```
Sync:  client -> primary -> [wait for replica ack] -> ack to client   (higher latency, no lag)
Async: client -> primary -> ack to client -> (replica catches up later)  (lower latency, lag window)

Primary fails during the lag window -> failover promotes the replica ->
any write the replica hadn't yet applied is gone.
```

**Pourquoi c'est un piège :** les candidats présentent souvent la réplication async comme strictement pire (« on peut perdre
des données ! ») sans nommer ce qu'elle apporte en échange — le piège fonctionne aussi dans l'autre sens : tout mettre
en synchrone « par sécurité » impose discrètement un coût de latence et de disponibilité à des données
qui n'avaient jamais besoin de cette garantie (voir Q9).

#### Q11. Pourquoi read-your-own-writes se brise-t-il sous réplication asynchrone, et comment le corriger pour les données qui en ont besoin ?
**Réponse :** Avec la réplication async (Q10), une écriture atterrit sur le primaire et est acquittée avant que
chaque réplique l'ait appliquée. Si la requête suivante du *même utilisateur* est une lecture routée vers une
réplique en retard — une configuration courante, puisque les lectures sont généralement réparties entre les répliques pour
le débit — elle peut renvoyer l'état d'avant l'écriture, donnant l'impression que l'action de l'utilisateur n'a pas
pris effet. C'est un bug réellement déroutant pour l'utilisateur (« je viens de sauvegarder, où est-ce passé ? »),
distinct d'un autre utilisateur qui voit des données périmées, ce qui est généralement tolérable. Correctifs : router les
lectures d'un utilisateur vers le primaire (ou une réplique connue comme à jour) pendant une courte fenêtre juste après
sa propre écriture ; passer un token/timestamp « read-your-own-writes » que le chemin de lecture compare au lag de la
réplique avant de répondre depuis une réplique ; ou, pour les champs concernés, faire afficher par le client
de façon optimiste ce qu'il vient d'écrire plutôt que de re-fetcher immédiatement.

**Exemple :**
```
t=0.00  user PATCHes /profile {bio: "new bio"} -> primary commits, acks -> client shows "saved"
t=0.05  client re-fetches /profile to confirm -> load balancer routes to replica-3
t=0.05  replica-3 hasn't applied the write yet -> returns bio: "old bio"
        user sees their own save appear to have been silently reverted
```

**Pourquoi c'est un piège :** on le confond facilement avec le « la cohérence à terme suffit pour les
données à faible enjeu » de la Q9 — mais l'enjeu ici ne tient pas à l'importance de la donnée, il tient à *qui* lit :
une péremption vue par un autre utilisateur est généralement invisible et acceptable, alors qu'une péremption vue par
l'*auteur* juste après sa propre écriture passe pour une fonctionnalité cassée.

#### Q12. Two-phase commit vs sagas — comment garde-t-on des données cohérentes entre plusieurs services sans base de données partagée ?
**Réponse :** Le **two-phase commit (2PC)** coordonne une transaction atomique unique sur plusieurs ressources : un coordinateur demande à chaque participant de
*prepare* (voter oui, en conservant les verrous), et ce n'est que si tous votent oui qu'il leur dit de *commit*. Il donne une forte atomicité mais à un
prix : les participants conservent des verrous pendant le protocole, donc le débit et la disponibilité chutent ; le coordinateur est un point unique dont la défaillance entre les phases laisse
les participants **bloqués dans le doute** ; et il exige que chaque participant le supporte (XA), ce que la plupart des message brokers, API SaaS et stores NoSQL ne font pas.
Une **saga** remplace une transaction distribuée par une séquence de transactions locales, chacune publiant un événement ou une commande qui déclenche la suivante ; si une
étape échoue, les étapes déjà terminées sont défaites par des **actions compensatoires** (rembourser le paiement, libérer le stock réservé) plutôt que rollbackées. Elle peut être
**chorégraphiée** (les services réagissent aux événements des autres — simple pour peu d'étapes, difficile à suivre quand ça grossit) ou **orchestrée** (un coordinateur détient l'état du workflow — plus facile à
raisonner, superviser et soumettre à des timeouts). Les conséquences à prévoir : les sagas sont **à cohérence à terme**, avec des états intermédiaires visibles par d'autres requêtes (une commande « pending » pendant un moment) ; les compensations doivent être
**idempotentes** et peuvent elles-mêmes échouer (retry, puis alerter un humain) ; certaines actions ne peuvent pas être annulées (un email envoyé, un colis expédié), donc ordonner les étapes pour placer les
irréversibles en dernier ; et chaque étape et son événement doivent être publiés de façon fiable avec un outbox (module 4 Q26) pour qu'un crash entre « write » et « publish » ne bloque pas la saga. En pratique : préférer éviter la
transaction distribuée en gardant les données fortement couplées dans un seul service (Q22), utiliser des sagas pour les vrais processus métier inter-services, et n'utiliser le 2PC qu'au sein d'une seule
plateforme de confiance où tous les participants le supportent et où la latence est acceptable.

**Exemple :**
```text
Order saga (orchestrated):
  1. Orders:    create order PENDING                  compensation: mark CANCELLED
  2. Payments:  charge card                            compensation: refund
  3. Inventory: reserve stock                          compensation: release stock
  4. Shipping:  create shipment (irreversible - last)  compensation: n/a
  step 3 fails  ->  refund (2), cancel order (1); each compensation is idempotent and retried
```

**Pourquoi c'est un piège :** les candidats répondent « on utilise des transactions distribuées » (un problème de disponibilité) ou « on utilise une saga » sans mentionner l'échec des compensations, l'idempotence, la visibilité des états
intermédiaires ni l'outbox — et les affirmations « exactly-once » entre services cachent presque toujours du *at-least-once delivery plus traitement idempotent* (module 4 Q15).

### Scaling & caching

#### Q13. Mise à l'échelle horizontale vs verticale — quel est le vrai compromis ?
**Réponse :** La mise à l'échelle verticale (une machine plus grosse — plus de CPU/RAM sur le même nœud) est plus simple (pas de
complexité de systèmes distribués, pas de partitionnement de données à raisonner) mais a un plafond dur
(il existe une plus grosse machine achetable) et un point unique de défaillance. La mise à l'échelle horizontale (plus de
machines) n'a pas de plafond pratique et améliore la tolérance aux pannes, mais introduit une vraie complexité :
load balancing, cohérence des données entre nœuds, latence réseau entre des composants qui étaient auparavant des appels
in-process, et surcharge opérationnelle. La réponse pratique à laquelle aboutissent la plupart des systèmes : monter
verticalement aussi loin que c'est raisonnable pour la simplicité, et recourir à l'horizontal quand
le plafond du vertical ou le risque de point unique de défaillance devient la contrainte réelle, pas par défaut
dès le premier jour pour un système qui n'en a pas encore besoin.

**Exemple :**
```
Vertical: db.small -> db.large -> db.2xlarge -> db.8xlarge -> ... -> biggest instance money buys
          one machine, one failure domain, zero coordination code

Horizontal: 1 node -> 3 nodes -> 20 nodes -> ...
          needs: a load balancer, a partitioning/sharding scheme, replica consistency,
          and monitoring for N failure domains instead of one
```

**Pourquoi c'est un piège :** « il suffit de scaler horizontalement, c'est plus moderne » est la réponse naïve — un candidat
senior nomme la complexité réelle qu'achète la mise à l'échelle horizontale (partitionnement, cohérence, surcharge
opérationnelle) au lieu de la traiter comme une mise à niveau gratuite, et sait dire clairement quand la mise à l'échelle verticale reste
le bon choix.

#### Q14. Comment choisit-on une clé de sharding de base de données, et que se passe-t-il avec un mauvais choix ?
**Réponse :** Une clé de sharding détermine sur quel shard physique vit une ligne donnée (généralement via un hash
de la clé, ou un partitionnement par plage sur celle-ci) — l'objectif est de répartir à la fois le volume de données et, surtout,
la *charge de requêtes/écritures* uniformément entre les shards. Un mauvais choix crée un « hot shard » : choisir
une clé à faible cardinalité (p. ex. sharder par `country` alors que 80 % des utilisateurs sont dans un seul pays) ou une clé
corrélée à un biais du pattern d'accès (un petit nombre de comptes générant une part disproportionnée
de toute l'activité) place l'essentiel de la charge réelle sur un seul shard, peu importe l'uniformité de la répartition du
*stockage*. Corriger une mauvaise clé de sharding après coup (re-sharder un système en production avec des
données déjà inégalement réparties) est l'une des migrations les plus pénibles sur le plan opérationnel dans les
systèmes distribués, ce qui explique précisément pourquoi le choix mérite un vrai examen avant que le système ne soit
construit autour.

**Exemple :**
```
Sharded by `country`: 4 shards, one per region
  shard(US) -> 80% of all users and all traffic  <- hot shard
  shard(NZ), shard(IS), shard(LU) -> nearly idle

Cluster-wide CPU on the main dashboard reads "35% utilized" while shard(US) sits at 95%.
```

**Pourquoi c'est un piège :** les métriques agrégées du cluster masquent complètement un hot shard — un candidat qui se contente de
vérifier « le cluster est-il en surcapacité » rate le symptôme réel en production, qui se manifeste par la dégradation de la latence d'un seul
shard alors que la moyenne sur toute la flotte a encore l'air saine.

#### Q15. Qu'est-ce que le consistent hashing, et pourquoi l'utilise-t-on pour les caches distribués et le sharding plutôt que le simple hashing modulo ?
**Réponse :** Le simple hashing modulo (`hash(key) % N` pour choisir un serveur parmi N) pose un grave problème
quand N change (un serveur est ajouté ou retiré) : le serveur assigné à presque toutes les clés change aussi,
parce que le modulo lui-même a changé — pour un cache distribué, cela signifie qu'un changement de nœud invalide
presque tout le cache d'un coup (un « cache stampede » qui frappe la base de données simultanément, S2).
Le consistent hashing place serveurs et clés sur un anneau conceptuel, et chaque clé appartient au
serveur suivant dans le sens horaire sur l'anneau — ajouter ou retirer un serveur ne remappe que les clés
tombant précisément entre lui et son voisin, laissant la grande majorité des assignations clé-serveur
inchangées.

**Exemple :**
```
Modulo, N=4->5 servers:  hash(key) % 4  vs  hash(key) % 5  -> ~80% of keys remap

Consistent hashing, ring with a 5th server added:
  only the keys between the new server and its counter-clockwise neighbor move
  -> roughly 1/5 of keys remap, not 4/5
```

**Pourquoi c'est un piège :** les candidats savent généralement expliquer le problème du hashing modulo mais s'arrêtent avant le
mécanisme qui le corrige — « le consistent hashing aide » sans la mécanique d'anneau/voisin est un nom
sans explication, et la relance d'un intervieweur (« pourquoi seul ce sous-ensemble bouge-t-il ? ») expose
immédiatement la lacune.

#### Q16. Citez les principales stratégies d'invalidation/d'écriture de cache et leurs compromis — « il n'y a que deux choses difficiles en informatique. »
**Réponse :** **Cache-aside** (lazy loading) : l'application vérifie d'abord le cache, et en cas de miss,
lit dans la base de données et alimente le cache — simple, mais la première requête pour n'importe quelle clé est
toujours un miss lent, et il y a un vrai risque de servir des données périmées jusqu'à l'expiration du TTL ou une
invalidation explicite. **Write-through** : chaque écriture va au cache et à la base de données ensemble,
de façon synchrone — garde le cache toujours cohérent, au prix d'une latence d'écriture accrue et de la mise en cache de
données qui ne seront peut-être jamais lues. **Write-behind (write-back)** : les écritures vont au cache
immédiatement et sont vidées de façon asynchrone vers la base de données plus tard — écritures les plus rapides, mais risque de perte
de données si le cache tombe avant le flush. L'expiration par TTL est souvent superposée à n'importe laquelle d'entre elles
comme simple filet de sécurité, bornant l'âge que peuvent atteindre les données périmées même si l'invalidation explicite est oubliée.

**Exemple :**
```python
# Cache-aside
def get_user(id):
    if (u := cache.get(id)) is not None:
        return u
    u = db.query(id)
    cache.set(id, u, ttl=300)
    return u
```

**Pourquoi c'est un piège :** « il suffit d'ajouter un cache » sans nommer laquelle de ces trois stratégies, ni son
compromis précis en péremption/latence, est le véritable anti-pattern contre lequel met en garde la blague classique —
le signal en entretien est de choisir une stratégie délibérément selon le ratio lecture/écriture concerné,
et non de réciter les trois comme des choix par défaut équivalents.

#### Q17. Que résout réellement un CDN, et quand n'aide-t-il pas ?
**Réponse :** Un CDN met en cache du contenu sur des points de présence (edge) géographiquement proches des utilisateurs finaux, réduisant
la latence et déchargeant le serveur d'origine du trafic pour du contenu identique pour tous les utilisateurs.
Il est très efficace pour le contenu statique ou peu changeant (images, bundles JS/CSS, vidéo)
et, avec la bonne configuration de cache-control, même pour du contenu semi-dynamique identique
pour tous les utilisateurs pendant une courte fenêtre. Il n'aide *pas* pour du contenu réellement dynamique, par utilisateur et en temps
réel — le mettre en cache à l'edge sert soit des données périmées/erronées au mauvais utilisateur, soit exige une
clé de cache si granulaire qu'elle cesse complètement de fonctionner comme un cache partagé.

**Exemple :**
```
Cache-Control: public, max-age=86400          # product image — great CDN hit rate
Cache-Control: private, no-store               # "your account balance" — must not be cached
Cache-Control: private, max-age=0, must-revalidate  # personalized feed — edge can't help here
```

**Pourquoi c'est un piège :** « mets un CDN devant » est proposé comme correctif de performance par défaut même pour
des endpoints intrinsèquement par utilisateur — le piège est de traiter le CDN comme de la vitesse gratuite au lieu de
vérifier d'abord si la réponse est réellement partageable entre les requêtes.

### Fiabilité

#### Q18. Quel est le piège de l'idempotency key quand un client retente une écriture après un timeout ?
**Réponse :** Un client envoie une écriture (p. ex. « passer commande »), le serveur la traite et commit, mais
la réponse est perdue en route ou le client expire avant qu'elle n'arrive — du point de vue du client,
le résultat de la requête est inconnu, donc un client naïf retente exactement la même requête.
Sans mécanisme explicite pour reconnaître « c'est la même requête logique, pas une nouvelle », le
retry exécute l'écriture une seconde fois — une deuxième commande, un deuxième prélèvement. Le correctif est une
idempotency key : le client génère une clé unique par opération logique (pas par tentative HTTP)
et l'envoie à chaque tentative ; le serveur persiste la clé avec le résultat de la première
exécution réussie et, en voyant une clé répétée, renvoie le résultat stocké au lieu de
ré-exécuter l'écriture. Cela doit être garanti par une contrainte d'unicité au niveau de la couche de stockage,
et pas seulement par une vérification en mémoire, sinon une course entre deux retries quasi simultanés peut encore laisser passer les deux.

**Exemple :**
```
POST /orders
Idempotency-Key: 7f3a9c21-...   <- same key on every retry of THIS logical request

Attempt 1: times out client-side after the server already committed the order
Attempt 2 (retry, same key): server finds the key already recorded -> returns the
                              original order's result, does NOT insert a new row

CREATE UNIQUE INDEX ON idempotency_keys (key);  -- the actual enforcement point
```

**Pourquoi c'est un piège :** « il suffit de retenter sur timeout, c'est plus sûr que de perdre la requête » est l'instinct —
vrai pour les lectures, faux pour les écritures sans idempotence, et un candidat qui dit « il suffit de retenter »
sans nommer le risque d'écriture en double n'a pas vraiment réfléchi à ce que « timeout » signifie : la
requête a très bien pu réussir côté serveur sans que le client ne l'ait jamais su.

#### Q19. Comment le backpressure et le load shedding maintiennent-ils un système surchargé en vie, et que se passe-t-il sans eux ?
**Réponse :** Tout système a un débit maximal ; quand le taux d'arrivée le dépasse, le travail s'accumule dans des files (thread pools, backlogs de connexions, files de messages), la **latence croît sans limite**, la mémoire se remplit, les timeouts se déclenchent, les clients retentent, et les retries ajoutent *encore plus* de
charge — un effondrement auto-renforcé dont le système ne peut souvent pas se relever même après la fin du pic initial (une « metastable failure » ; voir S20). Deux
mécanismes l'empêchent. Le **Backpressure** repousse la limite en amont : des files bornées qui bloquent ou rejettent quand elles sont pleines, un consommateur qui signale ce qu'il peut absorber
(demande des reactive streams, fenêtres TCP, modèle pull de Kafka), et un producteur qui ralentit. Le **Load shedding** rejette délibérément le surplus tôt et à peu de frais —
renvoyer `429`/`503` avec `Retry-After` immédiatement — pour que les requêtes acceptées soient servies vite ; prioriser par importance (health checks et clients payants avant le trafic batch) et rejeter
d'abord le *moins précieux*. Pratiques complémentaires : des **timeouts** sur chaque appel distant (plus courts que le timeout de l'appelant lui-même, une deadline propagée
en aval), des **retries avec backoff exponentiel et jitter** et un budget de retries, des **circuit breakers** pour cesser d'appeler une dépendance défaillante, des **bulkheads**
(pools séparés pour qu'une dépendance lente ne puisse pas consommer tous les threads), et l'autoscaling comme *complément* — il réagit en minutes, alors que la surcharge
arrive en secondes. Les files non bornées sont l'anti-pattern : elles transforment la surcharge en latence invisible puis finalement en crash out-of-memory.

**Exemple :**
```java
// Bounded work queue: when full, reject immediately instead of queueing forever.
ThreadPoolExecutor pool = new ThreadPoolExecutor(
    16, 16, 0, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(200),                    // bounded: at most 200 waiting
    new ThreadPoolExecutor.AbortPolicy());            // -> RejectedExecutionException

@PostMapping("/reports")
ResponseEntity<?> create(@RequestBody ReportRequest r) {
    try {
        pool.execute(() -> reports.generate(r));
        return ResponseEntity.accepted().build();
    } catch (RejectedExecutionException e) {
        return ResponseEntity.status(503).header("Retry-After", "5").build();   // shed load early
    }
}
```

**Pourquoi c'est un piège :** les équipes traitent la capacité comme « ajouter des serveurs » et laissent chaque file non bornée, si bien que le premier pic de trafic
ou la première dépendance lente se convertit en minutes de latence et en une panne qui dure plus longtemps que le déclencheur. Échouer vite sous surcharge paraît une
expérience utilisateur pire dans une démo, mais c'est ce qui garde le service disponible pour les requêtes qu'il peut servir.

#### Q20. Pourquoi un lock distribué (Redis `SET NX`, ZooKeeper, ligne de base de données) n'est-il pas aussi sûr qu'il en a l'air, et que sont les fencing tokens ?
**Réponse :** Un lock est censé garantir qu'un seul worker à la fois effectue une action sur une ressource. Dans un système distribué, le détenteur du lock
peut *se tromper en croyant le détenir encore* : le lock est acquis avec un **TTL** (pour qu'un détenteur planté ne bloque pas tout le monde indéfiniment), mais une longue pause GC, une VM bloquée ou un
réseau lent peuvent amener le détenteur à continuer à travailler après l'expiration du bail — alors qu'un second worker a acquis le lock et travaille aussi. Les deux
écrivent alors, et la garantie a silencieusement disparu. Le décalage d'horloge et le failover du service de lock lui-même (un primaire Redis qui plante avant de
répliquer la clé du lock) produisent le même effet. Vérifier « détiens-je encore le lock ? » juste avant d'écrire n'y remédie pas, car la pause peut survenir entre la vérification et l'écriture. Le
correctif robuste est un **fencing token** : le service de lock distribue un nombre strictement croissant à chaque attribution ; le worker envoie le token avec chaque écriture
vers la ressource protégée, et c'est la *ressource* qui rejette toute écriture portant un token inférieur à un token déjà vu. Cela déplace la garantie de correction du détenteur du lock (peu fiable)
vers la ressource (faisant autorité). Là où un fencing token n'est pas possible, concevoir l'action pour qu'elle soit **idempotente** (Q18) ou rendre l'écriture conditionnelle
(`UPDATE ... WHERE version = ?`, optimistic locking), ce qui est souvent une alternative plus simple à un lock. Utiliser les locks pour l'*efficacité* (éviter le travail en double) plutôt que pour la *correction*
sauf si l'on a du fencing ; pour une vraie exclusion mutuelle, préférer les verrous de ligne/contraintes d'unicité propres à la base de données, ou un système basé sur le consensus (etcd/ZooKeeper) avec fencing.

**Exemple :**
```text
worker A: acquires lock, token=33   ── long GC pause ──────────────► writes (token=33)  REJECTED
lock TTL expires
worker B: acquires lock, token=34 ──► writes (token=34) OK   (storage remembers max token = 34)

storage rule:  if request.token < max_seen_token: reject
```
```sql
-- Optimistic alternative: the write only succeeds if nobody changed the row meanwhile.
update accounts set balance = :new, version = version + 1
where id = :id and version = :expected_version;      -- 0 rows updated -> conflict, retry
```

**Pourquoi c'est un piège :** `SET key value NX PX 30000` dans un exemple de code ressemble à un mutex, et la défaillance
n'apparaît que lors de la rare pause ou du failover qui n'arrive jamais dans les tests — alors deux workers facturent deux fois un client ou corrompent un fichier. La défense consiste à cesser de
faire confiance à l'avis du détenteur du lock sur le lock.

#### Q21. Que signifient RTO et RPO dans la planification de la reprise après sinistre, et comment guident-ils les décisions d'architecture ?
**Réponse :** **RTO (Recovery Time Objective)** : combien de temps le système peut être indisponible avant que l'impact
métier ne devienne inacceptable — guide les décisions sur l'automatisation du failover et l'infrastructure de secours.
**RPO (Recovery Point Objective)** : quelle perte de données (mesurée en temps) est acceptable — guide
les décisions de réplication et de fréquence de sauvegarde. Les deux sont des décisions métier, pas purement techniques
— le travail d'un architecte est de traduire un RTO/RPO énoncé en mécanisme technique concret
qui l'atteint réellement, et de challenger si un objectif énoncé (p. ex. « zéro perte de données, zéro
interruption ») exigerait un coût ou une complexité disproportionnés par rapport au besoin métier réel qui le
motive.

**Exemple :**
```
RTO = 5 min   -> needs automated failover to a hot standby, health checks, auto-promotion
RPO = 0       -> needs synchronous replication for the affected data (Q10), not async
RTO = 4 hours -> a documented manual runbook and a warm (not hot) standby is enough
```

**Pourquoi c'est un piège :** les candidats proposent parfois la configuration la plus robuste possible (multi-région
synchrone, tout automatisé) sans tenir compte des objectifs énoncés — sur-construire face à un
RTO/RPO plus souple que ce dont le métier a réellement besoin a son propre coût réel, ce n'est pas un choix par défaut sûr.

### Architecture & sécurité

#### Q22. Quand un monolithe est-il préférable aux microservices, et quel est le vrai coût de choisir les microservices trop tôt ?
**Réponse :** Un monolithe est le meilleur choix par défaut pour une petite équipe, un produit en phase initiale avec un
modèle de domaine évolutif/flou, ou un système où la surcharge opérationnelle des systèmes distribués
n'est pas encore justifiée par un besoin organisationnel ou de mise à l'échelle réel. Le coût réel des
microservices prématurés : découper un système selon des frontières qui s'avèrent fausses (les vraies frontières
du domaine n'étaient pas encore comprises) est bien plus coûteux à défaire à travers des frontières réseau et
des déploiements séparés que de refactorer les frontières de modules au sein d'une seule base de code — et une petite équipe porte désormais
aussi toute la charge opérationnelle d'un système distribué pour une échelle et une
structure organisationnelle qui n'en avaient pas encore besoin. Les microservices méritent leur coût précisément quand la propriété indépendante par
équipe, le déploiement indépendant et la mise à l'échelle indépendante deviennent de véritables contraintes, ressenties aujourd'hui.

**Exemple :**
```
Year 1, 4-person team splits into "user-service", "order-service", "notification-service" —
the actual bounded contexts weren't known yet, so "order" needs "user" data on every
request: a chatty network call replaces what used to be one in-process join, and the team
now debugs 3 deployments instead of 1 for every feature.
```

**Pourquoi c'est un piège :** « les microservices sont le choix scalable/moderne » est proposé comme choix par défaut — une
réponse senior nomme la contrainte *précise*, ressentie aujourd'hui, qui justifie le découpage, et n'hésite pas
à dire qu'un monolithe est la bonne réponse pour une équipe qui n'a pas encore cette contrainte.

#### Q23. Que centralise une API Gateway, et pourquoi la placer devant une architecture de microservices ?
**Réponse :** Une API Gateway se place comme point d'entrée unique devant un ensemble de services backend,
centralisant des préoccupations qui devraient sinon être dupliquées dans chaque service individuel :
l'authentification/autorisation, le rate limiting, le routage des requêtes, la traduction de protocole, et souvent
l'agrégation de réponses. Le compromis : c'est un nouveau point unique qui, s'il tombe, peut couper
l'accès à chaque service derrière lui — ce qui explique pourquoi la disponibilité/redondance de la gateway est traitée avec
le même sérieux que tout autre composant réellement critique du chemin, et pourquoi la logique de la gateway elle-même
doit rester mince (routage et préoccupations transverses) plutôt que d'accumuler de la vraie
logique métier.

**Exemple :**
```
client -> [API Gateway: authn, rate-limit, route] -> user-service
                                                    -> order-service
                                                    -> notification-service

Gateway goes down -> every service behind it becomes unreachable, even though each
individual service is still healthy on its own.
```

**Pourquoi c'est un piège :** les candidats proposent une gateway comme un pur avantage (l'auth en un seul endroit !) sans
nommer le SPOF qu'elle introduit — la relance à anticiper est « que se passe-t-il quand la gateway
elle-même tombe », ce qui explique précisément pourquoi la redondance de la gateway est traitée aussi sérieusement que les
services qu'elle protège.

#### Q24. Citez plusieurs risques de l'OWASP Top 10 et comment vous atténuez chacun au niveau de la conception du système.
**Réponse :** **Injection** (SQL, commande) : requêtes paramétrées/prepared statements, jamais
d'entrée concaténée sous forme de chaîne dans une requête. **Broken authentication** : politiques de mots de passe robustes, MFA,
gestion de session sécurisée, ne pas réinventer sa propre crypto/auth. **Sensitive data exposure** : chiffrer
les données en transit (TLS) et au repos, ne pas journaliser les champs sensibles, minimiser ce qui est collecté/conservé
dès le départ. **Broken access control** : appliquer l'autorisation côté serveur à chaque requête
(ne jamais se fier à une seule vérification côté client), deny par défaut plutôt qu'allow par défaut. **Security
misconfiguration** : pas d'identifiants par défaut, surface exposée minimale, dépendances patchées.
**Cross-site scripting (XSS)** : échapper/assainir toute entrée utilisateur restituée dans du HTML, utiliser l'
échappement intégré d'un framework plutôt qu'une interpolation de chaînes artisanale dans le markup.
**Insecure deserialization** : ne jamais désérialiser une entrée non fiable vers des types arbitraires sans
validation stricte. Le point au niveau conception du système : la sécurité est un ensemble de décisions de frontière
délibérées (où l'entrée est-elle validée, où la sortie est-elle échappée, où l'autorisation est-elle appliquée)
intégrées à l'architecture, et non une checklist appliquée après coup.

**Exemple :**
```java
// Injection — vulnerable:
String sql = "SELECT * FROM users WHERE email = '" + input + "'"; // attacker: ' OR '1'='1

// Fixed — parameterized, input is always data, never concatenated into the query text:
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE email = ?");
ps.setString(1, input);
```

**Pourquoi c'est un piège :** les candidats énumèrent bien les risques mais les traitent comme une checklist à mentionner, pas comme des
frontières autour desquelles concevoir — la relance qui sépare vraiment une réponse senior est « où dans
l'architecture cela est-il appliqué, et un appelant peut-il contourner cette couche » (une vérification d'autorisation
uniquement côté client est la version la plus courante de cette lacune en pratique).

#### Q25. Comment abordez-vous l'estimation de capacité « back-of-envelope » dans un entretien de system design ?
**Réponse :** Partir de l'échelle donnée (ou raisonnablement supposée, énoncée explicitement) — utilisateurs actifs quotidiens,
requêtes par utilisateur et par jour — et en déduire les requêtes par seconde, en étant explicite sur le
ratio pic/moyenne (une hypothèse simplificatrice courante est pic ≈ 2-3x la moyenne). À partir de là,
estimer le stockage (taille moyenne par enregistrement × enregistrements par jour × durée de rétention) et la bande passante
(requêtes/sec × taille moyenne de la charge utile). L'intérêt de le faire à voix haute n'est pas la précision — c'est de
montrer que les décisions d'architecture ultérieures (faut-il sharder, faut-il un CDN, une
seule instance de base de données est-elle seulement plausible) reposent sur de vrais chiffres plutôt que sur des impressions.

**Exemple :**
```
10M DAU, 20 requests/user/day -> 200M req/day -> ~2,300 req/sec average
Peak ~3x average -> ~7,000 req/sec peak -> this number decides whether one DB instance
                                             is even plausible before drawing anything
```

**Pourquoi c'est un piège :** les candidats soit sautent complètement cette étape, soit la font si discrètement qu'elle
n'informe pas la conception — le piège est de la traiter comme une case à cocher plutôt que comme un chiffre qui devrait
visiblement changer une décision en aval (sharding, caching, CDN) au cours du même entretien.

### Leadership

#### Q26. Un ingénieur junior commet sans cesse la même catégorie d'erreur malgré des commentaires de code review répétés. Quelle est votre approche concrète ?
**Réponse :** D'abord, vérifier si les retours jusqu'ici ont réellement expliqué le principe sous-jacent
ou se sont contentés de corriger le cas précis à chaque fois — répéter « corrige ça » sans le « pourquoi »
réutilisable qui l'accompagne enseigne à reconnaître le motif de ce seul commentaire de review, pas le
jugement généralisable qui préviendrait le *cas suivant*. Avoir une conversation directe et privée — passer
en revue deux ou trois vrais exemples ensemble, lui demander d'articuler le principe sous-jacent
avec ses propres mots, et convenir de quelque chose de concret à essayer différemment à l'avenir. Si le schéma
persiste après une conversation réellement claire et directe, c'est le signal d'impliquer son
manager — mais le premier geste est toujours une vraie conversation axée sur la compréhension, pas une
escalade.

**Exemple :**
```
PR comment pattern (3 PRs in a row): "missing null check on line 42"
                                       "missing null check on line 88"
                                       "missing null check on line 15"
-> each was fixed individually, none explained *why* this class of input can be null here,
   or how to recognize the pattern before writing the code, not just after review flags it.
```

**Pourquoi c'est un piège :** l'instinct sous la pression de l'entretien est « je continuerais à laisser des commentaires de review
clairs » — la question teste précisément si le candidat reconnaît que des commentaires corrects répétés qui ne portent pas
sont le signe que l'intervention elle-même doit changer, et non se répéter.

#### Q27. Comment contestez-vous une décision technique venant d'une partie prenante senior ou d'un manager que vous jugez erronée ?
**Réponse :** Commencer par une vraie curiosité sur leur raisonnement avant d'affirmer le vôtre — ils peuvent
avoir un contexte que vous n'avez pas (une contrainte métier, une tentative échouée antérieure, une pression de calendrier qui
change le calcul). Énoncer votre préoccupation de façon concrète et précise (le risque ou le coût réel,
idéalement avec une quantification approximative), proposer une alternative précise plutôt que de seulement soulever une
objection, et être explicite sur ce qu'il faudrait voir pour vous faire changer d'avis. Si, après cette
conversation, la décision va tout de même dans l'autre sens et qu'il ne s'agit pas d'un enjeu critique de correction ou de sécurité,
le geste de niveau senior est de s'engager pleinement dans la direction décidée plutôt que de la remettre
sans cesse en cause — « disagree and commit », réservé aux désaccords réellement non critiques.

**Exemple :**
```
Weak pushback:   "I don't think we should do it this way."
Strong pushback: "This approach adds ~2 weeks of migration risk because it touches the
                  payments schema live. If we instead do X, we lose feature Y for one
                  release but avoid that risk. What would need to be true for the
                  original approach to still be right?"
```

**Pourquoi c'est un piège :** un désaccord vague (« j'ai des inquiétudes ») passe pour de la friction sans substance —
le piège est de s'arrêter à soulever une objection au lieu de l'associer à un coût concret et à une
alternative concrète, ce qui rend la contestation persuasive plutôt que simplement notée.

#### Q28. En tant que tech lead, comment gérez-vous une design review où deux ingénieurs seniors sont fortement en désaccord ?
**Réponse :** Séparer d'abord le désaccord des personnes — s'assurer que les deux se sentent
réellement écoutés, puis faire écrire les deux positions assez concrètement pour les comparer sur les mêmes
axes (que optimise chaque approche, que coûte chacune, dans quel scénario futur
chacune se révélerait avoir été le meilleur choix). Chercher à savoir s'il s'agit d'une décision dont la
bonne réponse est connaissable et atteignable avec plus d'information (un spike, un benchmark) ou d'un vrai compromis de valeurs/
priorités sans réponse objectivement correcte — le premier cas se résout en obtenant l'information
manquante ; le second est un jugement qui a finalement besoin d'un responsable pour trancher, une fois
les deux côtés pleinement entendus, plutôt que d'être laissé à pourrir comme une impasse non résolue.

**Exemple :**
```
Position A: "Event-sourced — full audit trail, but higher complexity, 3 extra weeks."
Position B: "CRUD + audit table — simpler, ships now, harder to replay history later."

Resolvable by a spike? No — it's a genuine priority trade-off (audit depth vs. time-to-ship)
-> tech lead names the priority for this project explicitly, makes the call, explains why.
```

**Pourquoi c'est un piège :** chercher un consensus total sur un vrai compromis de valeurs peut bloquer un
projet indéfiniment — le piège est de traiter « faire s'accorder tout le monde » comme l'objectif au lieu de « faire
prendre la décision, l'expliquer et en porter la responsabilité », ce dont une review bloquée a réellement besoin.

#### Q29. Comment cadrez-vous et estimez-vous un projet à très forte incertitude pour des parties prenantes qui veulent une date ferme ?
**Réponse :** Être explicite sur le fait qu'une estimation ponctuelle unique pour un projet très incertain est en soi un
mensonge déguisé en précision — communiquer plutôt une fourchette fondée sur les sources réelles
d'incertitude (préciser ce qui est inconnu : une intégration tierce peu familière, une
exigence floue, une dépendance envers un travail non livré d'une autre équipe). Proposer une façon concrète de *réduire*
l'incertitude tôt — un court spike time-boxé sur l'inconnue la plus risquée avant de s'engager sur une
estimation complète. Découper le projet en jalons avec leurs propres points de contrôle, afin que la partie prenante
obtienne un vrai signal sur la conformité du projet à l'estimation bien avant la
date finale.

**Exemple :**
```
"3-5 weeks. The 2-week spread is entirely the unfamiliar payment-provider integration —
 we haven't confirmed their sandbox supports partial refunds yet. We'll spike that in
 week 1 and can tighten the estimate to +/- 2 days by end of week 1."
```

**Pourquoi c'est un piège :** céder à la pression pour une fausse date précise unique, ou refuser totalement d'estimer,
sont tous deux pires qu'une fourchette avec une cause nommée — le piège est de traiter « donne-moi une date ferme »
comme une demande à laquelle il faut répondre par une date ferme, plutôt que de la recadrer autour de ce qui
génère réellement l'incertitude.

## 🔴 Expert / Ouvert

### Exercices de conception

#### Q30. Concevez le feed d'Instagram à haut niveau, puis approfondissez un composant.
**Réponse :** Exigences fonctionnelles : publier une photo, suivre des utilisateurs, voir un fil de posts des
comptes suivis, aimer/commenter. Non fonctionnelles : forte lecture (bien plus de consultations du fil que de posts), la génération
du fil doit être rapide, cohérence à terme acceptable pour les compteurs de likes et même pour la fraîcheur du fil
dans une petite fenêtre. HLD : un service de posts gérant les uploads (métadonnées dans une base de données, l'image dans
un stockage objet, servie via CDN) ; un service de graphe social suivant les relations de follow ; et une approche
de génération du fil — le point d'approfondissement naturel. Le **Fan-out on write** (quand un utilisateur publie, pousser
le post immédiatement dans le fil précalculé de chaque abonné, stocké dans un store rapide comme Redis)
rend les *lectures* du fil extrêmement rapides mais est coûteux pour les comptes avec des millions d'abonnés et
gaspille du travail à précalculer des fils pour des abonnés qui ne les consulteront peut-être jamais. Le **Fan-out on read**
(calculer le fil au moment de la requête en interrogeant les posts de tous ceux que l'utilisateur suit) évite cette
amplification d'écriture mais rend les *lectures* coûteuses pour un utilisateur qui suit beaucoup de comptes. Les systèmes réels
utilisent un hybride : fan-out on write pour la grande majorité des utilisateurs, et fan-out on read spécifiquement pour les
posts des comptes à nombreux abonnés, évitant l'explosion du fan-out on write précisément pour le
cas où elle serait la pire.

**Exemple :**
```
Normal user posts (500 followers):
  write -> push post_id into all 500 followers' precomputed feed lists (Redis)

Celebrity posts (50M followers):
  write -> post stored once, NOT fanned out
  follower's feed read -> merge their precomputed list with "posts from celebrities I
                            follow, queried live" at request time
```

**Pourquoi c'est un piège :** les candidats présentent souvent le fan-out on write comme simplement « l'option rapide » sans
nommer le mode de défaillance du compte célébrité — une conception qui ne traite pas à part les comptes à nombreux abonnés
s'effondrera visiblement (ou accumulera silencieusement une énorme amplification d'écriture) dès qu'un
vrai compte célébrité sera modélisé dans le même système.

#### Q31. Concevez un rate limiter comme composant de système distribué. Quelles sont les considérations d'échelle ?
**Réponse :** Partir du choix de l'algorithme (le token bucket est un choix par défaut courant pour autoriser des
rafales naturelles dans le cadre d'un plafond de débit moyen), puis de la question de conception plus difficile : où l'état de
la limite de débit vit-il réellement, sachant que le limiteur doit fonctionner correctement sur de nombreuses instances de
le service protégé, pas seulement une. Un compteur en mémoire par instance est simple mais faux à
l'échelle — il sous-limite (chaque instance autorise séparément la limite complète, donc N instances
autorisent collectivement N fois la limite voulue). Le correctif standard est de centraliser l'état du compteur dans
un store partagé rapide (Redis, avec des opérations atomiques d'incrément avec expiration) que chaque instance
consulte — ce qui introduit ses propres considérations : le store partagé devient une nouvelle dépendance du chemin critique
(fail open vs fail closed s'il est brièvement indisponible est une vraie décision de conception avec
de vrais compromis) et ajoute un aller-retour réseau à chaque vérification, qui doit rester assez rapide pour ne pas
devenir le nouveau goulot d'étranglement des requêtes mêmes qu'il est censé protéger.

**Exemple :**
```
Per-instance counter (wrong at scale):
  instance-1: allows 100/min   instance-2: allows 100/min   instance-3: allows 100/min
  -> a client behind a load balancer effectively gets ~300/min, not the intended 100/min

Shared Redis counter (correct):
  INCR rate:user123:2026-09-16T10:05  EX 60
  every instance checks the SAME counter -> the limit is actually 100/min, cluster-wide
```

**Pourquoi c'est un piège :** l'algorithme (token bucket vs sliding window) est la partie que les candidats
sur-préparent — le vrai bug qui casse à l'échelle est presque toujours l'erreur d'état par instance,
que le seul choix de l'algorithme ne corrige pas.

#### Q32. Concevez un système de notifications (email, SMS, push) qui sert de nombreuses équipes produit. Puis approfondissez les garanties de livraison.
Clarifier d'abord (Q1) : canaux, volume (disons 50 M de notifications/jour avec des pics ×10 lors des campagnes marketing), classes de latence (un OTP doit arriver en quelques secondes, une
newsletter peut prendre des heures), préférences utilisateur et opt-outs, et si l'ordre ou la livraison exactly-once compte. **Architecture :** les producteurs (autres services) appellent une
API de notification ou publient un événement ; le service valide, applique les préférences utilisateur, les plages de silence et les règles réglementaires (désinscription, consentement), rend un template avec
localisation, et place un message dans une **file par canal et par priorité** (des files séparées pour qu'une rafale marketing en masse ne puisse pas retarder les OTP — un bulkhead, Q19). Les **workers de canal** consomment et
appellent les fournisseurs (SES/SendGrid, Twilio, APNs/FCM), avec **abstraction de fournisseur et failover** vers un second prestataire, des limites de débit et un backoff par fournisseur. Persister un enregistrement de notification avec une
machine à états (`QUEUED → SENT → DELIVERED / FAILED`), et ingérer les webhooks des fournisseurs pour les événements de livraison, de bounce et de plainte, qui alimentent une liste de suppression. **Garanties de
livraison :** de bout en bout, c'est du **at-least-once** : la file redélivre en cas de défaillance d'un worker et un appel fournisseur peut réussir alors que la réponse est perdue, donc des
doublons sont possibles ; les réduire avec une **idempotency key** par notification logique (table de dédoublonnage avec contrainte d'unicité avant l'envoi, Q18), utiliser l'
idempotence supportée par le fournisseur lorsqu'elle existe, et accepter qu'un doublon rare vaut mieux qu'un OTP perdu — pour les messages critiques préférer les doublons à la perte, pour le marketing préférer l'inverse. Échecs : retry avec backoff
exponentiel et jitter jusqu'à une limite, puis une dead-letter queue avec alertes ; les mauvaises adresses et les hard bounces arrêtent les retries. **Échelle et abus :** shard/partitionner par utilisateur ou
tenant, appliquer des limites de débit par utilisateur et par tenant (Q31) pour qu'un bug dans un producteur ne puisse pas spammer tous les clients, et protéger la réputation du fournisseur (warm-up, throttling, suivi des plaintes).
Observabilité : lag et âge des files par priorité, latence d'envoi/de livraison, taux de bounce et de plainte. Les compromis ouverts à discuter : le choix du broker (SQS/Kafka/RabbitMQ), l'envoi synchrone
pour les OTP versus tout via les files, le regroupement par utilisateur (digest) pour éviter la fatigue de notifications, et construire ou acheter (Q35).

### Multi-région

#### Q33. Comment concevriez-vous un service pour qu'il s'exécute en active-active sur deux régions, et à quoi devez-vous renoncer ?
L'active-active signifie que les deux régions servent du **trafic réel et acceptent des écritures**, offrant une latence plus faible aux utilisateurs proches de chaque région et la survie à la perte d'une région entière avec un temps de
failover minimal (RTO proche de zéro, Q21). Le point dur, ce sont les données. Avec une **réplication asynchrone** entre régions, une écriture dans la région A devient visible dans B avec un certain
délai de quelques millisecondes à quelques secondes (le replication lag est votre RPO), et si les deux régions peuvent écrire le *même enregistrement*, on obtient des **conflits** : last-write-wins par timestamp (simple, perd silencieusement des
mises à jour et dépend de la qualité des horloges), CRDTs ou fonctions de merge pour les données à fusion naturelle (compteurs, ensembles, texte collaboratif), ou résolution au niveau
applicatif. La réplication inter-régions **synchrone** (consensus à la Spanner) évite les conflits mais ajoute un aller-retour WAN (de dizaines à centaines de ms) à chaque écriture. Les conceptions pragmatiques contournent le
problème : **partitionner les données par propriété** (chaque utilisateur ou tenant a une *région d'origine* qui gère ses écritures, l'autre région servant de réplique chaude — « active-active par
shard »), garder en écrivain unique les données fortement cohérentes et sujettes aux conflits (soldes, inventaire) tout en autorisant le multi-région pour les données à forte lecture ou naturellement fusionnables, et router avec du geo-DNS ou
du load balancing global. Ce qu'il faut construire et tester : un failover de trafic avec health checks, des choix de data stores qui supportent les écritures multi-régions (DynamoDB global tables, Cassandra,
CockroachDB/Spanner) ou un replication lag toléré avec gestion du read-your-writes (Q11) via un routage sticky, un traitement d'événements **idempotent** car les événements sont répliqués et rejoués,
une génération d'ID uniques qui n'entrent pas en collision entre régions, et une **marge de capacité** — si une région meurt, la survivante doit absorber 100 % du trafic, donc chacune tourne à moins de
50 % ou fait de l'autoscaling rapide. Coûts : à peu près le double d'infrastructure, une complexité plus élevée et un rayon d'impact plus grand pour les mauvais déploiements (déployer région par région). Être honnête avec l'intervieweur : beaucoup de
systèmes sont mieux servis par de l'active-passive avec un failover testé, et c'est l'exigence (un vrai chiffre de RTO/RPO, Q21) — et non la technologie — qui doit justifier l'active-active.

### Leadership & stratégie

#### Q34. Vous héritez d'une équipe au moral bas et avec une dette technique importante. Décrivez votre approche pour les 90 premiers jours en tant que tech lead.
**Réponse :** Résister à l'envie de lancer immédiatement de grosses réécritures ou des changements radicaux avant de
comprendre pourquoi les choses en sont arrivées là — les premières semaines servent surtout à écouter : des 1:1 avec
chaque membre de l'équipe, et examiner les incidents/postmortems récents et l'état réel de la base de code
directement plutôt que de s'appuyer uniquement sur un récit de seconde main. Trouver une ou deux victoires concrètes et visibles
atteignables dans le premier mois — pas le plus gros poste de dette technique, mais quelque chose qui
réduit de façon démontrable un vrai irritant quotidien, en bâtissant la confiance que les choses peuvent réellement s'améliorer
avant de demander de la patience pour le travail structurel plus important et plus lent. En parallèle, établir un petit
nombre de pratiques concrètes et légères qui se cumulent avec le temps (un processus de postmortem blameless,
du temps protégé pour la dette technique, une definition of done plus claire), et être explicite et transparent
avec l'équipe sur le plan et le raisonnement derrière les décisions de priorisation. À la fin des 90
jours, le but n'est pas que la dette technique ait disparu — c'est que l'équipe ait confiance qu'un plan
crédible et visible est en cours d'exécution.

**Exemple :**
```
Weeks 1-2:  1:1s with all 6 engineers + read last 4 postmortems + skim the top 5 hottest files
Week 3:     ship one visible fix for the #1 complaint (flaky CI -> stable in 3 days)
Weeks 4-12: protected 20% time for debt, blameless postmortem template adopted,
            weekly written update on what shipped and why it was prioritized
Day 90:     debt backlog is still long, but every engineer can name what changed and why
```

**Pourquoi c'est un piège :** l'instinct sous la pression de l'entretien est d'ouvrir avec un plan technique audacieux
(une réécriture, une nouvelle architecture) — la question teste si le candidat commence par
l'écoute et une petite victoire qui bâtit la confiance, puisqu'une équipe au moral bas n'adhérera pas à un gros
plan venant de quelqu'un qui n'a pas encore gagné sa crédibilité auprès d'elle.

#### Q35. Comment décidez-vous entre construire un composant vous-même et l'acheter (ou adopter de l'open source) ?
Le cadrer comme un **coût total de possession sur la durée de vie**, pesé face à la valeur stratégique. Demander d'abord : est-ce un **différenciateur** — quelque chose qui donne au produit un avantage
concurrentiel — ou une **commodité** (authentification, paiements, livraison d'emails, observabilité, recherche) ? Les capacités de commodité favorisent presque toujours l'achat ou l'adoption : le fournisseur
a déjà consacré des milliers d'années-ingénieur aux cas limites, à la conformité (PCI, SOC 2, GDPR) et aux correctifs de sécurité, et le temps rare de vos ingénieurs va à
ce que seule votre entreprise peut construire. Construire quand c'*est* le différenciateur, quand aucun produit ne satisfait les contraintes (latence, résidence des données, échelle inhabituelle), ou quand le vendor lock-in et la tarification
à votre échelle feraient plus mal que le coût d'ingénierie. Inclure le coût complet de chaque option : pour **construire** — développement initial, maintenance continue et on-call, charge de sécurité
et de montées de version, recrutement de personnes qui le comprennent, et coût d'opportunité de ce que ces personnes n'ont pas construit ; pour **acheter** — frais de licence ou d'usage qui croissent avec le volume (modéliser le
prix à 10× le trafic), effort d'intégration, **lock-in et coût de sortie** (export de données, différences d'API), stabilité du fournisseur, SLA, et flexibilité perdue. Réduire le risque de l'achat en isolant le fournisseur derrière
votre propre interface mince (un adapter ou une couche anti-corruption), en gardant les données portables, et en menant une preuve de concept time-boxée face à vos vraies exigences. Réduire le risque de la construction en
commençant par la plus petite version et en réévaluant : un composant maison devenu un fardeau de maintenance sans valeur différenciante est un signal pour le remplacer par un produit, et un
fournisseur dont les coûts ou contraintes dominent désormais est un signal pour le rapatrier en interne. Consigner la décision et ses hypothèses (un ADR) avec une date de réexamen, pour que l'équipe puisse dire plus tard si le raisonnement tient toujours.

## 🎯 Scénarios réels

### S1. La panne d'un seul serveur met hors service toute l'application
- **Symptômes :** Un serveur plante ou devient injoignable, et l'application est entièrement hors service
  pour tous les utilisateurs jusqu'à ce qu'il soit redémarré ou remplacé manuellement.
- **Diagnostic :** Aucune redondance n'existe — une instance unique sans load balancer devant elle et
  sans standby est un point unique de défaillance d'école ; la « cause » n'est pas vraiment le plantage lui-même
  (les serveurs plantent) mais le manque de tolérance de l'architecture à cet événement parfaitement normal.
- **Exemple :**
  ```
  10:14:02  app-01 (only instance) OOM-killed by the orchestrator
  10:14:02  no other instance registered -> 100% of traffic returns connection refused
  10:19:41  app-01 manually restarted -> service recovers, 5 minutes of full outage
  ```
- **Résolution :** Rétablir le service immédiatement (redémarrer, remplacer l'instance), puis, comme vrai
  correctif, introduire un load balancer avec au moins deux instances derrière, afin que la défaillance de n'importe quelle instance
  dégrade la capacité au lieu de faire tomber tout le système.
- **Prévention :** Traiter « que se passe-t-il quand ce composant unique tombe en panne » comme une question de conception
  obligatoire pour chaque composant d'une architecture de production, et non comme une réflexion après coup traitée seulement
  après la première panne qu'elle provoque.

### S2. L'expiration d'un cache sur une hot key provoque un pic soudain de charge sur la base de données
- **Symptômes :** Un pic de charge bref mais sévère sur la base de données (et souvent un pic de latence ou une
  vague de timeouts correspondant) survient à intervalle prévisible, en corrélation avec l'expiration du TTL d'un élément populaire en cache.
- **Diagnostic :** Cache stampede — de nombreuses requêtes concurrentes pour la même hot key désormais expirée manquent toutes
  simultanément le cache et frappent la base de données pour recalculer/récupérer la même valeur en même temps,
  au lieu qu'une seule requête la rafraîchisse pendant que les autres attendent ou servent brièvement des données périmées.
- **Exemple :**
  ```
  14:00:00.000  hot key "homepage:featured" TTL expires
  14:00:00.010-14:00:00.300  4,800 concurrent requests all miss cache simultaneously
  14:00:00.310  database connection pool exhausted -> unrelated queries start timing out too
  ```
- **Résolution :** Ajouter du request coalescing (une seule requête interroge réellement la base de données lors d'un
  miss pour une clé donnée ; les requêtes concurrentes pour la même clé attendent ce seul résultat), ou servir
  des données légèrement périmées tout en rafraîchissant de façon asynchrone en arrière-plan (« stale-while-revalidate »),
  ou échelonner les TTL avec du jitter pour que de nombreuses clés n'expirent pas exactement au même instant.
- **Prévention :** Pour toute hot key à une échelle où des cache misses simultanés pourraient plausiblement
  submerger la source de vérité, le request coalescing ou le TTL jitter doit faire partie de la conception du caching
  dès le départ, et non d'un correctif réactif après le premier incident causé par un stampede.

### S3. La requête retentée d'un client après un timeout crée une commande en double au lieu d'une seule
- **Symptômes :** Un client est débité deux fois, ou voit deux commandes identiques pour un seul clic de paiement,
  et les tickets de support mentionnent « je n'ai cliqué qu'une fois ».
- **Diagnostic :** Tracer les logs de requêtes pour la paire en double — vérifier si les deux requêtes viennent
  du même client dans une courte fenêtre (un retry côté client après un timeout) et si
  l'API a accepté l'écriture sans aucun mécanisme de dédoublonnage (Q18).
- **Exemple :**
  ```
  10:02:01  POST /orders  (attempt #1) -> server commits order #4471, response lost in transit
  10:02:04  client times out waiting for a response -> automatically retries
  10:02:04  POST /orders  (attempt #2, no idempotency key) -> server has no way to
            recognize this as the same logical request -> commits a second order #4472
  ```
- **Résolution :** Ajouter une exigence d'idempotency key sur l'endpoint d'écriture, adossée à une contrainte
  d'unicité au niveau de la base de données, et rembourser/fusionner manuellement les commandes en double déjà créées
  pour les clients concernés.
- **Prévention :** Exiger une idempotency key sur chaque endpoint d'écriture exposé aux clients dès le départ,
  signalée spécifiquement en design review d'API pour tout endpoint qu'un client pourrait retenter (paiements, création
  de commande, tout ce qui est déclenché par un bouton sur lequel un utilisateur pourrait double-cliquer ou qu'un client mobile pourrait
  retenter en cas de connectivité instable).

### S4. Deux moitiés d'un système distribué acceptent indépendamment des écritures conflictuelles pendant une partition réseau
- **Symptômes :** Après la résolution d'une partition réseau entre deux data centers (ou deux ensembles de nœuds),
  des données conflictuelles sont découvertes — les deux côtés ont accepté des écritures pour ce qui aurait dû être
  le même enregistrement logique unique, et ils divergent.
- **Diagnostic :** C'est un résultat de « split-brain », conséquence directe et attendue d'un
  choix de conception de système AP (favorisant la disponibilité) pendant une partition (Q8) — les deux côtés ont continué à
  servir des requêtes pendant la partition (par conception, pour la disponibilité), et la réconciliation du
  conflit qui en résulte est le coût que ce choix a toujours reporté au moment de la récupération de la partition.
- **Exemple :**
  ```
  region A (majority) accepts: UPDATE inventory SET qty = qty - 1 WHERE sku = 'X'  (5 -> 4)
  region B (minority, still serving for availability) accepts the same decrement independently
  partition heals: both sides claim qty = 4, but 2 units actually sold -> real qty should be 3
  ```
- **Résolution :** Appliquer la stratégie de résolution de conflits choisie par le système (last-write-wins par
  timestamp, une fonction de merge personnalisée, ou dans les cas réellement ambigus, faire remonter le conflit pour une
  résolution manuelle/au niveau métier) — le mécanisme précis aurait dû être décidé en choisissant AP dès le
  départ, et non improvisé pendant l'incident lui-même.
- **Prévention :** Si un système est conçu AP, la résolution de conflits doit être une partie de premier plan de l'architecture,
  conçue et testée dès le premier jour, et non une supposition que les partitions
  « n'arriveront probablement pas » — elles arriveront, un jour, et le système doit avoir une vraie réponse prête.

### S5. Un utilisateur relit immédiatement ses données tout juste sauvegardées et voit l'ancienne valeur
- **Symptômes :** Un utilisateur met à jour son profil/ses paramètres, voit une confirmation « saved », mais au
  chargement de page suivant l'ancienne valeur est de retour — le support reçoit des signalements « mes changements ne sont pas sauvegardés »
  alors que l'écriture a clairement réussi côté serveur.
- **Diagnostic :** Vérifier si les lectures sont réparties entre les répliques indépendamment de l'endroit où
  l'écriture précédente a atterri (Q11) — confirmer en vérifiant si la valeur « revenue en arrière » réapparaît
  de façon constante après un court délai (le replication lag qui rattrape) plutôt que de rester fausse indéfiniment.
- **Exemple :**
  ```
  10:00:00.000  PATCH /settings {theme: "dark"}  -> primary commits, ack sent
  10:00:00.050  GET /settings                    -> routed to replica-2, lag = 180ms
  10:00:00.050  replica-2 still has theme: "light" -> UI reverts to light before the
                replica catches up 130ms later
  ```
- **Résolution :** Router la lecture immédiate après écriture de cet utilisateur vers le primaire (ou une réplique
  confirmée comme à jour) pendant une courte fenêtre, ou faire en sorte que le client fasse confiance à sa propre écriture optimiste
  au lieu de re-fetcher immédiatement.
- **Prévention :** Traiter « ce flux relit-il sa propre écriture » comme une vérification obligatoire pour toute fonctionnalité
  avec un pattern de confirmation puis réaffichage immédiat, avant sa mise en production sur une configuration
  de read replicas avec load balancing.

### S6. Un shard de base de données est constamment bien plus chargé que les autres, et sa surcharge dégrade périodiquement tout le système
- **Symptômes :** La supervision montre un shard précis avec un CPU/une latence disproportionnément élevés
  par rapport à ses semblables, et sa dégradation corrèle avec des ralentissements plus larges du système.
- **Diagnostic :** Un hot shard dû à un mauvais choix de clé de sharding (Q14) — un petit nombre de clés très actives
  atterrissant sur le même shard génèrent une part disproportionnée de la charge totale, et la
  capacité propre du shard est le vrai goulot d'étranglement alors que la capacité globale du cluster semble correcte en
  agrégé.
- **Exemple :**
  ```
  shard-us: cpu 94%, p99 latency 890ms
  shard-eu, shard-apac, shard-latam: cpu 20-30%, p99 latency 40ms
  cluster-wide average CPU reported on the main dashboard: 36% ("looks healthy")
  ```
- **Résolution :** Une atténuation à court terme peut consister à isoler manuellement ou à mettre spécialement en cache les
  données de la ou des hot keys concernées ; le correctif durable est un re-sharding avec une clé (ou une stratégie intégrant le
  consistent hashing, Q15, ou le fractionnement supplémentaire d'une clé aberrante) qui répartit la charge plus uniformément.
- **Prévention :** Modéliser un biais réaliste du pattern d'accès (pas seulement le volume de stockage) lors du
  choix initial d'une clé de sharding, en vérifiant spécifiquement les aberrations connues ou plausibles à forte activité avant de
  s'engager sur une clé qui les concentrerait sur un seul shard.

### S7. Une design review entre deux ingénieurs seniors bloque un projet pendant des semaines sans résolution
- **Symptômes :** Deux ingénieurs seniors ont des positions fermes et opposées sur une décision
  d'architecture centrale, et des réunions de review répétées ne convergent pas — le calendrier du projet glisse
  pendant que le désaccord continue.
- **Diagnostic :** En tant que tech lead qui relit cela, vérifier si le désaccord porte réellement sur
  un fait technique connaissable (résoluble avec un spike/benchmark) ou sur une différence non dite de ce que
  chacun optimise (Q28) — un désaccord bloqué persiste souvent précisément parce que
  aucun des deux camps n'a identifié qu'il argumente à partir de priorités différentes et non dites.
- **Exemple :**
  ```
  Week 1: review meeting -> no resolution, "let's discuss again next week"
  Week 2: same two positions restated, no new information surfaced
  Week 3: project owner asks each engineer to write down what their approach optimizes
          for -> reveals a genuine time-to-ship vs. long-term-flexibility trade-off, not a
          resolvable factual disagreement -> tech lead makes the call the same day
  ```
- **Résolution :** Faciliter une conversation qui rend explicites et comparables les vrais compromis des deux positions,
  obtenir directement la réponse à toute question factuelle résoluble, et s'il s'agit réellement d'un
  jugement sans réponse objectivement juste, trancher explicitement en tant que responsable de la décision.
- **Prévention :** Établir un processus de décision clair (qui a le dernier mot, et dans quelles
  circonstances un spike time-boxé tranche un désaccord) avant le début d'un projet, pour qu'un vrai
  désaccord ait un chemin de résolution connu plutôt que de dégénérer par défaut en débat sans fin.

### S8. Les PR d'un ingénieur junior répètent la même catégorie d'erreur malgré les commentaires de review
- **Symptômes :** Les commentaires de code review identifient correctement la même classe de problème sur plusieurs
  PR consécutives du même ingénieur, corrigée individuellement à chaque fois mais réapparaissant dans la PR
  suivante.
- **Diagnostic :** Selon Q26 — les commentaires de review corrigent des cas, ils ne construisent pas le
  jugement sous-jacent qui préviendrait le *cas suivant* ; un schéma de récurrence malgré des retours
  corrects répétés signifie généralement que le « pourquoi » n'a pas réellement porté, pas que la personne
  n'écoute pas.
- **Exemple :**
  ```
  PR #212 review comment: "missing null check here"
  PR #219 review comment: "same issue as #212 — missing null check"
  PR #227 review comment: "third time — let's talk"  <- direct 1:1 held after this, not #212
  ```
- **Résolution :** Avoir la conversation directe axée sur les principes de la Q26 plutôt qu'un autre commentaire
  de PR — passer en revue ensemble plusieurs vrais exemples, lui faire réexpliquer le principe sous-jacent
  avec ses propres mots, et convenir d'une pratique concrète pour la suite.
- **Prévention :** Pour toute catégorie d'erreur apparaissant plus de deux fois chez la même personne,
  passer proactivement des commentaires de PR à une conversation directe, plutôt que d'attendre qu'elle
  devienne un schéma manifestement enraciné.

### S9. Le moral de l'équipe chute visiblement après un licenciement ou une réorganisation, et la productivité/la confiance en souffrent
- **Symptômes :** Les membres restants de l'équipe montrent un engagement réduit, un scepticisme accru envers la
  communication de la direction, et un ralentissement notable de la livraison au-delà de ce que la seule réduction d'effectif
  expliquerait.
- **Diagnostic :** L'érosion de la confiance après un licenciement/une réorganisation est une réaction normale et attendue, pas un
  problème de discipline — les gens traitent l'incertitude sur leur propre sécurité et le deuil de
  collègues/de relations de travail qui ont changé.
- **Exemple :**
  ```
  Before reorg: sprint velocity ~40 pts, Slack activity in #team normal
  2 weeks after: velocity ~22 pts, 1:1s reveal 4/6 remaining engineers are job-searching,
                 standup updates get noticeably shorter and less detailed
  ```
- **Résolution :** Sur-communiquer, honnêtement, plus qu'il ne semble nécessaire — reconnaître directement ce qui
  s'est passé, être transparent sur ce qui est et n'est pas connu de l'avenir, et rebâtir
  la prévisibilité par des engagements plus petits et constants tenus de façon fiable, plutôt que par un grand
  geste censé « réparer » le moral.
- **Prévention :** C'est en grande partie non évitable au niveau d'un manager individuel une fois qu'une décision de
  licenciement/réorganisation est prise au-dessus de lui, mais le schéma de communication constant et honnête d'un manager
  *avant* un tel événement est ce qui détermine la quantité de confiance résiduelle sur laquelle
  rebâtir.

### S10. Une partie prenante exige une deadline irréaliste pour une fonctionnalité complexe
- **Symptômes :** Une partie prenante énonce une deadline ferme pour une fonctionnalité que l'équipe d'ingénierie estime
  nécessiter sensiblement plus de temps, la deadline étant apparemment non négociable d'après
  le cadrage de la partie prenante.
- **Diagnostic :** Avant de supposer que la deadline elle-même est la contrainte immuable, clarifier ce qui est
  réellement à l'origine de celle-ci (un engagement externe réel versus un objectif choisi en interne, plus
  flexible qu'il n'y paraît) et clarifier séparément si le *périmètre* est vraiment figé.
- **Exemple :**
  ```
  Stakeholder: "This needs to ship by the 30th, no exceptions — it's tied to a partner launch."
  Follow-up: "Is the 30th the partner's hard date, or our internal target for it?"
  Answer: "...it's actually our target, the partner's real cutoff is 6 weeks later."
  -> the "non-negotiable" deadline had 6 weeks of hidden slack once actually asked about.
  ```
- **Résolution :** Présenter explicitement le vrai compromis — « voici ce qui tient d'ici cette date, voici
  ce qui devrait être reporté à un suivi, voici le risque si on le comprime à la place » — et laisser la
  partie prenante prendre une décision éclairée, en utilisant l'approche d'estimation sous incertitude de la Q29 si le
  périmètre lui-même est encore flou.
- **Prévention :** Bâtir avec les parties prenantes récurrentes une relation de travail où les compromis de périmètre et de
  calendrier sont une partie normale et attendue de la conversation dès le début de tout
  projet, plutôt que de laisser la première conversation de ce type avoir lieu sous pression de deadline.

### S11. Deux membres de l'équipe sont en conflit permanent sur la propriété du code ou l'approche technique
- **Symptômes :** Frictions répétées en review ou en planification entre deux membres précis de l'équipe,
  qui dépassent le désaccord technique normal pour devenir une dynamique personnelle ou territoriale qui
  commence à affecter la dynamique de l'équipe élargie.
- **Diagnostic :** Distinguer un désaccord technique réel et résoluble (le domaine de la Q28) d'une
  rupture de relation/de communication qui s'exprime par des désaccords
  techniques — le second cas demande une intervention différente de davantage de discussions techniques.
- **Exemple :**
  ```
  Reviewer A (1:1): "I keep getting blocked because B rewrites my PRs in review instead of
                      commenting."
  Reviewer B (1:1): "A's code doesn't follow the patterns we agreed on, so I just fix it
                      myself to keep things moving."
  -> both are reacting to a missing shared review norm, not to each other personally.
  ```
- **Résolution :** Avoir d'abord des conversations 1:1 séparées avec chaque personne, puis, si approprié, une
  conversation commune facilitée centrée sur la relation de travail et les normes de communication pour la
  suite, sans remettre en cause les désaccords techniques précis qui l'ont déclenchée.
- **Prévention :** Traiter la friction tôt, dès le premier signe d'un schéma plutôt qu'après qu'il
  affecte visiblement l'équipe élargie — une conversation privée et à faible enjeu tôt est bien plus facile qu'
  une médiation plus lourde après des semaines de friction accumulée.

### S12. Un incident de production remonte à une décision d'architecture que vous avez personnellement prise
- **Symptômes :** Une enquête de postmortem identifie la cause racine comme un choix de conception précis
  que vous avez défendu et pris, et non un bug sans rapport ou un facteur extérieur.
- **Diagnostic/réflexion :** C'est un moment où la façon dont vous le gérez compte autant que le
  correctif technique — minimiser votre propre rôle, ou à l'inverse s'excuser à outrance au point de détourner
  le véritable objectif du postmortem, sont tous deux moins utiles qu'un compte rendu clair et factuel de la
  décision et de ce qui est différent aujourd'hui pour que le résultat soit visible.
- **Exemple :**
  ```
  Postmortem timeline entry, written by the decision-maker themselves:
  "2026-02-11: I chose async replication for the orders DB to hit the launch date,
   accepting the RPO trade-off documented in ADR-014. That trade-off is what caused
   today's data loss on failover. The information available in Feb didn't include our
   current write volume."
  ```
- **Résolution :** Assumer la décision simplement sans rejeter la faute ailleurs, centrer la
  discussion sur le véritable but du postmortem blameless (quel facteur systémique a permis ce résultat,
  et quels changements réduisent le risque d'une erreur similaire de la part de quiconque à l'avenir), et assurer
  visiblement le suivi des actions convenues.
- **Prévention :** Une équipe qui a vu son tech lead gérer sa propre erreur de cette façon bâtit
  bien plus de confiance dans le processus de postmortem blameless qu'une équipe qui ne l'a vu appliqué qu'aux
  autres — ce moment précis a une influence disproportionnée sur la question de savoir si l'équipe croit réellement
  que le processus est blameless en pratique.

### S13. Le choix de la réplication asynchrone pour la disponibilité mène à un vrai incident de perte de données, visible des utilisateurs, lors d'un failover
- **Symptômes :** La défaillance d'une base de données primaire déclenche un failover vers une réplique, et des utilisateurs signalent que des données
  qu'ils avaient récemment soumises (dans les secondes précédant la panne) sont absentes de la
  réplique promue.
- **Diagnostic :** C'est la conséquence directe et connue du choix de conception de la réplication async
  (Q10) qui se manifeste pour de vrai — le replication lag signifiait que la réplique n'était pas complètement à jour au
  moment du failover, et toute écriture non encore répliquée à cet instant est réellement perdue.
- **Exemple :**
  ```
  10:41:03  primary DB fails
  10:41:03  replica was 1.8s behind at time of failure (normal lag for this system)
  10:41:05  replica promoted -> the last ~40 writes in that 1.8s window are gone,
            confirmed missing when customers report orders they placed "disappeared"
  ```
- **Résolution :** Communiquer en toute transparence avec les utilisateurs concernés sur les données perdues précises si
  elles sont identifiables, et réévaluer si le RPO (Q21) que cet incident vient de démontrer en
  pratique correspond réellement à ce que le métier avait prévu lors du choix de la réplication async — si la
  tolérance a été surestimée, c'est le déclencheur pour revenir vers une conception à RPO plus strict pour les
  données précises où cela compte le plus.
- **Prévention :** Faire du compromis de RPO une décision explicite et documentée, communiquée aux
  parties prenantes lors du choix de la réplication async, formulée en termes concrets : « cela signifie que jusqu'à N secondes
  d'écritures récentes peuvent être perdues lors d'un failover non planifié ».

### S14. Un service central devient le goulot d'étranglement dominant du système alors que le trafic de l'entreprise est multiplié par 10
- **Symptômes :** Un service conçu des années plus tôt pour une échelle bien plus petite est désormais constamment
  le facteur limitant du débit et de la latence globaux du système, malgré diverses optimisations
  tactiques déjà appliquées.
- **Diagnostic :** Distinguer un vrai plafond architectural (la conception actuelle ne peut fondamentalement
  pas monter plus en charge quel que soit le tuning) d'une inefficacité soluble (une requête non optimisée, un
  cache manquant) confondue avec un problème d'architecture — le correctif et son coût diffèrent grandement
  selon le cas.
- **Exemple :**
  ```
  order-service p99 latency: 80ms (2 years ago, 500 req/s) -> 1,400ms (today, 6,000 req/s)
  already applied: query caching, connection pool tuning, read replicas
  still degrading linearly with load -> single-writer primary is the actual ceiling,
  not a fixable inefficiency
  ```
- **Résolution :** Si c'est réellement architectural, c'est là que les décisions de la Q22 (monolithe vers microservices)
  ou de sharding de la Q14 sont revisitées avec l'avantage de connaître désormais réellement les vrais
  patterns d'accès et le vrai goulot d'étranglement — proposer une ré-architecture précise ciblant le goulot d'étranglement
  mesuré, pas une réécriture générale pour elle-même.
- **Prévention :** Revisiter proactivement les hypothèses d'architecture aux jalons de croissance significatifs —
  un système conçu pour l'ordre de grandeur d'échelle précédent est exactement le genre de chose
  qui mérite d'être explicitement réévalué avant qu'il ne devienne ce qui bloque l'ordre de grandeur suivant.

### S15. Une rotation d'astreinte se noie sous des pages non actionnables, et l'équipe cesse de faire assez confiance aux alertes pour réagir vite à une vraie
- **Symptômes :** La rotation d'astreinte reçoit des dizaines de pages par semaine, dont la grande majorité
  se résolvent d'elles-mêmes ou ne demandent aucune action ; les ingénieurs signalent qu'ils mettent en sourdine ou retardent les pages, et un
  incident réellement critique est récemment resté non acquitté pendant plus de 20 minutes parce qu'il ressemblait à du
  bruit de routine.
- **Diagnostic :** Extraire le dernier mois de pages et catégoriser chacune comme actionnable (a nécessité une réponse
  humaine) vs non actionnable (résolue d'elle-même, en flapping, ou symptomatique d'un problème connu, déjà suivi)
  — un ratio élevé de non actionnables est la cause directe de la désensibilisation, pas un problème de
  discipline de la personne d'astreinte.
- **Exemple :**
  ```
  Last 30 days: 214 pages fired
    - 6   required actual human intervention
    - 91  self-resolved within 2 minutes (flapping health check, no action needed)
    - 117 duplicate/downstream alerts for one root-cause incident, firing separately
  -> signal-to-noise ratio ~2.8%, and the one incident that mattered was buried in it
  ```
- **Résolution :** Réajuster les seuils d'alerte selon l'actionnabilité réelle, ajouter de la déduplication/du
  regroupement d'alertes pour qu'une cause racine déclenche une page au lieu de plusieurs, et supprimer ou rétrograder en
  non-paging toute alerte qui n'a nécessité aucune action dans la fenêtre de revue.
- **Prévention :** Revoir les alertes de paging selon leur actionnabilité réelle à cadence régulière, et
  traiter « cette page a-t-elle exigé qu'un humain fasse réellement quelque chose » comme le critère pour la garder en
  page, plutôt qu'en ticket ou en métrique de dashboard.

### S16. Un membre de l'équipe réagit systématiquement de façon défensive aux retours de code review, quelle que soit la manière dont ils sont formulés
- **Symptômes :** Des retours de review raisonnables et bien formulés se heurtent de façon répétée à des objections,
  des justifications ou une frustration visible d'un membre précis de l'équipe, même quand le retour est
  factuellement correct et délivré de façon constructive par plusieurs relecteurs différents.
- **Diagnostic :** Une défensive constante chez plusieurs relecteurs et plusieurs styles de formulation
  suggère que le problème ne tient pas vraiment à la façon dont le retour est formulé — il tient plus probablement à la façon dont la
  personne vit le feedback en général.
- **Exemple :**
  ```
  Reviewer A: "consider extracting this into a helper" -> pushback + justification thread
  Reviewer B: "nit: this could be simplified" -> same pattern, different reviewer, same person
  Reviewer C (different team, first time reviewing this person): same pattern again
  -> consistent across reviewers and phrasing rules out "it's how it's being said."
  ```
- **Résolution :** Avoir une conversation directe, privée et curieuse (non accusatrice) portant spécifiquement sur
  le schéma lui-même, séparée de toute PR précise, et par ailleurs s'assurer que la culture de review de l'équipe
  elle-même n'y contribue pas involontairement.
- **Prévention :** Établir tôt des normes et attentes de review claires et partagées dans l'équipe, pour que
  la réaction d'un individu au feedback porte plus probablement sur le contenu précis que sur un
  standard ambigu ou appliqué de façon incohérente.

### S17. Une dépendance inter-équipes bloque de façon répétée la livraison de votre équipe
- **Symptômes :** La roadmap de votre équipe continue de glisser parce qu'un travail requis d'une autre
  équipe n'est pas prêt quand il le faut, de façon récurrente sur plusieurs projets et non comme un raté
  ponctuel de planning.
- **Diagnostic :** Un schéma récurrent suggère un problème structurel — les priorités ne sont pas réellement
  alignées entre les équipes, ou il n'existe pas de processus clair pour négocier et s'engager sur des
  éléments de travail inter-équipes avec une vraie responsabilité.
- **Exemple :**
  ```
  Project Alpha: slipped 3 weeks waiting on Team Y's export API
  Project Beta (2 months later): slipped 2 weeks waiting on the same Team Y, different API
  -> a recurring pattern with the same team, not a one-off scheduling miss
  ```
- **Résolution :** Escalader pour rendre la dépendance et son impact métier visibles à un niveau où
  les priorités des deux équipes peuvent réellement être conciliées, en apportant un impact concret et chiffré plutôt
  qu'une plainte vague du type « on est bloqués ».
- **Prévention :** Pour les dépendances inter-équipes connues et récurrentes, établir un processus explicite de
  priorisation/d'engagement avant que le prochain projet n'en ait besoin, plutôt que des demandes informelles
  sans véritable mécanisme pour être honorées face à des priorités concurrentes.

### S18. Retirer un système legacy dont dépendent encore de nombreuses équipes s'avère bien plus difficile que prévu
- **Symptômes :** Une dépréciation planifiée d'un ancien système cale à répétition — les équipes ont toujours « encore
  une » dépendance qui n'est pas prête à migrer, et la date de sunset ne cesse de glisser.
- **Diagnostic :** Le plan a probablement sous-estimé le périmètre réel des dépendants et/ou n'a pas donné aux
  équipes dépendantes assez d'incitation ou de soutien pour prioriser réellement leur travail de migration face à
  la pression de leur propre roadmap.
- **Exemple :**
  ```
  known dependents at planning time: 4 services
  actual dependents discovered mid-migration: 11 services, including one found only
  because it started throwing errors the week the legacy write path was deprecated
  ```
- **Résolution :** Faire un audit de dépendances réellement approfondi avant de s'engager sur une date ferme,
  fournir un soutien concret à la migration (outillage, documentation, aide directe d'ingénierie pour les
  migrations les plus difficiles), et envisager un sunset par étapes qui fait remonter les dépendants oubliés
  plus tôt et de façon moins catastrophique.
- **Prévention :** Pour tout futur système censé avoir une large adoption interne, intégrer dès le début de sa vie
  l'outillage de dépréciation/migration et le suivi des dépendances, et non comme une
  réflexion après coup quand le sunset devient nécessaire des années plus tard.

### S19. En tant qu'intervieweur, vous devez évaluer équitablement la réponse d'un candidat en system design
- **Symptômes :** Un candidat produit une conception avec un diagramme d'apparence raisonnable, mais vous devez
  évaluer si elle reflète réellement un solide jugement en system design ou des réponses
  mémorisées, toutes faites, qui ne démontrent pas une vraie compréhension.
- **Diagnostic :** Le signal le plus fort n'est pas de savoir s'il a dessiné le « bon » diagramme — c'est de savoir s'il
  a posé des questions de clarification avant de concevoir (Q1), s'il sait articuler le vrai
  compromis derrière chaque décision importante, et s'il sait approfondir au moins un
  composant quand on le pousse.
- **Exemple :**
  ```
  Candidate proposes fan-out-on-write for the whole feed design, no mention of celebrity
  accounts. Interviewer: "This account has 50M followers — walk me through what happens
  when they post."
  Strong candidate: adapts live, proposes the fan-out-on-read special case (Q30).
  Weak candidate: repeats the original design unchanged, doesn't register the new constraint.
  ```
- **Résolution :** Pousser spécifiquement sur les compromis (« pourquoi ceci et pas X ») plutôt que d'accepter une
  conception énoncée telle quelle, et introduire une contrainte modifiée en cours d'entretien pour voir si
  le candidat sait adapter sa conception et son raisonnement en direct.
- **Prévention :** Calibrer les attentes et les grilles des intervieweurs autour du raisonnement sur les compromis et de
  l'adaptabilité spécifiquement, et non de la complétude du diagramme ou de la conformité à une architecture de référence « correcte » précise.

### S20. Une dépendance lente déclenche une panne complète du système qui se poursuit longtemps après le rétablissement de la dépendance
- **Symptômes :** Le service de recommandations devient lent pendant deux minutes (un mauvais déploiement, depuis annulé). En
  cinq minutes, la page produit, le paiement et le login échouent tous avec des timeouts. La dépendance est de nouveau saine, pourtant la plateforme reste hors service
  pendant 40 minutes de plus et ne se rétablit qu'après que les ingénieurs ont redémarré des services et bloqué le trafic au load balancer.
- **Diagnostic :** Une **défaillance en cascade et métastable** (Q19). Tracer le chemin de la requête : le service produit appelle les recommandations de façon synchrone avec un
  timeout de 10 secondes, donc pendant le ralentissement chaque thread worker est en attente ; le thread pool et le connection pool
  saturent, les health checks échouent, les instances sont redémarrées (caches froids, démarrage coûteux), et les clients et services en amont **retentent**, multipliant la charge
  par 2–3. Même quand la dépendance se rétablit, le trafic de retries plus le démarrage à froid maintiennent le système au-dessus de sa capacité, donc il reste hors service — le déclencheur a disparu mais la boucle de rétroaction l'entretient.
  Preuves : longueur de la file du thread pool et nombre de threads actifs bloqués au maximum, débit de requêtes vers chaque couche supérieur au
  débit de requêtes utilisateur, et une chronologie montrant les retries comme trafic dominant.
- **Exemple :**
  ```text
  user req/s:               1,000  (constant)
  product -> reco calls:    1,000 -> 3,000 req/s (3 attempts, no backoff, no budget)
  reco capacity:            1,500 req/s   => stays overloaded although the original bug is fixed
  ```
- **Résolution :** Briser la boucle : rejeter de la charge à la périphérie (rate-limit ou rejet d'une part du trafic avec `503`), désactiver l'appel non essentiel (feature flag sur les recommandations),
  scaler out des instances préchauffées, et rouvrir le trafic progressivement. Puis corriger la conception : des timeouts courts (bien en dessous du budget côté utilisateur), un **circuit breaker avec un
  fallback** (afficher des recommandations génériques), des pools bulkheadés pour qu'une dépendance optionnelle ne puisse pas prendre tous les threads, des retries avec backoff, jitter et budget de retries, et des files bornées. Vérifier avec un
  test de game-day qui injecte 5 s de latence dans les recommandations et confirme que le paiement reste sain.
- **Prévention :** Classer les dépendances en critiques vs optionnelles et dégrader gracieusement pour les secondes ; propager les deadlines ; alerter sur la saturation (profondeur de file, usage des threads) autant que sur les erreurs ;
  pratiquer régulièrement l'injection de pannes ; inclure « comment cela se comporte-t-il quand la dépendance est lente, et non en panne ? » dans chaque design review.

### S21. Une clé Redis reçoit l'essentiel du trafic ; ce nœud sature alors que la moyenne du cluster paraît correcte
- **Symptômes :** Pendant une vente flash, un nœud Redis Cluster est à 100 % de CPU avec une latence croissante et des timeouts, alors que les autres nœuds sont à 10 %.
  Ajouter des nœuds et resharder n'aide pas. La page de détail produit de l'article en vente est lente pour tout le monde.
- **Diagnostic :** Une **hot key** : une clé est mappée sur un slot d'un nœud, donc ajouter des shards ne peut pas répartir sa charge (la leçon de la clé de sharding de la Q14, dans un cache). Confirmer avec
  `redis-cli --hotkeys` (nécessite la politique LFU) ou un échantillonnage bref de `MONITOR`, des métriques d'accès par clé dans le client, et le CPU/réseau au niveau des nœuds comparés sur le cluster.
  Lié au stampede d'expiration de cache de la S2 : vérifier si la clé expire aussi simultanément pour tous les clients.
- **Exemple :**
  ```text
  GET product:99871      # 180,000 req/s -> all routed to the node owning slot 4128
  other keys             # ~2,000 req/s per node
  ```
- **Résolution :** Réduire la charge sur la clé unique : ajouter un petit **cache local in-process** (un TTL de quelques secondes via Caffeine) pour que la plupart des lectures ne quittent jamais l'instance applicative ; **répliquer
  la hot key** sous plusieurs noms (`product:99871#0..7`, en choisir un au hasard en lecture, écrire dans tous) pour la répartir sur les nœuds ; utiliser des read replicas pour les lectures ; servir la
  page via le CDN (Q17). Se protéger du stampede d'expiration avec des TTL jitterés et du request coalescing/single-flight. Vérifier avec un test de charge aux débits de vente flash qu'aucun nœud isolé
  ne dépasse ~60 % de CPU.
- **Prévention :** Tester en charge avec des distributions *biaisées* réalistes (Zipf), pas des clés uniformes ; surveiller le trafic par clé ou par slot ; préchauffer et prérépliquer les articles chauds connus
  (produits de campagne) avant un événement ; concevoir les clés pour que les articles extrêmement populaires disposent d'un cache à plusieurs niveaux.

### S22. La facture cloud mensuelle est 3× la prévision et personne ne sait pourquoi
- **Symptômes :** La finance signale une facture de 180 k$ contre les 60 k$ attendus. Il n'y a pas eu de croissance de trafic de cet ordre, et personne ne peut désigner
  un changement précis ; le dashboard de coûts montre « EC2-Other » et « Data Transfer » comme lignes les plus importantes.
- **Diagnostic :** Décomposer le coût par **service, compte, région et tag** (requêtes Cost Explorer / CUR) et regarder *quand* il a augmenté, puis corréler avec l'historique de déploiements
  et de changements. Coupables typiques : **NAT gateway / transfert de données inter-AZ / inter-régions** (un service bavard dans une autre zone, du trafic vers S3 via un NAT plutôt que via un gateway endpoint),
  une **explosion de logs ou de métriques** (logging debug laissé activé, labels à haute cardinalité), des ressources oubliées (volumes non attachés, load balancers inactifs, anciens snapshots, clusters de test abandonnés),
  un autoscaling qui monte mais ne redescend jamais, des instances surdimensionnées, des invocations serverless non plafonnées issues d'une boucle de retry ou d'un déclencheur infini, et une rétention de stockage illimitée. L'absence de tagging
  est elle-même la cause racine du « personne ne sait ».
- **Exemple :**
  ```text
  Cost Explorer, group by usage type (month over month):
    NatGateway-Bytes           $ 4,200 -> $ 61,000     <- a new service reads S3 through the NAT
    CloudWatch Logs ingestion  $ 3,100 -> $ 38,000     <- DEBUG level enabled in production
  ```
- **Résolution :** Arrêter d'abord la fuite la plus importante (ajouter le gateway endpoint S3, rétablir les niveaux de log, fixer une politique de rétention), supprimer les ressources orphelines, redimensionner et régler le scale-in
  de l'autoscaling ; puis confirmer que la courbe de coût quotidienne s'infléchit en quelques jours. Négocier avec les propriétaires à partir de données, pas de blâme, et consigner les économies.
- **Prévention :** **Tags d'allocation des coûts** obligatoires (équipe, service, environnement) imposés au déploiement ; budgets et **alertes de détection d'anomalies** par compte/équipe ; revue des coûts en
  architecture review (estimer la facture d'une nouvelle conception à 10× le trafic) ; montrer aux équipes leurs propres dépenses (FinOps) ; valeurs par défaut de cycle de vie et de rétention pour les logs, snapshots et buckets.

### S23. Le produit ne veut que des fonctionnalités ; l'ingénierie dit que la dette technique ralentit tout le monde — et la direction ne finance pas le nettoyage
- **Symptômes :** Le lead time par fonctionnalité a doublé en un an, les incidents se répètent dans le même module legacy, et les meilleurs ingénieurs râlent sur « le code
  de facturation ». Chaque demande de « sprint de refactoring » est refusée comme un coût non chiffré sans valeur client.
- **Diagnostic :** Le problème est généralement la **communication et la priorisation**, pas un manque de bonne volonté : la dette est décrite en termes d'ingénierie (« c'est le bazar ») que
  le métier ne peut pas peser face aux fonctionnalités. Rassembler des preuves : la part de chaque sprint consacrée aux reprises et corrections de bugs dans ce module, le cycle time et le taux d'échec des changements avant et
  après, le nombre d'incidents et le coût qui lui est imputable, le temps d'onboarding, et les fonctionnalités qu'elle a *bloquées ou retardées*. Identifier quelle dette porte des intérêts (sur le chemin du travail à venir de la roadmap)
  versus la dette laide mais stable qu'on peut laisser tranquille (l'approche des 90 jours de la Q34).
- **Exemple :**
  ```text
  Billing module, last 2 quarters:
    31% of bug tickets, 4 of 6 Sev-2 incidents, median PR lead time 9 days (vs 2 days elsewhere)
    Q3 roadmap: 3 of 5 planned features touch it  ->  estimated 6 weeks of extra work if untouched
  ```
- **Résolution :** La présenter comme un business case : coût du retard et risque versus un investissement borné (« 3 semaines maintenant économisent ~6 semaines au T3 et suppriment la principale
  source de Sev-2 »). Proposer une approche incrémentale qui continue de livrer — refactorer *dans le cadre* des fonctionnalités de la roadmap qui touchent la zone, protéger une part fixe de capacité
  (10–20 %) pour la dette avec des métriques convenues, ou une approche strangler — plutôt qu'un « on arrête les fonctionnalités pendant un trimestre » en big-bang. Convenir de mesures de succès et les réexaminer.
- **Prévention :** Suivre la dette explicitement (un registre visible avec impact et coût du retard), intégrer les métriques de qualité aux revues produit régulières, appliquer la règle du « boy scout »
  au quotidien, et maintenir les responsables de l'ingénierie et le produit dans une conversation permanente sur l'allocation de capacité plutôt qu'une négociation en temps de crise.

### S24. La production et la qualité d'un ingénieur ont baissé sur plusieurs mois, et l'équipe le remarque
- **Symptômes :** Un ingénieur auparavant fiable manque désormais ses engagements, ses PR sont en retard et peu soignées, il est plus silencieux en réunion, et ses collègues commencent discrètement à
  le contourner. Personne ne l'a soulevé directement.
- **Diagnostic :** Ne pas supposer un « problème de performance » — d'abord découvrir **ce qui a changé** : le travail de la personne (inadéquation de rôle ou de compétence, attentes floues, un
  projet non souhaité), l'environnement (une réorganisation, un nouveau manager, des priorités floues, une dynamique toxique, un blocage par d'autres équipes) ou sa vie (santé, burn-out, famille). Avoir un
  one-to-one privé et curieux (avant tout processus formel) en posant des questions ouvertes et en regardant les faits : exemples précis d'attentes non tenues, comment on en est arrivé là, si les objectifs étaient clairs, si
  la charge de travail est réaliste. Comparer aux attentes que la personne a réellement reçues, pas à un niveau implicite.
- **Exemple :**
  ```text
  1:1 opening: "I've noticed the last three deliverables slipped and you seem less engaged than usual.
                I want to understand what's going on and how I can help - what's your view?"
  -> reveals: moved to a legacy project against their wishes + no clear ownership since the reorg
  ```
- **Résolution :** Selon la cause : clarifier par écrit les attentes et la propriété, lever les blocages, ajuster le travail ou apporter du soutien (congés, charge réduite
  s'il s'agit d'une situation personnelle, coaching ou pairing pour une lacune de compétence), et convenir d'**objectifs spécifiques et mesurables avec une cadence de suivi** (p. ex. hebdomadaire pendant 4–6 semaines). Documenter les conversations. S'il
  n'y a pas d'amélioration malgré des attentes claires et un soutien réel, impliquer les RH/le manager et passer à un plan d'amélioration formel — avec dignité, et avec une communication honnête sur les issues possibles. Vérifier
  les progrès par rapport aux objectifs convenus, pas aux impressions.
- **Prévention :** 1:1 réguliers et feedback précoce et précis pour que les problèmes émergent en semaines, pas en trimestres ; attentes explicites par niveau ; guetter les signes de burn-out ; et traiter le problème directement au lieu de laisser
  l'équipe compenser en silence, ce qui érode la confiance de tous les autres.

### S25. Une migration de données big-bang échoue à mi-parcours du cutover, et l'équipe ne peut pas revenir en arrière proprement
- **Symptômes :** Lors d'un cutover un samedi vers une nouvelle base de données (ou un nouveau service) après un projet de migration de six mois, le script de migration échoue à 60 % à cause de données
  inattendues (lignes legacy malformées). L'application a déjà basculé certains écrivains vers le nouveau système, donc les deux stores contiennent maintenant des données différentes. L'équipe débat
  pendant des heures entre rouler en avant et revenir en arrière ; la direction demande une ETA que personne ne peut donner.
- **Diagnostic :** Le plan manquait d'un **chemin réversible et incrémental** : il dépendait d'une copie unique à un instant donné, sans
  validation préalable de la qualité des données, sans moyen de garder les deux systèmes synchronisés, et avec un plan de rollback jamais répété (et impossible une fois que les nouvelles écritures allaient uniquement vers le nouveau système). Les
  causes racines sont le big bang lui-même et des hypothèses non testées sur les données de production ; le besoin immédiat est de déterminer exactement quelles écritures existent dans quel système.
- **Exemple :**
  ```text
  T-0   switch writes to new DB              (old DB frozen, no reverse sync)
  T+2h  migration of history fails at 60%    (legacy rows violate new constraints)
  T+3h  new DB has 3h of writes not in old DB -> "rollback" would lose 3h of customer data
  ```
- **Résolution :** Stabiliser : arrêter tout changement supplémentaire, **décider à partir des données** — mettre l'application en mode maintenance/lecture seule si nécessaire, et réconcilier en rejouant les écritures post-cutover dans l'ancien système
  (depuis le change log/l'outbox) ou terminer le fix-forward si la défaillance est comprise et bornée. Communiquer honnêtement et régulièrement. Après la reprise, refaire la migration avec le pattern sûr :
  **expand/contract** et **dual-write ou synchronisation basée sur CDC** pour que l'ancien et le nouveau restent cohérents, des **shadow reads** comparant les résultats, un **backfill par lots** idempotent
  et redémarrable, un basculement progressif du trafic par pourcentage ou par tenant, et un **rollback répété** valide à chaque étape jusqu'à la mise hors service de l'ancien système. Vérifier par une
  réconciliation automatisée (nombres de lignes, checksums, comparaisons par échantillonnage) avant chaque étape.
- **Prévention :** Ne jamais planifier une migration dont le seul rollback est la restauration d'une sauvegarde ; profiler tôt les données de production pour repérer les anomalies ; répéter le tout sur une copie de taille production avec chronométrage ; définir à l'avance des critères go/no-go et des points d'abandon ;
  garder l'ancien système en lecture seule et disponible pendant une période fixe après le cutover ; et traiter la mise hors service de l'ancien système comme une décision séparée, ultérieure (voir S18).

## 📌 Cheat-sheet

- **Avant de concevoir** : exigences fonctionnelles (quoi) + exigences non fonctionnelles (quelle qualité — échelle, latence, disponibilité, coût) — toujours en premier.
- **HLD vs LLD** : grandes pièces et flux de données vs détail d'implémentation d'une fonctionnalité.
- **CAP** : pendant une partition, choisir Consistency ou Availability — pas une réponse universelle, un compromis par système et par cas d'usage.
- **Mitigations OWASP** : requêtes paramétrées (injection), authz côté serveur à chaque requête (broken access control), échapper la sortie (XSS), TLS + chiffrement au repos (données sensibles), surface exposée minimale (misconfiguration).
- **Horizontal vs vertical** : vertical = simple, plafond dur, SPOF ; horizontal = pas de plafond, tolérant aux pannes, vraie complexité des systèmes distribués.
- **Idempotency keys** : le retry d'un client après timeout peut dupliquer une écriture sans elles — les imposer par une contrainte d'unicité au niveau du stockage, pas par une vérification en mémoire.
- **Réplication sync vs async** : sync = pas de lag, latence plus élevée/disponibilité plus faible ; async = latence plus faible/disponibilité plus élevée, replication lag = perte de données possible au failover.
- **Read-your-own-writes** : les lectures sur réplique async peuvent faire paraître annulée l'écriture d'un utilisateur — router la lecture immédiate après écriture vers le primaire, ou faire confiance à l'écriture optimiste du client.
- **Clé de sharding** : choisir pour une répartition uniforme de la *charge*, pas seulement du stockage — se méfier des clés à faible cardinalité ou biaisées par l'activité, qu'une moyenne saine à l'échelle du cluster peut masquer.
- **Consistent hashing** : minimise le remapping quand des nœuds rejoignent/quittent — évite l'invalidation de masse de type cache stampede que provoque le hashing modulo.
- **CDN** : excellent pour le contenu statique/partagé ; aucune aide pour les données dynamiques temps réel réellement par utilisateur.
- **Stratégies de cache** : cache-aside (lazy, simple, risque de péremption) / write-through (cohérent, écritures plus lentes) / write-behind (rapide, risque de perte de données) — choisir délibérément, plus le TTL comme filet de sécurité.
- **Back-of-envelope** : DAU → requêtes/sec (avec multiplicateur de pic) → stockage/bande passante — fonder les décisions sur de vrais chiffres, même approximatifs.
- **Monolithe vs microservices** : monolithe par défaut jusqu'à ce que la propriété indépendante par équipe/le déploiement indépendant/la mise à l'échelle indépendante soit une contrainte *actuelle* et réelle — un découpage prématuré coûte plus cher à défaire qu'un découpage tardif à faire.
- **API Gateway** : centralise l'auth, le rate limiting, le routage — devient un nouveau point unique critique, la garder mince.
- **Cohérence à terme vs forte** : à terme pour les données à faible coût de péremption (compteurs de likes) ; forte pour tout ce dont la péremption a un vrai coût financier/métier (soldes, inventaire).
- **RTO/RPO** : tolérances définies par le métier pour l'indisponibilité et la perte de données — les traduire en architecture concrète de réplication/failover/sauvegarde, ne pas sur- ou sous-construire par rapport à elles.
- **Fatigue d'alertes d'astreinte** : un faible ratio de pages actionnables est ce qui désensibilise une équipe, pas un problème de discipline — ajuster les seuils et dédupliquer selon l'actionnabilité réelle, pas le risque théorique.
- **Leadership** : feedback spécifique, opportun et centré sur le pourquoi ; séparer les personnes des désaccords en design review ; assumer ses erreurs simplement dans les postmortems blameless ; rendre explicites les compromis et les estimations sous incertitude plutôt qu'implicites.
- **SQL vs NoSQL** : relationnel par défaut (ACID, jointures, requêtes ad hoc) ; ajouter des stores spécialisés comme copies *dérivées* ; ne choisir un NoSQL comme base principale que pour une raison nommable (accès par clé à très grande échelle, volume d'écriture, écritures multi-régions).
- **Services stateless** : pas d'état par utilisateur dans la mémoire de l'instance ou sur le disque local — sessions, fichiers et jobs migrent vers des stores partagés ; les pertes d'état ne peuvent coûter que de la performance, jamais de la correction.
- **Surcharge** : les files non bornées transforment les pics en latence invisible et en OOM ; utiliser des files bornées, du backpressure, du load shedding (`429`/`503` + `Retry-After`), des timeouts, backoff + jitter, budgets de retries, circuit breakers, bulkheads.
- **Locks distribués** : un lock à TTL peut expirer pendant que son détenteur est en pause — utiliser des fencing tokens vérifiés par la ressource, ou des écritures idempotentes/conditionnelles (`WHERE version = ?`) ; les locks servent l'efficacité, pas la correction.
- **2PC vs saga** : 2PC = atomique mais bloquant et dépendant du coordinateur ; saga = transactions locales + compensations idempotentes, cohérence à terme, étapes irréversibles en dernier, événements publiés via un outbox.
- **Système de notifications** : files par canal/priorité (bulkheads), failover de fournisseur, idempotency key, at-least-once avec dédoublonnage, DLQ, webhooks alimentant les listes de suppression, limites de débit par tenant.
- **Active-active** : le point dur, ce sont les conflits d'écriture — partitionner par région d'origine, garder les données sujettes aux conflits en écrivain unique, LWW perd des mises à jour ; la survivante doit absorber 100 % du trafic ; souvent l'active-passive suffit.
- **Build vs buy** : construire les différenciateurs, acheter les commodités ; comparer le TCO à 10× l'échelle en incluant le lock-in et le coût de sortie ; isoler les fournisseurs derrière un adapter ; consigner la décision comme un ADR avec une date de revue.
- **Défaillance en cascade** : lent bat en panne — retries + pools saturés + redémarrages à froid maintiennent un système hors service après la disparition du déclencheur ; briser la boucle en rejetant de la charge et en dégradant les dépendances optionnelles.
- **Hot keys** : ajouter des shards ne peut pas fractionner une clé — cache local, réplication de clé, read replicas, CDN ; TTL jitterés et single-flight.
- **Coût cloud** : regrouper par service/type d'usage/tag ; suspects habituels : transfert de données/NAT, logs et cardinalité des métriques, ressources orphelines ; imposer tags, budgets et alertes d'anomalies.
- **Négociation de la dette technique** : traduire la dette en coût du retard, incidents et éléments de roadmap bloqués ; refactorer le long de la roadmap et réserver une part fixe de capacité.
- **Performance en baisse** : trouver *ce qui a changé* avant de supposer un problème de performance ; attentes écrites claires, soutien, objectifs mesurables, puis un processus formel si nécessaire.
- **Migrations** : expand/contract, dual-write ou synchronisation CDC, shadow reads, backfill par lots idempotent, cutover progressif, rollback répété, et réconciliation avant la mise hors service.
