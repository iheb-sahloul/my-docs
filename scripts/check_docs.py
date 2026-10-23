#!/usr/bin/env python3
"""Docs checks: EN/FR parity and [.. Qn](file.md#slug) references. Exit 1 on errors."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "docs"
HEAD = re.compile(r"^#{3,4} ([QBSR]\d+)\b.*?(?:\{#([^}]*)\})?\s*$", re.M)
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LINK = re.compile(r"\[([^\]]*)\]\(([\w./-]+\.md)?(?:#([^)]+))?\)")
QNUM = re.compile(r"\b([QBSR]\d+)\b")  # "Q22–Q26" or "Q7, Q23": the link may target any of them
errors, warnings = [], []

for en in sorted((ROOT / "en").rglob("*.md")):
    rel = en.relative_to(ROOT / "en")
    fr = ROOT / "fr" / rel
    if not fr.exists():
        warnings.append(f"{rel}: no FR twin")
        continue
    a, b = en.read_text(), fr.read_text()
    ids_a, ids_b = HEAD.findall(a), HEAD.findall(b)
    if ids_a != ids_b:
        errors.append(f"{rel}: heading ids differ: EN-only {sorted(set(ids_a)-set(ids_b))} FR-only {sorted(set(ids_b)-set(ids_a))}")
    for q, slug in ids_a:
        if not SLUG.fullmatch(slug):
            errors.append(f"{rel}: {q} needs an ASCII anchor like {{#some-slug}}, got {{#{slug}}}")
    if len(re.findall(r"^#{2,3} ", a, re.M)) != len(re.findall(r"^#{2,3} ", b, re.M)):
        warnings.append(f"{rel}: ##/### heading count differs")
    la, lb = a.count("\n"), b.count("\n")
    if max(la, lb) > 1.5 * max(1, min(la, lb)):
        warnings.append(f"{rel}: line ratio EN {la} / FR {lb}")

# private/ is git-ignored: checked locally when present, skipped in CI
pages = sorted((ROOT / "en").rglob("*.md")) + sorted((ROOT / "fr").rglob("*.md")) + sorted((ROOT.parent / "private").glob("*.md"))
for f in pages:
    for m in LINK.finditer(f.read_text()):
        label, file, slug = m.groups()
        if not (qs := QNUM.findall(label)):
            continue
        where = f.relative_to(ROOT.parent)
        target = (f.parent / file).resolve() if file else f
        if not target.exists():
            errors.append(f"{where}: missing file {file}")
            continue
        ids = dict((s, n) for n, s in HEAD.findall(target.read_text()))
        if slug is None:
            if not set(qs) & set(ids.values()):
                errors.append(f"{where}: {label} -> no {qs[0]} in {file}")
        elif slug not in ids:
            errors.append(f"{where}: {label} -> no #{slug} in {file or 'this page'}")
        elif ids[slug] not in qs:
            errors.append(f"{where}: {label} -> #{slug} is now {ids[slug]}, update the label")

for w in warnings: print("WARN ", w)
for e in errors: print("ERROR", e)
sys.exit(1 if errors else 0)
