"""Results dialog for embedded simulation plots."""

import matplotlib
matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt


class ResultsWindow(QDialog):

    def __init__(self, fig, title="Simulation Results", parent=None):
        """
        Summary: Init.
        Args: fig
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 580)
        self.setSizeGripEnabled(True)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint
        )

        canvas  = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar2QT(canvas, self)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(toolbar)
        layout.addWidget(canvas, 1)
        layout.addLayout(btn_row)
