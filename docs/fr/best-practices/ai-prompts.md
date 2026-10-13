# Prompts IA pour ingénieurs seniors

Des prompts à copier-coller pour obtenir des résultats de niveau production avec un assistant de code (Claude Code, Copilot Chat, etc.). Remplacez `<...>` par votre contexte.

## 🧱 Anatomie d'un bon prompt

### Donner contexte, tâche, contraintes, format et critère de fin

Dites au modèle ce qu'il ne peut pas deviner : la stack, l'objectif, les limites, le format attendu et comment vous jugerez le résultat.

**Pourquoi c'est une bonne pratique :** le modèle comble chaque trou avec la réponse la plus courante, pas la vôtre. L'avantage d'un senior, ce sont les contraintes (versions, conventions, SLA) : mettez-les dans le prompt et le résultat demande bien moins de reprise.

```text
// ⛔ vague
Ajoute du cache au service utilisateur.

// ✅ précis
Contexte : Spring Boot 3.3, Java 21, Postgres, Redis déjà configuré (voir CacheConfig.java).
Tâche : mettre en cache UserService.findById.
Contraintes : abstraction Spring Cache uniquement, TTL 5 min, invalidation à la modification/suppression, aucune nouvelle dépendance.
Sortie : un diff + un test prouvant l'invalidation.
Terminé quand : `./mvnw -q test -Dtest=UserServiceCacheTest` passe.
```

### Demander un plan avant le code

Pour tout ce qui touche plus d'un fichier, demandez un plan et relisez-le d'abord.

**Pourquoi c'est une bonne pratique :** un mauvais plan se corrige en une minute ; un mauvais diff de 600 lignes coûte une heure. Relire l'approche est le point de contrôle le moins cher.

```text
// ⛔
Migre notre authentification vers OAuth2.

// ✅
N'écris pas encore de code. Lis le package security et propose un plan de migration vers OAuth2 resource server :
fichiers à modifier, ordre des étapes, risques, ce qui peut être annulé indépendamment. Pose-moi des questions si quelque chose est ambigu.
```

## 🔍 Comprendre le code

### Tracer un flux de bout en bout

Demandez un chemin concret avec références de fichiers, pas un résumé.

**Pourquoi c'est une bonne pratique :** « explique ce module » donne une description générique. Un flux tracé avec `fichier:ligne` est vérifiable et révèle le vrai couplage.

```text
// ⛔
Explique le module commandes.

// ✅
Trace ce qui se passe de POST /orders jusqu'au commit en base et à la publication de l'événement.
Liste chaque classe/méthode dans l'ordre avec fichier:ligne, où la transaction commence/finit, et tout endroit
où une exception pourrait laisser des données incohérentes.
```

### Cartographier avant de modifier

Demandez le rayon d'impact avant de toucher au code partagé.

**Pourquoi c'est une bonne pratique :** la plupart des régressions viennent d'appelants qu'on ne connaissait pas.

```text
Avant de changer la signature de PricingService.compute(), liste tous les appelants (y compris réflexion, tests
et config), ce que chacun passe, et lesquels casseraient. Ne modifie rien.
```

## 🏛️ Conception & architecture

### Demander les compromis, puis une recommandation

Demandez des options avec leurs coûts, et forcez une décision.

**Pourquoi c'est une bonne pratique :** une seule réponse cache les alternatives ; une liste non classée vous renvoie la décision. Les contraintes rendent la recommandation pertinente.

```text
Nous devons envoyer des factures de façon asynchrone. Compare RabbitMQ, Kafka et un outbox Postgres pour notre cas :
~50 msg/s, at-least-once acceptable, équipe de 3, nous n'exploitons que Postgres.
Tableau : coût d'exploitation, ordre, rejeu, modes de défaillance. Puis recommande-en un en 3 phrases et rédige l'ADR
(contexte, décision, conséquences).
```

### Le faire vous contredire

Demandez les objections les plus fortes contre votre conception.

**Pourquoi c'est une bonne pratique :** les modèles sont complaisants par défaut ; un cadrage adversarial explicite fait ressortir les failles qu'un relecteur trouverait plus tard.

```text
Voici ma conception <coller>. Joue un staff engineer sceptique. Liste les 5 façons les plus probables dont elle échoue
en production (charge, cohérence, exploitation, sécurité), classées par probabilité x impact, et ce que tu changerais.
```

## 🛠️ Implémentation

### Pointer un exemple existant à imiter

Référencez un fichier qui suit déjà vos conventions.

**Pourquoi c'est une bonne pratique :** « suis le style du code » n'est pas mesurable ; « imite `OrderController` » est concret et évite que le modèle invente de nouveaux patterns ou dépendances.

```text
// ⛔
Écris un contrôleur pour les factures.

// ✅
Ajoute InvoiceController en imitant OrderController (gestion d'erreurs, mapping DTO, validation, @PreAuthorize).
Réutilise ApiError et les mappers MapStruct existants. Aucune nouvelle dépendance. Ajoute un @WebMvcTest comme OrderControllerTest.
```

### Piloter par les tests

Donnez d'abord le test qui échoue, puis demandez l'implémentation minimale.

**Pourquoi c'est une bonne pratique :** le test est une spec exécutable ; le modèle peut itérer jusqu'au vert au lieu de deviner.

```text
Écris des tests en échec pour : une remise ne dépasse jamais 30 %, le cumul de coupons est refusé, les coupons expirés sont ignorés.
Lance-les, confirme qu'ils échouent pour la bonne raison. Puis implémente le minimum pour les faire passer et lance tout le module.
```

## 🐞 Débogage

### Fournir les preuves, demander des hypothèses, puis la cause racine

Collez la stack trace, les étapes de reproduction, le changement récent et ce que vous avez déjà écarté.

**Pourquoi c'est une bonne pratique :** avec le seul symptôme, le modèle corrige le symptôme. Des preuves et des hypothèses classées mènent à un correctif à la cause.

```text
// ⛔
Mon app lève une NPE, corrige.

// ✅
Stack trace : <coller>. Uniquement sous charge, depuis le commit <sha> (ajout d'un enrichissement asynchrone).
Déjà écarté : lignes null en base. Donne 3 hypothèses classées avec comment confirmer chacune (log, test, point d'arrêt).
Quand j'en confirme une, corrige la cause racine, pas seulement le test de null, et vérifie les autres appelants.
```

## 🔎 Revue de code & refactoring

### Relire avec un périmètre et un format

Limitez ce qu'il faut chercher et comment le rapporter.

**Pourquoi c'est une bonne pratique :** « relis ça » renvoie des remarques de style. Un périmètre étroit et un tri par gravité renvoient les quelques points qui comptent.

```text
Relis ce diff pour la justesse, la concurrence et la sécurité uniquement (pas de style). 7 remarques max, par gravité,
chacune avec fichier:ligne, pourquoi c'est faux, et un correctif. S'il n'y a rien, dis-le.
<diff>...</diff>
```

### Refactorer avec un filet de sécurité

Exigez des tests verts et aucun changement de comportement.

**Pourquoi c'est une bonne pratique :** un refactoring sans filet est une réécriture déguisée.

```text
Refactore OrderService.process() (300 lignes) en méthodes/collaborateurs plus petits. Le comportement ne doit pas changer :
ajoute d'abord des tests de caractérisation du comportement actuel, lance-les, puis refactore par petites étapes en
relançant les tests à chaque fois. Aucun changement d'API publique.
```

## 🧪 Tests

### Demander les cas limites, pas seulement le cas nominal

Listez les catégories à couvrir.

**Pourquoi c'est une bonne pratique :** les tests par défaut du modèle reflètent l'implémentation ; nommer les catégories l'envoie aux limites où vivent les bugs.

```text
Pour parseAmount(String) : écris des tests JUnit 5 paramétrés couvrant null/vide, séparateurs selon la locale, négatifs,
dépassement, arrondi (HALF_EVEN), chiffres unicode. Utilise AssertJ. Explique toute hypothèse de comportement.
```

### Diagnostiquer les tests instables

Donnez les logs d'échec et la fréquence.

```text
Ce test échoue ~1 run CI sur 15 : <coller test + log>. Liste les causes possibles (état partagé, temps, ordre,
asynchrone), quelles preuves les distinguent, puis propose le correctif qui supprime la cause plutôt que d'ajouter des retries.
```

**Pourquoi c'est une bonne pratique :** les retries masquent le non-déterminisme ; une cause nommée le supprime.

## 🗄️ SQL, JPA & performance

### Apporter le plan d'exécution

Collez l'`EXPLAIN (ANALYZE, BUFFERS)` et la taille des tables.

**Pourquoi c'est une bonne pratique :** un conseil de performance sans données est du folklore. Le plan montre le vrai goulot.

```text
Postgres 16. Requête et plan ci-dessous, orders contient 40 M de lignes. Explique où part le temps, propose des index
(avec le DDL exact et le coût en écriture) et toute réécriture. Ne propose rien qui change les résultats.
<requête> <sortie EXPLAIN ANALYZE>
```

### Traquer les N+1 et le lazy loading

```text
Voici le graphe d'entités JPA et la méthode de service. Identifie les N+1 selects et le lazy loading hors transaction.
Propose un correctif (fetch join, @EntityGraph ou projection DTO) avec les compromis, et un test utilisant les
statistiques Hibernate pour vérifier le nombre de requêtes.
```

**Pourquoi c'est une bonne pratique :** demander une assertion sur le nombre de requêtes rend le correctif démontrable et évite la régression.

## 🐳 DevOps & CI

### Relire l'infrastructure selon une checklist

```text
Relis ce Dockerfile et ce Deployment k8s pour la production : utilisateur non-root, digest d'image de base épinglé,
cache des couches, requests/limits, sondes liveness/readiness, arrêt propre, gestion des secrets.
Donne un tableau (problème, risque, correctif) puis les fichiers corrigés.
```

**Pourquoi c'est une bonne pratique :** une checklist explicite empêche le modèle de s'arrêter aux deux premiers problèmes évidents.

## 📝 Documentation & communication

### Générer depuis le diff, dans le format de votre équipe

```text
Rédige la description de PR à partir de ce diff : quoi et pourquoi (2-3 phrases), risques, comment tester, plan de déploiement/retour arrière.
Puis rédige l'entrée de runbook pour la nouvelle alerte (symptôme, dashboard, 3 premières vérifications, escalade).
```

**Pourquoi c'est une bonne pratique :** le modèle transforme bien des faits que vous avez déjà dans le format voulu ; les faits restent de votre responsabilité.

## ⚠️ Anti-patterns

- **Coller des secrets, tokens ou données clients.** Anonymisez ; considérez que les prompts quittent votre machine.
- **Accepter du code qu'on ne comprend pas.** Demandez « explique pourquoi c'est correct et ce qui peut casser » ; vous êtes responsable de ce que vous mergez.
- **Aucune étape de vérification.** Terminez toujours par « lance les tests/le linter et montre la sortie ».
- **Un seul prompt géant pour une grosse fonctionnalité.** Découpez : plan, puis tranche par tranche, en relisant chaque diff.
- **Corriger par répétition.** Si la troisième tentative échoue, reformulez le contexte ou repartez d'une session neuve.
- **Demander des faits invérifiables** (versions de bibliothèques, API). Pointez la doc ou le code source de votre dépôt.
