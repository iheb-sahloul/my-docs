# Bonnes pratiques Docker, Kubernetes & DevOps



## 🐳 Images Docker

### Utilisez des builds multi-stage
Construisez dans une étape avec toute la chaîne d'outils, et ne copiez que le résultat dans une petite image
d'exécution.

**Pourquoi c'est une bonne pratique :** une image mono-étape embarque en production le JDK, Maven, le cache
`~/.m2`, le code source et la chaîne d'outils Node. Ce sont des centaines de Mo à télécharger à chaque
déploiement, un démarrage à froid plus lent, et beaucoup plus de paquets avec des vulnérabilités connues à
corriger. L'étape finale n'a besoin que d'un JRE et du jar.

```dockerfile
# ✅
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN ./mvnw -q package -DskipTests

FROM eclipse-temurin:21-jre
COPY --from=build /app/target/app.jar /app/app.jar
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Figez les versions des images de base
Utilisez un tag de version précis, ou un digest pour une reproductibilité totale. Jamais `latest`.

**Pourquoi c'est une bonne pratique :** `latest` pointe vers ce qui a été poussé en dernier. Le même Dockerfile
produit une image différente la semaine suivante, peut-être avec une nouvelle version majeure du runtime, et un
build qui marchait hier casse sans aucun changement dans votre dépôt. Vous ne pouvez pas non plus savoir quelle
version tourne en production. Figez la version, et laissez un bot (Renovate, Dependabot) ouvrir des PR pour la
mettre à jour afin que les montées de version soient relues et testées.

⛔ `FROM node:latest`
✅ `FROM node:22.11-alpine` ou `FROM node:22.11-alpine@sha256:...`

### Ordonnez les couches de la moins à la plus souvent modifiée
Copiez d'abord les fichiers de dépendances et installez les dépendances, puis copiez le code source.

**Pourquoi c'est une bonne pratique :** Docker met chaque couche en cache et reconstruit tout ce qui suit la
première couche modifiée. Avec `COPY . .` en premier, toute modification du code invalide la couche des
dépendances, donc chaque build retélécharge toutes les dépendances. Copier `package.json` / `pom.xml` seuls
d'abord fait que les dépendances ne sont réinstallées que quand elles changent vraiment : les builds passent de
minutes à secondes.

```dockerfile
# ✅
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
```

### Ajoutez un `.dockerignore`
Excluez `.git`, `node_modules`, `target`, les fichiers `.env` locaux et les dossiers d'IDE du contexte de build.

**Pourquoi c'est une bonne pratique :** sans lui, `COPY . .` envoie tout le répertoire au build, y compris un
dossier `.git` qui peut peser plus lourd que l'application, des sorties de build locales qui écrasent celles
construites dans l'image, et des fichiers `.env` contenant de vrais secrets qui finissent dans une couche lisible
par quiconque possède l'image.

✅ `.dockerignore` : `.git`, `node_modules`, `target`, `.env*`, `*.log`

### Ne tournez pas en root
Créez un utilisateur non root dans l'image et basculez dessus avec `USER`.

**Pourquoi c'est une bonne pratique :** par défaut, le processus du conteneur tourne en root. Si l'application est
compromise, l'attaquant est root dans le conteneur, peut modifier ses fichiers, et n'est qu'à une vulnérabilité du
noyau ou du runtime d'être root sur le nœud. Avec un utilisateur non root, une évasion du conteneur rapporte bien
moins. Kubernetes peut l'imposer avec `securityContext.runAsNonRoot: true`.

```dockerfile
# ✅
RUN useradd --system --uid 10001 app
USER 10001
```

### Ne mettez jamais de secrets dans l'image
Ne faites pas de `COPY` d'identifiants et ne les définissez pas avec `ENV` / `ARG`. Injectez-les à l'exécution
(Secret Kubernetes, vault). Utilisez `RUN --mount=type=secret` si le build lui-même en a besoin.

**Pourquoi c'est une bonne pratique :** chaque couche d'une image est conservée et peut être extraite avec
`docker save` ou `docker history`, même si une couche suivante supprime le fichier. Les valeurs `ENV` et `ARG`
sont stockées en clair dans les métadonnées de l'image. Quiconque peut récupérer l'image (un registry, un cache
de CI, le poste d'un développeur) obtient le secret, et le renouveler oblige à reconstruire toutes les images.

⛔ `ENV DB_PASSWORD=s3cr3t`, `COPY id_rsa /root/.ssh/`
✅ secret monté à l'exécution, `RUN --mount=type=secret,id=npmrc npm ci` au moment du build

## 📦 Conteneurs à l'exécution

### Utilisez la forme exec et gérez `SIGTERM`
Écrivez `ENTRYPOINT` / `CMD` sous forme de tableau JSON, et faites en sorte que l'application termine le travail
en cours quand elle reçoit `SIGTERM`.

**Pourquoi c'est une bonne pratique :** la forme shell (`ENTRYPOINT java -jar app.jar`) lance `/bin/sh` en PID 1,
et le shell ne transmet pas les signaux. Lors d'un arrêt ou d'un déploiement, l'application ne reçoit jamais
`SIGTERM`, est tuée par `SIGKILL` à la fin du délai de grâce, et les requêtes en cours échouent. La forme exec
fait de l'application le PID 1, elle reçoit donc le signal et peut s'arrêter proprement.

⛔ `ENTRYPOINT java -jar /app/app.jar`
✅ `ENTRYPOINT ["java", "-jar", "/app/app.jar"]`

### Un processus par conteneur, logs sur stdout
Lancez un seul processus principal par conteneur, et écrivez les logs sur stdout / stderr, pas dans des fichiers.

**Pourquoi c'est une bonne pratique :** le cycle de vie du conteneur suit son processus principal : si vous en
lancez plusieurs avec un script, l'un peut planter alors que le conteneur reste « running » et en bonne santé.
Des conteneurs séparés peuvent être mis à l'échelle, redémarrés et surveillés indépendamment. La plateforme
collecte stdout automatiquement ; les fichiers de log dans un conteneur remplissent son disque et disparaissent à
son redémarrage. Loggez en JSON pour que l'agrégateur puisse indexer les champs.

⛔ un `start.sh` qui lance nginx et l'application en arrière-plan et fait un tail d'un fichier de log
✅ un conteneur par processus, logs JSON sur stdout

## ☸️ Kubernetes

### Définissez les requests et limits de ressources
Donnez à chaque conteneur des `requests` CPU et mémoire, et une `limit` mémoire.

**Pourquoi c'est une bonne pratique :** le scheduler place les pods selon leurs `requests`. Sans elles, il entasse
trop de pods sur un nœud, qui se disputent le CPU et la mémoire. Sans limite mémoire, un pod qui fuit peut
consommer toute la mémoire du nœud et faire évincer les autres pods. Une limite mémoire trop basse fait tuer le
pod (`OOMKilled`), donc mesurez d'abord la consommation réelle. Pour la JVM, dimensionnez le heap par rapport au
conteneur (`-XX:MaxRAMPercentage=75`). Une limite CPU provoque du throttling, donc beaucoup d'équipes ne
définissent qu'une request CPU.

```yaml
# ✅
resources:
  requests: { cpu: 250m, memory: 512Mi }
  limits: { memory: 512Mi }
```

### Configurez correctement les probes liveness, readiness et startup
La readiness décide si le pod reçoit du trafic. La liveness décide s'il est redémarré. La startup protège les
démarrages lents.

**Pourquoi c'est une bonne pratique :** sans probe de readiness, du trafic est envoyé à un pod qui n'a pas fini
de démarrer, et les clients reçoivent des erreurs à chaque déploiement. Une probe de liveness qui vérifie la base
redémarre tous les pods quand la base a un raté, ce qui transforme une petite panne en panne totale : la liveness
ne doit vérifier que le processus lui-même. Une application lente à démarrer avec seulement une probe de liveness
est tuée avant d'être prête, en boucle ; une `startupProbe` désactive les autres probes jusqu'à ce que le
démarrage réussisse.

```yaml
# ✅
startupProbe:   { httpGet: { path: /actuator/health/liveness,  port: 8080 }, failureThreshold: 30, periodSeconds: 5 }
livenessProbe:  { httpGet: { path: /actuator/health/liveness,  port: 8080 } }
readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
```

### Gardez la configuration dans des ConfigMaps et des Secrets
Stockez la configuration propre à chaque environnement dans des `ConfigMap` et les identifiants dans des `Secret`
(idéalement synchronisés depuis un vault), pas dans l'image.

**Pourquoi c'est une bonne pratique :** la même image doit tourner dans tous les environnements, seule la
configuration change. Si l'URL de la base est figée dans l'image, il faut un build par environnement, et ce que
vous avez testé n'est pas ce que vous déployez. Les Secrets sont seulement encodés en base64, pas chiffrés :
activez le chiffrement au repos, restreignez l'accès avec RBAC, et préférez un outil comme External Secrets ou
Sealed Secrets plutôt que de les commiter.

⛔ une image par environnement, identifiants dans `values.yaml` sur Git
✅ `envFrom: [{ configMapRef: { name: app-config } }, { secretRef: { name: app-secrets } }]`

### Lancez plusieurs réplicas avec un `PodDisruptionBudget`
Lancez au moins 2 réplicas de tout ce qui est exposé aux utilisateurs, répartis sur plusieurs nœuds, et
protégez-les avec un `PodDisruptionBudget`.

**Pourquoi c'est une bonne pratique :** avec un seul réplica, chaque déploiement, mise à jour de nœud ou crash est
une interruption de service. Même avec plusieurs, un drain de nœud peut tous les évincer en même temps. Un PDB
indique à Kubernetes combien de pods doivent rester actifs pendant les interruptions volontaires, donc la
maintenance attend au lieu de faire tomber le service. Les topology spread constraints empêchent tous les
réplicas d'atterrir sur le même nœud.

```yaml
# ✅
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 1
  selector: { matchLabels: { app: orders } }
```

### Utilisez des rolling updates avec `maxUnavailable: 0`
Configurez la stratégie de déploiement pour que les nouveaux pods soient prêts avant que les anciens ne soient
supprimés.

**Pourquoi c'est une bonne pratique :** combinés à une probe de readiness, `maxUnavailable: 0` et `maxSurge: 1`
font que Kubernetes démarre un nouveau pod, attend qu'il soit prêt, et seulement ensuite arrête un ancien. Si la
nouvelle version n'est jamais prête, le déploiement s'arrête et les anciens pods continuent de servir le trafic.
Revenez en arrière avec `kubectl rollout undo`.

✅ `strategy: { type: RollingUpdate, rollingUpdate: { maxUnavailable: 0, maxSurge: 1 } }`

## ⎈ Helm

### Un chart, un fichier de values par environnement
Gardez un seul chart avec des valeurs par défaut raisonnables dans `values.yaml`, et ne surchargez que ce qui
diffère dans `values-<env>.yaml`.

**Pourquoi c'est une bonne pratique :** copier le chart ou les manifestes par environnement oblige à appliquer
chaque correction plusieurs fois, et les copies divergent jusqu'à ce que la production ne corresponde plus à ce
que vous avez testé. Avec des fichiers de values par environnement, la différence entre environnements est petite
et visible dans un seul diff.

⛔ `charts/orders-dev/`, `charts/orders-prod/`
✅ `helm upgrade --install orders ./chart -f values.yaml -f values-prod.yaml`

### Lintez et rendez les charts en CI
Lancez `helm lint` et `helm template` (plus un validateur de schéma comme kubeconform) à chaque modification.

**Pourquoi c'est une bonne pratique :** une erreur de template ou une mauvaise indentation YAML n'est découverte
qu'au déploiement, souvent en production. Rendre le chart en CI détecte les erreurs de syntaxe et les manifestes
invalides avant le merge, et la sortie rendue peut être comparée en review pour voir les vrais objets Kubernetes
qui vont changer.

✅ `helm lint ./chart && helm template ./chart -f values-prod.yaml | kubeconform -strict`

## 🚀 CI/CD

### Construisez une fois, promouvez le même artefact
Construisez l'image une seule fois, taguez-la avec le SHA du commit, et déployez cette même image dans tous les
environnements.

**Pourquoi c'est une bonne pratique :** reconstruire pour chaque environnement peut produire une image différente
(une nouvelle image de base, une autre version de dépendance), donc ce que vous avez testé en staging n'est pas ce
qui tourne en production. Un tag immuable comme le SHA du commit dit exactement quel code tourne et fait d'un
rollback un simple redéploiement du tag précédent. Les tags mutables (`latest`, `prod`) changent sous vos pieds et
cassent les deux.

⛔ reconstruire à chaque merge de branche, déployer `myapp:latest`
✅ `myapp:3f9c2ab` construit une fois, promu dev → staging → prod

### Scannez les images et les dépendances dans le pipeline
Scannez les images (Trivy, Grype) et les dépendances à chaque build, et faites échouer le build sur les
vulnérabilités critiques.

**Pourquoi c'est une bonne pratique :** la plupart des vulnérabilités viennent des images de base et des
bibliothèques tierces, pas de votre propre code, et de nouvelles sont publiées chaque jour pour des paquets que
vous avez livrés il y a des mois. Scanner en CI bloque les problèmes connus avant qu'ils n'atteignent la
production, et scanner régulièrement les images en cours d'exécution vous dit quand il faut reconstruire.

✅ `trivy image --exit-code 1 --severity CRITICAL myapp:3f9c2ab`
