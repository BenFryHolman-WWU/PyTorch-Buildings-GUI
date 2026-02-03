#!/bin/bash

# PyTorch Buildings GUI - Environment Setup
# Safe version: does NOT create or modify repo files
# Only touches:
#   - .venv/
#   - neuromancer_repo/   (optional reference clone)

set -e

echo "=========================================="
echo "PyTorch Buildings GUI - Environment Setup"
echo "=========================================="
echo ""

# -----------------------------
# Python detection
# -----------------------------
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3.12 is not installed"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" != "12" ]; then
    echo "Error: Python 3.12.x required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"
echo ""

# -----------------------------
# Virtual environment
# -----------------------------
echo "Setting up virtual environment..."

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo "✓ Created .venv"
else
    echo "✓ Using existing .venv"
fi

echo ""

source .venv/bin/activate
pip install --upgrade pip -q

# -----------------------------
# PyTorch stack (CPU-safe)
# -----------------------------
echo "Installing PyTorch stack..."
pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true
pip install torch torchvision torchaudio -q
echo "✓ PyTorch installed"
echo ""

# -----------------------------
# Core dependencies
# -----------------------------
echo "Installing core dependencies..."
pip install \
    PyQt6 \
    numpy \
    scipy \
    pandas \
    matplotlib \
    tqdm \
    pyyaml \
    torchdiffeq \
    beartype \
    -q
echo "✓ Core dependencies installed"
echo ""

# -----------------------------
# NeuroMANCER
# -----------------------------
echo "Installing NeuroMANCER (HVAC branch)..."
pip install git+https://github.com/pnnl/neuromancer.git@hvac -q
echo "✓ NeuroMANCER installed"
echo ""

# -----------------------------
# Optional reference clone
# -----------------------------
if [ ! -d "neuromancer_repo" ]; then
    echo "Cloning neuromancer_repo (reference only)..."
    git clone -b hvac https://github.com/pnnl/neuromancer.git neuromancer_repo -q
    echo "✓ neuromancer_repo created"
else
    echo "✓ neuromancer_repo already exists"
fi

echo ""

# -----------------------------
# Verification
# -----------------------------
echo "Verifying environment..."
python << 'PYEOF'
import sys

def check(name, fn):
    try:
        v = fn()
        print(f"  ✓ {name}: {v}")
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        sys.exit(1)

check("torch", lambda: __import__("torch").__version__)
check("torchvision", lambda: __import__("torchvision").__version__)
check("torchdiffeq", lambda: __import__("torchdiffeq").__version__)
check("numpy", lambda: __import__("numpy").__version__)
check("matplotlib", lambda: __import__("matplotlib").__version__)

from PyQt6 import QtCore
check("PyQt6", lambda: QtCore.PYQT_VERSION_STR)

check("neuromancer", lambda: __import__("neuromancer").__version__)

# torchvision API sanity check
from torchvision.models import VGG16_Weights
print("  ✓ torchvision VGG16_Weights available")

print("\nEnvironment verified successfully!")
PYEOF


echo ""
echo "=========================================="
echo "✓ Environment Ready"
echo "=========================================="
echo ""
echo "Activate with:"
echo "  source .venv/bin/activate"
echo ""
echo "Run app:"
echo "  python src/main.py"
echo ""
