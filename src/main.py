import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

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
# App Entry
# -----------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
