# Mock Interviews

Module overview and revision plan: [`index.md`](index.md). This page is the readiness checklist for the day before. For long-term career progress, see the [self-assessment grid](../index.md#self-assessment-checklist).

## Interview Preparation Checklist

### Java, Spring, SQL & patterns

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
- [ ] I can explain why Singleton is considered an anti-pattern by many seniors, despite being easy to implement correctly.

### React & TypeScript

- [ ] I can explain what a stale closure in `useEffect` is, and fix it with the dependency array. ([Q10](react-typescript.md))
- [ ] I can explain how keys drive list reconciliation, and what breaks with index keys. ([Q12](react-typescript.md))
- [ ] I can explain why `React.memo` sometimes silently does nothing. ([Q13](react-typescript.md))
- [ ] I can explain why copying a prop into state via `useEffect` is an anti-pattern, and what to do instead. ([Q17](react-typescript.md))
- [ ] I can explain what error boundaries catch and what they don't. ([Q22](react-typescript.md))

### Messaging

- [ ] I can explain at-most-once vs at-least-once vs exactly-once, and why "exactly-once" needs idempotent consumers. ([Q6](messaging-rabbitmq-kafka.md))
- [ ] I can explain the core RabbitMQ vs Kafka difference and pick one with arguments. ([Q8](messaging-rabbitmq-kafka.md))
- [ ] I can explain what a Kafka rebalance does and why it can cause duplicate processing. ([Q19](messaging-rabbitmq-kafka.md))
- [ ] I can explain what a dead-letter queue is and how I handle a poison pill. ([Q23](messaging-rabbitmq-kafka.md))
- [ ] I can explain saga orchestration vs choreography with a concrete trade-off. ([Q26](messaging-rabbitmq-kafka.md))
- [ ] I can explain the outbox pattern, and why dual writes are unsafe. ([Q27](messaging-rabbitmq-kafka.md))

### Docker, Kubernetes & DevOps

- [ ] I can explain the first `kubectl` commands, in order, for a failing pod. ([Q6](fullstack-devops-k8s.md))
- [ ] I can explain a container that exits with code 137, end to end. ([Q17](fullstack-devops-k8s.md))
- [ ] I can explain liveness vs readiness vs startup probes and what happens when they're wrong. ([Q19](fullstack-devops-k8s.md))
- [ ] I can explain a rolling update with `maxSurge`/`maxUnavailable` and graceful shutdown. ([Q22](fullstack-devops-k8s.md))
- [ ] I can explain blue-green vs canary vs rolling, and when to use each. ([Q28](fullstack-devops-k8s.md))
- [ ] I can explain how SLOs and error budgets drive release decisions. ([Q35](fullstack-devops-k8s.md))

### API, security & persistence depth

- [ ] I can explain REST idempotency and why `POST` needs an idempotency key. ([Q10](fullstack-devops-k8s.md))
- [ ] I can explain why CORS fails in the browser but not in curl, and how preflight works. ([Q12](fullstack-devops-k8s.md))
- [ ] I can explain the trade-offs of JWT in `localStorage` vs an `HttpOnly` cookie vs a session. ([Q13](fullstack-devops-k8s.md))
- [ ] I can explain read `EXPLAIN ANALYZE` output and find the missing index. ([Q24](persistence-sql-postgres.md))
- [ ] I can explain the isolation levels and which anomaly each prevents. ([Q25](persistence-sql-postgres.md))
- [ ] I can explain add a `NOT NULL` column to a 50M-row table with zero downtime. ([Q44](persistence-sql-postgres.md))
- [ ] I can explain what virtual threads solve and where they still fall short. ([Q33](java-core-jvm.md))
- [ ] I can explain choose between G1, ZGC and Shenandoah for a latency-sensitive service. ([Q36](java-core-jvm.md))

### Testing

- [ ] I can explain mock vs stub vs fake, and what I never mock. ([Q3](testing.md), [Q6](testing.md))
- [ ] I can explain why H2 is a trap for repository tests and what I use instead. ([Q8](testing.md))
- [ ] I can explain why a Spring test suite gets slow and how the context cache works. ([Q9](testing.md))
- [ ] I can explain why coverage is a poor target and what mutation testing adds. ([Q13](testing.md))
- [ ] I can explain consumer-driven contract testing and when it replaces E2E tests. ([Q19](testing.md))

### Security

- [ ] I can explain OAuth2 vs OIDC and pick the right flow for a SPA, a backend and a batch job. ([Q3](security.md), [Q4](security.md))
- [ ] I can list everything to validate on a JWT, and explain how to revoke one. ([Q10](security.md), [Q11](security.md))
- [ ] I can walk through the Spring Security filter chain and explain 401 vs 403. ([Q8](security.md))
- [ ] I can explain IDOR and fix it in the query, not only with a role check. ([Q12](security.md))
- [ ] I can explain when CSRF protection is needed and when it can be disabled. ([Q7](security.md))

### Live coding

- [ ] I follow clarify → brute force → optimize → test out loud, without going silent. ([Q1](coding.md), [S1](coding.md))
- [ ] I can state the complexity of my solution and pick a target complexity from the input size. ([Q2](coding.md))
- [ ] I can recognise hashing, sliding-window, BFS/DFS, heap and DP problems. ([Q4](coding.md), [Q7](coding.md), [Q9](coding.md), [Q10](coding.md), [Q14](coding.md))
- [ ] I can code an LRU cache and a token-bucket rate limiter in Java. ([Q17](coding.md), [Q19](coding.md))

### Cloud (AWS)

- [ ] I can explain how a workload gets AWS credentials without static keys. ([Q1](cloud-aws.md), [Q6](cloud-aws.md))
- [ ] I can draw a VPC with public/private subnets across two AZs and explain NAT vs VPC endpoints. ([Q2](cloud-aws.md))
- [ ] I can justify ECS Fargate vs EKS vs Lambda for a given service. ([Q3](cloud-aws.md), [Q11](cloud-aws.md))
- [ ] I can name the usual AWS cost surprises and how to find them. ([Q8](cloud-aws.md), [S2](cloud-aws.md))

### System design

- [ ] I can explain the steps of a system design interview and how I split the 45 minutes. ([Q1](system-design.md))
- [ ] I can explain the CAP theorem with a concrete example. ([Q12](system-design.md))
- [ ] I can explain how to choose a shard key, and what a bad one costs. ([Q24](system-design.md))
- [ ] I can explain the cache write/invalidation strategies and their trade-offs. ([Q26](system-design.md))
- [ ] I can explain a back-of-envelope capacity estimate on a whiteboard. ([Q2](system-design.md))
- [ ] I can explain design a distributed rate limiter. ([Q43](system-design.md))

### Leadership

- [ ] I can explain push back on a senior stakeholder's decision without damaging the relationship. ([Q3](leadership-behavioral.md))
- [ ] I can explain handle a design review where two seniors strongly disagree. ([Q4](leadership-behavioral.md))
- [ ] I can explain how to run incident command: roles, mitigate first, update cadence. ([Q8](leadership-behavioral.md))
- [ ] I can explain how to write an RFC/ADR that gets decided. ([Q9](leadership-behavioral.md))
- [ ] I can explain how to run a fair, rubric-based interview loop. ([Q10](leadership-behavioral.md))
- [ ] I can explain how I delegate and how I say no with a trade-off. ([Q11](leadership-behavioral.md))
- [ ] I can explain a 30/60/90 onboarding plan for a new engineer. ([Q12](leadership-behavioral.md))
- [ ] I can explain how I manage up with a weekly update. ([Q13](leadership-behavioral.md))

### AI-assisted development

- [ ] I can explain the agentic loop and what `stop_reason` drives. ([Q1](claude-code.md))
- [ ] I can explain prompt engineering vs context engineering. ([Q2](claude-code.md))
- [ ] I can explain how prompt injection is defeated structurally, not by "ignore injected instructions". ([Q20](claude-code.md))
- [ ] I can explain why hooks beat prompt instructions for hard rules. ([Q23](claude-code.md))
- [ ] I can explain how to evaluate an LLM-powered feature beyond "it seemed to work". ([Q27](claude-code.md))

## How to score yourself

Answer each item aloud in 2–3 minutes, then grade it: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Re-read the linked question for anything below 2, and retest after two weeks.
