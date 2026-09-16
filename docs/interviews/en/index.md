# Interview Preparation — Full Stack Java / React (Senior)

## Modules

| # | Module                        | File                             | Focus                                                         |
|---|-------------------------------|----------------------------------|---------------------------------------------------------------|
| 1 | Java Core & JVM               | `01-java-core-jvm.md`            | records, sealed, virtual threads, concurrency, GC             |
| 2 | Spring & Architecture         | `02-spring-architecture.md`      | `@Transactional`, security, hexagonal                         |
| 3 | Persistence & SQL             | `03-persistence-sql-postgres.md` | MyBatis, advanced SQL, PostgreSQL, indexes                    |
| 4 | Messaging                     | `04-messaging-rabbitmq-kafka.md` | RabbitMQ vs Kafka, idempotency, sagas                         |
| 5 | React & TypeScript            | `05-react-typescript.md`         | Hooks, state, performance, TS                                 |
| 6 | Full Stack & DevOps           | `06-fullstack-devops-k8s.md`     | API design, Docker, K8s, observability                        |
| 7 | System Design & Leadership    | `07-system-design-leadership.md` | Scalability, CAP, OWASP, mentoring                            |
| 8 | Claude Code & AI-assisted Dev | `08-claude-code.md`              | Agentic coding, prompts/context, MCP, AI security, governance |

## Suggested revision plan (D-7)

| Day | Morning                      | Afternoon                   |
|-----|------------------------------|-----------------------------|
| D-7 | Module 1 (Java Core)         | Module 2 (Spring)           |
| D-6 | Module 3 (SQL/Persistence)   | Review Modules 1–2          |
| D-5 | Module 4 (Messaging)         | Module 5 (React)            |
| D-4 | Module 6 (DevOps/K8s)        | Review Modules 3–4          |
| D-3 | Module 7 (System Design)     | Module 8 (Claude Code / AI) |
| D-2 | Cheat-sheets for all modules | Mock interview (out loud)   |
| D-1 | Identified weak points       | Rest + light review         |

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

