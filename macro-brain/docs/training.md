# Training Pipeline & Curriculum

Located in `src/training/`, this module governs *how* the Brain learns.

## Train.py (The Entry Point)
This is where the actual model initialization happens. We load hyperparameter configurations (like Learning Rate, Batch Size, Gamma) from JSON profiles. We instantiate a `MaskablePPO` core, wrap our `SwarmEnv` into a vectorized environment (allowing multiple simulations to train in parallel), and launch `.learn()`.

## Curriculum Learning (`curriculum.py`)
Training an AI to defeat a massive, coordinated enemy swarm on Day 1 is impossible. It will fail repeatedly and never learn anything.

### What is Curriculum Learning?
We break the training into a **5-Stage Curriculum**, exactly like a video game tutorial:
1. **Phase 1: Stationary Targets**. The enemy doesn't shoot back. The AI learns basic movement and pathfinding.
2. **Phase 2: Dumb Rush**. The enemy moves straight at the AI. The AI learns basic kiting.
3. **Phase 3: Environmental Hazards**. Lava and slow-zones are introduced. The AI learns to navigate safely.
4. **Phase 4: Coordinated Skirmish**. The enemy uses boids and flanking.
5. **Phase 5: Full Wars**. Massive entity counts, full fog of war active.

### How it works
The `CurriculumManager` analyzes the AI's win rate over a rolling window. If the win rate exceeds 85%, it automatically "Promotes" the AI to the next stage by sending an environment modifier configuration over ZMQ to the Rust Core. If the win rate drops below 30%, it "Demotes" the AI so it doesn't catastrophically unlearn its base skills.

## Callbacks (`callbacks.py`)
During an RL training run (which can take days), we need to peek inside.
Callbacks are hooks that trigger at specific intervals.
- **`TensorBoardCallback`**: Logs training metrics (Loss, Reward avg, Curriculum Phase) to the dashboard.
- **`CheckpointCallback`**: Saves a `.zip` copy of the neural weights every `N` steps, so if your machine crashes, you don't lose days of training.
