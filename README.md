# PyTorch Buildings GUI

A desktop application for designing and simulating building HVAC systems using the NeuroMANCER library.

## Requirements

-   Python 3.10, 3.11, or 3.12

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.gitcd PyTorch-Buildings-GUI
```

### 2. Run the setup script

**macOS / Linux**

```bash
chmod +x scripts/setup.sh./scripts/setup.sh
```

**Windows**

```bat
scriptssetup.bat
```

### 3. Run the application

```bash
source .venv/bin/activate        # Windows: .venvScriptsactivatepython src/main.py
```

## Project Structure

```
PyTorch-Buildings-GUI/├── src/│   ├── main.py                  # Application entry point│   ├── gui/                     # PyQt6 GUI components│   ├── models/                  # Building model (state, zones, connections)│   └── simulation/              # Simulation runner and plotter├── neuromancer_repo/            # Bundled NeuroMANCER HVAC library│   └── src/neuromancer/│       ├── hvac/                # HVAC building components and simulation│       ├── constraint.py│       ├── gradients.py│       └── utils.py├── assets/                      # Icons and images├── docs/                        # Project documentation├── saved/                       # Saved building layouts (JSON)├── scripts/│   ├── setup.sh                 # Setup script (macOS/Linux)│   └── setup.bat                # Setup script (Windows)├── requirements.txt             # Python dependencies└── .venv/                       # Virtual environment (not in Git)