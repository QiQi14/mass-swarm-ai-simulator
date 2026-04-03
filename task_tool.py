#!/usr/bin/env python3
"""
task_tool.py — Multi-Agent Task Lifecycle Management Utility

This script is the SINGLE SOURCE OF TRUTH for all task state mutations
in the multi-agent DAG execution framework. No agent is permitted to
manually edit task_state.json or move files. All operations go through
this tool.

State Machine:
  PENDING → IN_PROGRESS → DONE (executor) → COMPLETE (QA verified) → auto-archive
                                           → FAILED (QA rejected) → PENDING (reset)

Capabilities:
  - init           : Initialize task_state.json from tasks_pending/ directory
  - status         : Display current state of all tasks
  - start          : Transition a task from PENDING → IN_PROGRESS
  - done           : Transition a task to DONE (executor finished, ready for QA)
  - complete       : Transition a task from DONE → COMPLETE (QA verified)
  - fail           : Transition a task to FAILED with a reason (triggers QA BLOCKER)
  - reset          : Transition a FAILED task back to PENDING (after revision)
  - archive        : Manually trigger archive (auto-triggered on all-complete)

Lock Safety:
  Uses fcntl-based file locking on task_state.json to prevent concurrent
  write collisions in a parallel multi-agent environment.

Usage:
  python task_tool.py init [--feature "Feature Name"]
  python task_tool.py status [--verbose]
  python task_tool.py start    <TASK_ID>        # Executor: I'm working on this
  python task_tool.py done     <TASK_ID>        # Executor: Ready for QA review
  python task_tool.py complete <TASK_ID>        # QA: Verified and certified
  python task_tool.py fail     <TASK_ID> --reason "..."  # QA: Defects found
  python task_tool.py reset    <TASK_ID>
  python task_tool.py archive  [--force]
"""

import argparse
import fcntl
import json
import os
import re
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
STATE_FILE = PROJECT_ROOT / "task_state.json"
LOCK_FILE = PROJECT_ROOT / ".task_state.lock"
TASKS_PENDING_DIR = PROJECT_ROOT / "tasks_pending"
IMPLEMENTATION_PLAN = PROJECT_ROOT / "implementation_plan.md"
ARCHIVE_BASE_DIR = PROJECT_ROOT / ".agents" / "history"

# Valid state transitions (from → set of allowed destinations)
# DONE = executor finished, awaiting QA review
# COMPLETE = QA verified and certified
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"IN_PROGRESS", "DONE"},
    "IN_PROGRESS": {"DONE", "FAILED"},
    "DONE": {"COMPLETE", "FAILED"},    # QA reviews: pass → COMPLETE, fail → FAILED
    "FAILED": {"PENDING"},             # reset after revision
    "COMPLETE": set(),                  # terminal state
}

# Terminal-safe ANSI colors
class _Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GRAY    = "\033[90m"

    @classmethod
    def disable(cls):
        for attr in ("RESET", "BOLD", "RED", "GREEN", "YELLOW", "BLUE", "CYAN", "GRAY"):
            setattr(cls, attr, "")

C = _Colors()

# Disable colors when stdout is not a TTY (e.g., piped)
if not sys.stdout.isatty():
    C.disable()

# ---------------------------------------------------------------------------
# File Locking
# ---------------------------------------------------------------------------

@contextmanager
def locked_state(mode: str = "r+"):
    """
    Context manager that provides exclusive access to task_state.json
    via an advisory fcntl lock on a companion .lock file.

    Yields a tuple of (state_dict, write_fn) where write_fn persists
    the state_dict back to disk atomically.
    """
    LOCK_FILE.touch(exist_ok=True)
    lock_fd = open(LOCK_FILE, "r")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

        if not STATE_FILE.exists():
            raise SystemExit(
                f"{C.RED}ERROR:{C.RESET} {STATE_FILE.name} not found. "
                f"Run '{C.CYAN}python task_tool.py init{C.RESET}' first."
            )

        with open(STATE_FILE, "r") as f:
            state: dict[str, Any] = json.load(f)

        def _write(updated_state: dict[str, Any]) -> None:
            """Write state atomically via temp file + rename."""
            tmp = STATE_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(updated_state, f, indent=2, ensure_ascii=False)
                f.write("\n")
            tmp.replace(STATE_FILE)

        yield state, _write
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _find_task(state: dict, task_id: str) -> Optional[dict]:
    for t in state.get("tasks", []):
        if t["task_id"] == task_id:
            return t
    return None


def _status_icon(status: str) -> str:
    return {
        "PENDING":     f"{C.GRAY}○{C.RESET}",
        "IN_PROGRESS": f"{C.BLUE}◉{C.RESET}",
        "DONE":        f"{C.YELLOW}◉{C.RESET}",
        "COMPLETE":    f"{C.GREEN}✔{C.RESET}",
        "FAILED":      f"{C.RED}✘{C.RESET}",
    }.get(status, "?")


def _status_color(status: str) -> str:
    return {
        "PENDING":     C.GRAY,
        "IN_PROGRESS": C.BLUE,
        "DONE":        C.YELLOW,
        "COMPLETE":    C.GREEN,
        "FAILED":      C.RED,
    }.get(status, "")


def _derive_global_status(tasks: list[dict]) -> str:
    """
    Derive the global project status from the individual task states.

    Rules:
      - ANY task FAILED                  → BLOCKED
      - ALL tasks COMPLETE               → ALL_COMPLETE
      - ALL tasks DONE or COMPLETE       → REVIEW (all code written, QA pending)
      - ANY task IN_PROGRESS             → IN_PROGRESS
      - Otherwise                        → PENDING
    """
    statuses = {t["status"] for t in tasks}
    if "FAILED" in statuses:
        return "BLOCKED"
    if statuses == {"COMPLETE"}:
        return "ALL_COMPLETE"
    if statuses <= {"DONE", "COMPLETE"}:
        return "REVIEW"
    if "IN_PROGRESS" in statuses or "DONE" in statuses:
        return "IN_PROGRESS"
    return "PENDING"


def _discover_tasks_from_pending() -> list[dict]:
    """
    Scan /tasks_pending/ for task_*.md files and build the initial task list.
    Task IDs are derived from filenames: task_01_auth_ui.md → task_01_auth_ui
    Changelog files (*_changelog.md) are excluded.
    """
    if not TASKS_PENDING_DIR.exists():
        return []

    tasks: list[dict] = []
    pattern = re.compile(r"^task_.+\.md$", re.IGNORECASE)

    for path in sorted(TASKS_PENDING_DIR.iterdir()):
        if not path.is_file():
            continue
        if not pattern.match(path.name):
            continue
        # Skip changelog files
        if path.name.endswith("_changelog.md"):
            continue

        task_id = path.stem  # e.g. "task_01_auth_ui"

        # Try to extract phase from file content
        phase = _extract_phase_from_file(path)

        tasks.append({
            "task_id": task_id,
            "status": "PENDING",
            "phase": phase,
            "source_file": str(path.relative_to(PROJECT_ROOT)),
            "fail_reason": None,
            "started_at": None,
            "completed_at": None,
            "failed_at": None,
        })

    return tasks


def _extract_phase_from_file(filepath: Path) -> Optional[str]:
    """
    Attempt to extract Execution_Phase from a task markdown file.
    Looks for patterns like:
      - Execution_Phase: 1
      - **Execution_Phase**: 1
      - `Execution_Phase`: 1
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        match = re.search(
            r"\*{0,2}(?:execution_phase|Execution_Phase)\*{0,2}\s*[:=]\s*[`\"'*]?(\S+)[`\"'*]?",
            content,
            re.IGNORECASE,
        )
        return match.group(1).strip("*`\"'") if match else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    """
    Initialize task_state.json from the current /tasks_pending/ directory.
    If --feature is given, use it as the feature name; otherwise default.
    """
    if STATE_FILE.exists() and not args.force:
        print(
            f"{C.YELLOW}WARNING:{C.RESET} {STATE_FILE.name} already exists. "
            f"Use {C.CYAN}--force{C.RESET} to reinitialize."
        )
        sys.exit(1)

    tasks = _discover_tasks_from_pending()

    if not tasks:
        print(
            f"{C.YELLOW}WARNING:{C.RESET} No task files found in "
            f"{TASKS_PENDING_DIR.relative_to(PROJECT_ROOT)}/. "
            f"Creating empty state file."
        )

    feature_name = args.feature or "Unnamed Feature"

    state: dict[str, Any] = {
        "feature": feature_name,
        "global_status": "PENDING",
        "total_tasks": len(tasks),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "tasks": tasks,
    }

    # Write without locking since we're creating fresh
    LOCK_FILE.touch(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{C.GREEN}✔{C.RESET} Initialized {C.BOLD}{STATE_FILE.name}{C.RESET}")
    print(f"  Feature : {C.CYAN}{feature_name}{C.RESET}")
    print(f"  Tasks   : {C.BOLD}{len(tasks)}{C.RESET}")

    if tasks:
        print(f"\n  Discovered tasks:")
        for t in tasks:
            phase_str = f" (Phase {t['phase']})" if t.get("phase") else ""
            print(f"    {_status_icon(t['status'])} {t['task_id']}{phase_str}")


def cmd_status(args: argparse.Namespace) -> None:
    """Display the current state of the project and all tasks."""
    with locked_state() as (state, _write):
        g = state["global_status"]
        g_color = {
            "PENDING": C.GRAY,
            "IN_PROGRESS": C.BLUE,
            "REVIEW": C.YELLOW,
            "BLOCKED": C.RED,
            "ALL_COMPLETE": C.GREEN,
        }.get(g, "")

        print(f"\n{C.BOLD}╔══════════════════════════════════════╗{C.RESET}")
        print(f"{C.BOLD}║  TASK STATE DASHBOARD                ║{C.RESET}")
        print(f"{C.BOLD}╚══════════════════════════════════════╝{C.RESET}")
        print(f"  Feature : {C.CYAN}{state.get('feature', '?')}{C.RESET}")
        print(f"  Status  : {g_color}{C.BOLD}{g}{C.RESET}")
        print(f"  Tasks   : {state.get('total_tasks', '?')}")
        print(f"  Updated : {state.get('updated_at', '?')}")

        # Aggregate counts
        counts = {"PENDING": 0, "IN_PROGRESS": 0, "DONE": 0, "COMPLETE": 0, "FAILED": 0}
        for t in state.get("tasks", []):
            counts[t["status"]] = counts.get(t["status"], 0) + 1

        total = len(state.get("tasks", []))
        bar_width = 30
        if total > 0:
            complete_pct = counts["COMPLETE"] / total
            done_pct = counts["DONE"] / total
            failed_pct = counts["FAILED"] / total
            progress_pct = counts["IN_PROGRESS"] / total
            done_chars = int(bar_width * complete_pct)
            qa_chars = int(bar_width * done_pct)
            fail_chars = int(bar_width * failed_pct)
            prog_chars = int(bar_width * progress_pct)
            pend_chars = bar_width - done_chars - qa_chars - fail_chars - prog_chars
            bar = (
                f"{C.GREEN}{'█' * done_chars}{C.RESET}"
                f"{C.YELLOW}{'▓' * qa_chars}{C.RESET}"
                f"{C.BLUE}{'▓' * prog_chars}{C.RESET}"
                f"{C.RED}{'░' * fail_chars}{C.RESET}"
                f"{C.GRAY}{'·' * pend_chars}{C.RESET}"
            )
            overall_pct = int((complete_pct + done_pct * 0.8) * 100)
            print(f"\n  [{bar}] {overall_pct}%")
            print(
                f"  {C.GREEN}✔ {counts['COMPLETE']}{C.RESET}  "
                f"{C.YELLOW}◉ {counts['DONE']}{C.RESET}  "
                f"{C.BLUE}◉ {counts['IN_PROGRESS']}{C.RESET}  "
                f"{C.RED}✘ {counts['FAILED']}{C.RESET}  "
                f"{C.GRAY}○ {counts['PENDING']}{C.RESET}"
            )

        # Build phase groups
        phases: dict[str, list[dict]] = {}
        for t in state.get("tasks", []):
            phase_key = t.get("phase") or "unassigned"
            phases.setdefault(phase_key, []).append(t)

        print(f"\n{'─' * 42}")

        for phase_key in sorted(phases.keys(), key=lambda x: (x == "unassigned", x)):
            label = f"Phase {phase_key}" if phase_key != "unassigned" else "Unassigned"
            print(f"\n  {C.BOLD}{label}{C.RESET}")

            for t in phases[phase_key]:
                sc = _status_color(t["status"])
                icon = _status_icon(t["status"])
                line = f"    {icon} {sc}{t['task_id']:<32}{C.RESET} {sc}{t['status']}{C.RESET}"
                print(line)

                if args.verbose:
                    if t.get("started_at"):
                        print(f"      {C.GRAY}Started : {t['started_at']}{C.RESET}")
                    if t.get("completed_at"):
                        print(f"      {C.GRAY}Done    : {t['completed_at']}{C.RESET}")
                    if t.get("verified_at"):
                        print(f"      {C.GRAY}Verified: {t['verified_at']}{C.RESET}")
                    if t.get("fail_reason"):
                        print(f"      {C.RED}Reason  : {t['fail_reason']}{C.RESET}")

        if state["global_status"] == "BLOCKED":
            failed_tasks = [t for t in state.get("tasks", []) if t["status"] == "FAILED"]
            print(f"\n  {C.RED}{C.BOLD}⚠ PROJECT BLOCKED — {len(failed_tasks)} task(s) FAILED:{C.RESET}")
            for t in failed_tasks:
                reason = t.get("fail_reason") or "No reason provided"
                print(f"    {C.RED}✘ {t['task_id']}: {reason}{C.RESET}")

        print()


def cmd_start(args: argparse.Namespace) -> None:
    """Transition a task from PENDING → IN_PROGRESS."""
    task_id = args.task_id

    with locked_state() as (state, write):
        task = _find_task(state, task_id)
        if task is None:
            print(f"{C.RED}ERROR:{C.RESET} Task '{task_id}' not found.")
            sys.exit(1)

        current = task["status"]
        if "IN_PROGRESS" not in VALID_TRANSITIONS.get(current, set()):
            print(
                f"{C.RED}ERROR:{C.RESET} Cannot transition '{task_id}' "
                f"from {current} → IN_PROGRESS."
            )
            sys.exit(1)

        task["status"] = "IN_PROGRESS"
        task["started_at"] = _now_iso()
        state["global_status"] = _derive_global_status(state["tasks"])
        state["updated_at"] = _now_iso()

        write(state)
        print(
            f"{C.BLUE}◉{C.RESET} {C.BOLD}{task_id}{C.RESET} → "
            f"{C.BLUE}IN_PROGRESS{C.RESET}"
        )


def cmd_done(args: argparse.Namespace) -> None:
    """
    Executor marks a task as DONE (implementation finished, ready for QA).
    This does NOT trigger auto-archive. QA must verify before completion.
    """
    task_id = args.task_id

    with locked_state() as (state, write):
        task = _find_task(state, task_id)
        if task is None:
            print(f"{C.RED}ERROR:{C.RESET} Task '{task_id}' not found.")
            sys.exit(1)

        current = task["status"]
        if "DONE" not in VALID_TRANSITIONS.get(current, set()):
            print(
                f"{C.RED}ERROR:{C.RESET} Cannot transition '{task_id}' "
                f"from {current} → DONE."
            )
            sys.exit(1)

        task["status"] = "DONE"
        task["completed_at"] = _now_iso()
        state["global_status"] = _derive_global_status(state["tasks"])
        state["updated_at"] = _now_iso()

        write(state)
        print(
            f"{C.YELLOW}◉{C.RESET} {C.BOLD}{task_id}{C.RESET} → "
            f"{C.YELLOW}DONE{C.RESET} (awaiting QA review)"
        )

        # Notify if all tasks are now done/complete
        if state["global_status"] == "REVIEW":
            print(
                f"\n  {C.YELLOW}{C.BOLD}📋 All tasks implemented!{C.RESET} "
                f"Dispatch QA sessions to verify."
            )


def cmd_complete(args: argparse.Namespace) -> None:
    """
    QA certifies a task as COMPLETE (verified).
    Only accepts tasks in DONE state. Auto-archives if all tasks are verified.
    """
    task_id = args.task_id

    with locked_state() as (state, write):
        task = _find_task(state, task_id)
        if task is None:
            print(f"{C.RED}ERROR:{C.RESET} Task '{task_id}' not found.")
            sys.exit(1)

        current = task["status"]
        if "COMPLETE" not in VALID_TRANSITIONS.get(current, set()):
            if current in ("PENDING", "IN_PROGRESS"):
                print(
                    f"{C.RED}ERROR:{C.RESET} Cannot complete '{task_id}' — "
                    f"it is still {current}. "
                    f"The executor must call {C.CYAN}done{C.RESET} first."
                )
            else:
                print(
                    f"{C.RED}ERROR:{C.RESET} Cannot transition '{task_id}' "
                    f"from {current} → COMPLETE."
                )
            sys.exit(1)

        task["status"] = "COMPLETE"
        task["verified_at"] = _now_iso()
        state["global_status"] = _derive_global_status(state["tasks"])
        state["updated_at"] = _now_iso()

        write(state)
        print(
            f"{C.GREEN}✔{C.RESET} {C.BOLD}{task_id}{C.RESET} → "
            f"{C.GREEN}COMPLETE{C.RESET} (QA verified)"
        )

        # Check if ALL tasks are complete → trigger auto-archive
        if state["global_status"] == "ALL_COMPLETE":
            print(
                f"\n{C.GREEN}{C.BOLD}🎉 All tasks verified!{C.RESET} "
                f"Auto-archiving..."
            )
            _perform_archive(state)


def cmd_fail(args: argparse.Namespace) -> None:
    """
    Mark a task as FAILED with a reason.
    Sets the global project status to BLOCKED (QA Blocker).
    """
    task_id = args.task_id
    reason = args.reason

    if not reason or not reason.strip():
        print(f"{C.RED}ERROR:{C.RESET} --reason is required and cannot be empty.")
        sys.exit(1)

    with locked_state() as (state, write):
        task = _find_task(state, task_id)
        if task is None:
            print(f"{C.RED}ERROR:{C.RESET} Task '{task_id}' not found.")
            sys.exit(1)

        current = task["status"]
        # Allow failing from any non-terminal state
        if current == "COMPLETE":
            print(
                f"{C.RED}ERROR:{C.RESET} Cannot fail '{task_id}' — "
                f"it is already COMPLETE."
            )
            sys.exit(1)

        task["status"] = "FAILED"
        task["fail_reason"] = reason.strip()
        task["failed_at"] = _now_iso()
        state["global_status"] = _derive_global_status(state["tasks"])  # → BLOCKED
        state["updated_at"] = _now_iso()

        write(state)
        print(
            f"{C.RED}✘{C.RESET} {C.BOLD}{task_id}{C.RESET} → "
            f"{C.RED}FAILED{C.RESET}"
        )
        print(f"  Reason: {C.YELLOW}{reason.strip()}{C.RESET}")
        print(
            f"\n  {C.RED}{C.BOLD}⚠ PROJECT STATUS → BLOCKED{C.RESET}\n"
            f"  {C.GRAY}The Executor must address the failure reason and "
            f"then run:{C.RESET}\n"
            f"  {C.CYAN}python task_tool.py reset {task_id}{C.RESET}"
        )


def cmd_reset(args: argparse.Namespace) -> None:
    """
    Reset a FAILED task back to PENDING so the Executor can re-attempt
    after addressing the QA feedback.
    """
    task_id = args.task_id

    with locked_state() as (state, write):
        task = _find_task(state, task_id)
        if task is None:
            print(f"{C.RED}ERROR:{C.RESET} Task '{task_id}' not found.")
            sys.exit(1)

        current = task["status"]
        if "PENDING" not in VALID_TRANSITIONS.get(current, set()):
            print(
                f"{C.RED}ERROR:{C.RESET} Cannot reset '{task_id}' — "
                f"current status is {current} (only FAILED tasks can be reset)."
            )
            sys.exit(1)

        task["status"] = "PENDING"
        task["fail_reason"] = None
        task["failed_at"] = None
        task["started_at"] = None
        state["global_status"] = _derive_global_status(state["tasks"])
        state["updated_at"] = _now_iso()

        write(state)
        print(
            f"{C.YELLOW}↻{C.RESET} {C.BOLD}{task_id}{C.RESET} → "
            f"{C.GRAY}PENDING{C.RESET} (ready for re-execution)"
        )


def cmd_archive(args: argparse.Namespace) -> None:
    """
    Manually trigger the archive process.
    Without --force, this only works when ALL tasks are COMPLETE.
    """
    with locked_state() as (state, _write):
        if not args.force:
            failed = [t for t in state["tasks"] if t["status"] == "FAILED"]
            pending = [t for t in state["tasks"] if t["status"] in ("PENDING", "IN_PROGRESS")]

            if failed:
                print(
                    f"{C.RED}ERROR:{C.RESET} Cannot archive — "
                    f"{len(failed)} task(s) are FAILED. "
                    f"Resolve them first or use {C.CYAN}--force{C.RESET}."
                )
                sys.exit(1)

            if pending:
                print(
                    f"{C.RED}ERROR:{C.RESET} Cannot archive — "
                    f"{len(pending)} task(s) are still PENDING/IN_PROGRESS. "
                    f"Use {C.CYAN}--force{C.RESET} to override."
                )
                sys.exit(1)

        _perform_archive(state)


def _perform_archive(state: dict) -> None:
    """
    Move the following artifacts into .agents/history/<timestamp>/:
      - task_state.json
      - implementation_plan.md
      - tasks_pending/  (entire directory)
      - .dispatch/      (generated session prompts)

    This is the ONLY authorized cleanup mechanism.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    feature_slug = re.sub(r"[^a-z0-9]+", "_", state.get("feature", "unnamed").lower()).strip("_")
    archive_dir = ARCHIVE_BASE_DIR / f"{timestamp}_{feature_slug}"

    try:
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Move task_state.json
        if STATE_FILE.exists():
            shutil.move(str(STATE_FILE), str(archive_dir / STATE_FILE.name))
            print(f"  {C.GREEN}→{C.RESET} Archived {STATE_FILE.name}")

        # Move implementation_plan.md
        if IMPLEMENTATION_PLAN.exists():
            shutil.move(str(IMPLEMENTATION_PLAN), str(archive_dir / IMPLEMENTATION_PLAN.name))
            print(f"  {C.GREEN}→{C.RESET} Archived {IMPLEMENTATION_PLAN.name}")

        # Move tasks_pending/ directory
        if TASKS_PENDING_DIR.exists():
            shutil.move(str(TASKS_PENDING_DIR), str(archive_dir / TASKS_PENDING_DIR.name))
            print(f"  {C.GREEN}→{C.RESET} Archived {TASKS_PENDING_DIR.name}/")

        # Move .dispatch/ directory (generated session prompts)
        dispatch_dir = PROJECT_ROOT / ".dispatch"
        if dispatch_dir.exists():
            shutil.move(str(dispatch_dir), str(archive_dir / dispatch_dir.name))
            print(f"  {C.GREEN}→{C.RESET} Archived {dispatch_dir.name}/")

        # Cleanup the lock file
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()

        print(
            f"\n  {C.GREEN}{C.BOLD}✔ Archive complete:{C.RESET} "
            f"{C.CYAN}{archive_dir.relative_to(PROJECT_ROOT)}{C.RESET}"
        )

    except Exception as e:
        print(f"{C.RED}ERROR:{C.RESET} Archive failed — {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Add Task (for Planning Agent to register tasks programmatically)
# ---------------------------------------------------------------------------

def cmd_add(args: argparse.Namespace) -> None:
    """
    Add a new task to an existing task_state.json.
    Used by the Planning Agent when creating task node files.
    """
    task_id = args.task_id
    phase = args.phase
    source_file = args.source_file

    with locked_state() as (state, write):
        if _find_task(state, task_id) is not None:
            print(f"{C.YELLOW}WARNING:{C.RESET} Task '{task_id}' already exists. Skipping.")
            return

        task = {
            "task_id": task_id,
            "status": "PENDING",
            "phase": phase,
            "source_file": source_file,
            "fail_reason": None,
            "started_at": None,
            "completed_at": None,
            "failed_at": None,
        }

        state["tasks"].append(task)
        state["total_tasks"] = len(state["tasks"])
        state["updated_at"] = _now_iso()
        write(state)

        print(
            f"{C.GREEN}+{C.RESET} Added {C.BOLD}{task_id}{C.RESET}"
            + (f" (Phase {phase})" if phase else "")
        )


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task_tool",
        description="Multi-Agent Task Lifecycle Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python task_tool.py init --feature "User Authentication"
  python task_tool.py status --verbose
  python task_tool.py start   task_01_auth_repo   # Executor: starting work
  python task_tool.py done    task_01_auth_repo   # Executor: ready for QA
  python task_tool.py complete task_01_auth_repo   # QA: verified
  python task_tool.py fail    task_02_login_ui --reason "Missing error states"  # QA: defects
  python task_tool.py reset   task_02_login_ui
  python task_tool.py archive
  python task_tool.py add     task_03_tests --phase 2 --source-file tasks_pending/task_03_tests.md
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Initialize task_state.json from tasks_pending/")
    p_init.add_argument("--feature", type=str, default=None, help="Feature name for this planning session")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing task_state.json")

    # status
    p_status = sub.add_parser("status", help="Display current task states")
    p_status.add_argument("--verbose", "-v", action="store_true", help="Show timestamps and failure reasons")

    # start
    p_start = sub.add_parser("start", help="Mark a task as IN_PROGRESS")
    p_start.add_argument("task_id", type=str, help="The Task ID to start")

    # done (Executor → ready for QA)
    p_done = sub.add_parser("done", help="Mark a task as DONE (executor finished, ready for QA)")
    p_done.add_argument("task_id", type=str, help="The Task ID to mark as done")

    # complete (QA → verified)
    p_complete = sub.add_parser("complete", help="Mark a DONE task as COMPLETE (QA verified)")
    p_complete.add_argument("task_id", type=str, help="The Task ID to certify as complete")

    # fail
    p_fail = sub.add_parser("fail", help="Mark a task as FAILED (triggers QA BLOCKER)")
    p_fail.add_argument("task_id", type=str, help="The Task ID to fail")
    p_fail.add_argument("--reason", type=str, required=True, help="Explanation for the failure (required)")

    # reset
    p_reset = sub.add_parser("reset", help="Reset a FAILED task back to PENDING")
    p_reset.add_argument("task_id", type=str, help="The Task ID to reset")

    # archive
    p_archive = sub.add_parser("archive", help="Archive all artifacts to .agents/history/")
    p_archive.add_argument("--force", action="store_true", help="Archive even if tasks are not all complete")

    # add
    p_add = sub.add_parser("add", help="Add a new task to the state file")
    p_add.add_argument("task_id", type=str, help="The Task ID to register")
    p_add.add_argument("--phase", type=str, default=None, help="Execution phase number")
    p_add.add_argument("--source-file", type=str, default=None, help="Path to the task brief file")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "init":     cmd_init,
        "status":   cmd_status,
        "start":    cmd_start,
        "done":     cmd_done,
        "complete": cmd_complete,
        "fail":     cmd_fail,
        "reset":    cmd_reset,
        "archive":  cmd_archive,
        "add":      cmd_add,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
