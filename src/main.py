#!/usr/bin/env python3
"""
PyTorch Buildings GUI - Main Entry Point
Interactive canvas with zoom/pan for building HVAC control
"""
import sys
from pathlib import Path

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGraphicsView, QGraphicsScene,
    QLabel, QSplitter, QStatusBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush


# ---------------------------
# Dependency Checks (ONE PASS)
# ---------------------------

def check_dependencies():
    results = {}

    # torch
    try:
        import torch
        results["torch"] = (True, torch.__version__)
    except Exception as e:
        results["torch"] = (False, str(e))

    # torchdiffeq
    try:
        import torchdiffeq
        results["torchdiffeq"] = (True, torchdiffeq.__version__)
    except Exception as e:
        results["torchdiffeq"] = (False, str(e))

    # numpy
    try:
        import numpy as np
        results["numpy"] = (True, np.__version__)
    except Exception as e:
        results["numpy"] = (False, str(e))

    # matplotlib
    try:
        import matplotlib
        results["matplotlib"] = (True, matplotlib.__version__)
    except Exception as e:
        results["matplotlib"] = (False, str(e))

    # PyQt6
    try:
        from PyQt6 import QtCore
        results["PyQt6"] = (True, QtCore.PYQT_VERSION_STR)
    except Exception as e:
        results["PyQt6"] = (False, str(e))

    # neuromancer (optional but useful)
    try:
        import neuromancer as nm
        results["neuromancer"] = (True, nm.__version__)
    except Exception as e:
        results["neuromancer"] = (False, str(e))

    all_ok = all(v[0] for v in results.values())
    return all_ok, results


ALL_DEPS_OK, DEP_RESULTS = check_dependencies()


# ---------------------------
# Canvas
# ---------------------------

class InteractiveCanvas(QGraphicsView):
    """Interactive canvas with zoom and pan capabilities"""

    def __init__(self):
        super().__init__()

        # Create scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Configure view
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Set background
        self.setBackgroundBrush(QBrush(QColor(240, 240, 245)))

        # Initial zoom
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0

        # Draw grid (NO crosshair)
        self.draw_grid()

    def draw_grid(self):
        """Draw a grid on the canvas (no origin crosshair)"""
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(1)

        grid_size = 50
        grid_range = 2000

        for x in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(x, -grid_range, x, grid_range, pen)

        for y in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(-grid_range, y, grid_range, y, pen)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        delta = event.angleDelta().y()

        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        zoom = zoom_in_factor if delta > 0 else zoom_out_factor

        new_zoom = self.zoom_factor * zoom
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        self.scale(zoom, zoom)
        self.zoom_factor = new_zoom
        event.accept()


# ---------------------------
# Main Window
# ---------------------------

class MainWindow(QMainWindow):
    """Main application window with interactive canvas"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Create left panel
        left_panel = self.create_left_panel()

        # Create canvas
        self.canvas = InteractiveCanvas()

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 1100])

        main_layout.addWidget(splitter)

        # Create status bar
        self.create_status_bar()

    # ---------------------------
    # Left Panel
    # ---------------------------

    def create_left_panel(self):
        """Create left panel showing ONE unified dependency check"""
        panel = QWidget()
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(380)

        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Title
        title = QLabel("System Check")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Overall status
        if ALL_DEPS_OK:
            overall = QLabel("✓ All dependencies ready")
            overall.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        else:
            overall = QLabel("✗ Missing / broken dependencies")
            overall.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")

        layout.addWidget(overall)
        layout.addSpacing(10)

        # Detailed results
        for name, (ok, info) in DEP_RESULTS.items():
            row = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 2, 0, 2)
            row.setLayout(row_layout)

            icon = QLabel("✓" if ok else "✗")
            icon.setFixedWidth(18)
            icon.setStyleSheet(
                "color: green; font-weight: bold;" if ok else "color: red; font-weight: bold;"
            )
            row_layout.addWidget(icon)

            if ok:
                label = QLabel(f"{name} ({info})")
            else:
                label = QLabel(f"{name} (not available)")
                label.setStyleSheet("color: #999;")

            row_layout.addWidget(label)
            row_layout.addStretch()

            layout.addWidget(row)

        layout.addStretch()

        # Style panel
        panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-right: 1px solid #ccc;
            }
            QLabel {
                color: #333;
            }
        """)

        return panel

    # ---------------------------
    # Status Bar
    # ---------------------------

    def create_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.zoom_label = QLabel("Zoom: 100%")
        status_bar.addPermanentWidget(self.zoom_label)

        status_bar.showMessage("Ready — Mouse wheel to zoom, drag to pan")


# ---------------------------
# App Entry
# ---------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PyTorch Buildings GUI")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
