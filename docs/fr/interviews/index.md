# Préparation d'entretien — Full Stack Java / React (Senior)

## Modules

| # | Module                                                         | Focus                                                                 |
|---|----------------------------------------------------------------|-----------------------------------------------------------------------|
| 1 | [`Design Patterns`](design-patterns.md)                     | Catalogue GoF, quand (ne pas) utiliser un pattern, patterns tactiques DDD |
| 2 | [`Java Core & JVM`](java-core-jvm.md)                       | records, sealed, virtual threads, concurrence, GC                     |
| 3 | [`Spring & Architecture`](spring-architecture.md)           | `@Transactional`, sécurité, hexagonal                                 |
| 4 | [`Persistance & SQL`](persistence-sql-postgres.md)          | MyBatis, SQL avancé, PostgreSQL, index                                |
| 5 | [`React & TypeScript`](react-typescript.md)                 | Hooks, état, performance, TS                                          |
| 6 | [`Messaging`](messaging-rabbitmq-kafka.md)                  | RabbitMQ vs Kafka, idempotence, sagas                                 |
| 7 | [`Full Stack & DevOps`](fullstack-devops-k8s.md)            | Conception d'API, Docker, K8s, observabilité                          |
| 8 | [`System Design`](system-design.md)                       | Méthode d'entretien, ordres de grandeur, conceptions complètes avec diagrammes |
| 9 | [`Leadership & Comportemental (STAR)`](leadership-behavioral.md) | Feedback, conflits, parties prenantes, estimation, santé d'équipe     |
| 10 | [`Ingénierie IA & Claude Code`](claude-code.md)        | Agentic coding, prompts/contexte, MCP, sécurité de l'IA, gouvernance  |
| 11 | [`Tests`](testing.md) | Pyramide, doublures de test, Testcontainers, tests instables, tests de contrat, RTL/Playwright |
| 12 | [`Sécurité`](security.md) | OAuth2/OIDC, JWT, Spring Security, injection/XSS/CSRF/IDOR/SSRF, supply chain |
| 13 | [`Live coding`](coding.md) | Méthode, Big-O, patterns clés (hachage, fenêtres, BFS/DFS, tas, DP), pièges Java, take-homes |
| 14 | [`Cloud (AWS)`](cloud-aws.md) | IAM, VPC, ECS/EKS/Lambda, données & messaging managés, hébergement SPA, HA, coûts |
| 15 | [`Conception d'API REST`](rest-api.md) | Pagination, PUT vs PATCH, ETag, problem details, cache, évolution |
| 16 | [`Performance & tests de charge`](performance-load-testing.md) | k6/Gatling, percentiles, coordinated omission, méthode USE, capacité |
| 17 | [`Observabilité`](observability.md) | RED/USE, corrélation, cardinalité, échantillonnage, alertes de burn rate SLO |
| 18 | [`Kotlin`](kotlin.md) | Null safety, classes sealed/value, coroutines, plugins Spring + JPA, interop Java |
| 19 | [`Cache & Redis`](caching-redis.md) | Structures de données Redis, éviction, stampede, pièges de Spring Cache, verrous, Cluster |
| ✓ | [`Entretien blanc`](mock-interview.md)                      | Checklist de préparation pour la veille                               |

Les liens sélectionnés par sujet se trouvent dans **Ressources › [Pour aller plus loin](../resources/further-reading.md)**.

## Planning de révision suggéré (J-7)

| Jour | Matin                          | Après-midi                    |
|------|--------------------------------|-------------------------------|
| J-7  | Module 2 (Java Core)           | Module 3 (Spring)             |
| J-6  | Module 4 (SQL/Persistance)     | Module 11 (Tests) + révision Modules 2–3 |
| J-5  | Module 6 (Messaging)           | Module 5 (React)              |
| J-4  | Modules 7 + 14 (DevOps/K8s, Cloud) | Module 12 (Sécurité) + révision Modules 4–6 |
| J-3  | Modules 8–9 (System Design, Leadership & Comportemental) | Module 10 (Ingénierie IA) |
| J-2  | Module 1 (Design Patterns) + cheat-sheets | Module 13 (Live coding, 2 problèmes chronométrés) + mock interview (à voix haute) |
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
| 🗣️ Questions posées      | questions d'entretiens réels avec courtes réponses types (`R1`, `R2`…) : Java, Spring, SQL, Messaging, System Design, Cloud, Sécurité, DevOps |
| 🎤 Quiz oral             | dix questions à traiter à voix haute, auto-notées |
| 📌 Cheat-sheet           | Révision rapide la veille                      |

**Leadership & Comportemental** suit la même structure. Sa partie **Comportemental** reprend les mêmes niveaux mais sans scénarios : chaque question indique pourquoi le recruteur la pose, un exemple de réponse ⭐ STAR, et le piège à éviter. Une dernière section **📞 Entretien avec le recruteur** couvre les questions du premier appel (raison du départ, salaire, projet à cinq ans, approfondissement de projet, questions à poser).

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
- **En coding** ([module 13](coding.md)), discutez de la complexité, des cas limites et des tests.

## Checklist finale

Une fois tous les modules parcourus, [`mock-interview.md`](mock-interview.md) est une checklist compacte
d'auto-évaluation pour la veille — parcourez-la et soyez honnête sur les points que vous ne savez pas
encore expliquer de mémoire, avec du code, sur le moment.
