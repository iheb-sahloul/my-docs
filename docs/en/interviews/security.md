# Security

Rules and code-review checklists live in [Best practices › Security](../best-practices/security.md); this module is the interview Q&A. Related questions elsewhere: CORS in [Full Stack Q12](fullstack-devops-k8s.md#browser-request-fail-cors-error), token storage in [Full Stack Q13](fullstack-devops-k8s.md#jwt-localstorage-jwt-httponly-cookie), Kubernetes secrets in [Full Stack Q38](fullstack-devops-k8s.md#application-secrets-managed-kubernetes-kubernetes), the OWASP Top 10 at design level in [System Design Q34](system-design.md#name-several-owasp-top-10), and URL vs method authorization in [Spring Q41](spring-architecture.md#authorization-live-url-rules-method).

## 🟢 Fundamentals

### Identity

#### Q1. Authentication vs authorization — and where does each happen in a typical Spring + React app? {#authentication-authorization-each-spring-react}
**Answer:** **Authentication** answers "who are you?" (verify credentials or a token and establish an identity).
**Authorization** answers "what may you do?" (check that identity's roles, scopes or ownership against the resource).
In a modern setup, the React app sends the user to an identity provider (Keycloak, Auth0, Entra ID, Cognito), gets
tokens back, and calls the API with an access token. The Spring API, configured as an **OAuth2 resource server**,
authenticates each request by validating the token, then authorizes at two levels: coarse URL rules in the filter
chain and fine-grained checks in the service (`@PreAuthorize`, ownership checks). The frontend may hide buttons, but
that is UX, not security: every check must also exist on the server.

#### Q2. How should passwords be stored? {#passwords-stored}
**Answer:** Never encrypted and never with a fast hash (MD5, SHA-1, SHA-256). Use a **slow, salted, adaptive
password hashing function**: Argon2id, bcrypt or scrypt (PBKDF2 when FIPS compliance requires it). "Salted" means
each password gets a random salt, so identical passwords produce different hashes and precomputed tables are useless.
"Adaptive" means you can raise the cost factor as hardware gets faster. In Spring, use
`PasswordEncoderFactories.createDelegatingPasswordEncoder()`, which prefixes the algorithm id (`{bcrypt}...`) so you can
migrate algorithms by rehashing on next login. Better still for most business apps: don't store passwords at all;
delegate to an identity provider.

**Example:**

```java
PasswordEncoder encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
String stored = encoder.encode("s3cret!");   // {bcrypt}$2a$10$...
encoder.matches("s3cret!", stored);          // true
```

#### Q3. What are OAuth 2.0 and OpenID Connect, and how do they differ? {#oauth-2-0-openid-connect}
**Answer:** **OAuth 2.0** is a **delegated authorization** framework: it lets a client obtain an **access token** to
call an API on behalf of a user (or itself), with limited **scopes**, without seeing the user's password. It says
nothing standard about who the user is. **OpenID Connect (OIDC)** is an identity layer on top of OAuth 2.0: it adds an
**ID token** (a JWT describing the authenticated user, meant for the client), a `userinfo` endpoint, discovery
(`/.well-known/openid-configuration`) and standard claims. Rule: the **ID token** is for the client to know who logged
in; the **access token** is for the API. Sending the ID token to your API as a bearer token is a common mistake.

#### Q4. Which OAuth2 flow do you use for which client? {#oauth2-flow-client}
**Answer:**

- **Browser SPA or mobile app** (public client, can't keep a secret): **Authorization Code + PKCE**. The implicit
  flow is deprecated because it returned tokens in the URL.
- **Server-side web app or BFF** (confidential client): Authorization Code (+ PKCE, recommended everywhere now),
  with a client secret or private-key JWT.
- **Service to service, no user**: **Client Credentials**.
- **Devices without a browser** (TV, CLI): **Device Authorization** flow.
- **Resource Owner Password** flow: deprecated; it hands the user's password to the client.

**Example:**

```text
SPA ──(1) redirect /authorize?response_type=code&code_challenge=S256(verifier)──▶ IdP
SPA ◀─(2) redirect back with ?code=abc ───────────────────────────────────────── IdP
SPA ──(3) POST /token code=abc&code_verifier=verifier ──────────────────────────▶ IdP
SPA ◀─(4) access_token (+ refresh_token, id_token) ───────────────────────────── IdP
SPA ──(5) GET /api/orders  Authorization: Bearer <access_token> ────────────────▶ API
```

### Web attacks

#### Q5. What is SQL injection, and why is "escaping input" the wrong fix? {#sql-injection-escaping-input-wrong}
**Answer:** SQL injection happens when user input is concatenated into a SQL string, so the input becomes part of the
query's code (`' OR 1=1 --`). The fix is **parameterized queries / prepared statements**: the SQL structure is sent
separately from the values, so a value can never change the structure. JPA named parameters, Spring Data derived
queries, `JdbcTemplate` with `?` and MyBatis `#{}` all do this. Hand-escaping is fragile (encodings, dialect quirks)
and easy to forget once. Watch the places parameters can't go: **dynamic column names or `ORDER BY`** need an allowlist,
and MyBatis `${}` performs raw substitution.

**Example:**

```java
// ⛔ injectable
em.createQuery("select u from User u where u.email = '" + email + "'");
// ✅ parameterized
em.createQuery("select u from User u where u.email = :email").setParameter("email", email);
// ✅ ORDER BY needs an allowlist
var column = Set.of("createdAt", "total").contains(sort) ? sort : "createdAt";
```

#### Q6. What is XSS, which kinds exist, and how does a React app defend against it? {#xss-kinds-exist-react-app}
**Answer:** Cross-site scripting injects attacker-controlled script into a page viewed by other users, so it runs with
the victim's session. **Stored** XSS is saved in the database (a comment); **reflected** XSS bounces off a URL
parameter; **DOM-based** XSS happens entirely in client-side JavaScript. React escapes everything rendered through
JSX by default, which removes most risk. The holes are `dangerouslySetInnerHTML` (sanitize with DOMPurify first),
`href`/`src` built from user input (`javascript:` URLs), direct DOM APIs (`innerHTML`, `eval`), and third-party
scripts. Defence in depth: a strict **Content-Security-Policy** (no `unsafe-inline`, nonces or hashes), `HttpOnly`
cookies so script can't read session tokens, and output encoding on the server for any HTML it renders.

**Example:**

```tsx
// ⛔ executes <img src=x onerror=...>
<div dangerouslySetInnerHTML={{ __html: comment.body }} />
// ✅ sanitized
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />
// ⛔ javascript: URL from user input
<a href={profile.website}>site</a>   // validate the scheme is http(s)
```

#### Q7. What is CSRF, and when do you need CSRF protection? {#csrf-need-csrf-protection}
**Answer:** Cross-site request forgery makes the victim's browser send a state-changing request to your site from
another site, and the browser **attaches the victim's cookies automatically**. It matters whenever authentication
rides on cookies (session cookie, or a JWT in a cookie). Defences: **SameSite** cookies (`Lax` blocks most cross-site
POSTs, `Strict` blocks more), a **CSRF token** (synchronizer or double-submit) checked by the server, and checking
`Origin`. An API that only accepts `Authorization: Bearer` headers set by JavaScript is not exposed to classic CSRF,
because the browser never adds that header on its own. That is why disabling CSRF in Spring Security is fine for a
pure bearer-token API and dangerous for a cookie-session app.

**Why it's a trap:** "We use JWT, so CSRF doesn't apply" is wrong the moment the JWT is stored in a cookie.

### Spring Security

#### Q8. How does the Spring Security filter chain process a request? {#spring-security-filter-chain-process}
**Answer:** A servlet filter, `DelegatingFilterProxy`, hands the request to `FilterChainProxy`, which picks the first
`SecurityFilterChain` whose matcher fits the request (you can define several, for example one for `/api/**` with
bearer tokens and one for `/admin/**` with form login). That chain runs an ordered list of filters: CORS, CSRF,
authentication filters (`BearerTokenAuthenticationFilter`, `UsernamePasswordAuthenticationFilter`), which build an
`Authentication` and store it in the `SecurityContextHolder`; then `ExceptionTranslationFilter`, which turns
`AuthenticationException` into 401 and `AccessDeniedException` into 403; and finally `AuthorizationFilter`, which
applies the URL rules. Method security (`@PreAuthorize`) runs later, through an AOP proxy around your beans.

**Example:**

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
        .csrf(c -> c.disable())              // bearer-token API only, see Q7
        .build();
}
```

#### Q9. How do you configure a Spring Boot API as an OAuth2 resource server? {#configure-spring-boot-api-oauth2}
**Answer:** Add `spring-boot-starter-oauth2-resource-server` and set the issuer:
`spring.security.oauth2.resourceserver.jwt.issuer-uri`. Spring fetches the issuer's discovery document and JWKS (public
keys), verifies the signature, `exp`/`nbf` and `iss` on every request, and caches the keys (it refetches when it
sees an unknown `kid`, which handles key rotation). You still need to add **audience validation** (the token must be
meant for this API) and map claims to authorities: by default scopes become `SCOPE_x`; roles in a custom claim (for
example Keycloak's `realm_access.roles`) need a `JwtAuthenticationConverter`.

**Example:**

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

## 🟡 Senior traps

### Questions

#### Q10. What exactly must you validate on a JWT before trusting it? {#exactly-validate-jwt-before-trusting}
**Answer:** **Signature** with a key from the issuer's JWKS, using an **allowlist of algorithms** chosen by the server
(never trust the token's own `alg` header: `alg: none` and RS256→HS256 confusion attacks exploit that). **`iss`**
equals the expected issuer. **`aud`** contains this API. **`exp`** and **`nbf`** with a small clock skew. Then the
**scopes/roles** for the operation. Also remember that a JWT is **signed, not encrypted**: anyone can base64-decode it,
so never put secrets or sensitive personal data in claims.

**Why it's a trap:** Many hand-written filters only decode the token and read `sub`, or verify the signature but skip
`aud`, which lets a token issued for another API in the same realm call yours.

#### Q11. How do you revoke a JWT, and how do refresh tokens fit in? {#revoke-jwt-refresh-tokens-fit}
**Answer:** A self-contained JWT stays valid until `exp`; the API doesn't ask anyone. Options, by cost: keep access
tokens **short-lived** (5–15 minutes) and accept that window; use **refresh tokens** (longer-lived, stored safely,
**rotated** on every use with reuse detection, revocable at the identity provider) to get new access tokens; for
immediate revocation, keep a **denylist** of token ids (`jti`) or a per-user "tokens issued before" timestamp in a
fast store, checked on each request; or use **opaque tokens with introspection**, which makes every request call the
identity provider (or a cache). Sessions server-side are the simplest when you need instant logout and have one
backend.

**Why it's a trap:** "Logout" in a SPA that only deletes the token locally leaves a stolen copy usable until expiry.

#### Q12. What is IDOR (broken object-level authorization), and why do scanners miss it? {#idor-broken-object-level-authorization}
**Answer:** Insecure Direct Object Reference: the API checks that the caller is authenticated but not that **this**
object belongs to them. `GET /api/invoices/1043` works for any logged-in user who changes the id. It is the first item
in the OWASP API Security Top 10. Scanners and role checks miss it because the request is well-formed and the user
has the right role; only the business relationship is wrong. Fix it at the data access layer: query by id **and**
owner/tenant (`findByIdAndCustomerId`), or check ownership in a `@PreAuthorize` expression or a domain service,
and return 404 rather than 403 to avoid confirming the id exists. Random UUIDs make ids harder to guess but are not
authorization.

**Example:**

```java
// ⛔ any authenticated user can read any invoice
return invoiceRepo.findById(id).orElseThrow(NotFoundException::new);
// ✅ scoped to the caller
return invoiceRepo.findByIdAndCustomerId(id, currentUser.customerId()).orElseThrow(NotFoundException::new);
```

**Why it's a trap:** endpoint-level `hasRole("CUSTOMER")` looks complete in review; the vulnerability is in the query.

#### Q13. What is SSRF, and how do you prevent it? {#ssrf-prevent}
**Answer:** Server-side request forgery: the server fetches a URL the attacker controls (a webhook URL, an "import from
URL" feature, an image proxy, a PDF renderer), and the attacker points it at internal targets: the cloud metadata
endpoint `169.254.169.254` (which can leak IAM credentials), internal admin services, or `localhost`. Defences:
**allowlist** destinations where possible; otherwise resolve the host and **block private, loopback, link-local and
metadata ranges** after DNS resolution (and re-check on redirects, since DNS rebinding and redirects bypass a check on
the hostname string); disable redirects or limit them; run fetchers in an isolated network segment with no route to
internal services; and on AWS enforce **IMDSv2**, which requires a token that a simple SSRF GET can't obtain.

**Why it's a trap:** validating that the URL "starts with https://" or isn't literally `localhost` is bypassed by
`https://127.0.0.1.nip.io`, decimal IPs or an open redirect.

#### Q14. Where should a browser app store tokens, and what is a BFF? {#browser-app-store-tokens-bff}
**Answer:** The trade-offs between `localStorage`, memory and cookies are covered in [Full Stack Q13](fullstack-devops-k8s.md#jwt-localstorage-jwt-httponly-cookie).
The senior answer for a sensitive app is the **Backend for Frontend (BFF)** pattern: a small server-side component
(Spring Cloud Gateway with `TokenRelay`, or a dedicated service) acts as the confidential OAuth client. It performs the
code flow, keeps access and refresh tokens server-side, and gives the browser only an **`HttpOnly`, `Secure`,
`SameSite` session cookie**. The browser never sees a token, so XSS can't steal one (it can still act as the user
while the page is open). In exchange you need CSRF protection on the BFF and a stateful component to run.

**Why it's a trap:** "We use PKCE, so tokens in the SPA are safe" mixes two problems: PKCE protects the code exchange,
not tokens sitting in JavaScript-readable storage.

#### Q15. What is software supply-chain security in practice for a Java/Node project? {#software-supply-chain-security-practice}
**Answer:** Your build pulls hundreds of transitive dependencies, base images and CI actions, each of which can be
vulnerable or malicious. Practices: **pin versions** with lockfiles (`package-lock.json`, Gradle dependency locking)
and pin CI actions and base images by digest; **scan** dependencies and images (OWASP Dependency-Check, Trivy, Snyk,
Dependabot/Renovate for updates) and fail builds on critical vulnerabilities that are actually reachable; generate an
**SBOM** (CycloneDX) per build so you can answer "are we affected by CVE-X?" in minutes; **sign** artifacts and images
(Sigstore/cosign) and verify signatures at deploy; use a private registry proxy; watch for **typosquatting and
dependency confusion** (an internal package name published publicly with a higher version); and run `npm ci` with
`--ignore-scripts` where install scripts aren't needed.

**Example:**

```text
Log4Shell day: "which services ship log4j-core < 2.17.1?"
With SBOMs in an index: one query, 15 minutes.
Without: grep every repo, rebuild to inspect fat jars, two days.
```

**Why it's a trap:** scanning only direct dependencies misses most of the tree; Log4Shell mostly arrived transitively.

## 🔴 Expert / Open

### Questions

#### Q16. How do you propagate user identity across microservices? {#propagate-user-identity-across-microservices}
**Answer:** Options: **forward the user's access token** (simple, each service validates it and sees the real user, but
the token's audience must include every service, and a compromised service can replay it elsewhere); **token
exchange** (RFC 8693: the gateway or service trades the user token for a new, narrowly scoped token for the
downstream service, keeping the user as subject and the caller as actor); or **service identity only** (client
credentials or mTLS) with the user id passed as a trusted header, which is safe only if the network guarantees the
header can't be set by anyone else. For service-to-service authentication, a service mesh with **mTLS** (Istio,
Linkerd) or SPIFFE identities removes shared secrets. Whatever you choose, authorization on user data still happens in
the service that owns it.

#### Q17. How would you run a threat-modeling session for a new feature? {#run-threat-modeling-session-new}
**Answer:** Keep it lightweight and early, in the design review. Draw a **data-flow diagram**: actors, processes,
data stores, flows, and **trust boundaries** (browser↔API, API↔third party, tenant↔tenant). Walk each flow with
**STRIDE**: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege. For
each credible threat write the mitigation, an owner and a test, and rank by likelihood × impact. Output: a short list
of security requirements in the tickets, not a 40-page document. A tech lead's role is to make this a habit (a
template in the design-doc, 30 minutes per significant feature) and to bring in the security team for high-risk areas
like payments, auth and file processing.

**Example:**

```text
Feature: "upload invoice PDF"
S  — upload as another tenant?            → tenant from token, never from form field
T  — PDF replaced after virus scan?       → store by content hash, immutable bucket
I  — public bucket URL guessable?         → private bucket, short-lived signed URLs
D  — 2 GB upload?                         → size limit at gateway + streaming
E  — malicious PDF exploits the renderer? → render in a sandboxed worker without network
```

#### Q18. How do you protect sensitive data at rest and in logs, and where does encryption actually help? {#protect-sensitive-data-rest-logs}
**Answer:** Start by **minimizing**: don't collect or keep what you don't need, and set retention. Encryption **at
rest** (disk, RDS, S3 with KMS) protects against stolen disks and snapshots, not against an attacker who goes through
your application, because the app decrypts transparently. For high-value fields (national ids, IBANs, health data),
add **application-level or column encryption** with keys in a KMS and **envelope encryption** (a data key per
record or tenant, wrapped by a master key), so a database dump alone is useless and keys can be rotated. Use
**tokenization** when other systems need a reference but not the value. Use **hashing** (HMAC with a secret key) when
you only need equality lookups. Keep personal data out of logs with structured logging and masking, and make access to
data auditable. Encryption in transit (TLS everywhere, including inside the cluster) is the baseline.

#### Q19. How do you design the protection of sensitive healthcare data (authentication, access, audit, encryption, retention)? {#design-protection-sensitive-healthcare-data}
**Answer:** Health data is a special category under GDPR (and in France must be hosted by a certified HDS provider), so you
design with **least privilege, traceability and minimisation** from the start, in layers. (1) **Authentication**: strong
authentication for practitioners (MFA, and national schemes such as Pro Santé Connect where applicable), OIDC with short-lived
access tokens (see [Security Q9](security.md#configure-spring-boot-api-oauth2), [Security Q10](security.md#exactly-validate-jwt-before-trusting)), session timeouts and device checks. (2)
**Authorization**: deny by default, role- and **relationship-based** checks ("this practitioner treats this patient"), object-level
checks on every endpoint to avoid IDOR (see [Security Q12](security.md#idor-broken-object-level-authorization)), and a **break-glass** path for emergencies that is
loudly logged. (3) **Data minimisation and purpose limitation**: collect and expose only the fields the use case needs;
search indexes and analytics use pseudonymised or aggregated data; separate identity data from clinical data so one leak
does not reveal both. (4) **Audit**: an append-only, tamper-evident log of *who* accessed or changed *which* patient record,
*when*, *why* and from where, including reads; kept separately, reviewed, and alertable (unusual volume, off-hours,
"VIP" records). Never put health data in application logs or traces (mask identifiers). (5) **Encryption**: TLS 1.2+ everywhere
including internal hops, encryption at rest (disk and database), **field-level / envelope encryption** for the most sensitive
columns with keys in a KMS/HSM, per-tenant keys where required, key rotation and strict key-access policies (see
[Security Q18](security.md#protect-sensitive-data-rest-logs)). (6) **Secrets**: no secrets in code or images; a vault or cloud secret manager with rotation and
short-lived database credentials. (7) **Retention and rights**: defined retention periods per data class, automated deletion
or archival, support for access/rectification/erasure requests (erasure vs the legal duty to keep medical records is a
business/legal decision to surface), consent records, and backups that respect the same rules. (8) **Environment hygiene**:
no production data in dev/test (synthetic or anonymised data only), network segmentation, dependency and image scanning,
penetration tests, an incident-response and breach-notification process (72-hour GDPR notification).

**Example:**

```java
@PreAuthorize("hasRole('PRACTITIONER') and @careTeam.isInCareTeam(authentication.name, #patientId)")
public PatientRecord read(UUID patientId) {
    PatientRecord r = records.findById(patientId).orElseThrow();
    audit.log(AuditEvent.read(currentUser(), patientId, request.purpose(), request.ip())); // append-only store
    return r;
}
```

```sql
-- Field-level protection: the application encrypts with a KMS data key; the column only holds ciphertext.
ALTER TABLE patient ADD COLUMN national_id_enc bytea, ADD COLUMN national_id_hmac bytea; -- hmac = blind index for equality lookup
-- Row security as a second line of defence:
ALTER TABLE medical_note ENABLE ROW LEVEL SECURITY;
CREATE POLICY care_team ON medical_note USING (patient_id IN (SELECT patient_id FROM care_team WHERE user_id = current_setting('app.user_id')::uuid));
```

**Why it's a trap:** treating compliance as "turn on encryption" misses the usual real leaks: over-broad authorization,
health data in logs and analytics exports, copies in non-production environments, and no audit trail to prove who looked at a
record. Mention that legal specifics (HDS, consent, retention periods) must be confirmed with the DPO/legal team rather than assumed.

#### Q20. How does end-to-end encryption of patient–practitioner messages and documents work, and what does it cost the product? {#end-end-encryption-patientpractitioner-messages}
**Answer:** With encryption **at rest**, the server holds the keys (through KMS) and can decrypt. With **end-to-end** encryption, only the participants can. Each user has a key pair generated on their device; the private key never leaves the device unencrypted (it can be backed up wrapped by a user secret or recovery key). Each document or conversation gets a random symmetric key (AES-256-GCM) that encrypts the content. That key is then **wrapped** with each recipient's public key, and the server stores only ciphertext and wrapped keys. Costs to state: no server-side search, preview, antivirus scan or analytics on the content; **key recovery** when a device is lost (recovery codes, multi-device key sync); adding a new practitioner to a case means re-wrapping keys from an existing participant's device; support cannot see what went wrong. It is a product decision as much as a security one: apply it to the most sensitive data, and use KMS-based encryption plus strict access control and audit ([Q19](security.md#design-protection-sensitive-healthcare-data)) for the rest.

**Example:**

```java
// Encrypt once, wrap the content key for each recipient. The server only stores the output.
record Sealed(byte[] iv, byte[] ciphertext, List<byte[]> wrappedKeys) {}

static Sealed seal(byte[] content, List<PublicKey> recipients) throws GeneralSecurityException {
    KeyGenerator keyGen = KeyGenerator.getInstance("AES");
    keyGen.init(256);
    SecretKey contentKey = keyGen.generateKey();
    byte[] iv = new byte[12];
    new SecureRandom().nextBytes(iv);
    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE, contentKey, new GCMParameterSpec(128, iv));
    List<byte[]> wrapped = new ArrayList<>();
    for (PublicKey pk : recipients) {
        Cipher rsa = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        rsa.init(Cipher.WRAP_MODE, pk);
        wrapped.add(rsa.wrap(contentKey));
    }
    return new Sealed(iv, cipher.doFinal(content), wrapped);
}
```

**Why it's a trap:** calling TLS plus disk encryption "end-to-end". If the server can decrypt, it is not end-to-end. The opposite trap is proposing E2E for everything without saying what the product loses.

## 🎯 Real-world scenarios

### S1. A customer reports they can see another customer's invoices by changing the URL {#customer-reports-see-another-customer}
- **Symptoms:** Support forwards a screenshot: `/invoices/18342` shows another company's invoice. Penetration tests last
  year passed.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classic IDOR. Confirm on the endpoint: it checks authentication and role but loads the invoice by id
  only. Then search for the same pattern everywhere: every `findById` reachable from a controller with a path id.
  Check access logs for enumeration (one user requesting many sequential ids) to scope the exposure.
- **Example:**

  ```text
  grep -rn "findById(id)" src/main/java/**/web
  access log: user 7731 requested /invoices/18000..18450 in 4 minutes
  ```

- **Resolution:** Hotfix the endpoint to query by id and tenant (return 404 otherwise), deploy, then fix every other
  occurrence. Treat it as a data breach: involve security and the DPO, determine which records were accessed, and notify
  as required by GDPR (72 hours to the authority).
- **Prevention:** Enforce tenant scoping centrally (Hibernate filter or PostgreSQL row-level security keyed on a
  session variable), add an authorization test per endpoint ("user A can't read B's resource"), and add BOLA checks to
  the review checklist.

</details>

### S2. A JWT signing key appears in a public GitHub repository {#jwt-signing-key-appears-public}
- **Symptoms:** GitHub secret scanning (or an external researcher) reports that the HS256 secret used to sign tokens was
  committed six months ago in a test config.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** With that key, anyone can mint valid tokens for any user and role. Assume compromise. Check whether
  the same key is used in production, how long it was public, and search logs for tokens with unusual claims, issuers
  or subjects that never logged in.
- **Example:**

  ```bash
  git log -S "jwt.secret" --all
  logs: tokens with sub=admin issued outside the auth service (no matching login event)
  ```

- **Resolution:** **Rotate the key immediately** (all existing tokens become invalid, users log in again), remove it from
  history (BFG/`git filter-repo`) knowing the leak itself is already permanent, and audit actions taken with suspicious
  tokens.
- **Prevention:** Move to **asymmetric signing** (RS256/ES256) by an identity provider, so APIs only hold public keys;
  keep secrets in a vault; enable push protection for secrets; plan key rotation with `kid` so it is routine rather than
  an emergency.

</details>

### S3. A security scan flags a critical CVE in a transitive dependency on a Friday afternoon {#security-scan-flags-critical-cve}
- **Symptoms:** The pipeline now fails on a CVSS 9.8 in a library none of your code imports directly; a release is
  planned for Monday.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Find which path pulls it in and whether the vulnerable code is **reachable** in your usage (the
  advisory names the affected class or feature). Check whether it is exploited in the wild (CISA KEV, EPSS score). Check
  which services ship it through the SBOM index.
- **Example:**

  ```text
  ./gradlew dependencyInsight --dependency snakeyaml
  snakeyaml:1.33  <- spring-boot-starter:3.0.5
  advisory: RCE when parsing untrusted YAML with the default constructor
  our use: parses only our own application.yml at startup -> not reachable from user input
  ```

- **Resolution:** If reachable or actively exploited: upgrade (or force the version with a constraint/BOM) and ship
  today. If not reachable: record a time-boxed exception with the justification, keep the release, and schedule the
  upgrade.
- **Prevention:** Renovate/Dependabot with grouped weekly updates so the gap stays small, an SBOM per artifact, and a
  written policy for severity, reachability and SLA so Friday decisions aren't improvised.

</details>

### S4. After moving the frontend to a new domain, logged-in users randomly get 403 on every POST {#after-moving-frontend-new-domain}
- **Symptoms:** GET requests work; POST/PUT/DELETE fail with 403 for some users only. The frontend moved from
  `app.example.com` to `example.com/app`, still talking to the same session-cookie API.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** 403 only on state-changing methods points at **CSRF**, not authentication. Check that the CSRF cookie
  is still sent and read: its `Path`/`Domain` was scoped to the old host, so the frontend can't read `XSRF-TOKEN` and
  doesn't send the header. Users with an old cookie still work, which explains "randomly".
- **Example:**

  ```text
  DevTools: POST /api/orders -> 403, no X-XSRF-TOKEN header
  Set-Cookie: XSRF-TOKEN=...; Domain=app.example.com; Path=/
  Spring log: "Invalid CSRF token found for http://example.com/api/orders"
  ```

- **Resolution:** Configure `CookieCsrfTokenRepository` with the right path/domain (and `withHttpOnlyFalse()` so the SPA
  can read it), and make sure the SPA sends the header on every mutating request.
- **Prevention:** An end-to-end smoke test that performs a POST after login on every deploy, and an explicit migration
  checklist for domain changes (cookies, CORS, CSP, redirect URIs at the identity provider).

</details>

### S5. A secret was committed to Git and pushed to the remote {#secret-was-committed-git-pushed}
- **Symptoms:** A scanner or a teammate reports an API key or database password in the history.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Treat it as compromised from the moment it was pushed, even if the commit is removed: clones, forks and CI logs may hold it. Check the provider's audit logs for use of the key.
- **Resolution:** Revoke and rotate the secret first, then deploy the new one from a secret manager. Rewriting history (`git filter-repo`) is secondary cleanup, not the fix. Review audit logs for misuse and document the incident.
- **Prevention:** Pre-commit and CI secret scanning (gitleaks), push protection on the repository, short-lived credentials, and secrets only in a vault or environment.

</details>

### S6. An "import avatar from URL" feature is used to read the cloud instance's credentials {#ssrf-image-url-metadata}
- **Symptoms:** A pentester (or bug-bounty report) shows that submitting `http://169.254.169.254/latest/meta-data/iam/security-credentials/` as an avatar URL returns AWS keys in the error message.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Server-side request forgery: the backend fetches any URL the user provides, including link-local, internal (`10.x`, `localhost:8080/actuator`) and redirect targets, and echoes the response or error.
- **Resolution:** Rotate the exposed role credentials immediately; enforce IMDSv2 (token required, hop limit 1) on all instances; fetch user URLs through an egress proxy with an allowlist of schemes/ports, resolve the host and reject private/link-local IPs after every redirect, cap size and timeout, and never return raw upstream errors.
- **Prevention:** SSRF test cases in the security test suite, IMDSv2 enforced by policy (SCP/Config rule), and network policies so application pods can't reach internal admin endpoints.

</details>

### S7. A fired employee's account is disabled, but they keep using the admin API for another hour {#jwt-valid-after-logout-role-change}
- **Symptoms:** Audit logs show admin calls after the account was disabled in the IdP; the API accepts their JWT because it's still within its 1-hour `exp`.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Stateless JWT validation only checks signature and expiry; nothing consults the IdP on each call, so disabling the user or removing a role has no effect until the token expires. A long-lived refresh token makes it worse.
- **Resolution:** Revoke the user's sessions/refresh tokens in the IdP, then shorten access-token lifetime (5–15 min), rotate refresh tokens and check user status on refresh, and for sensitive scopes use token introspection or a small deny-list (by `jti`/`sub`) checked at the gateway.
- **Prevention:** Offboarding runbook that includes token revocation, a test that disabled users are rejected within the access-token TTL, and step-up auth for admin actions.

</details>

## 🗣️ Reported interview questions

Questions reported from real interviews, grouped by topic. Each has a short model answer: expand it with the detailed questions and scenarios above, and say the answer aloud.

### Tokens & auth

#### R1. Difference and relationship between OAuth 2.0, JWT and OpenID Connect. {#relationship-oauth-2-0-jwt}
**Answer:** **OAuth 2.0** is an authorization framework (delegated access via access tokens). **OpenID Connect** is an identity layer on top of it (adds the ID token and `/userinfo`, i.e. *who the user is*). **JWT** is just a token *format* (signed JSON), used for OIDC ID tokens and often for OAuth access tokens. OAuth ≠ authentication, JWT ≠ protocol.

#### R2. Explain JWT structure and the JWT authentication/validation flow. {#jwt-structure-jwt-authentication-validation}
**Answer:** `header.payload.signature`, base64url-encoded: header (`alg`, `kid`), claims (`sub`, `iss`, `aud`, `exp`, roles), signature.

Flow: user logs in → the auth server issues a short-lived JWT → client sends `Authorization: Bearer` → the resource server verifies the signature (JWKS public key, pin the algorithm), `iss`, `aud`, `exp`/`nbf`, then authorizes from claims.

Use short expiry plus refresh tokens; never put secrets in the payload (it is only signed).

#### R3. How would you debug a 401 Unauthorized error? {#debug-401-unauthorized-error}
**Answer:** 401 = *not authenticated*.

Check the request has the credential (`Authorization` header present, correct scheme), the token is not expired (`exp`, clock skew), signature/`iss`/`aud` match the server config, the right environment/realm/key (JWKS rotation), a proxy or gateway not stripping the header, and the server logs at DEBUG for the exact validation failure.

Decode the JWT (without trusting it) to inspect claims. Distinguish from **403** (authenticated but not allowed).

### Incident response

#### R4. A secret was accidentally committed to GitHub and has already been cloned. What are your next exact steps? {#secret-was-accidentally-committed-github}
**Answer:** 1) **Revoke/rotate the secret immediately** (assume it is compromised; deleting the commit is not enough). 2) Check logs/CloudTrail for misuse since the commit time. 3) Remove it from history (`git filter-repo`/BFG) and force-push, knowing clones and forks still have it. 4) Issue the new secret via a secrets manager, never in the repo. 5) Add prevention: pre-commit/CI secret scanning (gitleaks), GitHub push protection, and a short post-mortem. See also [Full Stack & DevOps](fullstack-devops-k8s.md).

## 🎤 Oral quiz

Ten questions picked across the levels. Answer each **aloud in 2–3 minutes** without looking, structuring it as context → options → decision → trade-offs. Then open the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Below 24/30, redo the weak ones after two weeks. Questions and scenarios are in the sections above.

1. Q3. What are OAuth 2.0 and OpenID Connect, and how do they differ?
2. Q4. Which OAuth2 flow do you use for which client?
3. Q7. What is CSRF, and when do you need CSRF protection?
4. Q8. How does the Spring Security filter chain process a request?
5. Q10. What exactly must you validate on a JWT before trusting it?
6. Q11. How do you revoke a JWT, and how do refresh tokens fit in?
7. Q12. What is IDOR (broken object-level authorization), and why do scanners miss it?
8. Q15. What is software supply-chain security in practice for a Java/Node project?
9. Q19. How do you design the protection of sensitive healthcare data (authentication, access, audit, encryption, retention)?
10. S2. A JWT signing key appears in a public GitHub repository

## 📌 Cheat-sheet

### Identity & tokens

> **Start here:** authentication proves who, authorization decides what; the server checks both on every request.

- **Passwords** — Argon2id/bcrypt/scrypt, salted, adaptive. *Or delegate to an identity provider.*
- **OAuth2 vs OIDC** — OAuth2 = delegated access (access token); OIDC = identity (ID token). *Never send the ID token to the API.*
- **Flows** — SPA/mobile: code + PKCE; server: code; machine: client credentials; devices: device flow. *Implicit and password flows are deprecated.*
- **JWT validation** — signature with allowlisted alg, `iss`, `aud`, `exp`/`nbf`, then scopes. *Signed ≠ encrypted.*
- **Revocation** — short access tokens, rotating refresh tokens, denylist by `jti`, or introspection.
- **BFF** — tokens server-side, `HttpOnly` cookie to the browser. *Needs CSRF protection.*

### Web attacks

> **Start here:** never let data become code — parameterize queries, escape output, check ownership.

- **SQLi** — parameters everywhere; allowlist for column names and `ORDER BY`; MyBatis `#{}` not `${}`.
- **XSS** — React escapes JSX; watch `dangerouslySetInnerHTML`, `javascript:` URLs; strict CSP.
- **CSRF** — matters with cookies; SameSite + token + Origin check. *Bearer-header APIs are not exposed.*
- **IDOR/BOLA** — query by id **and** owner/tenant; return 404. *Role checks don't catch it.*
- **SSRF** — allowlist, block private ranges after DNS, no redirects, IMDSv2.
- **Health data** — least privilege + relationship-based checks, break-glass logged, append-only audit of reads, field-level encryption with KMS keys, no health data in logs, no production data in dev. *GDPR special category; HDS hosting in France; 72 h breach notice.*

### Spring Security

> **Start here:** `FilterChainProxy` → matching `SecurityFilterChain` → authentication filters → exception translation → authorization.

- **Resource server** — `issuer-uri`, JWKS caching, add an `aud` validator, map roles with `JwtAuthenticationConverter`.
- **401 vs 403** — not authenticated vs authenticated but not allowed (`ExceptionTranslationFilter`).
- **Method security** — `@PreAuthorize` for ownership and fine-grained rules; see [Spring Q41](spring-architecture.md#authorization-live-url-rules-method).

### Platform & process

> **Start here:** know what you ship, keep secrets out of code, and design threats out early.

- **Supply chain** — lockfiles, pinned digests, scanning, SBOM (CycloneDX), signing (cosign). *Watch transitive deps and dependency confusion.*
- **Service identity** — token forwarding vs token exchange vs mTLS/SPIFFE.
- **Data protection** — minimize, encrypt at rest, envelope encryption for sensitive fields, mask logs.
- **Threat modeling** — data-flow diagram + trust boundaries + STRIDE; output = tickets with owners.
