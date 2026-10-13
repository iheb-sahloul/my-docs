# Git Best Practices

## 📝 Commits

### Make small, atomic commits

One commit is one logical change that builds and passes tests on its own.

**Why it's a best practice:** a commit named "stuff" with 40 files can't be reviewed, reverted or bisected.
When production breaks, `git revert` of an atomic commit removes exactly one change; reverting a giant commit
also removes three unrelated fixes. `git bisect` finds the culprit in about log2(N) steps only if every
commit is buildable.

```bash
# ⛔
git add . && git commit -m "changes"

# ✅ stage by hunk, commit per idea
git add -p
git commit -m "fix(orders): reject negative quantities"
```

### Follow Conventional Commits

Format messages as `type(scope): summary`, with types such as `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

**Why it's a best practice:** a consistent format makes `git log --oneline` readable, and tools can generate
changelogs and pick the next semantic version (`feat` is minor, `fix` is patch, `!` is major) automatically.
Reviewers know from the prefix what to look for.

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

### Write the subject in the imperative, and explain why in the body

Keep the subject under about 50 characters ("Add", not "Added"), and use the body for the reason, not the diff.

**Why it's a best practice:** the diff already shows what changed; only the message can say why. Six months
later, `git blame` on a strange line leads to a message that either explains the decision or says "fix".
Imperative mood matches Git's own messages ("Merge...", "Revert...").

```text
# ⛔
fix(cache): fixed the thing

# ✅
fix(cache): evict entries on user update

The cache key ignored the tenant id, so users could see another tenant's
profile for up to 10 minutes after an update. Include the tenant in the key.

Closes #482
```

### Never rewrite history that others have pulled

Amend, rebase or force-push only your own unshared branches. Use `--force-with-lease` if you must.

**Why it's a best practice:** rewriting shared commits gives everyone else diverging histories, duplicate
commits and painful merges. Plain `--force` can also erase a teammate's push you haven't fetched;
`--force-with-lease` refuses if the remote moved.

```bash
# ⛔
git push --force origin main

# ✅ own feature branch only
git push --force-with-lease origin feature/login
```

## 🌿 Branching

### Use short-lived branches off main

Branch per task, merge within days, and delete the branch after merge. Prefer trunk-based development or GitHub Flow.

**Why it's a best practice:** the longer a branch lives, the more it diverges and the more painful the merge:
a 3-week branch can mean hundreds of conflicts and a risky big-bang release. Small frequent merges are easier to
review and cheaper to fix. Hide unfinished work behind a feature flag rather than a long branch.

```bash
# ⛔ feature/big-rewrite alive for 6 weeks

# ✅
git switch -c feat/order-export
# ... 1-3 days later: PR, review, merge, delete
git branch -d feat/order-export
```

### Name branches with a type and a ticket

Use `feat/`, `fix/`, `chore/` prefixes and, if you have a tracker, the ticket id.

**Why it's a best practice:** `my-branch2` says nothing on a list of 40 remote branches. Prefixes allow
filtering, CI rules (deploy from `release/*`) and links to tickets.

```text
# ⛔
test  fix  johns-branch

# ✅
feat/PAY-142-sepa-debit
fix/PAY-201-null-currency
```

### Protect the main branch

Require pull requests, at least one approval, and passing CI. Disallow force-push and direct commits.

**Why it's a best practice:** without protection, one bad push or a Friday-evening hotfix breaks the build for
everyone, or deploys untested code. Rules enforced by the platform apply to admins and tired humans equally.

```text
# ✅ GitHub branch protection on main
Require a pull request before merging (1 approval)
Require status checks: build, test
Block force pushes
Require linear history (optional)
```

## 🔍 Pull requests & reviews

### Keep pull requests small and focused

Aim for under about 400 changed lines and one purpose. Split refactors from behavior changes.

**Why it's a best practice:** review quality drops sharply with size: studies of code review show reviewers
find fewer defects after roughly 200 to 400 lines, and 2,000-line PRs get "LGTM" after a skim. Small PRs are
reviewed in minutes, merged the same day, and easy to revert.

```text
# ⛔
PR: "Refactor package layout + add export feature + upgrade Spring" (3,100 lines)

# ✅
PR 1: chore: upgrade Spring Boot 3.3 -> 3.4
PR 2: refactor: move order classes to order package (no behavior change)
PR 3: feat: CSV export of orders
```

### Write a pull request description that helps the reviewer

State what and why, how you tested it, and anything risky. Link the issue and add screenshots for UI changes.

**Why it's a best practice:** the reviewer lacks your context. A clear description turns a 30-minute puzzle
into a 5-minute review, and later serves as the record of a decision.

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

### Review the code, automate the style

Let formatters and linters (Spotless, Checkstyle) fail the build, so reviews focus on design, correctness and tests.

**Why it's a best practice:** arguments about braces waste review time and irritate people. A tool is
consistent and never tired. Reviewers then have the energy to find the missing null check or race condition.

```xml
<!-- ✅ pom.xml -->
<plugin>
  <groupId>com.diffplug.spotless</groupId>
  <artifactId>spotless-maven-plugin</artifactId>
</plugin>
```

## 🔀 Integrating changes

### Rebase your local branch, merge (or squash) into main

Rebase a private feature branch on the latest main to update it. Integrate into main by squash or merge commit through the PR.

**Why it's a best practice:** rebasing your own branch keeps the history linear and free of "Merge main into
feature" noise. Squash-merge gives one clean commit per PR on main, which is easy to revert. Rebasing a shared
branch, however, rewrites commits others have (see the history rule above).

```bash
# ✅ update your private branch
git fetch origin
git rebase origin/main

# ✅ tidy noisy commits before review
git rebase -i origin/main
```

### Resolve conflicts on purpose, and enable rerere

Read both sides, run the tests after resolving, and turn on `git rerere` to remember resolutions.

**Why it's a best practice:** picking "ours" or "theirs" for a whole file silently drops someone's work.
Resolved conflicts that were never compiled are a frequent cause of broken main. `rerere` replays a resolution
you already made when the same conflict appears again during a repeated rebase.

```bash
# ✅
git config --global rerere.enabled true
git config --global merge.conflictstyle zdiff3
```

## 🔐 Safety & automation

### Never commit secrets, and scan for them

Keep keys and passwords out of Git, use `.gitignore`, and run a scanner (gitleaks) in a pre-commit hook and in CI.

**Why it's a best practice:** removing a file in a later commit doesn't remove it from history, and anyone who
cloned already has it. Bots find pushed cloud keys in minutes. The only real fix is to rotate the credential;
rewriting history is cleanup, not a cure.

```bash
# ⛔
git add .env && git commit -m "add config"

# ✅
echo ".env" >> .gitignore
gitleaks protect --staged      # in a pre-commit hook
```

### Automate checks with Git hooks

Use pre-commit hooks (Husky, lefthook, pre-commit) for formatting and secrets, and commit-msg for message rules. Repeat them in CI.

**Why it's a best practice:** catching a formatting error or a leaked key in 2 seconds locally is better than a
failed pipeline 10 minutes later. Hooks can be skipped (`--no-verify`), so CI stays the real gate.

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

### Tag releases with annotated, semantic-version tags

Create `vMAJOR.MINOR.PATCH` annotated tags on the released commit and push them.

**Why it's a best practice:** a tag is the permanent answer to "what code is running in production?". Annotated
tags store the tagger, date and message, and can be signed. Lightweight or moved tags make releases
unreproducible. Never move a published tag: cached builds and consumers will differ from what you now claim.

```bash
# ⛔
git tag latest && git tag -f latest      # moving target

# ✅
git tag -a v1.4.0 -m "Release 1.4.0: SEPA debit"
git push origin v1.4.0
```

### Keep generated files and large binaries out of Git

Ignore build output (`target/`, `node_modules/`) and store big binaries in Git LFS or an artifact registry.

**Why it's a best practice:** every version of a binary stays in history forever: ten 50 MB jars make each clone
500 MB heavier. Generated files cause pointless merge conflicts.

```gitignore
# ✅ .gitignore
target/
build/
.idea/
*.log
.env
```

### Recover with reflog instead of panicking

Use `git reflog` to find lost commits, and prefer `git revert` for published mistakes.

**Why it's a best practice:** Git rarely destroys committed work: for about 90 days the reflog still points to
commits after a bad reset or rebase. `revert` adds an undo commit and is safe for shared branches, while
`reset --hard` rewrites and discards.

```bash
# ✅ undo a bad rebase
git reflog
git reset --hard HEAD@{5}

# ✅ undo a commit already on main
git revert 9fceb02
```
