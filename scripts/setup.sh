#!/bin/bash
# PyTorch Buildings GUI — Environment Setup (macOS / Linux)
# Installs all dependencies from the bundled neuromancer_repo.
# No internet access to GitHub is required for neuromancer.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo " PyTorch Buildings GUI — Environment Setup"
echo "=========================================="
echo ""

# -----------------------------------------------
# Python detection (3.10–3.12 supported)
# -----------------------------------------------
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3.10 or newer is required but was not found."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"
echo ""

# -----------------------------------------------
# Virtual environment
# -----------------------------------------------
cd "$ROOT"
echo "Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo "✓ Created .venv"
else
    echo "✓ Using existing .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
echo ""

# -----------------------------------------------
# PyTorch (CPU build — works on all machines)
# GPU users: replace with the appropriate index URL
# from https://pytorch.org/get-started/locally/
# -----------------------------------------------
echo "Installing PyTorch stack..."
pip install torch torchvision torchaudio -q
echo "✓ PyTorch installed"
echo ""

# -----------------------------------------------
# GUI + scientific dependencies
# -----------------------------------------------
echo "Installing GUI and scientific dependencies..."
pip install \
    PyQt6>=6.5.0 \
    numpy \
    scipy \
    matplotlib \
    tqdm \
    -q
echo "✓ Core dependencies installed"
echo ""

# -----------------------------------------------
# NeuroMANCER — bundled local copy (no clone needed)
# -----------------------------------------------
echo "Installing bundled NeuroMANCER..."
pip install \
    torchdiffeq \
    "networkx>=3,<4" \
    "pydot==1.4.2" \
    "plum-dispatch==1.7.3" \
    "lightning>=2.0.0" \
    -q
pip install -e "$ROOT/neuromancer_repo" -q
echo "✓ NeuroMANCER installed from neuromancer_repo/"
echo ""

# -----------------------------------------------
# Verification
# -----------------------------------------------
echo "Verifying environment..."
python - <<'PYEOF'
import sys

def check(name, fn):
    try:
        v = fn()
        print(f"  ✓ {name}: {v}")
    except Exception as exc:
        print(f"  ✗ {name}: {exc}")
        sys.exit(1)

check("Python",       lambda: sys.version.split()[0])
check("torch",        lambda: __import__("torch").__version__)
check("torchdiffeq",  lambda: __import__("torchdiffeq").__version__)
check("numpy",        lambda: __import__("numpy").__version__)
check("matplotlib",   lambda: __import__("matplotlib").__version__)
check("PyQt6",        lambda: __import__("PyQt6.QtCore", fromlist=["PYQT_VERSION_STR"]).PYQT_VERSION_STR)
check("neuromancer",  lambda: __import__("neuromancer").__version__)

# Confirm the HVAC components are importable
from neuromancer.hvac.building_components import Envelope, RTU, VAVBox, SolarGains
print("  ✓ HVAC components importable")

print("\nAll checks passed — environment is ready.")
PYEOF

echo ""
echo "=========================================="
echo " Setup complete"
echo "=========================================="
echo ""
echo "Activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "Run the application:"
echo "  python src/main.py"
echo ""
