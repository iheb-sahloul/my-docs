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

- [ ] I can explain what a stale closure in `useEffect` is, and fix it with the dependency array. ([Q10](react-typescript.md#stale-closure-useeffect-dependency-array))
- [ ] I can explain how keys drive list reconciliation, and what breaks with index keys. ([Q12](react-typescript.md#react-re-render-keys-affect))
- [ ] I can explain why `React.memo` sometimes silently does nothing. ([Q13](react-typescript.md#react-memo-help-sometimes-silently))
- [ ] I can explain why copying a prop into state via `useEffect` is an anti-pattern, and what to do instead. ([Q17](react-typescript.md#copying-prop-local-state-via))
- [ ] I can explain what error boundaries catch and what they don't. ([Q22](react-typescript.md#react-error-boundaries-catch-explicitly))

### Messaging

- [ ] I can explain at-most-once vs at-least-once vs exactly-once, and why "exactly-once" needs idempotent consumers. ([Q6](messaging-rabbitmq-kafka.md#most-once-least-once-exactly))
- [ ] I can explain the core RabbitMQ vs Kafka difference and pick one with arguments. ([Q8](messaging-rabbitmq-kafka.md#core-architectural-rabbitmq-kafka-drive))
- [ ] I can explain what a Kafka rebalance does and why it can cause duplicate processing. ([Q19](messaging-rabbitmq-kafka.md#happens-during-kafka-consumer-group))
- [ ] I can explain what a dead-letter queue is and how I handle a poison pill. ([Q23](messaging-rabbitmq-kafka.md#dead-letter-queue-production-system))
- [ ] I can explain saga orchestration vs choreography with a concrete trade-off. ([Q26](messaging-rabbitmq-kafka.md#saga-pattern-orchestration-choreography-trade))
- [ ] I can explain the outbox pattern, and why dual writes are unsafe. ([Q27](messaging-rabbitmq-kafka.md#outbox-pattern-problem-solve))

### Docker, Kubernetes & DevOps

- [ ] I can explain the first `kubectl` commands, in order, for a failing pod. ([Q6](fullstack-devops-k8s.md#pod-isn-working-first-kubectl))
- [ ] I can explain a container that exits with code 137, end to end. ([Q17](fullstack-devops-k8s.md#diagnosing-docker-container-exits-code))
- [ ] I can explain liveness vs readiness vs startup probes and what happens when they're wrong. ([Q19](fullstack-devops-k8s.md#kubernetes-liveness-readiness-startup-probes))
- [ ] I can explain a rolling update with `maxSurge`/`maxUnavailable` and graceful shutdown. ([Q22](fullstack-devops-k8s.md#kubernetes-rolling-update-maxsurge-maxunavailable))
- [ ] I can explain blue-green vs canary vs rolling, and when to use each. ([Q28](fullstack-devops-k8s.md#compare-blue-green-canary-rolling))
- [ ] I can explain how SLOs and error budgets drive release decisions. ([Q35](fullstack-devops-k8s.md#slos-error-budgets-drive-release))

### API, security & persistence depth

- [ ] I can explain REST idempotency and why `POST` needs an idempotency key. ([Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need))
- [ ] I can explain why CORS fails in the browser but not in curl, and how preflight works. ([Q12](fullstack-devops-k8s.md#browser-request-fail-cors-error))
- [ ] I can explain the trade-offs of JWT in `localStorage` vs an `HttpOnly` cookie vs a session. ([Q13](fullstack-devops-k8s.md#jwt-localstorage-jwt-httponly-cookie))
- [ ] I can explain read `EXPLAIN ANALYZE` output and find the missing index. ([Q24](persistence-sql-postgres.md#read-analyze-output-diagnose-slow))
- [ ] I can explain the isolation levels and which anomaly each prevents. ([Q25](persistence-sql-postgres.md#name-transaction-isolation-levels-anomalies))
- [ ] I can explain add a `NOT NULL` column to a 50M-row table with zero downtime. ([Q44](persistence-sql-postgres.md#safely-add-null-column-50))
- [ ] I can explain what virtual threads solve and where they still fall short. ([Q33](java-core-jvm.md#problem-virtual-threads-project-loom))
- [ ] I can explain choose between G1, ZGC and Shenandoah for a latency-sensitive service. ([Q36](java-core-jvm.md#choosing-g1-zgc-shenandoah-latency))

### Testing

- [ ] I can explain mock vs stub vs fake, and what I never mock. ([Q3](testing.md#mock-stub-fake-spy-each), [Q6](testing.md#mockito-well-never-mock))
- [ ] I can explain why H2 is a trap for repository tests and what I use instead. ([Q8](testing.md#h2-repository-tests))
- [ ] I can explain why a Spring test suite gets slow and how the context cache works. ([Q9](testing.md#spring-test-suite-slow-make))
- [ ] I can explain why coverage is a poor target and what mutation testing adds. ([Q13](testing.md#80-code-coverage-good-target))
- [ ] I can explain consumer-driven contract testing and when it replaces E2E tests. ([Q19](testing.md#consumer-driven-contract-testing-worth))

### Security

- [ ] I can explain OAuth2 vs OIDC and pick the right flow for a SPA, a backend and a batch job. ([Q3](security.md#oauth-2-0-openid-connect), [Q4](security.md#oauth2-flow-client))
- [ ] I can list everything to validate on a JWT, and explain how to revoke one. ([Q10](security.md#exactly-validate-jwt-before-trusting), [Q11](security.md#revoke-jwt-refresh-tokens-fit))
- [ ] I can walk through the Spring Security filter chain and explain 401 vs 403. ([Q8](security.md#spring-security-filter-chain-process))
- [ ] I can explain IDOR and fix it in the query, not only with a role check. ([Q12](security.md#idor-broken-object-level-authorization))
- [ ] I can explain when CSRF protection is needed and when it can be disabled. ([Q7](security.md#csrf-need-csrf-protection))

### Live coding

- [ ] I follow clarify → brute force → optimize → test out loud, without going silent. ([Q1](coding.md#approach-live-coding-exercise), [S1](coding.md#stuck-halfway-problem-interviewer-silent))
- [ ] I can state the complexity of my solution and pick a target complexity from the input size. ([Q2](coding.md#big-o-complexities-know-heart))
- [ ] I can recognise hashing, sliding-window, BFS/DFS, heap and DP problems. ([Q4](coding.md#hash-map-turn-o-n2), [Q7](coding.md#two-pointer-sliding-window-patterns), [Q9](coding.md#bfs-dfs-each-solve-number), [Q10](coding.md#heap-right-tool-solve-top), [Q14](coding.md#dynamic-programming-spot-dp-problem))
- [ ] I can code an LRU cache and a token-bucket rate limiter in Java. ([Q17](coding.md#implement-lru-cache-o-1), [Q19](coding.md#design-code-rate-limiter-class))

### Cloud (AWS)

- [ ] I can explain how a workload gets AWS credentials without static keys. ([Q1](cloud-aws.md#aws-iam-spring-boot-service), [Q6](cloud-aws.md#apply-least-privilege-iam-blocking))
- [ ] I can draw a VPC with public/private subnets across two AZs and explain NAT vs VPC endpoints. ([Q2](cloud-aws.md#vpc-public-private-subnets-fit))
- [ ] I can justify ECS Fargate vs EKS vs Lambda for a given service. ([Q3](cloud-aws.md#ec2-ecs-eks-lambda-run), [Q11](cloud-aws.md#serverless-right-architecture-java-team))
- [ ] I can name the usual AWS cost surprises and how to find them. ([Q8](cloud-aws.md#drives-aws-bill-web-application), [S2](cloud-aws.md#aws-bill-doubled-month-nobody))

### REST API, observability & performance

- [ ] I can explain keyset vs offset pagination and why a stable sort order matters. ([S1](rest-api.md#list-endpoint-gets-slower-every))
- [ ] I can explain how `ETag`/`If-Match` prevents lost updates. ([S4](rest-api.md#concurrent-edits-silently-overwrite))
- [ ] I can explain how to evolve an API without breaking old mobile clients. ([S2](rest-api.md#renamed-field-breaks-mobile-app))
- [ ] I can explain SLO burn-rate alerts and why a global error-rate threshold misses incidents. ([S2](observability.md#alert-fires-after-users-notice))
- [ ] I can explain label cardinality and why IDs never go into metric labels. ([S3](observability.md#prometheus-oom-label-cardinality))
- [ ] I can explain coordinated omission and open vs closed load models. ([S2](performance-load-testing.md#load-test-green-prod-falls-over))
- [ ] I can find the real bottleneck when adding pods doesn't add throughput. ([S3](performance-load-testing.md#throughput-plateaus-cpu-idle))

### Kotlin

- [ ] I can explain why `@Transactional` needs the `kotlin-spring` plugin. ([S3](kotlin.md#transactional-ignored-final-class))
- [ ] I can explain why a JPA entity should not be a `data class`. ([S4](kotlin.md#data-class-entity-equals-breaks))
- [ ] I can explain why `runBlocking` doesn't belong on a request thread. ([S5](kotlin.md#runblocking-in-request-thread))

### Caching & Redis

- [ ] I can pick a `maxmemory-policy` for a cache vs a datastore and explain the `noeviction` trap. ([Q3](caching-redis.md#ttl-eviction-maxmemory-policy))
- [ ] I can list three defences against a cache stampede. ([Q5](caching-redis.md#cache-stampede-prevent))
- [ ] I can explain why `@CacheEvict` inside a transaction can leave a stale value. ([S1](caching-redis.md#stale-price-after-update))
- [ ] I can explain why a Redis lock is fine for efficiency but not for correctness. ([Q9](caching-redis.md#redis-lock-redlock-debate))
- [ ] I can explain why `KEYS *` stalls every client. ([S3](caching-redis.md#redis-blocked-keys-command))

### System design

- [ ] I can explain the steps of a system design interview and how I split the 45 minutes. ([Q1](system-design.md#steps-follow-system-design-interview))
- [ ] I can explain the CAP theorem with a concrete example. ([Q12](system-design.md#cap-theorem-concrete-distributed-system))
- [ ] I can explain how to choose a shard key, and what a bad one costs. ([Q24](system-design.md#database-shard-key-happens-bad))
- [ ] I can explain the cache write/invalidation strategies and their trade-offs. ([Q26](system-design.md#cache-aside-write-write-behind))
- [ ] I can explain a back-of-envelope capacity estimate on a whiteboard. ([Q2](system-design.md#back-envelope-numbers-know-heart))
- [ ] I can explain design a distributed rate limiter. ([Q43](system-design.md#design-rate-limiter-distributed-system))

### Leadership

- [ ] I can explain push back on a senior stakeholder's decision without damaging the relationship. ([Q3](leadership-behavioral.md#push-back-technical-decision-coming))
- [ ] I can explain handle a design review where two seniors strongly disagree. ([Q4](leadership-behavioral.md#tech-lead-handle-design-review))
- [ ] I can explain how to run incident command: roles, mitigate first, update cadence. ([Q8](leadership-behavioral.md#run-incident-command-during-major))
- [ ] I can explain how to write an RFC/ADR that gets decided. ([Q9](leadership-behavioral.md#write-rfc-adr-team-decides))
- [ ] I can explain how to run a fair, rubric-based interview loop. ([Q10](leadership-behavioral.md#structure-hiring-interviewing-decisions-consistent))
- [ ] I can explain how I delegate and how I say no with a trade-off. ([Q11](leadership-behavioral.md#delegate-well-say-damaging-relationship))
- [ ] I can explain a 30/60/90 onboarding plan for a new engineer. ([Q12](leadership-behavioral.md#onboard-new-engineer-productive-quickly))
- [ ] I can explain how I manage up with a weekly update. ([Q13](leadership-behavioral.md#manage-up-keeping-manager-informed))

### AI-assisted development

- [ ] I can explain the agentic loop and what `stop_reason` drives. ([Q1](claude-code.md#basic-agentic-loop-stop-reason))
- [ ] I can explain prompt engineering vs context engineering. ([Q2](claude-code.md#prompt-engineering-context-engineering-distinction))
- [ ] I can explain how prompt injection is defeated structurally, not by "ignore injected instructions". ([Q20](claude-code.md#prompt-injection-defeated-structurally-doesn))
- [ ] I can explain why hooks beat prompt instructions for hard rules. ([Q23](claude-code.md#hooks-better-place-hard-rules))
- [ ] I can explain how to evaluate an LLM-powered feature beyond "it seemed to work". ([Q27](claude-code.md#evaluate-llm-powered-application-quality))

## 3-day plan with timings

Use it when you have three days, not three weeks. Each block is a timer: stop when it rings.

| Day | Block | Time | What to do |
|-----|-------|------|------------|
| 1 | Warm-up | 30 min | Read the cheat-sheets of Java, Spring and SQL; mark weak items |
| 1 | Oral quiz | 90 min | Answer the Oral-quiz questions of Java, Spring, Persistence aloud (2–3 min each), score yourself |
| 1 | Live coding | 60 min | Two timed problems: one hashing/two-pointer ([Q4](coding.md#hash-map-turn-o-n2), [Q7](coding.md#two-pointer-sliding-window-patterns)), one design ([Q17](coding.md#implement-lru-cache-o-1)) |
| 2 | Design | 90 min | One full system design in 45 min ([Q1](system-design.md#steps-follow-system-design-interview)), then review against the answer |
| 2 | Platform | 60 min | DevOps/K8s, security and testing quizzes aloud |
| 2 | Behavioral | 60 min | Write 6 STAR stories from the [story bank](leadership-behavioral.md#star-story-bank) and say each in 2 minutes |
| 3 | Mock interview | 60 min | Full run with a friend or a recording: intro (B1), 2 technical, 1 coding, 1 behavioral, your questions (B26) |
| 3 | Fix weak spots | 60 min | Re-read only the items scored below 2 |
| 3 | Stop | rest | Check logistics, sleep early |

## How to score yourself

Answer each item aloud in 2–3 minutes, then grade it: **0** blank · **1** definition only · **2** plus an example · **3** plus trade-offs and a pitfall. Re-read the linked question for anything below 2, and retest after two weeks.
