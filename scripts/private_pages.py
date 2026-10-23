"""mkdocs hook: serve the git-ignored private/*.md under fr/private/ for local reading only.

Enabled by mkdocs.private.yml (`mkdocs serve -f mkdocs.private.yml`); the published build never loads it
and excludes fr/private/ (see exclude_docs in mkdocs.yml).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def on_config(config):
    # the i18n plugin only accepts pages that live under docs_dir, so link private/ in as a git-ignored symlink
    link = Path(config.docs_dir) / "fr" / "private"
    if not link.is_symlink():
        link.symlink_to(Path("../../private"), target_is_directory=True)
    config.exclude_docs = None
    return config


def on_page_markdown(markdown, page, **kwargs):
    # links are written relative to private/ (../docs/fr/...) so they also work in the IDE
    if page.file.src_uri.startswith("fr/private/"):
        return markdown.replace("](../docs/fr/", "](../")
    return markdown
