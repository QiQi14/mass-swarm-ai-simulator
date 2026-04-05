# Study Notes — Mass-Swarm AI Simulator

Collected case studies, algorithm research, and bug postmortems from the development
of the Mass-Swarm AI Simulator.

## Bug Postmortems

Bugs discovered during Phase 2 integration testing. Each study includes: symptom,
investigation process, root cause analysis, fix, and lessons learned.

| # | Title | Impact | Root Cause |
|:-:|:------|:-------|:-----------|
| [001](001_broadcast_lagged_kills_forwarder.md) | Tokio Broadcast Lagged Kills Forwarder | All entities invisible | `while let Ok` breaks on recoverable `Lagged` error |
| [002](002_simstate_freezes_physics.md) | SimState Freezes Physics 90% of Time | Entities never move | ZMQ bridge blocks simulation via state gate |
| [003](003_changed_position_late_join.md) | Changed\<Position\> Late Join Problem | Initial entities invisible | `Changed<T>` consumed before client connects |
| [004](004_flowfield_omniscient_pathfinding.md) | Flow Field Ignores Fog of War | Swarm sees through fog | Goals collected without visibility filter |

## Algorithm Research

Deep dives into the core algorithms powering the simulation. Each study includes
mathematical foundations, design decisions, complexity analysis, and worked examples.

| # | Title | Domain | Key Concept |
|:-:|:------|:-------|:------------|
| [005](005_spatial_hash_grid.md) | Spatial Hash Grid | Spatial Indexing | O(1) proximity queries via sparse hashing |
| [006](006_chamfer_dijkstra_flow_fields.md) | Chamfer Dijkstra Flow Fields | Pathfinding | Integer L₂ approx + Central Difference Gradient |
| [007](007_disjoint_queries_zero_alloc.md) | Disjoint Queries & Zero-Alloc | ECS Architecture | Bevy's split-query pattern for mutual mutation |
| [008](008_composite_steering_boids.md) | Composite Steering (Flow + Boids) | Swarm AI | Macro navigation + micro collision avoidance |
| [009](009_bitpacked_fog_of_war.md) | Bit-Packed Fog of War | Game Systems | 632 bytes/faction for POMDP observability |

## Full Implementation Specifications

The detailed specs used by executor agents during implementation. These contain
complete Rust code, mathematical derivations, and test contracts.

| Task | Title | Location |
|:-----|:------|:---------|
| Task 02 | Spatial Hash Grid | [.agents/history/.../implementation_plan_task_02.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_02.md) |
| Task 03 | Flow Field + Registry | [.agents/history/.../implementation_plan_task_03.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_03.md) |
| Task 04 | Rule Resources | [.agents/history/.../implementation_plan_task_04.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_04.md) |
| Task 05 | Interaction + Removal Systems | [.agents/history/.../implementation_plan_task_05.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_05.md) |
| Task 06 | Movement + Spawning | [.agents/history/.../implementation_plan_task_06.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_06.md) |
| Task 07 | Telemetry & Debug Visualizer | [.agents/history/.../implementation_plan_task_07.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_07.md) |
