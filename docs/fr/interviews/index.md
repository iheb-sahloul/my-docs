# Préparation d'entretien — Full Stack Java / React (Senior)

## Modules

| # | Module                                                         | Focus                                                                 |
|---|----------------------------------------------------------------|-----------------------------------------------------------------------|
| 1 | [`Java Core & JVM`](java-core-jvm.md)                       | records, sealed, virtual threads, concurrence, GC                     |
| 2 | [`Spring & Architecture`](spring-architecture.md)           | `@Transactional`, sécurité, hexagonal                                 |
| 3 | [`Persistance & SQL`](persistence-sql-postgres.md)          | MyBatis, SQL avancé, PostgreSQL, index                                |
| 4 | [`Messaging`](messaging-rabbitmq-kafka.md)                  | RabbitMQ vs Kafka, idempotence, sagas                                 |
| 5 | [`React & TypeScript`](react-typescript.md)                 | Hooks, état, performance, TS                                          |
| 6 | [`Full Stack & DevOps`](fullstack-devops-k8s.md)            | Conception d'API, Docker, K8s, observabilité                          |
| 7 | [`System Design & Leadership`](system-design-leadership.md) | Scalabilité, CAP, OWASP, mentorat                                     |
| 8 | [`Claude Code & Dev assisté par IA`](claude-code.md)        | Agentic coding, prompts/contexte, MCP, sécurité de l'IA, gouvernance  |

## Planning de révision suggéré (J-7)

| Jour | Matin                          | Après-midi                    |
|------|--------------------------------|-------------------------------|
| J-7  | Module 1 (Java Core)           | Module 2 (Spring)             |
| J-6  | Module 3 (SQL/Persistance)     | Révision Modules 1–2          |
| J-5  | Module 4 (Messaging)           | Module 5 (React)              |
| J-4  | Module 6 (DevOps/K8s)          | Révision Modules 3–4          |
| J-3  | Module 7 (System Design)       | Module 8 (Claude Code / IA)   |
| J-2  | Cheat-sheets de tous les modules | Mock interview (à voix haute) |
| J-1  | Points faibles identifiés      | Repos + relecture légère      |

## Légende de difficulté

- 🟢 **Fondamentaux** — attendus de tout développeur confirmé.
- 🟡 **Pièges seniors** — ce qui distingue un senior.
- 🔴 **Expert / Ouvert** — architecture, arbitrages, questions ouvertes.

## Structure d'un module

| Section                  | Contenu                                        |
|--------------------------|------------------------------------------------|
| 🟢 Fondamentaux          | attendus de tout développeur confirmé          |
| 🟡 Pièges seniors        | ce qui distingue un senior                     |
| 🔴 Expert / Ouvert       | architecture et questions ouvertes             |
| 🎯 Scénarios réels       | cas détaillés issus de la production           |
| 📌 Cheat-sheet           | Révision rapide la veille                      |

## Format des scénarios

Chaque scénario suit le même plan :

1. **Symptômes** — ce que l'on observe concrètement (métriques, erreurs, plaintes).
2. **Diagnostic** — étapes d'investigation, avec l'outil utilisé et l'hypothèse testée.
3. **Résolution** — mitigation immédiate, correction de fond, vérification.
4. **Prévention** — garde-fous durables (test, alerte, règle d'équipe).

### En entretien

Dérouler ce plan à voix haute montre une méthode d'ingénieur plutôt qu'une réponse apprise par cœur. Précisez toujours comment vous vérifiez que le correctif fonctionne.

## Conseils d'entretien

- **Structurez vos réponses** : contexte → options → décision → compromis.
- **Pensez à voix haute.**
- **Donnez des exemples concrets tirés de votre expérience.**
- **Admettez ce que vous ne savez pas**, puis raisonnez.
- **En system design**, clarifiez les exigences (charge, latence, cohérence) avant de dessiner.
- **En coding**, discutez de la complexité, des cas limites et des tests.

## Checklist finale

Une fois tous les modules parcourus, [`mock-interview.md`](mock-interview.md) est une checklist compacte
d'auto-évaluation pour la veille — parcourez-la et soyez honnête sur les points que vous ne savez pas
encore expliquer de mémoire, avec du code, sur le moment.
