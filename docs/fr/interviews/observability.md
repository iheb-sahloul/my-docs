# Observabilité

Au-delà des trois piliers : alerting basé sur les SLO, corrélation, cardinalité, échantillonnage et coût. Les piliers sont dans [Full Stack & DevOps](fullstack-devops-k8s.md#three-pillars-observability-each-one) et le « à quoi ressemble le bon » dans la [Q30](fullstack-devops-k8s.md#put-three-pillars-observability-practice) ; les règles dans [Bonnes pratiques › Observabilité](../best-practices/observability.md).

## 🟢 Fondamentaux

#### Q1. Quelle différence entre monitoring et observabilité ? {#monitoring-observability}
**Réponse :** Le monitoring vérifie des modes de panne connus avec des tableaux de bord et alertes prédéfinis. L'observabilité permet de poser de **nouvelles** questions sur des pannes inconnues à partir de la télémétrie émise (événements riches à forte cardinalité, traces, métriques). En pratique : logs structurés avec contexte, traces entre services et métriques pour les SLI, pour passer d'un symptôme à une cause sans déployer de nouveau code.

#### Q2. Que sont les méthodes RED et USE, et sur quelles métriques alertez-vous ? {#red-methods-metrics-alert}
**Réponse :** **RED** pour les services : Rate (débit), Errors, Duration (par endpoint). **USE** pour les ressources : Utilisation, Saturation, Erreurs. Alertez sur les **symptômes ressentis par les utilisateurs** (taux d'erreur, SLI de latence consommant le budget), pas sur chaque cause (CPU 80 %). Les causes vont sur des tableaux de bord pour le diagnostic.

## 🟡 Pièges seniors

#### Q3. Comment corrélez-vous logs, métriques et traces entre services ? {#correlate-logs-metrics-traces-across}
**Réponse :** Propagez un **contexte de trace** (W3C `traceparent`) à chaque saut, HTTP et messagerie ; mettez `traceId`/`spanId` dans chaque ligne de log via le MDC pour passer d'une recherche de logs à la trace et inversement. Utilisez les exemplars sur les métriques pour relier un bucket lent à une trace d'exemple. Avec Spring Boot 3, cela vient de Micrometer Tracing avec un pont OpenTelemetry.

**Exemple :**

```text
2026-10-13 10:02:11 INFO  traceId=4bf92f35 spanId=00f067aa  Payment captured id=981
```

#### Q4. Qu'est-ce que la cardinalité d'une métrique, et comment fait-elle exploser la facture de monitoring ? {#metric-cardinality-blow-up-monitoring}
**Réponse :** Chaque combinaison unique de valeurs de labels est une série temporelle distincte. Des labels comme `userId`, `orderId`, une URL complète ou un message d'exception multiplient les séries par millions, avec pression mémoire et coût. Gardez des labels bornés (gabarit d'endpoint, classe de statut, région) ; mettez le détail à forte cardinalité dans les logs et traces.

#### Q5. Échantillonnage de traces head-based vs tail-based : comment choisir ? {#head-based-tail-based-trace}
**Réponse :** Le head-based décide au début (par ex. 5 % des requêtes) : peu coûteux et simple mais peut perdre les traces intéressantes. Le tail-based décide après la fin de la trace dans un collecteur, en gardant toutes les erreurs et requêtes lentes plus un échantillon du reste : plus utile mais exige du buffering et plus de mémoire. Gardez toujours les traces en erreur ou à forte latence.

## 🔴 Expert / Ouvert

#### Q6. Comment concevez-vous un alerting basé sur les SLO avec des burn rates ? {#design-slo-based-alerting-burn}
**Réponse :** Définissez un SLI (par ex. part des requêtes sous 300 ms et hors 5xx) et un SLO (99,9 % sur 30 jours), ce qui donne un budget d'erreur. Alertez sur le **burn rate** : une fenêtre rapide (par ex. 14× sur 1 h) déclenche une page immédiate, une fenêtre lente (par ex. 2× sur 6 h) ouvre un ticket. Cela réduit le bruit des à-coups courts tout en attrapant les fuites lentes. Voir [Full Stack Q35](fullstack-devops-k8s.md#slos-error-budgets-drive-release) pour SLO et budgets d'erreur.

## 🎯 Scénarios réels

### S1. Des clients signalent des erreurs, mais tous les tableaux de bord sont verts {#customers-report-errors-but-all}
- **Symptômes :** Les tickets du support mentionnent des paiements échoués dans une région ; les tableaux de taux d'erreur et de CPU paraissent normaux.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Les moyennes masquent une panne partielle. Découpez le taux d'erreur par région, endpoint et version, puis suivez la trace d'une requête en échec jusqu'à la dépendance fautive.
- **Résolution :** Corrigez ou annulez la cause, puis ajoutez le SLI manquant (taux de succès par région) et une alerte de burn rate dessus.
- **Prévention :** Alertez sur des SLI orientés utilisateur avec des dimensions pertinentes, et lancez des sondes synthétiques par région.

</details>

### S2. Les utilisateurs se plaignent de paiements échoués 40 minutes avant la première alerte {#alert-fires-after-users-notice}
- **Symptômes :** La chronologie du post-mortem montre des tickets support à 14:05 et l'astreinte appelée à 14:45. L'alerte était `error_rate > 5% for 30m` sur toute l'API.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** L'alerte moyenne le checkout (faible volume, critique) avec des endpoints à fort volume en bonne santé : 30 % d'échecs sur le checkout sont dilués sous 5 %. La longue fenêtre `for:` ajoute 30 minutes.
- **Exemple :**

  ```promql
  # burn rate par SLO, fenêtre rapide : 2 % d'un budget de 30 jours en 1h
  sum(rate(http_requests_total{route="/checkout",code=~"5.."}[5m]))
    / sum(rate(http_requests_total{route="/checkout"}[5m])) > 14.4 * 0.001
  ```

- **Résolution :** Définissez un SLO par parcours critique (checkout, login), alertez sur le burn rate multi-fenêtres (rapide 1h/5m + lent 6h/30m) plutôt qu'un seuil global, et ajoutez une sonde synthétique qui fait un vrai checkout chaque minute.
- **Prévention :** Chaque post-mortem note le « temps de détection » et « qui a détecté » ; si ce sont les clients, une action sur l'alerting est obligatoire.

</details>

### S3. Prometheus redémarre en boucle en OOM après une release d'apparence anodine {#prometheus-oom-label-cardinality}
- **Symptômes :** Les dashboards sont vides, la mémoire de Prometheus passe de 6 Go à 40 Go en quelques heures après un déploiement ; `prometheus_tsdb_head_series` passe de 800k à 12M.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Un nouveau label porte une valeur non bornée : `userId`, un chemin brut avec des IDs (`/orders/8812`) ou un message d'exception. Chaque valeur distincte crée une nouvelle série.
- **Exemple :**

  ```promql
  topk(10, count by (__name__)({__name__=~".+"}))
  # puis, pour la métrique en tête :
  count(count by (uri) (http_server_requests_seconds_count))
  ```

- **Résolution :** Supprimez ou réécrivez le label fautif au scrape (`metric_relabel_configs` avec `labeldrop`), annulez ou corrigez l'instrumentation pour utiliser le template de route (`/orders/{id}`), puis redémarrez Prometheus sans les séries fautives.
- **Prévention :** Règle de revue : un label a un ensemble de valeurs borné ; les IDs vont dans les logs et les traces, pas dans les métriques. Ajoutez un `sample_limit` par job de scrape et une alerte sur la croissance des séries.

</details>

### S4. Les traces s'arrêtent au producteur Kafka, et personne ne sait pourquoi certaines commandes prennent 10 minutes de bout en bout {#trace-breaks-at-kafka-hop}
- **Symptômes :** Dans l'outil de tracing, la trace `POST /orders` se termine à `kafka.send` ; côté consommateur apparaissent des centaines de traces racines sans lien avec la requête.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Le contexte de trace n'est pas propagé dans les en-têtes du message : soit le producteur n'est pas instrumenté, soit un serializer/wrapper maison perd les en-têtes, soit le consommateur traite dans un pool de threads où le contexte se perd.
- **Exemple :**

  ```text
  en-têtes du record produit : traceparent: 00-4bf92f35...-00f067aa0ba902b7-01
  consommateur : extraire le contexte des en-têtes -> nouveau span lié (ou enfant)
  ```

- **Résolution :** Utilisez l'instrumentation OpenTelemetry Kafka (ou l'observation Spring Kafka) des deux côtés pour que `traceparent` voyage dans les en-têtes, propagez le contexte dans les threads d'exécuteur, et mesurez le temps en file (consommation − production) comme attribut/métrique.
- **Prévention :** Un test de contrat qui vérifie la présence de `traceparent` sur les messages produits, et un dashboard de latence de bout en bout séparant « en file » et « traitement ».

</details>

### S5. La facture de logs triple en un mois et la recherche devient trop lente pour servir pendant les incidents {#log-bill-explodes-debug-left-on}
- **Symptômes :** L'ingestion passe de 200 Go/jour à 1,5 To/jour ; l'essentiel est constitué de lignes `DEBUG` d'un seul service et de corps de requêtes/réponses complets.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Regroupez l'ingestion par service et par niveau. Causes typiques : un niveau `DEBUG` activé pour un incident et jamais remis, des payloads loggés dans une boucle, ou une boucle de retry qui logge une stack trace par tentative.
- **Résolution :** Remettez le niveau (l'`/actuator/loggers` de Spring Boot permet de le changer à chaud sans redéploiement, dans les deux sens), arrêtez de logger les corps (aussi un risque RGPD), une ligne par échec plutôt que par tentative, et une rétention par index (ex. 7 jours pour le debug, 30 pour l'audit).
- **Prévention :** Niveau `INFO` par défaut vérifié en revue de config, niveaux debug temporaires avec date d'expiration, quotas/alertes d'ingestion par service et échantillonnage des logs de succès à fort volume.

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q1. Quelle différence entre monitoring et observabilité ?
2. Q2. Que sont les méthodes RED et USE, et sur quelles métriques alertez-vous ?
3. Q3. Comment corrélez-vous logs, métriques et traces entre services ?
4. Q4. Qu'est-ce que la cardinalité d'une métrique, et comment fait-elle exploser la facture de monitoring ?
5. Q5. Échantillonnage de traces head-based vs tail-based : comment choisir ?
6. Q6. Comment concevez-vous un alerting basé sur les SLO avec des burn rates ?
7. S1. Des clients signalent des erreurs, mais tous les tableaux de bord sont verts

## 📌 Cheat-sheet

- **Monitoring vs observabilité** — pannes connues vs nouvelles questions. *Émettez du contexte riche, pas seulement des compteurs.*
- **RED / USE** — services : débit, erreurs, durée ; ressources : utilisation, saturation, erreurs. *Alertez sur les symptômes.*
- **Corrélation** — `traceparent` à chaque saut et `traceId` dans chaque ligne de log. *Les exemplars relient métriques et traces.*
- **Cardinalité** — labels bornés uniquement. *Jamais `userId` ni URL complète dans les métriques.*
- **Échantillonnage et SLO** — le tail-based garde erreurs/lenteurs ; alertes de burn rate (fenêtres rapide + lente). *Moins de pages, moins d'oublis.*
