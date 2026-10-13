# Bonnes pratiques d'API REST

## 🏷️ Ressources & nommage

### Nommez les ressources avec des noms au pluriel

Modélisez les URL comme des collections de choses (`/orders`, `/orders/42/items`), pas comme des actions.

**Pourquoi c'est une bonne pratique :** la méthode HTTP dit déjà l'action, donc `/getOrders` et `/createOrder` la
disent deux fois et chaque équipe invente un verbe différent (`fetch`, `list`, `retrieve`). Les noms donnent une
forme prévisible : dès qu'un client connaît `/orders`, il peut deviner `/orders/{id}`. Utilisez des minuscules et
des tirets (`/purchase-orders`), et limitez l'imbrication à deux niveaux.

```text
// ⛔
GET  /getAllOrders
POST /createOrder
GET  /Orders/42/getItems

// ✅
GET  /orders
POST /orders
GET  /orders/42/items
```

### Utilisez les méthodes HTTP selon leur sens

`GET` lit, `POST` crée, `PUT` remplace, `PATCH` met à jour partiellement, `DELETE` supprime.

**Pourquoi c'est une bonne pratique :** les proxys, navigateurs et caches s'appuient sur ces sémantiques. Un `GET`
qui modifie des données est déclenché par les aperçus de liens, les robots d'indexation et le préchargement, qui
ont déjà supprimé de vrais enregistrements. `GET`, `PUT` et `DELETE` sont idempotents, donc les clients et
gateways peuvent les rejouer sans risque après un timeout ; `POST` ne l'est pas.

```java
// ⛔ effet de bord sur un GET
@GetMapping("/orders/{id}/cancel")
void cancel(@PathVariable long id) { ... }

// ✅
@PostMapping("/orders/{id}/cancellation")
ResponseEntity<Void> cancel(@PathVariable long id) { ... }
```

### Modélisez les actions comme des sous-ressources quand le CRUD ne suffit pas

Pour les vraies actions métier, créez un nom pour le résultat (`/orders/42/cancellation`, `/payments`) plutôt que des verbes RPC dans le chemin.

**Pourquoi c'est une bonne pratique :** cela conserve l'interface uniforme, et la nouvelle ressource peut être relue,
listée et auditée plus tard. Cela donne aussi à l'action un endroit naturel pour porter ses propres données
(raison, date).

```text
// ⛔
POST /orders/42/doCancel?reason=late

// ✅
POST /orders/42/cancellations   { "reason": "late" }
```

## 📟 Codes de statut & erreurs

### Renvoyez des codes de statut exacts

Utilisez 200/201/204 pour le succès, 4xx quand le client se trompe, 5xx quand c'est le serveur. Ne renvoyez jamais 200 avec un corps d'erreur.

**Pourquoi c'est une bonne pratique :** la supervision, les retries, les circuit breakers et les bibliothèques
clientes réagissent tous au statut. Un `200 {"error": "not found"}` est compté comme un succès dans les tableaux de
bord, mis en cache par les CDN, et ne déclenche jamais la gestion d'erreur du client. Un 500 pour des erreurs de
validation réveille l'astreinte pour rien.

```java
// ⛔
return ResponseEntity.ok(Map.of("error", "User not found"));

// ✅
@PostMapping
ResponseEntity<UserResponse> create(@Valid @RequestBody CreateUser body) {
    var user = service.create(body);
    return ResponseEntity.created(URI.create("/users/" + user.id())).body(user);   // 201 + Location
}
@DeleteMapping("/{id}")
@ResponseStatus(HttpStatus.NO_CONTENT)
void delete(@PathVariable long id) { service.delete(id); }
```

### Connaissez la différence entre 400 / 401 / 403 / 404 / 409 / 422

401 signifie « non authentifié », 403 « authentifié mais non autorisé », 404 « n'existe pas », 409 « en conflit avec l'état actuel », 422 « bien formé mais sémantiquement invalide ».

**Pourquoi c'est une bonne pratique :** les clients agissent différemment pour chacun : 401 déclenche un
rafraîchissement du token, 403 affiche « pas d'accès », 409 demande à l'utilisateur de recharger et de réessayer.
Utiliser 400 pour tout oblige les clients à analyser les messages. (Renvoyez 404 plutôt que 403 quand même
l'existence de la ressource est sensible.)

```text
// ✅
POST /users  {email already used}          -> 409 Conflict
POST /users  {"email": "not-an-email"}     -> 400 Bad Request
GET  /orders/9 (someone else's order)      -> 404 Not Found
```

### Renvoyez les erreurs au format RFC 9457 Problem Details

Utilisez un seul format d'erreur partout : `application/problem+json` avec `type`, `title`, `status`, `detail`, plus vos propres champs.

**Pourquoi c'est une bonne pratique :** quand chaque endpoint invente son propre JSON d'erreur, chaque client écrit un
parsing spécifique. La RFC 9457 (qui a remplacé la RFC 7807) est un standard, et Spring Boot 3 supporte
`ProblemDetail` nativement. Une URI `type` stable permet aux clients de réagir à l'erreur sans analyser de texte.

```java
// ⛔
return ResponseEntity.badRequest().body("Something went wrong");

// ✅
@RestControllerAdvice
class ApiExceptionHandler extends ResponseEntityExceptionHandler {
    @ExceptionHandler(OrderNotFoundException.class)
    ProblemDetail notFound(OrderNotFoundException ex) {
        var pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setType(URI.create("https://api.example.com/problems/order-not-found"));
        pd.setTitle("Order not found");
        return pd;
    }
}
// spring.mvc.problemdetails.enabled: true
```

### Signalez toutes les erreurs de validation en une fois

Renvoyez chaque champ invalide dans une seule réponse, pas seulement le premier trouvé.

**Pourquoi c'est une bonne pratique :** si un formulaire a 5 problèmes et que l'API en signale un par appel,
l'utilisateur a besoin de 5 allers-retours. Une liste d'erreurs par champ permet à l'UI de tous les mettre en
évidence.

```json
// ✅ 400 application/problem+json
{
  "type": "https://api.example.com/problems/validation",
  "title": "Validation failed",
  "status": 400,
  "errors": [
    { "field": "email", "message": "must be a well-formed email address" },
    { "field": "age",   "message": "must be greater than or equal to 18" }
  ]
}
```

## 📄 Collections

### Paginez toujours les collections

Chaque endpoint de liste prend `page`/`size` ou un curseur, avec une taille par défaut et une taille maximale.

**Pourquoi c'est une bonne pratique :** `GET /orders` fonctionne avec 100 lignes en dev et en renvoie 4 millions en
production : mémoire saturée côté serveur, timeout côté client, et scan complet de la table en base. Un maximum
strict (disons 100) vous protège aussi de `?size=1000000`.

```java
// ⛔
@GetMapping List<Order> all() { return repo.findAll(); }

// ✅
@GetMapping
Page<OrderResponse> list(@PageableDefault(size = 20) Pageable pageable) {
    return service.list(pageable);
}
// spring.data.web.pageable.max-page-size: 100
```

### Préférez la pagination par curseur pour les données volumineuses ou changeantes

Utilisez un curseur (`?after=<dernier id>`) plutôt que `OFFSET` pour les fils d'actualité et les grosses tables.

**Pourquoi c'est une bonne pratique :** `OFFSET 1000000` oblige la base à lire et jeter un million de lignes, donc la
page 10 000 est lente. Les lignes insérées pendant qu'un utilisateur pagine causent des doublons ou des éléments
sautés. Une condition keyset (`WHERE id < :last ORDER BY id DESC LIMIT 20`) utilise l'index et reste rapide à
n'importe quelle profondeur.

```sql
-- ⛔
SELECT * FROM orders ORDER BY id DESC LIMIT 20 OFFSET 1000000;

-- ✅
SELECT * FROM orders WHERE id < :lastId ORDER BY id DESC LIMIT 20;
```

### Supportez le filtrage et le tri avec une liste blanche

Acceptez `?status=PAID&sort=createdAt,desc` uniquement sur des champs connus.

**Pourquoi c'est une bonne pratique :** passer la valeur de `sort` directement à la requête permet de trier sur des
colonnes non indexées ou sensibles (`sort=passwordHash`), et les valeurs inconnues causent des 500. Une liste
blanche garde les requêtes sur des colonnes indexées et le contrat d'API explicite.

```java
// ✅
private static final Set<String> SORTABLE = Set.of("createdAt", "total");
```

## 🧬 Payloads

### Exposez des DTO, pas des entités

Convertissez les entités en records de requête et de réponse à la frontière de l'API.

**Pourquoi c'est une bonne pratique :** une entité exposée directement lie votre schéma de base de données au
contrat public : renommer une colonne devient un changement cassant. Cela divulgue aussi des champs internes,
déclenche des exceptions de lazy-loading pendant la sérialisation, et permet le mass assignment. Des types de
requête et de réponse séparés permettent à chacun d'évoluer indépendamment. Les records Java rendent cela peu
coûteux.

```java
// ⛔
@GetMapping("/{id}") Order get(@PathVariable long id) { return repo.findById(id).orElseThrow(); }

// ✅
record OrderResponse(long id, String status, BigDecimal total, Instant createdAt) {
    static OrderResponse from(Order o) { return new OrderResponse(o.getId(), o.getStatus().name(), o.getTotal(), o.getCreatedAt()); }
}
```

### Utilisez des formats cohérents pour les dates, l'argent et les enums

Envoyez les dates en ISO 8601 UTC (`2026-03-01T10:15:30Z`), l'argent en chaîne décimale ou en unités mineures plus une devise, et les enums en chaînes stables.

**Pourquoi c'est une bonne pratique :** `03/04/2026` est mars ou avril selon le lecteur. Un `double` pour l'argent
donne `0.1 + 0.2 = 0.30000000000000004`. Les ordinaux numériques d'enum changent silencieusement de sens quand
quelqu'un insère une valeur. Utilisez `BigDecimal` côté serveur.

```json
// ⛔
{ "date": "03/04/26", "price": 19.989999, "status": 2 }

// ✅
{ "createdAt": "2026-04-03T09:00:00Z", "price": { "amount": "19.99", "currency": "EUR" }, "status": "SHIPPED" }
```

## 🔄 Fiabilité & évolution

### Rendez les opérations non sûres idempotentes avec un `Idempotency-Key`

Laissez les clients envoyer une clé unique avec `POST` et renvoyez le résultat stocké en cas de répétition.

**Pourquoi c'est une bonne pratique :** les réseaux tombent après que le serveur a traité la requête mais avant que le
client ait vu la réponse. Le client réessaie, et le client final est débité deux fois. Stocker la clé (avec une
contrainte d'unicité) transforme les retries en opérations sans effet. Stripe et la plupart des API de paiement
fonctionnent ainsi.

```java
// ✅
@PostMapping("/payments")
ResponseEntity<PaymentResponse> pay(@RequestHeader("Idempotency-Key") String key,
                                    @Valid @RequestBody PayRequest body) {
    return service.findByKey(key)
        .map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.status(201).body(service.pay(key, body)));
}
// UNIQUE(idempotency_key) fait échouer les doublons concurrents au lieu de les laisser réussir tous les deux
```

### Utilisez la concurrence optimiste avec les ETags

Renvoyez un `ETag` (ou une `version`) et exigez `If-Match` sur les mises à jour. Répondez 412 ou 409 en cas de décalage.

**Pourquoi c'est une bonne pratique :** deux utilisateurs modifient le même enregistrement ; le second `PUT` écrase
silencieusement le premier (mise à jour perdue). Une vérification de version le détecte. `ETag` avec
`If-None-Match` offre aussi des `GET` conditionnels peu coûteux qui renvoient 304 sans corps.

```java
// ✅
@PutMapping("/{id}")
ResponseEntity<ProductResponse> update(@PathVariable long id,
        @RequestHeader("If-Match") String etag, @Valid @RequestBody UpdateProduct body) {
    var saved = service.update(id, Long.parseLong(etag.replace("\"", "")), body); // lève 412 si périmé
    return ResponseEntity.ok().eTag("\"" + saved.version() + "\"").body(saved);
}
```

### Versionnez l'API et évitez les changements cassants

Mettez une version dans l'URL (`/v1/`) ou dans un en-tête, et n'ajoutez que des champs optionnels au sein d'une version.

**Pourquoi c'est une bonne pratique :** dès que des applications mobiles et des partenaires dépendent de votre JSON,
renommer ou supprimer un champ casse des clients que vous ne pouvez pas redéployer. Ajouter un champ est sans
risque ; supprimer ou changer un type ne l'est pas. Publiez les dépréciations avec les en-têtes `Deprecation` et
`Sunset` et une date pour que les consommateurs puissent planifier.

```text
// ⛔ renommage sur place : { "name": ... } devient { "fullName": ... }

// ✅ changement additif dans v1 ; le changement cassant va dans v2
GET /v1/users/7   -> { "name": "Ann", "displayName": "Ann B." }
GET /v2/users/7   -> { "fullName": "Ann B." }
```

### Validez les entrées et documentez le contrat avec OpenAPI

Annotez les types de requête avec Bean Validation et générez une spécification OpenAPI (springdoc), versionnée ou publiée depuis la CI.

**Pourquoi c'est une bonne pratique :** une API non documentée s'apprend par essais et erreurs, et la documentation
écrite à la main dérive. Une spécification générée alimente la génération de clients, les tests de contrat et un
Swagger UI, et un diff de la spécification dans une pull request montre les changements cassants avant la
livraison.

```java
// ✅
@Operation(summary = "Create an order")
@ApiResponse(responseCode = "201", description = "Created")
@ApiResponse(responseCode = "400", description = "Validation failed")
@PostMapping
ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrder body) { ... }
```
