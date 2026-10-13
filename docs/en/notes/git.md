# Git

## Undo mistakes

### Discard or unstage changes

```bash
git restore file.txt                     # discard unstaged changes (unrecoverable)
git restore --staged file.txt            # unstage, keep the edits
git restore --source=HEAD~2 file.txt     # file as it was 2 commits ago
git clean -nd                            # dry run: untracked files/dirs to delete
git clean -fd                            # delete them
```

### Fix the last commit

```bash
git commit --amend                       # edit the message
git add forgotten.txt && git commit --amend --no-edit   # add a file, keep the message
git commit --amend --author="Name <me@example.com>" --no-edit
```

### Undo commits

```bash
git reset --soft HEAD~1                  # undo commit, keep changes staged
git reset HEAD~1                         # undo commit, keep changes unstaged (--mixed)
git reset --hard HEAD~1                  # undo commit and DROP the changes
git revert <hash>                        # new commit that reverses <hash> (safe on shared branches)
git revert -m 1 <merge-hash>             # revert a merge, keep parent 1 as mainline
git revert HEAD~3..HEAD                  # revert the last 3 commits
```

| Command | Rewrites history? | Use on pushed commits? |
|---|---|---|
| `revert` | No | Yes |
| `reset` | Yes | No (needs force push) |
| `commit --amend` | Yes | No |

### Committed to the wrong branch

```bash
git switch -c feature/right-branch       # new branch at current commit
git switch main
git reset --hard origin/main             # move main back
```

### Force push safely

```bash
git push --force-with-lease              # refuses if someone else pushed meanwhile
```

---

## Stash

```bash
git stash                                # tracked changes
git stash push -u -m "wip: login form"   # include untracked files, with a name
git stash push -p                        # choose hunks interactively
git stash push -- src/Foo.java           # only one path
git stash list
```

```text
stash@{0}: On main: wip: login form
stash@{1}: WIP on main: 3f2a1bc Fix typo
```

```bash
git stash show -p stash@{0}              # see the diff
git stash pop                            # apply latest and drop it
git stash apply stash@{1}                # apply and keep it
git stash branch fix-login stash@{0}     # new branch from the stash's base
git stash drop stash@{1}
git stash clear                          # delete all (careful)
```

---

## Interactive rebase

### Clean up the last N commits

```bash
git rebase -i HEAD~4
git rebase -i origin/main                # everything since branching
```

```text
pick   a1b2c3 Add login endpoint
squash d4e5f6 fix typo
reword 7a8b9c Add tests
drop   0d1e2f debug logging
```

| Command | Effect |
|---|---|
| `pick` | Keep as is |
| `reword` | Keep, edit the message |
| `edit` | Stop to amend the commit or split it |
| `squash` | Meld into the previous commit, combine messages |
| `fixup` | Like squash, discard this message |
| `drop` | Delete the commit |

### Autosquash workflow

```bash
git commit --fixup a1b2c3                # mark a fix for an earlier commit
git rebase -i --autosquash origin/main   # fixups are reordered automatically
git config --global rebase.autosquash true
```

### Rebase onto and conflicts

```bash
git rebase main                          # replay my branch on top of main
git rebase --onto main old-base feature  # move feature from old-base onto main
git rebase --continue                    # after fixing conflicts and `git add`
git rebase --skip
git rebase --abort                       # back to how it was
```

Never rebase commits others already pulled. Use `pull --rebase` for your own local commits.

---

## Cherry-pick

```bash
git cherry-pick a1b2c3                   # copy one commit onto the current branch
git cherry-pick a1b2c3 d4e5f6            # several
git cherry-pick a1b2c3..f6e5d4           # range (excludes the first)
git cherry-pick -x a1b2c3                # append "(cherry picked from ...)" to the message
git cherry-pick -n a1b2c3                # apply without committing
git cherry-pick -m 1 <merge-hash>        # pick a merge commit
git cherry-pick --continue               # after resolving conflicts
git cherry-pick --abort
```

Typical use: hotfix on `main`, then `git cherry-pick <hash>` onto `release/1.4`.

---

## Bisect ([`Example`](https://www.facebook.com/reel/938159275380021))

```bash
git log --oneline -50
git bisect start                         # or: git bisect start HEAD v1.4.0 (bad, good)
git bisect bad <bad-commit-hash>
git bisect good <good-commit-hash>
git bisect good | bad | skip             # answer for each commit git checks out
git bisect run node test.js              # automate: exit 0 = good, 1-127 = bad, 125 = skip
git bisect run ./mvnw -q test -Dtest=OrderServiceTest
git bisect log                           # what you decided so far
git show refs/bisect/bad                 # the first bad commit
git bisect reset                         # return to normal once the bad change is found
```

Git needs about log2(N) steps: 1000 commits take ~10 tests.

---

## Reflog

Records where `HEAD` and branches pointed, locally, for ~90 days. It is the undo button for resets, bad rebases and deleted branches.

```bash
git reflog
```

```text
3f2a1bc HEAD@{0}: reset: moving to HEAD~3
9d8c7b6 HEAD@{1}: commit: Add invoice export
5e4d3c2 HEAD@{2}: rebase (finish): returning to refs/heads/feature
```

```bash
git reset --hard HEAD@{1}                # go back to before the reset
git branch rescue 9d8c7b6                # or keep the lost commit on a branch
git reflog show feature                  # reflog of one branch
git checkout -b restored $(git rev-list -n 1 --before="yesterday" HEAD)
```

---

## Worktrees

Several branches checked out at once, sharing one `.git`. No stashing to jump to a hotfix.

```bash
git worktree add ../hotfix hotfix/123            # existing branch in a new dir
git worktree add -b feature/x ../feature-x main  # create branch from main
git worktree list
git worktree remove ../hotfix
git worktree prune                               # clean up records of deleted dirs
```

The same branch cannot be checked out in two worktrees.

---

## Tags

```bash
git tag v1.2.0                           # lightweight
git tag -a v1.2.0 -m "Release 1.2.0"     # annotated (use this for releases)
git tag -a v1.1.0 a1b2c3 -m "late tag"   # tag an old commit
git tag -l "v1.*"
git show v1.2.0
git push origin v1.2.0                   # tags are not pushed by default
git push origin --tags
git tag -d v1.2.0                        # delete locally
git push origin --delete v1.2.0          # delete remotely
git describe --tags                      # e.g. v1.2.0-5-g3f2a1bc
git checkout v1.2.0                      # detached HEAD, read-only browsing
```

---

## Inspecting history

```bash
git log --oneline --graph --decorate --all
git log -p -- path/to/file               # patches touching a file
git log -S"calculateTax" --oneline       # commits that added/removed this string
git log -G"regex" --oneline
git log --author="Iheb" --since="2 weeks ago"
git log main..feature                    # commits in feature not in main
git blame -L 10,30 file.txt
git diff main...feature                  # changes on feature since it forked
git diff --stat
git shortlog -sn --no-merges             # commits per author
git branch --merged main                 # safe to delete
git branch -vv                           # tracking info
```

---

## Useful config and aliases

### Config

```bash
git config --global user.name "Iheb Sahloul"
git config --global user.email "me@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase true             # pull = fetch + rebase
git config --global fetch.prune true             # drop deleted remote branches
git config --global rerere.enabled true          # remember conflict resolutions
git config --global push.autoSetupRemote true    # first push sets upstream
git config --global core.editor "code --wait"
git config --global diff.algorithm histogram
git config --global merge.conflictstyle zdiff3
git config --global --list --show-origin
```

### Aliases

```bash
git config --global alias.st "status -sb"
git config --global alias.lg "log --oneline --graph --decorate --all"
git config --global alias.co "checkout"
git config --global alias.undo "reset --soft HEAD~1"
git config --global alias.last "log -1 --stat"
git config --global alias.amend "commit --amend --no-edit"
git config --global alias.wip "!git add -A && git commit -m wip"
```

### Per-directory identity (~/.gitconfig)

```text
[includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work
```

### .gitignore already-tracked files

```bash
git rm --cached secrets.env              # untrack but keep on disk
echo "secrets.env" >> .gitignore
git check-ignore -v secrets.env          # which rule ignores it?
```
