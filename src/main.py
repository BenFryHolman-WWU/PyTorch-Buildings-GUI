"""Application entry point for the PyTorch Buildings GUI."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from gui.dialogue_manager import show_error_dialog
from gui.main_window import MainWindow

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    def show_unexpected_error(_error_type, _error, _traceback):
        show_error_dialog(
            window,
            "Unexpected Error",
            "The application encountered an unexpected error. Your current project has not been intentionally changed.",
        )

    sys.excepthook = show_unexpected_error
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
