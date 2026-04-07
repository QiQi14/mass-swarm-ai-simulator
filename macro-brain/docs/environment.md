# The Gymnasium Environment

Located in `src/env/`, this module's job is translating the raw physics engine into a format the AI can understand.

## What is a Gymnasium Environment?
For an AI to learn using standard tools, it needs to interact with the world via a strict `step()` API:
`observation, reward, terminated, truncated, info = env.step(action)`

Our **`SwarmEnv`** (`swarm_env.py`) wraps the ZeroMQ bridge. 

### How it works:
1. **Reset**: When `env.reset()` is called, Python sends a message telling Rust to clear the map and spawn a fresh wave. It then reads the initial state.
2. **Step**: When the AI chooses an `action` (a discrete integer), `SwarmEnv` converts it to a `MacroDirective` JSON payload and fires it to Rust. Rust runs the engine for `X` ticks, pauses, and replies with a new snapshot of the world.
3. **Action Masking**: We use a `MaskablePPO` variant. If a Faction's Frenzy ability is on cooldown, `SwarmEnv` masks out the "Use Frenzy" action so the AI physically cannot choose it, saving it from wasting time learning to avoid illegal moves.

## Shaping the Reward (`rewards.py`)

If you just tell an AI "win the game", it will take thousands of hours of random flailing to accidentally win and receive its first reward. This is called a *Sparse Reward* problem.

### The Solution: Reward Shaping
We use dense reward shaping. At every step, `rewards.py` evaluates the game state and hands out micro-rewards:
- **Survival Bonus**: Small `+` for staying alive.
- **Kill Bonus**: `+` for destroying enemy units.
- **Flanking Bonus**: `+` if friendly units surround an enemy group without colliding (encourages complex pincer strategies).
- **Pacifist Exploit Guard**: If the AI learns that running away extends the game and farms "Survival Bonus" infinitely, we apply a massive attenuation penalty. If you don't engage, survival means nothing.

## Translation (`spaces.py`)
This defines the mathematical bounds of the data. 
- The `Observation Space` flattens the 2D grid into a 1D vector of integers (Entity counts, zone modifiers).
- The `Action Space` is a `Discrete` range mapped to specific high-level commands.
