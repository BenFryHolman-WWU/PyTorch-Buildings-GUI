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
