#!/usr/bin/env python3
"""
dispatch.py — Multi-Agent Session Dispatch CLI

Generates context-rich session prompts for different agent roles
(Planner, Executor, QA) by composing agent identity templates with
project-local task data, contracts, and context bindings.

This script is part of a portable multi-agent framework. Copy the
entire project structure (`.agents/`, `task_tool.*`, `dispatch.*`)
to any new project to use it.

Commands:
  agents                    List available agent roles
  tasks                     Show all tasks with current state
  ready                     List tasks whose phase dependencies are met
  prompt  <role> [task_id]  Generate a session prompt to stdout
  session <role> [task_id]  Generate prompt → write to .dispatch/ → clipboard
  batch                     Generate session prompts for ALL ready tasks

Usage:
  python dispatch.py agents
  python dispatch.py tasks
  python dispatch.py ready
  python dispatch.py prompt executor task_01_auth_ui
  python dispatch.py session qa task_01_auth_ui
  python dispatch.py batch [--role executor]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
AGENTS_DIR = SCRIPT_DIR / ".agents" / "agents"
RULES_DIR = SCRIPT_DIR / ".agents" / "rules"
WORKFLOWS_DIR = SCRIPT_DIR / ".agents" / "workflows"
STATE_FILE = SCRIPT_DIR / "task_state.json"
TASKS_PENDING_DIR = SCRIPT_DIR / "tasks_pending"
IMPLEMENTATION_PLAN = SCRIPT_DIR / "implementation_plan.md"
IMPLEMENTATION_PLAN_FEATURE_GLOB = "implementation_plan_feature_*.md"
DISPATCH_DIR = SCRIPT_DIR / ".dispatch"

AVAILABLE_ROLES = {
    "planner": {
        "template": "planner.md",
        "description": "Lead Architect — creates DAG plans and task briefs",
        "requires_task": False,
    },
    "executor": {
        "template": "executor.md",
        "description": "Execution Specialist — implements a single task from the DAG",
        "requires_task": True,
    },
    "qa": {
        "template": "qa.md",
        "description": "QA Auditor — verifies executor output against contracts",
        "requires_task": True,
    },
}

# ---------------------------------------------------------------------------
# Terminal Colors
# ---------------------------------------------------------------------------

class _C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    MAGENTA = "\033[95m"

    @classmethod
    def disable(cls):
        for a in ("RESET","BOLD","RED","GREEN","YELLOW","BLUE","CYAN","GRAY","MAGENTA"):
            setattr(cls, a, "")

C = _C()
if not sys.stdout.isatty():
    C.disable()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _die(msg: str) -> None:
    print(f"{C.RED}ERROR:{C.RESET} {msg}", file=sys.stderr)
    sys.exit(1)


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        _die(f"{STATE_FILE.name} not found. Run './task_tool.sh init' first.")
    with open(STATE_FILE) as f:
        return json.load(f)


def _find_task(state: dict, task_id: str) -> Optional[dict]:
    for t in state.get("tasks", []):
        if t["task_id"] == task_id:
            return t
    return None


def _read_file_safe(path: Path) -> str:
    """Read a file, return its content or a placeholder if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return f"[File not found: {path.name}]"


def _get_ready_tasks(state: dict) -> list[dict]:
    """
    Return tasks that are PENDING and whose phase dependencies are met.
    A task is ready if ALL tasks in earlier phases are COMPLETE.
    """
    tasks = state.get("tasks", [])

    # Group by phase
    phases: dict[str, list[dict]] = {}
    for t in tasks:
        phase = t.get("phase") or "999"  # unassigned = last
        phases.setdefault(phase, []).append(t)

    ready = []
    for phase_key in sorted(phases.keys()):
        phase_tasks = phases[phase_key]

        # Check if all EARLIER phases are complete
        earlier_complete = True
        for earlier_key in sorted(phases.keys()):
            if earlier_key >= phase_key:
                break
            for t in phases[earlier_key]:
                if t["status"] != "COMPLETE":
                    earlier_complete = False
                    break
            if not earlier_complete:
                break

        if earlier_complete:
            for t in phase_tasks:
                if t["status"] == "PENDING":
                    ready.append(t)

    return ready


def _parse_task_brief(content: str) -> dict[str, Any]:
    """
    Parse structured metadata from a task brief markdown file.
    Extracts: Task_ID, Execution_Phase, Target_Files, Dependencies,
    Context_Bindings, and the full content.
    """
    result: dict[str, Any] = {"raw": content}

    # Task_ID
    m = re.search(r"Task_ID\s*[:=]\s*[`\"']?(\S+)", content, re.IGNORECASE)
    result["task_id"] = m.group(1).strip("`\"'") if m else None

    # Execution_Phase
    m = re.search(r"Execution_Phase\s*[:=]\s*[`\"']?(\S+)", content, re.IGNORECASE)
    result["phase"] = m.group(1).strip("`\"'") if m else None

    # Target_Files (multi-line list)
    result["target_files"] = _parse_list_field(content, "Target_Files")

    # Dependencies
    result["dependencies"] = _parse_list_field(content, "Dependencies")

    # Context_Bindings
    result["context_bindings"] = _parse_list_field(content, "Context_Bindings")

    # Model_Tier (basic / standard / advanced) — handles **bold** markers
    m = re.search(r"\*{0,2}Model_Tier\*{0,2}\s*[:=]\s*[`\"']?(\w+)", content, re.IGNORECASE)
    result["model_tier"] = m.group(1).strip("`\"'").lower() if m else "standard"

    return result


def _parse_list_field(content: str, field_name: str) -> list[str]:
    """
    Parse a field that may be followed by a bulleted/dashed list.
    Handles formats like:
      Target_Files:
        - src/ui/Foo.kt
        - src/ui/Bar.kt
    OR:
      **Target_Files**: `src/ui/Foo.kt`, `src/ui/Bar.kt`
    """
    items = []

    # Match the field (with optional bold markers) followed by its value block.
    # Stop at the next field-like line (- **FieldName** or **FieldName**) or heading.
    pattern = re.compile(
        rf"[-*\s]*\*{{0,2}}{field_name}\*{{0,2}}\s*[:=]\s*(.*?)(?=\n\s*[-*]*\s*\*{{2}}[A-Z]|\n#|\n---|$)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(content)
    if m:
        block = m.group(1).strip()
        # Extract list items: lines starting with "- " (NOT "**")
        list_items = re.findall(r"^\s*-\s+(.+)$", block, re.MULTILINE)
        if list_items:
            items = [item.strip().strip("`\"'") for item in list_items]
        elif block:
            # Inline comma-separated: `foo`, `bar`
            inline = re.findall(r"[`\"']([^`\"']+)[`\"']", block)
            if inline:
                items = inline
            elif "," in block:
                items = [x.strip().strip("`\"'") for x in block.split(",")]

    return items


def _resolve_context_binding(binding: str) -> Optional[Path]:
    """
    Resolve a context binding string to an actual file path.
    Tries multiple resolution strategies:
      - Direct path relative to project root
      - .agents/skills/<binding>/SKILL.md
      - .agents/context/<binding>.md
      - .agents/rules/<binding>.md
      - .agents/workflows/<binding>.md
    """
    binding = binding.strip().strip("`\"'")

    # Skills have special resolution: skills/<name> → .agents/skills/<name>/SKILL.md
    for prefix in ("skills/", ".agents/skills/"):
        if binding.startswith(prefix):
            skill_name = binding[len(prefix):].removesuffix("/SKILL.md").removesuffix(".md")
            skill_path = SCRIPT_DIR / ".agents" / "skills" / skill_name / "SKILL.md"
            return skill_path if skill_path.exists() else None

    # Remove common prefixes (normalize to bare name)
    for prefix in ("context/", "rules/", "workflows/", ".agents/context/", ".agents/rules/", ".agents/workflows/", "@"):
        if binding.startswith(prefix):
            binding = binding[len(prefix):]
            break

    # Remove .md extension if present
    binding_base = binding.removesuffix(".md")

    # Context dir
    context_dir = SCRIPT_DIR / ".agents" / "context"

    # Try all candidate paths
    candidates = [
        SCRIPT_DIR / binding,
        SCRIPT_DIR / f"{binding}.md",
        context_dir / f"{binding_base}.md",
        RULES_DIR / f"{binding_base}.md",
        WORKFLOWS_DIR / f"{binding_base}.md",
        SCRIPT_DIR / ".agents" / binding,
        SCRIPT_DIR / ".agents" / f"{binding}.md",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def _load_all_plan_content() -> str:
    """
    Load the main implementation_plan.md and any split feature detail files.
    Returns all plan content concatenated, with clear separators.

    Supports the split-plan convention:
      implementation_plan.md              (index / overview)
      implementation_plan_feature_1.md    (feature detail)
      implementation_plan_feature_2.md    (feature detail)
      ...
    """
    parts = []

    # Main plan (always required)
    main_content = _read_file_safe(IMPLEMENTATION_PLAN)
    parts.append(main_content)

    # Feature detail files (optional, sorted for determinism)
    feature_files = sorted(SCRIPT_DIR.glob(IMPLEMENTATION_PLAN_FEATURE_GLOB))
    for ff in feature_files:
        content = ff.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"\n\n---\n<!-- Source: {ff.name} -->\n\n{content}")

    return "\n".join(parts)


def _extract_contracts(plan_content: str, task_id: str) -> str:
    """
    Extract relevant shared contracts from implementation plan content.
    Looks for sections titled 'Contract', 'Shared Contracts', 'Handshake', etc.
    Searches across the main plan and any feature detail files.
    Returns the contract text or a fallback message.
    """
    # Try to find a contracts section
    contract_patterns = [
        r"(?:^#{1,3}\s*.*(?:contract|handshake|interface|shared).*$)(.*?)(?=^#{1,3}\s|\Z)",
    ]

    for pat in contract_patterns:
        m = re.search(pat, plan_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if m:
            return m.group(0).strip()

    return "_See `implementation_plan.md` for full contract definitions._"


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard via pbcopy."""
    try:
        proc = subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            check=True,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Prompt Generation
# ---------------------------------------------------------------------------

def generate_prompt(role: str, task_id: Optional[str] = None, feature_name: Optional[str] = None) -> str:
    """
    Generate a complete session prompt for the given role and task.

    1. Load agent template from .agents/agents/<role>.md
    2. Load task brief from tasks_pending/<task_id>.md
    3. Parse Context_Bindings → resolve to file paths
    4. Extract contracts from implementation_plan.md
    5. Fill template variables
    6. Return the composed prompt
    """
    role_info = AVAILABLE_ROLES.get(role)
    if not role_info:
        _die(f"Unknown role '{role}'. Available: {', '.join(AVAILABLE_ROLES)}")

    # Load agent template
    template_path = AGENTS_DIR / role_info["template"]
    if not template_path.exists():
        _die(f"Agent template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")

    # Load state for feature name
    if not feature_name:
        if STATE_FILE.exists():
            state = _load_state()
            feature_name = state.get("feature", "Unnamed Feature")
        else:
            feature_name = "Unnamed Feature"

    # --- Role: Planner (no task required) ---
    if role == "planner":
        prompt = template.replace("{{FEATURE_NAME}}", feature_name or "TBD")
        return prompt

    # --- Roles requiring a task_id ---
    if not task_id:
        _die(f"Role '{role}' requires a task_id. Usage: dispatch.py prompt {role} <task_id>")

    # Load task brief
    task_brief_path = TASKS_PENDING_DIR / f"{task_id}.md"
    if not task_brief_path.exists():
        _die(f"Task brief not found: {task_brief_path}")
    task_brief_content = task_brief_path.read_text(encoding="utf-8").strip()
    parsed = _parse_task_brief(task_brief_content)

    # Resolve Context_Bindings (deduplicated)
    # These are already hardcoded in the agent templates, so skip them
    builtin_bindings = {
        "execution-boundary", "execution-lifecycle",
        "qa-lifecycle", "qa-audit-protocol",
    }

    seen_paths: set[str] = set()
    bindings_list_lines = []
    for binding in parsed.get("context_bindings", []):
        # Normalize for dedup check
        binding_clean = binding.strip().strip("`\"'")
        binding_base = binding_clean.split("/")[-1].removesuffix(".md")
        if binding_base in builtin_bindings:
            continue  # Already in the template

        resolved = _resolve_context_binding(binding)
        if resolved:
            rel_str = str(resolved.relative_to(SCRIPT_DIR))
            if rel_str not in seen_paths:
                seen_paths.add(rel_str)
                bindings_list_lines.append(f"- `./{rel_str}`")
        else:
            bindings_list_lines.append(f"- `{binding}` _(not found — verify path)_")

    context_bindings_str = "\n".join(bindings_list_lines) if bindings_list_lines else "_No additional context bindings specified._"

    # Extract contracts from implementation plan (main + feature detail files)
    plan_content = _load_all_plan_content()
    contracts = _extract_contracts(plan_content, task_id)

    # Load changelog (for QA role)
    changelog_content = "_Changelog not yet created by executor._"
    if role == "qa":
        changelog_path = TASKS_PENDING_DIR / f"{task_id}_changelog.md"
        changelog_content = _read_file_safe(changelog_path)

    # Fill template variables
    prompt = template
    prompt = prompt.replace("{{TASK_ID}}", task_id)
    prompt = prompt.replace("{{FEATURE_NAME}}", feature_name)
    prompt = prompt.replace("{{MODEL_TIER}}", parsed.get("model_tier", "standard"))
    prompt = prompt.replace("{{TASK_BRIEF}}", task_brief_content)
    prompt = prompt.replace("{{CONTRACTS}}", contracts)
    prompt = prompt.replace("{{CONTEXT_BINDINGS_LIST}}", context_bindings_str)
    prompt = prompt.replace("{{CHANGELOG}}", changelog_content)

    return prompt


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_agents(_args: argparse.Namespace) -> None:
    """List available agent roles."""
    print(f"\n{C.BOLD}Available Agent Roles{C.RESET}")
    print(f"{'─' * 50}")
    for name, info in AVAILABLE_ROLES.items():
        task_req = f"{C.YELLOW}(requires task_id){C.RESET}" if info["requires_task"] else f"{C.GRAY}(no task needed){C.RESET}"
        print(f"  {C.CYAN}{C.BOLD}{name:<12}{C.RESET} {info['description']}")
        print(f"  {' ' * 12} {task_req}")
        print(f"  {' ' * 12} Template: {C.GRAY}.agents/agents/{info['template']}{C.RESET}")
        print()


def cmd_tasks(_args: argparse.Namespace) -> None:
    """Show all tasks with current state."""
    state = _load_state()

    icon_map = {
        "PENDING": f"{C.GRAY}○{C.RESET}",
        "IN_PROGRESS": f"{C.BLUE}◉{C.RESET}",
        "COMPLETE": f"{C.GREEN}✔{C.RESET}",
        "FAILED": f"{C.RED}✘{C.RESET}",
    }
    color_map = {
        "PENDING": C.GRAY,
        "IN_PROGRESS": C.BLUE,
        "COMPLETE": C.GREEN,
        "FAILED": C.RED,
    }

    print(f"\n{C.BOLD}Tasks — {state.get('feature', '?')}{C.RESET}")
    print(f"Global: {color_map.get(state['global_status'], '')}{C.BOLD}{state['global_status']}{C.RESET}")
    print(f"{'─' * 50}")

    for t in state.get("tasks", []):
        icon = icon_map.get(t["status"], "?")
        sc = color_map.get(t["status"], "")
        phase = f"P{t.get('phase', '?')}" if t.get("phase") else "  "
        print(f"  {phase} {icon} {sc}{t['task_id']:<30}{C.RESET} {sc}{t['status']}{C.RESET}")
        if t.get("fail_reason"):
            print(f"       {C.RED}↳ {t['fail_reason']}{C.RESET}")
    print()


def cmd_ready(_args: argparse.Namespace) -> None:
    """List tasks that are ready for execution."""
    state = _load_state()
    ready = _get_ready_tasks(state)

    if not ready:
        print(f"{C.YELLOW}No tasks are ready for execution.{C.RESET}")
        if state["global_status"] == "BLOCKED":
            print(f"{C.RED}Project is BLOCKED — resolve failed tasks first.{C.RESET}")
        elif state["global_status"] == "ALL_COMPLETE":
            print(f"{C.GREEN}All tasks are complete!{C.RESET}")
        return

    print(f"\n{C.BOLD}Ready Tasks{C.RESET} ({len(ready)} available)")
    print(f"{'─' * 50}")
    for t in ready:
        phase = f"Phase {t.get('phase', '?')}" if t.get("phase") else "Unassigned"
        print(f"  {C.CYAN}○{C.RESET} {C.BOLD}{t['task_id']}{C.RESET}  ({phase})")
    print()
    print(f"{C.GRAY}Generate prompts:{C.RESET}")
    print(f"  {C.CYAN}./dispatch.sh prompt executor <task_id>{C.RESET}")
    print(f"  {C.CYAN}./dispatch.sh batch{C.RESET}  (all ready tasks)")
    print()


def cmd_prompt(args: argparse.Namespace) -> None:
    """Generate a session prompt and print to stdout."""
    prompt = generate_prompt(
        role=args.role,
        task_id=args.task_id,
        feature_name=args.feature,
    )
    print(prompt)


def cmd_session(args: argparse.Namespace) -> None:
    """Generate a session prompt, write to .dispatch/, and copy to clipboard."""
    role = args.role
    task_id = args.task_id

    prompt = generate_prompt(
        role=role,
        task_id=task_id,
        feature_name=args.feature,
    )

    # Write to .dispatch/
    DISPATCH_DIR.mkdir(exist_ok=True)

    if task_id:
        filename = f"{role}__{task_id}.prompt.md"
    else:
        filename = f"{role}.prompt.md"

    filepath = DISPATCH_DIR / filename
    filepath.write_text(prompt, encoding="utf-8")

    # Copy to clipboard
    copied = _copy_to_clipboard(prompt)

    print(f"{C.GREEN}✔{C.RESET} Prompt written to {C.CYAN}{filepath.relative_to(SCRIPT_DIR)}{C.RESET}")
    if copied:
        print(f"{C.GREEN}✔{C.RESET} Copied to clipboard")
    else:
        print(f"{C.YELLOW}⚠{C.RESET} Could not copy to clipboard (pbcopy not available)")
    print()
    print(f"{C.BOLD}Next step:{C.RESET} Open a new Antigravity session and paste the prompt.")


def cmd_batch(args: argparse.Namespace) -> None:
    """Generate session prompts for ALL ready tasks."""
    state = _load_state()
    ready = _get_ready_tasks(state)

    role = args.role or "executor"

    if not ready:
        print(f"{C.YELLOW}No tasks are ready for dispatch.{C.RESET}")
        if state["global_status"] == "BLOCKED":
            print(f"{C.RED}Project is BLOCKED — resolve failed tasks first.{C.RESET}")
        return

    DISPATCH_DIR.mkdir(exist_ok=True)

    feature_name = state.get("feature", "Unnamed Feature")
    generated = []

    print(f"\n{C.BOLD}Dispatching {len(ready)} task(s) as '{role}'...{C.RESET}")
    print(f"{'─' * 50}")

    for t in ready:
        task_id = t["task_id"]
        try:
            prompt = generate_prompt(
                role=role,
                task_id=task_id,
                feature_name=feature_name,
            )

            filename = f"{role}__{task_id}.prompt.md"
            filepath = DISPATCH_DIR / filename
            filepath.write_text(prompt, encoding="utf-8")
            generated.append(filepath)

            phase = f"Phase {t.get('phase', '?')}" if t.get("phase") else ""
            print(f"  {C.GREEN}✔{C.RESET} {task_id} {C.GRAY}{phase}{C.RESET}")
            print(f"    → {C.CYAN}{filepath.relative_to(SCRIPT_DIR)}{C.RESET}")

        except SystemExit:
            print(f"  {C.RED}✘{C.RESET} {task_id} — failed to generate prompt")
            continue

    if generated:
        print(f"\n{'─' * 50}")
        print(f"{C.GREEN}{C.BOLD}✔ {len(generated)} prompt(s) generated.{C.RESET}\n")
        print(f"{C.BOLD}Open new Antigravity sessions with these prompts:{C.RESET}")
        for i, fp in enumerate(generated, 1):
            rel = fp.relative_to(SCRIPT_DIR)
            print(f"  {C.CYAN}{i}. {rel}{C.RESET}")
        print()
        print(f"{C.GRAY}Tip: Copy a prompt to clipboard with:{C.RESET}")
        print(f"  {C.CYAN}cat .dispatch/<file> | pbcopy{C.RESET}")
        print()


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dispatch",
        description="Multi-Agent Session Dispatch CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./dispatch.sh agents
  ./dispatch.sh tasks
  ./dispatch.sh ready
  ./dispatch.sh prompt planner --feature "User Auth"
  ./dispatch.sh prompt executor task_01_auth_repo
  ./dispatch.sh session executor task_01_auth_repo
  ./dispatch.sh session qa task_01_auth_repo
  ./dispatch.sh batch
  ./dispatch.sh batch --role qa
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # agents
    sub.add_parser("agents", help="List available agent roles")

    # tasks
    sub.add_parser("tasks", help="Show all tasks with current state")

    # ready
    sub.add_parser("ready", help="List tasks ready for execution")

    # prompt
    p_prompt = sub.add_parser("prompt", help="Generate a session prompt (stdout)")
    p_prompt.add_argument("role", choices=AVAILABLE_ROLES.keys(), help="Agent role")
    p_prompt.add_argument("task_id", nargs="?", default=None, help="Task ID (required for executor/qa)")
    p_prompt.add_argument("--feature", type=str, default=None, help="Feature name (for planner)")

    # session
    p_session = sub.add_parser("session", help="Generate prompt → .dispatch/ + clipboard")
    p_session.add_argument("role", choices=AVAILABLE_ROLES.keys(), help="Agent role")
    p_session.add_argument("task_id", nargs="?", default=None, help="Task ID (required for executor/qa)")
    p_session.add_argument("--feature", type=str, default=None, help="Feature name (for planner)")

    # batch
    p_batch = sub.add_parser("batch", help="Generate prompts for ALL ready tasks")
    p_batch.add_argument("--role", choices=["executor", "qa"], default=None, help="Role to dispatch as (default: executor)")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "agents":  cmd_agents,
        "tasks":   cmd_tasks,
        "ready":   cmd_ready,
        "prompt":  cmd_prompt,
        "session": cmd_session,
        "batch":   cmd_batch,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
