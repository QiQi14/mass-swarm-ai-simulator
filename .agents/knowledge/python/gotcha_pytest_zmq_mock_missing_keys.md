# Lesson: Pytest ZMQ Mock Missing Loop-Termination Keys

**Category:** gotcha
**Discovered:** Task 04 (task_04_python_profile_extension_changelog.md)
**Severity:** high

## Context
When writing unit tests involving ZMQ polling loops (e.g., `SwarmEnv.step()` waiting on `recv_string()` mock data with a while True tick-swallowing behavior).

## Problem
Test execution hangs indefinitely if `recv_string.side_effect` payloads exclude specifically checked loop-condition keys. For example, if the implementation waits for a message where `"type": "state_snapshot"`, and the mock returns empty dictionaries `{}`, the environmental `while True:` loop never breaks, freezing Pytest.

## Correct Approach
Always provide the strict terminating condition fields expected by the event loop in test mock payloads, like ensuring a `{"type": "state_snapshot"}`. Also ensure error simulation cases accurately mimic production structures, like setting explicit exceptions via `zmq.error.Again()` rather than omitting keys.

## Example
- ❌ What the executor did: Returning an incomplete dict that does not fulfill loop checks: `recv_string.return_value = "{}"`.
- ✅ What it should be: Explicitly defining loop-termination keys: `recv_string.return_value = json.dumps({"type": "state_snapshot", "active_sub_factions": []})`.
