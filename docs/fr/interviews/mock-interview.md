# Entretiens blancs

Vue d'ensemble des modules et planning de révision : [`index.md`](index.md). Cette page est la checklist de préparation pour la veille. Pour la progression de carrière à long terme, voir la [grille d'auto-évaluation](../index.md#self-assessment-checklist).

## Checklist de préparation à l'entretien

### Java, Spring, SQL & patterns

- [ ] Je sais expliquer interface vs classe abstraite à partir d'une vraie décision de conception, pas seulement la définition de manuel.
- [ ] Je sais retracer ce qui se passe en interne lors d'un put/get dans une HashMap, et expliquer pourquoi un mauvais hashCode() est un vrai
bug de performance.
- [ ] Je sais expliquer ConcurrentModificationException et montrer le bon correctif, de mémoire, avec du code.
- [ ] Je sais nommer les quatre stratégies d'implémentation d'un Singleton thread-safe et expliquer pourquoi Bill Pugh / la classe
interne statique est préférée.
- [ ] Je sais expliquer la différence entre synchronized et volatile sans confondre exclusion mutuelle
et visibilité.
- [ ] Je sais expliquer l'analyse d'accessibilité (reachability), les GC Roots et au moins deux algorithmes de GC nommés.
- [ ] Je sais expliquer pourquoi l'injection par champ est plus difficile à tester que l'injection par constructeur.
- [ ] Je sais expliquer en détail pourquoi @Transactional échoue silencieusement lors d'une auto-invocation — et nommer les quatre correctifs.
- [ ] Je sais expliquer la différence entre flush() et commit().
- [ ] Je sais expliquer pourquoi les méthodes @Async perdent le contexte Spring Security.
- [ ] Je sais expliquer les quatre états d'une entité Hibernate avec un exemple d'usage pour chacun.
- [ ] Je sais expliquer le problème N+1 et au moins deux façons de le corriger.
- [ ] Je sais expliquer le verrouillage optimiste vs pessimiste en termes de contention, pas seulement de définition.
- [ ] Je sais dérouler un exemple de normalisation de la 1NF à la 3NF sur un tableau blanc.
- [ ] Je sais expliquer l'ordre d'exécution logique du SQL et pourquoi WHERE ne peut pas référencer un alias du SELECT.
- [ ] Je sais expliquer les cinq design patterns qui sous-tendent Spring lui-même, pas seulement lister des noms de patterns GoF.
- [ ] Je sais expliquer la vraie différence entre hachage, encodage et chiffrement — et pourquoi l'encodage n'est pas de la sécurité.
- [ ] Je sais expliquer pourquoi le Singleton est considéré comme un anti-pattern par de nombreux seniors, bien qu'il soit facile à implémenter correctement.

### React & TypeScript

- [ ] Je sais expliquer ce qu'est une closure périmée (stale closure) dans `useEffect`, et la corriger avec le tableau de dépendances. ([Q10](react-typescript.md#stale-closure-useeffect-dependency-array))
- [ ] Je sais expliquer comment les `key` pilotent la réconciliation des listes, et ce qui casse avec des clés d'index. ([Q12](react-typescript.md#react-re-render-keys-affect))
- [ ] Je sais expliquer pourquoi `React.memo` ne fait parfois silencieusement rien. ([Q13](react-typescript.md#react-memo-help-sometimes-silently))
- [ ] Je sais expliquer pourquoi copier une prop dans le state via `useEffect` est un anti-pattern, et quoi faire à la place. ([Q17](react-typescript.md#copying-prop-local-state-via))
- [ ] Je sais expliquer ce que les error boundaries interceptent et ce qu'elles n'interceptent pas. ([Q22](react-typescript.md#react-error-boundaries-catch-explicitly))

### Messaging

- [ ] Je sais expliquer at-most-once vs at-least-once vs exactly-once, et pourquoi « exactly-once » exige des consumers idempotents. ([Q6](messaging-rabbitmq-kafka.md#most-once-least-once-exactly))
- [ ] Je sais expliquer la différence de fond RabbitMQ vs Kafka et choisir l'un des deux avec des arguments. ([Q8](messaging-rabbitmq-kafka.md#core-architectural-rabbitmq-kafka-drive))
- [ ] Je sais expliquer ce que fait un rebalance Kafka et pourquoi il peut provoquer des traitements en double. ([Q19](messaging-rabbitmq-kafka.md#happens-during-kafka-consumer-group))
- [ ] Je sais expliquer ce qu'est une dead-letter queue et comment je traite un poison pill. ([Q23](messaging-rabbitmq-kafka.md#dead-letter-queue-production-system))
- [ ] Je sais expliquer saga par orchestration vs chorégraphie avec un compromis concret. ([Q26](messaging-rabbitmq-kafka.md#saga-pattern-orchestration-choreography-trade))
- [ ] Je sais expliquer le pattern outbox, et pourquoi les doubles écritures sont risquées. ([Q27](messaging-rabbitmq-kafka.md#outbox-pattern-problem-solve))

### Docker, Kubernetes & DevOps

- [ ] Je sais expliquer les premières commandes `kubectl`, dans l'ordre, pour un pod en échec. ([Q6](fullstack-devops-k8s.md#pod-isn-working-first-kubectl))
- [ ] Je sais expliquer un conteneur qui sort avec le code 137, de bout en bout. ([Q17](fullstack-devops-k8s.md#diagnosing-docker-container-exits-code))
- [ ] Je sais expliquer les probes liveness vs readiness vs startup et ce qui arrive quand elles sont mal réglées. ([Q19](fullstack-devops-k8s.md#kubernetes-liveness-readiness-startup-probes))
- [ ] Je sais expliquer un rolling update avec `maxSurge`/`maxUnavailable` et l'arrêt gracieux. ([Q22](fullstack-devops-k8s.md#kubernetes-rolling-update-maxsurge-maxunavailable))
- [ ] Je sais expliquer blue-green vs canary vs rolling, et quand utiliser chacun. ([Q28](fullstack-devops-k8s.md#compare-blue-green-canary-rolling))
- [ ] Je sais expliquer comment les SLO et error budgets pilotent les décisions de release. ([Q35](fullstack-devops-k8s.md#slos-error-budgets-drive-release))

### API, sécurité & persistance (approfondissement)

- [ ] Je sais expliquer l'idempotence REST et pourquoi `POST` nécessite une clé d'idempotence. ([Q10](fullstack-devops-k8s.md#idempotency-rest-api-post-need))
- [ ] Je sais expliquer pourquoi CORS échoue dans le navigateur mais pas avec curl, et comment fonctionne le preflight. ([Q12](fullstack-devops-k8s.md#browser-request-fail-cors-error))
- [ ] Je sais expliquer les compromis entre JWT dans `localStorage`, cookie `HttpOnly` et session serveur. ([Q13](fullstack-devops-k8s.md#jwt-localstorage-jwt-httponly-cookie))
- [ ] Je sais expliquer lire la sortie d'`EXPLAIN ANALYZE` et trouver l'index manquant. ([Q24](persistence-sql-postgres.md#read-analyze-output-diagnose-slow))
- [ ] Je sais expliquer les niveaux d'isolation et l'anomalie que chacun empêche. ([Q25](persistence-sql-postgres.md#name-transaction-isolation-levels-anomalies))
- [ ] Je sais expliquer ajouter une colonne `NOT NULL` à une table de 50 M de lignes sans interruption. ([Q44](persistence-sql-postgres.md#safely-add-null-column-50))
- [ ] Je sais expliquer ce que résolvent les virtual threads et leurs limites. ([Q33](java-core-jvm.md#problem-virtual-threads-project-loom))
- [ ] Je sais expliquer choisir entre G1, ZGC et Shenandoah pour un service sensible à la latence. ([Q36](java-core-jvm.md#choosing-g1-zgc-shenandoah-latency))

### Tests

- [ ] Je sais expliquer mock vs stub vs fake, et ce que je ne mocke jamais. ([Q3](testing.md#mock-stub-fake-spy-each), [Q6](testing.md#mockito-well-never-mock))
- [ ] Je sais expliquer pourquoi H2 est un piège pour les tests de repository et ce que j'utilise à la place. ([Q8](testing.md#h2-repository-tests))
- [ ] Je sais expliquer pourquoi une suite de tests Spring devient lente et comment fonctionne le cache de contexte. ([Q9](testing.md#spring-test-suite-slow-make))
- [ ] Je sais expliquer pourquoi la couverture est un mauvais objectif et ce qu'apporte le mutation testing. ([Q13](testing.md#80-code-coverage-good-target))
- [ ] Je sais expliquer le contract testing piloté par le consommateur et quand il remplace les tests E2E. ([Q19](testing.md#consumer-driven-contract-testing-worth))

### Sécurité

- [ ] Je sais expliquer OAuth2 vs OIDC et choisir le bon flux pour une SPA, un backend et un batch. ([Q3](security.md#oauth-2-0-openid-connect), [Q4](security.md#oauth2-flow-client))
- [ ] Je sais lister tout ce qu'il faut valider sur un JWT, et expliquer comment en révoquer un. ([Q10](security.md#exactly-validate-jwt-before-trusting), [Q11](security.md#revoke-jwt-refresh-tokens-fit))
- [ ] Je sais dérouler la filter chain de Spring Security et expliquer 401 vs 403. ([Q8](security.md#spring-security-filter-chain-process))
- [ ] Je sais expliquer l'IDOR et le corriger dans la requête, pas seulement avec un contrôle de rôle. ([Q12](security.md#idor-broken-object-level-authorization))
- [ ] Je sais expliquer quand la protection CSRF est nécessaire et quand on peut la désactiver. ([Q7](security.md#csrf-need-csrf-protection))

### Live coding

- [ ] Je suis clarifier → force brute → optimiser → tester à voix haute, sans me taire. ([Q1](coding.md#approach-live-coding-exercise), [S1](coding.md#stuck-halfway-problem-interviewer-silent))
- [ ] Je sais donner la complexité de ma solution et choisir une complexité cible selon la taille de l'entrée. ([Q2](coding.md#big-o-complexities-know-heart))
- [ ] Je reconnais les problèmes de hachage, fenêtre glissante, BFS/DFS, tas et DP. ([Q4](coding.md#hash-map-turn-o-n2), [Q7](coding.md#two-pointer-sliding-window-patterns), [Q9](coding.md#bfs-dfs-each-solve-number), [Q10](coding.md#heap-right-tool-solve-top), [Q14](coding.md#dynamic-programming-spot-dp-problem))
- [ ] Je sais coder un cache LRU et un rate limiter token bucket en Java. ([Q17](coding.md#implement-lru-cache-o-1), [Q19](coding.md#design-code-rate-limiter-class))

### Cloud (AWS)

- [ ] Je sais expliquer comment un workload obtient des identifiants AWS sans clés statiques. ([Q1](cloud-aws.md#aws-iam-spring-boot-service), [Q6](cloud-aws.md#apply-least-privilege-iam-blocking))
- [ ] Je sais dessiner un VPC avec sous-réseaux publics/privés sur deux AZ et expliquer NAT vs VPC endpoints. ([Q2](cloud-aws.md#vpc-public-private-subnets-fit))
- [ ] Je sais justifier ECS Fargate vs EKS vs Lambda pour un service donné. ([Q3](cloud-aws.md#ec2-ecs-eks-lambda-run), [Q11](cloud-aws.md#serverless-right-architecture-java-team))
- [ ] Je sais citer les surprises de coût AWS habituelles et comment les trouver. ([Q8](cloud-aws.md#drives-aws-bill-web-application), [S2](cloud-aws.md#aws-bill-doubled-month-nobody))

### API REST, observabilité & performance

- [ ] Je sais expliquer la pagination keyset vs offset et pourquoi un ordre de tri stable compte. ([S1](rest-api.md#list-endpoint-gets-slower-every))
- [ ] Je sais expliquer comment `ETag`/`If-Match` évite les mises à jour perdues. ([S4](rest-api.md#concurrent-edits-silently-overwrite))
- [ ] Je sais expliquer comment faire évoluer une API sans casser les anciens clients mobiles. ([S2](rest-api.md#renamed-field-breaks-mobile-app))
- [ ] Je sais expliquer les alertes de burn rate SLO et pourquoi un seuil global de taux d'erreur rate des incidents. ([S2](observability.md#alert-fires-after-users-notice))
- [ ] Je sais expliquer la cardinalité des labels et pourquoi les IDs ne vont jamais dans les labels de métriques. ([S3](observability.md#prometheus-oom-label-cardinality))
- [ ] Je sais expliquer la coordinated omission et les modèles de charge ouvert vs fermé. ([S2](performance-load-testing.md#load-test-green-prod-falls-over))
- [ ] Je sais trouver le vrai goulot quand ajouter des pods n'augmente pas le débit. ([S3](performance-load-testing.md#throughput-plateaus-cpu-idle))

### Kotlin

- [ ] Je sais expliquer pourquoi `@Transactional` exige le plugin `kotlin-spring`. ([S3](kotlin.md#transactional-ignored-final-class))
- [ ] Je sais expliquer pourquoi une entité JPA ne doit pas être une `data class`. ([S4](kotlin.md#data-class-entity-equals-breaks))
- [ ] Je sais expliquer pourquoi `runBlocking` n'a rien à faire sur un thread de requête. ([S5](kotlin.md#runblocking-in-request-thread))

### Cache & Redis

- [ ] Je sais choisir une `maxmemory-policy` pour un cache et pour un datastore, et expliquer le piège de `noeviction`. ([Q3](caching-redis.md#ttl-eviction-maxmemory-policy))
- [ ] Je sais citer trois défenses contre un cache stampede. ([Q5](caching-redis.md#cache-stampede-prevent))
- [ ] Je sais expliquer pourquoi `@CacheEvict` dans une transaction peut laisser une valeur périmée. ([S1](caching-redis.md#stale-price-after-update))
- [ ] Je sais expliquer pourquoi un verrou Redis convient pour l'efficacité mais pas pour la correction. ([Q9](caching-redis.md#redis-lock-redlock-debate))
- [ ] Je sais expliquer pourquoi `KEYS *` bloque tous les clients. ([S3](caching-redis.md#redis-blocked-keys-command))

### System design

- [ ] Je sais expliquer les étapes d'un entretien de system design et comment je répartis les 45 minutes. ([Q1](system-design.md#steps-follow-system-design-interview))
- [ ] Je sais expliquer le théorème CAP avec un exemple concret. ([Q12](system-design.md#cap-theorem-concrete-distributed-system))
- [ ] Je sais expliquer comment choisir une shard key, et ce que coûte un mauvais choix. ([Q24](system-design.md#database-shard-key-happens-bad))
- [ ] Je sais expliquer les stratégies d'écriture/invalidation de cache et leurs compromis. ([Q26](system-design.md#cache-aside-write-write-behind))
- [ ] Je sais expliquer une estimation de capacité « back-of-envelope » au tableau. ([Q2](system-design.md#back-envelope-numbers-know-heart))
- [ ] Je sais expliquer concevoir un rate limiter distribué. ([Q43](system-design.md#design-rate-limiter-distributed-system))

### Leadership

- [ ] Je sais expliquer contester la décision d'un stakeholder senior sans abîmer la relation. ([Q3](leadership-behavioral.md#push-back-technical-decision-coming))
- [ ] Je sais expliquer gérer une revue de conception où deux seniors sont en fort désaccord. ([Q4](leadership-behavioral.md#tech-lead-handle-design-review))
- [ ] Je sais expliquer comment mener la coordination d'un incident : rôles, atténuer d'abord, cadence de points. ([Q8](leadership-behavioral.md#run-incident-command-during-major))
- [ ] Je sais expliquer comment rédiger une RFC/ADR qui aboutit à une décision. ([Q9](leadership-behavioral.md#write-rfc-adr-team-decides))
- [ ] Je sais expliquer comment mener un entretien équitable avec une grille. ([Q10](leadership-behavioral.md#structure-hiring-interviewing-decisions-consistent))
- [ ] Je sais expliquer comment je délègue et comment je dis non avec un compromis. ([Q11](leadership-behavioral.md#delegate-well-say-damaging-relationship))
- [ ] Je sais expliquer un plan d'onboarding 30/60/90 pour un nouvel ingénieur. ([Q12](leadership-behavioral.md#onboard-new-engineer-productive-quickly))
- [ ] Je sais expliquer comment je gère ma relation avec mon manager via un point hebdo. ([Q13](leadership-behavioral.md#manage-up-keeping-manager-informed))

### Dev assisté par IA

- [ ] Je sais expliquer la boucle agentique et ce que pilote `stop_reason`. ([Q1](claude-code.md#basic-agentic-loop-stop-reason))
- [ ] Je sais expliquer prompt engineering vs context engineering. ([Q2](claude-code.md#prompt-engineering-context-engineering-distinction))
- [ ] Je sais expliquer comment l'injection de prompt est neutralisée structurellement, pas par « ignore les instructions injectées ». ([Q20](claude-code.md#prompt-injection-defeated-structurally-doesn))
- [ ] Je sais expliquer pourquoi les hooks valent mieux que des instructions de prompt pour les règles strictes. ([Q23](claude-code.md#hooks-better-place-hard-rules))
- [ ] Je sais expliquer comment évaluer une fonctionnalité LLM au-delà de « ça avait l'air de marcher ». ([Q27](claude-code.md#evaluate-llm-powered-application-quality))

## Plan sur 3 jours avec durées

À utiliser quand tu as trois jours, pas trois semaines. Chaque bloc est un minuteur : arrête-toi quand il sonne.

| Jour | Bloc | Durée | À faire |
|------|------|-------|---------|
| 1 | Échauffement | 30 min | Relire les cheat-sheets Java, Spring et SQL ; repérer les points faibles |
| 1 | Quiz oral | 90 min | Répondre à voix haute aux quiz Java, Spring, Persistance (2–3 min chacun), te noter |
| 1 | Live coding | 60 min | Deux problèmes chronométrés : un hachage/two-pointer ([Q4](coding.md#hash-map-turn-o-n2), [Q7](coding.md#two-pointer-sliding-window-patterns)), un de conception ([Q17](coding.md#implement-lru-cache-o-1)) |
| 2 | Conception | 90 min | Un system design complet en 45 min ([Q1](system-design.md#steps-follow-system-design-interview)), puis comparaison avec la réponse |
| 2 | Plateforme | 60 min | Quiz DevOps/K8s, sécurité et tests à voix haute |
| 2 | Comportemental | 60 min | Écrire 6 histoires STAR depuis la [banque d'histoires](leadership-behavioral.md#banque-histoires-star) et dire chacune en 2 minutes |
| 3 | Entretien blanc | 60 min | Passage complet avec un ami ou un enregistrement : présentation (B1), 2 techniques, 1 coding, 1 comportemental, tes questions (B26) |
| 3 | Points faibles | 60 min | Relire seulement les points notés sous 2 |
| 3 | Stop | repos | Vérifier la logistique, dormir tôt |

## Comment te noter

Réponds à chaque point à voix haute en 2–3 minutes, puis note-toi : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Relis la question liée pour tout ce qui est sous 2, et retente après deux semaines.
