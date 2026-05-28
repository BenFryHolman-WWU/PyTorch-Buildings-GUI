"""Application entry point for the PyTorch Buildings GUI."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
