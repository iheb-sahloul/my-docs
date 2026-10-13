# Bonnes pratiques d'observabilité

## 📜 Logs

### Utilisez des logs structurés (JSON)

Émettez un objet JSON par ligne avec des noms de champs fixes, au lieu de texte libre.

**Pourquoi c'est une bonne pratique :** faire un grep de « Order 42 failed for user ann » marche sur un serveur ;
avec 30 pods qui envoient leurs logs à Elasticsearch ou Loki, il faut filtrer par `orderId` et `level`. Le texte
libre demande des regex fragiles qui cassent dès que quelqu'un reformule un message. Spring Boot 3.4+ supporte
nativement les logs structurés.

```yaml
# ⛔ pattern simple, analysé avec des regex en aval

# ✅ Spring Boot 3.4+
logging.structured.format.console: ecs     # ou logstash, gelf
```

```json
{"@timestamp":"2026-03-01T10:15:30Z","log.level":"ERROR","message":"Payment failed","orderId":42,"traceId":"4bf92f35"}
```

### Utilisez SLF4J avec des messages paramétrés

Loguez avec `log.info("... {}", value)`, jamais par concaténation de chaînes ni avec `System.out`.

**Pourquoi c'est une bonne pratique :** la concaténation construit la chaîne même quand le niveau est désactivé, ce
qui coûte du CPU et des allocations sur les chemins critiques. `System.out` n'a ni niveau, ni horodatage, ni
routage. Les placeholders ne sont évalués que si le niveau est activé, et un modèle reste constant, ce qui permet
aux outils de logs de regrouper les messages similaires.

```java
// ⛔
System.out.println("Order " + order + " saved");
log.debug("Order " + order.toJson() + " saved");

// ✅
log.debug("Order saved id={} total={}", order.id(), order.total());
```

### Choisissez les niveaux de log délibérément

`ERROR` = quelqu'un doit agir, `WARN` = inattendu mais géré, `INFO` = événements métier, `DEBUG` = diagnostic, `TRACE` = très détaillé.

**Pourquoi c'est une bonne pratique :** si tout est `ERROR`, les alertes se déclenchent sans cesse et sont mises en
sourdine ; si une vraie panne est en `INFO`, personne ne la voit. Un utilisateur qui saisit un mauvais mot de passe
n'est pas une ERROR. Faire tourner la production en `INFO` garde les coûts raisonnables : un service qui logue
1 Ko à 500 req/s produit environ 40 Go par jour au niveau DEBUG.

```java
// ⛔
log.error("User not found: {}", id);           // 404 normal, pas une erreur
log.info("NullPointerException", ex);

// ✅
log.info("User lookup missed id={}", id);
log.error("Payment provider unreachable orderId={}", orderId, ex);
```

### Loguez l'exception une seule fois, avec sa stack trace

Passez l'exception en dernier argument, et loguez-la à l'endroit où vous la traitez, pas à chaque couche.

**Pourquoi c'est une bonne pratique :** loguer et relancer à chaque couche imprime la même stack trace 4 fois, donc une
seule panne ressemble à 4 incidents. `log.error(ex.getMessage())` perd la stack trace, et la cause racine avec.

```java
// ⛔
catch (Exception e) { log.error(e.getMessage()); throw e; }

// ✅ encapsuler et lancer ; loguer une seule fois dans le gestionnaire d'exception
catch (SQLException e) { throw new OrderStorageException(orderId, e); }

@ExceptionHandler(OrderStorageException.class)
ProblemDetail handle(OrderStorageException ex) {
    log.error("Order storage failed orderId={}", ex.orderId(), ex);
    return ProblemDetail.forStatus(500);
}
```

### Ajoutez du contexte avec le MDC

Placez les valeurs propres à la requête (`requestId`, `userId`, `tenant`) dans le MDC via un filtre, pour que chaque ligne les porte.

**Pourquoi c'est une bonne pratique :** dans un service chargé, les lignes de log de 200 requêtes concurrentes sont
entremêlées, et « Insufficient funds » seul est inutile. Avec un id de corrélation, une seule recherche montre
toute l'histoire d'une requête. Videz le MDC à la fin, car les threads sont poolés et des valeurs périmées fuient
dans la requête suivante.

```java
// ✅
@Component
class RequestContextFilter extends OncePerRequestFilter {
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        MDC.put("requestId", Optional.ofNullable(req.getHeader("X-Request-Id")).orElse(UUID.randomUUID().toString()));
        try { chain.doFilter(req, res); } finally { MDC.clear(); }
    }
}
```

### Ne loguez jamais de secrets ni de données personnelles

Masquez les mots de passe, tokens, numéros de carte et données personnelles, et évitez de loguer des corps de requête entiers.

**Pourquoi c'est une bonne pratique :** les logs sont expédiés à des tiers, conservés des mois, et lisibles par de
nombreux ingénieurs. Un bearer token fuité dans les logs est un identifiant valide ; les données personnelles dans
les logs entraînent des obligations RGPD.

```java
// ⛔
log.info("Request: {}", request);        // contient le mot de passe, le numéro de carte

// ✅
log.info("Checkout started userId={} items={}", user.id(), cart.size());
```

## 📊 Métriques

### Exposez les métriques avec Micrometer et Prometheus

Ajoutez `spring-boot-starter-actuator` et `micrometer-registry-prometheus`, puis scrapez `/actuator/prometheus`.

**Pourquoi c'est une bonne pratique :** les logs disent ce qui s'est passé une fois ; les métriques disent comment le
système se comporte dans le temps, à peu de frais. La mémoire JVM, le GC, le pool de threads, la latence HTTP et
l'usage du pool de base de données sont fournis automatiquement et sont la première chose que l'on regarde pendant
un incident.

```yaml
# ✅
management:
  endpoints.web.exposure.include: health,info,prometheus
  metrics.tags.application: ${spring.application.name}
```

### Mesurez les signaux RED et USE

Pour chaque service, suivez Rate, Errors, Duration (requêtes) et Utilization, Saturation, Errors (ressources comme les pools et les files).

**Pourquoi c'est une bonne pratique :** des centaines de métriques sont inutiles sans liste de contrôle. RED répond à
« les utilisateurs souffrent-ils ? », USE répond à « quelle ressource est le goulot d'étranglement ? ». Un pool de
connexions saturé (threads en attente supérieurs à 0) explique la latence bien avant le CPU.

```text
# ✅ tableaux de bord
Rate      http_server_requests_seconds_count
Errors    idem, filtré sur status=~"5.."
Duration  histogram_quantile(0.99, ...)
Saturation hikaricp_connections_pending
```

### Ajoutez des métriques métier et personnalisées avec un ensemble borné de tags

Comptez ce qui intéresse le métier (commandes passées, paiements échoués) et gardez des valeurs de tags à faible cardinalité.

**Pourquoi c'est une bonne pratique :** « le CPU va bien » pendant que les paiements échouent en silence est une panne
courante. Mais chaque combinaison unique de tags est une série temporelle distincte : `userId` en tag crée un
million de séries et peut faire planter ou ruiner votre backend de métriques.

```java
// ⛔ cardinalité non bornée
registry.counter("orders", "userId", userId, "orderId", orderId).increment();

// ✅
registry.counter("orders.placed", "channel", "web", "country", "FR").increment();
Timer.builder("payment.duration").publishPercentileHistogram().register(registry)
     .record(() -> gateway.charge(order));
```

### Préférez les percentiles aux moyennes

Suivez la latence p50, p95 et p99 avec des histogrammes.

**Pourquoi c'est une bonne pratique :** une moyenne de 120 ms peut cacher 1 % de requêtes qui prennent 8 s. Les
utilisateurs qui subissent ces requêtes lentes existent, et avec 100 requêtes par page, la majorité des utilisateurs
en rencontre au moins une lente. Les moyennes de percentiles n'ont aucun sens, donc publiez des buckets
d'histogramme et calculez les percentiles côté serveur.

```yaml
# ✅
management.metrics.distribution.percentiles-histogram.http.server.requests: true
management.metrics.distribution.slo.http.server.requests: 100ms,500ms,1s
```

## 🧵 Traçage

### Propagez le contexte de trace entre les services

Utilisez Micrometer Tracing avec OpenTelemetry, les en-têtes W3C `traceparent`, et ajoutez l'id de trace à vos logs.

**Pourquoi c'est une bonne pratique :** une requête utilisateur peut toucher 8 services ; sans id de trace partagé, on
corrèle par horodatages et par supposition. Une trace montre quel appel a pris 2,3 s d'une requête de 2,5 s. Avec
Spring Boot 3, `RestClient`, `WebClient` et les clients Kafka construits depuis les builders auto-configurés
propagent le contexte automatiquement.

```yaml
# ✅
management:
  tracing.sampling.probability: 0.1      # 1.0 en dev
  otlp.tracing.endpoint: http://otel-collector:4318/v1/traces
logging.pattern.correlation: "[${spring.application.name:},%X{traceId:-},%X{spanId:-}] "
```

### Échantillonnez les traces intelligemment

Échantillonnez un pourcentage en production (ou utilisez un échantillonnage tail-based qui garde les erreurs et les traces lentes).

**Pourquoi c'est une bonne pratique :** stocker 100 % des traces à fort trafic coûte cher et est souvent inutile,
alors qu'un 1 % fixe peut manquer la rare panne dont vous avez besoin. L'échantillonnage tail-based dans le
collector garde chaque erreur et chaque trace lente, ainsi qu'un échantillon du reste.

```yaml
# ⛔ 1.0 en production à 5 000 req/s
management.tracing.sampling.probability: 1.0

# ✅
management.tracing.sampling.probability: 0.05
```

### Ajoutez des spans personnalisés autour des opérations importantes

Encadrez les étapes métier clés ou les appels externes avec une `Observation` (ou `@Observed`) portant un nom à faible cardinalité.

**Pourquoi c'est une bonne pratique :** l'instrumentation automatique couvre HTTP et JDBC, mais pas « calculer le prix
de livraison », qui peut être l'étape lente. Une seule `Observation` donne une métrique, un span et un contexte de
log à la fois.

```java
// ✅
@Observed(name = "shipping.quote", contextualName = "quote-shipping")
public Quote quote(Cart cart) { ... }
```

## ❤️ Santé & alertes

### Exposez des sondes de liveness et de readiness séparées

Utilisez `/actuator/health/liveness` et `/actuator/health/readiness`, et branchez-les sur Kubernetes.

**Pourquoi :** traité dans [Configurez correctement les probes liveness, readiness et startup](docker-k8s-devops.md#configurez-correctement-les-probes-liveness-readiness-et-startup).

```yaml
# ✅
management.endpoint.health.probes.enabled: true
management.endpoint.health.group.readiness.include: readinessState,db
```

```yaml
livenessProbe:  { httpGet: { path: /actuator/health/liveness,  port: 8080 } }
readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
```

### Arrêtez-vous proprement

Activez l'arrêt gracieux pour que les requêtes en cours se terminent avant la sortie du pod.

**Pourquoi c'est une bonne pratique :** sans cela, chaque déploiement coupe les requêtes en cours, ce qui donne aux
utilisateurs une rafale d'erreurs 502 à chaque déploiement. Spring attend les requêtes actives jusqu'au timeout.

```yaml
# ✅
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
```

### Alertez sur les symptômes, pas sur les causes

Réveillez sur les problèmes visibles par l'utilisateur (taux d'erreur, consommation du budget de SLO de latence, absence de trafic), et gardez le CPU et le disque en tickets ou en tableaux de bord.

**Pourquoi c'est une bonne pratique :** « CPU à 85 % » peut être parfaitement normal et réveille quelqu'un à 3 h du
matin pour rien ; la fatigue d'alerte pousse les gens à ignorer ou couper les alertes, et la vraie est alors
manquée. Alerter sur un SLO (par exemple, 99,9 % des requêtes sous 500 ms) lie les pages à l'impact client.

```yaml
# ⛔
- alert: HighCpu
  expr: cpu_usage > 0.8

# ✅
- alert: HighErrorRate
  expr: |
    sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
      / sum(rate(http_server_requests_seconds_count[5m])) > 0.02
  for: 5m
  labels: { severity: page }
  annotations: { runbook: https://wiki.example.com/runbooks/high-error-rate }
```

### Donnez à chaque alerte un responsable et un runbook

Chaque page renvoie vers un runbook qui dit ce que cela signifie, comment vérifier et comment atténuer. Supprimez les alertes sur lesquelles personne n'agit.

**Pourquoi c'est une bonne pratique :** à 3 h du matin, personne ne se souvient de ce que signifie `queue_depth_high`.
Un runbook réduit le temps d'atténuation, et une alerte ignorée trois fois de suite est du bruit à corriger ou à
supprimer.

```yaml
# ✅
annotations:
  summary: "Order queue backlog above 10k for 10 min"
  runbook: https://wiki.example.com/runbooks/order-queue
```

### Définissez des SLO et suivez le budget d'erreur

Fixez un objectif (disons 99,9 % de disponibilité sur 30 jours) et mesurez-le à partir des vraies métriques de requêtes.

**Pourquoi c'est une bonne pratique :** 99,9 % autorise environ 43 minutes d'indisponibilité par 30 jours, 99,99 %
seulement environ 4. Sans chiffre, « fiable » est une dispute. Le budget d'erreur restant vous dit quand livrer des
fonctionnalités et quand s'arrêter pour corriger la fiabilité.

```text
# ✅
SLI: successful requests / total requests (status < 500)
SLO: 99.9% over 30 days -> budget = 0.1% = ~43 min
```
