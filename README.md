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
