# ---

**TECHNICAL DESIGN DOCUMENT (TDD)**

**Project:** Decoupled Headless Mass-Swarm AI Simulation

**Architecture Pattern:** Tri-Node Decoupled System (Micro-Core, Macro-Brain, Debug Visualizer)

## **1\. System Architecture Overview**

This document outlines the architecture for a "Headless Simulation" framework designed to handle mass-entity AI (10,000+ units) and complex swarm behaviors. By decoupling the core game logic and machine learning from heavy game engines (Unity/Unreal) during the prototyping phase, the system achieves maximum computational performance, rapid iteration, absolute memory safety, and 100% logic reusability for final production.

The architecture consists of three main pillars:

1. **The Micro-Core (Rust):** Handles deterministic physics, pathfinding, and individual behaviors of tens of thousands of entities via an Entity Component System (ECS).  
2. **The Macro-Brain (Python):** Handles Deep Reinforcement Learning, pattern recognition, and high-level swarm strategy.  
3. **The Debug Visualizer (Web UI):** A lightweight, browser-based dashboard via WebSockets for real-time observation, debugging, and stakeholder demonstration.

## ---

**2\. The Micro-Core: Rust & Bevy ECS**

This layer acts as the absolute "Source of Truth" for the simulation. It runs entirely "headless" (without rendering graphics or windows).

### **2.1. Setup & Configuration**

* **Language:** Rust (Edition 2021\)  
* **Framework:** Bevy Engine  
* **Core Dependencies (Cargo.toml):**  
  Ini, TOML  
  \[dependencies\]  
  bevy \= { version \= "0.13", default-features \= false } \# Headless mode  
  serde \= { version \= "1.0", features \= \["derive"\] }  
  serde\_json \= "1.0"  
  tokio \= { version \= "1.0", features \= \["full", "rt-multi-thread"\] } \# Async networking  
  tokio-tungstenite \= "0.21"                            \# WebSockets for Web UI  
  zeromq \= "0.3"                                        \# IPC for Python Bridge

### **2.2. Specific Techniques**

* **Headless ECS Initialization:** Initialize Bevy using MinimalPlugins instead of DefaultPlugins. Implement a ScheduleRunnerPlugin to enforce a strict fixed timestep (e.g., 60 Ticks Per Second) to ensure deterministic physics, which is crucial for consistent AI training.  
* **Spatial Partitioning:** To prevent $O(N^2)$ performance degradation when 10,000+ entities check for collisions or proximity targets, implement a **Hash Grid** or **Quadtree** system purely in Rust memory.  
* **Vector Flow Fields (Pathfinding):** Standard A\* algorithms will bottleneck CPU performance if thousands of entities calculate individual paths simultaneously. Implement **Dijkstra Maps / Vector Flow Fields**. The core calculates a global directional map, and individual entities simply follow the velocity vector of the grid cell they currently occupy.  
* **C-ABI Export Preparation:** Structure the core logic as a dynamic library (cdylib). Expose functions using \#\[no\_mangle\] pub extern "C" so the final Game Engine can execute the logic natively via FFI (Foreign Function Interface) later on.

## ---

**3\. The Macro-Brain: Python & Machine Learning**

This layer acts as the "Director". It evaluates the global battlefield state and sends high-level directives to the Rust core.

### **3.1. Setup & Configuration**

* **Language:** Python 3.10+  
* **ML Stack:** PyTorch, Ray RLlib, Gymnasium (OpenAI API standard).  
* **Environment Setup:** pip install torch ray\[rllib\] gymnasium pyzmq onnx

### **3.2. Specific Techniques**

* **Custom Gymnasium Environment:** Wrap the ZeroMQ communication with Rust inside a standard gymnasium.Env class. This allows standard Reinforcement Learning algorithms (like PPO) to interact with the Rust simulation seamlessly using standard reset() and step(action) methods.  
* **State Vectorization (Observation Space):** Compress the complex JSON/Binary state received from Rust into flat numerical arrays (tensors) or low-resolution heatmaps (e.g., rat density, player health) for the neural network to process efficiently.  
* **Asynchronous Inference (Tick Decoupling):** The ML model does not need to run at 60 FPS. Rust handles frame-by-frame movement; Python only receives aggregated data and evaluates the board state every $N$ ticks (e.g., twice a second) to issue macro commands (e.g., TRIGGER\_FRENZY, FLANK\_LEFT).  
* **ONNX Exportation (Crucial for Production):** Python is strictly used for training and prototyping. Once the PyTorch model achieves the desired behavior, freeze the weights and export it to the **ONNX (Open Neural Network Exchange)** format.  
  Python  
  import torch  
  \# Export the trained PyTorch model to ONNX format  
  torch.onnx.export(model, dummy\_state\_input, "macro\_brain.onnx")

## ---

**4\. Inter-Process Communication (The Bridges)**

Robust networking protocols are required to bridge the decoupled modules without creating latency bottlenecks.

### **4.1. The AI Bridge (Rust $\\leftrightarrow$ Python)**

* **Protocol:** **ZeroMQ (ZMQ)** over local TCP (localhost).  
* **Pattern:** REQ/REP (Request-Reply).  
* **Workflow:** Rust pauses its simulation loop \-\> Serializes the state \-\> Sends to Python via ZMQ \-\> Python infers the macro-action \-\> Sends action back \-\> Rust applies the command and resumes the simulation.  
* **Data Serialization:** Use JSON for early prototyping readability. As entity counts scale past thousands, swap to binary serialization formats like **Bincode**, **MessagePack**, or **Protobuf** to minimize serialization/deserialization CPU overhead.

### **4.2. The Debug Bridge (Rust $\\leftrightarrow$ Web UI)**

* **Protocol:** **WebSockets**.  
* **Workflow:** Rust spawns a background asynchronous tokio task alongside the Bevy app. It broadcasts real-time telemetry data to connected browser clients without blocking the main ECS loop.

## ---

**5\. Web-Based Debug Visualizer**

A lightweight, zero-installation frontend for Game Designers, QA, and investors to observe and interact with the headless simulation.

### **5.1. Setup & Configuration**

* **Tech Stack:** HTML5 \<canvas\>, Vanilla JavaScript / TypeScript. No heavy frontend frameworks (like React) are necessary.  
* **Hosting:** A static index.html file that connects to ws://localhost:8080.

### **5.2. Specific Techniques**

* **Canvas Rendering Loop:** Do not draw immediately when a WebSocket message arrives. Save the state payload to a buffer and use window.requestAnimationFrame() to clear and redraw the canvas at the monitor's native refresh rate (60Hz) for visual smoothness.  
* **Geometric Abstraction:** Represent complex logic with simple primitives:  
  * ctx.arc(): Red circles for the Swarm, Blue circles for Defenders.  
  * ctx.lineTo(): Lines representing pathfinding intentions or aggro links.  
  * ctx.fillRect(): Semi-transparent grids indicating NavMesh weights or Fog of War.  
* **Delta Syncing (Bandwidth Optimization):** To prevent network bottlenecking, Rust should only broadcast "Delta updates" (entities that moved, spawned, or died) rather than the entire state array every frame.  
* **Bidirectional Control:** Implement HTML UI controls (Buttons, Sliders) that send JSON payloads back to Rust to manipulate the ECS state in real-time (e.g., {"cmd": "spawn\_wave", "amount": 500}).

## ---

**6\. Production Integration Pipeline (The Endgame)**

When the simulation logic is finalized and the AI is fully trained, the prototype tools (Python environment, Web visualizer) are discarded. The transition to the final Game Engine is seamless:

1. **Export Rust to Native C-ABI:** Compile the Rust Bevy core into a dynamic C-library (.dll for Windows, .so for Linux, .dylib for macOS).  
2. **Engine Integration (C\# / C++):** Drop the compiled library into Unity or Unreal. The engine uses FFI (Foreign Function Interface) to call the Rust logic tick-by-tick.  
3. **Python to Native Inference:** Import the exported macro\_brain.onnx AI model directly into Unity (via Unity Sentis) or Unreal (via NNI plugin). The game engine runs the neural network natively on the player's hardware.  
4. **Engine Role:** The commercial engine is now relegated to its optimal purpose: rendering 3D models at the X/Y coordinates provided by the Rust DLL, playing animations, triggering VFX/Audio, and managing user input.
