# Mes Docs

Ma documentation technique personnelle : notes et références auxquelles je veux revenir.

## Roadmap — Ingénieur Senior Java / React → Tech Lead

Une carte détaillée de ce qu'il faut maîtriser pour devenir ingénieur full-stack Java / React senior et
évoluer vers des rôles de tech lead. Elle couvre le code, les données, le messaging, le frontend, le DevOps,
la sécurité, l'architecture, le system design, le leadership et l'outillage, avec des liens vers les pages
détaillées de ce site.

## Comment utiliser cette roadmap

| Marqueur | Niveau           | Signification                                                                  |
|----------|------------------|--------------------------------------------------------------------------------|
| 🟢       | **Confirmé → Senior** | Attendu de tout bon développeur. Des lacunes ici bloquent tout le reste.  |
| 🟡       | **Senior**       | Ce qui distingue un senior : profondeur, compromis, expérience de la production. |
| 🔴       | **Tech Lead**    | Périmètre multi-équipes, architecture, décisions, humain.                      |

- **La profondeur avant l'étendue.** Maîtrisez à fond un outil par catégorie, connaissez les alternatives par leur nom et leurs compromis.
- **Apprendre → construire → expliquer.** Un sujet est « acquis » quand vous l'avez utilisé sur un vrai projet *et* que vous savez l'expliquer à quelqu'un d'autre.
- **Cochez les cases** de la [grille d'auto-évaluation](#self-assessment-checklist) à la fin, et revenez-y tous les quelques mois.
- **La production est le meilleur professeur.** Portez-vous volontaire pour l'astreinte, les incidents, les migrations et les problèmes de performance.

## Vue d'ensemble

| Étape            | Périmètre                           | Impact attendu                                                           | Signes que vous êtes prêt pour l'étape suivante                                     |
|------------------|-------------------------------------|--------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| 🟢 Confirmé      | Une fonctionnalité, un composant    | Livre en autonomie des tâches bien définies, avec une bonne qualité      | A besoin de peu d'accompagnement, écrit des tests par défaut, débogue seul          |
| 🟡 Senior        | Un service, un module, une epic     | Conçoit et livre de bout en bout, porte la production, élève le niveau   | Les autres sollicitent votre review/avis, vous anticipez les problèmes, vous débloquez les gens |
| 🔴 Tech Lead     | Une équipe / un système de services | Fixe la direction technique, prend et communique les décisions, fait grandir les gens | L'équipe livre mieux *grâce à vous*, pas seulement *à travers vous* ; les parties prenantes font confiance à vos estimations |

> Un senior se mesure à la qualité de ce qu'il construit. Un tech lead se mesure à la qualité de
> ce que **l'équipe** construit.

---

## 1. Fondamentaux — informatique & principes

### Informatique

| Sujet                          | Niveau | À savoir                                                                           |
|--------------------------------|--------|------------------------------------------------------------------------------------|
| Structures de données          | 🟢     | Tableaux, listes, hash maps, arbres (BST, B-tree), tas, graphes, tries             |
| Algorithmes & complexité       | 🟢     | Big-O temps/espace, tri, recherche, BFS/DFS, two pointers, sliding window, bases de la DP |
| Réseau                         | 🟢     | TCP vs UDP, DNS, HTTP/1.1 vs HTTP/2 vs HTTP/3, handshake TLS, cookies, CORS        |
| Systèmes d'exploitation        | 🟡     | Processus vs threads, changement de contexte, mémoire (pile/tas, mémoire virtuelle), descripteurs de fichiers, modèles d'I/O |
| Bases des systèmes distribués  | 🟡     | Ordres de grandeur de latence, horloges, pannes partielles, consensus (Raft) au niveau conceptuel |

### Principes d'ingénierie

| Principe                           | Niveau | Idée clé                                                                  |
|------------------------------------|--------|---------------------------------------------------------------------------|
| SOLID                              | 🟢     | Surtout SRP et DIP — ils conditionnent la testabilité et la modularité    |
| DRY / KISS / YAGNI                 | 🟢     | La duplication coûte moins cher que la mauvaise abstraction ; ne construisez pas « pour plus tard » |
| Composition plutôt qu'héritage     | 🟢     | Préférez de petits objets qui collaborent à des hiérarchies profondes     |
| Loi de Déméter, Tell-don't-ask     | 🟡     | Réduire le couplage, placer le comportement là où sont les données        |
| Clean Code & nommage               | 🟢     | Le code est bien plus souvent lu qu'écrit                                 |
| Refactoring                        | 🟡     | Petites étapes sûres et couvertes par des tests ; connaître le catalogue (extract, inline, move…) |
| Design patterns                    | 🟡     | Catalogue GoF — et surtout savoir **quand ne pas** en utiliser un         |
| Cohésion & couplage                | 🔴     | La vraie métrique derrière chaque décision d'architecture                 |
| Fail fast, moindre privilège, immutabilité par défaut | 🟡 | Des choix défensifs qui éliminent des familles entières de bugs |

**Pour aller plus loin :** [Design Patterns](interviews/design-patterns.md) · [Bonnes pratiques Java](best-practices/java.md)

**Pratique**

- Résolvez 2–3 problèmes d'algorithmique par semaine (LeetCode / Codewars) — en expliquant la complexité à voix haute.
- Prenez une classe legacy, couvrez-la de tests, puis refactorez-la pas à pas.

---

## 2. Parcours backend Java

### Langage & API de base

| Sujet                        | Niveau | À savoir                                                                                       |
|------------------------------|--------|------------------------------------------------------------------------------------------------|
| Java moderne (17 → 21 → 25)  | 🟢     | Records, sealed types, pattern matching (`switch`, `instanceof`, record patterns), text blocks, `var` |
| Collections                  | 🟢     | Implémentations de `List`/`Set`/`Map`, complexité, contrat `equals`/`hashCode`, collections immuables |
| Streams & style fonctionnel  | 🟢     | Lambdas, method refs, collectors, `Optional` bien utilisé, quand une boucle est plus claire    |
| Génériques                   | 🟡     | Types bornés, wildcards (PECS), effacement de type                                             |
| Exceptions                   | 🟢     | Checked vs unchecked, traduction d'exceptions, ne jamais les avaler                            |
| Concurrence                  | 🟡     | Java Memory Model, `happens-before`, `volatile`, verrous, `java.util.concurrent`, `CompletableFuture`, dimensionnement des pools de threads |
| Virtual threads & structured concurrency | 🟡 | Modèle Loom, pinning, quand ils aident (I/O-bound) et quand non                     |
| Internes de la JVM           | 🟡     | Heap/stack/metaspace, chargement de classes, JIT, GC (G1, ZGC, Shenandoah) et bases du tuning  |
| Profilage & diagnostic       | 🔴     | JFR, JDK Mission Control, async-profiler, heap dumps, thread dumps, `jcmd`                     |

### Build & tests

| Sujet                         | Niveau | À savoir                                                                  |
|-------------------------------|--------|---------------------------------------------------------------------------|
| Maven / Gradle                | 🟢     | Cycle de vie, gestion des dépendances, BOMs, builds multi-modules, plugins |
| Tests unitaires               | 🟢     | JUnit 5, AssertJ, Mockito — tester le comportement, pas l'implémentation  |
| Tests d'intégration           | 🟡     | Testcontainers, slices `@SpringBootTest` (`@WebMvcTest`, `@DataJpaTest`)  |
| Tests d'architecture          | 🟡     | Règles ArchUnit pour faire respecter les couches et les dépendances       |
| Tests de contrat              | 🔴     | Spring Cloud Contract / Pact entre services                               |
| Mutation testing              | 🔴     | PIT pour mesurer la *qualité* des tests, pas seulement la couverture      |
| TDD                           | 🟡     | Red → green → refactor ; savoir quand c'est rentable                      |

### Écosystème Spring

| Sujet                         | Niveau | À savoir                                                                      |
|-------------------------------|--------|-------------------------------------------------------------------------------|
| Spring Core                   | 🟢     | IoC/DI, scopes et cycle de vie des beans, configuration, profils              |
| Spring Boot                   | 🟢     | Auto-configuration, starters, configuration externalisée, Actuator            |
| Proxies & AOP                 | 🟡     | Proxies JDK vs CGLIB, piège de l'auto-invocation                              |
| `@Transactional`              | 🟡     | Propagation, isolation, règles de rollback, là où les transactions **ne s'appliquent pas** |
| Spring Data JPA / Hibernate   | 🟡     | Cycle de vie des entités, N+1, stratégies de fetch, dirty checking, verrouillage optimiste/pessimiste |
| Spring Security               | 🟡     | Filter chain, resource server OAuth2, login OIDC, JWT, sécurité au niveau méthode |
| Spring MVC vs WebFlux         | 🟡     | Bloquant vs réactif, et pourquoi les virtual threads ont changé le compromis  |
| Validation & gestion d'erreurs | 🟢    | Bean Validation, `@ControllerAdvice`, Problem Details (RFC 9457)              |
| Spring Cloud / résilience     | 🔴     | Config, gateway, Resilience4j (circuit breaker, retry, bulkhead)              |

**Pour aller plus loin :** [Java Core & JVM](interviews/java-core-jvm.md) · [Spring & Architecture](interviews/spring-architecture.md) ·
[Notes Java](notes/java.md) · [Bonnes pratiques Java](best-practices/java.md) · [Bonnes pratiques Spring Boot](best-practices/spring-boot.md) ·
[Tests](interviews/testing.md) · [Bonnes pratiques de tests](best-practices/testing.md) · [Live coding](interviews/coding.md)

**Pratique**

- Construisez un service Spring Boot avec des couches propres, une pyramide de tests complète et Testcontainers.
- Reproduisez un problème N+1 et un bug d'auto-invocation `@Transactional`, puis corrigez-les.
- Profilez un endpoint lent avec JFR / async-profiler et notez ce que vous avez trouvé.

---

## 3. Données & persistance

| Sujet                          | Niveau | À savoir                                                                    |
|--------------------------------|--------|-----------------------------------------------------------------------------|
| SQL                            | 🟢     | Jointures, agrégation, sous-requêtes, CTEs, fonctions de fenêtrage          |
| Modélisation des données       | 🟢     | Normalisation (et quand dénormaliser), contraintes, clés                    |
| Index                          | 🟡     | B-tree vs hash/GIN/GiST, ordre des index composites, index couvrants, `EXPLAIN ANALYZE` |
| Transactions                   | 🟡     | ACID, niveaux d'isolation, anomalies (dirty/non-repeatable/phantom reads), MVCC, deadlocks |
| Spécificités PostgreSQL        | 🟡     | JSONB, partitionnement, `VACUUM`, pool de connexions (HikariCP, PgBouncer)  |
| Migrations de schéma           | 🟢     | Flyway / Liquibase, migrations rétrocompatibles (expand/contract)           |
| ORM vs mappers SQL             | 🟡     | JPA vs MyBatis vs jOOQ — choisir selon le cas d'usage                       |
| Familles NoSQL                 | 🟡     | Document (MongoDB), clé-valeur (Redis), orienté colonnes (Cassandra), recherche (Elasticsearch) — quand chacun convient |
| Cache                          | 🟡     | Cache-aside, write-through, TTL, invalidation, protection contre le stampede |
| Réplication & sharding         | 🔴     | Réplicas en lecture, lag de réplication, clés de partitionnement, rééquilibrage |

**Pour aller plus loin :** [Persistance & SQL](interviews/persistence-sql-postgres.md)

**Pratique**

- Prenez une requête lente, lisez son plan, ajoutez le bon index, mesurez avant/après.
- Renommez une colonne sans interruption de service avec des migrations expand/contract.

---

## 4. Messaging, intégration & API

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Conception d'API REST          | 🟢     | Ressources, sémantique HTTP, codes de statut, pagination, filtrage, méthodes idempotentes |
| Contrats d'API                 | 🟢     | OpenAPI, contract-first vs code-first, stratégies de versioning               |
| REST vs gRPC vs GraphQL        | 🟡     | Compromis : couplage, performance, outillage, cache                           |
| Kafka vs RabbitMQ              | 🟡     | Log vs file, partitions, consumer groups, ordre, rétention                    |
| Sémantiques de livraison       | 🟡     | At-most / at-least / exactly-once, et pourquoi les consommateurs idempotents comptent |
| Transactional outbox & CDC     | 🔴     | Éviter les doubles écritures ; Debezium                                       |
| Sagas                          | 🔴     | Orchestration vs chorégraphie, actions de compensation                        |
| Évolution de schéma            | 🔴     | Avro/Protobuf, Schema Registry, compatibilité ascendante/descendante          |
| Webhooks, retries, DLQs        | 🟡     | Backoff exponentiel avec jitter, poison messages, rejeu                       |

**Pour aller plus loin :** [Messaging](interviews/messaging-rabbitmq-kafka.md) · [Bonnes pratiques REST](best-practices/rest-api.md) · [Bonnes pratiques Messaging](best-practices/messaging.md) · [Notes Kafka & RabbitMQ](notes/messaging.md)

**Pratique**

- Implémentez le pattern outbox entre un service Spring et Kafka, avec un consommateur idempotent.
- Concevez et documentez une API publique versionnée avec OpenAPI.

---

## 5. Parcours frontend React

### JavaScript & TypeScript

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Fondamentaux JS                | 🟢     | Portée, closures, `this`, prototypes, event loop, promesses, `async/await`    |
| JS moderne                     | 🟢     | Modules ES, déstructuration, spread, optional chaining, patterns d'immutabilité |
| TypeScript                     | 🟢     | Types vs interfaces, unions, narrowing, génériques                            |
| TypeScript avancé              | 🟡     | Utility & mapped types, types conditionnels, `satisfies`, unions discriminées, mode strict |
| Navigateur                     | 🟡     | DOM, pipeline de rendu, stockage, fetch, Web APIs, service workers            |

### React

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Composants & hooks             | 🟢     | `useState`, `useEffect`, `useRef`, `useContext`, hooks personnalisés, règles des hooks |
| Modèle de rendu                | 🟡     | Réconciliation, keys, quand et pourquoi les composants se re-rendent          |
| Performance                    | 🟡     | `memo`, `useMemo`, `useCallback` (et quand ils sont inutiles), React Compiler, virtualisation |
| Bien utiliser les effets       | 🟡     | « You might not need an effect », cleanup, race conditions                    |
| Gestion d'état                 | 🟡     | Local vs remonté vs global ; état serveur (TanStack Query) vs état client (Zustand / Redux Toolkit) |
| Formulaires & validation       | 🟢     | React Hook Form + Zod, contrôlé vs non contrôlé                               |
| Routing & chargement de données | 🟢    | React Router / TanStack Router, loaders, code splitting                       |
| Suspense, fonctionnalités concurrentes | 🟡 | `Suspense`, transitions, error boundaries                                 |
| Server Components & frameworks | 🔴     | Modèle RSC, Next.js, compromis SSR vs SSG vs CSR                              |
| Style                          | 🟢     | Fondamentaux CSS (flex, grid), CSS Modules / Tailwind, design systems         |
| Accessibilité                  | 🟡     | HTML sémantique, WCAG, ARIA, navigation au clavier, tests avec lecteur d'écran |
| Performance web                | 🟡     | Core Web Vitals (LCP, INP, CLS), analyse de bundle, lazy loading, optimisation des images |
| Tests                          | 🟢     | Vitest/Jest, React Testing Library, MSW, Playwright pour l'E2E                |
| Outillage                      | 🟢     | Vite, ESLint, Prettier, pnpm/npm, monorepos (Nx / Turborepo)                  |
| Sécurité frontend              | 🟡     | XSS, CSP, CSRF, stockage des tokens, hygiène des dépendances                  |
| Architecture frontend          | 🔴     | Dossiers par fonctionnalité, bibliothèque UI partagée, micro-frontends (et leur coût) |

**Pour aller plus loin :** [React & TypeScript](interviews/react-typescript.md) · [Bonnes pratiques React](best-practices/react-typescript.md) · Skill : `vercel-react-best-practices`

**Pratique**

- Construisez une app React + TS qui consomme votre API Spring, avec TanStack Query, formulaires, authentification et tests E2E.
- Auditez-la avec Lighthouse et un outil d'accessibilité ; corrigez les principaux problèmes.

---

## 6. DevOps & cloud

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Git                            | 🟢     | Branches, rebase vs merge, rebase interactif, bisect, trunk-based development, conventional commits |
| Linux & shell                  | 🟢     | Processus, permissions, commandes réseau, `grep`/`sed`/`awk`/`jq`/`curl`      |
| CI/CD                          | 🟢     | GitHub Actions / GitLab CI, étapes de pipeline, cache, quality gates (SonarQube), versioning des artefacts |
| Docker                         | 🟢     | Images vs conteneurs, builds multi-stage, cache des couches, images distroless/minimales, Compose |
| Kubernetes                     | 🟡     | Pods, Deployments, Services, Ingress, ConfigMaps/Secrets, probes, resources/limits, HPA |
| Helm / Kustomize               | 🟡     | Packaging, values par environnement, releases et rollbacks                    |
| Infrastructure as Code         | 🟡     | Terraform : state, modules, plan/apply, drift                                 |
| Fournisseur cloud (un seul en profondeur) | 🟡 | AWS / GCP / Azure : compute, bases managées, files, IAM, réseau (VPC), stockage |
| Stratégies de déploiement      | 🟡     | Rolling, blue/green, canary, feature flags, dark launches                     |
| Observabilité                  | 🟡     | Logs structurés, métriques, tracing distribué, OpenTelemetry, Prometheus/Grafana, correlation IDs |
| Fiabilité                      | 🔴     | SLI / SLO / error budgets, alertes sur les symptômes, capacity planning       |
| Gestion des incidents          | 🔴     | Astreinte, runbooks, postmortems sans reproche                                |
| GitOps & plateforme            | 🔴     | Argo CD / Flux, plateformes internes de développement, golden paths           |

**Pour aller plus loin :** [Full Stack & DevOps](interviews/fullstack-devops-k8s.md) · [Cloud (AWS)](interviews/cloud-aws.md) · [Notes Kubernetes](notes/kubernetes.md) ·
[Notes Docker](notes/docker.md) · [Git](notes/git.md) · [Linux](notes/linux.md) · [curl & jq](notes/http-curl-jq.md) · [Terraform](notes/terraform.md)

**Pratique**

- Conteneurisez votre app full-stack, déployez-la sur un cluster local (kind / k3d) avec Helm.
- Construisez un pipeline : lint → test → build de l'image → scan → déploiement en staging → smoke test.
- Ajoutez du tracing OpenTelemetry frontend → backend → BD, et un dashboard Grafana avec un SLO.

---

## 7. Sécurité

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| OWASP Top 10 (Web & API)       | 🟢     | Injection, contrôle d'accès défaillant, SSRF, mauvaise configuration de sécurité… |
| Authentification               | 🟡     | Sessions vs tokens, flux OAuth2 (Authorization Code + PKCE, Client Credentials), OIDC |
| Autorisation                   | 🟡     | RBAC vs ABAC, multi-tenancy, contrôles au niveau objet                        |
| Gestion des secrets            | 🟡     | Vault / gestionnaires de secrets cloud, jamais dans git, rotation             |
| Supply chain                   | 🟡     | Scan des dépendances (SCA), SBOM, scan d'images (Trivy), pinning & mises à jour (Renovate/Dependabot) |
| Transport & données            | 🟡     | TLS partout, chiffrement au repos, hachage des mots de passe (bcrypt/Argon2), gestion des données personnelles, RGPD |
| Threat modeling                | 🔴     | STRIDE, diagrammes de flux de données, revues de sécurité intégrées à la conception |
| SDLC sécurisé                  | 🔴     | SAST/DAST dans les pipelines, security champions, suivi des pentests          |

**Pour aller plus loin :** [Sécurité](interviews/security.md) · [Bonnes pratiques de sécurité](best-practices/security.md) · [System Design](interviews/system-design.md) (section OWASP)

---

## 8. Architecture

| Sujet                                   | Niveau | À savoir                                                             |
|-----------------------------------------|--------|----------------------------------------------------------------------|
| Architecture en couches                 | 🟢     | Controllers / services / repositories et leurs limites               |
| Hexagonale / Clean / Onion              | 🟡     | Ports & adapters, règle de dépendance, framework en périphérie       |
| Monolithe → monolithe modulaire → microservices | 🔴 | Quand découper (topologie d'équipe, scalabilité, indépendance des déploiements) et quand **ne pas** le faire |
| Domain-Driven Design — tactique         | 🟡     | Entités, value objects, agrégats, domain events, repositories        |
| Domain-Driven Design — stratégique      | 🔴     | Langage ubiquitaire, bounded contexts, context mapping, event storming |
| Architecture orientée événements        | 🔴     | Événements vs commandes, cohérence à terme, chorégraphie vs orchestration |
| CQRS & event sourcing                   | 🔴     | Bénéfices, coûts, et pourquoi la plupart des systèmes n'en ont pas besoin |
| Attributs de qualité                    | 🔴     | Scalabilité, disponibilité, maintenabilité, sécurité — et les compromis entre eux |
| Documenter l'architecture               | 🔴     | ADRs, modèle C4, arc42, diagrams as code (Mermaid, PlantUML, Structurizr) |
| Architecture évolutive                  | 🔴     | Fitness functions, strangler fig, anti-corruption layer              |
| Dette technique                         | 🔴     | L'identifier, la quantifier, la prioriser, négocier du temps pour elle |
| Team topologies & loi de Conway         | 🔴     | L'architecture reflète la structure de communication — concevez les deux |

**Pour aller plus loin :** [Spring & Architecture](interviews/spring-architecture.md) · [Design Patterns](interviews/design-patterns.md) ·
[System Design](interviews/system-design.md) · [Bonnes pratiques d'architecture](best-practices/architecture.md)

**Pratique**

- Refactorez un service en architecture hexagonale et faites-la respecter avec ArchUnit.
- Animez une session d'event storming sur un domaine que vous connaissez ; déduisez-en les bounded contexts.
- Rédigez 3 ADRs pour de vraies décisions de votre projet actuel.

---

## 9. System design

### Méthode

1. **Clarifier les exigences** — fonctionnelles, non fonctionnelles (charge, latence, disponibilité, cohérence, conformité).
2. **Estimer** — QPS, stockage, bande passante (calcul sur un coin de table).
3. **API** — principaux endpoints / événements.
4. **Modèle de données** — entités, patterns d'accès, choix du stockage.
5. **Conception haut niveau** — composants et flux.
6. **Approfondissement** — goulots d'étranglement, modes de défaillance, scalabilité de chaque composant.
7. **Compromis** — ce que vous avez choisi, ce à quoi vous avez renoncé, ce que vous feriez ensuite.

### Briques de base

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Scalabilité                    | 🟡     | Verticale vs horizontale, services stateless, load balancing (L4 vs L7)       |
| Couches de cache               | 🟡     | Navigateur, CDN, gateway, application, base de données                        |
| Distribution des données       | 🔴     | Réplication (leader/follower, multi-leader), sharding, consistent hashing     |
| Cohérence                      | 🔴     | CAP, PACELC, cohérence forte vs à terme, read-your-writes                     |
| Traitement asynchrone          | 🟡     | Files, back-pressure, traitement batch vs stream                              |
| Résilience                     | 🟡     | Timeouts, retries avec backoff + jitter, circuit breakers, bulkheads, dégradation gracieuse |
| Rate limiting                  | 🟡     | Token bucket, sliding window, où l'appliquer                                  |
| Recherche & analytique         | 🔴     | Index inversés, OLTP vs OLAP, pipelines de données                            |
| Multi-région                   | 🔴     | Actif-passif vs actif-actif, résidence des données, failover                  |

### Exercices classiques

- [ ] Raccourcisseur d'URL
- [ ] Rate limiter
- [ ] Fil d'actualité / timeline
- [ ] Système de chat / de notifications
- [ ] Stockage de fichiers (type Dropbox)
- [ ] Checkout & paiements e-commerce (idempotence, sagas)
- [ ] Système de réservation (concurrence, double réservation)
- [ ] Pipeline de métriques / de logs

**Pour aller plus loin :** [System Design](interviews/system-design.md)

---

## 10. Développement assisté par IA

| Sujet                          | Niveau | À savoir                                                                      |
|--------------------------------|--------|-------------------------------------------------------------------------------|
| Utiliser des agents de code    | 🟢     | Prompting efficace, fournir du contexte, itérer avec des tests                |
| Relire la production de l'IA   | 🟡     | La traiter comme la PR d'un junior : vérifier, tester, questionner            |
| Context engineering            | 🟡     | Instructions projet (`CLAUDE.md`), skills, serveurs MCP, hooks                |
| Adoption & gouvernance en équipe | 🔴   | Guidelines, sécurité (secrets, prompt injection), mesure de l'impact          |

**Pour aller plus loin :** [Ingénierie IA & Claude Code](interviews/claude-code.md)

---

## 11. Compétences de tech lead — la moitié hors code

### Leadership technique

| Compétence                     | Ce que ça donne en pratique                                                   |
|--------------------------------|-------------------------------------------------------------------------------|
| Vision technique               | Une direction écrite et partagée pour les 6–12 prochains mois, alignée avec le produit |
| Prise de décision              | RFCs / ADRs, portes à sens unique vs réversibles, disagree-and-commit, décider avec une information incomplète |
| Culture de la code review      | Reviews rapides, bienveillantes et ciblées ; conventions claires ; automatiser les détails |
| Standards de qualité           | Definition of done, stratégie de test, linting, gates de CI                   |
| Équilibrer dette et fonctionnalités | Rendre la dette visible, la relier à l'impact business, réserver de la capacité |
| Livraison                      | Découper les epics, identifier les risques tôt, livrer en fines tranches verticales |
| Estimation & planification     | Des fourchettes plutôt que des points, des hypothèses explicites, replanifier quand les faits changent |
| Responsabilité opérationnelle  | Santé de l'astreinte, pilotage des incidents, suivi des postmortems           |
| Mesure                         | Métriques DORA (lead time, fréquence de déploiement, taux d'échec des changements, MTTR) |

### Humain & communication

| Compétence                     | Ce que ça donne en pratique                                                   |
|--------------------------------|-------------------------------------------------------------------------------|
| Mentorat & coaching            | Pair programming, plans de progression, tâches stimulantes, questionner avant d'affirmer |
| Délégation                     | Confier des problèmes, pas des solutions ; ne pas prendre soi-même le chemin critique |
| Feedback                       | Précis, au bon moment, centré sur le comportement (modèle SBI)                |
| Communication avec les parties prenantes | Expliquer les compromis techniques en termes business ; dire non en proposant des alternatives |
| Écriture                       | Design docs clairs, points d'avancement, registres de décisions               |
| Animation                      | Mener des design reviews, des affinages, des rétrospectives qui débouchent sur des actions |
| Résolution de conflits         | Séparer les personnes des positions, s'aligner sur les objectifs, escalader proprement |
| Recrutement                    | Entretiens structurés, évaluation équitable, plans d'onboarding               |
| Sécurité psychologique         | Culture sans reproche, admettre ses propres erreurs, rendre sûr le fait de poser des questions |

**Pour aller plus loin :** [Leadership](interviews/leadership-behavioral.md)

**Pratique**

- Pilotez la conception d'une fonctionnalité de bout en bout : RFC → review → ADR → livraison → rétro.
- Mentorez une personne pendant 3 mois avec des objectifs explicites.
- Animez un postmortem sans reproche et suivez les actions jusqu'à leur terme.

---

## 12. Checklist des outils

| Catégorie             | Principal (à maîtriser)              | Alternatives (à connaître)                      |
|-----------------------|--------------------------------------|-------------------------------------------------|
| IDE                   | IntelliJ IDEA                        | VS Code, WebStorm                               |
| Build (backend)       | Maven                                | Gradle                                          |
| Build (frontend)      | Vite + pnpm                          | npm, Webpack, Turborepo / Nx                    |
| Tests (backend)       | JUnit 5, AssertJ, Mockito, Testcontainers | ArchUnit, PIT, WireMock, Pact              |
| Tests (frontend)      | Vitest, React Testing Library, Playwright | Jest, Cypress, MSW                         |
| Qualité du code       | SonarQube, ESLint, Prettier          | Checkstyle, SpotBugs, Error Prone               |
| Gestion de versions   | Git + GitHub / GitLab                | —                                               |
| CI/CD                 | GitHub Actions / GitLab CI           | Jenkins, Argo CD                                |
| Conteneurs & orchestration | Docker, Kubernetes, Helm        | Podman, Kustomize, kind / k3d                   |
| IaC                   | Terraform                            | Pulumi, CloudFormation                          |
| Observabilité         | OpenTelemetry, Prometheus, Grafana   | ELK / Loki, Jaeger / Tempo, Datadog             |
| Bases de données      | PostgreSQL, Redis                    | MongoDB, Elasticsearch                          |
| Messaging             | Kafka                                | RabbitMQ                                        |
| API                   | OpenAPI, Bruno / Postman, `curl`     | Insomnia, HTTPie                                |
| Diagrammes & docs     | Mermaid, Excalidraw, MkDocs          | PlantUML, Structurizr (C4), draw.io             |
| Profilage             | JFR / JMC, async-profiler            | VisualVM, Chrome DevTools, React Profiler       |
| IA                    | Claude Code                          | Autres assistants de code                       |

---

## 13. Calendrier suggéré

Un parcours réaliste en travaillant à temps plein. Adaptez-le à votre point de départ.

| Phase           | Focus                                                            | Jalon                                                           |
|-----------------|------------------------------------------------------------------|-----------------------------------------------------------------|
| **Mois 0–3**    | Combler les lacunes 🟢 : Java moderne, fondamentaux Spring, SQL, bases TS/React, Git, Docker | Une app full-stack testée (Spring + React) qui tourne dans Docker Compose |
| **Mois 3–6**    | JVM & concurrence, pièges JPA, performance React, CI/CD, stratégie de test | Pipeline avec quality gates ; app déployée sur Kubernetes avec Helm |
| **Mois 6–12**   | Messaging, observabilité, sécurité, hexagonale + DDD tactique, entraînement au system design | Fonctionnalité orientée événements avec outbox ; tracing + dashboard SLO ; 4 exercices de system design réalisés |
| **Mois 12–18**  | Architecture (DDD stratégique, ADRs, C4), approfondissement d'un fournisseur cloud, pilotage de fonctionnalités | A piloté une fonctionnalité de la RFC à la production ; a rédigé des ADRs ; a mentoré quelqu'un |
| **Mois 18–24**  | Compétences de tech lead : vision, planification, gestion des parties prenantes, pilotage des incidents | Porte la direction technique d'une équipe ; reconnu comme référent entre les équipes |

---

## 14. Lectures recommandées

| Domaine                   | Livres                                                                                             |
|---------------------------|----------------------------------------------------------------------------------------------------|
| Java                      | *Effective Java* (Bloch) · *Java Concurrency in Practice* (Goetz) · *Modern Java in Action*        |
| Artisanat du code         | *Clean Code* (Martin) · *Refactoring* (Fowler) · *The Pragmatic Programmer* · *Working Effectively with Legacy Code* (Feathers) |
| Tests                     | *Unit Testing: Principles, Practices, and Patterns* (Khorikov) · *Growing Object-Oriented Software, Guided by Tests* |
| Données & systèmes distribués | *Designing Data-Intensive Applications* (Kleppmann) · *Database Internals* (Petrov)           |
| Architecture              | *Fundamentals of Software Architecture* (Richards & Ford) · *Software Architecture: The Hard Parts* · *Building Microservices* (Newman) · *Clean Architecture* (Martin) · *Building Evolutionary Architectures* |
| DDD                       | *Domain-Driven Design* (Evans) · *Implementing DDD* (Vernon) · *Learning DDD* (Khononov)           |
| System design             | *System Design Interview* vol. 1 & 2 (Xu) · *Release It!* (Nygard)                                |
| DevOps & fiabilité        | *Accelerate* (Forsgren) · *The Phoenix Project* · *Site Reliability Engineering* (Google) · *Kubernetes in Action* |
| Frontend                  | *Learning TypeScript* · docs react.dev · *Refactoring UI* · web.dev (performance & accessibilité)  |
| Leadership                | *The Staff Engineer's Path* (Reilly) · *The Manager's Path* (Fournier) · *An Elegant Puzzle* (Larson) · *Team Topologies* · *Radical Candor* |

---

## Grille d'auto-évaluation {#self-assessment-checklist}

Cette grille suit votre niveau de carrière sur plusieurs mois. Pour être prêt la veille d'un entretien, utilisez la [checklist d'entretien blanc](interviews/mock-interview.md).

### 🟢 Confirmé → Senior

- [ ] Je sais expliquer `equals`/`hashCode`, la complexité des collections et les collectors de streams sans notes.
- [ ] J'écris des tests unitaires et d'intégration par défaut, y compris avec Testcontainers.
- [ ] Je sais lire un plan `EXPLAIN ANALYZE` et corriger un index manquant.
- [ ] Je sais quand un composant React se re-rend et comment éviter les rendus inutiles.
- [ ] Je sais écrire un Dockerfile avec un build multi-stage et un pipeline CI à partir de zéro.
- [ ] Je conçois des API REST avec une sémantique HTTP correcte, de la validation et un format d'erreur cohérent.
- [ ] J'utilise Git avec aisance : rebase, bisect, résolution de conflits.

### 🟡 Senior

- [ ] Je sais expliquer la propagation `@Transactional`, les pièges des proxies et le problème N+1 — et les corriger.
- [ ] Je sais diagnostiquer une fuite mémoire ou un problème de contention de threads avec les outils de la JVM.
- [ ] Je comprends les niveaux d'isolation et j'ai traité un bug de concurrence en production.
- [ ] Je choisis entre Kafka et RabbitMQ avec des arguments clairs, et je construis des consommateurs idempotents.
- [ ] J'ai déployé et débogué des services sur Kubernetes (probes, resources, logs, events).
- [ ] J'instrumente les services avec des métriques, des logs et des traces, et je définis des alertes pertinentes.
- [ ] Je sais appliquer les mitigations de l'OWASP Top 10 et implémenter correctement OAuth2/OIDC.
- [ ] Je structure le code en architecture hexagonale et avec les patterns tactiques DDD quand ils s'y prêtent.
- [ ] Je sais mener un entretien de system design de 45 minutes de bout en bout avec des compromis explicites.
- [ ] Mes code reviews améliorent le code *et* font progresser l'auteur.

### 🔴 Tech Lead

- [ ] J'ai rédigé des RFCs/ADRs que l'équipe a utilisés pour prendre des décisions.
- [ ] Je sais dessiner de mémoire les diagrammes C4 de contexte et de conteneurs de mon système.
- [ ] Je sais décider s'il faut découper un service — et argumenter *contre* les microservices quand c'est pertinent.
- [ ] J'ai piloté un incident et un postmortem sans reproche.
- [ ] J'ai défini des SLOs et utilisé les error budgets pour prioriser le travail.
- [ ] J'ai une roadmap technique écrite, alignée avec les objectifs produit.
- [ ] Je traduis les compromis techniques en impact business pour des interlocuteurs non techniques.
- [ ] Je mentore au moins un ingénieur avec des objectifs de progression explicites.
- [ ] Je suis la santé de la livraison (métriques DORA) et j'agis en conséquence.
- [ ] L'équipe prend de bonnes décisions quand je ne suis pas dans la pièce.
