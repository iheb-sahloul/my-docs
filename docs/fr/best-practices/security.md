# Bonnes pratiques de sécurité

## 🚪 Entrées & injection

### Validez toutes les entrées à la frontière

Validez chaque corps de requête, paramètre et en-tête avec Bean Validation, et rejetez les mauvaises entrées avec un 400.

**Pourquoi c'est une bonne pratique :** toute valeur venue de l'extérieur n'est pas fiable. Sans limites, une chaîne
de 500 Mo, une quantité négative ou un id nul se propagent profondément dans le système et échouent à des endroits
imprévisibles, ou pire, réussissent. Valider une fois à la périphérie donne un seul jeu de règles clair. Préférez
les listes d'autorisation (un enum, une regex) aux listes de blocage, que les attaquants contournent.

```java
// ⛔
record CreateUser(String email, int age) {}

// ✅
record CreateUser(
    @NotBlank @Email @Size(max = 254) String email,
    @Min(18) @Max(120) int age) {}

@PostMapping("/users")
User create(@Valid @RequestBody CreateUser body) { ... }
```

### Utilisez des requêtes paramétrées, jamais de concaténation de chaînes

Passez les valeurs en paramètres liés dans JDBC, JPQL et les requêtes natives.

**Pourquoi c'est une bonne pratique :** l'injection SQL figure dans l'OWASP Top 10 depuis vingt ans et provoque
encore des dumps complets de base de données. Avec `name = "x' OR '1'='1"`, une requête concaténée renvoie toutes
les lignes ; `'; DROP TABLE users;--` est pire. Un paramètre lié est envoyé séparément du texte SQL, donc la base
ne le traite jamais comme du code.

```java
// ⛔
jdbc.query("SELECT * FROM users WHERE name = '" + name + "'", mapper);

// ✅
jdbc.query("SELECT * FROM users WHERE name = ?", mapper, name);

// ✅ Spring Data
@Query("select u from User u where u.name = :name")
List<User> findByName(@Param("name") String name);
```

### Échappez les sorties et définissez une Content Security Policy

Encodez les données selon le contexte où elles sont rendues (HTML, JS, URL), et envoyez des en-têtes de sécurité.

**Pourquoi c'est une bonne pratique :** une XSS stockée permet au commentaire d'un utilisateur d'exécuter du
JavaScript dans le navigateur de chaque lecteur et de voler des sessions. Les moteurs de template comme Thymeleaf
échappent par défaut (`th:text`) ; la sortie brute (`th:utext`, `innerHTML`) désactive cette protection. Une CSP
limite les dégâts si vous en oubliez un endroit. Spring Security ajoute plusieurs en-têtes par défaut.

```java
// ⛔
<div th:utext="${comment}"></div>

// ✅
<div th:text="${comment}"></div>

// ✅
http.headers(h -> h.contentSecurityPolicy(c -> c.policyDirectives("default-src 'self'")));
```

### Prévenez le path traversal et le SSRF

Ne construisez jamais de chemins de fichiers ou d'URL sortantes directement à partir d'une saisie utilisateur. Normalisez et vérifiez contre une liste d'autorisation.

**Pourquoi c'est une bonne pratique :** `../../etc/passwd` dans un nom de fichier lit n'importe quel fichier
accessible au processus. Un attaquant qui contrôle une URL appelée par votre serveur peut atteindre
`http://169.254.169.254/` (métadonnées cloud) et voler les identifiants de l'instance, comme lors de la fuite
Capital One en 2019.

```java
// ⛔
Path file = Path.of("/data/uploads", filename);

// ✅
Path base = Path.of("/data/uploads").toRealPath();
Path file = base.resolve(filename).normalize();
if (!file.startsWith(base)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST);
```

## 🔑 Authentification & secrets

### Hachez les mots de passe avec un algorithme lent et adaptatif

Utilisez `BCryptPasswordEncoder`, Argon2 ou `DelegatingPasswordEncoder`. Ne stockez jamais de texte en clair, de MD5 ou de SHA simple.

**Pourquoi c'est une bonne pratique :** un GPU calcule des milliards de hachages SHA-256 par seconde, donc une table
fuitée sans sel est cassée en quelques heures. BCrypt est salé et volontairement lent (environ 100 ms par hachage
avec un coût de 10 à 12), ce qui rend la force brute impraticable. `DelegatingPasswordEncoder` stocke l'id de
l'algorithme, ce qui permet de migrer plus tard.

```java
// ⛔
user.setPassword(DigestUtils.md5Hex(rawPassword));

// ✅
@Bean
PasswordEncoder passwordEncoder() {
    return PasswordEncoderFactories.createDelegatingPasswordEncoder();
}
user.setPassword(passwordEncoder.encode(rawPassword));
```

### Gardez les secrets hors du code et de Git

Chargez les secrets depuis des variables d'environnement ou un gestionnaire de secrets (Vault, AWS Secrets Manager, secrets Kubernetes), et faites-les tourner.

**Pourquoi c'est une bonne pratique :** des bots scannent les commits publics de GitHub en quelques minutes et
utilisent les clés cloud fuitées pour miner de la cryptomonnaie ; les dépôts privés fuient via les forks et les
logs de CI. Un secret dans l'historique Git y reste après suppression, donc la seule solution est de le renouveler.
Ajoutez un scanner (gitleaks) en CI et un hook de pre-commit.

```yaml
# ⛔
spring.datasource.password: s3cr3t
# ✅
spring.datasource.password: ${DB_PASSWORD}
```

### Validez complètement les JWT et gardez-les de courte durée

Vérifiez la signature, `iss`, `aud` et `exp`. Utilisez des access tokens courts (5 à 15 min) avec des refresh tokens. N'acceptez jamais `alg: none`.

**Pourquoi c'est une bonne pratique :** un JWT ne peut pas être révoqué avant son expiration, donc un token volé de
30 jours est une brèche de 30 jours. Sauter la vérification de l'audience permet d'utiliser sur le service B un
token émis pour le service A. Utilisez le resource server de Spring plutôt qu'un parsing écrit à la main.

```java
// ⛔ décodage sans vérification
var claims = Jwts.parser().build().parseUnsecuredClaims(token);

// ✅
http.oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()));
// application.yml
// spring.security.oauth2.resourceserver.jwt.issuer-uri: https://auth.example.com
```

### Limitez le débit et verrouillez les endpoints de connexion

Limitez les tentatives d'authentification, et renvoyez le même message pour un mauvais utilisateur et un mauvais mot de passe.

**Pourquoi c'est une bonne pratique :** sans limites, un attaquant essaie 10 millions de mots de passe fuités contre
votre connexion (credential stuffing). Des messages différents (« utilisateur inconnu » vs « mauvais mot de
passe ») lui permettent d'énumérer d'abord les comptes valides. Ajoutez la MFA pour les comptes sensibles.

```java
// ⛔
if (user == null) return "User not found";
if (!matches) return "Wrong password";

// ✅
return ResponseEntity.status(401).body(problem("Invalid credentials"));
```

## 🛡️ Protections web

### Configurez CORS avec une liste d'origines explicite

Autorisez des origines, méthodes et en-têtes précis. Ne combinez jamais `*` avec les credentials.

**Pourquoi c'est une bonne pratique :** CORS est une règle du navigateur qui décide quels sites web peuvent lire les
réponses de votre API avec les cookies de l'utilisateur. `allowedOrigins("*")` sur une API authentifiée permet à
n'importe quel site malveillant de le faire. Les navigateurs refusent `*` avec les credentials, donc on « corrige »
en reflétant l'en-tête `Origin`, ce qui revient à la même faille.

```java
// ⛔
registry.addMapping("/**").allowedOriginPatterns("*").allowCredentials(true);

// ✅
registry.addMapping("/api/**")
    .allowedOrigins("https://app.example.com")
    .allowedMethods("GET", "POST", "PUT", "DELETE")
    .allowCredentials(true);
```

### Gardez la protection CSRF activée pour les sessions par cookie

Ne désactivez CSRF que pour les API sans état qui s'authentifient avec un bearer token dans un en-tête.

**Pourquoi c'est une bonne pratique :** les navigateurs joignent les cookies automatiquement, donc un formulaire
caché sur `evil.com` peut soumettre `POST /transfer` en tant qu'utilisateur connecté. Des tokens ou des cookies
`SameSite=Lax/Strict` l'empêchent. Désactiver CSRF « parce que le POST échouait dans Postman » retire la
protection de toute l'application.

```java
// ⛔ application à sessions avec protection désactivée
http.csrf(AbstractHttpConfigurer::disable);

// ✅ uniquement pour une API sans état à bearer token
http.csrf(AbstractHttpConfigurer::disable)
    .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
```

### Imposez HTTPS et des cookies sécurisés

Redirigez vers HTTPS, envoyez HSTS, et définissez `Secure`, `HttpOnly` et `SameSite` sur les cookies de session.

**Pourquoi c'est une bonne pratique :** sur le Wi-Fi d'un café, le trafic HTTP en clair peut être lu et modifié.
`HttpOnly` empêche JavaScript de lire le cookie de session, donc une faille XSS ne peut pas le voler. `Secure` le
garde hors des requêtes HTTP.

```yaml
# ✅
server.servlet.session.cookie.secure: true
server.servlet.session.cookie.http-only: true
server.servlet.session.cookie.same-site: lax
```

## 🧑‍⚖️ Autorisation

### Refusez par défaut et appliquez le moindre privilège

Exigez l'authentification pour chaque route, ouvrez explicitement certaines routes, et donnez à chaque compte ou service uniquement les permissions dont il a besoin.

**Pourquoi c'est une bonne pratique :** « Broken Access Control » est le numéro 1 de l'OWASP Top 10 (2021). Un
nouvel endpoint oublié sous un motif permit-all est public dès le premier jour. Un utilisateur de base de données
avec le droit `DROP` transforme une petite injection en perte totale ; un utilisateur applicatif qui ne peut faire
que `SELECT/INSERT/UPDATE` limite le rayon d'action.

```java
// ⛔
.authorizeHttpRequests(a -> a.requestMatchers("/api/**").permitAll())

// ✅
.authorizeHttpRequests(a -> a
    .requestMatchers("/actuator/health/**", "/v3/api-docs/**").permitAll()
    .requestMatchers("/api/admin/**").hasRole("ADMIN")
    .anyRequest().authenticated())
```

### Vérifiez la propriété à chaque accès à un objet

Vérifiez que l'appelant a le droit d'accéder à cet enregistrement précis, pas seulement qu'il est connecté.

**Pourquoi c'est une bonne pratique :** l'IDOR (insecure direct object reference) est le bug classique : l'utilisateur
5 appelle `GET /orders/1234` et obtient la commande de quelqu'un d'autre, parce que le code vérifie seulement « est
authentifié ». Les attaquants n'ont qu'à parcourir les ids. Imposez-le avec la sécurité par méthode ou en
interrogeant avec le propriétaire.

```java
// ⛔
return orders.findById(id).orElseThrow();

// ✅
@PreAuthorize("@orderAccess.isOwner(#id, authentication)")
@GetMapping("/orders/{id}")
Order get(@PathVariable long id) { ... }

// ✅ ou restreindre la requête
orders.findByIdAndCustomerId(id, currentUser.id());
```

## 📦 Chaîne d'approvisionnement & exposition des données

### Scannez les dépendances et mettez-les à jour régulièrement

Lancez OWASP Dependency-Check, Dependabot, Renovate ou Trivy en CI, et échouez sur les CVE de sévérité élevée.

**Pourquoi c'est une bonne pratique :** Log4Shell (CVE-2021-44228) était une exécution de code à distance dans une
bibliothèque que beaucoup d'équipes ne savaient même pas avoir. L'essentiel du code qui tourne chez vous est tiers.
Les pull requests automatiques rendent les mises à jour petites et fréquentes, au lieu d'un saut douloureux par-dessus
trois versions majeures pendant un incident.

```yaml
# ✅ .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: maven
    directory: "/"
    schedule: { interval: weekly }
```

### N'exposez jamais les entités ni les erreurs internes

Renvoyez des DTO et des corps d'erreur génériques. Loguez les détails uniquement côté serveur.

**Pourquoi c'est une bonne pratique :** renvoyer une entité JPA divulgue des colonnes comme `passwordHash` ou
`isAdmin`, et permet aux clients de définir des champs par mass assignment (`{"role":"ADMIN"}`). Une stack trace
révèle les versions du framework, les noms de tables et les chemins de fichiers, ce qui aide l'attaque suivante.

```java
// ⛔
@PostMapping User create(@RequestBody User user) { return repo.save(user); }

// ✅
record UserResponse(long id, String email) {}
@PostMapping UserResponse create(@Valid @RequestBody CreateUser body) { ... }

// application.yml
// server.error.include-stacktrace: never
// server.error.include-message: never
```

### Ne loguez jamais de secrets ni de données personnelles

Masquez les tokens, mots de passe, numéros de carte et données personnelles avant de les loguer.

**Pourquoi :** traité dans [Ne loguez jamais de secrets ni de données personnelles](observability.md#ne-loguez-jamais-de-secrets-ni-de-donnees-personnelles).

```java
// ⛔
log.info("Login request: {}", request);   // contient le mot de passe

// ✅
log.info("Login attempt for user id={}", userId);
```

### Sécurisez l'actuator et les autres endpoints de gestion

N'exposez publiquement que `health` et `info`, et placez le reste derrière une authentification ou un port privé.

**Pourquoi c'est une bonne pratique :** `/actuator/env`, `/heapdump` et `/threaddump` révèlent la configuration, et un
heap dump contient tous les secrets en mémoire. Les actuators exposés sont un constat fréquent dans les tests
d'intrusion.

```yaml
# ⛔
management.endpoints.web.exposure.include: "*"

# ✅
management.endpoints.web.exposure.include: health,info,prometheus
management.server.port: 9090
```
