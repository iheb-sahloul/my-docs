# Security Best Practices

## 🚪 Input & injection

### Validate all input at the boundary

Validate every request body, parameter and header with Bean Validation, and reject bad input with a 400.

**Why it's a best practice:** every value from outside is untrusted. Without limits, a 500 MB string, a
negative quantity or a null id travels deep into the system and fails in unpredictable places, or worse,
succeeds. Validating once at the edge gives one clear rule set. Prefer allow-lists (an enum, a regex) over
deny-lists, which attackers bypass.

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

### Use parameterized queries, never string concatenation

Pass values as bind parameters in JDBC, JPQL, and native queries.

**Why it's a best practice:** SQL injection has been in the OWASP Top 10 for two decades and still causes
full database dumps. With `name = "x' OR '1'='1"`, a concatenated query returns every row; `'; DROP TABLE users;--`
is worse. A bind parameter is sent separately from the SQL text, so the database never treats it as code.

```java
// ⛔
jdbc.query("SELECT * FROM users WHERE name = '" + name + "'", mapper);

// ✅
jdbc.query("SELECT * FROM users WHERE name = ?", mapper, name);

// ✅ Spring Data
@Query("select u from User u where u.name = :name")
List<User> findByName(@Param("name") String name);
```

### Escape output and set a Content Security Policy

Encode data for the context it's rendered in (HTML, JS, URL), and send security headers.

**Why it's a best practice:** stored XSS lets one user's comment run JavaScript in every viewer's browser and
steal sessions. Template engines like Thymeleaf escape by default (`th:text`); raw output (`th:utext`,
`innerHTML`) turns it off. A CSP limits the damage if you miss one place. Spring Security adds several
headers by default.

```java
// ⛔
<div th:utext="${comment}"></div>

// ✅
<div th:text="${comment}"></div>

// ✅
http.headers(h -> h.contentSecurityPolicy(c -> c.policyDirectives("default-src 'self'")));
```

### Prevent path traversal and SSRF

Never build file paths or outgoing URLs directly from user input. Normalize and check against an allow-list.

**Why it's a best practice:** `../../etc/passwd` in a filename reads any file the process can access. An
attacker who controls a URL your server fetches can reach `http://169.254.169.254/` (cloud metadata) and steal
instance credentials, as in the 2019 Capital One breach.

```java
// ⛔
Path file = Path.of("/data/uploads", filename);

// ✅
Path base = Path.of("/data/uploads").toRealPath();
Path file = base.resolve(filename).normalize();
if (!file.startsWith(base)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST);
```

## 🔑 Authentication & secrets

### Hash passwords with a slow adaptive algorithm

Use `BCryptPasswordEncoder`, Argon2 or `DelegatingPasswordEncoder`. Never store plain text, MD5 or plain SHA.

**Why it's a best practice:** a GPU computes billions of SHA-256 hashes per second, so a leaked unsalted table is
cracked in hours. BCrypt is salted and deliberately slow (about 100 ms per hash at cost 10 to 12), which makes
brute force impractical. `DelegatingPasswordEncoder` stores the algorithm id, so you can upgrade later.

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

### Keep secrets out of code and Git

Load secrets from environment variables, a secret manager (Vault, AWS Secrets Manager, Kubernetes secrets),
and rotate them.

**Why it's a best practice:** bots scan public GitHub commits within minutes and use leaked cloud keys to mine
crypto; private repos leak through forks and CI logs. A secret in Git history stays there after deletion, so the
only fix is to rotate it. Add a scanner (gitleaks) in CI and a pre-commit hook.

```yaml
# ⛔
spring.datasource.password: s3cr3t
# ✅
spring.datasource.password: ${DB_PASSWORD}
```

### Validate JWTs completely and keep them short-lived

Verify signature, `iss`, `aud` and `exp`. Use short access tokens (5 to 15 min) with refresh tokens. Never accept `alg: none`.

**Why it's a best practice:** a JWT can't be revoked before it expires, so a stolen 30-day token is a 30-day
breach. Skipping the audience check lets a token issued for service A be used on service B. Use Spring's
resource server instead of hand-written parsing.

```java
// ⛔ decoding without verifying
var claims = Jwts.parser().build().parseUnsecuredClaims(token);

// ✅
http.oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()));
// application.yml
// spring.security.oauth2.resourceserver.jwt.issuer-uri: https://auth.example.com
```

### Rate-limit and lock down login endpoints

Throttle authentication attempts, and return the same message for a wrong user and a wrong password.

**Why it's a best practice:** without limits, an attacker tries 10 million leaked passwords against your
login (credential stuffing). Different messages ("no such user" vs "bad password") let them enumerate valid
accounts first. Add MFA for sensitive accounts.

```java
// ⛔
if (user == null) return "User not found";
if (!matches) return "Wrong password";

// ✅
return ResponseEntity.status(401).body(problem("Invalid credentials"));
```

## 🛡️ Web protections

### Configure CORS with an explicit origin list

Allow specific origins, methods and headers. Never combine `*` with credentials.

**Why it's a best practice:** CORS is a browser rule that decides which websites can read your API responses
with the user's cookies. `allowedOrigins("*")` on an authenticated API lets any malicious site do so.
Browsers refuse `*` together with credentials, so people "fix" it by reflecting the `Origin` header, which is
the same hole.

```java
// ⛔
registry.addMapping("/**").allowedOriginPatterns("*").allowCredentials(true);

// ✅
registry.addMapping("/api/**")
    .allowedOrigins("https://app.example.com")
    .allowedMethods("GET", "POST", "PUT", "DELETE")
    .allowCredentials(true);
```

### Keep CSRF protection on for cookie-based sessions

Disable CSRF only for stateless APIs that authenticate with a bearer token in a header.

**Why it's a best practice:** browsers attach cookies automatically, so a hidden form on `evil.com` can submit
`POST /transfer` as the logged-in user. Tokens or `SameSite=Lax/Strict` cookies stop that. Turning CSRF off
"because the POST failed in Postman" removes the protection for the whole app.

```java
// ⛔ session app with protection off
http.csrf(AbstractHttpConfigurer::disable);

// ✅ stateless bearer-token API only
http.csrf(AbstractHttpConfigurer::disable)
    .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
```

### Enforce HTTPS and secure cookies

Redirect to HTTPS, send HSTS, and set `Secure`, `HttpOnly` and `SameSite` on session cookies.

**Why it's a best practice:** on café Wi-Fi, plain HTTP traffic can be read and modified. `HttpOnly` stops
JavaScript from reading the session cookie, so an XSS bug can't steal it. `Secure` keeps it off HTTP requests.

```yaml
# ✅
server.servlet.session.cookie.secure: true
server.servlet.session.cookie.http-only: true
server.servlet.session.cookie.same-site: lax
```

## 🧑‍⚖️ Authorization

### Deny by default and apply least privilege

Require authentication for every route, open specific ones explicitly, and give each account or service only the permissions it needs.

**Why it's a best practice:** "Broken Access Control" is number 1 in the OWASP Top 10 (2021). A forgotten new
endpoint under a permit-all pattern is public on day one. A database user with `DROP` rights turns a small
injection into total loss; an app user that can only `SELECT/INSERT/UPDATE` limits the blast radius.

```java
// ⛔
.authorizeHttpRequests(a -> a.requestMatchers("/api/**").permitAll())

// ✅
.authorizeHttpRequests(a -> a
    .requestMatchers("/actuator/health/**", "/v3/api-docs/**").permitAll()
    .requestMatchers("/api/admin/**").hasRole("ADMIN")
    .anyRequest().authenticated())
```

### Check ownership on every object access

Verify that the caller may access this particular record, not just that they are logged in.

**Why it's a best practice:** IDOR (insecure direct object reference) is the classic bug: user 5 calls
`GET /orders/1234` and gets someone else's order, because the code only checks "is authenticated". Attackers
just iterate through IDs. Enforce it with method security or by querying with the owner.

```java
// ⛔
return orders.findById(id).orElseThrow();

// ✅
@PreAuthorize("@orderAccess.isOwner(#id, authentication)")
@GetMapping("/orders/{id}")
Order get(@PathVariable long id) { ... }

// ✅ or scope the query
orders.findByIdAndCustomerId(id, currentUser.id());
```

## 📦 Supply chain & data exposure

### Scan dependencies and update them regularly

Run OWASP Dependency-Check, Dependabot, Renovate or Trivy in CI, and fail on high-severity CVEs.

**Why it's a best practice:** Log4Shell (CVE-2021-44228) was a remote code execution in a library many teams
didn't even know they had. Most of your running code is third-party. Automated pull requests make upgrades small
and frequent, instead of a painful jump across three major versions during an incident.

```yaml
# ✅ .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: maven
    directory: "/"
    schedule: { interval: weekly }
```

### Never expose entities or internal errors

Return DTOs and generic error bodies. Log the details on the server only.

**Why it's a best practice:** returning a JPA entity leaks columns like `passwordHash` or `isAdmin`, and lets
clients set fields via mass assignment (`{"role":"ADMIN"}`). A stack trace reveals framework versions, table
names and file paths, which help the next attack.

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

### Never log secrets or personal data

Mask tokens, passwords, card numbers and personal data before logging.

**Why:** covered in [Never log secrets or personal data](observability.md#never-log-secrets-or-personal-data).

```java
// ⛔
log.info("Login request: {}", request);   // includes the password

// ✅
log.info("Login attempt for user id={}", userId);
```

### Secure the actuator and other management endpoints

Expose only `health` and `info` publicly, and put the rest behind authentication or a private port.

**Why it's a best practice:** `/actuator/env`, `/heapdump` and `/threaddump` reveal configuration, and a heap dump
contains every secret in memory. Exposed actuators are a common finding in penetration tests.

```yaml
# ⛔
management.endpoints.web.exposure.include: "*"

# ✅
management.endpoints.web.exposure.include: health,info,prometheus
management.server.port: 9090
```
