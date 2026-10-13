# Docker

## Images

### Construire une image

```bash
docker build -t myapp:1.0 .                       # Dockerfile dans le dossier courant
docker build -f docker/Dockerfile.prod -t myapp:prod .
docker build --build-arg JAR=app.jar -t myapp .   # ARG dans le Dockerfile
docker build --no-cache -t myapp .                # ignore le cache des couches
docker buildx build --platform linux/amd64,linux/arm64 -t me/myapp:1.0 --push .
```

### Dockerfile multi-stage (image d'exécution légère)

```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q dependency:go-offline          # en cache tant que pom.xml ne change pas
COPY src ./src
RUN mvn -q package -DskipTests

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/app.jar app.jar
USER 1000
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
```

Placez d'abord les étapes qui changent rarement : chaque instruction est une couche, et une couche modifiée invalide toutes les suivantes.

### .dockerignore

```text
.git
target/
node_modules/
*.log
.env
```

### Lister, taguer, pousser, supprimer

```bash
docker images                                  # images locales
docker image ls --filter dangling=true
docker tag myapp:1.0 registry.example.com/team/myapp:1.0
docker login registry.example.com
docker push registry.example.com/team/myapp:1.0
docker pull postgres:16
docker rmi myapp:1.0
```

### Inspecter les couches et la taille d'une image

```bash
docker history myapp:1.0                       # taille de chaque couche
docker image inspect myapp:1.0 --format '{{.Size}} {{.Config.Env}}'
```

---

## Conteneurs

### Exécuter

```bash
docker run --rm -it alpine sh                  # interactif, supprimé à la sortie
docker run -d --name web -p 8080:80 nginx      # en arrière-plan, hôte 8080 -> conteneur 80
docker run -d --name db \
  -e POSTGRES_PASSWORD=secret \
  -v pgdata:/var/lib/postgresql/data \
  -p 5432:5432 postgres:16
docker run --rm -v "$PWD":/work -w /work node:20 npm test   # exécuter un outil sans l'installer
```

### Options courantes de `run`

| Option | Signification |
|---|---|
| `-d` | Détaché (arrière-plan) |
| `-it` | Interactif + TTY (pour les shells) |
| `--rm` | Supprime le conteneur à sa sortie |
| `-p host:container` | Publier un port |
| `-e KEY=val` / `--env-file .env` | Variables d'environnement |
| `-v name:/path` / `-v ./dir:/path` | Volume nommé / bind mount |
| `--network mynet` | Rattacher à un réseau défini par l'utilisateur |
| `--restart unless-stopped` | Politique de redémarrage |
| `--memory 512m --cpus 1.5` | Limites de ressources |
| `--user 1000:1000` | Exécuter en non-root |
| `--read-only` | Système de fichiers racine en lecture seule |

### Cycle de vie

```bash
docker ps                                      # en cours d'exécution
docker ps -a                                   # y compris arrêtés
docker stop web                                # SIGTERM, puis SIGKILL après 10 s
docker start web
docker restart web
docker kill web                                # SIGKILL immédiat
docker rm web                                  # supprime un conteneur arrêté
docker rm -f web                               # arrêt + suppression
```

### Sortie personnalisée de `ps`

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

```text
NAMES   STATUS         PORTS
web     Up 2 minutes   0.0.0.0:8080->80/tcp
db      Up 2 minutes   0.0.0.0:5432->5432/tcp
```

---

## Débogage

### Logs

```bash
docker logs web
docker logs -f --tail 100 web                  # suivre, 100 dernières lignes
docker logs --since 10m web
docker logs -t web                             # avec horodatage
```

### Ouvrir un shell dans un conteneur en cours d'exécution

```bash
docker exec -it web sh                         # ou bash si l'image l'a
docker exec web env                            # commande ponctuelle
docker exec -u root -it web sh                 # en root
```

### Copier des fichiers vers et depuis un conteneur

```bash
docker cp web:/etc/nginx/nginx.conf ./nginx.conf
docker cp ./index.html web:/usr/share/nginx/html/
```

### Inspecter

```bash
docker inspect web                             # JSON complet
docker inspect -f '{{.NetworkSettings.IPAddress}}' web
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' web   # pourquoi s'est-il arrêté ?
docker port web                                # ports publiés
docker top web                                 # processus à l'intérieur
docker stats                                   # CPU/mémoire en direct par conteneur
docker events --since 10m                      # événements du daemon
```

### Le conteneur s'arrête immédiatement

```bash
docker ps -a                                   # regarder STATUS : Exited (137) = tué/OOM, (1) = erreur applicative
docker logs <name>
docker run --rm -it --entrypoint sh myapp:1.0  # contourner ENTRYPOINT et fouiller
```

| Code de sortie | Cause habituelle |
|---|---|
| 0 | Le processus principal s'est terminé normalement |
| 1 | Erreur applicative |
| 125-127 | Erreur Docker / commande non exécutable / introuvable |
| 137 | SIGKILL (souvent manque de mémoire) |
| 143 | SIGTERM (arrêt propre) |

### Déboguer une image sans shell (distroless)

```bash
docker run --rm -it --pid=container:web --network=container:web nicolaka/netshoot
```

---

## Dépannage : trouver la cause, puis corriger

Méthode, toujours dans cet ordre :

```bash
docker ps -a                                   # tourne-t-il ? code de sortie ?
docker logs --tail 100 <name>                  # ce que l'appli a dit
docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}' <name>
docker exec -it <name> sh                      # ou --entrypoint sh s'il ne reste pas up
```

| Symptôme | Cause probable | Vérifier | Correction |
|---|---|---|---|
| S'arrête immédiatement (code 1) | Erreur applicative / variable d'env manquante | `docker logs` | Passer l'env (`-e`, `--env-file`), corriger la config |
| Sort avec 137 | OOM ou `docker kill` | `.State.OOMKilled` vaut `true` | Augmenter `--memory` / la mémoire de Docker Desktop, corriger la fuite |
| Sort avec 126 / 127 | Entrypoint non exécutable / introuvable | `docker logs` : `exec: not found` | `chmod +x` dans l'image, corriger le chemin, vérifier shebang / fins de ligne CRLF |
| `exec format error` | Image construite pour un autre CPU (arm64 vs amd64) | `docker image inspect -f '{{.Architecture}}' img` | Construire/tirer avec `--platform linux/amd64` |
| Port publié mais inaccessible | L'appli écoute sur `127.0.0.1` à l'intérieur | `docker exec x ss -tln` | Faire écouter l'appli sur `0.0.0.0` |
| `port is already allocated` | Port hôte déjà utilisé | `lsof -i :8080` | Changer le côté hôte de `-p 8081:8080` ou arrêter l'autre processus |
| `name is already in use` | Un conteneur arrêté garde le nom | `docker ps -a` | `docker rm <name>` ou utiliser `--rm` |
| Un conteneur n'en joint pas un autre par son nom | Réseau bridge par défaut | `docker network inspect bridge` | Utiliser un réseau défini par l'utilisateur / Compose |
| Impossible de joindre un service de l'hôte | `localhost` est le conteneur lui-même | | `host.docker.internal` (Linux : `--add-host=host.docker.internal:host-gateway`) |
| `permission denied` sur un montage | UID différent entre hôte et conteneur | `docker exec x id`, `ls -ln` sur l'hôte | `--user "$(id -u):$(id -g)"`, `chown`, ou un volume nommé |
| Le bind mount est vide | Mauvais chemin absolu / dossier non partagé avec Docker Desktop | `docker inspect -f '{{json .Mounts}}' x` | Utiliser un chemin absolu, autoriser le dossier dans Docker Desktop |
| `no space left on device` | Images, couches, volumes accumulés | `docker system df` | `docker system prune`, `docker volume prune` (vérifier avant !) |
| `pull access denied` / `unauthorized` | Non connecté ou mauvais nom d'image | | `docker login <registry>`, corriger nom/tag |
| Le build ignore ma modification | Cache de couches périmé | | `docker build --no-cache`, ou réordonner les `COPY` pour mettre les dépendances en cache à part |
| Compose : l'appli démarre avant la base | `depends_on` n'attend que le démarrage | `docker compose logs app` montre connection refused | Ajouter un `healthcheck` + `depends_on: { db: { condition: service_healthy } }` |

Appliquer la correction, puis vérifier :

```bash
docker compose up -d --build --force-recreate
docker compose ps
docker compose logs -f app
```

---

## Volumes et bind mounts

### Volumes

```bash
docker volume create pgdata
docker volume ls
docker volume inspect pgdata                   # Mountpoint, driver
docker volume rm pgdata
```

### Sauvegarder et restaurer un volume

```bash
docker run --rm -v pgdata:/data -v "$PWD":/backup alpine \
  tar czf /backup/pgdata.tgz -C /data .

docker run --rm -v pgdata:/data -v "$PWD":/backup alpine \
  tar xzf /backup/pgdata.tgz -C /data
```

| Type | Syntaxe | À utiliser pour |
|---|---|---|
| Volume nommé | `-v pgdata:/var/lib/...` | Données persistantes gérées par Docker |
| Bind mount | `-v "$PWD"/src:/app/src` | Édition à chaud du code source |
| tmpfs | `--tmpfs /tmp` | Données temporaires, jamais sur disque |

---

## Réseaux

### Bridge défini par l'utilisateur (les conteneurs se résolvent par leur nom)

```bash
docker network create backend
docker run -d --name db  --network backend postgres:16
docker run -d --name api --network backend -e DB_HOST=db myapp   # l'hôte "db" fonctionne
docker network ls
docker network inspect backend                 # conteneurs connectés + IP
docker network connect backend web             # rattacher un conteneur en cours d'exécution
docker network disconnect backend web
```

Le réseau `bridge` par défaut n'a **pas** de résolution de noms. Créez toujours votre propre réseau.

### Joindre l'hôte depuis un conteneur

```bash
# Docker Desktop (Mac/Windows) : host.docker.internal
# Linux : à ajouter soi-même
docker run --add-host=host.docker.internal:host-gateway myapp
```

### Tester la connectivité

```bash
docker exec api sh -c 'nc -zv db 5432'
docker exec api wget -qO- http://web:80
```

---

## Docker Compose

### compose.yaml

```yaml
services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/app
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
```

### Commandes quotidiennes

```bash
docker compose up -d                           # crée + démarre en arrière-plan
docker compose up -d --build                   # reconstruit d'abord les images
docker compose ps
docker compose logs -f api
docker compose exec db psql -U postgres app
docker compose run --rm api ./mvnw test        # conteneur ponctuel
docker compose restart api
docker compose stop                            # conserve les conteneurs
docker compose down                            # supprime conteneurs + réseau
docker compose down -v                         # ...et les volumes (supprime les données !)
docker compose config                          # affiche le fichier fusionné et résolu
```

### Fichiers de surcharge et profils

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d   # le dernier fichier surcharge les précédents
docker compose --profile debug up -d                       # services avec `profiles: [debug]`
```

---

## Nettoyage

### Espace disque et prune

```bash
docker system df                               # ce qui occupe de l'espace
docker container prune                         # conteneurs arrêtés
docker image prune                             # images dangling
docker image prune -a                          # toute image non utilisée par un conteneur
docker volume prune                            # volumes inutilisés (perte de données !)
docker network prune
docker builder prune                           # cache de build
docker system prune -a --volumes               # tout ce qui est inutilisé
```

### Suppression ciblée

```bash
docker rm $(docker ps -aq -f status=exited)
docker rmi $(docker images -q -f dangling=true)
docker container prune --filter "until=24h"
```

---

## Commandes utiles en une ligne

### Obtenir l'IP / l'environnement / les montages d'un conteneur

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' web
docker inspect -f '{{json .Config.Env}}' web | jq
docker inspect -f '{{json .Mounts}}' web | jq
```

### Tout arrêter

```bash
docker stop $(docker ps -q)
```

### Exécuter avec son propre utilisateur pour éviter les fichiers appartenant à root

```bash
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/work -w /work maven:3.9 mvn package
```
