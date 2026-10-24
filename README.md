# my-docs

My personal tech docs — notes and references on Java, Spring, SQL, messaging, React/TypeScript, DevOps/Kubernetes, system design, and interview prep — built with [Zensical](https://zensical.org/).

Published at: https://iheb-sahloul.github.io/my-docs/

## Building locally

**Prerequisites:** Python 3.10+

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   If `pip` doesn't work, try `pip3` instead.


2. Serve the site locally with live reload:

   ```bash
   zensical serve                      # English
   zensical serve -f mkdocs.fr.yml     # French
   ```

   Then open http://127.0.0.1:8000 in your browser.

3. Before pushing, check that the build has no warnings (broken links, missing pages):

   ```bash
   zensical build --strict && zensical build --strict -f mkdocs.fr.yml
   ```

   Build EN first: it cleans `site/`, then FR builds into `site/fr/`.

## Content

| Section | What it holds |
|---|---|
| `interviews/` | 19 interview modules (Q&A by level, real-world scenarios, oral quiz, cheat-sheet) + a readiness checklist (`mock-interview.md`). |
| `best-practices/` | Rules with ✅/⛔ examples: Git, Java, Spring Boot, testing, security, observability, REST, messaging, architecture, React, SQL/JPA, Docker/K8s, CI/CD, AI prompts |
| `resources/` | `further-reading.md`: curated links per topic (EN: English links, FR: French links) |
| `notes/` | Command-oriented cheat sheets: Git, Java, Maven/Gradle, SQL query tuning, Postgres, Docker, Kubernetes, Terraform, Linux, Kafka/RabbitMQ, curl/jq, AI |

Scenarios have a collapsed answer (`<details markdown="1">`, enabled by `md_in_html`): write your own hypotheses first, then open it.

## Translations

Content lives in `docs/en/` (default, served at `/`) and `docs/fr/` (served at `/fr/`). Each language is its own build: `mkdocs.yml` (EN) and `mkdocs.fr.yml` (FR), both inheriting the shared theme and extensions from `mkdocs.base.yml`. There is no fallback to English: every page needs its twin in `docs/fr/` at the same relative path, and the page must be listed in both files' `nav` (French labels go in `mkdocs.fr.yml`).

Keep EN and FR in sync when you edit a page, and check with `python3 scripts/check_docs.py` and the two strict builds above.

Images go next to the page in both `docs/en/` and `docs/fr/`; `docs/assets/` is outside both builds and is not published.

## Deployment

Pushes to `main` automatically trigger the [deploy workflow](.github/workflows/deploy.yml), which builds both languages with Zensical and publishes `site/` to GitHub Pages (Settings → Pages → Source: GitHub Actions).

To deploy by hand (any branch), go to Actions → 🚀 Deployment → Run workflow and enter the branch name.
