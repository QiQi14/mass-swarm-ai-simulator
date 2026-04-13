# Task 07: ZMQ Protocol Upgrade + Atomic Reset + Terrain Tiers

**Task_ID:** `task_07_zmq_protocol_upgrade`
**Execution_Phase:** 3
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/bridges/zmq_protocol.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_bridge/systems.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_bridge/mod.rs` (MODIFY)
  - `micro-core/src/terrain.rs` (MODIFY)
  - `micro-core/src/systems/flow_field_update.rs` (MODIFY)
**Dependencies:** Task 03 (DensityMaps), Task 05 (directive executor resources + systems)
**Context_Bindings:**
  - `implementation_plan.md` → ZMQ Protocol section (FULL — includes AiResponse, ResetEnvironment, terrain tiers)
  - `implementation_plan_feature_2.md` → Task 07 section (legacy reference)
  - `skills/rust-code-standards`

## Strict Instructions

### 1. ZMQ Response Envelope (`zmq_protocol.rs`)

Add the following types to handle the **dual response format** from Python:

```rust
/// Discriminated union for ZMQ responses from Python.
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum AiResponse {
    #[serde(rename = "macro_directive")]
    Directive {
        #[serde(flatten)]
        directive: MacroDirective,
    },
    
    #[serde(rename = "reset_environment")]
    ResetEnvironment {
        terrain: Option<TerrainPayload>,
        spawns: Vec<SpawnConfig>,
    },
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct TerrainPayload {
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SpawnConfig {
    pub faction_id: u32,
    pub count: u32,
    pub x: f32,
    pub y: f32,
    pub spread: f32,
}
```

### 2. Terrain Tier Constants & Methods (`terrain.rs`)

Add 3-tier terrain encoding:

```rust
pub const TERRAIN_DESTRUCTIBLE_MIN: u16 = 60_001;
pub const TERRAIN_DESTRUCTIBLE_MAX: u16 = 65_534;
pub const TERRAIN_PERMANENT_WALL: u16 = u16::MAX; // 65_535

impl TerrainGrid {
    pub fn is_destructible(&self, cell: IVec2) -> bool {
        let cost = self.get_hard_cost(cell);
        cost >= TERRAIN_DESTRUCTIBLE_MIN && cost <= TERRAIN_DESTRUCTIBLE_MAX
    }
    
    pub fn is_permanent_wall(&self, cell: IVec2) -> bool {
        self.get_hard_cost(cell) == TERRAIN_PERMANENT_WALL
    }
    
    pub fn is_wall(&self, cell: IVec2) -> bool {
        self.get_hard_cost(cell) >= TERRAIN_DESTRUCTIBLE_MIN
    }
    
    pub fn damage_cell(&mut self, cell: IVec2, damage: u16) -> bool {
        if !self.in_bounds(cell) { return false; }
        let idx = (cell.y as u32 * self.width + cell.x as u32) as usize;
        let cost = self.hard_costs[idx];
        if cost == TERRAIN_PERMANENT_WALL { return false; }
        if cost >= TERRAIN_DESTRUCTIBLE_MIN {
            let new_cost = cost.saturating_sub(damage);
            if new_cost < TERRAIN_DESTRUCTIBLE_MIN {
                self.hard_costs[idx] = 100;
                return true;
            }
            self.hard_costs[idx] = new_cost;
        }
        false
    }
}
```

### 3. `ai_poll_system` — Handle `AiResponse` Envelope (`systems.rs`)

Update `ai_poll_system` to parse `AiResponse` instead of `MacroAction`:

- If `AiResponse::Directive` → extract `MacroDirective`, forward to `LatestDirective` resource
- If `AiResponse::ResetEnvironment` → atomic reset:
  1. Despawn all entities
  2. Apply terrain (or reset to flat if `terrain: null`)
  3. Respawn factions per `spawns` config (Fibonacci spiral)
  4. Dirty all flow fields
  5. Send fresh snapshot on next trigger cycle
- **Legacy fallback:** If parsing as `AiResponse` fails, try `MacroAction` (backward compat)

### 4. Populate Snapshot with Live Data (`systems.rs`)

`build_state_snapshot` must read from ECS resources:
- `density_maps` ← `Res<DensityMaps>` 
- `intervention_active` ← `Res<InterventionTracker>`
- `active_zones` ← `Res<ActiveZoneModifiers>` → map to `ZoneModifierSnapshot`
- `active_sub_factions` ← `Res<ActiveSubFactions>`
- `aggro_masks` ← `Res<AggroMaskRegistry>`

### 5. Moses Effect Guard (`flow_field_update.rs`)

The existing guard (`if current_cost == u16::MAX { continue; }`) already only protects Tier 2 permanent walls. **Destructible walls (60,001-65,534) pass through.** Update the comment to reflect the 3-tier model. No logic change needed.

## CRITICAL: ZMQ REP Discipline During Reset

The `ResetEnvironment` triggers a **2-cycle ZMQ exchange**:
1. Rust sends snapshot → Python replies `ResetEnvironment` 
2. Rust processes reset, sends **fresh snapshot** → Python replies `Hold`

The `ai_poll_system` must re-trigger `ai_trigger_system` after processing a reset to send the fresh snapshot.

## Verification_Strategy
```
Test_Type: unit + integration
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - AiResponse::Directive parses correctly with all 8 MacroDirective variants
  - AiResponse::ResetEnvironment parses with terrain payload
  - AiResponse::ResetEnvironment parses with terrain=null
  - Legacy MacroAction fallback still works
  - Terrain tier helpers: is_destructible, is_permanent_wall, is_wall
  - damage_cell: permanent wall immune, destructible wall reduces, collapses at threshold
  - Moses Effect: permanent walls immune to zone modifiers (unchanged)
  - Moses Effect: destructible walls CAN be modified by zone modifiers
  - Snapshot includes density_maps, intervention_active, active_zones, active_sub_factions, aggro_masks
  - 20+ tests total
Suggested_Test_Commands:
  - "cd micro-core && cargo test zmq"
  - "cd micro-core && cargo test terrain"
  - "cd micro-core && cargo test flow_field"
```
