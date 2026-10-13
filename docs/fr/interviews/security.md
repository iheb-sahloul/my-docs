# Sécurité

Les règles et checklists de revue sont dans [Bonnes pratiques › Sécurité](../best-practices/security.md) ; ce module est le Q&A d'entretien. Questions liées ailleurs : CORS dans [Full Stack Q12](fullstack-devops-k8s.md), stockage des tokens dans [Full Stack Q13](fullstack-devops-k8s.md), secrets Kubernetes dans [Full Stack Q38](fullstack-devops-k8s.md), OWASP Top 10 au niveau conception dans [System Design Q34](system-design.md), et autorisation par URL vs par méthode dans [Spring Q41](spring-architecture.md).

## 🟢 Fondamentaux

### Identité

#### Q1. Authentification vs autorisation — et où chacune se passe-t-elle dans une app Spring + React typique ?

**Réponse :** L'**authentification** répond à « qui êtes-vous ? » (vérifier des identifiants ou un token et établir
une identité). L'**autorisation** répond à « que pouvez-vous faire ? » (comparer les rôles, scopes ou la propriété de
cette identité à la ressource). Dans une architecture moderne, l'app React envoie l'utilisateur vers un fournisseur
d'identité (Keycloak, Auth0, Entra ID, Cognito), récupère des tokens et appelle l'API avec un access token. L'API
Spring, configurée en **resource server OAuth2**, authentifie chaque requête en validant le token, puis autorise à deux
niveaux : des règles d'URL grossières dans la filter chain et des contrôles fins dans le service (`@PreAuthorize`,
contrôles de propriété). Le frontend peut masquer des boutons, mais c'est de l'UX, pas de la sécurité : chaque
contrôle doit aussi exister côté serveur.

#### Q2. Comment stocker les mots de passe ?

**Réponse :** Jamais chiffrés et jamais avec un hash rapide (MD5, SHA-1, SHA-256). Utilisez une **fonction de hachage
de mots de passe lente, salée et adaptative** : Argon2id, bcrypt ou scrypt (PBKDF2 quand la conformité FIPS l'exige).
« Salée » signifie que chaque mot de passe reçoit un sel aléatoire, donc deux mots de passe identiques donnent des
hashs différents et les tables précalculées ne servent à rien. « Adaptative » signifie qu'on peut augmenter le facteur
de coût à mesure que le matériel accélère. Dans Spring, utilisez
`PasswordEncoderFactories.createDelegatingPasswordEncoder()`, qui préfixe l'identifiant de l'algorithme
(`{bcrypt}...`) pour pouvoir migrer d'algorithme en rehachant à la connexion suivante. Encore mieux pour la plupart des
applications métier : ne stockez pas de mots de passe du tout, déléguez à un fournisseur d'identité.

**Exemple :**

```java
PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
String stored = encoder.encode("s3cret!");   // {bcrypt}$2a$10$...
encoder.matches("s3cret!", stored);          // true
```

#### Q3. Que sont OAuth 2.0 et OpenID Connect, et en quoi diffèrent-ils ?

**Réponse :** **OAuth 2.0** est un cadre d'**autorisation déléguée** : il permet à un client d'obtenir un **access
token** pour appeler une API au nom d'un utilisateur (ou en son propre nom), avec des **scopes** limités, sans voir le
mot de passe de l'utilisateur. Il ne dit rien de standard sur l'identité de l'utilisateur. **OpenID Connect (OIDC)**
est une couche d'identité au-dessus d'OAuth 2.0 : il ajoute un **ID token** (un JWT décrivant l'utilisateur
authentifié, destiné au client), un endpoint `userinfo`, la découverte (`/.well-known/openid-configuration`) et des
claims standard. Règle : l'**ID token** sert au client à savoir qui s'est connecté ; l'**access token** sert à l'API.
Envoyer l'ID token à son API comme bearer token est une erreur courante.

#### Q4. Quel flux OAuth2 utiliser pour quel client ?

**Réponse :**

- **SPA navigateur ou app mobile** (client public, ne peut pas garder de secret) : **Authorization Code + PKCE**. Le
  flux implicite est déprécié car il renvoyait les tokens dans l'URL.
- **App web côté serveur ou BFF** (client confidentiel) : Authorization Code (+ PKCE, recommandé partout désormais),
  avec un secret client ou un JWT signé par clé privée.
- **Service à service, sans utilisateur** : **Client Credentials**.
- **Appareils sans navigateur** (TV, CLI) : flux **Device Authorization**.
- Flux **Resource Owner Password** : déprécié ; il remet le mot de passe de l'utilisateur au client.

**Exemple :**

```text
SPA ──(1) redirection /authorize?response_type=code&code_challenge=S256(verifier)──▶ IdP
SPA ◀─(2) retour avec ?code=abc ───────────────────────────────────────────────────── IdP
SPA ──(3) POST /token code=abc&code_verifier=verifier ─────────────────────────────▶ IdP
SPA ◀─(4) access_token (+ refresh_token, id_token) ──────────────────────────────── IdP
SPA ──(5) GET /api/orders  Authorization: Bearer <access_token> ───────────────────▶ API
```

### Attaques web

#### Q5. Qu'est-ce que l'injection SQL, et pourquoi « échapper l'entrée » est-il le mauvais correctif ?

**Réponse :** L'injection SQL survient quand une entrée utilisateur est concaténée dans une chaîne SQL : l'entrée
devient alors du code de la requête (`' OR 1=1 --`). Le correctif est la **requête paramétrée / prepared statement** :
la structure SQL est envoyée séparément des valeurs, donc une valeur ne peut jamais en modifier la structure. Les
paramètres nommés JPA, les requêtes dérivées de Spring Data, `JdbcTemplate` avec `?` et MyBatis `#{}` font tous cela.
L'échappement manuel est fragile (encodages, particularités de dialecte) et facile à oublier une fois. Attention aux
endroits où un paramètre ne peut pas aller : **les noms de colonnes dynamiques ou `ORDER BY`** exigent une liste
blanche, et MyBatis `${}` fait une substitution brute.

**Exemple :**

```java
// ⛔ injectable
em.createQuery("select u from User u where u.email = '" + email + "'");
// ✅ paramétré
em.createQuery("select u from User u where u.email = :email").setParameter("email", email);
// ✅ ORDER BY exige une liste blanche
var column = Set.of("createdAt", "total").contains(sort) ? sort : "createdAt";
```

#### Q6. Qu'est-ce que le XSS, quels types existent, et comment une app React s'en défend-elle ?

**Réponse :** Le cross-site scripting injecte un script contrôlé par l'attaquant dans une page vue par d'autres
utilisateurs, qui s'exécute alors avec la session de la victime. Le XSS **stocké** est enregistré en base (un
commentaire) ; le XSS **réfléchi** rebondit sur un paramètre d'URL ; le XSS **DOM** se produit entièrement dans le
JavaScript côté client. React échappe par défaut tout ce qui est rendu via JSX, ce qui supprime l'essentiel du risque.
Les failles sont `dangerouslySetInnerHTML` (assainir d'abord avec DOMPurify), les `href`/`src` construits à partir
d'une entrée utilisateur (URLs `javascript:`), les API DOM directes (`innerHTML`, `eval`) et les scripts tiers. Défense
en profondeur : une **Content-Security-Policy** stricte (pas d'`unsafe-inline`, nonces ou hashs), des cookies
`HttpOnly` pour que le script ne puisse pas lire les tokens de session, et l'encodage de sortie côté serveur pour tout
HTML qu'il rend.

**Exemple :**

```tsx
// ⛔ exécute <img src=x onerror=...>
<div dangerouslySetInnerHTML={{ __html: comment.body }} />
// ✅ assaini
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />
// ⛔ URL javascript: issue d'une entrée utilisateur
<a href={profile.website}>site</a>   // vérifier que le schéma est http(s)
```

#### Q7. Qu'est-ce que le CSRF, et quand faut-il une protection CSRF ?

**Réponse :** Le cross-site request forgery fait envoyer par le navigateur de la victime une requête modifiant l'état
vers votre site depuis un autre site, et le navigateur **joint automatiquement les cookies de la victime**. Cela
compte dès que l'authentification repose sur des cookies (cookie de session, ou JWT dans un cookie). Défenses : cookies
**SameSite** (`Lax` bloque la plupart des POST inter-sites, `Strict` davantage), un **token CSRF** (synchronizer ou
double-submit) vérifié par le serveur, et le contrôle de l'en-tête `Origin`. Une API qui n'accepte que des en-têtes
`Authorization: Bearer` posés par JavaScript n'est pas exposée au CSRF classique, car le navigateur n'ajoute jamais cet
en-tête de lui-même. C'est pourquoi désactiver le CSRF dans Spring Security convient à une API purement bearer et est
dangereux pour une app à session par cookie.

**Pourquoi c'est un piège :** « On utilise des JWT, donc le CSRF ne s'applique pas » devient faux dès que le JWT est
stocké dans un cookie.

### Spring Security

#### Q8. Comment la filter chain de Spring Security traite-t-elle une requête ?

**Réponse :** Un filtre servlet, `DelegatingFilterProxy`, passe la requête à `FilterChainProxy`, qui choisit la
première `SecurityFilterChain` dont le matcher correspond (on peut en définir plusieurs, par exemple une pour `/api/**`
avec bearer tokens et une pour `/admin/**` avec form login). Cette chaîne exécute une liste ordonnée de filtres : CORS,
CSRF, filtres d'authentification (`BearerTokenAuthenticationFilter`, `UsernamePasswordAuthenticationFilter`), qui
construisent une `Authentication` et la stockent dans le `SecurityContextHolder` ; puis `ExceptionTranslationFilter`,
qui transforme `AuthenticationException` en 401 et `AccessDeniedException` en 403 ; et enfin `AuthorizationFilter`, qui
applique les règles d'URL. La sécurité de méthode (`@PreAuthorize`) s'exécute plus tard, via un proxy AOP autour de
vos beans.

**Exemple :**

```java
@Bean
SecurityFilterChain api(HttpSecurity http) throws Exception {
    return http
        .securityMatcher("/api/**")
        .authorizeHttpRequests(a -> a
            .requestMatchers(HttpMethod.GET, "/api/products/**").permitAll()
            .requestMatchers("/api/admin/**").hasRole("ADMIN")
            .anyRequest().authenticated())
        .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .csrf(c -> c.disable())              // API bearer uniquement, voir Q7
        .build();
}
```

#### Q9. Comment configurer une API Spring Boot en resource server OAuth2 ?

**Réponse :** Ajoutez `spring-boot-starter-oauth2-resource-server` et définissez l'émetteur :
`spring.security.oauth2.resourceserver.jwt.issuer-uri`. Spring récupère le document de découverte et le JWKS (clés
publiques) de l'émetteur, vérifie la signature, `exp`/`nbf` et `iss` à chaque requête, et met les clés en cache (il les
recharge quand il voit un `kid` inconnu, ce qui gère la rotation des clés). Il faut encore ajouter la **validation de
l'audience** (le token doit être destiné à cette API) et mapper les claims en autorités : par défaut les scopes
deviennent `SCOPE_x` ; des rôles dans un claim personnalisé (par exemple `realm_access.roles` de Keycloak) nécessitent
un `JwtAuthenticationConverter`.

**Exemple :**

```java
@Bean
JwtDecoder jwtDecoder(@Value("${spring.security.oauth2.resourceserver.jwt.issuer-uri}") String issuer) {
    NimbusJwtDecoder decoder = JwtDecoders.fromIssuerLocation(issuer);
    decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
        JwtValidators.createDefaultWithIssuer(issuer),
        new JwtClaimValidator<List<String>>("aud", aud -> aud != null && aud.contains("orders-api"))));
    return decoder;
}
```

## 🟡 Pièges seniors

### Questions

#### Q10. Que faut-il exactement valider sur un JWT avant de lui faire confiance ?

**Réponse :** La **signature** avec une clé du JWKS de l'émetteur, selon une **liste blanche d'algorithmes** choisie
par le serveur (ne jamais faire confiance à l'en-tête `alg` du token : les attaques `alg: none` et la confusion
RS256→HS256 l'exploitent). **`iss`** égal à l'émetteur attendu. **`aud`** contenant cette API. **`exp`** et **`nbf`**
avec une petite tolérance d'horloge. Puis les **scopes/rôles** pour l'opération. Rappelez-vous aussi qu'un JWT est
**signé, pas chiffré** : n'importe qui peut le décoder en base64, donc ne mettez jamais de secrets ni de données
personnelles sensibles dans les claims.

**Pourquoi c'est un piège :** Beaucoup de filtres écrits à la main se contentent de décoder le token et de lire `sub`,
ou vérifient la signature mais sautent `aud`, ce qui laisse un token émis pour une autre API du même realm appeler la
vôtre.

#### Q11. Comment révoquer un JWT, et quelle place pour les refresh tokens ?

**Réponse :** Un JWT autoportant reste valide jusqu'à `exp` ; l'API ne demande rien à personne. Options, par coût :
garder des access tokens **courts** (5–15 minutes) et accepter cette fenêtre ; utiliser des **refresh tokens** (plus
longs, stockés de façon sûre, **renouvelés** à chaque usage avec détection de réutilisation, révocables chez le
fournisseur d'identité) pour obtenir de nouveaux access tokens ; pour une révocation immédiate, tenir une **liste
noire** d'identifiants de token (`jti`) ou un horodatage « tokens émis avant » par utilisateur dans un store rapide,
vérifié à chaque requête ; ou utiliser des **tokens opaques avec introspection**, ce qui fait appeler le fournisseur
d'identité (ou un cache) à chaque requête. Les sessions côté serveur sont le plus simple quand il faut une déconnexion
instantanée avec un seul backend.

**Pourquoi c'est un piège :** une « déconnexion » dans une SPA qui supprime seulement le token localement laisse une
copie volée utilisable jusqu'à expiration.

#### Q12. Qu'est-ce que l'IDOR (broken object-level authorization), et pourquoi les scanners le ratent-ils ?

**Réponse :** Insecure Direct Object Reference : l'API vérifie que l'appelant est authentifié, mais pas que **cet**
objet lui appartient. `GET /api/invoices/1043` fonctionne pour tout utilisateur connecté qui change l'identifiant.
C'est le premier élément de l'OWASP API Security Top 10. Les scanners et les contrôles de rôle le ratent parce que la
requête est bien formée et que l'utilisateur a le bon rôle ; seule la relation métier est fausse. Corrigez-le dans la
couche d'accès aux données : requêter par identifiant **et** propriétaire/tenant (`findByIdAndCustomerId`), ou vérifier
la propriété dans une expression `@PreAuthorize` ou un service du domaine, et renvoyer 404 plutôt que 403 pour ne pas
confirmer que l'identifiant existe. Des UUID aléatoires rendent les identifiants plus durs à deviner mais ne sont pas
de l'autorisation.

**Exemple :**

```java
// ⛔ tout utilisateur authentifié peut lire n'importe quelle facture
return invoiceRepo.findById(id).orElseThrow(NotFoundException::new);
// ✅ limité à l'appelant
return invoiceRepo.findByIdAndCustomerId(id, currentUser.customerId()).orElseThrow(NotFoundException::new);
```

**Pourquoi c'est un piège :** un `hasRole("CUSTOMER")` au niveau de l'endpoint paraît complet en revue ; la
vulnérabilité est dans la requête.

#### Q13. Qu'est-ce que le SSRF, et comment l'empêcher ?

**Réponse :** Server-side request forgery : le serveur récupère une URL contrôlée par l'attaquant (URL de webhook,
fonctionnalité « importer depuis une URL », proxy d'images, moteur de rendu PDF), et l'attaquant la fait pointer vers
des cibles internes : l'endpoint de métadonnées cloud `169.254.169.254` (qui peut divulguer des identifiants IAM), des
services d'administration internes, ou `localhost`. Défenses : **liste blanche** des destinations quand c'est
possible ; sinon résoudre l'hôte et **bloquer les plages privées, loopback, link-local et métadonnées** après
résolution DNS (et revérifier sur les redirections, car le DNS rebinding et les redirections contournent un contrôle
sur la chaîne du nom d'hôte) ; désactiver ou limiter les redirections ; exécuter les récupérateurs dans un segment
réseau isolé sans route vers les services internes ; et sur AWS imposer **IMDSv2**, qui exige un token qu'un simple GET
SSRF ne peut pas obtenir.

**Pourquoi c'est un piège :** vérifier que l'URL « commence par https:// » ou n'est pas littéralement `localhost` est
contourné par `https://127.0.0.1.nip.io`, des IP décimales ou une redirection ouverte.

#### Q14. Où une app navigateur doit-elle stocker les tokens, et qu'est-ce qu'un BFF ?

**Réponse :** Les compromis entre `localStorage`, mémoire et cookies sont traités dans [Full Stack Q13](fullstack-devops-k8s.md).
La réponse senior pour une app sensible est le pattern **Backend for Frontend (BFF)** : un petit composant côté serveur
(Spring Cloud Gateway avec `TokenRelay`, ou un service dédié) joue le rôle de client OAuth confidentiel. Il exécute le
code flow, garde access et refresh tokens côté serveur, et ne donne au navigateur qu'un **cookie de session
`HttpOnly`, `Secure`, `SameSite`**. Le navigateur ne voit jamais de token, donc un XSS ne peut pas en voler (il peut
encore agir comme l'utilisateur tant que la page est ouverte). En échange, il faut une protection CSRF sur le BFF et un
composant avec état à exploiter.

**Pourquoi c'est un piège :** « On utilise PKCE, donc les tokens dans la SPA sont sûrs » mélange deux problèmes : PKCE
protège l'échange du code, pas les tokens posés dans un stockage lisible par JavaScript.

#### Q15. Concrètement, qu'est-ce que la sécurité de la chaîne d'approvisionnement logicielle pour un projet Java/Node ?

**Réponse :** Votre build tire des centaines de dépendances transitives, d'images de base et d'actions CI, chacune
pouvant être vulnérable ou malveillante. Pratiques : **épingler les versions** avec des lockfiles
(`package-lock.json`, verrouillage des dépendances Gradle) et épingler actions CI et images de base par digest ;
**scanner** dépendances et images (OWASP Dependency-Check, Trivy, Snyk, Dependabot/Renovate pour les mises à jour) et
faire échouer le build sur les vulnérabilités critiques réellement atteignables ; générer un **SBOM** (CycloneDX) par
build pour répondre à « sommes-nous touchés par la CVE-X ? » en quelques minutes ; **signer** artefacts et images
(Sigstore/cosign) et vérifier les signatures au déploiement ; utiliser un proxy de registre privé ; surveiller le
**typosquatting et la dependency confusion** (un nom de package interne publié publiquement avec une version
supérieure) ; et lancer `npm ci` avec `--ignore-scripts` quand les scripts d'installation ne sont pas nécessaires.

**Exemple :**

```text
Jour de Log4Shell : « quels services embarquent log4j-core < 2.17.1 ? »
Avec des SBOM indexés : une requête, 15 minutes.
Sans : grep dans chaque dépôt, rebuild pour inspecter les fat jars, deux jours.
```

**Pourquoi c'est un piège :** ne scanner que les dépendances directes rate l'essentiel de l'arbre ; Log4Shell est
surtout arrivé de façon transitive.

## 🔴 Expert / Ouvert

### Questions

#### Q16. Comment propager l'identité de l'utilisateur entre microservices ?

**Réponse :** Options : **transmettre l'access token de l'utilisateur** (simple, chaque service le valide et voit le
vrai utilisateur, mais l'audience du token doit inclure chaque service, et un service compromis peut le rejouer
ailleurs) ; l'**échange de token** (RFC 8693 : la gateway ou le service échange le token utilisateur contre un nouveau
token à portée restreinte pour le service aval, en gardant l'utilisateur comme sujet et l'appelant comme acteur) ; ou
**l'identité de service seule** (client credentials ou mTLS) avec l'identifiant utilisateur passé dans un en-tête de
confiance, sûr uniquement si le réseau garantit que personne d'autre ne peut poser cet en-tête. Pour
l'authentification de service à service, un service mesh avec **mTLS** (Istio, Linkerd) ou des identités SPIFFE
supprime les secrets partagés. Quel que soit le choix, l'autorisation sur les données utilisateur reste dans le
service qui les possède.

#### Q17. Comment mèneriez-vous une séance de threat modeling pour une nouvelle fonctionnalité ?

**Réponse :** Légère et tôt, dans la revue de conception. Dessinez un **diagramme de flux de données** : acteurs,
processus, stockages, flux, et **frontières de confiance** (navigateur↔API, API↔tiers, tenant↔tenant). Parcourez chaque
flux avec **STRIDE** : Spoofing (usurpation), Tampering (altération), Repudiation (répudiation), Information disclosure
(divulgation), Denial of service (déni de service), Elevation of privilege (élévation de privilèges). Pour chaque menace
crédible, écrivez la mitigation, un responsable et un test, et classez par probabilité × impact. Résultat : une courte
liste d'exigences de sécurité dans les tickets, pas un document de 40 pages. Le rôle d'un tech lead est d'en faire une
habitude (un modèle dans le design doc, 30 minutes par fonctionnalité significative) et d'impliquer l'équipe sécurité
sur les zones à haut risque comme le paiement, l'authentification et le traitement de fichiers.

**Exemple :**

```text
Fonctionnalité : « téléverser une facture PDF »
S  — téléverser au nom d'un autre tenant ?        → tenant tiré du token, jamais d'un champ de formulaire
T  — PDF remplacé après l'antivirus ?             → stockage par hash de contenu, bucket immuable
I  — URL de bucket public devinable ?             → bucket privé, URLs signées courtes
D  — téléversement de 2 Go ?                      → limite de taille à la gateway + streaming
E  — PDF malveillant exploitant le moteur de rendu ? → rendu dans un worker isolé sans réseau
```

#### Q18. Comment protéger les données sensibles au repos et dans les logs, et où le chiffrement aide-t-il vraiment ?

**Réponse :** Commencez par **minimiser** : ne collectez ni ne conservez ce dont vous n'avez pas besoin, et fixez une
durée de rétention. Le chiffrement **au repos** (disque, RDS, S3 avec KMS) protège contre le vol de disques et de
snapshots, pas contre un attaquant qui passe par votre application, car l'app déchiffre de façon transparente. Pour les
champs à forte valeur (numéros d'identité, IBAN, données de santé), ajoutez un **chiffrement applicatif ou par colonne**
avec des clés dans un KMS et du **chiffrement d'enveloppe** (une clé de données par enregistrement ou par tenant,
enveloppée par une clé maîtresse), pour qu'un dump de base seul soit inutilisable et que les clés puissent tourner.
Utilisez la **tokenisation** quand d'autres systèmes ont besoin d'une référence mais pas de la valeur. Utilisez le
**hachage** (HMAC avec une clé secrète) quand seules les recherches d'égalité sont nécessaires. Gardez les données
personnelles hors des logs avec du logging structuré et du masquage, et rendez l'accès aux données auditable. Le
chiffrement en transit (TLS partout, y compris dans le cluster) est le socle.

#### Q19. Comment concevez-vous la protection de données de santé sensibles (authentification, accès, audit, chiffrement, conservation) ?

**Réponse :** Les données de santé sont une catégorie particulière au sens du RGPD (et en France doivent être hébergées chez un
hébergeur certifié HDS) ; on conçoit donc dès le départ avec **moindre privilège, traçabilité et minimisation**, en couches.
(1) **Authentification** : authentification forte des praticiens (MFA, et schémas nationaux comme Pro Santé Connect le cas
échéant), OIDC avec jetons d'accès de courte durée (voir [Security Q9](security.md), [Security Q10](security.md)), expiration
de session et contrôle d'appareil. (2) **Autorisation** : refus par défaut, contrôles par rôle et **par relation** (« ce
praticien suit ce patient »), contrôles au niveau objet sur chaque endpoint pour éviter l'IDOR (voir
[Security Q12](security.md)), et une voie **« bris de glace »** pour les urgences, journalisée de façon très visible. (3)
**Minimisation des données et limitation des finalités** : ne collecter et n'exposer que les champs nécessaires au cas
d'usage ; index de recherche et analytique sur des données pseudonymisées ou agrégées ; séparer données d'identité et données
cliniques pour qu'une fuite ne révèle pas les deux. (4) **Audit** : un journal en ajout seul, inviolable, de *qui* a consulté
ou modifié *quel* dossier patient, *quand*, *pourquoi* et d'où, y compris les lectures ; conservé séparément, relu, avec
alertes (volume inhabituel, hors horaires, dossiers « sensibles »). Ne mettez jamais de données de santé dans les logs ou
traces applicatifs (masquer les identifiants). (5) **Chiffrement** : TLS 1.2+ partout y compris entre services internes,
chiffrement au repos (disque et base), **chiffrement au niveau du champ / par enveloppe** pour les colonnes les plus
sensibles avec des clés dans un KMS/HSM, clés par tenant si nécessaire, rotation des clés et politiques d'accès strictes (voir
[Security Q18](security.md)). (6) **Secrets** : aucun secret dans le code ou les images ; un coffre ou gestionnaire de secrets
cloud avec rotation et identifiants de base de courte durée. (7) **Conservation et droits** : durées de conservation par
catégorie de données, suppression ou archivage automatisés, prise en charge des demandes d'accès/rectification/effacement
(l'effacement face à l'obligation légale de conserver les dossiers médicaux est une décision métier/juridique à faire
remonter), registre des consentements, et sauvegardes soumises aux mêmes règles. (8) **Hygiène des environnements** : aucune
donnée de production en dev/test (données synthétiques ou anonymisées uniquement), segmentation réseau, analyse des
dépendances et des images, tests d'intrusion, processus de réponse aux incidents et de notification de violation (72 h pour le
RGPD).

**Exemple :**

```java
@PreAuthorize("hasRole('PRACTITIONER') and @careTeam.isInCareTeam(authentication.name, #patientId)")
public PatientRecord read(UUID patientId) {
    PatientRecord r = records.findById(patientId).orElseThrow();
    audit.log(AuditEvent.read(currentUser(), patientId, request.purpose(), request.ip())); // stockage en ajout seul
    return r;
}
```

```sql
-- Protection au niveau du champ : l'application chiffre avec une clé de données KMS ; la colonne ne contient que du chiffré.
ALTER TABLE patient ADD COLUMN national_id_enc bytea, ADD COLUMN national_id_hmac bytea; -- hmac = index aveugle pour les recherches d'égalité
-- Row Level Security comme seconde ligne de défense :
ALTER TABLE medical_note ENABLE ROW LEVEL SECURITY;
CREATE POLICY care_team ON medical_note USING (patient_id IN (SELECT patient_id FROM care_team WHERE user_id = current_setting('app.user_id')::uuid));
```

**Pourquoi c'est un piège :** réduire la conformité à « activer le chiffrement » ignore les vraies fuites habituelles :
autorisations trop larges, données de santé dans les logs et exports analytiques, copies en environnements hors production, et
absence de piste d'audit pour prouver qui a consulté un dossier. Précisez que les points juridiques (HDS, consentement, durées
de conservation) se confirment auprès du DPO/service juridique plutôt que de s'en remettre à des suppositions.

## 🎯 Scénarios réels

### S1. Un client signale qu'il peut voir les factures d'un autre client en changeant l'URL

- **Symptômes :** Le support transmet une capture : `/invoices/18342` affiche la facture d'une autre entreprise. Les
  tests d'intrusion de l'an dernier étaient passés.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** IDOR classique. Confirmer sur l'endpoint : il vérifie l'authentification et le rôle mais charge la
  facture par identifiant seulement. Puis chercher le même motif partout : chaque `findById` atteignable depuis un
  controller avec un identifiant dans le chemin. Vérifier dans les logs d'accès s'il y a eu énumération (un utilisateur
  demandant beaucoup d'identifiants séquentiels) pour mesurer l'exposition.
- **Exemple :**

  ```text
  grep -rn "findById(id)" src/main/java/**/web
  log d'accès : l'utilisateur 7731 a demandé /invoices/18000..18450 en 4 minutes
  ```

- **Résolution :** Corriger en urgence l'endpoint pour requêter par identifiant et tenant (404 sinon), déployer, puis
  corriger toutes les autres occurrences. Traiter comme une violation de données : impliquer la sécurité et le DPO,
  déterminer quels enregistrements ont été consultés, et notifier comme l'exige le RGPD (72 heures auprès de
  l'autorité).
- **Prévention :** Imposer le cloisonnement par tenant de façon centrale (filtre Hibernate ou row-level security
  PostgreSQL basée sur une variable de session), ajouter un test d'autorisation par endpoint (« l'utilisateur A ne peut
  pas lire la ressource de B »), et ajouter les contrôles BOLA à la checklist de revue.

</details>

### S2. Une clé de signature JWT apparaît dans un dépôt GitHub public

- **Symptômes :** Le secret scanning de GitHub (ou un chercheur externe) signale que le secret HS256 utilisé pour signer
  les tokens a été commité il y a six mois dans une config de test.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Avec cette clé, n'importe qui peut forger des tokens valides pour tout utilisateur et tout rôle.
  Partir du principe que c'est compromis. Vérifier si la même clé est utilisée en production, combien de temps elle a
  été publique, et chercher dans les logs des tokens aux claims, émetteurs ou sujets inhabituels qui ne se sont jamais
  connectés.
- **Exemple :**

  ```bash
  git log -S "jwt.secret" --all
  logs : tokens avec sub=admin émis hors du service d'authentification (aucun événement de login correspondant)
  ```

- **Résolution :** **Faire tourner la clé immédiatement** (tous les tokens existants deviennent invalides, les
  utilisateurs se reconnectent), la retirer de l'historique (BFG/`git filter-repo`) en sachant que la fuite elle-même
  est déjà définitive, et auditer les actions effectuées avec des tokens suspects.
- **Prévention :** Passer à une **signature asymétrique** (RS256/ES256) par un fournisseur d'identité, pour que les API
  ne détiennent que des clés publiques ; garder les secrets dans un vault ; activer la push protection des secrets ;
  prévoir la rotation des clés avec `kid` pour qu'elle soit une routine plutôt qu'une urgence.

</details>

### S3. Un scan de sécurité signale une CVE critique dans une dépendance transitive un vendredi après-midi

- **Symptômes :** Le pipeline échoue désormais sur un CVSS 9.8 dans une bibliothèque qu'aucun code n'importe
  directement ; une release est prévue lundi.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Trouver quel chemin la tire et si le code vulnérable est **atteignable** dans votre usage (l'avis
  nomme la classe ou la fonctionnalité concernée). Vérifier si elle est exploitée activement (CISA KEV, score EPSS).
  Vérifier quels services l'embarquent via l'index des SBOM.
- **Exemple :**

  ```text
  ./gradlew dependencyInsight --dependency snakeyaml
  snakeyaml:1.33  <- spring-boot-starter:3.0.5
  avis : RCE lors du parsing de YAML non fiable avec le constructeur par défaut
  notre usage : parse seulement notre application.yml au démarrage -> non atteignable depuis une entrée utilisateur
  ```

- **Résolution :** Si atteignable ou activement exploitée : mettre à jour (ou forcer la version par une
  contrainte/BOM) et livrer aujourd'hui. Sinon : enregistrer une exception limitée dans le temps avec sa
  justification, maintenir la release, et planifier la mise à jour.
- **Prévention :** Renovate/Dependabot avec des mises à jour groupées hebdomadaires pour garder l'écart faible, un SBOM
  par artefact, et une politique écrite sur la sévérité, l'atteignabilité et les délais pour que les décisions du
  vendredi ne soient pas improvisées.

</details>

### S4. Après le déplacement du frontend vers un nouveau domaine, des utilisateurs connectés reçoivent des 403 sur chaque POST

- **Symptômes :** Les GET fonctionnent ; les POST/PUT/DELETE échouent en 403 pour certains utilisateurs seulement. Le
  frontend est passé de `app.example.com` à `example.com/app`, et parle toujours à la même API à session par cookie.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un 403 uniquement sur les méthodes qui modifient l'état oriente vers le **CSRF**, pas vers
  l'authentification. Vérifier que le cookie CSRF est toujours envoyé et lu : son `Path`/`Domain` était limité à
  l'ancien hôte, donc le frontend ne peut pas lire `XSRF-TOKEN` et n'envoie pas l'en-tête. Les utilisateurs qui ont un
  ancien cookie fonctionnent encore, ce qui explique le « certains ».
- **Exemple :**

  ```text
  DevTools : POST /api/orders -> 403, pas d'en-tête X-XSRF-TOKEN
  Set-Cookie: XSRF-TOKEN=...; Domain=app.example.com; Path=/
  Log Spring : "Invalid CSRF token found for http://example.com/api/orders"
  ```

- **Résolution :** Configurer `CookieCsrfTokenRepository` avec le bon chemin/domaine (et `withHttpOnlyFalse()` pour que
  la SPA puisse le lire), et s'assurer que la SPA envoie l'en-tête sur chaque requête de modification.
- **Prévention :** Un smoke test end-to-end qui effectue un POST après connexion à chaque déploiement, et une checklist
  de migration explicite pour les changements de domaine (cookies, CORS, CSP, redirect URIs chez le fournisseur
  d'identité).

</details>

## 🗣️ Questions posées en entretien

Questions rapportées d'entretiens réels, regroupées par sujet. Chacune a une courte réponse type : approfondissez avec les questions et scénarios détaillés ci-dessus, et dites la réponse à voix haute.

### Tokens & authentification

#### R1. Différence et relation entre OAuth 2.0, JWT et OpenID Connect.

**Réponse :** **OAuth 2.0** est un framework d'autorisation (accès délégué via des access tokens). **OpenID Connect** est une couche d'identité par-dessus (ajoute l'ID token et `/userinfo`, soit *qui est l'utilisateur*). **JWT** n'est qu'un *format* de jeton (JSON signé), utilisé pour les ID tokens OIDC et souvent les access tokens OAuth. OAuth ≠ authentification, JWT ≠ protocole.

#### R2. Expliquez la structure d'un JWT et le flux d'authentification/validation.

**Réponse :** `header.payload.signature`, en base64url : en-tête (`alg`, `kid`), claims (`sub`, `iss`, `aud`, `exp`, rôles), signature.

Flux : l'utilisateur se connecte → le serveur d'auth émet un JWT de courte durée → le client envoie `Authorization: Bearer` → le serveur de ressources vérifie la signature (clé publique JWKS, algorithme imposé), `iss`, `aud`, `exp`/`nbf`, puis autorise d'après les claims.

Courte expiration plus refresh tokens ; jamais de secrets dans le payload (il est seulement signé).

#### R3. Comment déboguer une erreur 401 Unauthorized ?

**Réponse :** 401 = *non authentifié*.

Vérifier que la requête porte l'identifiant (en-tête `Authorization` présent, bon schéma), que le jeton n'est pas expiré (`exp`, décalage d'horloge), que signature/`iss`/`aud` correspondent à la config du serveur, le bon environnement/realm/clé (rotation JWKS), qu'un proxy ou une gateway ne retire pas l'en-tête, et les logs serveur en DEBUG pour la raison exacte de l'échec.

Décoder le JWT (sans lui faire confiance) pour inspecter les claims. Ne pas confondre avec **403** (authentifié mais non autorisé).

### Réponse à incident

#### R4. Un secret a été commité par erreur sur GitHub et déjà cloné. Quelles sont vos prochaines étapes exactes ?

**Réponse :** 1) **Révoquer/faire tourner le secret immédiatement** (le considérer compromis ; supprimer le commit ne suffit pas). 2) Examiner logs/CloudTrail pour tout usage depuis le commit. 3) Le retirer de l'historique (`git filter-repo`/BFG) et force-push, sachant que clones et forks le gardent. 4) Émettre le nouveau secret via un gestionnaire de secrets, jamais dans le dépôt. 5) Prévention : scan de secrets en pre-commit/CI (gitleaks), push protection GitHub, et court post-mortem. Voir aussi [Full Stack & DevOps](fullstack-devops-k8s.md).

## 🎤 Quiz oral

Dix questions réparties sur les niveaux. Répondez à chacune **à voix haute en 2–3 minutes**, sans regarder, en structurant : contexte → options → décision → compromis. Ouvrez ensuite la question et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Sous 24/30, refaites les points faibles après deux semaines. Les questions et scénarios sont dans les sections ci-dessus.

1. Q3. Que sont OAuth 2.0 et OpenID Connect, et en quoi diffèrent-ils ?
2. Q4. Quel flux OAuth2 utiliser pour quel client ?
3. Q7. Qu'est-ce que le CSRF, et quand faut-il une protection CSRF ?
4. Q8. Comment la filter chain de Spring Security traite-t-elle une requête ?
5. Q10. Que faut-il exactement valider sur un JWT avant de lui faire confiance ?
6. Q11. Comment révoquer un JWT, et quelle place pour les refresh tokens ?
7. Q12. Qu'est-ce que l'IDOR (broken object-level authorization), et pourquoi les scanners le ratent-ils ?
8. Q15. Concrètement, qu'est-ce que la sécurité de la chaîne d'approvisionnement logicielle pour un projet Java/Node ?
9. Q17. Comment mèneriez-vous une séance de threat modeling pour une nouvelle fonctionnalité ?
10. S2. Une clé de signature JWT apparaît dans un dépôt GitHub public

## 📌 Cheat-sheet

### Identité & tokens

> **Pour commencer :** l'authentification prouve qui, l'autorisation décide quoi ; le serveur vérifie les deux à chaque requête.

- **Mots de passe** — Argon2id/bcrypt/scrypt, salés, adaptatifs. *Ou déléguer à un fournisseur d'identité.*
- **OAuth2 vs OIDC** — OAuth2 = accès délégué (access token) ; OIDC = identité (ID token). *Ne jamais envoyer l'ID token à l'API.*
- **Flux** — SPA/mobile : code + PKCE ; serveur : code ; machine : client credentials ; appareils : device flow. *Implicite et password sont dépréciés.*
- **Validation JWT** — signature avec alg en liste blanche, `iss`, `aud`, `exp`/`nbf`, puis scopes. *Signé ≠ chiffré.*
- **Révocation** — access tokens courts, refresh tokens renouvelés, liste noire par `jti`, ou introspection.
- **BFF** — tokens côté serveur, cookie `HttpOnly` vers le navigateur. *Exige une protection CSRF.*

### Attaques web

> **Pour commencer :** ne jamais laisser une donnée devenir du code — paramétrer les requêtes, échapper la sortie, vérifier la propriété.

- **SQLi** — des paramètres partout ; liste blanche pour les noms de colonnes et `ORDER BY` ; MyBatis `#{}` et non `${}`.
- **XSS** — React échappe le JSX ; surveiller `dangerouslySetInnerHTML`, les URLs `javascript:` ; CSP stricte.
- **CSRF** — compte avec les cookies ; SameSite + token + contrôle d'Origin. *Les API à en-tête bearer ne sont pas exposées.*
- **IDOR/BOLA** — requêter par identifiant **et** propriétaire/tenant ; renvoyer 404. *Les contrôles de rôle ne l'attrapent pas.*
- **SSRF** — liste blanche, bloquer les plages privées après DNS, pas de redirections, IMDSv2.

### Spring Security

> **Pour commencer :** `FilterChainProxy` → `SecurityFilterChain` correspondante → filtres d'authentification → traduction des exceptions → autorisation.

- **Resource server** — `issuer-uri`, cache JWKS, ajouter un validateur `aud`, mapper les rôles avec `JwtAuthenticationConverter`.
- **401 vs 403** — non authentifié vs authentifié mais non autorisé (`ExceptionTranslationFilter`).
- **Sécurité de méthode** — `@PreAuthorize` pour la propriété et les règles fines ; voir [Spring Q41](spring-architecture.md).

### Plateforme & processus

> **Pour commencer :** savoir ce qu'on livre, garder les secrets hors du code, et éliminer les menaces dès la conception.

- **Supply chain** — lockfiles, digests épinglés, scan, SBOM (CycloneDX), signature (cosign). *Surveiller les dépendances transitives et la dependency confusion.*
- **Identité de service** — transmission du token vs échange de token vs mTLS/SPIFFE.
- **Protection des données** — minimiser, chiffrer au repos, chiffrement d'enveloppe pour les champs sensibles, masquer les logs.
- **Threat modeling** — diagramme de flux + frontières de confiance + STRIDE ; résultat = tickets avec responsables.
