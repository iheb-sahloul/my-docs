# AI Prompts for Senior Engineers

Copy-paste prompts that get production-grade results from a coding assistant (Claude Code, Copilot Chat, etc.). Replace `<...>` with your own context.

## 🧱 Anatomy of a good prompt

### State context, task, constraints, output and done-criteria

Tell the model what it cannot guess: the stack, the goal, the boundaries, the expected format, and how you will judge success.

**Why it's a best practice:** the model fills every gap with the statistically most common answer, not your answer. A senior engineer's edge is knowing the constraints (versions, conventions, SLAs); put them in the prompt and the output needs far less rework.

```text
// ⛔ vague
Add caching to the user service.

// ✅ specific
Context: Spring Boot 3.3, Java 21, Postgres, Redis already configured (see CacheConfig.java).
Task: cache UserService.findById.
Constraints: Spring Cache abstraction only, TTL 5 min, evict on update/delete, no new dependencies.
Output: a diff + a test proving eviction works.
Done when: `./mvnw -q test -Dtest=UserServiceCacheTest` passes.
```

### Ask for a plan before code

For anything touching more than one file, ask for a plan and review it first.

**Why it's a best practice:** a wrong plan costs one minute to fix; a wrong 600-line diff costs an hour. Reviewing the approach is the cheapest checkpoint you have.

```text
// ⛔
Migrate our auth to OAuth2.

// ✅
Do not write code yet. Read the security package and propose a migration plan to OAuth2 resource server:
files to change, order of steps, risks, what can be rolled back independently. Ask me questions if anything is ambiguous.
```

## 🔍 Understanding code

### Trace a flow end to end

Ask for a concrete path with file references, not a summary.

**Why it's a best practice:** "explain this module" yields a generic description. A traced flow with `file:line` is verifiable and exposes the real coupling.

```text
// ⛔
Explain the order module.

// ✅
Trace what happens from POST /orders to the row being committed and the event being published.
List each class/method in order with file:line, where the transaction starts/ends, and any place an exception
could leave data inconsistent.
```

### Map before you change

Ask for blast radius before editing shared code.

**Why it's a best practice:** most regressions come from callers you did not know existed.

```text
Before I change the signature of PricingService.compute(), list every caller (including reflection, tests, and
config), what each passes, and which would break. Do not edit anything.
```

## 🏛️ Design & architecture

### Ask for trade-offs, then a recommendation

Request options with costs, and force a decision.

**Why it's a best practice:** a single answer hides the alternatives; an unranked list pushes the decision back to you. Constraints make the recommendation relevant.

```text
We need to send invoices asynchronously. Compare RabbitMQ, Kafka and a Postgres outbox for our case:
~50 msg/s, at-least-once is fine, 3-person team, already run Postgres only.
Table: ops cost, ordering, replay, failure modes. Then recommend one in 3 sentences and write the ADR
(context, decision, consequences).
```

### Make it challenge you

Ask for the strongest objections to your design.

**Why it's a best practice:** models are agreeable by default; explicit adversarial framing surfaces the flaws a reviewer would find later.

```text
Here is my design <paste>. Act as a skeptical staff engineer. List the 5 most likely ways this fails in production
(scale, consistency, operability, security), ranked by likelihood x impact, and what you would change.
```

## 🛠️ Implementation

### Point at an existing example to match

Reference a file that already follows your conventions.

**Why it's a best practice:** "follow the codebase style" is unmeasurable; "mirror `OrderController`" is concrete, and keeps the model from inventing new patterns or dependencies.

```text
// ⛔
Write a controller for invoices.

// ✅
Add InvoiceController mirroring OrderController (error handling, DTO mapping, validation, @PreAuthorize).
Reuse ApiError and the existing MapStruct mappers. No new dependencies. Add a @WebMvcTest like OrderControllerTest.
```

### Drive it with tests

Give the failing test first, then ask for the minimal implementation.

**Why it's a best practice:** the test is an executable spec; the model can iterate until it is green instead of guessing.

```text
Write failing tests for: a discount never exceeds 30%, stacking coupons is rejected, expired coupons are ignored.
Run them, confirm they fail for the right reason. Then implement the minimum to pass and run the whole module.
```

## 🐞 Debugging

### Give evidence, ask for hypotheses, then a root cause

Paste the stack trace, repro steps, recent change and what you already ruled out.

**Why it's a best practice:** with only the symptom the model patches the symptom. Evidence plus a request for ranked hypotheses yields a fix at the cause.

```text
// ⛔
My app throws NPE, fix it.

// ✅
Stack trace: <paste>. Happens only under load, started after commit <sha> (added async enrichment).
Already ruled out: null DB rows. Give 3 ranked hypotheses with how to confirm each (log, test, breakpoint).
After I confirm one, fix the root cause, not just the null check, and check other callers for the same bug.
```

## 🔎 Code review & refactoring

### Review with a scope and a format

Limit what to look for and how to report.

**Why it's a best practice:** "review this" returns style nits. A narrow scope and severity ordering returns the few findings that matter.

```text
Review this diff for correctness, concurrency and security only (no style). Max 7 findings, ordered by severity,
each with file:line, why it is wrong, and a fix. If nothing is wrong, say so.
<diff>...</diff>
```

### Refactor behind a safety net

Require tests to stay green and no behavior change.

**Why it's a best practice:** a refactor without a safety net is a rewrite in disguise.

```text
Refactor OrderService.process() (300 lines) into smaller methods/collaborators. Behavior must not change:
first add characterization tests around current behavior, run them, then refactor in small steps, running tests
after each. No public API changes.
```

## 🧪 Testing

### Ask for edge cases, not just the happy path

List the categories you want covered.

**Why it's a best practice:** the model's default tests mirror the implementation; naming categories pushes it to the boundaries where bugs live.

```text
For parseAmount(String): write JUnit 5 parameterized tests covering null/blank, locale separators, negative,
overflow, rounding (HALF_EVEN), and unicode digits. Use AssertJ. Explain any behavior you had to assume.
```

### Diagnose flaky tests

Give the failure logs and how often it fails.

```text
This test fails ~1 in 15 CI runs: <paste test + failure log>. List possible causes (shared state, time, ordering,
async), which evidence distinguishes them, then propose the fix that removes the cause rather than adding retries.
```

**Why it's a best practice:** retries hide the nondeterminism; a named cause removes it.

## 🗄️ SQL, JPA & performance

### Bring the query plan

Paste the `EXPLAIN (ANALYZE, BUFFERS)` and the table sizes.

**Why it's a best practice:** performance advice without data is folklore. The plan shows the real bottleneck.

```text
Postgres 16. Query and plan below, orders has 40M rows. Explain where the time goes, suggest indexes
(with the exact DDL and write-cost trade-off), and any rewrite. Do not suggest changes that alter results.
<query> <EXPLAIN ANALYZE output>
```

### Hunt N+1 and lazy-loading issues

```text
Here is the JPA entity graph and the service method. Identify N+1 selects and lazy-loading outside a transaction.
Propose a fix (fetch join, @EntityGraph, or DTO projection) with the trade-offs, and a test using
Hibernate statistics to assert the query count.
```

**Why it's a best practice:** asking for a query-count assertion makes the fix provable and prevents regression.

## 🐳 DevOps & CI

### Review infrastructure against a checklist

```text
Review this Dockerfile and k8s Deployment for production: non-root user, pinned base image digest, layer caching,
resource requests/limits, liveness/readiness probes, graceful shutdown, secrets handling.
Give a table (issue, risk, fix) and then the corrected files.
```

**Why it's a best practice:** an explicit checklist stops the model from stopping at the first two obvious issues.

## 📝 Docs & communication

### Generate from the diff, in your team's format

```text
Write the PR description from this diff: what and why (2-3 sentences), risks, how to test, rollout/rollback plan.
Then draft the runbook entry for the new alert (symptom, dashboard, first 3 checks, escalation).
```

**Why it's a best practice:** the model is good at transforming facts you already have into the format your team wants; you still own the facts.

## ⚠️ Anti-patterns

- **Pasting secrets, tokens or customer data.** Redact; treat prompts as leaving your machine.
- **Accepting code you do not understand.** Ask "explain why this is correct and what could break"; you own what you merge.
- **No verification step.** Always end with "run the tests/linter and show the output".
- **One giant prompt for a big feature.** Split: plan, then slice by slice, reviewing each diff.
- **Correcting by repetition.** If the third attempt fails, restate the context or start a fresh session instead of arguing.
- **Asking for facts you can't check** (library versions, APIs). Point it at the docs or the source in your repo.
