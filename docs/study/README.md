# Study Notes

Engineering case studies documenting bugs, design decisions, and research encountered during development. Each entry captures the problem, root cause analysis, and solution.

## Index

### Phase 2: Core Algorithms
| # | Title | Topic |
|---|-------|-------|
| [001](001_broadcast_lagged_kills_forwarder.md) | Broadcast Lagged Kills Forwarder | WS delta sync missed entity deaths |
| [002](002_simstate_freezes_physics.md) | SimState Freezes Physics | Bevy state machine blocked ECS systems |
| [003](003_changed_position_late_join.md) | Changed\<Position\> Late Join | Change detection missed initial spawns |
| [004](004_flowfield_omniscient_pathfinding.md) | Flow Field Omniscient Pathfinding | Pathfinding ignored Fog of War |
| [005](005_spatial_hash_grid.md) | Spatial Hash Grid | O(1) neighbor queries at 10K+ scale |
| [006](006_chamfer_dijkstra_flow_fields.md) | Chamfer Dijkstra Flow Fields | Mass pathfinding without per-entity A* |
| [007](007_disjoint_queries_zero_alloc.md) | Disjoint Queries Zero Allocation | Bevy ECS borrow checker patterns |
| [008](008_composite_steering_boids.md) | Composite Steering Boids | Flow field + separation blending |
| [009](009_bitpacked_fog_of_war.md) | Bit-Packed Fog of War | Memory-efficient visibility grid |

### Phase 3: RL Training & Multi-Master Arbitration
| # | Title | Topic |
|---|-------|-------|
| [010](010_rl_training_methodology.md) | RL Training Methodology | 2-stage curriculum, reward shaping, OGM decision, MaskablePPO |
| [011](011_3tier_interactable_terrain.md) | 3-Tier Interactable Terrain | Terrain encoding, Moses Effect, procedural generation |
| [012](012_multi_master_arbitration.md) | Multi-Master Arbitration | Authority tiers, 8-action vocabulary, 8 safety patches |
| [013](013_training_stage_refinement.md) | Training Stage Refinement | 5-Stage curriculum expansion, Retreat action locking, dynamic spawning, decoupled '--training' flag |
