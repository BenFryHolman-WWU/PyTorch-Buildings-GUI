"""Shared helpers for the main window modules."""

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QPushButton, QSizePolicy

from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox

COMPONENTS = [Envelope, RTU, VAVBox, SolarGains]
COMPONENT_ICON_NAMES = {
    "Envelope": ["RTU", "rtu", "rooftop_unit"],
    "RTU": ["Envelope", "envelope", "building_envelope"],
    "VAVBox": ["Vavbox", "vav_box", "vav"],
    "SolarGains": ["SolarGains", "solar_gains", "solar"],
}

OPACITY_STEPS = [1.0, 0.0]


def _button_style(
    *,
    bg: str = "#fafbfd",
    hover_bg: str = "#eaecf5",
    pressed_bg: str = "#d8dbe9",
    color: str = "#3a4468",
    border: str = "#c4c9dc",
    hover_border: str = "#a8b0cc",
    radius: int = 4,
    font_size: int = 10,
    font_weight: int = 600,
    padding: str = "0",
) -> str:
    """
    Summary: Button style.
    Returns: Return the computed value.
    """
    return (
        f"QPushButton {{ background: {bg}; color: {color}; border: 1px solid {border};"
        f" border-radius: {radius}px; font-size: {font_size}px;"
        f" font-weight: {font_weight}; padding: {padding}; }}"
        f"QPushButton:hover {{ background: {hover_bg}; border: 1px solid {hover_border}; }}"
        f"QPushButton:pressed {{ background: {pressed_bg}; }}"
    )


def _line_toggle_style(enabled: bool) -> str:
    """
    Summary: Line toggle style.
    Returns: Return the computed value.
    """
    fill = "#2f9d68" if enabled else "#b8bfcc"
    border = "#ffffff" if enabled else "#f4f6fc"
    return _button_style(
        bg=fill,
        hover_bg=fill,
        pressed_bg=fill,
        color="#ffffff",
        border=border,
        hover_border="#2c3868",
        radius=4,
        font_size=8,
        padding="0",
    )


def _policy_toggle_style(enabled: bool) -> str:
    """
    Summary: Policy toggle style.
    Returns: Return the computed value.
    """
    fill = "#2f9d68" if enabled else "#c04040"
    return _button_style(
        bg=fill,
        hover_bg=fill,
        pressed_bg=fill,
        color="#ffffff",
        border="#f4f6fc",
        hover_border="#2c3868",
        radius=7,
        font_size=8,
        padding="0",
    )


def _plot_settings_title(text: str, fallback: str, max_len: int = 18) -> str:
    """
    Summary: Plot settings title.
    Args: fallback, max_len
    Returns: Return the computed value.
    """
    title = (text or fallback).split("[", 1)[0].strip()
    replacements = {
        "Temperature": "Temp",
        "Setpoint": "Setpt",
        "Supply": "Sup.",
        "Pressure": "Press.",
        "Airflow": "Air",
        "Power": "Pwr",
    }
    for old, new in replacements.items():
        title = title.replace(old, new)
    title = title or fallback
    if len(title) > max_len:
        title = title[: max_len - 3].rstrip() + "..."
    return title


class LineStylePreviewButton(QPushButton):

    selected = pyqtSignal(str)

    def __init__(self, style: str, icon: QIcon, parent=None):
        """
        Summary: Init.
        Args: icon
        """
        super().__init__(parent)
        self.style = style
        self.setIcon(icon)
        self.setIconSize(QSize(204, 18))
        self.setFixedSize(204, 26)
        self.setToolTip(style)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 2px 0; }"
            "QPushButton:hover { background: #dce7fb; }"
        )
        self.clicked.connect(lambda: self.selected.emit(self.style))


class LineStyleButton(QPushButton):

    def __init__(self, make_icon, style: str, line_width: int, parent=None):
        super().__init__(parent)
        self._make_icon = make_icon
        self.line_style = style
        self.line_width = line_width
        self.setMinimumHeight(22)
        self.setMinimumWidth(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(style)
        self._refresh_icon()

    def set_line_appearance(self, style: str, width: int):
        self.line_style = style
        self.line_width = width
        self.setToolTip(style)
        self._refresh_icon()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_icon()

    def _refresh_icon(self):
        icon_w = max(40, self.width() - 10)
        self.setIcon(self._make_icon(self.line_style, icon_w, 14, self.line_width))
        self.setIconSize(QSize(icon_w, 14))
