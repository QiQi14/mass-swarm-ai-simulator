#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Build micro-core for WebAssembly target
# Output goes to debug-visualizer/public/wasm/ for Vite to serve
# ═══════════════════════════════════════════════════════════════

set -e

echo "🔨 Building micro-core for wasm32-unknown-unknown..."
cd micro-core

# Build with wasm feature, no default features (excludes native/tokio/zmq)
cargo build \
    --target wasm32-unknown-unknown \
    --features wasm \
    --no-default-features \
    --release

echo "📦 Running wasm-bindgen..."
wasm-bindgen \
    target/wasm32-unknown-unknown/release/micro_core.wasm \
    --out-dir ../debug-visualizer/public/wasm \
    --target web \
    --no-typescript

echo "✅ WASM build complete!"
echo "   Output: debug-visualizer/public/wasm/"
ls -la ../debug-visualizer/public/wasm/
