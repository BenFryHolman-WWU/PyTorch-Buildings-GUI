import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
NEUROMANCER_SRC = ROOT / "neuromancer_repo" / "src"

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp")

for path in (SRC, NEUROMANCER_SRC):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def get_qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class CanvasStub:
    def update_connection_lines_for_item(self, item):
        pass

    def notify_component_clicked(self, item):
        pass
