#!/usr/bin/env bash
# ============================================================================
# dispatch.sh — Self-contained wrapper for the Multi-Agent Dispatch CLI
# ============================================================================
#
# This script ensures a Python virtual environment exists, activates it,
# and delegates all arguments to dispatch.py.
#
# Usage:
#   ./dispatch.sh agents
#   ./dispatch.sh tasks
#   ./dispatch.sh ready
#   ./dispatch.sh prompt executor task_01_auth_repo
#   ./dispatch.sh session qa task_01_auth_repo
#   ./dispatch.sh batch
#
# The venv is created at .venv_dispatch/ next to this script.
# Since dispatch.py uses only the Python standard library, no pip
# install step is needed.
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve paths (works even if called from a different directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv_dispatch"
PYTHON_SCRIPT="${SCRIPT_DIR}/dispatch.py"
REQUIRED_PYTHON_VERSION="3"

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
RED='\033[0;91m'
GREEN='\033[0;92m'
YELLOW='\033[0;93m'
CYAN='\033[0;96m'
BOLD='\033[1m'
RESET='\033[0m'

if [[ ! -t 1 ]]; then
    RED="" GREEN="" YELLOW="" CYAN="" BOLD="" RESET=""
fi

_info()  { echo -e "${CYAN}[dispatch]${RESET} $*"; }
_ok()    { echo -e "${GREEN}[dispatch]${RESET} $*"; }
_warn()  { echo -e "${YELLOW}[dispatch]${RESET} $*"; }
_error() { echo -e "${RED}[dispatch]${RESET} $*" >&2; }

# ---------------------------------------------------------------------------
# Step 1: Locate a suitable Python 3 interpreter
# ---------------------------------------------------------------------------
find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local ver
            ver="$("$candidate" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo "")"
            if [[ "$ver" == "$REQUIRED_PYTHON_VERSION" ]]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(find_python)" || {
    _error "Python ${REQUIRED_PYTHON_VERSION} not found on PATH."
    _error "Install Python ${REQUIRED_PYTHON_VERSION} and try again."
    exit 1
}

# ---------------------------------------------------------------------------
# Step 2: Create virtual environment if it doesn't exist
# ---------------------------------------------------------------------------
if [[ ! -d "${VENV_DIR}" ]]; then
    _info "Creating virtual environment at ${BOLD}.venv_dispatch/${RESET} ..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    _ok "Virtual environment created."
fi

# ---------------------------------------------------------------------------
# Step 3: Activate the venv
# ---------------------------------------------------------------------------
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# ---------------------------------------------------------------------------
# Step 4: Verify dispatch.py exists
# ---------------------------------------------------------------------------
if [[ ! -f "${PYTHON_SCRIPT}" ]]; then
    _error "dispatch.py not found at: ${PYTHON_SCRIPT}"
    _error "Ensure dispatch.py is in the same directory as this script."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 5: Delegate to the Python script with all arguments
# ---------------------------------------------------------------------------
python "${PYTHON_SCRIPT}" "$@"
