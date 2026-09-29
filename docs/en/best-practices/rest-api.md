# REST API Best Practices



## 🏷️ Resources & naming

### Name resources with plural nouns
Model URLs as collections of things (`/orders`, `/orders/42/items`), not actions.

**Why it's a best practice:** the HTTP method already says the action, so `/getOrders` and `/createOrder` say it
twice and every team invents a different verb (`fetch`, `list`, `retrieve`). Nouns give a predictable shape:
once a client knows `/orders`, they can guess `/orders/{id}`. Use lowercase and hyphens (`/purchase-orders`), and
keep nesting to two levels.

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

### Use HTTP methods for their meaning
`GET` reads, `POST` creates, `PUT` replaces, `PATCH` partially updates, `DELETE` removes.

**Why it's a best practice:** proxies, browsers and caches rely on these semantics. A `GET` that changes data
gets triggered by link previews, crawlers and prefetching, which have deleted real records. `GET`, `PUT` and
`DELETE` are idempotent, so clients and gateways may safely retry them after a timeout; `POST` is not.

```java
// ⛔ side effect on GET
@GetMapping("/orders/{id}/cancel")
void cancel(@PathVariable long id) { ... }

// ✅
@PostMapping("/orders/{id}/cancellation")
ResponseEntity<Void> cancel(@PathVariable long id) { ... }
```

### Model actions as sub-resources when CRUD isn't enough
For real business actions, create a noun for the result (`/orders/42/cancellation`, `/payments`) instead of RPC verbs in the path.

**Why it's a best practice:** it keeps the uniform interface, and the new resource can be read back, listed, and
audited later. It also gives the action a natural place to hold its own data (reason, date).

```text
// ⛔
POST /orders/42/doCancel?reason=late

// ✅
POST /orders/42/cancellations   { "reason": "late" }
```

## 📟 Status codes & errors

### Return accurate status codes
Use 200/201/204 for success, 4xx when the client is wrong, 5xx when the server is. Never return 200 with an error body.

**Why it's a best practice:** monitoring, retries, circuit breakers and client libraries all branch on the
status. A `200 {"error": "not found"}` is counted as success in dashboards, cached by CDNs, and never triggers
the client's error handling. A 500 for validation errors pages the on-call for nothing.

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

### Know the 400 / 401 / 403 / 404 / 409 / 422 difference
401 means "not authenticated", 403 "authenticated but not allowed", 404 "doesn't exist", 409 "conflicts with current state", 422 "well-formed but semantically invalid".

**Why it's a best practice:** clients act differently on each: 401 triggers a token refresh, 403 shows "no
access", 409 asks the user to reload and retry. Using 400 for everything forces clients to parse messages.
(Return 404 instead of 403 when even the existence of the resource is sensitive.)

```text
// ✅
POST /users  {email already used}          -> 409 Conflict
POST /users  {"email": "not-an-email"}     -> 400 Bad Request
GET  /orders/9 (someone else's order)      -> 404 Not Found
```

### Return errors as RFC 9457 Problem Details
Use one error format everywhere: `application/problem+json` with `type`, `title`, `status`, `detail`, plus your own fields.

**Why it's a best practice:** when each endpoint invents its own error JSON, every client writes special-case
parsing. RFC 9457 (which replaced RFC 7807) is a standard, and Spring Boot 3 supports `ProblemDetail` natively.
A stable `type` URI lets clients switch on the error without parsing text.

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

### Report all validation errors at once
Return every invalid field in one response, not the first one found.

**Why it's a best practice:** if a form has 5 problems and the API reports one per call, the user needs 5
round trips. A list of field errors lets the UI highlight all of them.

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

### Always paginate collections
Every list endpoint takes `page`/`size` or a cursor, with a default and a maximum size.

**Why it's a best practice:** `GET /orders` works with 100 rows in dev and returns 4 million in production: out
of memory on the server, a timeout at the client, and a full table scan on the database. A hard maximum
(say 100) also protects you from `?size=1000000`.

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

### Prefer cursor pagination for large or changing data
Use a cursor (`?after=<last id>`) rather than `OFFSET` for feeds and big tables.

**Why it's a best practice:** `OFFSET 1000000` makes the database read and discard a million rows, so page
10,000 is slow. Rows inserted while a user pages cause duplicates or skipped items. A keyset condition
(`WHERE id < :last ORDER BY id DESC LIMIT 20`) uses the index and stays fast at any depth.

```sql
-- ⛔
SELECT * FROM orders ORDER BY id DESC LIMIT 20 OFFSET 1000000;

-- ✅
SELECT * FROM orders WHERE id < :lastId ORDER BY id DESC LIMIT 20;
```

### Support filtering and sorting with a whitelist
Accept `?status=PAID&sort=createdAt,desc` on known fields only.

**Why it's a best practice:** passing the `sort` value straight to the query allows sorting on unindexed or
sensitive columns (`sort=passwordHash`), and unknown values cause 500s. A whitelist keeps queries on indexed
columns and the API contract explicit.

```java
// ✅
private static final Set<String> SORTABLE = Set.of("createdAt", "total");
```

## 🧬 Payloads

### Expose DTOs, not entities
Map entities to request and response records at the API boundary.

**Why it's a best practice:** an entity exposed directly ties your database schema to the public contract:
renaming a column becomes a breaking change. It also leaks internal fields, triggers lazy-loading exceptions
during serialization, and allows mass assignment. Separate request and response types let each evolve
independently. Java records make this cheap.

```java
// ⛔
@GetMapping("/{id}") Order get(@PathVariable long id) { return repo.findById(id).orElseThrow(); }

// ✅
record OrderResponse(long id, String status, BigDecimal total, Instant createdAt) {
    static OrderResponse from(Order o) { return new OrderResponse(o.getId(), o.getStatus().name(), o.getTotal(), o.getCreatedAt()); }
}
```

### Use consistent formats for dates, money and enums
Send dates as ISO 8601 UTC (`2026-03-01T10:15:30Z`), money as a decimal string or minor units plus a currency, and enums as stable strings.

**Why it's a best practice:** `03/04/2026` is March or April depending on the reader. A `double` for money gives
`0.1 + 0.2 = 0.30000000000000004`. Numeric enum ordinals silently change meaning when someone inserts a value.
Use `BigDecimal` server-side.

```json
// ⛔
{ "date": "03/04/26", "price": 19.989999, "status": 2 }

// ✅
{ "createdAt": "2026-04-03T09:00:00Z", "price": { "amount": "19.99", "currency": "EUR" }, "status": "SHIPPED" }
```

## 🔄 Reliability & evolution

### Make unsafe operations idempotent with an `Idempotency-Key`
Let clients send a unique key with `POST` and return the stored result on a repeat.

**Why it's a best practice:** networks fail after the server processed the request but before the client saw
the answer. The client retries, and the customer is charged twice. Storing the key (with a unique constraint)
turns retries into safe no-ops. Stripe and most payment APIs work this way.

```java
// ✅
@PostMapping("/payments")
ResponseEntity<PaymentResponse> pay(@RequestHeader("Idempotency-Key") String key,
                                    @Valid @RequestBody PayRequest body) {
    return service.findByKey(key)
        .map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.status(201).body(service.pay(key, body)));
}
// UNIQUE(idempotency_key) makes concurrent duplicates fail instead of both succeeding
```

### Use optimistic concurrency with ETags
Return an `ETag` (or a `version`) and require `If-Match` on updates. Respond 412 or 409 on mismatch.

**Why it's a best practice:** two users edit the same record; the second `PUT` silently overwrites the first
(lost update). A version check detects it. `ETag` with `If-None-Match` also gives cheap conditional `GET`s
returning 304 with no body.

```java
// ✅
@PutMapping("/{id}")
ResponseEntity<ProductResponse> update(@PathVariable long id,
        @RequestHeader("If-Match") String etag, @Valid @RequestBody UpdateProduct body) {
    var saved = service.update(id, Long.parseLong(etag.replace("\"", "")), body); // throws 412 when stale
    return ResponseEntity.ok().eTag("\"" + saved.version() + "\"").body(saved);
}
```

### Version the API and avoid breaking changes
Put a version in the URL (`/v1/`) or header, and only add optional fields within a version.

**Why it's a best practice:** once mobile apps and partners depend on your JSON, renaming or removing a field
breaks clients you can't redeploy. Adding a field is safe; removing or changing a type is not. Publish
deprecations with `Deprecation` and `Sunset` headers and a date so consumers can plan.

```text
// ⛔ rename in place: { "name": ... } becomes { "fullName": ... }

// ✅ additive change in v1; breaking change goes to v2
GET /v1/users/7   -> { "name": "Ann", "displayName": "Ann B." }
GET /v2/users/7   -> { "fullName": "Ann B." }
```

### Validate input and document the contract with OpenAPI
Annotate request types with Bean Validation and generate an OpenAPI spec (springdoc), checked in or published from CI.

**Why it's a best practice:** an undocumented API is learned by trial and error, and hand-written docs drift.
A generated spec powers client generation, contract tests, and a Swagger UI, and a diff on the spec in a pull
request shows breaking changes before release.

```java
// ✅
@Operation(summary = "Create an order")
@ApiResponse(responseCode = "201", description = "Created")
@ApiResponse(responseCode = "400", description = "Validation failed")
@PostMapping
ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrder body) { ... }
```
