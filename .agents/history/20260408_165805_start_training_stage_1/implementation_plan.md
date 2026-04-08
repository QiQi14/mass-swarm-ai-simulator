# Start Stage 1 ML Training & Reduce Hardware Load

We are ready to start the first stage of ML training. You have also requested to "reduce combat speed to avoid hardware overheat". There is a slight ambiguity in how to achieve this, so this plan outlines the options.

## User Review Required

> [!IMPORTANT]
> **What do you mean by "combat speed"?**
> 
> 1. **Throttle the simulation (Recommended for overheat):** 
>    Currently, in `train.sh`, the Rust Micro-Core `custom_runner` runs as fast as possible (`loop { app.update(); }` without sleep) when `is_training` is true. This maxes out the CPU core. We can add a sleep duration (e.g., limit it to 20-60 TPS) to drastically reduce CPU usage and prevent hardware overheat.
> 2. **Reduce In-Game Variables:** 
>    We can reduce the actual `max_speed` (currently 60.0) in the movement system and `delta_per_second` (currently -25.0 damage) in the combat rules inside `default_swarm_combat.json`. Combat will take longer to resolve, meaning the AI evaluates interactions over more ticks.
> 3. **Increase AI Evaluation Interval:**
>    We can increase `ai_eval_interval_ticks` (currently 30) in the profile to make the AI run less frequently, saving Python-side CPU limits.
> 
> Please let me know which approach you want to take or if you want a combination!

## Proposed Changes

### Configuration / Execution Module

#### [MODIFY] [main.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/main.rs) (Option 1)
- Modify `custom_runner` to enforce a throttle even when `is_training = true`. 
- For instance, applying a `std::thread::sleep` if elapsed time is under `1.0 / 60.0` seconds (or `1.0 / 30.0` for even lower hardware stress).

#### [MODIFY] [default_swarm_combat.json](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/profiles/default_swarm_combat.json) (Option 2/3)
- Adjust `movement:max_speed` and `combat:rules[0].delta_per_second` to physically reduce speeds.
- Alternatively, adjust `ai_eval_interval_ticks`.

## Verification Plan

### Manual Verification
- We will execute `./train.sh` and monitor the system.
- The visualizer or console output will show the step cadence. We can confirm hardware temperatures/CPU usage via `top` remain under threshold.

---
**Once you approve and select the preferred throttling approach, I will execute the changes and launch the training script!**
