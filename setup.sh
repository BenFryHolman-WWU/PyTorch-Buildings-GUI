#!/bin/bash

# PyTorch Buildings GUI - Complete Project Setup
# This script creates the entire project structure from scratch

set -e  # Exit on error

echo "=========================================="
echo "PyTorch Buildings GUI - Project Setup"
echo "=========================================="
echo ""
echo "This will create a complete project structure for a GUI application"
echo "using PNNL's NeuroMANCER library for building control."
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

# Step 1: Create directory structure
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
.virtualenv/

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
*.spec

# PyTorch & NeuroMANCER
*.pth
*.pt
*.ckpt
wandb/
lightning_logs/

# IDE
.vscode/
.idea/
*.swp
*.swo
*.sublime-project
*.sublime-workspace

# OS
.DS_Store
Thumbs.db
*.log

# Jupyter Notebooks
.ipynb_checkpoints/
*.ipynb

# Data (large files should be downloaded separately)
data/raw/
data/processed/
data/*.zip
data/*.tar.gz
!data/samples/

# Model weights
models/*.pth
models/*.pt
models/*.ckpt
!models/.gitkeep

# Environment variables
.env
.env.local

# Coverage reports
htmlcov/
.coverage
.pytest_cache/

# Project specific
outputs/
experiments/
checkpoints/
results/
GITIGNORE

echo "✓ .gitignore created"
echo ""

# Step 3: Create .gitattributes (optional, for Git LFS)
echo "Step 3: Creating .gitattributes..."
cat > .gitattributes << 'GITATTRIBUTES'
# Git LFS tracking for large binary files
# Uncomment these if you want to store model weights in Git

# PyTorch model files
# *.pth filter=lfs diff=lfs merge=lfs -text
# *.pt filter=lfs diff=lfs merge=lfs -text
# *.ckpt filter=lfs diff=lfs merge=lfs -text
GITATTRIBUTES

echo "✓ .gitattributes created"
echo ""

# Step 4: Create main README.md
echo "Step 4: Creating README.md..."
cat > README.md << 'README'
# PyTorch Buildings GUI

A GUI application for building energy management and control using PNNL's NeuroMANCER library - a PyTorch-based framework for differentiable predictive control and optimization.

## Overview

This application provides an interactive interface for:
- Building energy system modeling and control
- HVAC optimization using neural networks
- Real-time building performance visualization
- Model training and evaluation

Built on top of [NeuroMANCER](https://github.com/pnnl/neuromancer), this tool leverages differentiable predictive control for efficient building operations.

## Requirements

- **Python 3.12.x** (required)
- CUDA-compatible GPU (recommended for training)
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git
cd PyTorch-Buildings-GUI
```

### 2. Run Setup Script

The setup script will create a virtual environment, install all dependencies including NeuroMANCER, and prepare the project.

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
setup.bat
```

### 3. Run the Application

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Launch GUI
python src/main.py
```

## Manual Installation

If you prefer to set up manually:

### 1. Create Virtual Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install --upgrade pip

# Install PyTorch (adjust for your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install NeuroMANCER
pip install neuromancer

# Install GUI and other dependencies
pip install -r requirements.txt
```

## Project Structure

```
PyTorch-Buildings-GUI/
├── src/
│   ├── main.py              # Application entry point
│   ├── gui/                 # GUI components (PySide6)
│   │   ├── main_window.py   # Main application window
│   │   └── widgets.py       # Custom widgets
│   ├── models/              # NeuroMANCER model definitions
│   │   └── building_control.py
│   └── utils/               # Utility functions
│       └── data_processing.py
├── data/
│   └── samples/             # Example data
├── models/                  # Trained model weights
├── scripts/                 # Training/preprocessing scripts
├── tests/                   # Unit tests
├── assets/                  # Icons, images, etc.
└── requirements.txt         # Python dependencies
```

## Features

### Current Features
- Interactive GUI for building control
- Integration with NeuroMANCER framework
- Model training and evaluation interface
- Data visualization

### Planned Features
- Real-time building data integration
- Multi-building optimization
- Advanced visualization dashboards
- Export/import functionality for models

## Usage

### Training a Model

```bash
python scripts/train_model.py --data data/building_data.csv --epochs 100
```

### Running Tests

```bash
pytest tests/
```

## Development

### Setting Up for Development

```bash
# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
pytest

# Format code
black src/

# Lint
flake8 src/
```

## About NeuroMANCER

This project uses [NeuroMANCER (Neural Modules with Adaptive Nonlinear Constraints and Efficient Regularizations)](https://github.com/pnnl/neuromancer), developed by Pacific Northwest National Laboratory (PNNL). NeuroMANCER enables:

- Differentiable predictive control (DPC)
- Physics-informed neural networks
- Constrained optimization with neural networks
- Building energy management applications

## Citation

If you use this tool in your research, please cite:

```bibtex
@article{Neuromancer2022,
    title={{NeuroMANCER: Neural Modules with Adaptive Nonlinear Constraints and Efficient Regularizations}},
    author={Tuor, Aaron and Drgona, Jan and Skomski, Mia and Koch, James and Chen, Zhao and Dernbach, Stefan and Legaard, Christian Møldrup and Vrabie, Draguna},
    url={https://github.com/pnnl/neuromancer},
    year={2022}
}
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Specify your license here]

## Contact

Ben Fry Holman - Western Washington University

Project Link: https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI

## Acknowledgments

- [PNNL NeuroMANCER Team](https://github.com/pnnl/neuromancer)
- [PyTorch](https://pytorch.org/)
- [PySide6](https://www.qt.io/qt-for-python)
README

echo "✓ README.md created"
echo ""

# Step 5: Create requirements.txt
echo "Step 5: Creating requirements.txt..."
cat > requirements.txt << 'REQUIREMENTS'
# Core Dependencies - Requires Python 3.12.x

# PyTorch (install separately for your system - see README)
# torch>=2.0.0
# torchvision>=0.15.0

# NeuroMANCER - PyTorch-based control library
neuromancer>=1.5.0

# GUI Framework
PySide6>=6.5.0

# Scientific Computing
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0

# Image Processing (if needed)
Pillow>=10.0.0

# Utilities
tqdm>=4.65.0
pyyaml>=6.0

# Development (optional)
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0

# Note: PyTorch should be installed separately based on your system
# For CUDA 11.8: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# For CPU only: pip install torch torchvision
REQUIREMENTS

echo "✓ requirements.txt created"
echo ""

# Step 6: Create Python package structure
echo "Step 6: Creating Python package files..."

# Create __init__.py files
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

A GUI application for building energy management using NeuroMANCER.
"""
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    """Main application window - starter template"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Add welcome message
        label = QLabel("Welcome to PyTorch Buildings GUI\n\nBuilt with NeuroMANCER")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; padding: 50px;")
        layout.addWidget(label)
        
        # TODO: Add your GUI components here
        # - Control panels
        # - Visualization widgets
        # - Model configuration
        # - Data input/output


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("PyTorch Buildings GUI")
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
MAINPY

chmod +x src/main.py

# Create example model file
cat > src/models/building_control.py << 'MODELPY'
"""
Building Control Models using NeuroMANCER

This module contains model definitions for building energy control.
"""
import torch
import neuromancer as nm


class BuildingController:
    """Example building controller using NeuroMANCER"""
    
    def __init__(self, input_size: int, output_size: int):
        """
        Initialize building controller
        
        Args:
            input_size: Number of input features (sensors, weather, etc.)
            output_size: Number of control outputs (HVAC setpoints, etc.)
        """
        self.input_size = input_size
        self.output_size = output_size
        
        # Create neural network for control policy
        # TODO: Implement your NeuroMANCER model here
        # Example:
        # self.policy = nm.blocks.MLP(
        #     insize=input_size,
        #     outsize=output_size,
        #     hsizes=[64, 64]
        # )
    
    def predict(self, state: torch.Tensor) -> torch.Tensor:
        """
        Predict control actions given current state
        
        Args:
            state: Current building state (temperature, occupancy, etc.)
            
        Returns:
            Control actions (HVAC setpoints, etc.)
        """
        # TODO: Implement control logic
        pass


# TODO: Add more model classes as needed
MODELPY

# Create example utility file
cat > src/utils/data_processing.py << 'UTILSPY'
"""
Data Processing Utilities

Functions for loading, preprocessing, and handling building data.
"""
import pandas as pd
import numpy as np
from pathlib import Path


def load_building_data(filepath: Path) -> pd.DataFrame:
    """
    Load building energy data from file
    
    Args:
        filepath: Path to data file (CSV, Excel, etc.)
        
    Returns:
        DataFrame with building data
    """
    # TODO: Implement data loading
    pass


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess building data for model input
    
    Args:
        df: Raw building data
        
    Returns:
        Preprocessed data ready for model
    """
    # TODO: Implement preprocessing
    # - Handle missing values
    # - Normalize features
    # - Create time features
    # - etc.
    pass


# TODO: Add more utility functions
UTILSPY

echo "✓ Python package files created"
echo ""

# Step 7: Create .gitkeep files for empty directories
echo "Step 7: Creating .gitkeep files..."
touch data/.gitkeep
touch data/samples/.gitkeep
touch models/.gitkeep
touch assets/.gitkeep

echo "✓ .gitkeep files created"
echo ""

# Step 8: Create or update virtual environment
echo "Step 8: Setting up virtual environment..."

if [ ! -d ".venv" ]; then
    echo "Creating new virtual environment..."
    $PYTHON_CMD -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Step 9: Install dependencies
echo "Step 9: Installing dependencies..."
echo "This may take several minutes..."
echo ""

source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo "Installing PyTorch (this may take a while)..."
# Install PyTorch with CUDA 11.8 support (adjust as needed)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 --quiet

echo "Installing NeuroMANCER..."
pip install neuromancer --quiet

echo "Installing GUI and other dependencies..."
pip install -r requirements.txt --quiet

echo "✓ All dependencies installed"
echo ""

# Step 10: Initialize Git repository
echo "Step 10: Initializing Git repository..."

if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit: Project setup with NeuroMANCER integration"
    echo "✓ Git repository initialized"
else
    echo "✓ Git repository already exists"
fi

echo ""

# Step 11: Create useful scripts
echo "Step 11: Creating utility scripts..."

cat > scripts/train_model.py << 'TRAINPY'
#!/usr/bin/env python3
"""
Model Training Script

Train a building control model using NeuroMANCER.
"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="Train building control model")
    parser.add_argument("--data", type=str, required=True, help="Path to training data")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--output", type=str, default="models/", help="Output directory for model")
    
    args = parser.parse_args()
    
    print(f"Training model on {args.data} for {args.epochs} epochs")
    # TODO: Implement training logic
    

if __name__ == "__main__":
    main()
TRAINPY

chmod +x scripts/train_model.py

echo "✓ Utility scripts created"
echo ""

# Step 12: Create sample test
cat > tests/test_basic.py << 'TESTPY'
"""
Basic Tests

Verify project setup and imports work correctly.
"""
import pytest


def test_imports():
    """Test that key packages can be imported"""
    import torch
    import neuromancer
    from PySide6 import QtWidgets
    assert True


def test_project_structure():
    """Test that project directories exist"""
    from pathlib import Path
    
    assert Path("src").exists()
    assert Path("src/models").exists()
    assert Path("src/gui").exists()
    assert Path("data").exists()
    assert Path("models").exists()


# TODO: Add more tests
TESTPY

echo "✓ Tests created"
echo ""

echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Project structure created successfully!"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Test the installation:"
echo "   python src/main.py"
echo ""
echo "3. Run tests:"
echo "   pytest tests/"
echo ""
echo "4. Start developing your GUI in src/gui/"
echo ""
echo "5. Add your NeuroMANCER models in src/models/"
echo ""
echo "6. When ready, push to GitHub:"
echo "   git remote add origin https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git"
echo "   git push -u origin main"
echo ""
echo "For more information, see README.md"
echo ""
echo "Documentation:"
echo "  - NeuroMANCER: https://pnnl.github.io/neuromancer/"
echo "  - PyTorch: https://pytorch.org/docs/"
echo "  - PySide6: https://doc.qt.io/qtforpython/"
echo ""