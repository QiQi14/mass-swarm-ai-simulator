#!/usr/bin/env python3
"""
Generate tests/INDEX.md for an archive folder by scanning QA certification reports.

Extracts test file information from *_qa_report.md files in the archive's
tasks_pending/ directory and produces a structured index for traceability.

Usage:
  # Index a specific archive:
  python3 .agents/scripts/gen_tests_index.py .agents/history/20260401_104645_my_feature

  # Index ALL archives (batch mode):
  python3 .agents/scripts/gen_tests_index.py --all
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
HISTORY_DIR = SCRIPT_DIR / "history"


def extract_feature_name(archive_path: Path) -> str:
    """Extract feature name from task_state.json or folder name."""
    state_file = archive_path / "task_state.json"
    if state_file.is_file():
        try:
            data = json.loads(state_file.read_text())
            return data.get("feature", archive_path.name)
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: parse folder name (timestamp_feature_name → Feature Name)
    name = archive_path.name
    parts = name.split("_", 2)  # Split off timestamp prefix
    if len(parts) >= 3:
        return parts[2].replace("_", " ").title()
    return name


def extract_archive_date(archive_path: Path) -> str:
    """Extract date from archive folder name or task_state.json."""
    state_file = archive_path / "task_state.json"
    if state_file.is_file():
        try:
            data = json.loads(state_file.read_text())
            updated = data.get("updated_at", "")
            if updated:
                return updated[:10]  # YYYY-MM-DD
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: parse folder name (YYYYMMDD_HHMMSS_...)
    m = re.match(r"(\d{4})(\d{2})(\d{2})", archive_path.name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return datetime.now().strftime("%Y-%m-%d")


def parse_qa_report(report_path: Path) -> dict:
    """Parse a QA certification report for test file entries."""
    content = report_path.read_text()
    task_id = report_path.stem.replace("_qa_report", "")

    result = {
        "task_id": task_id,
        "test_files": [],
        "test_type": "unknown",
        "test_stack": "unknown",
        "acceptance_criteria_covered": [],
        "overall_result": "UNKNOWN",
    }

    # Extract certification decision (COMPLETE or FAIL)
    # Handles: **Status:** COMPLETE  |  - **Status:** COMPLETE  |  Status: COMPLETE
    decision_match = re.search(
        r"\*?\*?Status:?\*?\*?\s*(COMPLETE|FAIL|PASS)",
        content,
        re.IGNORECASE,
    )
    if decision_match:
        status = decision_match.group(1).upper()
        result["overall_result"] = "PASS" if status in ("COMPLETE", "PASS") else "FAIL"

    # Extract test type from Verification_Strategy or report
    # Handles: Test_Type: manual_steps  |  Test_Type: unit
    type_match = re.search(r"Test_Type:\s*(\w+)", content)
    if type_match:
        result["test_type"] = type_match.group(1)
    # Note: if Test_Type not found, we infer later after test files are parsed

    # Extract test stack
    # Handles: **Test Stack:** `stacks/react-fsd`  |  Test Stack: stacks/kotlin-multiplatform
    stack_match = re.search(
        r"\*?\*?Test[ _]Stack:?\*?\*?\s*`?([^`\n]+?)`?\s*$",
        content,
        re.IGNORECASE | re.MULTILINE,
    )
    if stack_match:
        result["test_stack"] = stack_match.group(1).strip()

    # Extract test files from "Test Files Created" section
    # Handles formats like:
    #   - `filename.test.ts`
    #   - filename.test.ts
    #   - **Test Files Created:** `file1.test.ts`, `file2.test.ts`
    files_section = re.search(
        r"Test Files Created\s*[:\-]\s*(.*?)(?=\n###|\n##|\n\*\*|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if files_section:
        section_text = files_section.group(1)
        # Find all backtick-quoted filenames
        backtick_files = re.findall(r"`([^`]+\.\w+)`", section_text)
        # Find all list-item filenames (- filename.ext)
        list_files = re.findall(r"^\s*[-*]\s+`?([^\s`]+\.\w+)`?", section_text, re.MULTILINE)
        # Merge and deduplicate
        all_files = list(dict.fromkeys(backtick_files + list_files))
        result["test_files"] = all_files

    # Extract coverage info
    coverage_match = re.search(
        r"Coverage\s*[:\-]\s*(.*?)(?=\n###|\n##|\n\*\*|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if coverage_match:
        coverage_text = coverage_match.group(1).strip()
        # Extract criterion numbers like #1, #2, #3
        criteria_nums = re.findall(r"#(\d+)", coverage_text)
        if criteria_nums:
            result["acceptance_criteria_covered"] = [f"#{n}" for n in criteria_nums]
        else:
            # Use the raw text as a single coverage note
            result["acceptance_criteria_covered"] = [coverage_text[:100]]

    # Extract from acceptance criteria table
    if not result["acceptance_criteria_covered"]:
        criteria_matches = re.findall(
            r"\|\s*(\d+)\s*\|[^|]+\|\s*[✅✓]\s*\|",
            content,
        )
        if criteria_matches:
            result["acceptance_criteria_covered"] = [f"#{n}" for n in criteria_matches]

    # Infer test_type if not explicitly set
    if result["test_type"] == "unknown":
        if result["test_files"]:
            result["test_type"] = "unit"
        elif re.search(r"manual.*(verification|testing|device|walkthrough)", content, re.IGNORECASE):
            result["test_type"] = "manual_steps"

    return result


def generate_index(archive_path: Path) -> bool:
    """Generate tests/INDEX.md for a single archive folder."""
    tasks_dir = archive_path / "tasks_pending"
    if not tasks_dir.is_dir():
        return False

    # Find all QA reports
    reports = sorted(tasks_dir.glob("*_qa_report.md"))
    if not reports:
        return False

    # Parse all reports
    entries = []
    for report in reports:
        parsed = parse_qa_report(report)
        entries.append(parsed)

    # Check if there are any test files across all reports
    has_tests = any(e["test_files"] for e in entries)
    if not has_tests:
        # Still generate index but note no test files
        pass

    feature_name = extract_feature_name(archive_path)
    archive_date = extract_archive_date(archive_path)

    # Build index content
    lines = [
        "# Test Archive Index",
        "",
        "> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.",
        "",
        f"**Feature:** {feature_name}",
        f"**Archived:** {archive_date}",
        f"**Tasks Verified:** {len(entries)}",
        "",
    ]

    if has_tests:
        lines.extend([
            "## Test Files",
            "",
            "| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |",
            "|-----------|------|-----------|------------|-----------------|--------|",
        ])

        for entry in entries:
            if not entry["test_files"]:
                continue
            criteria_str = ", ".join(entry["acceptance_criteria_covered"]) or "—"
            for tf in entry["test_files"]:
                lines.append(
                    f"| `{tf}` "
                    f"| {entry['task_id']} "
                    f"| {entry['test_type']} "
                    f"| {entry['test_stack']} "
                    f"| {criteria_str} "
                    f"| {entry['overall_result']} |"
                )
        lines.append("")

    # Summary section
    lines.extend([
        "## Verification Summary",
        "",
        "| Task | Test Type | Files | Result |",
        "|------|-----------|-------|--------|",
    ])

    for entry in entries:
        file_count = len(entry["test_files"])
        file_str = f"{file_count} file(s)" if file_count > 0 else "manual only"
        lines.append(
            f"| {entry['task_id']} "
            f"| {entry['test_type']} "
            f"| {file_str} "
            f"| {entry['overall_result']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
    ])

    # Write index
    tests_dir = archive_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    index_file = tests_dir / "INDEX.md"
    index_file.write_text("\n".join(lines) + "\n")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 .agents/scripts/gen_tests_index.py <archive_path>")
        print("  python3 .agents/scripts/gen_tests_index.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        if not HISTORY_DIR.is_dir():
            print(f"✘ History directory not found: {HISTORY_DIR}")
            sys.exit(1)

        count = 0
        skipped = 0
        for name in sorted(os.listdir(HISTORY_DIR)):
            archive_path = HISTORY_DIR / name
            if not archive_path.is_dir():
                continue
            if generate_index(archive_path):
                print(f"  ✔ {name}/tests/INDEX.md")
                count += 1
            else:
                skipped += 1

        print(f"\n✔ Generated {count} index(es), skipped {skipped} archive(s) (no QA reports)")
    else:
        archive_path = Path(sys.argv[1]).resolve()
        if not archive_path.is_dir():
            print(f"✘ Archive directory not found: {archive_path}")
            sys.exit(1)

        if generate_index(archive_path):
            print(f"✔ Generated {archive_path / 'tests' / 'INDEX.md'}")
        else:
            print(f"✘ No QA reports found in {archive_path / 'tasks_pending'}")
            sys.exit(1)


if __name__ == "__main__":
    main()
