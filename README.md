# PyTorch Buildings GUI

A GUI application for building HVAC control using PNNL's NeuroMANCER library.

## Requirements

- **Python 3.12.x** (required)

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git
cd PyTorch-Buildings-GUI

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

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
├── .gitignore
├── .gitattributes
├── src/
│   ├── main.py              # GUI entry point
│   ├── gui/                 # Your GUI code
│   ├── models/              # Your models using NeuroMANCER
│   └── utils/
├── neuromancer_repo/        # Full NeuroMANCER clone (NOT in Git)
│   └── (Clone of pnnl/neuromancer for reference)
├── assets/
├── docs/
├── scripts/
|── tests/
└── .venv/                   # Virtual environment (NOT in Git)
```

## NeuroMANCER Access

### Using in Code
```python
import neuromancer as nm
from neuromancer.blocks import MLP
from neuromancer.system import Node

# Full access to all NeuroMANCER features
```

## Resources

- **NeuroMANCER Docs**: https://pnnl.github.io/neuromancer/
- **NeuroMANCER GitHub**: https://github.com/pnnl/neuromancer/tree/hvac
