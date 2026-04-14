# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Phase 1 Micro-Phase 2: WebSocket Bridge
**Archived:** 2026-04-04
**Tasks Verified:** 8

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `micro-core/src/bridges/ws_server.rs` | task_02_ws_server | unit | cargo test | ** Verified WebSocket connection logic, rx channel reception, and sink transmission.
- **Test Stack: | PASS |
| `micro-core/src/systems/ws_sync.rs` | task_03_ws_sync_system | unit | cargo test | ** Tested state projection/mapping (e.g., verifying coordinate and ID layout) onto JSON string forma | PASS |
| `.agents/scripts/ws_test.py` | task_04_integration_ws | unit | unknown | ** Validates WS delta messages stream emission `{"type":"SyncDelta"...}` and JSON content.
- **Test  | PASS |
| `micro-core/src/bridges/zmq_protocol.rs` | task_06_zmq_protocol_cargo | unit | cargo | ** Tests cover serialization mapping (`type` attribute mapping JSON matching), `MacroAction`, and pa | PASS |
| `micro-core/src/bridges/zmq_bridge.rs` | task_07_zmq_bridge_plugin | unit | cargo test | ** 
  1. Default config check
  2. Config JSON serialization roundtrip
  3. `ai_trigger_system` skip | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_ws_dependencies_and_contracts | unknown | manual only | PASS |
| task_02_ws_server | unit | 1 file(s) | PASS |
| task_03_ws_sync_system | unit | 1 file(s) | PASS |
| task_04_integration_ws | unit | 1 file(s) | PASS |
| task_05_python_stub_ai | manual_steps | manual only | PASS |
| task_06_zmq_protocol_cargo | unit | 1 file(s) | PASS |
| task_07_zmq_bridge_plugin | unit | 1 file(s) | PASS |
| task_08_integration_zmq | manual_steps | manual only | PASS |

---

*Generated on 2026-04-13 20:18:34*
