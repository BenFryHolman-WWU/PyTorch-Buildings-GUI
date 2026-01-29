#!/bin/bash

# PyTorch Buildings GUI - Setup with NeuroMANCER (No Large Files in Git)
# This installs NeuroMANCER directly but keeps it OUT of your Git repo

set -e  # Exit on error

echo "=========================================="
echo "PyTorch Buildings GUI Setup"
echo "NeuroMANCER HVAC Integration"
echo "(Large files excluded from Git)"
echo "=========================================="
echo ""

# Check for Python 3.12
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3.12 is not installed"
    echo "Please install Python 3.12: https://www.python.org/downloads/"
    exit 1
fi

# Verify Python version is 3.12.x
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" != "12" ]; then
    echo "Error: Python 3.12.x is required, but found Python $PYTHON_VERSION"
    echo "Please install Python 3.12: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Step 1: Create project structure
echo "Step 1: Creating project directory structure..."
mkdir -p src/gui
mkdir -p src/models
mkdir -p src/utils
mkdir -p data/samples
mkdir -p models
mkdir -p scripts
mkdir -p tests
mkdir -p assets
mkdir -p docs
mkdir -p neuromancer_examples  # Local copy of HVAC examples only

echo "✓ Directory structure created"
echo ""

# Step 2: Create .gitignore
echo "Step 2: Creating .gitignore..."
cat > .gitignore << 'GITIGNORE'
# Virtual Environment
.venv/
venv/
env/
ENV/

# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# PyTorch & NeuroMANCER
*.pth
*.pt
*.ckpt
wandb/
lightning_logs/

# NeuroMANCER local clone (NOT in Git)
neuromancer_repo/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
*.log

# Jupyter Notebooks
.ipynb_checkpoints/
*.ipynb

# Data
data/raw/
data/processed/
data/*.zip
data/*.tar.gz
!data/samples/

# Model weights
models/*.pth
models/*.pt
!models/.gitkeep

# Environment variables
.env

# Coverage reports
htmlcov/
.coverage
.pytest_cache/

# Outputs
outputs/
experiments/
checkpoints/
results/
GITIGNORE

echo "✓ .gitignore created"
echo ""

# Step 3: Create README
echo "Step 3: Creating README.md..."
cat > README.md << 'README'
# PyTorch Buildings GUI

A GUI application for building HVAC control using PNNL's NeuroMANCER library.

## Overview

This project uses NeuroMANCER for building control but does NOT include the full NeuroMANCER repository to avoid Git size limits. Instead:
- NeuroMANCER is installed via pip from Git
- HVAC example code is copied to `neuromancer_examples/` (tracked in Git)
- Full NeuroMANCER repo is cloned locally to `neuromancer_repo/` (NOT in Git)

## Requirements

- **Python 3.12.x** (required)
- Git
- CUDA-compatible GPU (recommended)

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git
cd PyTorch-Buildings-GUI

# Run setup script
chmod +x setup.sh
./setup.sh
```

This will:
- Create virtual environment
- Install NeuroMANCER directly from GitHub
- Clone NeuroMANCER repo locally for reference (not in your Git)
- Copy HVAC examples to your project
- Install all dependencies

### 2. Run the Application

```bash
source .venv/bin/activate
python src/main.py
```

## Project Structure

```
PyTorch-Buildings-GUI/
├── README.md
├── requirements.txt
├── src/
│   ├── main.py              # GUI entry point
│   ├── gui/                 # Your GUI code
│   ├── models/              # Your models using NeuroMANCER
│   └── utils/
├── neuromancer_examples/    # HVAC examples (in Git)
│   ├── hvac_safe_dpc.py    # Copied from NeuroMANCER
│   ├── building_dynamics.ipynb
│   └── README.md           # Reference to original files
├── neuromancer_repo/        # Full NeuroMANCER clone (NOT in Git)
│   └── (Clone of pnnl/neuromancer for reference)
├── data/
├── models/
└── .venv/                   # Virtual environment (NOT in Git)
```

## NeuroMANCER Access

### Installation
NeuroMANCER is installed directly from GitHub:
```bash
pip install git+https://github.com/pnnl/neuromancer.git
```

### Using in Code
```python
import neuromancer as nm
from neuromancer.blocks import MLP
from neuromancer.system import Node

# Full access to all NeuroMANCER features
```

### HVAC Examples
HVAC control examples are available in two places:

1. **In your project** (tracked in Git):
   - `neuromancer_examples/` - Key HVAC examples copied here
   - Safe to commit, reference, and modify

2. **Local reference** (NOT in Git):
   - `neuromancer_repo/` - Full NeuroMANCER clone
   - Use for exploring all examples
   - Not committed to avoid large files

### Updating NeuroMANCER

To get the latest version:

```bash
# Update pip installation
source .venv/bin/activate
pip install --upgrade git+https://github.com/pnnl/neuromancer.git

# Update local reference clone
cd neuromancer_repo
git pull origin master
cd ..

# Copy any new HVAC examples you want to track
cp neuromancer_repo/examples/building_systems/new_example.py neuromancer_examples/
git add neuromancer_examples/
git commit -m "Add new HVAC example"
```

## Development Workflow

### 1. Study HVAC Examples
```bash
# Look at examples in your project
cd neuromancer_examples

# Or explore full examples
cd neuromancer_repo/examples/building_systems
jupyter notebook building_dynamics_tutorial.ipynb
```

### 2. Adapt for Your GUI
```python
# src/models/hvac_controller.py
import neuromancer as nm

# Adapt HVAC examples from neuromancer_examples/
# Build your control logic
```

### 3. Build GUI Interface
```python
# src/gui/control_panel.py
# Create Qt widgets for HVAC control
```

### 4. Commit Your Work
```bash
# Only your code and copied examples go to Git
git add src/ neuromancer_examples/
git commit -m "Add HVAC control GUI"
git push
```

## For Collaborators

When someone clones your project:

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git
cd PyTorch-Buildings-GUI
./setup.sh  # Installs NeuroMANCER and clones reference repo
```

They get:
- Your GUI code
- HVAC examples you've copied
- NeuroMANCER installed from GitHub
- Local reference clone created (not from your Git)

## Why This Approach?

### ✅ Advantages
- No large files in your Git repo
- Still have access to all HVAC examples
- NeuroMANCER always up-to-date (pip install from Git)
- Can reference full examples locally
- Key examples tracked in your repo

### 📊 Comparison

| Approach | Your Git Size | HVAC Access | Updates |
|----------|---------------|-------------|---------|
| **This approach** | Small | Full | Easy |
| Git submodule | Large (fails) | Full | Manual |
| PyPI only | Small | None | Easy |

## Citation

```bibtex
@article{Neuromancer2022,
    title={{NeuroMANCER: Neural Modules with Adaptive Nonlinear Constraints and Efficient Regularizations}},
    author={Tuor, Aaron and Drgona, Jan and Skomski, Mia and Koch, James and Chen, Zhao and Dernbach, Stefan and Legaard, Christian Møldrup and Vrabie, Draguna},
    url={https://github.com/pnnl/neuromancer},
    year={2022}
}
```

## Resources

- **NeuroMANCER Docs**: https://pnnl.github.io/neuromancer/
- **NeuroMANCER GitHub**: https://github.com/pnnl/neuromancer
- **Your HVAC Examples**: `neuromancer_examples/`
- **Full Examples Reference**: `neuromancer_repo/examples/` (local only)

## Contact

Ben Fry Holman - Western Washington University
Project: https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI
README

echo "✓ README.md created"
echo ""

# Step 4: Create requirements.txt
echo "Step 4: Creating requirements.txt..."
cat > requirements.txt << 'REQUIREMENTS'
# Core Dependencies - Python 3.12.x required

# PyTorch (install via setup script for your system)
# torch>=2.0.0
# torchvision>=0.15.0

# NeuroMANCER (installed directly from GitHub)
# git+https://github.com/pnnl/neuromancer.git

# GUI Framework
PySide6>=6.5.0

# Scientific Computing
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Image Processing
Pillow>=10.0.0

# NeuroMANCER optional dependencies
cvxpy>=1.3.0
casadi>=3.6.0

# Utilities
tqdm>=4.65.0
pyyaml>=6.0
dill>=0.3.6

# Development
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0

# Note: PyTorch and NeuroMANCER installed separately by setup script
REQUIREMENTS

echo "✓ requirements.txt created"
echo ""

# Step 5: Create Python package structure
echo "Step 5: Creating Python files..."

touch src/__init__.py
touch src/gui/__init__.py
touch src/models/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# Create main.py
cat > src/main.py << 'MAINPY'
#!/usr/bin/env python3
"""
PyTorch Buildings GUI - Main Entry Point
Using NeuroMANCER for HVAC Control
"""
import sys
from pathlib import Path

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PySide6.QtCore import Qt

try:
    import neuromancer as nm
    NEUROMANCER_AVAILABLE = True
except ImportError:
    NEUROMANCER_AVAILABLE = False


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI - NeuroMANCER HVAC")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Title
        title = QLabel("PyTorch Buildings GUI")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # NeuroMANCER status
        if NEUROMANCER_AVAILABLE:
            status = QLabel(f"✓ NeuroMANCER {nm.__version__} loaded")
            status.setStyleSheet("color: green; font-size: 18px;")
        else:
            status = QLabel("✗ NeuroMANCER not available - run setup.sh")
            status.setStyleSheet("color: red; font-size: 18px;")
        status.setAlignment(Qt.AlignCenter)
        layout.addWidget(status)
        
        # Info text
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
            <h2>HVAC Control with NeuroMANCER</h2>
            <p><b>Project Structure:</b></p>
            <ul>
                <li><b>neuromancer_examples/</b> - HVAC examples (in Git)</li>
                <li><b>neuromancer_repo/</b> - Full reference clone (local only)</li>
                <li><b>src/</b> - Your GUI application code</li>
            </ul>
            <p><b>HVAC Examples Location:</b></p>
            <ul>
                <li>neuromancer_examples/ (tracked in your Git)</li>
                <li>neuromancer_repo/examples/building_systems/ (local reference)</li>
            </ul>
            <p><b>Next Steps:</b></p>
            <ol>
                <li>Explore examples in neuromancer_examples/</li>
                <li>Reference full examples in neuromancer_repo/</li>
                <li>Build your GUI in src/gui/</li>
                <li>Create models in src/models/</li>
            </ol>
        """)
        layout.addWidget(info_text)
        
        # Buttons
        btn_examples = QPushButton("Show HVAC Examples Location")
        btn_examples.clicked.connect(self.show_examples)
        layout.addWidget(btn_examples)
    
    def show_examples(self):
        from PySide6.QtWidgets import QMessageBox
        examples_in_git = Path(__file__).parent.parent / "neuromancer_examples"
        examples_local = Path(__file__).parent.parent / "neuromancer_repo" / "examples" / "building_systems"
        
        msg = f"HVAC Examples:\n\n"
        msg += f"In your Git repo:\n{examples_in_git}\n\n"
        msg += f"Full examples (local only):\n{examples_local}\n\n"
        msg += "Key files to explore:\n"
        msg += "• Part_7_Control_HVAC_SafeDPC.py\n"
        msg += "• building_dynamics_tutorial.ipynb"
        
        QMessageBox.information(self, "HVAC Examples", msg)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
MAINPY

chmod +x src/main.py

echo "✓ Python files created"
echo ""

# Step 6: Create neuromancer_examples directory with README
echo "Step 6: Setting up neuromancer_examples directory..."
cat > neuromancer_examples/README.md << 'EXAMPLESREADME'
# NeuroMANCER HVAC Examples

This directory contains HVAC control examples copied from NeuroMANCER.

## Source

These examples are copied from:
https://github.com/pnnl/neuromancer/tree/master/examples/building_systems

## Files

After running setup.sh, this directory will contain:
- Key HVAC control examples from NeuroMANCER
- Building thermal dynamics tutorials
- Safe DPC implementations

## Full Examples

For the complete set of examples, see:
- `../neuromancer_repo/examples/building_systems/` (local reference, not in Git)

## Usage

These files are tracked in Git so your team can:
- Reference the examples
- Modify for your specific needs
- Learn from NeuroMANCER implementations

To update to latest examples:
```bash
cd neuromancer_repo
git pull origin master
cd ..
cp neuromancer_repo/examples/building_systems/FILE.py neuromancer_examples/
git add neuromancer_examples/
git commit -m "Update HVAC examples"
```
EXAMPLESREADME

echo "✓ neuromancer_examples/ created"
echo ""

# Step 7: Create/update virtual environment
echo "Step 7: Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Step 8: Install dependencies
echo "Step 8: Installing dependencies..."
echo "This will take several minutes..."
echo ""

source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing PyTorch (CUDA 11.8)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

echo "Installing NeuroMANCER directly from GitHub..."
pip install git+https://github.com/pnnl/neuromancer.git

echo "Installing other dependencies..."
pip install -r requirements.txt

echo "✓ All dependencies installed"
echo ""

# Step 9: Clone NeuroMANCER locally for reference (NOT in Git)
echo "Step 9: Cloning NeuroMANCER for local reference..."
if [ ! -d "neuromancer_repo" ]; then
    echo "Cloning NeuroMANCER repository (this will take a moment)..."
    git clone https://github.com/pnnl/neuromancer.git neuromancer_repo
    echo "✓ NeuroMANCER cloned to neuromancer_repo/ (NOT tracked in Git)"
else
    echo "✓ neuromancer_repo/ already exists"
fi
echo ""

# Step 10: Copy HVAC examples to project
echo "Step 10: Copying HVAC examples to your project..."
if [ -d "neuromancer_repo/examples/building_systems" ]; then
    echo "Copying building_systems examples..."
    cp -r neuromancer_repo/examples/building_systems/*.py neuromancer_examples/ 2>/dev/null || true
    cp -r neuromancer_repo/examples/building_systems/*.ipynb neuromancer_examples/ 2>/dev/null || true
    echo "✓ HVAC examples copied to neuromancer_examples/"
else
    echo "⚠️  Could not find building_systems examples"
fi
echo ""

# Step 11: Create .gitkeep files
touch data/.gitkeep
touch data/samples/.gitkeep
touch models/.gitkeep
touch assets/.gitkeep

# Step 12: Initialize Git if needed
echo "Step 11: Setting up Git..."
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial setup: PyTorch Buildings GUI with NeuroMANCER"
    echo "✓ Git initialized"
else
    echo "✓ Git already initialized"
fi
echo ""

echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "NeuroMANCER has been installed without adding large files to Git!"
echo ""
echo "Project structure:"
echo "  • Your code: src/"
echo "  • HVAC examples (in Git): neuromancer_examples/"
echo "  • Full NeuroMANCER reference (NOT in Git): neuromancer_repo/"
echo ""
echo "✓ Your Git repo stays small (no large files)"
echo "✓ NeuroMANCER installed: pip install git+https://..."
echo "✓ HVAC examples copied to neuromancer_examples/"
echo "✓ Full examples available in neuromancer_repo/ (local only)"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Test the GUI:"
echo "   python src/main.py"
echo ""
echo "3. Explore HVAC examples:"
echo "   cd neuromancer_examples"
echo "   ls *.py"
echo ""
echo "4. Reference full examples:"
echo "   cd neuromancer_repo/examples/building_systems"
echo ""
echo "5. Push to GitHub (small repo!):"
echo "   git remote add origin https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git"
echo "   git push -u origin main"
echo ""
echo "To update NeuroMANCER later:"
echo "   pip install --upgrade git+https://github.com/pnnl/neuromancer.git"
echo "   cd neuromancer_repo && git pull && cd .."
echo ""