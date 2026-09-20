# my-docs

My personal tech docs — notes and references on Java, Spring, SQL, messaging, React/TypeScript, DevOps/Kubernetes, system design, and interview prep — built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

Published at: https://iheb-sahloul.github.io/my-docs/

## Building locally

**Prerequisites:** Python 3.x

1. Install MkDocs Material:

   ```bash
   pip install mkdocs-material mkdocs-static-i18n
   ```

   If `pip` doesn't work, try `pip3` instead.


2. Serve the site locally with live reload:

   ```bash
   python3 -m mkdocs serve
   ```

   Then open http://127.0.0.1:8000 in your browser.

## Translations

Content lives in `docs/en/` (default, served at `/`) and `docs/fr/` (served at `/fr/`). To translate a page, copy it into `docs/fr/` at the same relative path; untranslated pages fall back to English. Shared images stay in `docs/assets/`.

## Deployment

Pushes to `main` automatically trigger the [deploy workflow](.github/workflows/deploy.yml), which builds the site with `mkdocs gh-deploy` and publishes it to GitHub Pages.
