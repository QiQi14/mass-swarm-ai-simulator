#!/usr/bin/env bash
# ============================================================================
# Mass-Swarm AI Simulator — Development Environment Launcher
# ============================================================================
#
# Starts all required services for debugging:
#   1. Rust Micro-Core (simulation engine + WS server on :8080)
#   2. Vite dev server for Debug Visualizer (on :5173)
#
# Usage:
#   ./dev.sh              — Normal dev mode
#   ./dev.sh --watch      — Visualizer only (no Rust core, safe during training)
#   ./dev.sh --training   — Alias for --watch (training monitor mode)
#   ./dev.sh --smoke      — Run 300-tick smoke test then exit
#   ./dev.sh --release    — Build and run with release optimizations
#   ./dev.sh --prod       — Production build (no debug telemetry)
#   ./dev.sh --clean      — Kill leftover processes and exit
#   ./dev.sh --help       — Show this help
# ============================================================================

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Configuration ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MICRO_CORE_DIR="$SCRIPT_DIR/micro-core"
VISUALIZER_DIR="$SCRIPT_DIR/debug-visualizer"
HTTP_PORT=5173
WS_PORT=8080
PID_FILE="$SCRIPT_DIR/.dev.pids"
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "your-local-ip")

# ── Port Cleanup Function ──────────────────────────────────────────────
# Kills any process occupying the given port.
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "  ${YELLOW}⚠  Port $port in use — killing PID(s): $pids${RESET}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.3
    fi
}

# Kill processes from a previous dev.sh run (PID file)
kill_saved_pids() {
    if [ -f "$PID_FILE" ]; then
        while IFS= read -r pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
}

# ── Parse Arguments ─────────────────────────────────────────────────────
CARGO_PROFILE=""
CARGO_EXTRA_ARGS=""
FEATURES=""
SMOKE_TEST=false
WATCH_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --watch|--passive|--training)
            WATCH_ONLY=true
            ;;
        --smoke)
            SMOKE_TEST=true
            CARGO_EXTRA_ARGS="$CARGO_EXTRA_ARGS --smoke-test"
            ;;
        --release)
            CARGO_PROFILE="--release"
            ;;
        --prod|--production)
            CARGO_PROFILE="--release"
            FEATURES="--no-default-features"
            ;;
        --clean)
            echo -e "${YELLOW}▸ Cleaning up leftover processes...${RESET}"
            kill_saved_pids
            kill_port "$HTTP_PORT"
            kill_port "$WS_PORT"
            echo -e "${GREEN}✔ All ports freed.${RESET}"
            exit 0
            ;;
        --help|-h)
            head -n 18 "$0" | tail -n 15
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${RESET}"
            exit 1
            ;;
    esac
done

# ── Cleanup on Exit ────────────────────────────────────────────────────
# Trapping SIGHUP is critical — that's what the terminal sends on close.
CORE_PID=""
HTTP_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}⏹  Shutting down...${RESET}"
    
    if [ -n "$CORE_PID" ] && kill -0 "$CORE_PID" 2>/dev/null; then
        kill "$CORE_PID" 2>/dev/null || true
        wait "$CORE_PID" 2>/dev/null || true
        echo -e "   ${DIM}Micro-Core stopped${RESET}"
    fi
    
    if [ -n "$HTTP_PID" ] && kill -0 "$HTTP_PID" 2>/dev/null; then
        kill "$HTTP_PID" 2>/dev/null || true
        wait "$HTTP_PID" 2>/dev/null || true
        echo -e "   ${DIM}Vite dev server stopped${RESET}"
    fi
    
    # Only kill ports that THIS script owns
    lsof -ti:"$HTTP_PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
    # Only kill WS port if we started the Rust core (NOT in watch mode)
    if [ "$WATCH_ONLY" != true ] && [ -n "$CORE_PID" ]; then
        lsof -ti:"$WS_PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    echo -e "${GREEN}✔  All services stopped.${RESET}"
}

trap cleanup EXIT INT TERM HUP

# ── Banner ──────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║     Mass-Swarm AI Simulator — Dev Environment    ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Watch-Only Mode ────────────────────────────────────────────────────
if [ "$WATCH_ONLY" = true ]; then
    kill_port "$HTTP_PORT"

    # Ensure npm dependencies are installed
    if [ ! -d "$VISUALIZER_DIR/node_modules" ]; then
        echo -e "${YELLOW}▸ Installing visualizer dependencies...${RESET}"
        (cd "$VISUALIZER_DIR" && npm install --silent)
    fi

    echo -e "${YELLOW}▸ Starting Vite dev server on port $HTTP_PORT...${RESET}"
    (cd "$VISUALIZER_DIR" && npx vite --port "$HTTP_PORT" --host 0.0.0.0) &
    HTTP_PID=$!
    echo "$HTTP_PID" > "$PID_FILE"

    sleep 2
    if ! kill -0 "$HTTP_PID" 2>/dev/null; then
        echo -e "${RED}✘ Failed to start Vite dev server on port $HTTP_PORT.${RESET}"
        exit 1
    fi

    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo -e "${GREEN}${BOLD}  👁  Watch mode — Visualizer only${RESET}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "  ${BOLD}Local Access:${RESET}      ${CYAN}http://127.0.0.1:$HTTP_PORT${RESET}"
    echo -e "  ${BOLD}Network Access:${RESET}    ${CYAN}http://$LOCAL_IP:$HTTP_PORT${RESET}"
    echo -e "  ${BOLD}Modes:${RESET}             ${YELLOW}#training (monitor) · #playground (debug)${RESET}"
    echo -e "  ${DIM}Rust core and training must be started separately.${RESET}"
    echo -e "  ${DIM}Training logs served from: public/logs/run_latest/${RESET}"
    echo ""
    echo -e "  ${DIM}Press Ctrl+C to stop the visualizer.${RESET}"
    echo ""

    wait "$HTTP_PID" 2>/dev/null || true
    exit 0
fi

# ── Step 0: Kill leftovers from previous runs ──────────────────────────
kill_saved_pids
kill_port "$HTTP_PORT"
kill_port "$WS_PORT"

# ── Step 1: Build Micro-Core ───────────────────────────────────────────
echo -e "${YELLOW}▸ Building Micro-Core...${RESET}"

BUILD_CMD="cargo build $CARGO_PROFILE $FEATURES"
echo -e "  ${DIM}$ cd micro-core && $BUILD_CMD${RESET}"

if ! (cd "$MICRO_CORE_DIR" && eval "$BUILD_CMD" 2>&1); then
    echo -e "${RED}✘ Build failed. Fix compilation errors and retry.${RESET}"
    exit 1
fi
echo -e "${GREEN}✔ Build succeeded${RESET}"
echo ""

# ── Step 2: Start Vite Dev Server for Visualizer ──────────────────────
if [ "$SMOKE_TEST" = false ]; then
    # Ensure npm dependencies are installed
    if [ ! -d "$VISUALIZER_DIR/node_modules" ]; then
        echo -e "${YELLOW}▸ Installing visualizer dependencies...${RESET}"
        (cd "$VISUALIZER_DIR" && npm install --silent)
    fi

    echo -e "${YELLOW}▸ Starting Vite dev server on port $HTTP_PORT...${RESET}"
    (cd "$VISUALIZER_DIR" && npx vite --port "$HTTP_PORT" --host 0.0.0.0) &
    HTTP_PID=$!
    
    # Save PID for cross-session cleanup
    echo "$HTTP_PID" > "$PID_FILE"
    
    # Verify the dev server started
    sleep 2
    if ! kill -0 "$HTTP_PID" 2>/dev/null; then
        echo -e "${RED}✘ Failed to start Vite dev server on port $HTTP_PORT.${RESET}"
        echo -e "  ${DIM}Run: ./dev.sh --clean${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✔ Visualizer serving at http://127.0.0.1:$HTTP_PORT (Network: http://$LOCAL_IP:$HTTP_PORT)${RESET}"
    echo ""
fi

# ── Step 3: Start Micro-Core ───────────────────────────────────────────
echo -e "${YELLOW}▸ Starting Micro-Core simulation...${RESET}"

RUN_CMD="cargo run $CARGO_PROFILE $FEATURES"
if [ -n "$CARGO_EXTRA_ARGS" ]; then
    RUN_CMD="$RUN_CMD -- $CARGO_EXTRA_ARGS"
fi
echo -e "  ${DIM}$ cd micro-core && $RUN_CMD${RESET}"
echo ""

if [ "$SMOKE_TEST" = true ]; then
    # Foreground — run and exit
    (cd "$MICRO_CORE_DIR" && eval "$RUN_CMD")
    echo ""
    echo -e "${GREEN}✔ Smoke test complete.${RESET}"
else
    # Run in foreground directly (not subshell) — keeps it attached to terminal
    cd "$MICRO_CORE_DIR"

    eval "$RUN_CMD" &
    CORE_PID=$!
    
    # Save both PIDs for cross-session cleanup
    echo "$CORE_PID" >> "$PID_FILE"
    
    sleep 1
    if ! kill -0 "$CORE_PID" 2>/dev/null; then
        echo -e "${RED}✘ Micro-Core failed to start. Check errors above.${RESET}"
        exit 1
    fi
    
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo -e "${GREEN}${BOLD}  🚀 All services running!${RESET}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════${RESET}"
    echo ""
    echo -e "  ${BOLD}Local Access:${RESET}      ${CYAN}http://127.0.0.1:$HTTP_PORT${RESET}"
    echo -e "  ${BOLD}Network Access:${RESET}    ${CYAN}http://$LOCAL_IP:$HTTP_PORT${RESET}"
    echo -e "  ${BOLD}WebSocket Server:${RESET}  ${CYAN}ws://0.0.0.0:$WS_PORT${RESET}"
    echo -e "  ${BOLD}Modes:${RESET}             ${YELLOW}#training · #playground${RESET}"
    echo -e "  ${BOLD}Rust Logs:${RESET}         ${DIM}(streaming below)${RESET}"
    echo ""
    echo -e "  ${DIM}Press Ctrl+C to stop all services.${RESET}"
    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────${RESET}"
    
    # Wait for Core process — keeps script alive and logs streaming
    wait "$CORE_PID" 2>/dev/null || true
fi
