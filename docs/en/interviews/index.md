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
| 8 | [`System Design & Leadership`](system-design-leadership.md) | Scalability, CAP, OWASP, mentoring                                |
| 9 | [`Claude Code & AI-assisted Dev`](claude-code.md)           | Agentic coding, prompts/context, MCP, AI security, governance     |


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
| 📌 Cheat-sheet          | Quick review the day before             |

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
- **For coding**, discuss complexity, edge cases and tests.

## Final checklist

Once you've been through every module, [`mock-interview.md`](mock-interview.md) is a compact,
self-assessable checklist for the day before — work through it and be honest about which items
you can't yet answer from memory, with code, on the spot.
