# Conception d'API REST

Questions de conception REST plus poussées : pagination, PUT vs PATCH, erreurs, cache et rate limiting. Les bases (principes, versionnement, clés d'idempotence, OpenAPI) sont dans [Full Stack & DevOps](fullstack-devops-k8s.md#core-principles-good-rest-api) ; les règles dans [Bonnes pratiques › API REST](../best-practices/rest-api.md).

## 🟢 Fondamentaux

#### Q1. Comment modélisez-vous les ressources et choisissez-vous méthodes HTTP et codes de statut ? {#model-resources-http-methods-status}
**Réponse :** Modélisez des **noms**, pas des actions : `/appointments/42`, avec `GET` (lecture, sûr), `POST` (création, non idempotent), `PUT` (remplacement, idempotent), `PATCH` (mise à jour partielle), `DELETE` (idempotent). Utilisez des codes précis : `201` + `Location` à la création, `204` sans corps, `400` requête mal formée, `401` non authentifié, `403` interdit, `404` absent, `409` conflit, `422` syntaxe valide mais validation échouée. Une action hors CRUD devient une sous-ressource (`POST /appointments/42/cancellation`).

#### Q2. Quelle différence entre `PUT` et `PATCH`, et comment gérer les mises à jour concurrentes ? {#put-patch-handle-concurrent-updates}
**Réponse :** `PUT` remplace toute la ressource (les champs absents sont réinitialisés) ; `PATCH` ne modifie que les champs envoyés (JSON Merge Patch, ou JSON Patch pour des opérations). Les deux risquent la mise à jour perdue : renvoyez un `ETag` au `GET`, exigez `If-Match` à l'écriture et répondez `412 Precondition Failed` (ou `409`) en cas de décalage. C'est du verrouillage optimiste exposé en HTTP.

**Exemple :**

```http
PUT /appointments/42
If-Match: "v7"

→ 412 Precondition Failed   (quelqu'un a enregistré v8)
```

## 🟡 Pièges seniors

#### Q3. Pagination offset ou keyset (curseur) : comment choisir ? {#offset-keyset-cursor-pagination}
**Réponse :** `LIMIT/OFFSET` est simple et permet de sauter à la page N, mais le coût croît avec l'offset (la base lit et jette les lignes sautées) et les lignes se décalent aux insertions, causant doublons ou trous. La pagination **keyset** (`WHERE (created_at, id) < (:last_at, :last_id) ORDER BY created_at DESC, id DESC LIMIT 50`) reste rapide sur un index et stable, mais ne saute pas à une page arbitraire. Renvoyez un `nextCursor` opaque, ajoutez toujours une colonne unique de départage et plafonnez `limit`.

#### Q4. Quel format d'erreur renvoyez-vous, et que ne faut-il jamais divulguer ? {#error-format-return-never-leak}
**Réponse :** Utilisez un format unique, idéalement **RFC 9457 Problem Details** (`application/problem+json`) : `type`, `title`, `status`, `detail`, plus des champs comme `errors[]` pour la validation. Avec Spring Boot 3, activez `ProblemDetail` via un `@RestControllerAdvice`. Ne divulguez jamais stack traces, SQL, noms de classes ni l'existence d'un utilisateur ; journalisez-les côté serveur avec un identifiant de corrélation renvoyé dans la réponse pour que le support retrouve la cause.

#### Q5. Comment utilisez-vous le cache HTTP et le rate limiting sur une API ? {#http-caching-rate-limiting-api}
**Réponse :** Cache : `Cache-Control` (`max-age`, `private` vs `public`), validateurs `ETag`/`Last-Modified` et `GET` conditionnel renvoyant `304`, et `Vary` pour la négociation de contenu. Ne mettez jamais de données par utilisateur dans un cache partagé. Rate limiting : appliquez-le par clé client (token bucket à la passerelle), répondez `429 Too Many Requests` avec `Retry-After` et exposez les limites en en-têtes ; protégez plus strictement les endpoints coûteux.

## 🔴 Expert / Ouvert

#### Q6. Comment faire évoluer une API sans casser les clients ? {#evolve-api-breaking-clients}
**Réponse :** Privilégiez le changement **additif** : nouveaux champs optionnels, nouveaux endpoints, lecteurs tolérants qui ignorent les champs inconnus. Ne renommez, ne supprimez ni ne changez jamais le sens d'un champ sur place. Quand une rupture est inévitable, versionnez (chemin ou en-tête), faites tourner les deux versions, annoncez la dépréciation avec les en-têtes `Deprecation`/`Sunset` et suivez l'usage par client avant suppression. Les tests de contrat pilotés par le consommateur détectent les ruptures accidentelles en CI.

## 🎯 Scénarios réels

### S1. Un endpoint de liste ralentit chaque mois et renvoie parfois des doublons {#list-endpoint-gets-slower-every}
- **Symptômes :** La page 1 est rapide, les pages profondes prennent plusieurs secondes et les clients voient parfois le même élément sur deux pages.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Pagination offset sur une table croissante, triée par une colonne non unique. Vérifiez dans `EXPLAIN` un gros tri/saut et les colonnes de l'`ORDER BY`.
- **Résolution :** Passez à la pagination keyset sur un index `(created_at, id)`, renvoyez `nextCursor`, plafonnez la taille de page et ne gardez l'offset que pour de petites listes d'admin.
- **Prévention :** Règle de revue : tout endpoint de liste exige un ordre total stable, un `limit` maximal et un test de charge avec des pages profondes.

</details>

### S2. Un renommage de champ part en prod le vendredi et l'app mobile plante pour tous ceux restés sur la version du mois dernier {#renamed-field-breaks-mobile-app}
- **Symptômes :** Le web fonctionne (déployé en même temps), mais les crash reports Android/iOS explosent : `NullPointerException` en parsant `customerName`, devenu `fullName`.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Comparez la spec OpenAPI entre les deux releases (`oasdiff breaking old.yaml new.yaml`). On ne force pas la mise à jour d'un client mobile : tout champ supprimé/renommé, nouveau champ requis en entrée ou enum restreint est un breaking change pendant des semaines.
- **Exemple :**

  ```text
  error  response-property-removed  GET /customers/{id}  200  'customerName'
  ```

- **Résolution :** Corrigez en avant en réintroduisant `customerName` (les deux champs servis), puis dépréciez-le via les en-têtes `Deprecation`/`Sunset` et ne le retirez que lorsque les analytics montrent les anciennes versions sous un seuil convenu.
- **Prévention :** Contrôle des breaking changes sur la spec en CI (build en échec), tests de contrat pilotés par le consommateur avec l'équipe mobile, règle expand → migrate → contract pour tout changement de champ.

</details>

### S3. Un client mobile sur un réseau instable est débité deux fois pour un seul paiement {#retried-post-double-payment}
- **Symptômes :** Deux lignes `payment` à quelques secondes d'écart, même montant et même panier ; l'access log montre deux `POST /payments` du même appareil, le premier terminé par un timeout côté client.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** La première requête a réussi côté serveur mais la réponse a été perdue ; le client (ou un proxy/SDK) a rejoué. `POST` n'est pas idempotent et le serveur ne peut pas savoir qu'il s'agit de la même intention.
- **Exemple :**

  ```http
  POST /payments
  Idempotency-Key: 4f1c2b9e-...

  # serveur : INSERT INTO idempotency(key, request_hash, response) ... ON CONFLICT (key) DO NOTHING
  # rejeu avec la même clé    -> renvoie la réponse stockée, pas de nouveau débit
  # même clé, autre corps     -> 422
  ```

- **Résolution :** Remboursez le doublon ; exigez un en-tête `Idempotency-Key` sur les `POST` qui déplacent de l'argent, stockez clé + hash de requête + réponse dans la même transaction que le paiement (contrainte unique), rejouez la réponse stockée, expirez les clés après 24–48 h.
- **Prévention :** Clés d'idempotence obligatoires dans les guidelines API pour les `POST` à effet de bord, un test de chaos qui perd les réponses et rejoue, et transmettez la clé au PSP (il la supporte aussi).

</details>

### S4. Deux utilisateurs du back-office modifient le même client et l'un perd ses changements sans le savoir {#concurrent-edits-silently-overwrite}
- **Symptômes :** Un agent du support met à jour l'adresse, un collègue met à jour le téléphone une minute plus tard depuis un onglet ouvert avant ; l'adresse est revenue à l'ancienne valeur. Aucune erreur nulle part.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Lost update classique : l'UI envoie l'objet complet en `PUT` (ou un `PATCH` construit depuis un état périmé), le dernier qui écrit gagne. Rien dans la requête n'indique quelle version le client a éditée.
- **Exemple :**

  ```http
  GET /customers/42        -> 200, ETag: "v7"
  PATCH /customers/42
  If-Match: "v7"           -> 412 Precondition Failed si quelqu'un a sauvé v8 entre-temps
  ```

- **Résolution :** Renvoyez un `ETag` (version de l'entité, ex. `@Version` JPA) sur le `GET`, exigez `If-Match` sur `PUT`/`PATCH`, répondez `412` en cas d'écart (`428` s'il manque) et laissez l'UI proposer recharger/fusionner. N'envoyez que les champs modifiés en `PATCH`.
- **Prévention :** Verrouillage optimiste par défaut pour les ressources éditables, un test d'intégration avec deux mises à jour concurrentes, et des guidelines API qui rendent `If-Match` obligatoire en écriture.

</details>

### S5. La synchro nocturne d'un partenaire devient une tempête de retries qui dégrade l'API pour tout le monde {#partner-retry-storm-429}
- **Symptômes :** À 02:00 le trafic est multiplié par 20, presque entièrement depuis une seule clé d'API ; la plupart des réponses sont des `429`, pourtant le débit continue d'augmenter et le p99 des autres clients triple.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le rate limiting fonctionne, mais le client du partenaire rejoue chaque `429` immédiatement et en parallèle. Le limiteur (et l'auth, les logs, le TLS) coûte du CPU à chaque appel rejeté : rejeter ne suffit pas à protéger le service.
- **Exemple :**

  ```http
  HTTP/1.1 429 Too Many Requests
  Retry-After: 30
  RateLimit-Policy: 100;w=60
  RateLimit: remaining=0, reset=30
  ```

- **Résolution :** À court terme : baissez le quota de cette clé et bloquez au niveau gateway/WAF (la couche la moins chère). Ensuite, renvoyez les en-têtes `Retry-After` et `RateLimit`, et convenez avec le partenaire d'un backoff exponentiel avec jitter, d'un plafond de concurrence et d'un endpoint d'export en masse plutôt que des milliers de petits appels.
- **Prévention :** Quotas par client appliqués en bordure, un contrat de retry documenté dans le guide API, une alerte sur le taux de `429` par clé, et un SDK qui implémente correctement le backoff.

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q1. Comment modélisez-vous les ressources et choisissez-vous méthodes HTTP et codes de statut ?
2. Q2. Quelle différence entre `PUT` et `PATCH`, et comment gérer les mises à jour concurrentes ?
3. Q3. Pagination offset ou keyset (curseur) : comment choisir ?
4. Q4. Quel format d'erreur renvoyez-vous, et que ne faut-il jamais divulguer ?
5. Q5. Comment utilisez-vous le cache HTTP et le rate limiting sur une API ?
6. Q6. Comment faire évoluer une API sans casser les clients ?
7. S1. Un endpoint de liste ralentit chaque mois et renvoie parfois des doublons

## 📌 Cheat-sheet

- **Méthodes** — `GET` sûr, `PUT`/`DELETE` idempotents, `POST` ni l'un ni l'autre. *Utilisez `201`+`Location`, `409` conflit, `422` validation.*
- **Concurrence** — `ETag` + `If-Match` → `412`. *Verrouillage optimiste en HTTP.*
- **Pagination** — keyset bat offset sur les grosses tables. *Exige un départage unique et un curseur opaque.*
- **Erreurs** — RFC 9457 `problem+json` et un identifiant de corrélation. *Ne divulguez jamais de stack trace.*
- **Évolution** — changements additifs, lecteurs tolérants, en-tête `Sunset`. *Ne versionnez que si la rupture est inévitable.*
