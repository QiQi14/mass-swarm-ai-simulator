# Infrastructure

## Development

### Micro-Core (Rust)
- **Build:** `cd micro-core && cargo build`
- **Run:** `cd micro-core && cargo run` (starts headless simulation at 60 TPS)
- **Test:** `cd micro-core && cargo test`
- **Lint:** `cd micro-core && cargo clippy`
- **Format:** `cd micro-core && cargo fmt`

### Macro-Brain (Python)
- **Setup:** `cd macro-brain && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- **Run:** `cd macro-brain && python3 -m src.training.train`
- **Test:** `cd macro-brain && pytest`
- **Lint:** `cd macro-brain && ruff check .`
- **Format:** `cd macro-brain && black .`

### Debug Visualizer (Web)
- **Run:** Open `debug-visualizer/index.html` in a browser (no build step)
- **Prerequisite:** Micro-Core must be running with WS bridge on `ws://localhost:8080`

## Build & Deploy

### Prototype Phase (Current)
- No unified build system — each node builds independently
- No deployment target — all runs locally on `localhost`

### Web Engine Integration Phase (Phase 5)
- **Rust → WASM:** `cd micro-core && wasm-pack build --target web` → `pkg/` with `.wasm` + JS bindings
- **Rust → C-ABI (reference):** `cd micro-core && cargo build --release --lib` → `.dylib` / `.so` / `.dll`
- **C headers:** `cbindgen --crate micro-core --output micro_core.h`
- **Python → ONNX:** `torch.onnx.export(model, ...)` → `macro_brain.onnx`
- **Engine Integration Demo:** `cd engine-integration && npm install && npm run dev`
- **Future paths (documented, not built):** Unity (Sentis + P/Invoke), Unreal (NNI + C++ FFI)

## Environment Variables
<!-- None defined for prototype phase — all config is in-code or CLI args -->
- **ZMQ Port:** `tcp://localhost:5555` (Rust ↔ Python, hardcoded for prototype)
- **WS Port:** `ws://localhost:8080` (Rust ↔ Web UI, hardcoded for prototype)

## CI/CD
<!-- Not yet configured — define when moving to multi-developer workflow -->
<!-- Future pipeline: -->
<!-- PR → cargo clippy + cargo test → pytest → Merge -->

## Multi-Node Startup Order
1. **Start Micro-Core** first (it hosts both ZMQ and WS servers)
2. **Start Macro-Brain** second (it connects to Rust's ZMQ socket as a client)
3. **Open Debug Visualizer** last (it connects to Rust's WS endpoint)

> [!IMPORTANT]
> The Micro-Core must be running before either client node can connect. There is no retry/reconnect logic in the prototype phase.

