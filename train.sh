#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# Mass-Swarm AI Simulator — Training Launch Script
#
# Starts three components in order:
#   1. Debug Visualizer (opens browser)
#   2. Rust Micro-Core (background, waits for ZMQ ready)
#   3. Python ML Training (foreground)
#
# Usage:
#   ./train.sh
#   ./train.sh --profile profiles/custom.json --timesteps 500000
#   ./train.sh --no-visualizer  # skip opening browser
#
# Ctrl+C stops training and kills all background processes.
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="profiles/default_swarm_combat.json"
TIMESTEPS=100000
OPEN_VIZ=true
EXTRA_ARGS=""

# Parse known flags, forward unknown to Python
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --timesteps) TIMESTEPS="$2"; shift 2 ;;
        --no-visualizer) OPEN_VIZ=false; shift ;;
        *) EXTRA_ARGS+=" $1"; shift ;;
    esac
done

RUST_PID=""
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [[ -n "$RUST_PID" ]]; then
        kill "$RUST_PID" 2>/dev/null || true
        wait "$RUST_PID" 2>/dev/null || true
        echo "   Rust Micro-Core stopped"
    fi
    echo "   Done."
}
trap cleanup EXIT INT TERM

# 1. Open Debug Visualizer
if $OPEN_VIZ; then
    echo "🌐 Opening Debug Visualizer..."
    open "$SCRIPT_DIR/debug-visualizer/index.html" 2>/dev/null || \
    xdg-open "$SCRIPT_DIR/debug-visualizer/index.html" 2>/dev/null || \
    echo "   (Could not auto-open browser — open debug-visualizer/index.html manually)"
fi

# 2. Build and start Rust Micro-Core
echo "⚙️  Building Rust Micro-Core..."
(cd "$SCRIPT_DIR/micro-core" && cargo build --release 2>&1)
echo "🦀 Starting Rust Micro-Core (background)..."
(cd "$SCRIPT_DIR/micro-core" && cargo run --release 2>&1 | sed 's/^/   [rust] /') &
RUST_PID=$!

# Wait for Micro-Core WS port to be ready
echo "⏳ Waiting for WebSocket port 8080..."
for i in $(seq 1 10); do
    if lsof -i :8080 >/dev/null 2>&1; then
        echo "   ✅ WebSocket ready"
        break
    fi
    sleep 1
done

# 3. Start Python training
echo "🧠 Starting ML Training..."
echo "   Profile:   $PROFILE"
echo "   Timesteps: $TIMESTEPS"
echo ""
cd "$SCRIPT_DIR/macro-brain"
source venv/bin/activate 2>/dev/null || true
python -m src.training.train \
    --profile "$PROFILE" \
    --timesteps "$TIMESTEPS" \
    $EXTRA_ARGS
