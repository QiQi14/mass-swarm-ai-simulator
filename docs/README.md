# Documentation

Developer-facing documentation for the Mass-Swarm AI Simulator.

## Guides

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | Tri-Node system overview, data flow, and design decisions |
| [IPC Protocol](ipc-protocol.md) | Complete message schema for ZMQ and WebSocket bridges |
| [Agent Workflow](agent-workflow.md) | Multi-agent task framework (Plan → Dispatch → Execute → Verify) |

## Study Notes

In-depth engineering case studies documenting bugs, design decisions, and research encountered during development. See [study/README.md](study/README.md) for the full index.

### Phase 2: Core Algorithms (001–009)
Spatial hash grid, Chamfer Dijkstra flow fields, composite Boids steering, bit-packed Fog of War, and 5 bug investigations.

### Phase 3: RL Training & Multi-Master Arbitration (010–012)
RL training methodology (MaskablePPO curriculum), 3-tier interactable terrain encoding, and multi-master arbitration architecture.
