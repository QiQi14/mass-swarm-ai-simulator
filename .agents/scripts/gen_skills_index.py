#!/usr/bin/env python3
"""
Generate .agents/skills/index.md from all SKILL.md frontmatter.
Run this whenever you add/modify a skill to update the catalog.

Usage: python3 .agents/scripts/gen_skills_index.py
"""
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = SCRIPT_DIR / "skills"
INDEX_FILE = SKILLS_DIR / "index.md"


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from SKILL.md."""
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return {}

    fm = fm_match.group(1)
    result = {}

    for field in ("name", "description"):
        m = re.search(rf'{field}:\s*(.+)', fm)
        if m:
            result[field] = m.group(1).strip()

    # Parse keywords array: [word1, word2, ...]
    kw_match = re.search(r'keywords:\s*\[(.+?)\]', fm)
    if kw_match:
        result["keywords"] = [k.strip() for k in kw_match.group(1).split(",")]
    else:
        result["keywords"] = []

    return result


def main():
    entries = []

    for name in sorted(os.listdir(SKILLS_DIR)):
        skill_path = SKILLS_DIR / name / "SKILL.md"
        if not skill_path.is_file():
            continue

        content = skill_path.read_text()[:3000]
        fm = parse_frontmatter(content)
        if not fm:
            continue

        entries.append({
            "folder": name,
            "name": fm.get("name", name),
            "description": fm.get("description", "No description"),
            "keywords": fm.get("keywords", []),
        })

    # Generate index
    lines = [
        "# Skills Catalog",
        "",
        "> Auto-generated. Run `python3 .agents/scripts/gen_skills_index.py` to update.",
        "> The Planner reads this to assign relevant skills to task briefs.",
        "",
        "## Available Skills",
        "",
    ]

    for entry in entries:
        kw_str = ", ".join(f"`{k}`" for k in entry["keywords"][:8])
        lines.extend([
            f"### `skills/{entry['folder']}`",
            f"**{entry['description']}**",
            "",
            f"Keywords: {kw_str}" if kw_str else "",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## How Skills Work in the DAG",
        "",
        "1. **Planner** reads this catalog during Step 1 (planning)",
        "2. If a task involves keywords from a skill, the Planner adds it to `Context_Bindings`:",
        "   ```yaml",
        "   Context_Bindings:",
        "     - skills/session-management",
        "     - context/tech-stack",
        "   ```",
        "3. **Dispatch** resolves `skills/session-management` → `.agents/skills/session-management/SKILL.md`",
        "4. **Executor** receives the full SKILL.md content and follows its instructions",
        "",
        "## Adding a New Skill",
        "",
        "1. Create `.agents/skills/<name>/SKILL.md` with YAML frontmatter:",
        "   ```yaml",
        "   ---",
        "   name: my-skill",
        "   description: What this skill does and when to use it.",
        "   keywords: [keyword1, keyword2, keyword3]",
        "   ---",
        "   ```",
        "2. Add `resources/` and `examples/` subdirectories as needed",
        "3. Run `python3 .agents/scripts/gen_skills_index.py` to update this catalog",
    ])

    INDEX_FILE.write_text("\n".join(lines) + "\n")
    print(f"✔ Generated {INDEX_FILE} with {len(entries)} skill(s)")


if __name__ == "__main__":
    main()
