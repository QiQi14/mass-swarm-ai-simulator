# Skills Catalog

> Auto-generated. Run `python3 .agents/scripts/gen_skills_index.py` to update.
> The Planner reads this to assign relevant skills to task briefs.

## Available Skills

### `skills/frontend-ux-ui`
**Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.**



### `skills/rust-code-standards`
**Rust commenting conventions and unit testing patterns for the Micro-Core. Load this skill for ANY Rust task.**

Keywords: `rust`, `test`, `unit-test`, `comment`, `doc`, `documentation`, `cargo-test`, `verify`

---

## How Skills Work in the DAG

1. **Planner** reads this catalog during Step 1 (planning)
2. If a task involves keywords from a skill, the Planner adds it to `Context_Bindings`:
   ```yaml
   Context_Bindings:
     - skills/session-management
     - context/tech-stack
   ```
3. **Dispatch** resolves `skills/session-management` → `.agents/skills/session-management/SKILL.md`
4. **Executor** receives the full SKILL.md content and follows its instructions

## Adding a New Skill

1. Create `.agents/skills/<name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: What this skill does and when to use it.
   keywords: [keyword1, keyword2, keyword3]
   ---
   ```
2. Add `resources/` and `examples/` subdirectories as needed
3. Run `python3 .agents/scripts/gen_skills_index.py` to update this catalog
