# Lesson: Never Use Heredocs in run_command — Use write_to_file Instead

**Category:** tooling
**Discovered:** Token Estimation Script (2026-04-05), confirmed recurring across multiple sessions
**Severity:** high

## Context
Agents frequently need to create test files, config files, or multi-line content on disk. The natural shell approach is `cat > file << 'EOF' ... EOF` (heredoc syntax).

## Problem
The `run_command` tool sends commands to a shell subprocess. Heredoc syntax (`<< 'EOF'`) is **unreliable** in this context:

1. **Invisible whitespace** — The EOF marker requires exact matching. Trailing spaces, tabs, or encoding differences cause the shell to hang indefinitely waiting for a terminator that never arrives.
2. **Stacked heredocs** — Multiple `cat << EOF` blocks in one command compound the failure risk. If the first hangs, the entire command is stuck.
3. **Terminal zombie cascade** — A hung heredoc consumes a terminal slot. Subsequent `run_command` calls fail with `Failed to start terminal` because the zombie process blocks new terminal allocation.
4. **Session crash** — The terminal failure propagates to the entire Antigravity session, causing a crash that loses conversation context.

## Correct Approach
**Always use `write_to_file` (or `write_to_file` with `Overwrite: true`) to create files with multi-line content.** Never use heredocs, `echo -e`, or `printf` with embedded newlines in `run_command`.

## Example
- ❌ Anti-pattern (causes terminal hang → session crash):
  ```bash
  # DO NOT DO THIS in run_command
  cat > tasks_pending/task_01.md << 'EOF'
  # Task Brief
  ...multi-line content...
  EOF
  ```

- ✅ Best practice:
  Use the `write_to_file` tool directly to create the file, then use `run_command` only for simple, single-line commands (ls, cp, python3 script.py, etc.).

## Additional Rules for run_command Safety
1. **Keep commands single-line** — avoid multi-line strings, heredocs, and complex pipelines
2. **Don't chain file-creation commands** — if you need to create 3 files, make 3 separate `write_to_file` calls
3. **Check terminal health** — if a `run_command` fails with timeout or `Failed to start terminal`, the session may be in a degraded state
