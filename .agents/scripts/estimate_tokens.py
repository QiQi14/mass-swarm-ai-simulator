#!/usr/bin/env python3
"""
estimate_tokens.py — Context Token Budget Estimator

Calculates the estimated input context token count for each task in
tasks_pending/, enabling data-driven Model_Tier assignment instead of
guessing. The Planner runs this AFTER writing task briefs but BEFORE
dispatching.

Uses a conservative len(text)/3 heuristic (1 token ≈ 3 chars) to
intentionally overestimate, providing a built-in safety buffer.

Tier Thresholds (default):
  basic    ≤  8,000 tokens  — Qwen 3.6 14B, Gemma 3 27B, Nemotron Nano
  standard ≤ 32,000 tokens  — Gemini Flash, Claude Sonnet 4.6, GPT-OSS 120B
  advanced >  32,000 tokens — Gemini Pro, Claude Opus 4.6

Usage:
  python3 .agents/scripts/estimate_tokens.py                    # summary table
  python3 .agents/scripts/estimate_tokens.py --verbose          # per-task breakdown
  python3 .agents/scripts/estimate_tokens.py --task task_01_xxx # single task
  python3 .agents/scripts/estimate_tokens.py --basic-max 6000   # custom threshold
  python3 .agents/scripts/estimate_tokens.py --json             # machine-readable

This script uses only the Python standard library (no external deps).
It imports resolution logic from dispatch.py to stay DRY.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path Setup — resolve project root from script location
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent          # .agents/scripts/
AGENTS_DIR = SCRIPT_DIR.parent                         # .agents/
PROJECT_ROOT = AGENTS_DIR.parent                       # project root

# Import dispatch.py functions — it lives at PROJECT_ROOT/dispatch.py
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from dispatch import (
        _parse_task_brief,
        _resolve_context_binding,
        _read_file_safe,
        _load_all_plan_content,
        _extract_contracts,
    )
except ImportError:
    print(
        "ERROR: Cannot import from dispatch.py. "
        "Ensure dispatch.py exists at the project root.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASKS_PENDING_DIR = PROJECT_ROOT / "tasks_pending"
AGENTS_AGENTS_DIR = AGENTS_DIR / "agents"
KNOWLEDGE_DIR = AGENTS_DIR / "knowledge"
CONTEXT_DIR = AGENTS_DIR / "context"
RESEARCH_DIGEST = PROJECT_ROOT / "research_digest.md"
STRATEGY_BRIEF = PROJECT_ROOT / "strategy_brief.md"

# Default tier thresholds (tokens)
DEFAULT_BASIC_MAX = 8_000
DEFAULT_STANDARD_MAX = 32_000

# Conservative token estimation: 1 token ≈ 3 characters
CHARS_PER_TOKEN = 3

# Agent templates by role
EXECUTOR_TEMPLATE = AGENTS_AGENTS_DIR / "executor.md"
QA_TEMPLATE = AGENTS_AGENTS_DIR / "qa.md"

# Mandatory context files loaded by standard/advanced executors
EXECUTOR_MANDATORY_CONTEXT = [
    AGENTS_DIR / "context.md",
    AGENTS_DIR / "workflows" / "execution-lifecycle.md",
    AGENTS_DIR / "rules" / "execution-boundary.md",
]

# Mandatory context files loaded by QA agents
QA_MANDATORY_CONTEXT = [
    AGENTS_DIR / "context.md",
    AGENTS_DIR / "workflows" / "qa-lifecycle.md",
    AGENTS_DIR / "workflows" / "qa-certification-template.md",
    AGENTS_DIR / "workflows" / "knowledge-capture.md",
    AGENTS_DIR / "rules" / "qa-audit-protocol.md",
]

# Builtin bindings that are already in agent templates (skip for dedup)
BUILTIN_BINDINGS = {
    "execution-boundary", "execution-lifecycle",
    "qa-lifecycle", "qa-audit-protocol",
    "qa-certification-template", "knowledge-capture",
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
        for a in ("RESET", "BOLD", "RED", "GREEN", "YELLOW", "BLUE", "CYAN", "GRAY", "MAGENTA"):
            setattr(cls, a, "")

C = _C()
if not sys.stdout.isatty():
    C.disable()


# ---------------------------------------------------------------------------
# Token Estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Conservative token estimate: len(text) / 3."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def recommend_tier(tokens: int, basic_max: int, standard_max: int) -> str:
    """Recommend a tier based on token count."""
    if tokens <= basic_max:
        return "basic"
    elif tokens <= standard_max:
        return "standard"
    else:
        return "advanced"


def collect_knowledge_files() -> list[Path]:
    """Recursively collect all .md files from .agents/knowledge/ (excluding README)."""
    if not KNOWLEDGE_DIR.exists():
        return []
    files = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        if path.is_file():
            files.append(path)
    return files


# ---------------------------------------------------------------------------
# Per-Task Analysis
# ---------------------------------------------------------------------------

def analyze_task(
    task_file: Path,
    basic_max: int,
    standard_max: int,
) -> dict[str, Any]:
    """
    Analyze a single task brief and calculate its estimated token budget.

    Returns a dict with:
      - task_id, model_tier (current), estimated_tokens, recommended_tier, status
      - breakdown: dict of component → {tokens, files}
    """
    content = task_file.read_text(encoding="utf-8").strip()
    parsed = _parse_task_brief(content)

    task_id = task_file.stem  # e.g., "task_01_terrain_grid"
    current_tier = parsed.get("model_tier", "standard")
    context_bindings = parsed.get("context_bindings", [])

    breakdown: dict[str, Any] = {}
    total_chars = 0

    # ── 1. Agent Template ──────────────────────────────────────────────────
    # Determine role from task file or default to executor
    template_path = EXECUTOR_TEMPLATE
    role = "executor"
    # Simple heuristic: if "qa" is in the task_id or brief mentions QA role
    if "qa" in task_id.lower():
        template_path = QA_TEMPLATE
        role = "qa"

    template_text = _read_file_safe(template_path)
    template_chars = len(template_text)
    total_chars += template_chars
    breakdown["agent_template"] = {
        "file": template_path.name,
        "chars": template_chars,
        "tokens": estimate_tokens(template_text),
    }

    # ── 2. Task Brief ──────────────────────────────────────────────────────
    brief_chars = len(content)
    total_chars += brief_chars
    breakdown["task_brief"] = {
        "file": task_file.name,
        "chars": brief_chars,
        "tokens": estimate_tokens(content),
    }

    # ── Basic tier stops here ──────────────────────────────────────────────
    if current_tier == "basic":
        total_tokens = estimate_tokens(" " * total_chars)  # Use total chars for consistency
        recommended = recommend_tier(total_tokens, basic_max, standard_max)

        # Even for basic, flag if the brief alone is too large
        return {
            "task_id": task_id,
            "model_tier": current_tier,
            "role": role,
            "estimated_tokens": total_tokens,
            "recommended_tier": recommended,
            "status": _compute_status(current_tier, recommended),
            "breakdown": breakdown,
        }

    # ── 3. Context Bindings ────────────────────────────────────────────────
    bindings_detail = []
    bindings_chars = 0

    for binding in context_bindings:
        binding_clean = binding.strip().strip("`\"'")
        binding_base = binding_clean.split("/")[-1].removesuffix(".md")

        # Skip builtins already counted in mandatory context
        if binding_base in BUILTIN_BINDINGS:
            continue

        resolved = _resolve_context_binding(binding)
        if resolved and resolved.exists():
            text = resolved.read_text(encoding="utf-8").strip()
            chars = len(text)
            bindings_chars += chars
            total_chars += chars
            rel = str(resolved.relative_to(PROJECT_ROOT))
            bindings_detail.append({
                "binding": binding_clean,
                "resolved": rel,
                "chars": chars,
                "tokens": estimate_tokens(text),
            })
        else:
            bindings_detail.append({
                "binding": binding_clean,
                "resolved": None,
                "chars": 0,
                "tokens": 0,
            })

    breakdown["context_bindings"] = {
        "files": bindings_detail,
        "total_chars": bindings_chars,
        "total_tokens": estimate_tokens(" " * bindings_chars),
    }

    # ── 4. Contracts from Implementation Plan ──────────────────────────────
    plan_content = _load_all_plan_content()
    contracts = _extract_contracts(plan_content, task_id)
    contracts_chars = len(contracts)
    total_chars += contracts_chars
    breakdown["contracts"] = {
        "chars": contracts_chars,
        "tokens": estimate_tokens(contracts),
    }

    # ── 5. Mandatory Context (tier-dependent) ──────────────────────────────
    mandatory_files = QA_MANDATORY_CONTEXT if role == "qa" else EXECUTOR_MANDATORY_CONTEXT
    mandatory_detail = []
    mandatory_chars = 0

    for mf in mandatory_files:
        if mf.exists():
            text = mf.read_text(encoding="utf-8").strip()
            chars = len(text)
            mandatory_chars += chars
            total_chars += chars
            rel = str(mf.relative_to(PROJECT_ROOT))
            mandatory_detail.append({
                "file": rel,
                "chars": chars,
                "tokens": estimate_tokens(text),
            })

    breakdown["mandatory_context"] = {
        "files": mandatory_detail,
        "total_chars": mandatory_chars,
        "total_tokens": estimate_tokens(" " * mandatory_chars),
    }

    # ── 6. Knowledge Files ─────────────────────────────────────────────────
    knowledge_files = collect_knowledge_files()
    knowledge_chars = 0
    knowledge_count = len(knowledge_files)

    for kf in knowledge_files:
        text = kf.read_text(encoding="utf-8").strip()
        knowledge_chars += len(text)
        total_chars += len(text)

    breakdown["knowledge"] = {
        "file_count": knowledge_count,
        "total_chars": knowledge_chars,
        "total_tokens": estimate_tokens(" " * knowledge_chars),
    }

    # ── 7. Research Artifacts (advanced tier only) ─────────────────────────
    # dispatch.py auto-injects these for advanced executors, so we must
    # account for them in the token budget.
    if current_tier == "advanced" and role != "qa":
        research_detail = []
        research_chars = 0

        for artifact_path in (RESEARCH_DIGEST, STRATEGY_BRIEF):
            if artifact_path.exists():
                text = artifact_path.read_text(encoding="utf-8").strip()
                chars = len(text)
                research_chars += chars
                total_chars += chars
                research_detail.append({
                    "file": artifact_path.name,
                    "chars": chars,
                    "tokens": estimate_tokens(text),
                })

        breakdown["research_artifacts"] = {
            "files": research_detail,
            "total_chars": research_chars,
            "total_tokens": estimate_tokens(" " * research_chars),
        }

    # ── Final Calculation ──────────────────────────────────────────────────
    total_tokens = total_chars // CHARS_PER_TOKEN
    recommended = recommend_tier(total_tokens, basic_max, standard_max)

    return {
        "task_id": task_id,
        "model_tier": current_tier,
        "role": role,
        "estimated_tokens": total_tokens,
        "recommended_tier": recommended,
        "status": _compute_status(current_tier, recommended),
        "breakdown": breakdown,
    }


def _compute_status(current: str, recommended: str) -> str:
    """Compare current tier vs recommended and return a status string."""
    tier_rank = {"basic": 0, "standard": 1, "advanced": 2}
    cur = tier_rank.get(current, 1)
    rec = tier_rank.get(recommended, 1)

    if cur == rec:
        return "OK"
    elif cur < rec:
        return "UPGRADE"
    else:
        return "DOWNGRADE"


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def _format_tokens(n: int) -> str:
    """Format token count with thousands separator."""
    return f"{n:,}"


def print_summary_table(results: list[dict]) -> None:
    """Print the summary table for all tasks."""
    if not results:
        print(f"{C.YELLOW}No task files found in tasks_pending/.{C.RESET}")
        return

    # Calculate column widths
    id_w = max(len("Task ID"), max(len(r["task_id"]) for r in results))
    cur_w = max(len("Current"), max(len(r["model_tier"]) for r in results))
    tok_w = max(len("Est.Tokens"), max(len(_format_tokens(r["estimated_tokens"])) for r in results))
    rec_w = max(len("Recommended"), max(len(r["recommended_tier"]) for r in results))
    sta_w = max(len("Status"), 12)

    header = (
        f"  {'Task ID':<{id_w}}  "
        f"{'Current':<{cur_w}}  "
        f"{'Est.Tokens':>{tok_w}}  "
        f"{'Recommended':<{rec_w}}  "
        f"{'Status':<{sta_w}}"
    )
    sep = "  " + "─" * (id_w + cur_w + tok_w + rec_w + sta_w + 12)

    print(f"\n{C.BOLD}Token Budget Estimation{C.RESET}")
    print(sep)
    print(f"{C.BOLD}{header}{C.RESET}")
    print(sep)

    warnings = 0
    for r in results:
        status = r["status"]
        if status == "OK":
            status_str = f"{C.GREEN}✔ OK{C.RESET}"
        elif status == "UPGRADE":
            status_str = f"{C.RED}⚠ UPGRADE{C.RESET}"
            warnings += 1
        else:
            status_str = f"{C.YELLOW}↓ DOWNGRADE{C.RESET}"

        # Color the token count based on status
        tok_str = _format_tokens(r["estimated_tokens"])
        if status == "UPGRADE":
            tok_colored = f"{C.RED}{tok_str}{C.RESET}"
        elif status == "DOWNGRADE":
            tok_colored = f"{C.YELLOW}{tok_str}{C.RESET}"
        else:
            tok_colored = f"{C.GREEN}{tok_str}{C.RESET}"

        print(
            f"  {r['task_id']:<{id_w}}  "
            f"{r['model_tier']:<{cur_w}}  "
            f"{tok_colored:>{tok_w + len(tok_colored) - len(tok_str)}}  "
            f"{r['recommended_tier']:<{rec_w}}  "
            f"{status_str}"
        )

    print(sep)

    if warnings:
        print(
            f"\n  {C.RED}{C.BOLD}⚠ {warnings} task(s) need tier adjustment.{C.RESET}\n"
            f"  {C.GRAY}Edit Model_Tier in the task briefs, then re-run to verify.{C.RESET}"
        )
    else:
        print(f"\n  {C.GREEN}{C.BOLD}✔ All tasks within budget.{C.RESET}")

    print()


def print_verbose_breakdown(results: list[dict]) -> None:
    """Print detailed per-task token breakdown."""
    for r in results:
        tokens = r["estimated_tokens"]
        tier = r["model_tier"]
        status = r["status"]
        recommended = r["recommended_tier"]

        if status == "OK":
            status_msg = f"{C.GREEN}within {tier} budget{C.RESET}"
        elif status == "UPGRADE":
            status_msg = f"{C.RED}EXCEEDS {tier} budget → recommend {recommended}{C.RESET}"
        else:
            status_msg = f"{C.YELLOW}below {tier} budget → consider {recommended}{C.RESET}"

        print(f"\n{C.BOLD}{r['task_id']}{C.RESET} — {_format_tokens(tokens)} tokens ({status_msg})")
        print(f"  Role: {r['role']}  |  Current tier: {tier}")

        bd = r["breakdown"]

        # Agent template
        at = bd.get("agent_template", {})
        print(f"  {C.GRAY}agent template ({at.get('file', '?')}):{C.RESET}  {_format_tokens(at.get('tokens', 0)):>8} tokens")

        # Task brief
        tb = bd.get("task_brief", {})
        print(f"  {C.GRAY}task brief:{C.RESET}                       {_format_tokens(tb.get('tokens', 0)):>8} tokens")

        # Context bindings
        cb = bd.get("context_bindings", {})
        if cb and cb.get("files"):
            print(f"  {C.GRAY}context bindings:{C.RESET}")
            for bf in cb["files"]:
                if bf.get("resolved"):
                    print(f"    {C.GRAY}{bf['resolved']}:{C.RESET}  {_format_tokens(bf['tokens']):>6} tokens")
                else:
                    print(f"    {C.RED}{bf['binding']}:{C.RESET}  {C.RED}NOT FOUND{C.RESET}")

        # Contracts
        ct = bd.get("contracts", {})
        if ct.get("tokens", 0) > 0:
            print(f"  {C.GRAY}contracts (impl plan):{C.RESET}            {_format_tokens(ct.get('tokens', 0)):>8} tokens")

        # Mandatory context
        mc = bd.get("mandatory_context", {})
        if mc and mc.get("files"):
            print(f"  {C.GRAY}mandatory context:{C.RESET}")
            for mf in mc["files"]:
                print(f"    {C.GRAY}{mf['file']}:{C.RESET}  {_format_tokens(mf['tokens']):>6} tokens")

        # Knowledge
        kn = bd.get("knowledge", {})
        if kn.get("file_count", 0) > 0:
            print(f"  {C.GRAY}knowledge ({kn['file_count']} files):{C.RESET}             {_format_tokens(kn.get('total_tokens', 0)):>8} tokens")

        # Research artifacts (advanced tier only)
        ra = bd.get("research_artifacts", {})
        if ra and ra.get("files"):
            print(f"  {C.CYAN}research artifacts (advanced):{C.RESET}")
            for rf in ra["files"]:
                print(f"    {C.CYAN}{rf['file']}:{C.RESET}  {_format_tokens(rf['tokens']):>6} tokens")

        print(f"  {'─' * 40}")
        print(f"  {C.BOLD}TOTAL:{C.RESET}                               {_format_tokens(tokens):>8} tokens")


def print_json_output(results: list[dict], basic_max: int, standard_max: int) -> None:
    """Print machine-readable JSON output."""
    output = {
        "thresholds": {
            "basic_max": basic_max,
            "standard_max": standard_max,
            "chars_per_token": CHARS_PER_TOKEN,
        },
        "tasks": results,
    }
    print(json.dumps(output, indent=2, default=str))


# ---------------------------------------------------------------------------
# Main Logic
# ---------------------------------------------------------------------------

def discover_task_files(single_task: Optional[str] = None) -> list[Path]:
    """Find task brief files in tasks_pending/."""
    if not TASKS_PENDING_DIR.exists():
        return []

    pattern = re.compile(r"^task_.+\.md$", re.IGNORECASE)
    files = []

    for path in sorted(TASKS_PENDING_DIR.iterdir()):
        if not path.is_file():
            continue
        if not pattern.match(path.name):
            continue
        # Skip changelogs and QA reports
        if path.name.endswith("_changelog.md") or path.name.endswith("_qa_report.md"):
            continue
        # Filter to single task if requested
        if single_task and path.stem != single_task:
            continue
        files.append(path)

    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="estimate_tokens",
        description="Estimate input context token budget for each task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tier thresholds (default):
  basic    ≤  8,000 tokens  (local ~14B-30B models)
  standard ≤ 32,000 tokens  (mid-tier cloud: Flash, Sonnet, GPT-OSS)
  advanced >  32,000 tokens (top-tier: Pro, Opus)

Examples:
  python3 .agents/scripts/estimate_tokens.py
  python3 .agents/scripts/estimate_tokens.py --verbose
  python3 .agents/scripts/estimate_tokens.py --task task_01_terrain_grid
  python3 .agents/scripts/estimate_tokens.py --basic-max 6000 --standard-max 24000
  python3 .agents/scripts/estimate_tokens.py --json
        """,
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-task token breakdown",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Analyze a single task by ID (e.g., task_01_terrain_grid)",
    )
    parser.add_argument(
        "--basic-max",
        type=int,
        default=DEFAULT_BASIC_MAX,
        help=f"Max tokens for basic tier (default: {DEFAULT_BASIC_MAX:,})",
    )
    parser.add_argument(
        "--standard-max",
        type=int,
        default=DEFAULT_STANDARD_MAX,
        help=f"Max tokens for standard tier (default: {DEFAULT_STANDARD_MAX:,})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    args = parser.parse_args()

    # Discover tasks
    task_files = discover_task_files(single_task=args.task)

    if not task_files:
        if args.task:
            print(
                f"{C.RED}ERROR:{C.RESET} Task '{args.task}' not found in "
                f"{TASKS_PENDING_DIR.relative_to(PROJECT_ROOT)}/",
                file=sys.stderr,
            )
        else:
            print(
                f"{C.YELLOW}No task files found in "
                f"{TASKS_PENDING_DIR.relative_to(PROJECT_ROOT)}/.{C.RESET}",
                file=sys.stderr,
            )
        sys.exit(1)

    # Analyze each task
    results = []
    for tf in task_files:
        result = analyze_task(tf, args.basic_max, args.standard_max)
        results.append(result)

    # Output
    if args.json:
        print_json_output(results, args.basic_max, args.standard_max)
    else:
        print_summary_table(results)
        if args.verbose:
            print_verbose_breakdown(results)


if __name__ == "__main__":
    main()
