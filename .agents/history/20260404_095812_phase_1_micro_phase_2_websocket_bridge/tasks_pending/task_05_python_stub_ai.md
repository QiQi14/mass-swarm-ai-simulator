---
Task_ID: 05_python_stub_ai
Execution_Phase: Phase A (Parallelizable)
Model_Tier: basic
Target_Files:
  - macro-brain/requirements.txt
  - macro-brain/src/__init__.py
  - macro-brain/src/stub_ai.py
Dependencies: None
Context_Bindings: []
---

# STRICT INSTRUCTIONS

> **Feature:** P1_MP3 — ZeroMQ Bridge + Stub AI Round-Trip
> **Role:** Create the Python-side ZMQ REP responder that the Rust Micro-Core connects to.

1. **Create `macro-brain/requirements.txt`**
   ```
   pyzmq>=25.1.2
   ```

2. **Create `macro-brain/src/__init__.py`**
   - Empty file (Python package marker).

3. **Create `macro-brain/src/stub_ai.py`**
   - This script is a minimal ZeroMQ REP socket server that Python binds to `tcp://*:5555`.
   - It receives JSON state snapshots from the Rust Micro-Core and replies with a fixed `HOLD` action.
   - Complete implementation:

   ```python
   """
   Stub AI Responder — ZeroMQ REP socket.

   Binds to tcp://*:5555 and echoes a HOLD action for every state
   snapshot received from the Rust Micro-Core.

   Usage:
       python3 src/stub_ai.py
   """

   import json
   import zmq


   BIND_ADDRESS = "tcp://*:5555"
   HOLD_ACTION = {"type": "macro_action", "action": "HOLD", "params": {}}


   def main():
       context = zmq.Context()
       socket = context.socket(zmq.REP)
       socket.bind(BIND_ADDRESS)
       print(f"[Stub AI] Listening on {BIND_ADDRESS}")

       try:
           while True:
               # Receive state snapshot from Rust
               message = socket.recv_json()
               tick = message.get("tick", "?")
               entity_count = len(message.get("entities", []))
               swarm = message.get("summary", {}).get("swarm_count", "?")
               defender = message.get("summary", {}).get("defender_count", "?")
               print(
                   f"[Stub AI] Tick {tick} | "
                   f"Entities: {entity_count} | "
                   f"Swarm: {swarm} | Defenders: {defender}"
               )

               # Reply with HOLD action
               socket.send_json(HOLD_ACTION)
       except KeyboardInterrupt:
           print("\n[Stub AI] Shutting down.")
       finally:
           socket.close()
           context.term()


   if __name__ == "__main__":
       main()
   ```

   **Requirements:**
   - The script MUST bind to `tcp://*:5555` (not connect — it is the server).
   - The reply MUST be exactly `{"type": "macro_action", "action": "HOLD", "params": {}}`.
   - The script MUST handle `KeyboardInterrupt` gracefully and close the socket.
   - The script MUST log the tick number and entity count from each received snapshot.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: python
Acceptance_Criteria:
  - "`python3 -m py_compile macro-brain/src/stub_ai.py` succeeds with no errors."
  - "The script starts without errors when `pyzmq` is installed."
Suggested_Test_Commands:
  - `python3 -m py_compile macro-brain/src/stub_ai.py`
