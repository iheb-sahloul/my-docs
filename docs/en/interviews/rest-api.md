# REST API Design

Deeper REST design questions: pagination, PUT vs PATCH, errors, caching and rate limiting. The basics (principles, versioning, idempotency keys, OpenAPI) are in [Full Stack & DevOps](fullstack-devops-k8s.md#core-principles-good-rest-api); rules live in [Best practices › REST API](../best-practices/rest-api.md).

## 🟢 Fundamentals

#### Q1. How do you model resources and choose HTTP methods and status codes? {#model-resources-http-methods-status}
**Answer:** Model **nouns**, not actions: `/appointments/42`, with `GET` (read, safe), `POST` (create, not idempotent), `PUT` (replace, idempotent), `PATCH` (partial update), `DELETE` (idempotent). Use precise codes: `201` + `Location` on create, `204` with no body, `400` malformed, `401` unauthenticated, `403` forbidden, `404` missing, `409` conflict, `422` valid syntax but failed validation. An action that does not fit CRUD becomes a sub-resource (`POST /appointments/42/cancellation`).

#### Q2. What is the difference between `PUT` and `PATCH`, and how do you handle concurrent updates? {#put-patch-handle-concurrent-updates}
**Answer:** `PUT` replaces the whole resource (missing fields are reset); `PATCH` changes only the fields sent (JSON Merge Patch, or JSON Patch for operations). Both are lost-update prone: return an `ETag` on `GET`, require `If-Match` on write, and answer `412 Precondition Failed` (or `409`) on mismatch. This is optimistic locking exposed over HTTP.

**Example:**

```http
PUT /appointments/42
If-Match: "v7"

→ 412 Precondition Failed   (someone else saved v8)
```

## 🟡 Senior traps

#### Q3. Offset or keyset (cursor) pagination: how do you choose? {#offset-keyset-cursor-pagination}
**Answer:** `LIMIT/OFFSET` is simple and allows jumping to page N, but cost grows with the offset (the database still reads and discards the skipped rows) and rows shift when data is inserted, causing duplicates or gaps. **Keyset** pagination (`WHERE (created_at, id) < (:last_at, :last_id) ORDER BY created_at DESC, id DESC LIMIT 50`) stays fast on an index and is stable, but cannot jump to arbitrary pages. Return an opaque `nextCursor`, always add a unique tie-breaker column, and cap `limit`.

#### Q4. What error format do you return, and what must never leak? {#error-format-return-never-leak}
**Answer:** Use one consistent format, ideally **RFC 9457 Problem Details** (`application/problem+json`): `type`, `title`, `status`, `detail`, plus fields such as `errors[]` for validation. In Spring Boot 3, enable `ProblemDetail` with a `@RestControllerAdvice`. Never leak stack traces, SQL, class names or whether a user exists; log them server-side with a correlation id returned in the response so support can find the cause.

#### Q5. How do you use HTTP caching and rate limiting on an API? {#http-caching-rate-limiting-api}
**Answer:** Caching: `Cache-Control` (`max-age`, `private` vs `public`), validators `ETag`/`Last-Modified` and conditional `GET` returning `304`, and `Vary` for content negotiation. Never cache per-user data in a shared cache. Rate limiting: apply per client key (token bucket at the gateway), answer `429 Too Many Requests` with `Retry-After`, and expose limits in headers; protect expensive endpoints more tightly than cheap ones.

## 🔴 Expert / Open

#### Q6. How do you evolve an API without breaking clients? {#evolve-api-breaking-clients}
**Answer:** Prefer **additive** change: new optional fields, new endpoints, tolerant readers that ignore unknown fields. Never rename, remove or change the meaning of a field in place. When a break is unavoidable, version (path or header), run both versions, announce deprecation with `Deprecation`/`Sunset` headers, and track usage per client before removal. Consumer-driven contract tests catch accidental breaks in CI.

## 🎯 Real-world scenarios

### S1. A list endpoint gets slower every month and sometimes returns duplicate items {#list-endpoint-gets-slower-every}
- **Symptoms:** Page 1 is fast, deep pages take seconds, and clients occasionally see the same item twice across pages.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Offset pagination on a growing table, ordered by a non-unique column. Check `EXPLAIN` for a large sort/skip and the `ORDER BY` columns.
- **Resolution:** Switch to keyset pagination on an indexed `(created_at, id)`, return `nextCursor`, cap the page size, and keep offset only for small admin lists.
- **Prevention:** Review rule: any list endpoint needs a stable total order, a max `limit` and a load test with deep pages.

</details>

### S2. A field rename ships on Friday and the mobile app crashes for every user still on last month's version {#renamed-field-breaks-mobile-app}
- **Symptoms:** Web works (deployed in lockstep), but Android/iOS crash reports spike: `NullPointerException` parsing `customerName`, now `fullName`.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Diff the OpenAPI spec between the two releases (`oasdiff breaking old.yaml new.yaml`). Mobile clients can't be force-upgraded: any removed/renamed field, new required request field, or narrowed enum is a breaking change for weeks.
- **Example:**

  ```text
  error  response-property-removed  GET /customers/{id}  200  'customerName'
  ```

- **Resolution:** Roll forward by re-adding `customerName` (serve both fields), then deprecate it with a `Deprecation`/`Sunset` header and remove only once analytics show old app versions below an agreed threshold.
- **Prevention:** Breaking-change check on the spec in CI (fails the build), consumer-driven contract tests with the mobile team, expand → migrate → contract as the rule for any field change.

</details>

### S3. A mobile client on a flaky network is charged twice for one checkout {#retried-post-double-payment}
- **Symptoms:** Two `payment` rows a few seconds apart, same amount and cart; the access log shows two `POST /payments` from the same device, the first one ending in a client-side timeout.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** The first request succeeded on the server but the response was lost; the client (or a proxy/SDK) retried. `POST` is not idempotent and the server has no way to know it's the same intent.
- **Example:**

  ```http
  POST /payments
  Idempotency-Key: 4f1c2b9e-...

  # server: INSERT INTO idempotency(key, request_hash, response) ... ON CONFLICT (key) DO NOTHING
  # replay with same key  -> return stored response, no new charge
  # same key, other body  -> 422
  ```

- **Resolution:** Refund the duplicate; require an `Idempotency-Key` header on money-moving `POST`s, store key + request hash + response in the same transaction as the payment (unique constraint), replay the stored response on retry, expire keys after 24–48 h.
- **Prevention:** Idempotency keys mandatory in the API guidelines for side-effecting `POST`s, a chaos test that drops responses and retries, and pass the key through to the payment provider (they support it too).

</details>

### S4. Two back-office users edit the same customer and one of them silently loses their changes {#concurrent-edits-silently-overwrite}
- **Symptoms:** A support agent updates the address, a colleague updates the phone number a minute later from a tab opened earlier; the address is back to the old value. No error anywhere.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Classic lost update: the UI sends the full object with `PUT` (or a `PATCH` built from stale state), last write wins. Nothing in the request says which version the client edited.
- **Example:**

  ```http
  GET /customers/42        -> 200, ETag: "v7"
  PATCH /customers/42
  If-Match: "v7"           -> 412 Precondition Failed if someone saved v8 meanwhile
  ```

- **Resolution:** Return an `ETag` (entity version, e.g. JPA `@Version`) on `GET`, require `If-Match` on `PUT`/`PATCH`, answer `412` on mismatch (`428` if missing), and let the UI show a reload/merge dialog. Send only changed fields with `PATCH`.
- **Prevention:** Optimistic locking as the default for editable resources, an integration test with two concurrent updates, and API guidelines that make `If-Match` mandatory on writes.

</details>

### S5. A partner's nightly sync turns into a retry storm that degrades the API for everyone {#partner-retry-storm-429}
- **Symptoms:** At 02:00 traffic jumps 20×, almost all from one API key; most responses are `429`, yet the request rate keeps rising and p99 for other clients triples.

> 🧠 **Try first:** Before opening the answer, write your first three hypotheses and the command or metric you would check for each.

<details markdown="1">
<summary>Show diagnosis, resolution & prevention</summary>

- **Diagnosis:** Rate limiting works, but the partner's client retries every `429` immediately and in parallel. The limiter itself (and auth, logging, TLS) still costs CPU on every rejected call, so rejections alone don't protect the service.
- **Example:**

  ```http
  HTTP/1.1 429 Too Many Requests
  Retry-After: 30
  RateLimit-Policy: 100;w=60
  RateLimit: remaining=0, reset=30
  ```

- **Resolution:** Short term: lower that key's quota and block at the gateway/WAF (cheapest layer). Then send `Retry-After` and `RateLimit` headers, and agree with the partner on exponential backoff with jitter, a concurrency cap and a bulk/export endpoint instead of thousands of small calls.
- **Prevention:** Per-client quotas enforced at the edge, a documented retry contract in the API guide, an alert on `429` rate per key, and an SDK that implements backoff correctly.

</details>

## 🎤 Oral quiz

Answer each question **aloud in 2–3 minutes** without looking: context → options → decision → trade-offs. Then re-read the linked question and score yourself: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall.

1. Q1. How do you model resources and choose HTTP methods and status codes?
2. Q2. What is the difference between `PUT` and `PATCH`, and how do you handle concurrent updates?
3. Q3. Offset or keyset (cursor) pagination: how do you choose?
4. Q4. What error format do you return, and what must never leak?
5. Q5. How do you use HTTP caching and rate limiting on an API?
6. Q6. How do you evolve an API without breaking clients?
7. S1. A list endpoint gets slower every month and sometimes returns duplicate items

## 📌 Cheat-sheet

- **Methods** — `GET` safe, `PUT`/`DELETE` idempotent, `POST` neither. *Use `201`+`Location`, `409` conflict, `422` validation.*
- **Concurrency** — `ETag` + `If-Match` → `412`. *Optimistic locking over HTTP.*
- **Pagination** — keyset beats offset on large tables. *Needs a unique tie-breaker and an opaque cursor.*
- **Errors** — RFC 9457 `problem+json` and a correlation id. *Never leak stack traces.*
- **Evolution** — additive changes, tolerant readers, `Sunset` header. *Version only when a break is unavoidable.*
