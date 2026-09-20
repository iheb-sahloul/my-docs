# Entretiens blancs

| Document | Contenu |
|---|---|
| **`mock-interview.md`** (ce fichier) | Checklist de préparation avant l'entretien |
| [`index.md`](index.md) | Vue d'ensemble des modules, planning de révision, format des scénarios |
| [`java-core-jvm.md`](java-core-jvm.md) | **Java Core & JVM** — records, sealed, virtual threads, concurrence, GC |
| [`spring-architecture.md`](spring-architecture.md) | **Spring & Architecture** — DI, `@Transactional`, sécurité, hexagonal, design patterns |
| [`persistence-sql-postgres.md`](persistence-sql-postgres.md) | **Persistance & SQL** — MyBatis, SQL avancé, PostgreSQL, index |
| [`messaging-rabbitmq-kafka.md`](messaging-rabbitmq-kafka.md) | **Messaging** — RabbitMQ vs Kafka, idempotence, sagas |
| [`react-typescript.md`](react-typescript.md) | **React & TypeScript** — hooks, état, performance, TS |
| [`fullstack-devops-k8s.md`](fullstack-devops-k8s.md) | **Full Stack & DevOps** — conception d'API, Docker, K8s, observabilité, git |
| [`system-design-leadership.md`](system-design-leadership.md) | **System Design & Leadership** — scalabilité, CAP, OWASP, mentorat |
| [`claude-code.md`](claude-code.md) | **Claude Code & Dev assisté par IA** — agentic coding, MCP, sécurité de l'IA |


## Checklist de préparation à l'entretien
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
