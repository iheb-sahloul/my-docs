# My Docs

My personal tech doc, to hold notes and references I want to go back to.

# Roadmap — Senior Java / React Engineer → Tech Lead

A detailed map of what to master to become a senior full-stack Java / React engineer and step into
tech lead roles. It covers coding, data, messaging, frontend, DevOps, security, architecture,
system design, leadership and tooling, and links to the deeper pages of this site.

## How to use this roadmap

| Marker | Level          | Meaning                                                                |
|--------|----------------|------------------------------------------------------------------------|
| 🟢     | **Mid → Senior** | Expected from any solid developer. Gaps here block everything else.  |
| 🟡     | **Senior**       | What distinguishes a senior: depth, trade-offs, production experience. |
| 🔴     | **Tech Lead**    | Cross-team scope, architecture, decisions, people.                     |

- **Depth over breadth.** Master one tool per category deeply, know the alternatives by name and trade-offs.
- **Learn → build → explain.** A topic is "done" when you have used it in a real project *and* can explain it to someone else.
- **Tick the checkboxes** in the [self-assessment](#self-assessment-checklist) at the end, and revisit every few months.
- **Production is the best teacher.** Volunteer for on-call, incidents, migrations and performance issues.

## The big picture

| Stage            | Scope                             | Expected impact                                                        | Signals you're ready for the next step                                             |
|------------------|-----------------------------------|------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| 🟢 Mid           | A feature, a component            | Delivers well-defined tasks autonomously with good quality             | Needs little guidance, writes tests by default, debugs independently               |
| 🟡 Senior        | A service, a module, an epic      | Designs and delivers end-to-end, owns production, raises the bar       | Others ask for your review/opinion, you anticipate problems, you unblock people    |
| 🔴 Tech Lead     | A team / a system of services     | Sets technical direction, makes and communicates decisions, grows people | Team delivers better *because of you*, not just *through you*; stakeholders trust your estimates |

> A senior is measured by the quality of what they build. A tech lead is measured by the quality of
> what the **team** builds.

---

## 1. Foundations — CS & principles

### Computer science

| Topic                          | Level | What to know                                                                       |
|--------------------------------|-------|------------------------------------------------------------------------------------|
| Data structures                | 🟢    | Arrays, lists, hash maps, trees (BST, B-tree), heaps, graphs, tries                |
| Algorithms & complexity        | 🟢    | Big-O time/space, sorting, searching, BFS/DFS, two pointers, sliding window, DP basics |
| Networking                     | 🟢    | TCP vs UDP, DNS, HTTP/1.1 vs HTTP/2 vs HTTP/3, TLS handshake, cookies, CORS        |
| Operating systems              | 🟡    | Processes vs threads, context switching, memory (stack/heap, virtual memory), file descriptors, I/O models |
| Distributed systems basics     | 🟡    | Latency numbers, clocks, partial failures, consensus (Raft) at a conceptual level  |

### Engineering principles

| Principle                          | Level | Key idea                                                                  |
|------------------------------------|-------|---------------------------------------------------------------------------|
| SOLID                              | 🟢    | Especially SRP and DIP — they drive testability and modularity           |
| DRY / KISS / YAGNI                 | 🟢    | Duplication is cheaper than the wrong abstraction; don't build for "later" |
| Composition over inheritance       | 🟢    | Favour small collaborating objects over deep hierarchies                  |
| Law of Demeter, Tell-don't-ask     | 🟡    | Reduce coupling, push behaviour to where the data is                      |
| Clean Code & naming                | 🟢    | Code is read far more than written                                        |
| Refactoring                        | 🟡    | Small, safe, test-covered steps; know the catalogue (extract, inline, move…) |
| Design patterns                    | 🟡    | GoF catalogue — and more importantly **when not** to use one              |
| Cohesion & coupling                | 🔴    | The real metric behind every architecture decision                        |
| Fail fast, least privilege, immutability by default | 🟡 | Defensive defaults that prevent whole classes of bugs      |

**Go deeper:** [Design Patterns](interviews/design-patterns.md) · [Java best practices](best-practices/java.md)

**Practice**

- Solve 2–3 algorithm problems a week (LeetCode / Codewars) — focus on explaining complexity out loud.
- Take a legacy class, cover it with tests, then refactor it step by step.

---

## 2. Java backend track

### Language & core APIs

| Topic                        | Level | What to know                                                                                   |
|------------------------------|-------|------------------------------------------------------------------------------------------------|
| Modern Java (17 → 21 → 25)   | 🟢    | Records, sealed types, pattern matching (`switch`, `instanceof`, record patterns), text blocks, `var` |
| Collections                  | 🟢    | `List`/`Set`/`Map` implementations, complexity, `equals`/`hashCode` contract, immutable collections |
| Streams & functional style   | 🟢    | Lambdas, method refs, collectors, `Optional` done right, when a loop is clearer                |
| Generics                     | 🟡    | Bounded types, wildcards (PECS), type erasure                                                  |
| Exceptions                   | 🟢    | Checked vs unchecked, exception translation, never swallow                                     |
| Concurrency                  | 🟡    | Java Memory Model, `happens-before`, `volatile`, locks, `java.util.concurrent`, `CompletableFuture`, thread pools sizing |
| Virtual threads & structured concurrency | 🟡 | Loom model, pinning, when they help (I/O-bound) and when they don't                  |
| JVM internals                | 🟡    | Heap/stack/metaspace, class loading, JIT, GC (G1, ZGC, Shenandoah) and tuning basics          |
| Profiling & diagnostics      | 🔴    | JFR, JDK Mission Control, async-profiler, heap dumps, thread dumps, `jcmd`                     |

### Build & testing

| Topic                         | Level | What to know                                                              |
|-------------------------------|-------|---------------------------------------------------------------------------|
| Maven / Gradle                | 🟢    | Lifecycle, dependency management, BOMs, multi-module builds, plugins      |
| Unit testing                  | 🟢    | JUnit 5, AssertJ, Mockito — test behaviour, not implementation            |
| Integration testing           | 🟡    | Testcontainers, `@SpringBootTest` slices (`@WebMvcTest`, `@DataJpaTest`)  |
| Architecture tests            | 🟡    | ArchUnit rules to enforce layering and dependencies                       |
| Contract testing              | 🔴    | Spring Cloud Contract / Pact between services                             |
| Mutation testing              | 🔴    | PIT to measure the *quality* of tests, not just coverage                  |
| TDD                           | 🟡    | Red → green → refactor; know when it pays off                             |

### Spring ecosystem

| Topic                         | Level | What to know                                                                  |
|-------------------------------|-------|-------------------------------------------------------------------------------|
| Spring Core                   | 🟢    | IoC/DI, bean scopes and lifecycle, configuration, profiles                    |
| Spring Boot                   | 🟢    | Auto-configuration, starters, externalized config, Actuator                   |
| Proxies & AOP                 | 🟡    | JDK vs CGLIB proxies, self-invocation trap                                    |
| `@Transactional`              | 🟡    | Propagation, isolation, rollback rules, where transactions **don't** apply    |
| Spring Data JPA / Hibernate   | 🟡    | Entity lifecycle, N+1, fetch strategies, dirty checking, optimistic/pessimistic locking |
| Spring Security               | 🟡    | Filter chain, OAuth2 resource server, OIDC login, JWT, method security        |
| Spring MVC vs WebFlux         | 🟡    | Blocking vs reactive, and why virtual threads changed the trade-off           |
| Validation & error handling   | 🟢    | Bean Validation, `@ControllerAdvice`, Problem Details (RFC 9457)              |
| Spring Cloud / resilience     | 🔴    | Config, gateway, Resilience4j (circuit breaker, retry, bulkhead)              |

**Go deeper:** [Java Core & JVM](interviews/java-core-jvm.md) · [Spring & Architecture](interviews/spring-architecture.md) ·
[Java 25](tech/backend/java-25.md) · [ArchUnit](tech/backend/arch-unit.md) · [Java notes](notes/java.md) ·
[Java best practices](best-practices/java.md) · [Streams in IntelliJ](tech/backend/java-stream-intellij.md)

**Practice**

- Build a Spring Boot service with a clean layering, full test pyramid and Testcontainers.
- Reproduce an N+1 problem and a `@Transactional` self-invocation bug, then fix them.
- Profile a slow endpoint with JFR / async-profiler and write down what you found.

---

## 3. Data & persistence

| Topic                          | Level | What to know                                                                |
|--------------------------------|-------|-----------------------------------------------------------------------------|
| SQL                            | 🟢    | Joins, aggregation, subqueries, CTEs, window functions                      |
| Data modeling                  | 🟢    | Normalization (and when to denormalize), constraints, keys                  |
| Indexes                        | 🟡    | B-tree vs hash/GIN/GiST, composite index ordering, covering indexes, `EXPLAIN ANALYZE` |
| Transactions                   | 🟡    | ACID, isolation levels, anomalies (dirty/non-repeatable/phantom reads), MVCC, deadlocks |
| PostgreSQL specifics           | 🟡    | JSONB, partitioning, `VACUUM`, connection pooling (HikariCP, PgBouncer)     |
| Schema migrations              | 🟢    | Flyway / Liquibase, backward-compatible (expand/contract) migrations        |
| ORM vs SQL mappers             | 🟡    | JPA vs MyBatis vs jOOQ — pick by use case                                   |
| NoSQL families                 | 🟡    | Document (MongoDB), key-value (Redis), wide-column (Cassandra), search (Elasticsearch) — when each fits |
| Caching                        | 🟡    | Cache-aside, write-through, TTL, invalidation, stampede protection          |
| Replication & sharding         | 🔴    | Read replicas, replication lag, partitioning keys, rebalancing              |

**Go deeper:** [Persistence & SQL](interviews/persistence-sql-postgres.md)

**Practice**

- Take a slow query, read its plan, add the right index, measure before/after.
- Run a zero-downtime column rename with expand/contract migrations.

---

## 4. Messaging, integration & APIs

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| REST API design                | 🟢    | Resources, HTTP semantics, status codes, pagination, filtering, idempotent methods |
| API contracts                  | 🟢    | OpenAPI, contract-first vs code-first, versioning strategies                  |
| REST vs gRPC vs GraphQL        | 🟡    | Trade-offs: coupling, performance, tooling, caching                           |
| Kafka vs RabbitMQ              | 🟡    | Log vs queue, partitions, consumer groups, ordering, retention                |
| Delivery semantics             | 🟡    | At-most / at-least / exactly-once, and why idempotent consumers matter        |
| Transactional outbox & CDC     | 🔴    | Avoid dual writes; Debezium                                                   |
| Sagas                          | 🔴    | Orchestration vs choreography, compensating actions                           |
| Schema evolution               | 🔴    | Avro/Protobuf, Schema Registry, backward/forward compatibility                |
| Webhooks, retries, DLQs        | 🟡    | Exponential backoff with jitter, poison messages, replay                      |

**Go deeper:** [Messaging](interviews/messaging-rabbitmq-kafka.md) · [API guidelines](tech/backend/api-guidelines.md) ·
[AAA](tech/backend/aaa.md)

**Practice**

- Implement the outbox pattern between a Spring service and Kafka, with an idempotent consumer.
- Design and document a versioned public API with OpenAPI.

---

## 5. Frontend React track

### JavaScript & TypeScript

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| JS fundamentals                | 🟢    | Scope, closures, `this`, prototypes, event loop, promises, `async/await`      |
| Modern JS                      | 🟢    | ES modules, destructuring, spread, optional chaining, immutability patterns   |
| TypeScript                     | 🟢    | Types vs interfaces, unions, narrowing, generics                              |
| Advanced TypeScript            | 🟡    | Utility & mapped types, conditional types, `satisfies`, discriminated unions, strict mode |
| Browser                        | 🟡    | DOM, rendering pipeline, storage, fetch, Web APIs, service workers            |

### React

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| Components & hooks             | 🟢    | `useState`, `useEffect`, `useRef`, `useContext`, custom hooks, rules of hooks |
| Rendering model                | 🟡    | Reconciliation, keys, when and why components re-render                       |
| Performance                    | 🟡    | `memo`, `useMemo`, `useCallback` (and when they are useless), React Compiler, virtualization |
| Effects done right             | 🟡    | "You might not need an effect", cleanup, race conditions                      |
| State management               | 🟡    | Local vs lifted vs global; server state (TanStack Query) vs client state (Zustand / Redux Toolkit) |
| Forms & validation             | 🟢    | React Hook Form + Zod, controlled vs uncontrolled                             |
| Routing & data loading         | 🟢    | React Router / TanStack Router, loaders, code splitting                       |
| Suspense, concurrent features  | 🟡    | `Suspense`, transitions, error boundaries                                     |
| Server Components & frameworks | 🔴    | RSC model, Next.js, SSR vs SSG vs CSR trade-offs                              |
| Styling                        | 🟢    | CSS fundamentals (flex, grid), CSS Modules / Tailwind, design systems         |
| Accessibility                  | 🟡    | Semantic HTML, WCAG, ARIA, keyboard navigation, screen reader testing         |
| Web performance                | 🟡    | Core Web Vitals (LCP, INP, CLS), bundle analysis, lazy loading, image optimization |
| Testing                        | 🟢    | Vitest/Jest, React Testing Library, MSW, Playwright for E2E                   |
| Tooling                        | 🟢    | Vite, ESLint, Prettier, pnpm/npm, monorepos (Nx / Turborepo)                  |
| Frontend security              | 🟡    | XSS, CSP, CSRF, token storage, dependency hygiene                             |
| Frontend architecture          | 🔴    | Feature-based folders, shared UI library, micro-frontends (and their cost)    |

**Go deeper:** [React & TypeScript](interviews/react-typescript.md) · Skill: `vercel-react-best-practices`

**Practice**

- Build a React + TS app consuming your Spring API, with TanStack Query, forms, auth and E2E tests.
- Audit it with Lighthouse and an accessibility checker; fix the top findings.

---

## 6. DevOps & cloud

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| Git                            | 🟢    | Branching, rebase vs merge, interactive rebase, bisect, trunk-based development, conventional commits |
| Linux & shell                  | 🟢    | Processes, permissions, networking commands, `grep`/`sed`/`awk`/`jq`/`curl`   |
| CI/CD                          | 🟢    | GitHub Actions / GitLab CI, pipeline stages, caching, quality gates (SonarQube), artifact versioning |
| Docker                         | 🟢    | Images vs containers, multi-stage builds, layer caching, distroless/minimal images, Compose |
| Kubernetes                     | 🟡    | Pods, Deployments, Services, Ingress, ConfigMaps/Secrets, probes, resources/limits, HPA |
| Helm / Kustomize               | 🟡    | Packaging, values per environment, releases and rollbacks                     |
| Infrastructure as Code         | 🟡    | Terraform: state, modules, plan/apply, drift                                  |
| Cloud provider (pick one deep) | 🟡    | AWS / GCP / Azure: compute, managed DBs, queues, IAM, networking (VPC), storage |
| Deployment strategies          | 🟡    | Rolling, blue/green, canary, feature flags, dark launches                     |
| Observability                  | 🟡    | Structured logs, metrics, distributed tracing, OpenTelemetry, Prometheus/Grafana, correlation IDs |
| Reliability                    | 🔴    | SLI / SLO / error budgets, alerting on symptoms, capacity planning            |
| Incident management            | 🔴    | On-call, runbooks, blameless postmortems                                      |
| GitOps & platform              | 🔴    | Argo CD / Flux, internal developer platforms, golden paths                    |

**Go deeper:** [Full Stack & DevOps](interviews/fullstack-devops-k8s.md) · [kubectl](tech/devops/kubectl.md) ·
[Helm](tech/devops/helm.md) · [Git](notes/git.md) · Shell: [grep](tech/shell/grep.md), [sed](tech/shell/sed.md),
[awk](tech/shell/awk.md), [jq](tech/shell/jq.md), [curl](tech/shell/curl.md)

**Practice**

- Containerize your full-stack app, deploy it on a local cluster (kind / k3d) with Helm.
- Build a pipeline: lint → test → build image → scan → deploy to staging → smoke test.
- Add OpenTelemetry tracing across frontend → backend → DB, and a Grafana dashboard with an SLO.

---

## 7. Security

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| OWASP Top 10 (Web & API)       | 🟢    | Injection, broken access control, SSRF, security misconfiguration…            |
| Authentication                 | 🟡    | Sessions vs tokens, OAuth2 flows (Authorization Code + PKCE, Client Credentials), OIDC |
| Authorization                  | 🟡    | RBAC vs ABAC, multi-tenancy, object-level checks                              |
| Secrets management             | 🟡    | Vault / cloud secret managers, never in git, rotation                         |
| Supply chain                   | 🟡    | Dependency scanning (SCA), SBOM, image scanning (Trivy), pinning & updates (Renovate/Dependabot) |
| Transport & data               | 🟡    | TLS everywhere, encryption at rest, hashing passwords (bcrypt/Argon2), PII handling, GDPR |
| Threat modeling                | 🔴    | STRIDE, data-flow diagrams, security reviews as part of design                |
| Secure SDLC                    | 🔴    | SAST/DAST in pipelines, security champions, pentest follow-up                 |

**Go deeper:** [System Design & Leadership](interviews/system-design-leadership.md) (OWASP section)

---

## 8. Architecture

| Topic                                   | Level | What to know                                                         |
|-----------------------------------------|-------|----------------------------------------------------------------------|
| Layered architecture                    | 🟢    | Controllers / services / repositories and their limits               |
| Hexagonal / Clean / Onion               | 🟡    | Ports & adapters, dependency rule, framework at the edge             |
| Monolith → modular monolith → microservices | 🔴 | When to split (team topology, scaling, deployment independence) and when **not** to |
| Domain-Driven Design — tactical         | 🟡    | Entities, value objects, aggregates, domain events, repositories     |
| Domain-Driven Design — strategic        | 🔴    | Ubiquitous language, bounded contexts, context mapping, event storming |
| Event-driven architecture               | 🔴    | Events vs commands, eventual consistency, choreography vs orchestration |
| CQRS & event sourcing                   | 🔴    | Benefits, costs, and why most systems don't need them               |
| Quality attributes                      | 🔴    | Scalability, availability, maintainability, security — and trade-offs between them |
| Documenting architecture                | 🔴    | ADRs, C4 model, arc42, diagrams as code (Mermaid, PlantUML, Structurizr) |
| Evolutionary architecture               | 🔴    | Fitness functions, strangler fig, anti-corruption layer              |
| Technical debt                          | 🔴    | Identify, quantify, prioritize, negotiate time for it                |
| Team topologies & Conway's law          | 🔴    | Architecture mirrors communication structure — design both           |

**Go deeper:** [Hexagonal architecture](architecture/hexagonal.md) · [Spring & Architecture](interviews/spring-architecture.md) ·
[Tech debt](tech/tech-debt.md) · [ArchUnit](tech/backend/arch-unit.md)

**Practice**

- Refactor a service into hexagonal architecture and enforce it with ArchUnit.
- Run an event storming session on a domain you know; derive bounded contexts.
- Write 3 ADRs for real decisions in your current project.

---

## 9. System design

### Method

1. **Clarify requirements** — functional, non-functional (load, latency, availability, consistency, compliance).
2. **Estimate** — QPS, storage, bandwidth (back-of-the-envelope).
3. **API** — main endpoints / events.
4. **Data model** — entities, access patterns, storage choice.
5. **High-level design** — components and flows.
6. **Deep dive** — bottlenecks, failure modes, scaling each component.
7. **Trade-offs** — what you chose, what you gave up, what you would do next.

### Building blocks

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| Scaling                        | 🟡    | Vertical vs horizontal, stateless services, load balancing (L4 vs L7)          |
| Caching layers                 | 🟡    | Browser, CDN, gateway, application, database                                  |
| Data distribution              | 🔴    | Replication (leader/follower, multi-leader), sharding, consistent hashing      |
| Consistency                    | 🔴    | CAP, PACELC, strong vs eventual consistency, read-your-writes                 |
| Asynchronous processing        | 🟡    | Queues, back-pressure, batch vs stream processing                            |
| Resilience                     | 🟡    | Timeouts, retries with backoff + jitter, circuit breakers, bulkheads, graceful degradation |
| Rate limiting                  | 🟡    | Token bucket, sliding window, where to enforce it                             |
| Search & analytics             | 🔴    | Inverted indexes, OLTP vs OLAP, data pipelines                                |
| Multi-region                   | 🔴    | Active-passive vs active-active, data residency, failover                     |

### Classic exercises

- [ ] URL shortener
- [ ] Rate limiter
- [ ] News feed / timeline
- [ ] Chat / notification system
- [ ] File storage (Dropbox-like)
- [ ] E-commerce checkout & payments (idempotency, sagas)
- [ ] Booking system (concurrency, double booking)
- [ ] Metrics / logging pipeline

**Go deeper:** [System Design & Leadership](interviews/system-design-leadership.md)

---

## 10. AI-assisted development

| Topic                          | Level | What to know                                                                  |
|--------------------------------|-------|-------------------------------------------------------------------------------|
| Using coding agents            | 🟢    | Effective prompting, giving context, iterating with tests                     |
| Reviewing AI output            | 🟡    | Treat it as a junior's PR: verify, test, question                             |
| Context engineering            | 🟡    | Project instructions (`CLAUDE.md`), skills, MCP servers, hooks                |
| Team adoption & governance     | 🔴    | Guidelines, security (secrets, prompt injection), measuring impact            |

**Go deeper:** [Claude Code & AI-assisted Dev](interviews/claude-code.md)

---

## 11. Tech lead skills — the non-code half

### Technical leadership

| Skill                          | What it looks like in practice                                                |
|--------------------------------|-------------------------------------------------------------------------------|
| Technical vision               | A written, shared direction for the next 6–12 months, aligned with the product |
| Decision making                | RFCs / ADRs, one-way vs two-way doors, disagree-and-commit, decide with incomplete information |
| Code review culture            | Fast, kind, focused reviews; clear conventions; automate the nitpicks          |
| Quality standards              | Definition of done, testing strategy, linting, CI gates                       |
| Balancing debt vs features     | Make debt visible, tie it to business impact, reserve capacity                 |
| Delivery                       | Break down epics, identify risks early, deliver in thin vertical slices       |
| Estimation & planning          | Ranges not points, explicit assumptions, re-plan when facts change            |
| Operational ownership          | On-call health, incident leadership, postmortem follow-through                 |
| Measuring                      | DORA metrics (lead time, deploy frequency, change failure rate, MTTR)          |

### People & communication

| Skill                          | What it looks like in practice                                                |
|--------------------------------|-------------------------------------------------------------------------------|
| Mentoring & coaching           | Pairing, growth plans, giving stretch tasks, asking before telling            |
| Delegation                     | Give problems, not solutions; don't take the critical path yourself           |
| Feedback                       | Specific, timely, behaviour-focused (SBI model)                               |
| Stakeholder communication      | Explain technical trade-offs in business terms; say no with alternatives      |
| Writing                        | Clear design docs, status updates, decision records                           |
| Facilitation                   | Running design reviews, refinements, retrospectives that lead to action       |
| Conflict resolution            | Separate people from positions, align on goals, escalate cleanly              |
| Hiring                         | Structured interviews, fair evaluation, onboarding plans                      |
| Psychological safety           | Blameless culture, admitting your own mistakes, making it safe to ask         |

**Go deeper:** [System Design & Leadership](interviews/system-design-leadership.md)

**Practice**

- Lead the design of one feature end-to-end: RFC → review → ADR → delivery → retro.
- Mentor one person for 3 months with explicit goals.
- Run a blameless postmortem and follow the action items to completion.

---

## 12. Tools checklist

| Category              | Primary (master)                     | Alternatives (know)                             |
|-----------------------|--------------------------------------|-------------------------------------------------|
| IDE                   | IntelliJ IDEA                        | VS Code, WebStorm                               |
| Build (backend)       | Maven                                | Gradle                                          |
| Build (frontend)      | Vite + pnpm                          | npm, Webpack, Turborepo / Nx                    |
| Testing (backend)     | JUnit 5, AssertJ, Mockito, Testcontainers | ArchUnit, PIT, WireMock, Pact              |
| Testing (frontend)    | Vitest, React Testing Library, Playwright | Jest, Cypress, MSW                         |
| Code quality          | SonarQube, ESLint, Prettier          | Checkstyle, SpotBugs, Error Prone               |
| Version control       | Git + GitHub / GitLab                | —                                               |
| CI/CD                 | GitHub Actions / GitLab CI           | Jenkins, Argo CD                                |
| Containers & orchestration | Docker, Kubernetes, Helm        | Podman, Kustomize, kind / k3d                   |
| IaC                   | Terraform                            | Pulumi, CloudFormation                          |
| Observability         | OpenTelemetry, Prometheus, Grafana   | ELK / Loki, Jaeger / Tempo, Datadog             |
| Databases             | PostgreSQL, Redis                    | MongoDB, Elasticsearch                          |
| Messaging             | Kafka                                | RabbitMQ                                        |
| API                   | OpenAPI, Bruno / Postman, `curl`     | Insomnia, HTTPie                                |
| Diagrams & docs       | Mermaid, Excalidraw, MkDocs          | PlantUML, Structurizr (C4), draw.io             |
| Profiling             | JFR / JMC, async-profiler            | VisualVM, Chrome DevTools, React Profiler       |
| AI                    | Claude Code                          | Other coding assistants                         |

---

## 13. Suggested timeline

A realistic path while working full-time. Adjust to your starting point.

| Phase           | Focus                                                            | Milestone                                                       |
|-----------------|------------------------------------------------------------------|-----------------------------------------------------------------|
| **Months 0–3**  | Fill 🟢 gaps: modern Java, Spring fundamentals, SQL, TS/React basics, Git, Docker | A tested full-stack app (Spring + React) running in Docker Compose |
| **Months 3–6**  | JVM & concurrency, JPA pitfalls, React performance, CI/CD, testing strategy | Pipeline with quality gates; app deployed on Kubernetes with Helm |
| **Months 6–12** | Messaging, observability, security, hexagonal + DDD tactical, system design practice | Event-driven feature with outbox; tracing + SLO dashboard; 4 system design exercises done |
| **Months 12–18**| Architecture (DDD strategic, ADRs, C4), cloud provider deep dive, leading features | Led a feature from RFC to production; wrote ADRs; mentored someone |
| **Months 18–24**| Tech lead skills: vision, planning, stakeholder management, incident leadership | Owning a team's technical direction; recognized as go-to person across teams |

---

## 14. Reading list

| Area                      | Books                                                                                              |
|---------------------------|----------------------------------------------------------------------------------------------------|
| Java                      | *Effective Java* (Bloch) · *Java Concurrency in Practice* (Goetz) · *Modern Java in Action*        |
| Code craft                | *Clean Code* (Martin) · *Refactoring* (Fowler) · *The Pragmatic Programmer* · *Working Effectively with Legacy Code* (Feathers) |
| Testing                   | *Unit Testing: Principles, Practices, and Patterns* (Khorikov) · *Growing Object-Oriented Software, Guided by Tests* |
| Data & distributed systems| *Designing Data-Intensive Applications* (Kleppmann) · *Database Internals* (Petrov)               |
| Architecture              | *Fundamentals of Software Architecture* (Richards & Ford) · *Software Architecture: The Hard Parts* · *Building Microservices* (Newman) · *Clean Architecture* (Martin) · *Building Evolutionary Architectures* |
| DDD                       | *Domain-Driven Design* (Evans) · *Implementing DDD* (Vernon) · *Learning DDD* (Khononov)           |
| System design             | *System Design Interview* vol. 1 & 2 (Xu) · *Release It!* (Nygard)                                |
| DevOps & reliability      | *Accelerate* (Forsgren) · *The Phoenix Project* · *Site Reliability Engineering* (Google) · *Kubernetes in Action* |
| Frontend                  | *Learning TypeScript* · react.dev docs · *Refactoring UI* · web.dev (performance & accessibility)  |
| Leadership                | *The Staff Engineer's Path* (Reilly) · *The Manager's Path* (Fournier) · *An Elegant Puzzle* (Larson) · *Team Topologies* · *Radical Candor* |

**More:** [Further reading](interviews/further-reading.md)

---

## Self-assessment checklist

### 🟢 Mid → Senior

- [ ] I can explain `equals`/`hashCode`, collections complexity and stream collectors without notes.
- [ ] I write unit and integration tests by default, including with Testcontainers.
- [ ] I can read an `EXPLAIN ANALYZE` plan and fix a missing index.
- [ ] I know when a React component re-renders and how to avoid unnecessary renders.
- [ ] I can write a Dockerfile with a multi-stage build and a CI pipeline from scratch.
- [ ] I design REST APIs with correct HTTP semantics, validation and error format.
- [ ] I use Git confidently: rebase, bisect, resolving conflicts.

### 🟡 Senior

- [ ] I can explain `@Transactional` propagation, proxy pitfalls and the N+1 problem — and fix them.
- [ ] I can diagnose a memory leak or a thread contention issue with JVM tools.
- [ ] I understand isolation levels and have handled a concurrency bug in production.
- [ ] I choose between Kafka and RabbitMQ with clear arguments, and build idempotent consumers.
- [ ] I have deployed and debugged services on Kubernetes (probes, resources, logs, events).
- [ ] I instrument services with metrics, logs and traces and set meaningful alerts.
- [ ] I can apply OWASP Top 10 mitigations and implement OAuth2/OIDC correctly.
- [ ] I structure code with hexagonal architecture and DDD tactical patterns when they fit.
- [ ] I can run a 45-minute system design interview end-to-end with explicit trade-offs.
- [ ] My code reviews improve the code *and* teach the author.

### 🔴 Tech Lead

- [ ] I have written RFCs/ADRs that the team used to make decisions.
- [ ] I can draw the C4 context and container diagrams of my system from memory.
- [ ] I can decide whether to split a service — and argue *against* microservices when appropriate.
- [ ] I have led an incident and a blameless postmortem.
- [ ] I have defined SLOs and used error budgets to prioritize work.
- [ ] I have a written technical roadmap aligned with product goals.
- [ ] I translate technical trade-offs into business impact for non-technical stakeholders.
- [ ] I mentor at least one engineer with explicit growth goals.
- [ ] I track delivery health (DORA metrics) and act on it.
- [ ] The team makes good decisions when I'm not in the room.
