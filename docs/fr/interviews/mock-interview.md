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

- [ ] Je sais expliquer ce qu'est une closure périmée (stale closure) dans `useEffect`, et la corriger avec le tableau de dépendances. ([Q10](react-typescript.md))
- [ ] Je sais expliquer comment les `key` pilotent la réconciliation des listes, et ce qui casse avec des clés d'index. ([Q12](react-typescript.md))
- [ ] Je sais expliquer pourquoi `React.memo` ne fait parfois silencieusement rien. ([Q13](react-typescript.md))
- [ ] Je sais expliquer pourquoi copier une prop dans le state via `useEffect` est un anti-pattern, et quoi faire à la place. ([Q17](react-typescript.md))
- [ ] Je sais expliquer ce que les error boundaries interceptent et ce qu'elles n'interceptent pas. ([Q22](react-typescript.md))

### Messaging

- [ ] Je sais expliquer at-most-once vs at-least-once vs exactly-once, et pourquoi « exactly-once » exige des consumers idempotents. ([Q6](messaging-rabbitmq-kafka.md))
- [ ] Je sais expliquer la différence de fond RabbitMQ vs Kafka et choisir l'un des deux avec des arguments. ([Q8](messaging-rabbitmq-kafka.md))
- [ ] Je sais expliquer ce que fait un rebalance Kafka et pourquoi il peut provoquer des traitements en double. ([Q19](messaging-rabbitmq-kafka.md))
- [ ] Je sais expliquer ce qu'est une dead-letter queue et comment je traite un poison pill. ([Q23](messaging-rabbitmq-kafka.md))
- [ ] Je sais expliquer saga par orchestration vs chorégraphie avec un compromis concret. ([Q26](messaging-rabbitmq-kafka.md))
- [ ] Je sais expliquer le pattern outbox, et pourquoi les doubles écritures sont risquées. ([Q27](messaging-rabbitmq-kafka.md))

### Docker, Kubernetes & DevOps

- [ ] Je sais expliquer les premières commandes `kubectl`, dans l'ordre, pour un pod en échec. ([Q6](fullstack-devops-k8s.md))
- [ ] Je sais expliquer un conteneur qui sort avec le code 137, de bout en bout. ([Q17](fullstack-devops-k8s.md))
- [ ] Je sais expliquer les probes liveness vs readiness vs startup et ce qui arrive quand elles sont mal réglées. ([Q19](fullstack-devops-k8s.md))
- [ ] Je sais expliquer un rolling update avec `maxSurge`/`maxUnavailable` et l'arrêt gracieux. ([Q22](fullstack-devops-k8s.md))
- [ ] Je sais expliquer blue-green vs canary vs rolling, et quand utiliser chacun. ([Q28](fullstack-devops-k8s.md))
- [ ] Je sais expliquer comment les SLO et error budgets pilotent les décisions de release. ([Q35](fullstack-devops-k8s.md))

### API, sécurité & persistance (approfondissement)

- [ ] Je sais expliquer l'idempotence REST et pourquoi `POST` nécessite une clé d'idempotence. ([Q10](fullstack-devops-k8s.md))
- [ ] Je sais expliquer pourquoi CORS échoue dans le navigateur mais pas avec curl, et comment fonctionne le preflight. ([Q12](fullstack-devops-k8s.md))
- [ ] Je sais expliquer les compromis entre JWT dans `localStorage`, cookie `HttpOnly` et session serveur. ([Q13](fullstack-devops-k8s.md))
- [ ] Je sais expliquer lire la sortie d'`EXPLAIN ANALYZE` et trouver l'index manquant. ([Q24](persistence-sql-postgres.md))
- [ ] Je sais expliquer les niveaux d'isolation et l'anomalie que chacun empêche. ([Q25](persistence-sql-postgres.md))
- [ ] Je sais expliquer ajouter une colonne `NOT NULL` à une table de 50 M de lignes sans interruption. ([Q44](persistence-sql-postgres.md))
- [ ] Je sais expliquer ce que résolvent les virtual threads et leurs limites. ([Q33](java-core-jvm.md))
- [ ] Je sais expliquer choisir entre G1, ZGC et Shenandoah pour un service sensible à la latence. ([Q36](java-core-jvm.md))

### Tests

- [ ] Je sais expliquer mock vs stub vs fake, et ce que je ne mocke jamais. ([Q3](testing.md), [Q6](testing.md))
- [ ] Je sais expliquer pourquoi H2 est un piège pour les tests de repository et ce que j'utilise à la place. ([Q8](testing.md))
- [ ] Je sais expliquer pourquoi une suite de tests Spring devient lente et comment fonctionne le cache de contexte. ([Q9](testing.md))
- [ ] Je sais expliquer pourquoi la couverture est un mauvais objectif et ce qu'apporte le mutation testing. ([Q13](testing.md))
- [ ] Je sais expliquer le contract testing piloté par le consommateur et quand il remplace les tests E2E. ([Q19](testing.md))

### Sécurité

- [ ] Je sais expliquer OAuth2 vs OIDC et choisir le bon flux pour une SPA, un backend et un batch. ([Q3](security.md), [Q4](security.md))
- [ ] Je sais lister tout ce qu'il faut valider sur un JWT, et expliquer comment en révoquer un. ([Q10](security.md), [Q11](security.md))
- [ ] Je sais dérouler la filter chain de Spring Security et expliquer 401 vs 403. ([Q8](security.md))
- [ ] Je sais expliquer l'IDOR et le corriger dans la requête, pas seulement avec un contrôle de rôle. ([Q12](security.md))
- [ ] Je sais expliquer quand la protection CSRF est nécessaire et quand on peut la désactiver. ([Q7](security.md))

### Live coding

- [ ] Je suis clarifier → force brute → optimiser → tester à voix haute, sans me taire. ([Q1](coding.md), [S1](coding.md))
- [ ] Je sais donner la complexité de ma solution et choisir une complexité cible selon la taille de l'entrée. ([Q2](coding.md))
- [ ] Je reconnais les problèmes de hachage, fenêtre glissante, BFS/DFS, tas et DP. ([Q4](coding.md), [Q7](coding.md), [Q9](coding.md), [Q10](coding.md), [Q14](coding.md))
- [ ] Je sais coder un cache LRU et un rate limiter token bucket en Java. ([Q17](coding.md), [Q19](coding.md))

### Cloud (AWS)

- [ ] Je sais expliquer comment un workload obtient des identifiants AWS sans clés statiques. ([Q1](cloud-aws.md), [Q6](cloud-aws.md))
- [ ] Je sais dessiner un VPC avec sous-réseaux publics/privés sur deux AZ et expliquer NAT vs VPC endpoints. ([Q2](cloud-aws.md))
- [ ] Je sais justifier ECS Fargate vs EKS vs Lambda pour un service donné. ([Q3](cloud-aws.md), [Q11](cloud-aws.md))
- [ ] Je sais citer les surprises de coût AWS habituelles et comment les trouver. ([Q8](cloud-aws.md), [S2](cloud-aws.md))

### System design

- [ ] Je sais expliquer les étapes d'un entretien de system design et comment je répartis les 45 minutes. ([Q1](system-design.md))
- [ ] Je sais expliquer le théorème CAP avec un exemple concret. ([Q12](system-design.md))
- [ ] Je sais expliquer comment choisir une shard key, et ce que coûte un mauvais choix. ([Q24](system-design.md))
- [ ] Je sais expliquer les stratégies d'écriture/invalidation de cache et leurs compromis. ([Q26](system-design.md))
- [ ] Je sais expliquer une estimation de capacité « back-of-envelope » au tableau. ([Q2](system-design.md))
- [ ] Je sais expliquer concevoir un rate limiter distribué. ([Q43](system-design.md))

### Leadership

- [ ] Je sais expliquer contester la décision d'un stakeholder senior sans abîmer la relation. ([Q3](leadership-behavioral.md))
- [ ] Je sais expliquer gérer une revue de conception où deux seniors sont en fort désaccord. ([Q4](leadership-behavioral.md))
- [ ] Je sais expliquer comment mener la coordination d'un incident : rôles, atténuer d'abord, cadence de points. ([Q8](leadership-behavioral.md))
- [ ] Je sais expliquer comment rédiger une RFC/ADR qui aboutit à une décision. ([Q9](leadership-behavioral.md))
- [ ] Je sais expliquer comment mener un entretien équitable avec une grille. ([Q10](leadership-behavioral.md))
- [ ] Je sais expliquer comment je délègue et comment je dis non avec un compromis. ([Q11](leadership-behavioral.md))
- [ ] Je sais expliquer un plan d'onboarding 30/60/90 pour un nouvel ingénieur. ([Q12](leadership-behavioral.md))
- [ ] Je sais expliquer comment je gère ma relation avec mon manager via un point hebdo. ([Q13](leadership-behavioral.md))

### Dev assisté par IA

- [ ] Je sais expliquer la boucle agentique et ce que pilote `stop_reason`. ([Q1](claude-code.md))
- [ ] Je sais expliquer prompt engineering vs context engineering. ([Q2](claude-code.md))
- [ ] Je sais expliquer comment l'injection de prompt est neutralisée structurellement, pas par « ignore les instructions injectées ». ([Q20](claude-code.md))
- [ ] Je sais expliquer pourquoi les hooks valent mieux que des instructions de prompt pour les règles strictes. ([Q23](claude-code.md))
- [ ] Je sais expliquer comment évaluer une fonctionnalité LLM au-delà de « ça avait l'air de marcher ». ([Q27](claude-code.md))

## Comment te noter

Réponds à chaque point à voix haute en 2–3 minutes, puis note-toi : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège. Relis la question liée pour tout ce qui est sous 2, et retente après deux semaines.
