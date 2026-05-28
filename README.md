# PyTorch Buildings GUI

A desktop application for designing and simulating building HVAC systems using the NeuroMANCER library.

## Requirements

- Python 3.10, 3.11, or 3.12

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/BenFryHolman-WWU/PyTorch-Buildings-GUI.git
cd PyTorch-Buildings-GUI
```

### 2. Run the setup script

**macOS / Linux**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows**
```bat
scripts\setup.bat
```

### 3. Run the application

```bash
# macOS / Linux
source .venv/bin/activate
python src/main.py

# Windows
.venv\Scripts\activate
python src\main.py
```

## Run Tests

```bash
source .venv/bin/activate
python scripts/run_tests.py
```

The test runner uses `unittest` and shows a progress bar with the current test and pass/fail status.

## UI Icons

Add toolbar and component icons to `assets/icons/`. The UI checks this folder first and falls back to generated initials if an icon is missing. See `assets/icons/README.md` for recommended filenames.

## Project Structure

```
PyTorch-Buildings-GUI/
├── src/
│   ├── main.py                  # Application entry point
│   ├── gui/                     # PyQt6 GUI components
│   ├── models/                  # Building model (state, zones, connections)
│   └── simulation/              # Simulation runner and plotter
├── neuromancer_repo/            # Bundled NeuroMANCER HVAC library
│   └── src/neuromancer/
│       ├── hvac/                # HVAC building components and simulation
│       ├── constraint.py
│       ├── gradients.py
│       └── utils.py
├── assets/                      # Icons and images
├── docs/                        # Project documentation
├── saved/                       # Saved building layouts (JSON)
├── scripts/
│   ├── setup.sh                 # Setup script (macOS/Linux)
│   └── setup.bat                # Setup script (Windows)
├── requirements.txt             # Python dependencies
└── .venv/                       # Virtual environment (not in Git)
```

## Supported Components

| Component  | Description                              |
|------------|------------------------------------------|
| Envelope   | Building thermal envelope (zones, walls) |
| RTU        | Rooftop unit (heating, cooling, fan)     |
| VAVBox     | Variable air volume terminal box         |
| SolarGains | Solar irradiance and outdoor temperature |

## Dependencies

| Package       | Purpose                         |
|---------------|---------------------------------|
| PyQt6         | GUI framework                   |
| torch         | Tensor computation              |
| torchdiffeq   | ODE solver for thermal model    |
| numpy / scipy | Numerical computation           |
| matplotlib    | Plot export                     |
| networkx      | System graph (neuromancer)      |
| pydot         | Graph visualisation             |
| plum-dispatch | Multiple dispatch (neuromancer) |
| lightning     | Neural network utilities        |
| beartype      | Runtime type checking           |

## NeuroMANCER

This project uses the HVAC branch of the [NeuroMANCER](https://github.com/pnnl/neuromancer) library, bundled in `neuromancer_repo/`.

- [HVAC source code](https://github.com/pnnl/neuromancer/tree/hvac/src/neuromancer/hvac)
- [NeuroMANCER documentation and user guides](https://github.com/pnnl/neuromancer?tab=readme-ov-file#documentation-and-user-guides)
