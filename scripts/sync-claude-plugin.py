#!/usr/bin/env python3
"""Sync the Architect Claude plugin bundle from source skill assets.

This keeps the installable plugin self-contained while preserving the repo
skills/references/scripts as the source of truth.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "claude-plugin" / "architect"

SKILL_SOURCES = {
    REPO_ROOT / "skills" / "architect-init" / "SKILL.md": (
        PLUGIN_ROOT / "skills" / "init" / "SKILL.md",
        "init",
    ),
    REPO_ROOT / "skills" / "architect-plan" / "SKILL.md": (
        PLUGIN_ROOT / "skills" / "plan" / "SKILL.md",
        "plan",
    ),
    REPO_ROOT / "skills" / "architect-diagram" / "SKILL.md": (
        PLUGIN_ROOT / "skills" / "diagram" / "SKILL.md",
        "diagram",
    ),
    REPO_ROOT / "skills" / "architect-diagram-prompt" / "SKILL.md": (
        PLUGIN_ROOT / "skills" / "diagram-prompt" / "SKILL.md",
        "diagram-prompt",
    ),
}

DIRECT_COPIES = {
    REPO_ROOT / "skills" / "references" / "architecture-contract.md":
        PLUGIN_ROOT / "skills" / "references" / "architecture-contract.md",
    REPO_ROOT / "skills" / "architect-diagram" / "references" / "diagram-output-contract.md":
        PLUGIN_ROOT / "skills" / "diagram" / "references" / "diagram-output-contract.md",
    REPO_ROOT / "skills" / "architect-diagram" / "references" / "html-diagram-spec.md":
        PLUGIN_ROOT / "skills" / "diagram" / "references" / "html-diagram-spec.md",
    REPO_ROOT / "skills" / "architect-diagram" / "references" / "svg-fragment-spec.md":
        PLUGIN_ROOT / "skills" / "diagram" / "references" / "svg-fragment-spec.md",
    REPO_ROOT / "skills" / "architect-diagram" / "references" / "interactive-diagram-prompt.md":
        PLUGIN_ROOT / "skills" / "diagram" / "references" / "interactive-diagram-prompt.md",
    REPO_ROOT / "skills" / "architect-diagram" / "templates" / "diagram-app.html":
        PLUGIN_ROOT / "templates" / "diagram-app.html",
    REPO_ROOT / "skills" / "architect-diagram" / "scripts" / "render-diagram-html.py":
        PLUGIN_ROOT / "scripts" / "render-diagram-html.py",
    REPO_ROOT / "skills" / "architect-diagram" / "scripts" / "validate-feedback-update.py":
        PLUGIN_ROOT / "scripts" / "validate-feedback-update.py",
    REPO_ROOT / "skills" / "architect-diagram" / "scripts" / "validate-diagram-html.sh":
        PLUGIN_ROOT / "scripts" / "validate-diagram-html.sh",
    REPO_ROOT / "skills" / "architect-diagram" / "scripts" / "generate-svg-fragments.py":
        PLUGIN_ROOT / "scripts" / "generate-svg-fragments.py",
    REPO_ROOT / "skills" / "architect-plan" / "scripts" / "decision-coverage-check.py":
        PLUGIN_ROOT / "scripts" / "decision-coverage-check.py",
    REPO_ROOT / "skills" / "architect-plan" / "scripts" / "container-decomposition-check.py":
        PLUGIN_ROOT / "scripts" / "container-decomposition-check.py",
    REPO_ROOT / "skills" / "architect-plan" / "scripts" / "semantic-diff-gate.py":
        PLUGIN_ROOT / "scripts" / "semantic-diff-gate.py",
}

ALLOWED_SKILL_DIRS = {
    "init",
    "plan",
    "diagram",
    "diagram-prompt",
    "references",
}


COMMAND_REPLACEMENTS = [
    ("python3 skills/architect-diagram/scripts/generate-svg-fragments.py", "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/generate-svg-fragments.py"),
    ("python3 skills/architect-diagram/scripts/render-diagram-html.py", "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-diagram-html.py"),
    ("skills/architect-diagram/scripts/validate-diagram-html.sh", "${CLAUDE_PLUGIN_ROOT}/scripts/validate-diagram-html.sh"),
    ("skills/architect-plan/scripts/decision-coverage-check.py", "${CLAUDE_PLUGIN_ROOT}/scripts/decision-coverage-check.py"),
    ("skills/architect-plan/scripts/container-decomposition-check.py", "${CLAUDE_PLUGIN_ROOT}/scripts/container-decomposition-check.py"),
    ("skills/architect-plan/scripts/semantic-diff-gate.py", "${CLAUDE_PLUGIN_ROOT}/scripts/semantic-diff-gate.py"),
]


SKILL_LINK_REPLACEMENTS = [
    ("../architect-diagram/", "../diagram/"),
]


def replace_skill_name(text: str, new_name: str) -> str:
    return re.sub(r"(?m)^name:\s*.+$", f"name: {new_name}", text, count=1)


def transform_skill_text(text: str, new_name: str) -> str:
    text = replace_skill_name(text, new_name)
    for old, new in COMMAND_REPLACEMENTS:
        text = text.replace(old, new)
    for old, new in SKILL_LINK_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def prune_plugin_skill_dirs() -> None:
    skills_root = PLUGIN_ROOT / "skills"
    if not skills_root.exists():
        return
    for child in skills_root.iterdir():
        if child.is_dir() and child.name not in ALLOWED_SKILL_DIRS:
            shutil.rmtree(child)


def main() -> int:
    prune_plugin_skill_dirs()

    for source, (dest, new_name) in SKILL_SOURCES.items():
        text = source.read_text(encoding="utf-8")
        write_text(dest, transform_skill_text(text, new_name))

    for source, dest in DIRECT_COPIES.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
