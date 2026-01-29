#!/bin/bash

# PyTorch Buildings GUI - Setup Script
# Installs NeuroMANCER HVAC branch and PyQt6
# Fixes torch/torchvision compatibility automatically

set -e

echo "=========================================="
echo "PyTorch Buildings GUI - Setup"
echo "NeuroMANCER HVAC Branch"
echo "=========================================="
echo ""

# Check for Python 3.12
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3.12 is not installed"
    exit 1
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" != "12" ]; then
    echo "Error: Python 3.12.x required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"
echo ""

# Create directory structure
echo "Creating project structure..."
mkdir -p src/{gui,models,utils}
mkdir -p data/samples models scripts tests assets
echo "✓ Directories created"
echo ""

# Create .gitignore
echo "Creating .gitignore..."
cat > .gitignore << 'EOF'
# Virtual Environment
.venv/
venv/
env/

# Python
*.pyc
__pycache__/
*.so
*.egg-info/
dist/
build/

# PyTorch & NeuroMANCER
*.pth
*.pt
*.ckpt
wandb/

# NeuroMANCER repo (local reference only)
neuromancer_repo/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
*.log

# Data
data/raw/
data/processed/
data/*.zip
!data/samples/

# Models
models/*.pth
models/*.pt

# Outputs
outputs/
experiments/
checkpoints/
EOF
echo "✓ .gitignore created"
echo ""

# Create requirements.txt
echo "Creating requirements.txt..."
cat > requirements.txt << 'EOF'
# GUI
PyQt6>=6.5.0

# Scientific
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0

# Visualization
matplotlib>=3.7.0

# Utilities
tqdm>=4.65.0
pyyaml>=6.0
EOF
echo "✓ requirements.txt created"
echo ""

# Create Python package files
echo "Creating Python package structure..."
touch src/__init__.py src/gui/__init__.py src/models/__init__.py src/utils/__init__.py tests/__init__.py
echo "✓ Python packages created"
echo ""

# Create/update virtual environment
echo "Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi
echo ""

# Activate and install dependencies
echo "Installing dependencies..."
source .venv/bin/activate

pip install --upgrade pip -q

echo "  Installing PyTorch (CPU, compatible build)..."
pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true
pip install torch torchvision torchaudio -q

echo "  Installing PyQt6..."
pip install PyQt6 -q

echo "  Installing NeuroMANCER (HVAC branch)..."
pip install git+https://github.com/pnnl/neuromancer.git@hvac -q

echo "  Installing other dependencies..."
pip install -r requirements.txt -q

echo "✓ Dependencies installed"
echo ""

# Clone NeuroMANCER for reference (not in Git)
echo "Cloning NeuroMANCER HVAC branch for reference..."
if [ ! -d "neuromancer_repo" ]; then
    git clone -b hvac https://github.com/pnnl/neuromancer.git neuromancer_repo -q
    echo "✓ NeuroMANCER cloned to neuromancer_repo/ (local only)"
else
    echo "✓ neuromancer_repo/ exists"
fi
echo ""

# Test installations and verify torchvision compatibility
echo "Verifying installations..."
python << 'PYEOF'
import sys

# Test PyTorch
try:
    import torch
    print(f"  ✓ PyTorch {torch.__version__}")
except Exception as e:
    print("  ✗ PyTorch failed:", e)
    sys.exit(1)

# Test torchvision weight API
try:
    from torchvision.models import VGG16_Weights
    print("  ✓ torchvision VGG16_Weights available")
except Exception as e:
    print("  ✗ torchvision mismatch:", e)
    print("    → torch / torchvision versions are incompatible")
    sys.exit(1)

# Test NeuroMANCER
try:
    import neuromancer as nm
    print(f"  ✓ NeuroMANCER {nm.__version__}")
except Exception as e:
    print("  ✗ NeuroMANCER failed:", e)
    sys.exit(1)

# Test PyQt6
try:
    from PyQt6 import QtCore
    print(f"  ✓ PyQt6 {QtCore.PYQT_VERSION_STR}")
except Exception as e:
    print("  ✗ PyQt6 failed:", e)
    sys.exit(1)

print("")
print("All dependencies verified successfully!")
PYEOF

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate environment: source .venv/bin/activate"
echo "  2. Run GUI: python src/main.py"
echo ""
echo "HVAC examples: neuromancer_repo/examples/building_systems/"
echo ""
