# Bonnes pratiques Git

## 📝 Commits

### Faites des commits petits et atomiques

Un commit est un changement logique qui compile et passe les tests par lui-même.

**Pourquoi c'est une bonne pratique :** un commit nommé « stuff » avec 40 fichiers ne peut être ni relu, ni annulé,
ni bisecté. Quand la production casse, `git revert` d'un commit atomique retire exactement un changement ; annuler
un commit géant retire aussi trois correctifs sans rapport. `git bisect` trouve le coupable en environ log2(N)
étapes seulement si chaque commit compile.

```bash
# ⛔
git add . && git commit -m "changes"

# ✅ indexer par hunk, un commit par idée
git add -p
git commit -m "fix(orders): reject negative quantities"
```

### Suivez Conventional Commits

Formatez les messages en `type(scope): résumé`, avec des types comme `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

**Pourquoi c'est une bonne pratique :** un format cohérent rend `git log --oneline` lisible, et des outils peuvent
générer les changelogs et choisir automatiquement la prochaine version sémantique (`feat` est mineure, `fix` est
correctif, `!` est majeure). Les relecteurs savent grâce au préfixe ce qu'ils doivent chercher.

```text
# ⛔
fixed bug
WIP
update

# ✅
feat(payments): add SEPA direct debit
fix(auth): refresh token before expiry
feat(api)!: remove deprecated /v1/users endpoint
```

### Rédigez le sujet à l'impératif, et expliquez le pourquoi dans le corps

Gardez le sujet sous environ 50 caractères (« Add », pas « Added »), et utilisez le corps pour la raison, pas pour le diff.

**Pourquoi c'est une bonne pratique :** le diff montre déjà ce qui a changé ; seul le message peut dire pourquoi. Six
mois plus tard, `git blame` sur une ligne étrange mène à un message qui explique la décision ou qui dit « fix ».
L'impératif correspond aux propres messages de Git (« Merge... », « Revert... »).

```text
# ⛔
fix(cache): fixed the thing

# ✅
fix(cache): evict entries on user update

The cache key ignored the tenant id, so users could see another tenant's
profile for up to 10 minutes after an update. Include the tenant in the key.

Closes #482
```

### Ne réécrivez jamais un historique que d'autres ont récupéré

Faites amend, rebase ou force-push uniquement sur vos propres branches non partagées. Utilisez `--force-with-lease` si vous devez.

**Pourquoi c'est une bonne pratique :** réécrire des commits partagés donne aux autres des historiques divergents,
des commits en double et des merges douloureux. Un simple `--force` peut aussi effacer le push d'un collègue que
vous n'avez pas récupéré ; `--force-with-lease` refuse si le distant a bougé.

```bash
# ⛔
git push --force origin main

# ✅ uniquement sur votre propre branche de fonctionnalité
git push --force-with-lease origin feature/login
```

## 🌿 Branches

### Utilisez des branches de courte durée issues de main

Une branche par tâche, un merge en quelques jours, et suppression de la branche après le merge. Préférez le trunk-based development ou GitHub Flow.

**Pourquoi c'est une bonne pratique :** plus une branche vit longtemps, plus elle diverge et plus le merge est
douloureux : une branche de 3 semaines peut signifier des centaines de conflits et une livraison big-bang risquée.
De petits merges fréquents sont plus faciles à relire et moins chers à corriger. Cachez le travail inachevé derrière
un feature flag plutôt qu'une longue branche.

```bash
# ⛔ feature/big-rewrite vivante pendant 6 semaines

# ✅
git switch -c feat/order-export
# ... 1 à 3 jours plus tard : PR, relecture, merge, suppression
git branch -d feat/order-export
```

### Nommez les branches avec un type et un ticket

Utilisez les préfixes `feat/`, `fix/`, `chore/` et, si vous avez un outil de suivi, l'id du ticket.

**Pourquoi c'est une bonne pratique :** `my-branch2` ne dit rien dans une liste de 40 branches distantes. Les
préfixes permettent le filtrage, des règles de CI (déployer depuis `release/*`) et des liens vers les tickets.

```text
# ⛔
test  fix  johns-branch

# ✅
feat/PAY-142-sepa-debit
fix/PAY-201-null-currency
```

### Protégez la branche main

Exigez des pull requests, au moins une approbation, et une CI qui passe. Interdisez le force-push et les commits directs.

**Pourquoi c'est une bonne pratique :** sans protection, un mauvais push ou un correctif urgent du vendredi soir casse
le build pour tout le monde, ou déploie du code non testé. Les règles imposées par la plateforme s'appliquent de la
même façon aux admins et aux humains fatigués.

```text
# ✅ protection de branche GitHub sur main
Require a pull request before merging (1 approval)
Require status checks: build, test
Block force pushes
Require linear history (optional)
```

## 🔍 Pull requests & relectures

### Gardez les pull requests petites et ciblées

Visez moins d'environ 400 lignes modifiées et un seul objectif. Séparez les refactorings des changements de comportement.

**Pourquoi c'est une bonne pratique :** la qualité de la relecture chute fortement avec la taille : les études sur la
revue de code montrent que les relecteurs trouvent moins de défauts au-delà d'environ 200 à 400 lignes, et les PR
de 2 000 lignes reçoivent un « LGTM » après un survol. Les petites PR sont relues en quelques minutes, mergées le
jour même, et faciles à annuler.

```text
# ⛔
PR: "Refactor package layout + add export feature + upgrade Spring" (3,100 lines)

# ✅
PR 1: chore: upgrade Spring Boot 3.3 -> 3.4
PR 2: refactor: move order classes to order package (no behavior change)
PR 3: feat: CSV export of orders
```

### Rédigez une description de pull request qui aide le relecteur

Dites quoi et pourquoi, comment vous l'avez testé, et tout ce qui est risqué. Liez le ticket et ajoutez des captures d'écran pour les changements d'UI.

**Pourquoi c'est une bonne pratique :** le relecteur n'a pas votre contexte. Une description claire transforme un
casse-tête de 30 minutes en une relecture de 5 minutes, et sert ensuite de trace d'une décision.

```markdown
## What
Add CSV export for orders (max 10k rows).
## Why
Support requests #482, #501.
## How tested
Unit tests + manual export with 10k rows (2.1 s).
## Risk
New endpoint only; no schema changes.
```

### Relisez le code, automatisez le style

Laissez les formateurs et linters (Spotless, Checkstyle) faire échouer le build, pour que les relectures se concentrent sur la conception, la justesse et les tests.

**Pourquoi c'est une bonne pratique :** les discussions sur les accolades font perdre du temps de relecture et
irritent. Un outil est cohérent et jamais fatigué. Les relecteurs ont alors l'énergie de trouver la vérification de
null manquante ou la race condition.

```xml
<!-- ✅ pom.xml -->
<plugin>
  <groupId>com.diffplug.spotless</groupId>
  <artifactId>spotless-maven-plugin</artifactId>
</plugin>
```

## 🔀 Intégrer les changements

### Rebasez votre branche locale, mergez (ou squashez) dans main

Rebasez une branche de fonctionnalité privée sur le dernier main pour la mettre à jour. Intégrez dans main par squash ou commit de merge via la PR.

**Pourquoi c'est une bonne pratique :** rebaser votre propre branche garde l'historique linéaire et sans le bruit
« Merge main into feature ». Le squash-merge donne un commit propre par PR sur main, facile à annuler. Rebaser une
branche partagée, en revanche, réécrit des commits que d'autres possèdent (voir la règle sur l'historique
ci-dessus).

```bash
# ✅ mettre à jour votre branche privée
git fetch origin
git rebase origin/main

# ✅ nettoyer les commits bruyants avant la relecture
git rebase -i origin/main
```

### Résolvez les conflits délibérément, et activez rerere

Lisez les deux côtés, lancez les tests après la résolution, et activez `git rerere` pour mémoriser les résolutions.

**Pourquoi c'est une bonne pratique :** choisir « ours » ou « theirs » pour un fichier entier supprime
silencieusement le travail de quelqu'un. Des conflits résolus sans jamais avoir été compilés sont une cause fréquente
de main cassée. `rerere` rejoue une résolution que vous avez déjà faite quand le même conflit réapparaît pendant un
rebase répété.

```bash
# ✅
git config --global rerere.enabled true
git config --global merge.conflictstyle zdiff3
```

## 🔐 Sécurité & automatisation

### Ne commitez jamais de secrets, et scannez-les

Gardez les clés et mots de passe hors de Git, utilisez `.gitignore`, et lancez un scanner (gitleaks) dans un hook de pre-commit et en CI.

**Pourquoi c'est une bonne pratique :** supprimer un fichier dans un commit ultérieur ne le retire pas de l'historique,
et quiconque a cloné l'a déjà. Les bots trouvent les clés cloud poussées en quelques minutes. La seule vraie
solution est de renouveler l'identifiant ; réécrire l'historique est un nettoyage, pas un remède.

```bash
# ⛔
git add .env && git commit -m "add config"

# ✅
echo ".env" >> .gitignore
gitleaks protect --staged      # dans un hook de pre-commit
```

### Automatisez les vérifications avec les hooks Git

Utilisez des hooks de pre-commit (Husky, lefthook, pre-commit) pour le formatage et les secrets, et commit-msg pour les règles de message. Répétez-les en CI.

**Pourquoi c'est une bonne pratique :** attraper une erreur de formatage ou une clé fuitée en 2 secondes en local vaut
mieux qu'un pipeline en échec 10 minutes plus tard. Les hooks peuvent être contournés (`--no-verify`), donc la CI
reste la vraie barrière.

```yaml
# ✅ lefthook.yml
pre-commit:
  commands:
    format: { run: ./mvnw -q spotless:apply }
    secrets: { run: gitleaks protect --staged }
commit-msg:
  commands:
    conventional: { run: npx commitlint --edit {1} }
```

### Taguez les releases avec des tags annotés en versionnage sémantique

Créez des tags annotés `vMAJOR.MINOR.PATCH` sur le commit livré et poussez-les.

**Pourquoi c'est une bonne pratique :** un tag est la réponse permanente à « quel code tourne en production ? ». Les
tags annotés stockent l'auteur, la date et le message, et peuvent être signés. Les tags légers ou déplacés rendent
les releases non reproductibles. Ne déplacez jamais un tag publié : les builds en cache et les consommateurs
différeront de ce que vous affirmez maintenant.

```bash
# ⛔
git tag latest && git tag -f latest      # cible mouvante

# ✅
git tag -a v1.4.0 -m "Release 1.4.0: SEPA debit"
git push origin v1.4.0
```

### Gardez les fichiers générés et les gros binaires hors de Git

Ignorez les sorties de build (`target/`, `node_modules/`) et stockez les gros binaires dans Git LFS ou un registre d'artefacts.

**Pourquoi c'est une bonne pratique :** chaque version d'un binaire reste dans l'historique pour toujours : dix jars de
50 Mo alourdissent chaque clone de 500 Mo. Les fichiers générés causent des conflits de merge inutiles.

```gitignore
# ✅ .gitignore
target/
build/
.idea/
*.log
.env
```

### Récupérez avec le reflog plutôt que de paniquer

Utilisez `git reflog` pour retrouver des commits perdus, et préférez `git revert` pour les erreurs publiées.

**Pourquoi c'est une bonne pratique :** Git détruit rarement le travail commité : pendant environ 90 jours, le reflog
pointe encore vers les commits après un mauvais reset ou rebase. `revert` ajoute un commit d'annulation et est sûr
pour les branches partagées, alors que `reset --hard` réécrit et supprime.

```bash
# ✅ annuler un mauvais rebase
git reflog
git reset --hard HEAD@{5}

# ✅ annuler un commit déjà sur main
git revert 9fceb02
```
