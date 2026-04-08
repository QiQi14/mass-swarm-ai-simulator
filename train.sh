#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# Mass-Swarm AI Simulator — Training Launch Script
#
# Starts three components in order:
#   1. Debug Visualizer (opens browser)
#   2. Rust Micro-Core (background)
#   3. Python ML Training (foreground)
#
# Speed Modes:
#   Default:        Normal 60 TPS (human-observable via browser)
#   --slow-train:   Max TPS (training speed, no frame sleep)
#
# Usage:
#   ./train.sh                             # normal speed, opens browser
#   ./train.sh --no-visualizer             # normal speed, headless
#   ./train.sh --slow-train --timesteps 1000000  # fast training
#   ./train.sh --profile profiles/custom.json
#
# Ctrl+C stops training and kills all background processes.
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="profiles/stage1_tactical.json"
TIMESTEPS=100000
OPEN_VIZ=true
TRAINING_MODE=false    # false = 60 TPS, true = max TPS
EXTRA_ARGS=""

# Parse known flags, forward unknown to Python
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --timesteps) TIMESTEPS="$2"; shift 2 ;;
        --no-visualizer) OPEN_VIZ=false; shift ;;
        --slow-train) TRAINING_MODE=true; shift ;;
        *) EXTRA_ARGS+=" $1"; shift ;;
    esac
done

RUST_PID=""
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [[ -n "$RUST_PID" ]]; then
        pkill -P "$RUST_PID" 2>/dev/null || true
        kill -9 "$RUST_PID" 2>/dev/null || true
        killall -9 micro-core 2>/dev/null || true
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

# Determine Rust flags based on speed mode
# Always pass --training (required: sets SimPaused=false so ZMQ-driven simulation works)
# Add --throttle for 60 TPS human-observable speed (default)
# --slow-train omits --throttle for maximum TPS
RUST_FLAGS="--training"
if ! $TRAINING_MODE; then
    RUST_FLAGS="--training --throttle"
    echo "🦀 Starting Rust Micro-Core (NORMAL SPEED — 60 TPS)..."
else
    echo "🦀 Starting Rust Micro-Core (TRAINING SPEED — max TPS)..."
fi

(cd "$SCRIPT_DIR/micro-core" && cargo run --release -- $RUST_FLAGS 2>&1 | sed 's/^/   [rust] /') &
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
SPEED_LABEL="NORMAL (60 TPS)"
if $TRAINING_MODE; then
    SPEED_LABEL="FAST (max TPS)"
fi

echo "🧠 Starting ML Training..."
echo "   Profile:   $PROFILE"
echo "   Timesteps: $TIMESTEPS"
echo "   Speed:     $SPEED_LABEL"
echo ""
cd "$SCRIPT_DIR/macro-brain"
source venv/bin/activate 2>/dev/null || true
python -m src.training.train \
    --profile "$PROFILE" \
    --timesteps "$TIMESTEPS" \
    $EXTRA_ARGS
