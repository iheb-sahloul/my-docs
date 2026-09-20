# Full Stack & DevOps

## 🟢 Fondamentaux

### REST

#### Q1. Quels sont les principes fondamentaux d'une bonne conception d'API REST ?
Modélisez les URLs autour de ressources (des noms), pas d'actions — `/orders/123`, et non `/getOrder?id=123` — et
utilisez les méthodes HTTP pour exprimer l'action : `GET` (lecture, safe et idempotent), `POST` (création, non
idempotent), `PUT` (remplacement complet, idempotent), `PATCH` (mise à jour partielle), `DELETE` (suppression,
idempotent). Utilisez les codes de statut pour porter un vrai sens (`200`/`201`/`204` pour les variantes de succès,
`400` pour une requête malformée, `401`/`403` pour les échecs d'authentification, `404` pour les ressources absentes, `409`
pour un conflit, `422` pour des données sémantiquement invalides, `500` pour les erreurs serveur) plutôt que de toujours
renvoyer `200` avec un indicateur d'erreur enfoui dans le corps. Imbriquez les ressources pour exprimer une véritable
appartenance (`/orders/123/items`), gardez des réponses de forme cohérente d'un endpoint à l'autre, et versionnez
l'API de manière délibérée (Q8) plutôt que de laisser des breaking changes partir silencieusement.

### Containers

#### Q2. Qu'est-ce qu'un container, et en quoi diffère-t-il fondamentalement d'une machine virtuelle ?
Un container empaquette une application avec ses dépendances et partage le kernel de la machine hôte —
c'est un processus isolé (via les namespaces Linux pour l'isolation et les cgroups pour les limites de ressources),
et non un système d'exploitation séparé, ce qui le rend léger (démarre en millisecondes à secondes,
image de petite taille) comparé à une VM, qui virtualise le matériel et exécute un OS invité complet et un kernel séparés
(démarre en dizaines de secondes à minutes, empreinte bien plus grande). Le compromis :
une VM offre une isolation plus forte (un kernel séparé signifie qu'un exploit au niveau du kernel dans une VM n'atteint pas
automatiquement les autres) au prix d'un vrai coût en ressources ; le modèle à kernel partagé d'un container est
plus léger et plus dense, mais implique que les containers d'un même hôte sont des processus isolés, pas des systèmes
d'exploitation isolés.

#### Q3. Expliquez comment fonctionnent les layers d'image Docker et le cache de build.
Chaque instruction d'un Dockerfile (`RUN`, `COPY`, `ADD`) crée un nouveau layer immuable empilé sur
le précédent, et Docker met chaque layer en cache — si l'instruction d'un layer et ses entrées n'ont pas
changé depuis le dernier build, Docker réutilise le layer en cache au lieu de le ré-exécuter, et
tous les layers *après* le premier modifié doivent être reconstruits (le cache s'invalide à partir de ce point,
pas de façon sélective). C'est pourquoi l'ordre des instructions compte pour la vitesse de build : placez d'abord les
étapes qui changent peu (installation des paquets OS, restauration des dépendances depuis un fichier
de lock) et en dernier celles qui changent souvent (copie du code source de l'application), afin qu'une modification
du code source n'invalide et ne reconstruise que les derniers layers plutôt que l'image entière, y compris
le re-téléchargement inutile des dépendances.

#### Q4. Volumes Docker vs bind mounts vs layer inscriptible du container — où doivent vivre les données ?
Le filesystem propre d'un container est un mince **layer inscriptible** au-dessus des layers d'image en lecture seule : il
démarre vite, mais tout ce qu'il contient disparaît quand le container est supprimé, et les écritures lourdes
via le storage driver en copy-on-write sont plus lentes qu'avec un vrai volume. Tout ce qui doit
survivre à la vie d'un container — le répertoire de données d'une base, les fichiers uploadés — doit se trouver en dehors. Un
**named volume** (`docker run -v pgdata:/var/lib/postgresql/data`) est créé et géré par
Docker, vit dans l'espace propre à Docker sur l'hôte, fonctionne de la même façon sur tous les OS, est portable entre
containers, est le bon choix par défaut pour les données persistantes, et peut être sauvegardé ou piloté par un plugin
de volume (NFS, disque cloud). Un **bind mount** (`-v $(pwd)/src:/app/src`) mappe un chemin précis de l'hôte dans
le container : idéal en développement, où les modifications de votre éditeur doivent être visibles immédiatement dans le container,
mais il lie le container à l'organisation des répertoires et aux permissions de l'hôte (le problème classique
« les fichiers créés par le container appartiennent à root sur mon hôte », ou l'inverse sous Linux avec des
UIDs différents) et il est plus lent sur macOS/Windows à cause de la couche de partage de fichiers de la VM. Un mount `tmpfs` est
uniquement en mémoire, utile pour des secrets ou des fichiers temporaires qui ne doivent jamais toucher le disque. Kubernetes fait la même
distinction : `emptyDir` pour les données temporaires liées à la vie du pod, et un `PersistentVolumeClaim` pour les données
qui doivent lui survivre. Le point d'entretien est le mode de défaillance : un container de base de données lancé sans
volume perd toutes ses données au `docker rm`, et `docker compose down -v` supprime aussi les volumes.

### Kubernetes

#### Q5. Qu'est-ce qu'un Pod Kubernetes, et pourquoi Kubernetes n'exécute-t-il pas simplement les containers directement ?
Un Pod est la plus petite unité déployable dans Kubernetes — un ou plusieurs containers toujours
schedulés ensemble sur le même node, qui partagent un network namespace (ils peuvent donc se joindre via
`localhost` et partagent une seule IP), et peuvent partager des volumes de stockage. Kubernetes ne gère pas les containers
nus directement parce que la plupart des vrais workloads ont besoin de ce regroupement « toujours colocalisés, toujours
co-schedulés » — un container applicatif principal plus un sidecar (un log shipper, un proxy de service
mesh) qui doit tourner à ses côtés sur le même node et partager son réseau — et l'abstraction Pod
donne à Kubernetes une seule unité à scheduler, à health-checker et à scaler dans son ensemble, plutôt que
d'avoir à raisonner sur des containers faiblement couplés qui ont simplement besoin d'être à proximité les uns des autres.

#### Q6. Un pod ne fonctionne pas — quelles sont vos premières commandes `kubectl`, dans l'ordre ?
Allez de « dans quel état est-il ? » à « pourquoi ? » sans deviner. `kubectl get pods -o wide` montre le statut,
les restarts, le node et l'IP : le statut restreint déjà le champ (`Pending` = problème de scheduling,
`ImagePullBackOff` = image ou credentials du registry, `CrashLoopBackOff` = le processus démarre et meurt,
`Running` mais `0/1 READY` = readiness probe en échec). Ensuite `kubectl describe pod <name>` — lisez d'abord la section
**Events** en bas : elle signale les `FailedScheduling` (CPU insuffisant, taints,
volume non lié), les probes en échec, les OOM kills ou les erreurs de pull d'image, et le bloc `Last State` montre le
code de sortie et la raison du container précédent (`OOMKilled`, `Error`, exit 137/143). Puis
`kubectl logs <pod>` pour la sortie de l'application — et `--previous` pour un container qui a déjà
redémarré, car l'instance courante n'a peut-être encore rien loggé — avec `-c <container>` dans un
pod multi-containers. S'il tourne mais se comporte mal, `kubectl exec -it <pod> -- sh` pour l'examiner (résolutions DNS,
`curl` vers une dépendance, variables d'environnement), ou `kubectl debug` avec un container éphémère quand l'image n'a pas de shell.
Pour les problèmes de trafic, vérifiez la couche au-dessus : `kubectl get endpoints <service>` (vide = problème de selector ou de
readiness, S4) et `kubectl get events --sort-by=.lastTimestamp` pour le namespace. Ce n'est
qu'ensuite qu'on sort `top`, les conditions du node, ou le statut de rollout du controller
(`kubectl rollout status deploy/<name>`). L'habitude qui distingue les seniors est de lire les Events et les
logs `--previous` *avant* de changer quoi que ce soit.

### Observabilité

#### Q7. Quels sont les trois piliers de l'observabilité, et qu'est-ce que chacun vous apprend réellement ?
Les **Logs** sont des événements discrets et horodatés — ce qui s'est passé précisément, avec du détail (un message
d'erreur, les paramètres d'une requête donnée) — idéaux pour creuser une occurrence précise
quand on sait déjà à peu près où regarder. Les **Metrics** sont des mesures numériques agrégées dans
le temps (débit de requêtes, taux d'erreur, percentiles de latence, usage CPU/mémoire) — idéales pour voir les tendances,
définir des seuils d'alerte et répondre à « le système est-il sain en ce moment » d'un coup d'œil, mais
sans le détail d'un événement particulier. Les **Traces** suivent le chemin d'une requête à travers un
système distribué, en montrant le timing de chaque hop/span — idéales pour répondre à « où, dans cette
chaîne d'appels multi-services, le temps est-il passé, ou où cela a-t-il échoué » pour une requête précise. Les trois
sont complémentaires, pas substituables : les metrics disent que quelque chose ne va pas et à peu près où ; les traces
identifient quel hop précis ; les logs donnent le détail exact de ce qui s'y est passé.

## 🟡 Pièges seniors

### Conception d'API & sécurité

#### Q8. Comment versionner une API REST sans casser les clients existants ?
**Réponse :** La discipline de base consiste à distinguer les changements rétrocompatibles (ajout d'un nouveau
champ optionnel, ajout d'un nouvel endpoint) — qui ne nécessitent pas d'incrément de version, puisque les anciens clients
ignorent simplement les champs qu'ils ne connaissent pas — des breaking changes (suppression/renommage d'un champ,
changement du type ou du sens d'un champ, changement de paramètres obligatoires), qui, eux, en nécessitent. Pour les breaking
changes, stratégies courantes : versioning par chemin d'URL (`/v1/orders`, `/v2/orders` — simple, très
visible, facile à router, mais peut conduire à dupliquer la logique d'implémentation entre versions) ;
versioning par header (`Accept: application/vnd.api.v2+json` — garde des URLs stables, moins
visible/découvrable) ; ou, de façon plus robuste, traiter le versioning comme un dernier recours et concevoir les changements pour
qu'ils soient additifs et rétrocompatibles autant que possible (la même discipline que derrière la Q27 de la question sur
l'évolution de schéma du module 4), en réservant un vrai incrément de version aux breaking changes réellement
inévitables, avec une fenêtre de dépréciation claire et une communication aux consommateurs avant que l'ancienne version ne soit
retirée.

**Exemple :**
```
GET /v1/orders/123        # versioning par chemin d'URL — simple, visible, mais duplique la logique entre versions
GET /orders/123
Accept: application/vnd.api.v2+json   # versioning par header — URL stable, moins découvrable
```

**Pourquoi c'est un piège :** recourir à un incrément de version pour chaque changement, y compris additif, force
chaque client à migrer explicitement pour quelque chose qui était rétrocompatible dès le départ
— une réponse senior traite le versioning comme le dernier recours pour les changements réellement cassants, pas comme la
réponse par défaut à toute modification de schéma.

#### Q9. Que signifie l'idempotence pour une API REST, et pourquoi `POST` nécessite-t-il un traitement spécial ?
**Réponse :** Une opération idempotente produit le même état final quel que soit le nombre de fois où elle est
appliquée — `GET`, `PUT` et `DELETE` sont idempotents par définition/convention (appeler
`DELETE /orders/123` cinq fois laisse le même état final que l'appeler une fois), mais `POST`
(typiquement « créer une nouvelle ressource ») ne l'est pas — rejouer un `POST` à cause d'un timeout ou d'un accroc réseau
peut créer des ressources en double, exactement le schéma du problème d'idempotence de messagerie du module 4
(Q9/Q10 là-bas) mais au niveau HTTP. La solution a la même forme : accepter une clé d'idempotence explicite
du client (un UUID généré une fois par opération logique, envoyé dans un header, et renvoyé
à l'identique à chaque retry), et le serveur vérifie si cette clé a déjà été traitée avant de
créer une nouvelle ressource — un client qui rejoue une requête en timeout avec la même clé reçoit le
résultat d'origine sans danger au lieu d'un doublon.

**Exemple :**
```http
POST /payments
Idempotency-Key: 7c9e6679-7425-40de-944b-e07fc1f90ae7
{...}
```
Un timeout réseau pousse le client à rejouer avec la même clé — le serveur reconnaît que la clé
a déjà été traitée et renvoie le résultat d'origine au lieu de créer un second paiement.

**Pourquoi c'est un piège :** croire que la logique de retry seule (« on rejoue simplement à chaque timeout ») est un défaut sûr
quelle que soit la méthode HTTP — rejouer un `POST` sans clé d'idempotence peut créer silencieusement
des ressources en double précisément quand le client essaie d'être résilient.

#### Q10. Quels sont les algorithmes courants de rate-limiting d'API, et quel est le compromis entre eux ?
**Réponse :** Le **fixed window** compte les requêtes dans un bucket de temps fixe (par ex. par minute) et se réinitialise
à la frontière — simple, mais autorise une rafale allant jusqu'à 2x la limite juste à la frontière d'une fenêtre (une
pleine allocation juste avant la frontière, puis une autre pleine allocation juste après). Le **sliding
window** lisse cela en pondérant le compte entre la fenêtre courante et la précédente
proportionnellement au temps écoulé — plus précis, un peu plus complexe à implémenter. Le **token
bucket** remplit des tokens à un rythme régulier jusqu'à une capacité, et chaque requête consomme un token —
il autorise naturellement de brèves rafales (jusqu'à la capacité du bucket) tout en imposant un débit moyen stable
dans le temps, ce qui correspond mieux à de nombreux schémas de trafic réels qu'un plafond strict par fenêtre. Le **leaky
bucket** traite les requêtes à un débit de sortie strictement constant quelle que soit l'irrégularité de l'entrée,
lissant complètement la sortie au prix d'une latence ajoutée pour le trafic légitime en rafale. Le
choix dépend de si le trafic légitime est naturellement en rafales (favorise le token bucket) ou
si un débit aval strictement lisse est requis (favorise le leaky bucket).

**Exemple :**
```
# Fixed window : rafale jusqu'à 2x possible juste à la frontière.
11:00:59 -> 100 requêtes autorisées (la fenêtre se réinitialise à 11:01:00)
11:01:00 -> 100 requêtes de plus autorisées immédiatement -> 200 en ~1 seconde

# Le token bucket lisse cela en plafonnant la rafale à la capacité propre du bucket, rechargé régulièrement.
```

**Pourquoi c'est un piège :** choisir le fixed window parce que c'est le plus simple à implémenter, sans
tenir compte de son défaut de rafale à la frontière, revient à faire de la limite une simple recommandation souple au
moment précis où le trafic est le plus en rafales — l'opposé de quand elle doit réellement tenir.

#### Q11. Pourquoi une requête navigateur échoue-t-elle avec une erreur CORS alors que l'API fonctionne dans curl, et comment les preflights et les cookies (`SameSite`) changent-ils la donne ?
**Réponse :** CORS est appliqué par le **navigateur**, pas par le serveur ni le réseau : `curl` et les appels serveur-à-serveur ne
le voient jamais. Quand une page sur `https://app.example.com` appelle `https://api.example.com`, le navigateur ne laisse
JavaScript lire la réponse que si l'API renvoie les headers `Access-Control-Allow-Origin` correspondants. Pour les
requêtes « non simples » — une méthode autre que `GET`/`POST`/`HEAD`, un `Content-Type: application/json`, ou un header custom comme
`Authorization` — le navigateur envoie d'abord une requête **preflight** `OPTIONS` avec `Access-Control-Request-Method/Headers`,
et le serveur doit répondre `2xx` avec `Access-Control-Allow-Methods/Headers` (cacheable avec `Access-Control-Max-Age`) sinon la vraie
requête n'est jamais envoyée. Les erreurs classiques : le preflight est bloqué par l'authentification (l'`OPTIONS` ne porte aucun
credential, donc un security filter répond `401` et CORS « échoue »), une origine wildcard `*` combinée aux credentials
(interdit — avec `Access-Control-Allow-Credentials: true` il faut renvoyer une origine explicite et ajouter
`Vary: Origin`), un reverse proxy qui supprime ou duplique les headers CORS, et les réponses d'erreur (`500`, `502`
venant d'une gateway) qui n'ont pas de headers CORS, si bien que le navigateur rapporte une « erreur CORS » et masque le vrai statut. Les cookies ajoutent une seconde couche : un cookie n'est envoyé
sur les requêtes cross-site que s'il est `SameSite=None; Secure` (la valeur par défaut est `Lax`), que la requête définit
`credentials: "include"`, et que le serveur autorise les credentials ; les restrictions sur les cookies tiers dans les navigateurs peuvent le bloquer malgré tout,
donc préférez un déploiement same-site (api.example.com et app.example.com partagent le site `example.com`) ou un
reverse proxy same-origin qui élimine CORS du problème.

**Exemple :**
```java
// Spring Security : CORS doit être géré *avant* le filtre d'authentification, sinon le preflight reçoit un 401.
@Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
    return http.cors(Customizer.withDefaults())
               .authorizeHttpRequests(a -> a.anyRequest().authenticated())
               .build();
}
@Bean CorsConfigurationSource cors() {
    var c = new CorsConfiguration();
    c.setAllowedOrigins(List.of("https://app.example.com"));   // origine explicite, pas "*"
    c.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
    c.setAllowedHeaders(List.of("Authorization", "Content-Type"));
    c.setAllowCredentials(true);
    c.setMaxAge(Duration.ofHours(1));
    var s = new UrlBasedCorsConfigurationSource();
    s.registerCorsConfiguration("/**", c);
    return s;
}
```

**Pourquoi c'est un piège :** les développeurs le « corrigent » avec `Access-Control-Allow-Origin: *` ou en désactivant les vérifications du navigateur,
ce qui soit échoue dès que des credentials sont impliqués, soit affaiblit la sécurité (renvoyer n'importe quel `Origin`
avec credentials permet à n'importe quel site d'appeler l'API en tant qu'utilisateur connecté). CORS n'est aussi *pas* un
contrôle de sécurité contre les clients non-navigateurs ni contre le CSRF — il ne fait qu'assouplir la same-origin policy, donc l'authentification et
les protections CSRF restent nécessaires.

#### Q12. JWT dans `localStorage`, JWT dans un cookie `HttpOnly`, ou session côté serveur — quels compromis et quels pièges ?
**Réponse :** Une **session côté serveur** stocke l'état (utilisateur, rôles) sur le serveur et donne au navigateur un id opaque dans un
cookie : la révocation est triviale (supprimer la session), le client ne détient jamais de claims, mais cela nécessite un
stockage partagé (Redis) en cas de scale out. Un **JWT** est un token signé et autonome, vérifié sans lookup, ce qui
est pratique entre services, mais en contrepartie il **ne peut pas être révoqué avant son expiration**, ses
claims sont visibles de tous (signés, pas chiffrés), et des rôles périmés restent valides jusqu'à l'expiration. L'endroit où on le conserve
compte le plus : dans `localStorage`, n'importe quel XSS peut le lire et l'exfiltrer ; dans un cookie `HttpOnly; Secure; SameSite`, JavaScript
ne peut pas le lire, mais les cookies sont envoyés automatiquement, donc il faut une protection CSRF (`SameSite=Lax/Strict`, tokens CSRF). Erreurs
courantes avec les JWT : accepter `alg: none` ou laisser le token choisir son propre algorithme (figer l'algorithme et la clé), ne pas
valider `iss`/`aud`/`exp`, des access tokens à longue durée de vie, stocker des données sensibles dans les claims, et utiliser un secret HMAC partagé entre
services. Le design sain habituel est un **access token de courte durée (5–15 min) plus un refresh token rotatif** conservé dans un
cookie `HttpOnly`, avec détection de réutilisation du refresh token, plus une deny-list côté serveur uniquement pour le cas d'urgence. Pour une
application first-party orientée navigateur, un simple cookie de session est souvent plus simple et plus sûr que des JWT ; les JWT méritent leur place pour les appels
service-à-service et les API tierces (OAuth2/OIDC).

**Exemple :**
```http
Set-Cookie: refresh=9f2c...; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh; Max-Age=1209600

# Access token : courte durée, envoyé uniquement depuis la mémoire :
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjIwMjYtMDEifQ...
# Le vérificateur doit figer : alg=RS256, iss=https://id.example.com, aud=orders-api, et contrôler exp/nbf avec un léger clock skew.
```

**Pourquoi c'est un piège :** le « JWT stateless » est vendu comme scalable et simple, mais les équipes découvrent qu'on ne peut pas déconnecter un token volé,
que les changements de permissions sont en retard de la durée de vie du token, et que la commodité de `localStorage` transforme chaque XSS en
prise de contrôle de compte. La bonne réponse nomme le modèle de menace (XSS vs CSRF vs vol) plutôt que de déclarer un mécanisme gagnant.

### Docker

#### Q13. Pourquoi l'ordre des instructions du Dockerfile compte-t-il à la fois pour l'efficacité du cache et pour la taille finale de l'image, et que résout un build multi-stage ?
**Réponse :** Selon les mécanismes de cache de la Q3, les instructions doivent être ordonnées de la moins fréquemment
modifiée (installation des dépendances OS/système) à la plus fréquemment modifiée (copie du
source de l'application), afin que les changements de code courants n'invalident que les derniers layers, pas tout le build.
Les builds multi-stage résolvent un problème distinct : compiler/builder une application nécessite souvent des outils
(un JDK, des caches de build, `node_modules` avec les devDependencies) dont l'application *en cours d'exécution*
n'a absolument pas besoin — un Dockerfile multi-stage build dans un stage avec la toolchain complète, puis
copie uniquement l'artefact de build final (un jar, un binaire compilé, les assets statiques buildés) dans un
stage final neuf et minimal (`FROM eclipse-temurin:21-jre-alpine`, pas l'image JDK complète), de sorte que l'image
livrée ne transporte pas en production le poids et la surface d'attaque de toute la toolchain de build.

**Exemple :**
```dockerfile
# Single-stage : livre le JDK entier + le cache de build en production.
FROM eclipse-temurin:21-jdk
COPY . .
RUN mvn package

# Multi-stage : seul l'artefact final passe dans l'image runtime.
FROM eclipse-temurin:21-jdk AS build
COPY . .
RUN mvn package

FROM eclipse-temurin:21-jre-alpine
COPY --from=build /app/target/app.jar .
```

**Pourquoi c'est un piège :** « le build passe, l'image tourne » est traité comme la ligne d'arrivée — mais un
Dockerfile single-stage livre silencieusement toute la toolchain de build (et sa surface d'attaque) en
production, un problème qui semble purement cosmétique (taille de l'image) jusqu'à ce qu'il devienne un vrai problème de sécurité ou de
coût.

#### Q14. Expliquez comment diagnostiquer un container Docker qui se termine avec le code 137.
**Réponse :** Le code de sortie 137 vaut 128 + 9 (`SIGKILL`, signal 9) — le processus principal du container a été
terminé de force par une cause externe, et non arrêté proprement par sa propre logique, et les logs sont
souvent vides précisément parce qu'un `SIGKILL` ne laisse aucune chance au processus de flusher ou de logger quoi que ce soit
en partant. La cause la plus courante est l'OOM killer : le container a dépassé sa limite mémoire (ou
l'hôte subit une forte pression mémoire), et le kernel a tué le processus pour protéger le
système. Diagnostic : lancez `docker inspect` sur le container arrêté et vérifiez le champ `OOMKilled`
sous `State` — si `true`, c'est confirmé ; la résolution est d'augmenter la limite mémoire du container (s'il était
simplement sous-dimensionné) ou de corriger une vraie fuite mémoire dans l'application si l'usage grimpe
sans borne au lieu de se stabiliser. Si `OOMKilled` vaut `false`, consultez les logs kernel de l'hôte
(`dmesg`, `journalctl -k`) pour des signes d'un kill externe — un `docker stop` qui dépasse son
délai de grâce et escalade en `SIGKILL`, ou un orchestrateur (Kubernetes) qui évince le pod pour
ses propres raisons de pression sur les ressources.

**Exemple :**
```
$ docker inspect mycontainer --format '{{.State.OOMKilled}}'
true
```

**Pourquoi c'est un piège :** traiter un log vide comme « aucune preuve, donc ça doit être quelque chose d'obscur » — un
log vide après une sortie 137 est la signature *attendue* d'un `SIGKILL`, pas un mystère ; vérifier
`OOMKilled` dans `docker inspect` d'abord est plus rapide que de fouiller des logs applicatifs qui
n'allaient jamais rien contenir.

#### Q15. Pourquoi une application peut-elle échouer uniquement dans un container Docker, mais fonctionner très bien exécutée directement sur l'hôte ?
**Réponse :** Causes courantes : une référence codée en dur à `localhost` qui signifiait « cette même machine » sur
l'hôte mais qui, dans un container, désigne le network namespace isolé du container lui-même plutôt
qu'un autre service que le container doit joindre (ce qui nécessite plutôt un nom de service/alias réseau de container,
ou `host.docker.internal` dans certaines configurations) ; une incohérence de permissions de fichiers, puisque
l'utilisateur par défaut d'un container (parfois `root`, parfois un UID précis intégré à l'image) peut ne
pas correspondre aux permissions de l'utilisateur hôte sur un volume monté ; une variable d'environnement ou un
fichier de configuration manquant qui existait dans l'environnement de l'hôte mais n'a pas été explicitement transmis au
container ; ou une image de base avec une version d'OS/de bibliothèques différente de l'hôte, révélant une
dépendance implicitement satisfaite sur l'hôte mais absente de l'image du container (souvent bien plus
minimale, par ex. basée sur Alpine).

**Exemple :**
```yaml
environment:
  - DB_HOST=localhost   # signifiait "cette même machine" sur l'hôte ; dans le container cela
                         # se résout vers le network namespace du container lui-même, pas la DB
```

**Pourquoi c'est un piège :** supposer que « le code est identique, donc l'environnement doit l'être aussi » —
le network namespace, le filesystem et l'image de base d'un container sont des contextes d'exécution réellement différents,
même en exécutant exactement le même code applicatif et le même binaire que sur l'hôte.

### Workloads Kubernetes

#### Q16. Quelle est la différence entre les probes liveness, readiness et startup de Kubernetes, et que se passe-t-il quand elles sont mal configurées ?
**Réponse :** **Liveness** répond à « ce container est-il vivant, ou doit-il être redémarré » — son échec
pousse Kubernetes à tuer et redémarrer le container. **Readiness** répond à « ce container peut-il
actuellement servir du trafic » — son échec retire le pod des endpoints de load-balancing du Service
sans le redémarrer, ce qui est la bonne réaction pour un pod vivant mais temporairement incapable
de servir (chauffe d'un cache, attente d'une dépendance). **Startup** existe pour les applications
à démarrage lent, en retardant le moment où liveness/readiness commencent à être vérifiées, afin qu'un démarrage
légitimement lent ne soit pas pris pour un échec de liveness et tué avant d'avoir fini de booter. La
mauvaise configuration courante : utiliser le même check (ou aucun check, laissant Kubernetes supposer
« ready » immédiatement) pour liveness et readiness — une liveness probe trop agressive
(timeout court, faible failure threshold) sur un pod sous charge temporaire peut déclencher des
redémarrages inutiles d'un pod pourtant sain (une panne auto-infligée), tandis qu'une readiness
probe absente ou triviale envoie du trafic à un pod avant qu'il soit réellement capable de le gérer, provoquant des erreurs
à chaque rollout (S4).

**Exemple :**
```yaml
livenessProbe:
  httpGet: { path: /healthz, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 5
readinessProbe:
  httpGet: { path: /ready, port: 8080 } # vérifie les dépendances/le warm-up, pas seulement "le processus est up"
  periodSeconds: 5
```

**Pourquoi c'est un piège :** réutiliser le même check superficiel (« le processus répond ») pour liveness et
readiness traite deux questions différentes — « ceci doit-il être redémarré » vs. « ceci doit-il recevoir du
trafic » — comme une seule ; une liveness probe agressive construite comme un check de readiness peut redémarrer un
pod sain mais occupé, transformant un pic de charge en panne auto-infligée.

#### Q17. Que se passe-t-il si un Pod Kubernetes n'a ni resource requests ni limits ?
**Réponse :** Sans **request** (la quantité que le scheduler réserve pour ce pod sur un node), le
scheduler n'a aucune base réelle pour empiler les pods de façon sensée, et un pod sans requests est traité
comme de plus basse priorité (classe QoS `BestEffort`) — le premier à être évincé sous pression mémoire du node,
même s'il s'agit en réalité d'un workload important. Sans **limit** (le plafond strict appliqué à
l'exécution), un pod peut consommer une mémoire/un CPU illimités sur son node — une fuite mémoire dans un pod non borné
peut affamer tous les autres pods du node (« noisy neighbor », S11) au lieu d'être contenue à
lui-même, et peut finir par déclencher l'OOM killer du node, qui ne tue pas forcément
le pod fautif en particulier. Définir les deux délibérément (avec des limits confortablement au-dessus de l'usage attendu
en régime établi, mais bornées) est ce qui donne à Kubernetes l'information dont il a besoin pour scheduler
équitablement et contenir la défaillance d'un workload à lui-même.

**Exemple :**
```yaml
resources:
  requests: { memory: "256Mi", cpu: "250m" }
  limits: { memory: "512Mi", cpu: "500m" }
# Omettez entièrement ce bloc et le pod est en QoS BestEffort — évincé en premier, et libre de
# consommer des ressources illimitées sur son node en attendant.
```

**Pourquoi c'est un piège :** traiter les resource requests/limits comme un réglage optionnel plutôt que comme une
entrée de scheduling obligatoire — « ça marche très bien sans en dev » est vrai jusqu'à ce que la vraie contention
sur les nodes expose les deux modes de défaillance à la fois (éviction inéquitable, noisy-neighbor).

#### Q18. Comment le Horizontal Pod Autoscaler (HPA) décide-t-il de scaler, et quelle est une mauvaise configuration courante ?
**Réponse :** Le HPA compare périodiquement une métrique cible (couramment l'utilisation CPU ou mémoire, ou
une métrique custom comme la profondeur de file de requêtes) à une valeur cible configurée, et calcule un
nombre de replicas souhaité à peu près proportionnel à l'écart entre l'usage courant et la cible. Une mauvaise
configuration courante : le HPA scale sur l'utilisation CPU, mais le pod n'a pas de *request* CPU défini
(Q17) — le pourcentage d'utilisation est calculé relativement à la request, donc sans request définie,
le HPA n'a aucune base significative pour calculer et soit ne scale pas du tout, soit se comporte de
façon imprévisible. Autre problème courant : scaler sur une métrique qui ne corrèle pas réellement avec le
vrai goulot d'étranglement (scaler sur le CPU alors que le service est en fait I/O-bound et bloqué en attente d'un
appel aval, si bien que le CPU ne franchit jamais le seuil même alors que le service est réellement
submergé) — la solution est alors de scaler sur une métrique custom qui reflète réellement la charge (débit de requêtes,
profondeur de file) plutôt que de prendre le CPU par défaut parce que c'est l'option intégrée.

**Exemple :**
```
$ kubectl get hpa orders-hpa
NAME         REFERENCE           TARGETS         MINPODS   MAXPODS   REPLICAS
orders-hpa   Deployment/orders   <unknown>/70%   2         10        2
```
`<unknown>` comme valeur courante signifie que le HPA n'a pas de base de CPU request sur le pod pour calculer
l'utilisation — il ne scalera jamais depuis cet état, quelle que soit la charge du service.

**Pourquoi c'est un piège :** supposer que « le HPA est configuré, donc l'autoscaling fonctionne » — un HPA qui scale sur le
CPU sans CPU request défini, ou qui scale sur le CPU pour un service réellement I/O-bound, peut silencieusement
ne jamais se déclencher, et cet écart reste invisible jusqu'à ce qu'un vrai pic de trafic le révèle.

#### Q19. Expliquez un rolling update Kubernetes et comment `maxSurge`/`maxUnavailable` interagissent avec le graceful shutdown.
**Réponse :** Un rolling update remplace les pods de l'ancienne version par des pods de la nouvelle version de façon incrémentale plutôt
qu'en une seule fois : `maxSurge` contrôle combien de pods supplémentaires au-delà du nombre souhaité peuvent être créés
temporairement pendant le rollout (plus haut = rollout plus rapide, plus de marge de ressources nécessaire), et
`maxUnavailable` contrôle combien de pods peuvent être indisponibles en même temps pendant la transition (plus haut =
rollout plus rapide, plus de réduction de capacité tolérée entre-temps). L'interaction avec le graceful
shutdown (Q22/S16 du module 2) compte au moment où un ancien pod est terminé : Kubernetes envoie
`SIGTERM`, et le pod dispose de `terminationGracePeriodSeconds` pour terminer les requêtes en cours et s'arrêter
avant qu'un `SIGKILL` brutal ne suive — mais le pod est aussi retiré des endpoints du Service dans
le cadre de ce processus, et si ce retrait d'endpoint n'est pas correctement séquencé *avant* que les nouvelles
connexions cessent d'y être routées (un hook `preStop` ajoutant un bref délai avant que l'app ne commence réellement
à s'arrêter est la mitigation standard), il existe une fenêtre où le load balancer peut
encore router du nouveau trafic vers un pod qui a déjà cessé de l'accepter, provoquant une rafale d'erreurs
à chaque rollout.

**Exemple :**
```yaml
lifecycle:
  preStop:
    exec: { command: ["sleep", "5"] } # laisse au Service le temps de désenregistrer d'abord ce pod
terminationGracePeriodSeconds: 30
```

**Pourquoi c'est un piège :** supposer que `SIGTERM` seul suffit pour un rollout sans erreur — sans un bref
délai `preStop`, le pod peut cesser d'accepter les connexions avant que le Service ait fini de le retirer
de sa liste d'endpoints, provoquant une rafale d'erreurs à chaque déploiement.

#### Q20. Pourquoi l'adresse IP d'un Pod Kubernetes n'est-elle pas une valeur stable sur laquelle s'appuyer, et que fournit un Service à la place ?
**Réponse :** Les pods sont éphémères par conception — un Deployment peut recréer un pod (lors d'un crash, d'un rolling
update, d'une panne de node) à tout moment, et le nouveau pod reçoit une nouvelle adresse IP ; coder en dur ou mettre en cache
une IP de pod où que ce soit finira forcément par casser. Un **Service** fournit une IP virtuelle stable
et un nom DNS qui répartissent la charge entre les pods qui correspondent actuellement à son label selector,
en se mettant à jour automatiquement au fil des arrivées et départs de pods — les clients ciblent le Service, jamais un pod directement.
`ClusterIP` (le défaut) n'est joignable qu'au sein du cluster ; `NodePort` expose le service sur
un port statique de chaque node, joignable depuis l'extérieur du cluster ; `LoadBalancer` provisionne un
véritable load balancer externe (via le cloud provider) pointant vers le service, la façon standard
d'exposer un service sur internet.

**Exemple :**
```yaml
apiVersion: v1
kind: Service
metadata: { name: orders-svc }
spec:
  selector: { app: orders }
  ports: [{ port: 80, targetPort: 8080 }]
# Les clients ciblent "orders-svc" — jamais l'IP d'un pod précis, qui change à chaque recréation.
```

**Pourquoi c'est un piège :** mettre en cache ou coder en dur une IP de pod où que ce soit « parce qu'elle était stable pendant mes
tests » — les IPs de pod changent forcément au prochain reschedule, et le code qui suppose le
contraire fonctionne jusqu'au premier rolling update ou à la première panne de node.

#### Q21. Comment garder un service Kubernetes disponible pendant les node drains et les pannes de zone (PodDisruptionBudget, anti-affinity, topology spread) ?
**Réponse :** Trois types de pannes différents nécessitent trois outils différents. Les **disruptions volontaires** — un node drain pour
une mise à jour, un scale-down du cluster autoscaler — évincent des pods délibérément ; un **PodDisruptionBudget** (`minAvailable` ou
`maxUnavailable`) indique à l'eviction API de refuser une éviction qui ferait passer le service sous le budget, de sorte que
le drain progresse node par node sans réduire la capacité. Un PDB ne fait *rien* contre les pannes involontaires (un node qui plante,
des OOM kills). Pour survivre à la **perte d'un node ou d'une zone**, les replicas ne doivent pas tous atterrir dans le même domaine de défaillance : `podAntiAffinity`
(hard `required...` ou soft `preferred...`) ou mieux, `topologySpreadConstraints` avec `topologyKey: topology.kubernetes.io/zone` et
`maxSkew: 1` répartissent les pods uniformément et continuent à le faire pendant les rollouts. À combiner avec `replicas >= 3`, des readiness probes correctes, et
un graceful shutdown (Q19). Pièges : un PDB avec `minAvailable: 100%` ou égal au nombre de replicas rend le node
**impossible à drainer** et bloque les mises à jour (S21) ; un Deployment à un seul replica plus un PDB pose le même problème ; une anti-affinity hard avec
plus de replicas que de nodes laisse des pods en `Pending` ; et les règles de spread ne s'appliquent qu'au moment du *scheduling*, donc elles ne rééquilibrent pas les pods existants
quand des nodes vont et viennent (c'est le descheduler qui s'en charge).

**Exemple :**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: { name: orders }
spec:
  maxUnavailable: 1              # jamais moins de replicas-1 pendant les drains
  selector: { matchLabels: { app: orders } }
---
# dans le pod spec du Deployment
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway     # DoNotSchedule si le spread est une exigence stricte
    labelSelector: { matchLabels: { app: orders } }
```

**Pourquoi c'est un piège :** des équipes font tourner 3 replicas, se sentent en sécurité, et perdent le service parce que le scheduler a mis les trois sur un même node,
ou « durcissent » avec un PDB trop strict qui bloquera plus tard toutes les mises à jour du cluster à 2 h du matin. La haute disponibilité est une propriété de la
*politique de placement et de disruption*, pas du nombre de replicas.

#### Q22. Quelle est la différence entre un ConfigMap et un Secret Kubernetes, et quelle est l'idée fausse courante sur la sécurité des Secrets ?
**Réponse :** Les deux stockent de la configuration clé-valeur injectée dans les pods (en variables d'environnement ou en
fichiers montés) ; la distinction voulue est qu'un ConfigMap contient de la configuration non sensible et
un Secret des données sensibles (credentials, tokens, clés). L'idée fausse courante : les valeurs d'un
Secret sont *encodées* en base64, pas chiffrées — quiconque a un accès en lecture à l'objet Secret
via l'API Kubernetes (ou `kubectl get secret -o yaml`) peut trivialement le décoder en
clair, donc un Secret seul n'offre aucune confidentialité face à quiconque dispose d'un accès RBAC suffisant au cluster,
seulement une légère obfuscation contre l'exposition accidentelle. Une vraie protection exige
d'activer le chiffrement au repos des Secrets dans etcd (pas le défaut dans toutes les configurations de cluster), de
restreindre strictement l'accès RBAC aux Secrets, et, pour de meilleures garanties, d'intégrer un véritable
gestionnaire de secrets (Vault, secret stores des cloud providers) plutôt que de s'appuyer sur l'objet Secret de base comme s'il
était intrinsèquement chiffré.

**Exemple :**
```
$ kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d
SuperSecretPassword123
```

**Pourquoi c'est un piège :** considérer que « c'est stocké comme un Secret » suffit comme protection —
sans chiffrement au repos ni RBAC strict, un Secret est à un `kubectl get` du texte en clair pour
quiconque a un accès en lecture au cluster.

#### Q23. Quel problème Helm résout-il par rapport aux manifests Kubernetes bruts ?
**Réponse :** Les manifests YAML bruts dupliquent du boilerplate entre environnements (dev/staging/prod ayant chacun
besoin de fichiers Deployment/Service/ConfigMap quasi identiques ne différant que par une poignée de valeurs)
et n'ont aucune notion intégrée de « release » — pas de moyen simple d'installer, mettre à jour ou rollback un
ensemble de ressources liées comme une unité versionnée. Helm templatise les manifests
(en paramétrant les différences dans un `values.yaml` par environnement) et suit chaque
install/upgrade comme une release numérotée, supportant `helm rollback` vers une release précédente en une seule
commande plutôt que de reconstituer manuellement l'état du manifest précédent. Le compromis
est une complexité ajoutée (une couche de templating avec son propre outillage/courbe d'apprentissage) qui vaut la peine dès que
la même application doit être déployée dans plusieurs environnements ou plusieurs fois avec
des variations — pour un déploiement unique, simple et rarement modifié, les manifests bruts peuvent rester le choix
le plus simple.

**Exemple :**
```
$ helm upgrade orders ./chart -f values-prod.yaml
$ helm rollback orders 4   # retour à la révision 4 de la release, une seule commande
```

**Pourquoi c'est un piège :** adopter Helm (ou toute couche de templating) pour un déploiement unique, simple et rarement modifié
ajoute une vraie complexité sans bénéfice correspondant — sa valeur n'apparaît que lorsque le
même chart est déployé dans plusieurs environnements ou plusieurs fois avec de réelles variations.

### Delivery & debugging

#### Q24. De quelles étapes un bon pipeline CI/CD a-t-il besoin, et que signifie « fail fast » dans ce contexte ?
**Réponse :** Grosso modo, par ordre croissant de coût/temps : lint/analyse statique et tests unitaires rapides d'abord
(les moins chers, ils attrapent les erreurs les plus courantes en quelques secondes), puis une étape de build/compilation, puis
des tests d'intégration (plus lents, ils ont besoin de vraies dépendances comme une base de données), puis le scan de sécurité/dépendances,
puis un déploiement en staging avec des smoke tests, puis le déploiement réel en production
(souvent conditionné à un canary ou à une approbation manuelle pour les services critiques). « Fail fast »
signifie ordonner les étapes pour que les checks les moins chers et les plus susceptibles de détecter quelque chose s'exécutent en premier — un échec de lint
doit échouer en quelques secondes, pas après avoir attendu la fin d'une suite de tests d'intégration de 20 minutes —
afin que les développeurs aient un feedback le plus vite possible et que des ressources coûteuses ne soient pas
gaspillées à exécuter les étapes suivantes sur un changement qui allait déjà échouer à un check antérieur, moins cher.

**Exemple :**
```yaml
stages: [lint, unit-test, build, integration-test, security-scan, deploy-staging, deploy-prod]
# lint/unit-test s'exécutent en premier et finissent en quelques secondes ; integration-test et deploy sont en dernier et
# les plus coûteux — un échec de lint ne devrait jamais attendre derrière une suite de tests de 20 minutes.
```

**Pourquoi c'est un piège :** ordonner les étapes du pipeline selon leur date d'ajout historique plutôt que selon
leur coût — une étape coûteuse de tests d'intégration exécutée avant un check de lint bon marché gaspille des minutes de CI
et du temps de feedback développeur à chaque changement dont le lint échoue.

#### Q25. Comparez les stratégies de déploiement blue-green, canary et rolling.
**Réponse :** Le **Rolling** (le défaut de Kubernetes, Q19) remplace incrémentalement les anciens pods par des nouveaux
— simple, économe en ressources (pas besoin de faire tourner deux environnements complets simultanément), mais le rollback
consiste à défaire la mise à jour de la même façon incrémentale, et une mauvaise version sert *une partie* du
trafic pendant toute la durée du rollout avant d'être détectée. Le **Blue-green** fait tourner deux environnements complets et
indépendants (blue = actuel, green = nouveau) et bascule tout le trafic d'un coup
(typiquement au niveau du load balancer/DNS) une fois le nouvel environnement vérifié — le rollback est
une simple bascule inverse du trafic, quasi instantanée, mais il exige de faire tourner le double de l'infrastructure
simultanément pendant la transition, et tout composant stateful (un schéma de base de données, S15) doit
encore être compatible avec les deux environnements pendant la bascule. Le **Canary** route un petit
pourcentage du trafic réel vers la nouvelle version d'abord, observe les vraies metrics/erreurs de ce
sous-ensemble, et augmente progressivement le pourcentage si tout va bien (ou rollback immédiatement le canary
sinon) — le meilleur signal réel avant un rollout complet, au prix d'une plus grande complexité de déploiement
et de l'exigence que les deux versions coexistent sans danger pendant la durée (le piège de compatibilité de schéma de la S12
s'applique ici aussi).

**Exemple :**
```
Rolling:    old -> [old,new] -> [new] over N steps        (exposition partielle pendant le rollout)
Blue-green: [blue] -> [blue,green verified] -> [green]    (bascule instantanée, double infra)
Canary:     [old 95%, new 5%] -> ... -> [new 100%]        (validation d'abord sur du trafic réel)
```

**Pourquoi c'est un piège :** choisir une stratégie parce que c'est « la moderne » (canary, blue-green)
sans tenir compte de son coût réel — la double infrastructure et la charge de compatibilité de schéma du blue-green, ou
l'exigence de coexistence sûre des deux versions du canary — peut être pire
qu'un rolling update bien testé pour un système qui n'a pas réellement besoin de cette sécurité supplémentaire.

#### Q26. Comment utiliser `git bisect` pour trouver quel commit a introduit une régression ?
**Réponse :** `git bisect start`, puis marquez un commit connu comme mauvais (`git bisect bad <hash>`, souvent simplement
`HEAD` ou l'état cassé actuel) et un commit connu comme bon (`git bisect good <hash>`, un point
antérieur à l'existence du bug) — git checkout le commit médian entre les deux, vous le testez et
indiquez `git bisect good` ou `git bisect bad`, en répétant jusqu'à ce que git isole le commit exact
qui a introduit la régression, en O(log n) étapes plutôt que de vérifier chaque commit
individuellement. Si l'étape de « test » (ce commit présente-t-il le bug) peut être scriptée (un test
en échec précis, une commande avec un code de sortie distinguable), `git bisect run <command>` automatise
tout le processus de bout en bout sans cycles manuels de checkout/test/report. `git bisect reset`
ramène le dépôt à son état d'origine une fois le commit coupable identifié.

**Exemple :**
```
$ git bisect start
$ git bisect bad HEAD
$ git bisect good v2.3.0
$ git bisect run ./run-failing-test.sh
```

**Pourquoi c'est un piège :** examiner à l'œil « lequel de ces 200 commits semble suspect » au lieu de
bisecter gaspille exactement l'avantage en log n que bisect offre gratuitement — et sauter
`git bisect run` au profit de cycles manuels de checkout/test transforme un processus scriptable en 8 étapes en un
processus manuel lent et sujet aux erreurs.

### Observabilité

#### Q27. Mettez en pratique les trois piliers de l'observabilité — à quoi ressemble concrètement le « bon » pour chacun ?
**Réponse :** **Structured logging** : émettre les logs sous forme de données structurées (JSON, pas du texte libre) avec
des champs cohérents (un ID de requête/trace, le nom du service, la sévérité) afin qu'ils soient consultables et
corrélables entre services, et pas seulement lisibles par un humain un à un. **Metrics** : la méthode RED
pour les services pilotés par requêtes (Rate, Errors, Duration — par endpoint) et la méthode USE pour
les ressources (Utilization, Saturation, Errors — par CPU/mémoire/disque/file) donnent une checklist structurée et
reproductible de ce qu'il faut instrumenter, plutôt qu'une collection ad hoc de metrics qui
semblaient intéressantes sur le moment. **Distributed tracing** : propager un trace ID à travers
chaque hop (headers HTTP, métadonnées de message pour les hops asynchrones — contenu messagerie du module 4) en utilisant un
standard (OpenTelemetry) afin que le chemin complet et le timing d'une requête à travers les services soient
reconstituables, et pas seulement la vue isolée de chaque service.

**Exemple :**
```json
{"ts":"2024-03-11T10:00:00Z","level":"error","service":"orders","traceId":"a1b2c3","msg":"payment failed"}
```

**Pourquoi c'est un piège :** traiter « on a des logs » comme équivalent à « on a de l'observabilité » —
des logs non structurés et intraçables, sans trace ID partagé entre services, vous laissent toujours corréler à la main
des timestamps à travers une douzaine de services pendant un incident, exactement le mode de défaillance de
diagnostic lent que le structured logging plus le tracing existent pour éliminer.

## 🔴 Expert / Ouvert

### Delivery

#### Q28. Concevez un pipeline CI/CD et une stratégie de déploiement pour un service de paiement critique qui exige zéro downtime et un rollback rapide.
Pipeline : analyse statique rapide et tests unitaires d'abord (fail fast, Q24), puis tests d'intégration
contre une vraie base de données (containerisée, éphémère) et les mocks aval critiques, puis un
scan de sécurité/dépendances (les services de paiement sont une cible naturelle pour les attaques de supply chain, ce qui rend le scan de
vulnérabilités des dépendances non négociable), puis build d'un artefact versionné et immuable (une
image de container taguée, jamais `latest`) qui est le *même* artefact promu à travers chaque
environnement plutôt que reconstruit par environnement (éliminant « buildé différemment en prod » comme
classe de défaillance). Stratégie de déploiement : canary (Q25) spécifiquement pour un service critique de paiement,
en routant d'abord un petit pourcentage du trafic réel et en surveillant le taux d'erreur/la latence par rapport à des seuils de rollback
stricts et automatisés (pas seulement le jugement humain) avant d'augmenter progressivement le trafic
— combiné à la discipline de migration additive de la Q32 du module 3 pour que le schéma de base de données soit
compatible avec l'ancienne et la nouvelle version pendant toute la fenêtre du canary. Le rollback doit être une
commande unique, rapide et testée (rediriger le trafic vers la version précédente, c'est pourquoi les
pods de la version précédente ne sont souvent pas détruits immédiatement après un rollout, précisément pour rendre le
rollback quasi instantané) plutôt qu'un retour en arrière manuel et sujet aux erreurs. L'observabilité (Q27) avec un
alerting strict sur le chemin critique de paiement est ce qui rend fiable, au départ, le seuil de rollback automatisé
du canary — toute cette conception ne vaut que ce que vaut le signal à partir duquel elle prend ses décisions de
rollback.

#### Q29. Comment concevriez-vous la promotion d'environnement (dev → staging → production) pour que ce que vous avez testé soit exactement ce que vous livrez ?
Le principe est **build once, promote the same artifact** : le pipeline CI construit une image de container immuable par commit,
la tague avec le SHA du commit (jamais `latest`), la pousse et la signe ; chaque environnement
déploie ensuite *ce digest* et ne diffère que par la **configuration** injectée au moment du déploiement (fichiers de values, ConfigMaps, secrets issus d'un
gestionnaire de secrets) — jamais par une reconstruction pour chaque environnement, ce qui signifierait que la production exécute un binaire que personne n'a testé. La promotion est un
changement dans Git, pas un clic : avec une approche GitOps (Argo CD/Flux) chaque environnement a un répertoire ou une branche avec le digest d'image
souhaité et les values, et « promouvoir » est une pull request relue (ou automatisée une fois les gates franchies) qui incrémente la version dans l'
environnement suivant, ce qui donne une piste d'audit et un rollback en une ligne (revert). Les gates entre environnements doivent être automatisées
et pertinentes : le staging exécute les tests d'intégration/contract et les smoke tests ainsi que la migration de DB sur un jeu de données à l'image de la production ; la production
déploie progressivement (canary avec analyse automatique du taux d'erreur et de la latence, Q25) et s'arrête ou fait un rollback en cas de régression du SLO.
Gardez les environnements aussi similaires que possible en pratique (mêmes manifests, même chart Helm, values différentes), utilisez des environnements de preview
éphémères par pull request pour le feedback, et traitez les migrations de base de données comme une étape séparée et rétrocompatible
(expand → migrate → contract, S15) pour que l'application et le schéma puissent faire un rollback indépendamment. Compromis : un
staging identique coûte cher, donc décidez ce qui nécessite vraiment la parité (versions, topologie, volume de données) et acceptez le reste ; les branches
divergentes de longue durée par environnement créent de la dérive, donc préférez le trunk-based development avec des feature flags pour séparer le *deploy* de la *release*.

### Fiabilité & observabilité

#### Q30. Concevez de zéro la stack d'observabilité d'une nouvelle plateforme de microservices.
Standardisez l'instrumentation *avant* que les services ne se multiplient — adoptez OpenTelemetry comme standard
commun à tous les services pour les traces et les metrics dès le premier jour (rétrofiter un tracing cohérent
sur un parc déjà fragmenté et important coûte bien plus cher que de partir cohérent), avec
chaque service propageant le contexte de trace à travers les frontières synchrones (headers HTTP) et asynchrones
(métadonnées de message, module 4). Un structured logging (Q27) expédié vers un
agrégateur central (plutôt que des logs de chaque service vivant uniquement sur son propre host/pod, inaccessibles une fois
ce pod disparu) avec un schéma cohérent incluant le trace ID, de sorte qu'une trace précise puisse être
recoupée directement avec ses lignes de log correspondantes dans chaque service traversé. Des metrics
suivant RED/USE (Q27) collectées centralement (Prometheus ou équivalent) avec des dashboards construits autour de
véritables service-level objectives (SLOs) plutôt qu'un mur brut de toutes les metrics disponibles, et
un alerting lié à ces SLOs (basé sur les symptômes : « le budget d'erreurs/de latence est en train de brûler »,
détecté à partir de l'impact côté utilisateur) plutôt que des alertes purement basées sur les causes (une metric
interne précise franchissant un seuil qui peut ou non avoir un impact utilisateur réel) — l'alerting
basé sur les symptômes passe bien mieux à l'échelle quand le nombre de services croît, puisqu'il n'exige pas d'anticiper
et d'alerter individuellement sur chaque mode de défaillance interne possible. La décision précoce au plus fort levier
est le standard de tracing et la discipline de propagation, puisque tous les autres piliers
gagnent énormément en valeur dès que les traces permettent de recouper logs et metrics avec le chemin réel
d'une requête précise.

#### Q31. Comment les SLOs et les error budgets peuvent-ils piloter les décisions de release, et que faire quand le budget est épuisé ?
Un **SLI** est un indicateur mesuré de la qualité visible par l'utilisateur (la fraction de requêtes qui réussissent et se terminent en moins de 300 ms), un
**SLO** est la cible associée sur une fenêtre (99,9 % sur 30 jours), et l'**error budget** est la défaillance autorisée restante
(0,1 % ≈ 43 minutes d'indisponibilité totale par mois). Le budget transforme le débat « livrer plus vite » vs « être plus fiable » en une règle partagée et fondée sur les données :
tant qu'il reste du budget, les équipes peuvent prendre des risques — déployer souvent, mener des expériences, faire des migrations ; quand il brûle trop vite, les releases de
fonctionnalités ralentissent et l'effort d'ingénierie se déplace vers le travail de fiabilité jusqu'à sa récupération. Pour le rendre opérationnel : définir les SLIs du point de vue de l'utilisateur (pas du CPU),
alerter sur le **burn rate** avec plusieurs fenêtres (un burn rapide déclenche une page immédiate, un burn lent ouvre un ticket) plutôt que sur des seuils bruts
qui oscillent (S22), et laisser le pipeline de déploiement consulter le budget — la progressive delivery arrête un canary qui consomme trop vite du budget
(Q25). Convenez au préalable de la **politique** en cas d'épuisement (geler les releases non critiques, prioriser les action items du postmortem) et faites-la signer par la direction produit
et ingénierie, sinon elle reste sans mordant. Pièges : un SLO à 99,99 % dont personne n'a besoin (chaque neuf supplémentaire coûte de façon disproportionnée
plus cher), des SLOs sur des composants internes que aucun utilisateur ne remarque, des budgets jamais appliqués, et une mesure côté serveur qui ignore ce que
vit le client. Une bonne réponse note aussi qu'un service *trop* fiable (un budget jamais entamé) est un signal pour livrer plus vite ou assouplir le SLO.

#### Q32. Expliquez comment déboguer de bout en bout un problème « ça marche sur ma machine, ça échoue en CI/production ».
Commencez par établir exactement *où* la divergence se produit — reproduisez l'échec directement dans
l'environnement cible si c'est possible (ne déboguez pas à l'aveugle à partir des seuls logs si vous pouvez obtenir
un shell dans le container/pod en échec). Comparez systématiquement les deux environnements selon les axes
qui diffèrent couramment : variables d'environnement et configuration (Q15, S1/S3 du module 2), versions
d'image de base/OS/bibliothèques si l'un tourne dans Docker et pas l'autre, permissions de fichiers et
propriété des volumes montés, et valeurs par défaut de timezone/locale (une différence silencieuse classique entre la locale
de l'hôte d'un développeur et la locale `C` par défaut d'un container minimal, cassant le parsing de dates ou
le tri de façon subtile). Si la divergence est réellement une régression récente plutôt qu'une
différence d'environnement, `git bisect` (Q26) — exécuté dans l'environnement précis où cela
échoue réellement, pas en local — isole efficacement le commit fautif plutôt que de
relire manuellement un gros diff. Une fois isolé, la correction est généralement l'une des deux : rendre les deux
environnements plus cohérents (faire tourner en local le même environnement containerisé que celui de la CI/
production, supprimant à la source la classe de bugs « ça marche sur ma machine »), ou corriger un
vrai bug dépendant de l'environnement que le code n'aurait pas dû avoir (une hypothèse codée en dur sur la
locale, la timezone ou l'accessibilité réseau).

### Sécurité

#### Q33. Comment gérer les secrets applicatifs dans Kubernetes — Kubernetes Secrets, Vault, ou un external secrets operator ?
Partez des menaces : secrets commités dans Git, secrets lisibles par quiconque a accès au cluster, credentials de longue durée qui ne sont jamais renouvelés,
et absence de piste d'audit. Les objets Kubernetes `Secret` simples sont en base64, pas chiffrés (Q22) : ils nécessitent un chiffrement au repos
(provider KMS), un RBAC strict (qui peut `get secrets` dans un namespace), et ils doivent quand même *provenir* de quelque part — les commiter
dans Git est le mauvais endroit. Les patterns courants gardent la source de vérité dans un gestionnaire externe (AWS Secrets Manager, GCP
Secret Manager, Azure Key Vault, HashiCorp Vault) : l'**External Secrets Operator** (ou le driver CSI Secrets Store) synchronise
des secrets choisis dans le cluster sous forme de `Secret`s ou de fichiers montés, authentifié par l'identité du workload (IRSA/Workload Identity), de sorte qu'aucun credential
statique ne traîne dans les manifests ; **Sealed Secrets/SOPS** permettent de conserver des secrets *chiffrés* dans Git pour le GitOps quand on ne
fait pas tourner de gestionnaire externe. **Vault** va plus loin avec des **credentials dynamiques de courte durée** (un utilisateur de base de données créé à la demande
avec un bail d'1 heure) et des logs d'audit détaillés, au prix de l'exploitation de Vault (HA, unsealing, mises à jour). Règles de conception : donner à chaque workload sa propre identité et le moindre
privilège, préférer les fichiers montés aux variables d'environnement (les env vars fuient dans les crash dumps, `docker inspect` et les processus enfants),
rendre l'application capable de **recharger les secrets renouvelés** sans redéploiement, renouveler selon un calendrier et immédiatement en cas de suspicion de fuite,
et scanner les dépôts et les images à la recherche de secrets commités (S9). Choisir selon la taille de l'équipe : une petite équipe sur un seul cloud est bien servie par le gestionnaire de secrets
du cloud plus External Secrets ; Vault devient rentable quand on a besoin de credentials dynamiques, d'une cohérence multi-cloud et d'exigences d'audit fortes.

## 🎯 Scénarios réels

### S1. Un container meurt de façon répétée avec le code de sortie 137, et les logs ne montrent rien d'utile
- **Symptômes :** `docker ps -a` montre le code de sortie 137 sur un container arrêté brutalement ; aucun
  log applicatif n'a capturé l'arrêt.
- **Diagnostic :** Lancez `docker inspect` sur le container arrêté et vérifiez `State.OOMKilled` — si
  `true`, le container a dépassé sa limite mémoire et l'OOM killer du kernel l'a terminé avec
  `SIGKILL`, ce qui ne laisse aucune occasion de logger quoi que ce soit en partant (Q14).
- **Exemple :**
  ```
  $ docker inspect mycontainer --format '{{.State.OOMKilled}}'
  true
  ```
- **Résolution :** Si l'usage se stabilise sous un plafond raisonnable mais que la limite actuelle est simplement trop
  serrée, augmentez la limite mémoire. Si l'usage croît sans borne dans le temps, c'est une vraie
  fuite mémoire applicative (scénarios de fuites du module 1) qui nécessite une correction du code, pas une augmentation de limite.
- **Prévention :** Faites des load tests avec une pression mémoire réaliste avant de fixer les limites de production, et
  alertez sur la tendance d'usage mémoire qui approche la limite configurée, pas seulement sur l'événement OOMKill
  une fois qu'il s'est déjà produit.

### S2. Une application démarre avec succès mais échoue immédiatement à joindre une dépendance, uniquement quand elle tourne dans un container
- **Symptômes :** Exactement le même code et la même config fonctionnent en exécution directe sur la machine d'un développeur,
  mais dans un container Docker, un appel vers ce qui devrait être « la même base de données/le même service » n'arrive pas à
  se connecter.
- **Diagnostic :** Presque toujours une incohérence d'hypothèse réseau — `localhost` dans le
  container désigne le network namespace du container lui-même, pas l'hôte ni un autre container
  comme ce pourrait être le cas sur du bare metal, et l'adresse réellement joignable de la dépendance dans le
  réseau de containers (un nom de service sur un réseau Docker, ou `host.docker.internal`) est différente.
- **Exemple :**
  ```yaml
  # docker-compose.yml
  services:
    app:
      environment:
        - DB_HOST=localhost   # se résout vers le namespace du container app lui-même, pas vers le service db
    db:
      image: postgres
  # Correction : DB_HOST=db (le nom du service sur le même réseau Docker)
  ```
- **Résolution :** Remplacez la référence `localhost` codée en dur par l'adresse correcte pour le
  contexte réseau réel du container — le nom de service/container de la dépendance si les deux tournent dans
  le même réseau Docker, ou l'adresse de pont vers l'hôte appropriée si elle est réellement sur
  l'hôte.
- **Prévention :** Ne codez jamais `localhost` en dur pour une dépendance dans une configuration destinée à tourner
  en container — rendez toujours l'hôte cible configurable par variable d'environnement, avec une valeur par défaut
  adaptée à chaque environnement.

### S3. Un pod Kubernetes entre de façon répétée en `CrashLoopBackOff`
- **Symptômes :** `kubectl get pods` montre un pod qui redémarre avec un intervalle de backoff croissant, sans jamais
  atteindre un état running stable.
- **Diagnostic :** `kubectl logs <pod> --previous` (les logs de l'instance précédente, crashée, puisque
  l'instance courante n'a peut-être encore rien loggé) montre généralement directement la vraie raison du crash
  — une exception au démarrage, une variable d'environnement/config obligatoire manquante, ou un
  check de dépendance en échec sur lequel l'application plante intentionnellement. Si les logs sont vides, consultez
  `kubectl describe pod` pour la raison de sortie (souvent OOMKilled, même diagnostic que S1, mais au niveau du
  scheduling Kubernetes plutôt que de Docker seul).
- **Exemple :**
  ```
  $ kubectl logs orders-7d9f8-x2k4p --previous
  Error: required env var DATABASE_URL is not set
  $ kubectl describe pod orders-7d9f8-x2k4p | grep -A2 "Last State"
  ```
- **Résolution :** Corrigez l'échec de démarrage sous-jacent identifié dans les logs, ou ajustez les
  limites de ressources s'il s'agit de mémoire, ou corrigez une référence ConfigMap/Secret manquante si c'est là que réside le problème.
- **Prévention :** Échouez vite et *bruyamment* sur une configuration obligatoire manquante au démarrage (un
  message d'erreur clair nommant la config manquante), plutôt qu'un crash générique qui oblige à fouiller
  les logs pour l'identifier — cela transforme une investigation de `CrashLoopBackOff` en une lecture de log de cinq secondes
  au lieu d'un exercice de devinette.

### S4. Pendant un rollout, une rafale d'erreurs `502`/`503` touche les utilisateurs, en corrélation exacte avec l'arrivée de nouveaux pods
- **Symptômes :** Les erreurs explosent spécifiquement pendant les déploiements, pour les requêtes routées vers des pods
  nouvellement créés, et se résorbent une fois le rollout terminé.
- **Diagnostic :** La readiness probe (Q16) ne reflète pas fidèlement le moment où le pod peut réellement
  servir du trafic — soit elle est totalement absente (Kubernetes suppose « ready » immédiatement au
  démarrage du container) soit elle vérifie quelque chose de trop superficiel (le processus est up) plutôt que quelque chose
  qui reflète réellement la disponibilité (dépendances connectées, caches chauffés, le véritable endpoint de santé
  que l'application expose à cet effet).
- **Exemple :**
  ```yaml
  # Totalement absente -> Kubernetes route le trafic dès l'instant où le processus du container démarre :
  # readinessProbe: (none configured)
  ```
- **Résolution :** Ajoutez ou corrigez la readiness probe pour vérifier un endpoint de santé pertinent qui ne
  renvoie un succès que lorsque l'application est réellement capable de servir du trafic (dépendances
  connectées, warm-up requis terminé), afin que Kubernetes ne route pas de trafic vers le pod tant que
  ce n'est pas vrai.
- **Prévention :** Considérez une readiness probe correcte comme une partie obligatoire de la livraison de tout nouveau service,
  testée spécifiquement en observant un rollout sous charge en staging avant de lui faire confiance en
  production — cette classe de bug est invisible jusqu'à ce qu'un vrai rollout sous trafic réel la révèle.

### S5. Un déploiement provoque une rafale d'erreurs précisément au moment où les anciens pods sont terminés, pas quand les nouveaux démarrent
- **Symptômes :** Distinct de S4 — les erreurs corrèlent avec la *terminaison* des pods pendant le rollout, pas avec
  leur démarrage, et touchent des requêtes qui étaient vraisemblablement déjà en cours ou routées à nouveau juste
  au moment où l'ancien pod s'arrêtait.
- **Diagnostic :** C'est la race condition graceful-shutdown/désenregistrement d'endpoint de la Q19 — le load
  balancer/Service n'a pas fini de retirer le pod en cours de terminaison de sa table de routage avant que
  le pod cesse réellement d'accepter des connexions, si bien que certaines requêtes atterrissent sur un pod qui est déjà
  en train de s'arrêter.
- **Exemple :**
  ```yaml
  # preStop delay manquant -> le pod peut cesser d'accepter des connexions avant que le Service
  # ait fini de le désenregistrer :
  terminationGracePeriodSeconds: 30
  # lifecycle.preStop: (none configured)
  ```
- **Résolution :** Ajoutez un hook `preStop` avec un bref sleep avant que l'application ne commence sa propre
  séquence d'arrêt, laissant à la mise à jour des endpoints du Service/load balancer le temps de se propager avant que
  le pod cesse réellement d'accepter de nouvelles connexions, combiné à un `terminationGracePeriodSeconds`
  suffisamment grand pour que les requêtes en cours se terminent.
- **Prévention :** Testez les rollouts sous charge synthétique continue en staging en surveillant spécifiquement
  la garantie d'un taux d'erreur nul sur tout le cycle de déploiement — cette classe de race est facile
  à manquer sans générer délibérément du trafic exactement pendant un déploiement.

### S6. Le volume excessif de requêtes d'un seul client dégrade les temps de réponse de tous les autres clients d'une API partagée
- **Symptômes :** La latence globale de l'API et le taux d'erreur explosent, et l'investigation attribue l'essentiel du
  volume à un client/une clé d'API effectuant bien plus de requêtes que n'importe quel usage normal raisonnable.
- **Diagnostic :** Aucun rate limiting (Q10) n'est en place sur le ou les endpoints concernés, donc le trafic
  excessif d'un client (abusif ou simplement bugué — une boucle de retry sans backoff, cf. le territoire des scénarios des Q du module 1)
  consomme la capacité partagée (thread pool, connexions à la base de données) dont
  tous les autres clients dépendent aussi.
- **Exemple :**
  ```
  # Access log aggregated by API key over the last hour:
  api-key-a7f3: 480,000 requests
  api-key-b2e1: 1,200 requests
  ```
- **Résolution :** Ajoutez immédiatement un rate limiting par client/clé d'API en mitigation (même une limite
  grossière stoppe l'hémorragie), et relancez séparément le client fautif s'il s'agit d'un
  partenaire/d'une intégration connu(e) pour corriger à la source son schéma de retry/de trafic.
- **Prévention :** Le rate limiting par client doit être une partie standard et non optionnelle de la conception de toute
  API exposée au public (ou même interne, multi-équipes) dès le lancement — le rétrofiter pendant
  un incident actif est strictement pire que de l'avoir dès le premier jour.

### S7. Une régression est signalée, mais on ne sait pas lequel des commits des deux derniers mois l'a introduite
- **Symptômes :** Un bug est confirmé présent maintenant et confirmé absent d'un build d'il y a quelques
  mois, mais l'historique intermédiaire compte des centaines de commits et aucun suspect évident.
- **Diagnostic/résolution :** `git bisect start`, marquez le commit actuel `bad` et l'ancien commit connu comme bon
  `good` (Q26) — git checkout le point médian, testez-le (idéalement scripté via
  `git bisect run` contre une reproduction automatisée du bug), marquez `good`/`bad`, et répétez ;
  pour des centaines de commits, cela converge typiquement en moins de 10 étapes (log2 du nombre de commits)
  plutôt que de nécessiter une revue manuelle et linéaire de toute la plage.
- **Exemple :**
  ```
  $ git bisect start
  $ git bisect bad HEAD
  $ git bisect good v3.4.0
  $ git bisect run ./reproduce.sh
  # Converges on the exact commit in ~8 steps instead of reviewing 300 commits by hand.
  ```
- **Prévention :** Gardez des commits raisonnablement petits et ciblés (un bisect qui tombe sur un commit de 2 000 lignes
  touchant une douzaine de choses sans rapport est bien moins utile que celui qui tombe sur un petit commit
  à but unique), et maintenez un moyen rapide et fiable de tester « ce commit précis
  présente-t-il le bug » (une repro automatisée) pour que `git bisect run` puisse automatiser entièrement la recherche au lieu
  d'exiger des tests manuels à chaque étape.

### S8. La CI passe proprement tous les checks, mais la fonctionnalité casse immédiatement en production
- **Symptômes :** Tous les tests automatisés et quality gates sont verts, pourtant la fonctionnalité déployée échoue
  pour de vrais utilisateurs d'une façon qu'aucune suite de tests n'a détectée.
- **Diagnostic :** Cherchez un écart de parité d'environnement entre CI/test et production — un test
  double/mock tenant lieu de dépendance qui se comporte différemment de la vraie en
  production, une config ou un feature flag différent entre test et prod (une fonctionnalité désactivée
  en test mais activée en prod, ou l'inverse), ou simplement une vraie lacune de couverture de test pour le
  chemin précis qui a cassé.
- **Exemple :**
  ```yaml
  # La config CI pointe vers un mock sans application de timeout :
  PAYMENT_GATEWAY_URL: http://mock-gateway:8080
  # La production pointe vers la vraie gateway, qui applique un timeout plus strict que le mock n'a jamais fait.
  ```
- **Résolution :** Reproduisez l'échec avec un nouveau test qui l'aurait détecté (en confirmant la
  vraie lacune, sans se contenter de deviner), corrigez le bug sous-jacent, et évaluez spécifiquement si
  l'environnement de test doit refléter plus fidèlement la production pour la classe de dépendance/config
  qui a causé cet écart.
- **Prévention :** Auditez périodiquement où les environnements de test et de production divergent (dépendances
  mockées, config/feature flags différents) comme un exercice délibéré, plutôt que de
  découvrir chaque écart de façon réactive après qu'il a causé un incident en production.

### S9. Des credentials de base de données issus d'un Secret Kubernetes se retrouvent postés dans un chat d'équipe ou un ticket, traités comme si c'était sûr
- **Symptômes :** Quelqu'un partage la sortie de `kubectl get secret db-creds -o yaml` (ou la valeur décodée
  du base64) dans un canal de chat ou un ticket de support, apparemment en supposant qu'un « Secret » est
  intrinsèquement protégé.
- **Diagnostic :** Cela confirme directement l'idée fausse de la Q22 — le base64 est un encodage, pas un
  chiffrement, trivialement réversible par n'importe qui, et considérer le contenu d'un Secret comme sûr à partager
  parce que « c'est un objet Secret » est exactement le faux sentiment de sécurité contre lequel met en garde la distinction
  base64-pas-chiffré.
- **Exemple :**
  ```
  $ kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d
  SuperSecretPassword123
  ```
- **Résolution :** Renouvelez immédiatement le credential exposé, comme pour tout autre secret divulgué
  (la S10 du module 2 s'applique à l'identique ici), et supprimez/masquez le message partagé quand c'est possible.
- **Prévention :** Formez explicitement l'équipe au fait que les Secrets Kubernetes sont des conteneurs à accès contrôlé, pas
  chiffrés par défaut — activez le chiffrement au repos des Secrets dans le cluster, et
  traitez la valeur décodée de tout Secret avec la même discipline que celle d'un mot de passe en clair,
  sans jamais la coller dans un chat ou un ticket.

### S10. L'autoscaling ne se déclenche pas alors que le service est clairement sous forte charge
- **Symptômes :** La latence et le taux d'erreur grimpent sous fort trafic, mais `kubectl get hpa` montre le
  nombre de replicas inchangé, ou un scaling bien plus lent que ce que la charge justifierait.
- **Diagnostic :** Vérifiez si les pods ont une *request* CPU/mémoire configurée — le pourcentage d'
  utilisation du HPA est calculé relativement à la request, et sans elle, le HPA n'a aucune
  base pour scaler (Q18). Par ailleurs, vérifiez si la metric sur laquelle on scale reflète réellement
  le vrai goulot d'étranglement — si le service est I/O-bound (bloqué sur un appel aval lent)
  plutôt que CPU-bound, l'utilisation CPU peut rester bien sous le seuil de scaling même alors que le
  service est réellement saturé et n'arrive pas à suivre.
- **Exemple :**
  ```
  $ kubectl get hpa orders-hpa
  NAME         REFERENCE           TARGETS         MINPODS   MAXPODS   REPLICAS
  orders-hpa   Deployment/orders   <unknown>/70%   2         10        2
  ```
- **Résolution :** Définissez des resource requests explicites si elles manquent, et passez à (ou ajoutez) une metric
  custom qui corrèle réellement avec la charge (profondeur de file de requêtes, nombre de requêtes en cours)
  si le CPU n'est pas la vraie contrainte.
- **Prévention :** Validez que le HPA se déclenche réellement sous charge réaliste pendant les load
  tests, avant de compter sur lui comme filet de sécurité en production lors d'un vrai pic de trafic —
  « le HPA est configuré » et « le HPA fonctionne réellement pour le profil de charge de ce service » sont
  deux affirmations différentes.

### S11. Un pod défaillant fait ralentir ou évincer des pods sans rapport sur le même node
- **Symptômes :** Une dégradation de performance ou des évictions inattendues touchent des pods qui n'ont rien à
  voir avec un service séparé qui consomme actuellement une mémoire/un CPU anormalement élevés, mais qui sont tous
  colocalisés sur le même node.
- **Diagnostic :** Le pod fautif n'a pas de resource limits (Q17) — il est libre de consommer
  une mémoire/un CPU illimités sur le node, affamant tous les autres pods schedulés là (« noisy neighbor »),
  et selon la classe QoS, un pod `BestEffort` ou de faible priorité sans rapport peut être évincé en premier
  pour soulager la pression sur le node causée entièrement par le pod illimité.
- **Exemple :**
  ```
  $ kubectl top pods --sort-by=memory
  NAME          CPU(cores)   MEMORY(bytes)
  batch-job-x   1800m        7500Mi   <- no limit set, consuming most of the node
  orders-api    120m         180Mi    <- evicted first despite being unrelated and healthy
  ```
- **Résolution :** Définissez une limite mémoire/CPU appropriée sur le pod fautif afin que sa consommation de ressources
  soit contenue à lui-même plutôt qu'au node entier, et corrigez séparément ce qui a
  causé sa consommation anormalement élevée si ce n'est pas un comportement attendu/normal.
- **Prévention :** Exigez des resource requests et limits sur chaque workload déployé comme politique
  (appliquée via un admission controller/policy engine, pas juste un rappel en code review), de sorte qu'un
  workload sans limits ne puisse tout simplement pas être déployé sur un cluster partagé.

### S12. Une release canary cause des erreurs intermittentes qui ne corrèlent nettement ni avec l'ancienne ni avec la nouvelle version seule
- **Symptômes :** Pendant un rollout canary, des erreurs apparaissent sans impliquer clairement l'une ou l'autre version
  individuellement — le même type de requête réussit parfois et échoue parfois, apparemment
  selon le pod sur lequel elle est tombée.
- **Diagnostic :** Les versions canary (nouvelle) et stable (ancienne) tournent simultanément et ne sont
  en fait pas compatibles entre elles à une frontière partagée — typiquement un changement de contrat
  d'API/de schéma, ou un schéma de base de données partagé que seule l'une des deux versions attend (territoire de la Q32 du
  module 3, mais révélé par un canary plutôt que par un rolling update) — de sorte que le comportement précis
  dépend de la version du pod qui a traité une requête donnée ou de la version dont l'hypothèse
  sur l'état partagé a été violée.
- **Exemple :**
  ```java
  // La version stable attend : record ReserveRequest(String orderId, int quantity)
  // Le canary exige désormais un champ supplémentaire que le deserializer de la version stable rejette :
  record ReserveRequest(String orderId, int quantity, String warehouseId) {}
  // Le pod qui traite une requête donnée détermine si elle réussit ou échoue.
  ```
- **Résolution :** Faites un rollback du canary immédiatement (c'est exactement le mode de défaillance que les
  déploiements canary sont conçus pour détecter avant un rollout complet), et redessinez le changement pour qu'il soit réellement
  rétro/proactivement compatible pendant toute la durée où les deux versions doivent coexister, avant de retenter
  le canary.
- **Prévention :** Vérifiez explicitement la compatibilité entre la nouvelle et l'ancienne version pour chaque
  dépendance partagée (contrats d'API, schéma de base de données, formats de message) comme check obligatoire avant tout
  déploiement canary ou blue-green qui exige la coexistence des deux versions, même brève — ce
  n'est pas optionnel simplement parce que la fenêtre de coexistence est courte.

### S13. Une panne est diagnostiquée lentement parce qu'on ne sait pas lequel des nombreux services du chemin de requête est réellement responsable
- **Symptômes :** Un incident visible par les utilisateurs est confirmé, mais avec une douzaine de microservices dans le
  chemin de requête et chaque équipe ne consultant que les dashboards de son propre service, personne ne peut rapidement
  localiser l'origine réelle de la panne.
- **Diagnostic :** Il n'existe aucune observabilité centralisée et corrélable entre les services — les logs
  vivent uniquement par service sans trace ID partagé les reliant, et il n'y a pas de distributed
  tracing pour montrer le chemin réel de la requête et où elle a échoué ou ralenti (la S15 du module 2 au niveau du
  code applicatif, mais ici c'est la lacune d'infrastructure à l'échelle de la plateforme qui en est la cause).
- **Exemple :**
  ```
  service-a.log: 10:02:01.442 request received
  service-b.log: 10:02:01.503 forwarded to inventory
  # No shared trace ID -> no way to confirm these two lines even belong to the same request.
  ```
- **Résolution :** Une fois diagnostiqué par comparaison manuelle de logs entre équipes (lent, mais la seule option
  sans tracing déjà en place), corrigez l'incident immédiat, et considérez cet incident comme le déclencheur pour
  implémenter réellement le distributed tracing à l'échelle de la plateforme.
- **Prévention :** Construisez la stack d'observabilité (Q30) — propagation de trace cohérente, structured
  logging centralisé, metrics RED/USE — avant que la plateforme n'atteigne une échelle où cette
  investigation devient routinière et coûteuse ; la rétrofiter après plusieurs de ces incidents
  coûte bien plus cher que de l'intégrer dès une échelle plus petite et précoce.

### S14. Les images Docker ont grossi au point de ralentir sensiblement les exécutions du pipeline CI/CD et les déploiements
- **Symptômes :** Les temps de build, de push et de pull de l'image Docker de l'application ont augmenté
  régulièrement, ajoutant de vraies minutes à chaque exécution CI et à chaque déploiement.
- **Diagnostic :** Vérifiez si l'image finale inclut la toolchain de build complète (un JDK plus
  le cache de dépendances Maven, `node_modules` avec les devDependencies, des compilateurs) plutôt que seulement
  l'artefact runtime — une cause courante est un Dockerfile single-stage qui build et exécute dans la même
  image, transportant le poids du build jusque dans l'artefact livré.
- **Exemple :**
  ```
  $ docker images | grep myapp
  myapp   latest   1.8GB   <- includes the full JDK, Maven cache, and devDependencies
  ```
- **Résolution :** Passez à un build multi-stage (Q13) — build dans un stage avec la toolchain complète, puis
  copie de l'artefact final seul dans une image de base runtime minimale, réduisant considérablement la taille de l'image
  finale sans changer les capacités propres du processus de build.
- **Prévention :** Faites des Dockerfiles des nouveaux services un pattern multi-stage par défaut dès le départ, et
  suivez la taille de l'image comme une metric en CI (échec ou avertissement sur une augmentation inattendue importante)
  de la même façon qu'on pourrait suivre le temps de build ou la taille du bundle.

### S15. Après le rollback d'un déploiement blue-green, l'application échoue toujours, car le schéma de base de données qu'elle attend ne correspond pas à ce qui tourne réellement
- **Symptômes :** Un rollback vers la version applicative précédente (blue) est censé corriger instantanément
  un problème trouvé dans la nouvelle version (green), mais la version restaurée échoue maintenant contre la
  base de données, qui avait déjà été migrée pour les exigences de schéma de la version green.
- **Diagnostic :** L'étape de migration du déploiement n'a pas été conçue en pensant au rollback — la migration
  de schéma de la nouvelle version a été appliquée et n'est pas rétrocompatible avec les attentes de l'ancienne version, donc « rollback l'application » seul ne restaure pas
  un état pleinement fonctionnel, puisque la base de données est toujours dans le nouveau schéma.
- **Exemple :**
  ```sql
  -- Appliqué pour green, pas sûr pour blue, qui lit/écrit encore cette colonne :
  ALTER TABLE orders DROP COLUMN legacy_status;
  ```
- **Résolution :** Soit faire aussi un rollback de la migration de base de données (risqué et pas toujours possible si
  des données ont été écrites entre-temps dans la forme du nouveau schéma), soit — l'approche la plus sûre —
  redessiner la migration pour qu'elle soit additive et rétrocompatible dès le départ (pattern de la Q32 du
  module 3), afin que l'ancienne version de l'application continue de fonctionner correctement contre le schéma
  déjà migré sans nécessiter de rollback au niveau de la base de données.
- **Prévention :** Traitez « cette migration est-elle sûre pour que la version applicative précédente continue de
  tourner dessus, en cas de rollback » comme une question obligatoire pour toute migration livrée
  avec un déploiement blue-green ou canary — une stratégie de déploiement qui suppose un rollback instantané ne le
  délivre réellement que si chaque changement de schéma qui l'accompagne a été conçu de la même
  façon.

### S16. Une bascule de load balancer pendant un cutover blue-green coupe brutalement les connexions client de longue durée
- **Symptômes :** Des clients avec des connexions longues ou sticky (sessions WebSocket, requêtes de long-polling,
  connexions épinglées à un backend précis par session affinity) sont brutalement
  déconnectés au moment exact où le trafic est basculé de blue à green, alors que le
  cutover était par ailleurs « instantané ».
- **Diagnostic :** Le cutover a correctement redirigé les nouvelles connexions, mais n'a pas tenu compte des connexions
  *existantes* de longue durée encore attachées à l'ancien environnement (blue) — une bascule instantanée
  du trafic au niveau du load balancer ne draine pas proprement des connexions censées persister des minutes ou des heures,
  elle cesse simplement de router vers blue immédiatement, ce qui les tue de fait.
- **Exemple :**
  ```
  # Au cutover, le load balancer cesse immédiatement de router vers blue — un client WebSocket
  # en pleine session sur blue reçoit un connection reset brutal, pas une frame de fermeture propre.
  ```
- **Résolution :** Pour les connexions déjà en cours, implémentez une période de connection-drain
  — gardez l'environnement blue actif et joignable pour les connexions existantes pendant une fenêtre bornée
  après le cutover (les nouvelles connexions vont immédiatement vers green, les existantes sur blue peuvent
  se terminer ou se reconnecter proprement à green à leur rythme) plutôt qu'un cutover brutal et
  instantané pour chaque connexion quel que soit son cycle de vie.
- **Prévention :** Prenez explicitement en compte les types de connexions de longue durée/stateful comme une exigence distincte
  lors de la conception d'une stratégie de déploiement blue-green (ou de toute bascule de trafic) — une
  stratégie qui ne considère que le trafic requête/réponse de courte durée cassera systématiquement
  cette classe de clients, et elle doit être une partie nommée de la conception, pas un cas limite découvert
  en production.

### S17. La latence pique toutes les quelques secondes et le p99 vaut 10x la médiane, pourtant l'usage CPU semble faible et il n'y a aucune erreur
- **Symptômes :** Le temps de réponse p99 d'une API est de 2 s alors que la médiane est de 80 ms, selon un schéma régulier en dents de scie. Le graphe CPU
  du pod est bien en dessous de la limite (~40 %), la mémoire est correcte, pas de restarts, pas de logs d'erreur. Ajouter des replicas n'aide que très peu.
- **Diagnostic :** L'usage CPU moyen masque le **CFS throttling**. Une *limite* CPU (disons `500m`) est appliquée par périodes de 100 ms :
  un processus multi-threadé (threads de GC de la JVM, une rafale de requêtes) peut consommer son quota de 50 ms dans les 20 premières ms de la
  période et est alors *gelé* pour le reste de celle-ci — les requêtes se bloquent alors que la moyenne sur 1 minute paraît faible. Regardez
  `container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total` (ou `nr_throttled` dans
  `/sys/fs/cgroup/cpu.stat`) : un ratio de quelques pourcents à des dizaines de pourcents le confirme, et les pics de latence s'alignent sur les périodes throttlées (Q17).
- **Exemple :**
  ```yaml
  resources:
    requests: { cpu: "250m", memory: "512Mi" }
    limits:   { cpu: "500m", memory: "512Mi" }   # limite CPU serrée sur une JVM multi-threadée à charge irrégulière
  ```
- **Résolution :** Augmentez ou supprimez la *limite* CPU tout en gardant une *request* réaliste (beaucoup d'équipes définissent des requests CPU mais pas de limites CPU, puisque le CPU est
  compressible et que les requests garantissent déjà une part équitable ; les limites mémoire restent). Ajustez le runtime au container (JVM `-XX:ActiveProcessorCount`, tailles de thread pool
  alignées sur les cœurs réellement accordés). Vérifiez que le ratio de throttling tombe près de 0 et que le p99 converge vers la médiane sous la même charge.
- **Prévention :** Dashboard et alerte sur le ratio de throttling, pas seulement sur l'utilisation ; load test avec les réglages de ressources
  de production ; faire de « définir les requests à partir de mesures, être prudent avec les limites CPU » un défaut de la plateforme.

### S18. Un nouveau déploiement est bloqué en `ImagePullBackOff` / `ErrImagePull` et le rollout ne se termine jamais
- **Symptômes :** Après une release, les nouveaux pods restent en `ImagePullBackOff` tandis que les anciens continuent de servir (le rolling
  update se bloque, ce qui est la partie sûre). `kubectl rollout status` expire ; le pipeline rapporte un succès parce que le manifest a été appliqué.
- **Diagnostic :** `kubectl describe pod` — les Events disent exactement pourquoi. Causes typiques : un **mauvais tag ou un tag jamais poussé**
  (le pipeline a déployé avant la fin du push, ou une faute de frappe), un registry privé avec des **`imagePullSecrets` manquants/expirés** (`pull access denied`, `401`), un node qui ne peut pas joindre le registry
  (network policy, firewall d'egress, DNS), une **limite de débit** du registry (`toomanyrequests` de Docker Hub pour des pulls anonymes depuis de nombreux nodes), ou une incohérence
  d'architecture (une image `arm64` sur des nodes `amd64` : `no matching manifest`). Essayez `docker pull` depuis un node/pod de debug avec les mêmes credentials.
- **Exemple :**
  ```text
  Warning  Failed  kubelet  Failed to pull image "registry.example.com/orders:1.4.2":
           rpc error: code = Unknown desc = failed to resolve reference: pull access denied, ... 401 Unauthorized
  ```
- **Résolution :** Corrigez la cause précise — poussez le tag manquant, rafraîchissez le pull secret (`kubectl create secret docker-registry ...` et référencez-le dans le
  ServiceAccount), autorisez l'egress, mirrorez les images de base vers votre propre registry, ou publiez un manifest multi-arch. Les pods réessaient ensuite automatiquement avec backoff ; sinon,
  `kubectl rollout restart`. Vérifiez avec `kubectl rollout status` qui atteint le succès et tous les pods `Ready`.
- **Prévention :** Déployez par digest/tag SHA immuable uniquement après le succès de l'étape de push ; faites **attendre `rollout status`** au pipeline et faites-le échouer (et rollback) sur
  timeout avec `progressDeadlineSeconds` ; pullez via un registry mirror de cache ; renouvelez les credentials du registry par automatisation et alertez sur leur expiration.

### S19. Les appels vers des hôtes externes prennent ~5 secondes par intermittence, et les appels service-à-service sont lents, mais uniquement à l'intérieur du cluster
- **Symptômes :** Une application qui appelle `api.partner.com` subit des délais aléatoires de 5 secondes ou des erreurs « unknown host » sous charge ; le même
  appel depuis un laptop prend 50 ms. Les dashboards de latence montrent une longue traîne avec un chiffre rond suspect : 5 s (parfois 2,5 s ou 10 s).
- **Diagnostic :** Chronométrez le DNS séparément : `kubectl exec ... -- time nslookup api.partner.com` et consultez les logs, le CPU et les metrics de requêtes/latence des pods CoreDNS. Deux causes fréquentes :
  **`ndots:5`** — dans le `/etc/resolv.conf` d'un pod, un nom avec moins de 5 points est d'abord essayé avec chaque suffixe de recherche
  (`api.partner.com.default.svc.cluster.local`, `...svc.cluster.local`, `...cluster.local`) avant le vrai nom, multipliant
  les requêtes DNS (et les réponses `NXDOMAIN`) par résolution, et un CoreDNS surchargé ou un paquet UDP perdu en fait un **timeout de 5 s** (l'intervalle de retry par défaut du
  resolver) ; et la race conntrack sur le DNS UDP dans les anciens kernels, qui perd des paquets sous charge. Les applications qui ne mettent pas le DNS en cache, ou qui créent une nouvelle connexion par requête, aggravent beaucoup cela.
- **Exemple :**
  ```text
  # /etc/resolv.conf à l'intérieur du pod
  search default.svc.cluster.local svc.cluster.local cluster.local
  options ndots:5
  # résolution de "api.partner.com" (2 points) -> 4 requêtes, dont 3 NXDOMAIN, avant la réponse finale
  ```
- **Résolution :** Utilisez des noms pleinement qualifiés avec un point final (`api.partner.com.`) ou abaissez `ndots` via `dnsConfig` pour les pods qui appellent surtout
  des hôtes externes ; réutilisez les connexions (keep-alive, connection pools) pour que les résolutions soient rares ; scalez CoreDNS et déployez **NodeLocal DNSCache** pour
  réduire la latence et éviter le chemin conntrack ; donnez à la JVM/au client HTTP des TTL DNS raisonnables. Vérifiez en comparant le nombre de requêtes DNS et le p99 des
  appels externes avant et après.
- **Prévention :** Surveillez la latence et le taux d'erreur de CoreDNS, load test avec des appels externes réalistes, et gardez « DNS » sur la checklist d'incident —
  « c'est toujours le DNS » est une blague parce que c'est fréquemment vrai.

### S20. Les utilisateurs reçoivent soudain des avertissements de sécurité du navigateur et les clients d'API échouent avec `x509: certificate has expired`
- **Symptômes :** À 02:14 un samedi, le site affiche `NET::ERR_CERT_DATE_INVALID`, les intégrations partenaires échouent leurs handshakes TLS,
  et les services internes qui s'appellent en mTLS se mettent à échouer. Aucun déploiement n'a eu lieu ; tout fonctionnait vendredi.
- **Diagnostic :** Vérifiez le certificat réellement servi, pas celui que vous croyez configuré :
  `echo | openssl s_client -connect host:443 -servername host 2>/dev/null | openssl x509 -noout -dates -issuer -subject`. Puis trouvez
  *pourquoi* le renouvellement n'a pas eu lieu : un `Certificate`/`Order`/`Challenge` cert-manager bloqué en échec (un challenge HTTP-01 bloqué par une nouvelle redirection ou
  règle de firewall, des credentials DNS-01 expirés, une limite de débit ACME), un certificat géré manuellement que personne n'avait dans un calendrier, un cert renouvelé émis mais **non rechargé** par le proxy/la JVM
  qui l'avait chargé au démarrage, ou une CA interne / un certificat intermédiaire expiré.
- **Exemple :**
  ```bash
  kubectl get certificate,certificaterequest,order,challenge -A       # état de cert-manager
  kubectl describe challenge <name>                                     # "Waiting for HTTP-01 challenge propagation: 404"
  ```
- **Résolution :** Rétablissez d'abord le service — forcez le renouvellement (`cmctl renew`) ou installez manuellement un nouveau certificat et rechargez les serveurs/l'ingress — puis corrigez la cause racine (le
  chemin du challenge, les credentials, ou le rechargement). Vérifiez en relançant le check `openssl s_client` sur chaque endpoint (et depuis un
  point de vue externe) et en confirmant la nouvelle date d'expiration.
- **Prévention :** Automatisez l'émission et le renouvellement (cert-manager/ACME), **alertez bien avant l'expiration** — 30, 14 et 7 jours —
  avec une sonde externe ou des metrics `x509_certificate_expires`, inventoriez tous les certs (y compris les CA internes, les certificats clients
  et ceux embarqués dans des appliances), assurez-vous que les processus rechargent les certificats à chaud, et répétez le renouvellement en staging.

### S21. Une mise à jour de cluster bloque pendant des heures parce qu'un node refuse de se drainer
- **Symptômes :** Pendant une mise à jour de node pool, `kubectl drain` reste sur `Cannot evict pod as it would violate the pod's disruption budget`
  et se répète indéfiniment. Le rollout du cluster managé expire après la limite du provider, laissant des nodes en versions mixtes.
- **Diagnostic :** Listez les budgets bloquants : `kubectl get pdb -A` — cherchez `ALLOWED DISRUPTIONS = 0`. Les raisons habituelles sont
  un PDB avec `minAvailable` égal au nombre de replicas (ou `100%`), un Deployment à **un seul replica** avec un PDB `minAvailable: 1`,
  des pods déjà en mauvaise santé (un pod en `CrashLoopBackOff` compte contre la disponibilité), ou un `StatefulSet` dont le pod ne peut pas être rescheduled parce que son
  volume est lié à une zone sans capacité. Vérifiez aussi les pods sans controller (pods « nus ») et le stockage local, que `drain` refuse sans flags (Q21).
- **Exemple :**
  ```yaml
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  metadata: { name: reports }
  spec:
    minAvailable: 1          # le Deployment a replicas: 1 -> aucune éviction n'est jamais autorisée
    selector: { matchLabels: { app: reports } }
  ```
- **Résolution :** Débloquez la mise à jour en scalant le service à au moins 2 replicas (ou en assouplissant temporairement le PDB), en corrigeant les
  pods en mauvaise santé, puis en drainant à nouveau ; en dernier recours, supprimez délibérément le pod, en acceptant une brève interruption pour ce service. Vérifiez que `ALLOWED DISRUPTIONS >= 1` pour
  chaque PDB et que le node se draine en quelques minutes.
- **Prévention :** Utilisez `maxUnavailable: 1` (ou un pourcentage) plutôt qu'un `minAvailable` fixe, exigez
  replicas ≥ 2 pour tout ce qui a un PDB, ajoutez un policy check (Kyverno/OPA) rejetant les PDB qui rendent l'éviction impossible, mettez à jour d'abord sur un cluster de staging
  avec les mêmes workloads, et planifiez les mises à jour avec la capacité de surge-node pour rescheduler les pods.

### S22. Le téléphone d'astreinte sonne des dizaines de fois par nuit pour des alertes qui se résolvent d'elles-mêmes
- **Symptômes :** Une alerte « CPU > 80 % pendant 1 minute » se déclenche et se résout 30 fois par nuit ; une autre page dès qu'une seule
  requête échoue. L'ingénieur d'astreinte a commencé à mettre le canal en sourdine, et la semaine dernière un vrai incident est resté sans accusé de réception pendant 25 minutes.
- **Diagnostic :** Passez en revue l'historique des alertes : mesurez combien d'alertes étaient *actionnables* (quelqu'un a fait quelque chose) par rapport à combien se sont résolues seules.
  Le flapping vient de seuils statiques sur des signaux bruités (CPU, erreur isolée), de fenêtres d'évaluation plus courtes que la variance naturelle du signal, d'alertes sur des **causes** au lieu de
  **symptômes visibles par l'utilisateur** (un CPU élevé n'est pas une panne), de durées `for:` manquantes, et d'alertes qui couvrent
  la même défaillance plusieurs fois (le pod, le node, le service et l'endpoint paginent tous pour un seul incident).
- **Exemple :**
  ```yaml
  # Bruyant : page sur le moindre pic de CPU, que les utilisateurs soient affectés ou non.
  - alert: HighCPU
    expr: avg(rate(container_cpu_usage_seconds_total[1m])) > 0.8
    for: 1m
  ```
- **Résolution :** Remplacez les alertes basées sur les causes par des alertes **basées sur les symptômes et les SLO** (Q31) : paginez sur un burn rapide de l'error budget, par ex. un ratio de `5xx`
  au-dessus du seuil sur des fenêtres de 5 minutes *et* 1 heure, et routez tout le reste vers des tickets ou des dashboards. Ajoutez des durées `for:`, de l'agrégation, du regroupement et de l'inhibition
  (une alerte node-down supprime ses alertes de pods), et supprimez les alertes sur lesquelles personne n'agit. Vérifiez en mesurant les pages par shift d'astreinte et la part de celles qui étaient actionnables : l'objectif est que
  chaque page exige une décision humaine et renvoie vers un runbook.
- **Prévention :** Passez en revue la qualité des alertes à chaque postmortem et à chaque passation d'astreinte, exigez un lien vers un runbook et un propriétaire pour chaque
  alerte qui page, gardez une cible de « pages par shift », et traitez la fatigue d'alerte comme un risque de fiabilité en soi.

## 📌 Cheat-sheet

- **Conception REST** : des noms dans les URLs, des verbes via les méthodes HTTP, des codes de statut porteurs de sens réel — jamais `200` + erreur dans le corps.
- **Container vs VM** : kernel partagé (namespaces + cgroups), léger, isolation plus faible vs un OS séparé complet, plus lourd, isolation plus forte.
- **Caching Docker** : ordonnez les instructions du Dockerfile de la moins à la plus fréquemment modifiée ; les builds multi-stage retirent le poids du build de l'image livrée.
- **Exit 137** = `SIGKILL` (128+9) — vérifiez `docker inspect` → `State.OOMKilled` ; des logs vides sont attendus, pas un mystère.
- **Idempotence** : `GET`/`PUT`/`DELETE` idempotents par convention ; `POST` non — utilisez une clé d'idempotence pour des retries sûrs.
- **Rate limiting** : fixed window (simple, défaut de rafale à la frontière) vs sliding window (plus lisse) vs token bucket (autorise les rafales naturelles) vs leaky bucket (sortie strictement lisse).
- **Probes** : liveness = restart si échec ; readiness = retrait du LB si échec, sans restart ; startup = retarde les deux pour les boots lents. Mauvais choix de probe = pannes auto-infligées ou trafic vers des pods pas prêts.
- **Resource requests/limits** : pas de request = mauvais scheduling + évincé en premier ; pas de limit = noisy neighbor + risque d'OOM non contenu.
- **HPA** : scale à partir de l'utilisation relative aux *requests* — pas de request = pas de base pour le HPA. Scalez sur la metric qui reflète réellement le goulot d'étranglement, pas seulement le CPU par défaut.
- **Rolling update** : `maxSurge`/`maxUnavailable` contrôlent vitesse de rollout vs capacité ; graceful shutdown + délai `preStop` nécessaires pour que le désenregistrement du LB se termine avant que le pod cesse réellement d'accepter du trafic.
- **`git bisect`** : marquez good/bad, O(log n) étapes jusqu'au commit coupable ; `git bisect run <cmd>` l'automatise entièrement avec une repro scriptée.
- **Stratégies de déploiement** : rolling (efficace, exposition graduelle) vs blue-green (bascule/rollback instantané, double infra, compat de schéma requise dans les deux sens) vs canary (validation sur trafic réel avant rollout complet, compat de coexistence de versions requise).
- **Observabilité** : metrics (est-ce sain, où grosso modo) → traces (quel hop) → logs (détail exact) — complémentaires, pas substituables. RED pour les requêtes, USE pour les ressources.
- **K8s Service** : VIP/DNS stable au-dessus d'IPs de pod éphémères — ne ciblez jamais directement une IP de pod.
- **Les Secrets sont en base64, pas chiffrés** — activez le chiffrement au repos, restreignez le RBAC, ne considérez jamais une sortie décodée comme sûre à partager.
- **Helm** : templating + releases versionnées + rollback en une commande, rentable dès qu'on déploie dans plusieurs environnements/fois.
- **CI/CD fail fast** : checks les moins chers (lint, tests unitaires) d'abord, coûteux (intégration, deploy) en dernier.
</content>
- **Volumes** : le layer inscriptible meurt avec le container ; named volume = données persistantes ; bind mount = confort de dev (chemins hôte, permissions) ; `tmpfs` = mémoire uniquement ; `docker compose down -v` supprime les données.
- **Ordre de triage `kubectl`** : `get pods -o wide` → `describe` (lire les *Events* et *Last State*) → `logs --previous` → `exec`/`debug` → `get endpoints` pour les problèmes de trafic.
- **CORS** : appliqué par le navigateur ; le preflight `OPTIONS` doit réussir *sans* auth ; pas de `*` avec credentials ; les réponses d'erreur ont aussi besoin de headers CORS ; ne remplace pas l'auth/CSRF.
- **Cookies & sessions** : les cookies cross-site nécessitent `SameSite=None; Secure` + `credentials: "include"` ; préférez un déploiement same-site ou un reverse proxy.
- **JWT** : non révocable avant expiration, claims lisibles — access token de courte durée + refresh token rotatif dans un cookie `HttpOnly` ; figer `alg`, valider `iss`/`aud`/`exp`.
- **PDB + spread** : le PDB protège uniquement contre les disruptions *volontaires* ; `topologySpreadConstraints` pour les pannes de zone/node ; un PDB trop strict rend les nodes impossibles à drainer.
- **Promotion** : build once, promouvoir le même digest ; les environnements ne diffèrent que par la config ; promotion = un changement Git (GitOps) ; migrations de DB rétrocompatibles.
- **Secrets** : les Secrets sont encodés, pas chiffrés — gestionnaire externe + External Secrets/CSI, identité par workload, fichiers montés plutôt qu'env vars, rotation et rechargement, Vault pour les credentials dynamiques.
- **SLO / error budget** : SLIs du point de vue de l'utilisateur, budget = 1 − SLO ; alerter sur le burn rate multi-fenêtres ; prédéfinir ce qui se passe à l'épuisement.
- **Les limites CPU causent du throttling** — pics de p99 avec un CPU moyen faible ; surveillez `cfs_throttled_periods`, gardez des requests réalistes, soyez prudent avec les limites CPU.
- **`ImagePullBackOff`** : lire les Events — mauvais tag, pull secret, limite de débit du registry, incohérence d'archi ; le pipeline doit attendre `rollout status`.
- **DNS dans les pods** : `ndots:5` multiplie les résolutions, 5 s = timeout du resolver ; FQDN avec point final, réutilisation des connexions, NodeLocal DNSCache.
- **Certificats** : automatisez le renouvellement, alertez à 30/14/7 jours, assurez le rechargement, inventoriez les CA internes et certs mTLS ; vérifiez avec `openssl s_client`.
- **Fatigue d'alerte** : paginez sur les symptômes visibles par l'utilisateur/le burn SLO, pas sur les causes ; ajoutez `for:`, regroupement et inhibition ; chaque page a besoin d'un propriétaire et d'un runbook.
