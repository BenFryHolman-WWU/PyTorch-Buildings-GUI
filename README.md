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
