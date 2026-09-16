# Mock Interviews

| Document | Owns |
|---|---|
| **`mock-interview.md`** (this file) | Pre-interview readiness checklist |
| [`index.md`](index.md) | Module overview, revision plan, scenario format |
| [`01-java-core-jvm.md`](01-java-core-jvm.md) | **Java Core & JVM** — records, sealed, virtual threads, concurrency, GC |
| [`02-spring-architecture.md`](02-spring-architecture.md) | **Spring & Architecture** — DI, `@Transactional`, security, hexagonal, design patterns |
| [`03-persistence-sql-postgres.md`](03-persistence-sql-postgres.md) | **Persistence & SQL** — MyBatis, advanced SQL, PostgreSQL, indexes |
| [`04-messaging-rabbitmq-kafka.md`](04-messaging-rabbitmq-kafka.md) | **Messaging** — RabbitMQ vs Kafka, idempotency, sagas |
| [`05-react-typescript.md`](05-react-typescript.md) | **React & TypeScript** — hooks, state, performance, TS |
| [`06-fullstack-devops-k8s.md`](06-fullstack-devops-k8s.md) | **Full Stack & DevOps** — API design, Docker, K8s, observability, git |
| [`07-system-design-leadership.md`](07-system-design-leadership.md) | **System Design & Leadership** — scalability, CAP, OWASP, mentoring |
| [`08-claude-code.md`](08-claude-code.md) | **Claude Code & AI-assisted Dev** — agentic coding, MCP, AI security |


## Interview Preparation Checklist
- [ ] I can explain interface vs. abstract class using a real design decision, not just the textbook definition.
- [ ] I can trace what happens internally in a HashMap put/get, and explain why a bad hashCode() is a real
performance bug. 
- [ ] I can explain ConcurrentModificationException and show the correct fix, from memory, with code. 
- [ ] I can name all four thread-safe Singleton implementation strategies and explain why Bill Pugh / static
inner class is preferred.
- [ ] I can explain the difference between synchronized and volatile without conflating mutual exclusion
with visibility.
- [ ] I can explain reachability analysis, GC Roots, and at least two named GC algorithms.
- [ ] I can explain why field injection is harder to test than constructor injection. 
- [ ] I can explain, in detail, why @Transactional silently fails on self-invocation — and name all four fixes.
- [ ] I can explain the difference between flush() and commit().
- [ ] I can explain why @Async methods lose the Spring Security context.
- [ ] I can explain all four Hibernate entity states with a usage example for each.
- [ ] I can explain the N+1 problem and at least two ways to fix it.
- [ ] I can explain optimistic vs. pessimistic locking in terms of contention, not just definition.
- [ ] I can walk through a normalization example from 1NF to 3NF on a whiteboard.
- [ ] I can explain the logical SQL execution order and why WHERE can't reference a SELECT alias.
- [ ] I can explain the five design patterns underneath Spring itself, not just list GoF pattern names.
- [ ] I can explain the real difference between hashing, encoding, and encryption — and why encoding is not security.
