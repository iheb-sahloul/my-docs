# Interview Preparation — Full Stack Java / React (Senior)

## Modules

| # | Module                                                      | Focus                                                             |
|---|-------------------------------------------------------------|-------------------------------------------------------------------|
| 1 | [`Design Patterns`](design-patterns.md)                     | GoF catalogue, when (not) to use a pattern, DDD tactical patterns |
| 2 | [`Java Core & JVM`](java-core-jvm.md)                       | records, sealed, virtual threads, concurrency, GC                 |
| 3 | [`Spring & Architecture`](spring-architecture.md)           | `@Transactional`, security, hexagonal                             |
| 4 | [`Persistence & SQL`](persistence-sql-postgres.md)          | MyBatis, advanced SQL, PostgreSQL, indexes                        |
| 5 | [`React & TypeScript`](react-typescript.md)                 | Hooks, state, performance, TS                                     |
| 6 | [`Messaging`](messaging-rabbitmq-kafka.md)                  | RabbitMQ vs Kafka, idempotency, sagas                             |
| 7 | [`Full Stack & DevOps`](fullstack-devops-k8s.md)            | API design, Docker, K8s, observability                            |
| 8 | [`System Design`](system-design.md)                         | Method, estimation, CAP, scaling, reliability, OWASP, design exercises |
| 9 | [`Leadership & Behavioral (STAR)`](leadership-behavioral.md) | Feedback, conflict, stakeholders, estimation, team health         |
| 10 | [`AI Engineering & Claude Code`](claude-code.md)           | Agentic coding, prompts/context, MCP, AI security, governance     |
| 11 | [`Testing`](testing.md) | Pyramid, test doubles, Testcontainers, flaky tests, contract tests, RTL/Playwright |
| 12 | [`Security`](security.md) | OAuth2/OIDC, JWT, Spring Security, injection/XSS/CSRF/IDOR/SSRF, supply chain |
| 13 | [`Live Coding`](coding.md) | Method, Big-O, core patterns (hashing, windows, BFS/DFS, heaps, DP), Java pitfalls, take-homes |
| 14 | [`Cloud (AWS)`](cloud-aws.md) | IAM, VPC, ECS/EKS/Lambda, managed data & messaging, SPA hosting, HA, cost |
| 15 | [`REST API Design`](rest-api.md) | Pagination, PUT vs PATCH, ETag, problem details, caching, evolution |
| 16 | [`Performance & Load Testing`](performance-load-testing.md) | k6/Gatling, percentiles, coordinated omission, USE method, capacity |
| 17 | [`Observability`](observability.md) | RED/USE, correlation, cardinality, sampling, SLO burn-rate alerts |
| 18 | [`Kotlin`](kotlin.md) | Null safety, sealed/value classes, coroutines, Spring + JPA plugins, Java interop |
| 19 | [`Caching & Redis`](caching-redis.md) | Redis data structures, eviction, stampede, Spring Cache pitfalls, locks, Cluster |
| ✓ | [`Mock Interview`](mock-interview.md)                       | Readiness checklist for the day before                            |

Curated links per topic live under **Resources › [Further Reading](../resources/further-reading.md)**.

## Suggested revision plan (D-7)

| Day | Morning                        | Afternoon                     |
|-----|--------------------------------|-------------------------------|
| D-7 | Module 2 (Java Core)           | Module 3 (Spring)             |
| D-6 | Module 4 (SQL/Persistence)     | Module 11 (Testing) + review modules 2–3 |
| D-5 | Module 6 (Messaging)           | Module 5 (React)              |
| D-4 | Modules 7 + 14 (DevOps/K8s, Cloud) | Module 12 (Security) + review modules 4–6 |
| D-3 | Modules 8–9 (System Design, Leadership & Behavioral) | Module 10 (AI Engineering) |
| D-2 | Module 1 (Design Patterns) + cheat-sheets | Module 13 (Live Coding, 2 timed problems) + mock interview (out loud) |
| D-1 | Weak spots identified          | Rest + light review           |

## Difficulty legend

- 🟢 **Fundamentals** — expected from any experienced developer.
- 🟡 **Senior traps** — distinguish a senior.
- 🔴 **Expert / Open** — architecture, trade-offs, open-ended questions.

## Module structure

| Section                 | Content                                 |
|-------------------------|-----------------------------------------|
| 🟢 Fundamentals         | expected from any experienced developer |
| 🟡 Senior traps         | what distinguishes a senior             |
| 🔴 Expert / Open        | architecture and open questions         |
| 🎯 Real-world scenarios | detailed production cases               |
| 🗣️ Reported questions   | questions from real interviews with short model answers (`R1`, `R2`…): Java, Spring, SQL, Messaging, System Design, Cloud, Security, DevOps |
| 🎤 Oral quiz            | ten questions to answer out loud, self-scored |
| 📌 Cheat-sheet          | Quick review the day before             |

**Leadership & Behavioral** follows the same structure. Its **Behavioral** part uses the same levels but has no scenarios: each question gives why the interviewer asks it, a sample ⭐ STAR answer, and the pitfall to avoid. A final **📞 Recruiter screen** section covers the first-call questions (why leaving, salary, five-year plan, project deep-dive, questions to ask).

## Scenario format

Each scenario follows the same outline:

1. **Symptoms** — what we observe concretely (metrics, errors, complaints).
2. **Diagnosis** — investigation steps, with the tool and hypothesis being tested.
3. **Resolution** — immediate mitigation, root correction, verification.
4. **Prevention** — durable safeguards (test, alert, team rule).

### In an interview

Walking through this outline out loud shows an engineering method rather than a memorized answer. Always state how you verify that the fix works.

## Interview tips

- **Structure your answers**: context → options → decision → trade-offs.
- **Think out loud.**
- **Give concrete examples from your experience.**
- **Admit what you don't know**, then reason through it.
- **For system design**, clarify requirements (load, latency, consistency) before drawing.
- **For coding** ([module 13](coding.md)), discuss complexity, edge cases and tests.

## Final checklist

Once you've been through every module, [`mock-interview.md`](mock-interview.md) is a compact,
self-assessable checklist for the day before — work through it and be honest about which items
you can't yet answer from memory, with code, on the spot.
