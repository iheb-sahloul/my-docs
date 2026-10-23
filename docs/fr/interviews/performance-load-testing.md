# Performance & tests de charge

Comment mesurer, tester et raisonner sur la performance : profils de charge, outils (k6, Gatling), percentiles, chasse aux goulots et capacité. Les percentiles de latence sont introduits dans [Full Stack & DevOps](fullstack-devops-k8s.md#p50-p95-p99-latency-average) ; l'exercice p95 de bout en bout est la [Q36](fullstack-devops-k8s.md#reducing-endpoint-p95-latency-9).

## 🟢 Fondamentaux

#### Q1. Que sont les tests de charge, de stress, de pic et d'endurance (soak), et que trouve chacun ? {#load-stress-spike-soak-tests}
**Réponse :** **Charge** : trafic attendu, vérifie le respect du SLO. **Stress** : montée au-delà de la capacité pour trouver le point de rupture et la façon dont le système échoue (proprement ou non). **Pic** : saut brutal, teste l'autoscaling et les files. **Soak** : charge modérée pendant des heures, révèle fuites, épuisement de connexions et dégradation lente. À exécuter sur un environnement proche de la production avec un volume de données réaliste.

#### Q2. Comment écrivez-vous un test de charge avec k6 ou Gatling, et qu'est-ce qui le rend réaliste ? {#write-load-test-k6-gatling}
**Réponse :** Modélisez des **parcours utilisateur** avec temps de réflexion, pas un seul endpoint chaud ; variez les données (pas le même id, qui tape dans les caches) ; montez progressivement ; fixez des **seuils** qui font échouer l'exécution. Utilisez un modèle ouvert (débit d'arrivée fixe) pour les API publiques, fermé (utilisateurs fixes) pour les outils internes.

**Exemple :**

```javascript
export const options = {
  scenarios: { api: { executor: 'constant-arrival-rate', rate: 100, timeUnit: '1s',
                      duration: '5m', preAllocatedVUs: 200 } },
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<300'] },
};
```

## 🟡 Pièges seniors

#### Q3. Qu'est-ce que la coordinated omission, et pourquoi certains tests de charge affichent-ils des latences trop belles ? {#coordinated-omission-some-load-tests}
**Réponse :** Un outil en boucle fermée qui attend chaque réponse avant d'envoyer la suivante masque les blocages : pendant un gel de 5 s il n'envoie rien, donc la période lente est sous-comptée et le p99 paraît bon. Utilisez un modèle ouvert à débit d'arrivée fixe, ou un outil qui corrige (wrk2, HdrHistogram, executors arrival-rate de k6), et rapportez toujours p95/p99/max, jamais la seule moyenne.

#### Q4. Comment trouvez-vous le goulot quand le débit ne progresse plus ? {#find-bottleneck-throughput-stops-growing}
**Réponse :** Appliquez la **méthode USE** par ressource (Utilisation, Saturation, Erreurs) : CPU, mémoire, disque, réseau, puis ressources logicielles comme pools de connexions, pools de threads et verrous. Cherchez celle qui sature : un pool à 100 % avec une file d'attente croissante, un cœur CPU saturé, des pauses GC, ou une base à sa limite de connexions. Confirmez avec un profileur ou des traces, changez une chose, retestez.

#### Q5. Quel lien entre la loi de Little, le pool de connexions et la capacité ? {#little-law-connection-pool-relate}
**Réponse :** Loi de Little : concurrence = débit × latence. À 200 req/s avec 100 ms de latence, il faut environ 20 requêtes en vol. Un pool BD de 10 vous plafonne alors vers 100 req/s quel que soit le CPU. Dimensionnez les pools avec cette arithmétique, et rappelez-vous que plus de threads que la base ne peut servir allonge seulement les files.

## 🔴 Expert / Ouvert

#### Q6. Comment intégrer des contrôles de performance en CI/CD sans résultats instables ? {#put-performance-checks-ci-cd}
**Réponse :** Lancez une petite charge de fumée fixe à chaque merge sur un environnement stable et comparez à une référence avec tolérance (par ex. p95 à ±15 %) ; lancez soak/stress longs la nuit. Échouez sur les seuils de SLO, conservez les résultats dans le temps et isolez les voisins bruyants (runners dédiés). Traitez une régression comme un test en échec : bissectez jusqu'au commit.

## 🎯 Scénarios réels

### S1. Le p99 est bon à 50 % de charge mais explose à 8 s vers 80 % de CPU {#p99-fine-50-load-but}
- **Symptômes :** La latence médiane est stable, la queue de distribution explose quand la charge monte et les erreurs arrivent par rafales.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Mise en file : près de la saturation, le temps d'attente croît de façon non linéaire. Vérifiez attente des pools, pauses GC, thread dumps et retries qui amplifient la charge.
- **Résolution :** Ajoutez de la capacité ou réduisez le travail par requête, bornez files et timeouts, ajoutez du load shedding et des retries plafonnés avec jitter, et déclenchez l'autoscaling vers 60 % plutôt que 90 %.
- **Prévention :** Testez en charge jusqu'au coude de la courbe avant le lancement et alertez sur la saturation (profondeur de file, attente de pool), pas seulement sur le CPU.

</details>

### S2. Le test de charge passait à 3× le trafic prévu, et pourtant la prod tombe le jour du lancement à 1× {#load-test-green-prod-falls-over}
- **Symptômes :** Le rapport k6 montrait un p95 de 120 ms à 3000 req/s. En prod, à 1000 req/s, le p95 est à 4 s et le CPU de la base à 100 %.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Comparez le test à la réalité : 50 utilisateurs de test sur les mêmes 10 produits (tout en cache), un petit jeu de données de staging où chaque index tient en mémoire, pas de think time, un modèle fermé qui ralentit quand le système ralentit (coordinated omission) et aucun job de fond.
- **Exemple :**

  ```javascript
  // modèle ouvert : les arrivées n'attendent pas les réponses lentes
  export const options = { scenarios: { launch: {
    executor: 'constant-arrival-rate', rate: 1000, timeUnit: '1s',
    duration: '15m', preAllocatedVUs: 500 } } };
  ```

- **Résolution :** Scale out / ajoutez l'index manquant pour tenir, puis reconstruisez le test : données anonymisées de taille prod, distribution de clés réaliste (longue traîne, pas 10 produits chauds), modèle ouvert à taux d'arrivée constant, et les mêmes crons actifs pendant le test.
- **Prévention :** Traitez le test de charge comme un produit : revue de son réalisme comme du code, comparaison trimestrielle du mix de trafic avec les access logs de prod, et exécution en CI sur un environnement proche de la prod avant les gros lancements.

</details>

### S3. Le débit plafonne à ~400 req/s quel que soit le nombre de pods, et le CPU reste à 30 % {#throughput-plateaus-cpu-idle}
- **Symptômes :** Passer de 4 à 8 pods ne change pas le débit ; la latence croît linéairement avec la charge ; ni le CPU de l'app ni celui de la base ne sont saturés.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une ressource partagée et bornée est le goulot : c'est de l'attente, pas du calcul. Cherchez ce qui attend : `hikaricp_connections_pending`, un `max_connections` de la base réparti entre pods, un rate limit en aval, une file à une seule partition, ou un verrou (`pg_stat_activity` avec `wait_event_type = 'Lock'`).
- **Exemple :**

  ```text
  8 pods × pool 10 = 80 connexions, mais RDS max_connections = 100 et une ligne chaude
  UPDATE stock SET qty = qty - 1 WHERE sku = 'BESTSELLER'  -> chaque requête se sérialise sur un verrou de ligne
  ```

- **Résolution :** Corrigez la ressource contendue : supprimez l'update de ligne chaude (table de réservation, compteurs shardés ou décrément asynchrone), dimensionnez les pools d'après le nombre de cœurs de la base, ajoutez un pooler (PgBouncer) si les pods doivent encore scaler.
- **Prévention :** Les tests de charge rapportent les métriques de saturation (attente de pool, attente de verrous, profondeur de file), pas seulement la latence ; appliquez la méthode USE à chaque ressource partagée du chemin de requête.

</details>

### S4. Après une release, le p50 est inchangé mais le p99 a doublé, et le diff semble anodin {#p99-regression-after-release}
- **Symptômes :** Latence médiane identique, p99 de 180 ms à 400 ms ; pas plus d'erreurs ; CPU légèrement plus haut.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Une régression qui ne touche que la queue signifie souvent quelque chose de périodique ou qui alloue beaucoup : comparez les pauses GC (`jvm_gc_pause_seconds`) avant/après, puis profilez avec async-profiler en mode allocation. Coupable fréquent : un nouveau mapping JSON, du logging ou un pipeline `stream()` qui alloue de gros objets temporaires par requête.
- **Exemple :**

  ```bash
  # flame graph d'allocation sur un pod pendant 60 s
  ./asprof -e alloc -d 60 -f /tmp/alloc.html <pid>
  ```

- **Résolution :** Supprimez le point chaud d'allocation (réutiliser l'`ObjectMapper`, ne pas construire de chaînes pour des niveaux de log désactivés, streamer plutôt que matérialiser de grandes listes), ou ajustez heap/GC si le live set a réellement grandi.
- **Prévention :** Une barrière de performance en CI qui compare p99 et taux d'allocation au build précédent sur le même benchmark, avec une tolérance ; profilage continu en prod pour comparer les releases.

</details>

### S5. Chaque jour ouvré à 09:00, la latence explose pendant 10 minutes, puis revient quand l'autoscaling rattrape {#autoscaling-lags-morning-spike}
- **Symptômes :** Le HPA passe de 4 à 16 pods, mais les nouveaux pods mettent 90 s à être prêts et le HPA ne réagit qu'après un CPU haut prolongé ; erreurs et timeouts pendant la montée.

> 🧠 **À essayer d'abord :** Avant d'ouvrir la réponse, écrivez vos trois premières hypothèses et la commande ou la métrique que vous vérifieriez pour chacune.

<details markdown="1">
<summary>Afficher diagnostic, résolution & prévention</summary>

- **Diagnostic :** Tracez la chronologie : le trafic monte en 2 minutes ; synchro HPA + délai des métriques ≈ 1 min ; provisionnement de nœud (cluster autoscaler) 2–4 min ; démarrage JVM + warm-up 90 s. La somme dépasse la durée du pic.
- **Résolution :** Pré-scalez selon un planning avant le pic connu (scaler cron KEDA ou changement planifié de `minReplicas`), gardez de la marge (CPU cible 50–60 %), réduisez le temps de démarrage (CDS/AppCDS, init paresseuse, image plus petite) et utilisez une readiness probe qui attend le warm-up.
- **Prévention :** Testez la montée en charge elle-même, pas seulement le régime établi ; mesurez le « temps entre décision de scale et pod prêt » ; revue de capacité avant les événements connus (campagnes, jour de paie).

</details>

## 🎤 Quiz oral

Répondez à chaque question **à voix haute en 2–3 minutes**, sans regarder : contexte → options → décision → compromis. Relisez ensuite la question liée et notez-vous : **0** vide · **1** définition seule · **2** plus un exemple · **3** plus compromis et piège.

1. Q1. Que sont les tests de charge, de stress, de pic et d'endurance (soak), et que trouve chacun ?
2. Q2. Comment écrivez-vous un test de charge avec k6 ou Gatling, et qu'est-ce qui le rend réaliste ?
3. Q3. Qu'est-ce que la coordinated omission, et pourquoi certains tests de charge affichent-ils des latences trop belles ?
4. Q4. Comment trouvez-vous le goulot quand le débit ne progresse plus ?
5. Q5. Quel lien entre la loi de Little, le pool de connexions et la capacité ?
6. Q6. Comment intégrer des contrôles de performance en CI/CD sans résultats instables ?
7. S1. Le p99 est bon à 50 % de charge mais explose à 8 s vers 80 % de CPU

## 📌 Cheat-sheet

- **Types de tests** — charge = attendu, stress = au-delà, pic = brutal, soak = long. *Chacun trouve une panne différente.*
- **Réalisme** — parcours, temps de réflexion, données variées, seuils. *Modèle ouvert pour les API publiques.*
- **Percentiles** — rapportez p95/p99/max, jamais la moyenne seule. *Attention à la coordinated omission.*
- **Goulot** — méthode USE par ressource ; concurrence = débit × latence. *Dimensionnez les pools avec ce calcul.*
- **CI** — petite charge fixe par merge vs référence, longs tests la nuit. *Isolez les runners bruyants.*
