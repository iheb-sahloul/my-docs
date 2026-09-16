# my-docs

My personal tech docs — notes and references on Java, Spring, SQL, messaging, React/TypeScript, DevOps/Kubernetes, system design, and interview prep — built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

Published at: https://iheb-sahloul.github.io/my-docs/

## Building locally

**Prerequisites:** Python 3.x

1. (Optional) create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install MkDocs Material:

   ```bash
   pip install mkdocs-material
   ```

3. Serve the site locally with live reload:

   ```bash
   mkdocs serve
   ```

   Then open http://127.0.0.1:8000 in your browser.

4. Or build the static site into `site/`:

   ```bash
   mkdocs build
   ```

## Deployment

Pushes to `main` automatically trigger the [deploy workflow](.github/workflows/deploy.yml), which builds the site with `mkdocs gh-deploy` and publishes it to GitHub Pages.
