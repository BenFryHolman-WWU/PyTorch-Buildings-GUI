"""Icon loading helpers for toolbar and component assets."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap


ICON_EXTENSIONS = (".svg", ".png", ".jpg", ".jpeg")
FOLDER_ICON_CANDIDATES = (
    "web/icon-512.png",
    "web/icon-192.png",
    "android/play_store_512.png",
    "macos/AppIcon512.png",
    "macos/AppIcon256.png",
)

ICON_NAME_ALIASES = {
    "new": ("newProject",),
    "new_asset": ("newProject",),
    "newproject": ("newProject",),
    "plot_center": ("plotcenter",),
    "plot_center_asset": ("plotcenter",),
    "plotcenter": ("plotcenter",),
    "editcomponent": ("edit",),
    "edit_component": ("edit",),
    "edit_component_asset": ("edit",),
    "deletecomponent": ("delete",),
    "delete_component": ("delete",),
    "delete_component_asset": ("delete",),
    "deleteconnection": ("removeconnection",),
    "delete_connection": ("removeconnection",),
    "delete_connection_asset": ("removeconnection",),
    "remove_connection": ("removeconnection",),
    "remove_connection_asset": ("removeconnection",),
}


class IconProvider:

    def __init__(self, assets_path):
        self.assets_path = Path(assets_path)
        self.icon_path = self.assets_path / "icons"
        self._cache = {}

    def icon(self, *names, fallback_text=""):
        """
        Summary: Icon.
        Args: fallback_text, *names
        Returns: Return the computed value.
        """
        cache_key = tuple(names) + (fallback_text,)
        if cache_key in self._cache:
            return self._cache[cache_key]
        for name in names:
            found = self._find_icon(name)
            if found is not None:
                icon = QIcon(str(found))
                self._cache[cache_key] = icon
                return icon
        fallback = self._fallback_icon(fallback_text or (names[0] if names else "?"))
        self._cache[cache_key] = fallback
        return fallback

    def _find_icon(self, name):
        """
        Summary: Find icon.
        Returns: Return the computed value.
        """
        if not name:
            return None
        candidate = Path(name)
        aliases = ICON_NAME_ALIASES.get(candidate.stem.lower(), ())
        search_names = list(aliases) + [candidate.name]
        if candidate.suffix:
            search_names.append(candidate.stem)
        else:
            search_names.extend(f"{candidate.name}{ext}" for ext in ICON_EXTENSIONS)
        for base in (self.icon_path, self.assets_path):
            for search_name in search_names:
                path = base / search_name
                if path.exists():
                    if path.is_dir():
                        folder_icon = self._find_folder_icon(path)
                        if folder_icon is not None:
                            return folder_icon
                    else:
                        return path
        return None

    def _find_folder_icon(self, folder):
        for relative_path in FOLDER_ICON_CANDIDATES:
            path = folder / relative_path
            if path.exists():
                return path
        return None

    def _fallback_icon(self, text):
        """
        Summary: Fallback icon.
        Returns: Return the computed value.
        """
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#dce3f5"))
        painter.drawRoundedRect(5, 5, size - 10, size - 10, 12, 12)
        painter.setPen(QColor("#3a4468"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text[:2].upper())
        painter.end()
        return QIcon(pixmap)
