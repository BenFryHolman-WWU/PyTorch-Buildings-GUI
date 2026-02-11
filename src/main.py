import sys
from pathlib import Path

# -----------------------------
# Add src paths to sys.path
# -----------------------------
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

NM_SRC = Path(__file__).resolve().parents[1] / "neuromancer_repo" / "src"
if str(NM_SRC) not in sys.path:
    sys.path.insert(0, str(NM_SRC))

# -----------------------------
# Imports
# -----------------------------
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QSplitter
)
from PyQt6.QtCore import Qt

from interactive_canvas import InteractiveCanvas
from drag_button import DragButton

# -----------------------------
# Dependency Checks
# -----------------------------
def check_dependencies():
    results = {}

    try:
        import torch
        results["torch"] = (True, torch.__version__)
    except Exception:
        results["torch"] = (False, "")

    try:
        import torchdiffeq
        results["torchdiffeq"] = (True, torchdiffeq.__version__)
    except Exception:
        results["torchdiffeq"] = (False, "")

    try:
        import numpy as np
        results["numpy"] = (True, np.__version__)
    except Exception:
        results["numpy"] = (False, "")

    try:
        import matplotlib
        results["matplotlib"] = (True, matplotlib.__version__)
    except Exception:
        results["matplotlib"] = (False, "")

    try:
        from PyQt6 import QtCore
        results["PyQt6"] = (True, QtCore.PYQT_VERSION_STR)
    except Exception:
        results["PyQt6"] = (False, "")

    try:
        import neuromancer as nm
        results["neuromancer"] = (True, nm.__version__)
    except Exception:
        results["neuromancer"] = (False, "")

    return results

DEP_RESULTS = check_dependencies()

# -----------------------------
# Import Neuromancer Components
# -----------------------------
def import_components():
    from neuromancer.hvac.building_components.envelope import Envelope
    from neuromancer.hvac.building_components.rooftop_unit import RTU
    from neuromancer.hvac.building_components.vav_box import VAVBox
    from neuromancer.hvac.building_components.solar_gain import SolarGains
    return [Envelope, RTU, VAVBox, SolarGains]

COMPONENTS = import_components()

# -----------------------------
# Main Window
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Canvas
        self.canvas = InteractiveCanvas()

        # Left Panel
        left_panel = self.create_left_panel()

        # Splitter between left panel and canvas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 1100])

        main_layout.addWidget(splitter)

    # -----------------------------
    # Left Panel
    # -----------------------------
    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # ===== Dependency Status Section =====
        dep_title = QLabel("Dependency Status:")
        dep_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(dep_title)

        for name, (ok, version) in DEP_RESULTS.items():
            status = "✓" if ok else "✗"
            label = QLabel(f"{status} {name} ({version})")
            layout.addWidget(label)

        layout.addStretch()  # Pushes Components section down

        # ===== Components Section =====
        comp_title = QLabel("Components:")
        comp_title.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 20px;")
        layout.addWidget(comp_title)

        for cls in COMPONENTS:
            button = DragButton(cls.__name__, self.canvas)  # <-- pass canvas
            button.setFixedSize(120, 40)
            layout.addWidget(button)

        layout.addStretch()  # Pushes buttons to top, leaves space below
        return panel

# -----------------------------
# App Entry
# -----------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
