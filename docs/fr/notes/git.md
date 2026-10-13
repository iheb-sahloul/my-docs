# Git

## Annuler des erreurs

### Annuler ou retirer de l'index des modifications

```bash
git restore file.txt                     # annule les modifications non indexées (irrécupérable)
git restore --staged file.txt            # retire de l'index, conserve les modifications
git restore --source=HEAD~2 file.txt     # fichier tel qu'il était il y a 2 commits
git clean -nd                            # simulation : fichiers/dossiers non suivis à supprimer
git clean -fd                            # les supprime
```

### Corriger le dernier commit

```bash
git commit --amend                       # modifier le message
git add forgotten.txt && git commit --amend --no-edit   # ajouter un fichier, garder le message
git commit --amend --author="Name <me@example.com>" --no-edit
```

### Annuler des commits

```bash
git reset --soft HEAD~1                  # annule le commit, garde les changements indexés
git reset HEAD~1                         # annule le commit, garde les changements non indexés (--mixed)
git reset --hard HEAD~1                  # annule le commit et SUPPRIME les changements
git revert <hash>                        # nouveau commit qui inverse <hash> (sûr sur les branches partagées)
git revert -m 1 <merge-hash>             # annule un merge, garde le parent 1 comme ligne principale
git revert HEAD~3..HEAD                  # annule les 3 derniers commits
```

| Commande | Réécrit l'historique ? | Utilisable sur des commits poussés ? |
|---|---|---|
| `revert` | Non | Oui |
| `reset` | Oui | Non (nécessite un force push) |
| `commit --amend` | Oui | Non |

### Commit sur la mauvaise branche

```bash
git switch -c feature/right-branch       # nouvelle branche au commit courant
git switch main
git reset --hard origin/main             # ramène main en arrière
```

### Force push en sécurité

```bash
git push --force-with-lease              # refuse si quelqu'un d'autre a poussé entre-temps
```

---

## Stash

```bash
git stash                                # changements suivis
git stash push -u -m "wip: login form"   # inclut les fichiers non suivis, avec un nom
git stash push -p                        # choisir les hunks de façon interactive
git stash push -- src/Foo.java           # un seul chemin
git stash list
```

```text
stash@{0}: On main: wip: login form
stash@{1}: WIP on main: 3f2a1bc Fix typo
```

```bash
git stash show -p stash@{0}              # voir le diff
git stash pop                            # applique le dernier et le supprime
git stash apply stash@{1}                # applique et le conserve
git stash branch fix-login stash@{0}     # nouvelle branche depuis la base du stash
git stash drop stash@{1}
git stash clear                          # supprime tout (attention)
```

---

## Rebase interactif

### Nettoyer les N derniers commits

```bash
git rebase -i HEAD~4
git rebase -i origin/main                # tout depuis la création de la branche
```

```text
pick   a1b2c3 Add login endpoint
squash d4e5f6 fix typo
reword 7a8b9c Add tests
drop   0d1e2f debug logging
```

| Commande | Effet |
|---|---|
| `pick` | Conserver tel quel |
| `reword` | Conserver, modifier le message |
| `edit` | S'arrêter pour amender le commit ou le scinder |
| `squash` | Fusionner dans le commit précédent, combiner les messages |
| `fixup` | Comme squash, mais ignore ce message |
| `drop` | Supprimer le commit |

### Workflow autosquash

```bash
git commit --fixup a1b2c3                # marque un correctif pour un commit antérieur
git rebase -i --autosquash origin/main   # les fixups sont réordonnés automatiquement
git config --global rebase.autosquash true
```

### Rebase onto et conflits

```bash
git rebase main                          # rejoue ma branche par-dessus main
git rebase --onto main old-base feature  # déplace feature de old-base vers main
git rebase --continue                    # après avoir résolu les conflits et fait `git add`
git rebase --skip
git rebase --abort                       # retour à l'état initial
```

Ne jamais rebaser des commits que d'autres ont déjà récupérés. Utilisez `pull --rebase` pour vos propres commits locaux.

---

## Cherry-pick

```bash
git cherry-pick a1b2c3                   # copie un commit sur la branche courante
git cherry-pick a1b2c3 d4e5f6            # plusieurs
git cherry-pick a1b2c3..f6e5d4           # intervalle (exclut le premier)
git cherry-pick -x a1b2c3                # ajoute "(cherry picked from ...)" au message
git cherry-pick -n a1b2c3                # applique sans committer
git cherry-pick -m 1 <merge-hash>        # cherry-pick d'un commit de merge
git cherry-pick --continue               # après résolution des conflits
git cherry-pick --abort
```

Usage typique : hotfix sur `main`, puis `git cherry-pick <hash>` vers `release/1.4`.

---

## Bisect ([`Exemple`](https://www.facebook.com/reel/938159275380021))

```bash
git log --oneline -50
git bisect start                         # ou : git bisect start HEAD v1.4.0 (bad, good)
git bisect bad <bad-commit-hash>
git bisect good <good-commit-hash>
git bisect good | bad | skip             # réponse pour chaque commit extrait par git
git bisect run node test.js              # automatiser : exit 0 = good, 1-127 = bad, 125 = skip
git bisect run ./mvnw -q test -Dtest=OrderServiceTest
git bisect log                           # ce que vous avez décidé jusqu'ici
git show refs/bisect/bad                 # le premier mauvais commit
git bisect reset                         # revenir à la normale une fois le mauvais changement trouvé
```

Git a besoin d'environ log2(N) étapes : 1000 commits nécessitent ~10 tests.

---

## Reflog

Enregistre, en local, où pointaient `HEAD` et les branches pendant ~90 jours. C'est le bouton « annuler » après un reset, un mauvais rebase ou une branche supprimée.

```bash
git reflog
```

```text
3f2a1bc HEAD@{0}: reset: moving to HEAD~3
9d8c7b6 HEAD@{1}: commit: Add invoice export
5e4d3c2 HEAD@{2}: rebase (finish): returning to refs/heads/feature
```

```bash
git reset --hard HEAD@{1}                # revenir à avant le reset
git branch rescue 9d8c7b6                # ou conserver le commit perdu sur une branche
git reflog show feature                  # reflog d'une seule branche
git checkout -b restored $(git rev-list -n 1 --before="yesterday" HEAD)
```

---

## Worktrees

Plusieurs branches extraites en même temps, partageant un seul `.git`. Pas besoin de stash pour basculer sur un hotfix.

```bash
git worktree add ../hotfix hotfix/123            # branche existante dans un nouveau dossier
git worktree add -b feature/x ../feature-x main  # crée la branche depuis main
git worktree list
git worktree remove ../hotfix
git worktree prune                               # nettoie les entrées des dossiers supprimés
```

La même branche ne peut pas être extraite dans deux worktrees.

---

## Tags

```bash
git tag v1.2.0                           # léger (lightweight)
git tag -a v1.2.0 -m "Release 1.2.0"     # annoté (à utiliser pour les releases)
git tag -a v1.1.0 a1b2c3 -m "late tag"   # taguer un ancien commit
git tag -l "v1.*"
git show v1.2.0
git push origin v1.2.0                   # les tags ne sont pas poussés par défaut
git push origin --tags
git tag -d v1.2.0                        # suppression locale
git push origin --delete v1.2.0          # suppression distante
git describe --tags                      # ex. v1.2.0-5-g3f2a1bc
git checkout v1.2.0                      # HEAD détaché, consultation en lecture seule
```

---

## Inspecter l'historique

```bash
git log --oneline --graph --decorate --all
git log -p -- path/to/file               # patchs touchant un fichier
git log -S"calculateTax" --oneline       # commits qui ont ajouté/supprimé cette chaîne
git log -G"regex" --oneline
git log --author="Iheb" --since="2 weeks ago"
git log main..feature                    # commits dans feature absents de main
git blame -L 10,30 file.txt
git diff main...feature                  # changements sur feature depuis la divergence
git diff --stat
git shortlog -sn --no-merges             # commits par auteur
git branch --merged main                 # suppression sans risque
git branch -vv                           # informations de suivi
```

---

## Configuration et alias utiles

### Configuration

```bash
git config --global user.name "Iheb Sahloul"
git config --global user.email "me@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase true             # pull = fetch + rebase
git config --global fetch.prune true             # supprime les branches distantes effacées
git config --global rerere.enabled true          # mémorise les résolutions de conflits
git config --global push.autoSetupRemote true    # le premier push définit l'upstream
git config --global core.editor "code --wait"
git config --global diff.algorithm histogram
git config --global merge.conflictstyle zdiff3
git config --global --list --show-origin
```

### Alias

```bash
git config --global alias.st "status -sb"
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.co "checkout"
git config --global alias.undo "reset --soft HEAD~1"
git config --global alias.last "log -1 --stat"
git config --global alias.amend "commit --amend --no-edit"
git config --global alias.wip "!git add -A && git commit -m wip"
```

### Identité par dossier (~/.gitconfig)

```text
[includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work
```

### Ignorer avec .gitignore des fichiers déjà suivis

```bash
git rm --cached secrets.env              # arrête le suivi mais garde le fichier sur disque
echo "secrets.env" >> .gitignore
git check-ignore -v secrets.env          # quelle règle l'ignore ?
```
