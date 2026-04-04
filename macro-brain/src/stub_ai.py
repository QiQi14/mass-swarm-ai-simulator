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
