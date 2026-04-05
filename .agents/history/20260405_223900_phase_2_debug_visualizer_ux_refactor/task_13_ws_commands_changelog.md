# Task 13: WS Commands Changelog

## Touched Files
- `micro-core/src/systems/ws_command.rs` - **MODIFIED**

## Contract Fulfillment
- Enhanced `spawn_wave` with optional `spread` variable and Fibonacci Spiral algorithm that prevents initial clump and skips wall cells. Spawned entities now include `VisionRadius`.
- Added `set_terrain` command that batch updates terrain configuration based on the provided list of cells.
- Added `clear_terrain` command that resets the `TerrainGrid` to its default costs (both hard and soft costs return to 100).
- Added `save_scenario` command that broadcasts back `scenario_data` containing the current terrain grid layout and entity details inside the simulation. 
- Added `load_scenario` that removes all current entities, applies the new terrain data, and spawns the new entities. It also correctly maintains `NextEntityId`.
- Added `set_fog_faction` to toggle setting the `ActiveFogFaction` resource.

## Deviations/Notes
- **Missing Resource Dependency (`ActiveFogFaction`)**: 
  Based on my task instructions, I was strictly told to `set` the `ActiveFogFaction` resource which was stated to be created in Task 12 (`task_12_visibility_ipc`). However, before making any modifications, I performed a search across `mass-swarm-ai-simulator` focusing heavily on `ws_sync.rs` and `visibility.rs` where I confirmed the resource **was completely missing from the codebase**. 
  
  Since I am strictly instructed under **Rule 1: Scope Isolation** to ONLY modify files inside my `Target_Files` (`ws_command.rs`), I have locally declared `pub struct ActiveFogFaction(pub Option<u32>);` inside `micro-core/src/systems/ws_command.rs` in order to appease the Rust compiler and finish up logic inside my `set_fog_faction` message handler. QA agent and/or the next assignee should ensure the architecture binds this correctly once the visibility/sync modules formally export this resource. 
  
- The JSON input structure for the WebSocket commands inside the tests was incorrectly parsing without `"type": "command"`, so all test implementations were modified to include the `type` field to assure deserialization inside `try_recv()` goes through successfully. All mandated tests now pass.

## Human Interventions
- In response to reporting the undocumented gap about the missing `ActiveFogFaction` reference, the human intervention authorized to proceed implementing the task acknowledging that a *layer interaction later task will bind all items together*. Thus following the instruction, the placeholder is placed and tracked here for verification protocols.
