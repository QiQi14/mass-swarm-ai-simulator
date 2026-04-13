# Micro-Core Engine

Welcome to the **Micro-Core**! If you are a new intern or student joining the Mass-Swarm AI Simulator project, this is the foundational engine you need to understand first.

## What is the Micro-Core?
The `micro-core` is a **high-performance, headless simulation engine** written entirely in [Rust](https://www.rust-lang.org/). It runs the physical laws, movements, combat rules, and pathfinding of the swarm at a native 60 Ticks Per Second (TPS).

It is "headless", meaning it has absolutely no user interface or visual rendering engine attached to it natively. It simply calculates data.

## Why Rust and Bevy? (The Approach)
You might wonder why we didn't use an Object-Oriented language like Python or C# for the simulation rules.

The answer is **Data-Oriented Design (DoD)**.
We use the [Bevy](https://bevyengine.org/) Entity Component System (ECS). In OOP, an "Entity" (like a swarm agent) is an object containing both data and methods in memory. This fragments memory and causes CPU cache misses when iterating over thousands of entities.

In Bevy ECS:
- **Entities** are just integer IDs.
- **Components** are pure data arrays (`Position`, `Velocity`).
- **Systems** are functions that iterate linearly over these arrays.

This structure allows the CPU to pre-fetch memory, giving us the extreme performance needed to simulate 10,000+ interacting swarm units on a single thread.

## Core Keywords for Further Learning
Before diving deep into the code, you should familiarize yourself with these concepts:
- **Rust Traits & Lifetimes**: The bedrock of our safe memory management.
- **Bevy ECS**: How Entities, Components, and Systems interact.
- **ZeroMQ (ZMQ)**: The high-speed messaging protocol we use.
- **WebSockets via Tokio**: Our async bridge to the browser UI.

## Directory Map (Deep Dive)
To avoid an overwhelmingly large document, the technical details of how the micro-core actually works are categorized strictly by their architectural boundary.

Please read through these guides in order to master the system:

1. [**Architecture & Engine Lifecycle**](docs/architecture.md) - How the engine starts, limits its speed, and tracks time.
2. [**Components (Data)**](docs/components.md) - The schemas that make up our Swarm Agents and environment.
3. [**Systems (Logic)**](docs/systems.md) - How we apply the rules of physics, movement, and ML directives.
4. [**Spatial & Pathfinding**](docs/spatial.md) - How 10,000 entities map routes and find their neighbors in `O(1)` time.
5. [**Bridges (IPC)**](docs/bridges.md) - How this headless engine talks to the Python ML Brain and Browser UI.
6. [**Game Rules**](docs/rules.md) - The centralized, parameterizable game mechanics governing factions and combat.
