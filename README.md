# my-docs

My personal tech docs — notes and references on Java, Spring, SQL, messaging, React/TypeScript, DevOps/Kubernetes, system design, and interview prep — built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

Published at: https://iheb-sahloul.github.io/my-docs/

## Building locally

**Prerequisites:** Python 3.x

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   If `pip` doesn't work, try `pip3` instead.


2. Serve the site locally with live reload:

   ```bash
   python3 -m mkdocs serve
   ```

   Then open http://127.0.0.1:8000 in your browser.

3. Before pushing, check that the build has no warnings (broken links, missing pages):

   ```bash
   python3 -m mkdocs build --strict
   ```

## Content

| Section | What it holds |
|---|---|
| `interviews/` | 14 interview modules (Q&A by level, real-world scenarios, oral quiz, cheat-sheet) + a readiness checklist (`mock-interview.md`). |
| `best-practices/` | Rules with ✅/⛔ examples: Git, Java, Spring Boot, testing, security, observability, REST, messaging, architecture, React, SQL/JPA, Docker/K8s, CI/CD, AI prompts |
| `resources/` | `further-reading.md`: curated links per topic (EN: English links, FR: French links) |
| `notes/` | Command-oriented cheat sheets: Git, Java, Maven/Gradle, SQL query tuning, Postgres, Docker, Kubernetes, Terraform, Linux, Kafka/RabbitMQ, curl/jq, AI |

Scenarios have a collapsed answer (`<details markdown="1">`, enabled by `md_in_html`): write your own hypotheses first, then open it.

## Translations

Content lives in `docs/en/` (default, served at `/`) and `docs/fr/` (served at `/fr/`). To translate a page, copy it into `docs/fr/` at the same relative path; untranslated pages fall back to English. Nav labels are translated in `mkdocs.yml` under `nav_translations`.

Keep EN and FR in sync when you edit a page, and check with `python3 -m mkdocs build --strict`.

Shared images stay in `docs/assets/`.

## Deployment

Pushes to `main` automatically trigger the [deploy workflow](.github/workflows/deploy.yml), which builds the site with `mkdocs gh-deploy` and publishes it to GitHub Pages.
