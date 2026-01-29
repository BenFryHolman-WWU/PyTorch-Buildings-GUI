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
