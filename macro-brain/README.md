# Macro-Brain

Welcome to the **Macro-Brain** module! If the `micro-core` is the physical reality of the simulation, the `macro-brain` is the strategic general. It is a Machine Learning environment powered by Python.

## What is the Macro-Brain?
It is a Reinforcement Learning (RL) pipeline built using [Stable-Baselines3](https://stable-baselines3.readthedocs.io/en/master/) and [Gymnasium](https://gymnasium.farama.org/). 
Instead of controlling every single ant in the swarm individually, this AI acts as the "Hive Mind". It issues high-level commands (e.g., "Attack Zone B", "Frenzy Buff", "Retreat") via ZeroMQ to the Rust engine, sees the results, and adapts its policy to maximize its reward.

## Why Python and SB3?
The Rust ecosystem is unparalleled for raw physics simulation speed, but the Python ecosystem is unparalleled for AI research. Libraries like PyTorch and Stable-Baselines3 are industry standards. By splitting our architecture over a ZeroMQ bridge, we get the absolute best of both worlds without compromise.

## Core Keywords for Further Learning
- **Reinforcement Learning (RL)**: Action, State, Reward loop.
- **PPO (Proximal Policy Optimization)**: The specific neural network algorithm we use.
- **Gymnasium**: The standard API for reinforcement learning environments.
- **Curriculum Learning**: Training an AI on easy tasks first, then progressively increasing difficulty.

## Directory Map (Deep Dive)
To avoid an overwhelmingly large document, technical details are split into specific domains:

1. [**The Environment (`src/env/`)**](docs/environment.md) - How we wrap the Rust engine into a standard Gymnasium RL interface, process state spaces, and shape the rewards.
2. [**The Training Pipeline (`src/training/`)**](docs/training.md) - How the PPO model actually learns, the 5-stage curriculum, and our custom callback hooks.
