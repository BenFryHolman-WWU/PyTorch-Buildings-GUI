"""Top toolbar for primary project and canvas actions."""

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget

from .icons import IconProvider
ICON_SIZE = QSize(22, 22)
BASE_TOOLBAR_WIDTH = 1500


ACTION_ICONS = {
    "New": ("newProject", "new", "new_asset"),
    "Save As": ("saveas", "save_as", "save_as_asset", "save"),
    "Save": ("save", "save_asset"),
    "Load": ("load", "load_asset", "open"),
    "Undo": ("undo", "undo_asset"),
    "Redo": ("redo", "redo_asset"),
    "Add Connection": ("addconnection", "connection", "add_connection", "add_connection_asset"),
    "Edit Component": ("editcomponent", "edit", "edit_component", "edit_component_asset"),
    "Delete Component": ("deletecomponent", "delete", "trash", "delete_component", "delete_component_asset"),
    "Delete Connection": ("removeconnection", "deleteconnection", "delete_connection", "delete_connection_asset"),
    "Delete Area": ("deletearea", "delete_area", "delete_area_asset", "selection_delete", "delete"),
}


class HeaderBar(QWidget):

    def __init__(self, assets_path, callbacks):
        """
        Summary: Init.
        Args: assets_path, callbacks
        """
        super().__init__()
        self.assets_path = Path(assets_path)
        self.callbacks = callbacks
        self.icons = IconProvider(self.assets_path)
        self.action_buttons = []
        self.undo_btn = None
        self.redo_btn = None
        self.add_connection_btn = None
        self.edit_component_btn = None
        self.delete_component_btn = None
        self.delete_connection_btn = None
        self.area_delete_btn = None
        self._toolbar_layout = None
        self._title_label = None
        self._last_scale_key = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(42)
        self._build()

    def _build(self):
        """Summary: Build."""
        layout = QHBoxLayout(self)
        self._toolbar_layout = layout
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        title = QLabel("PyTorch Buildings")
        title.setObjectName("appTitle")
        self._title_label = title
        layout.addWidget(title)
        layout.addSpacing(8)

        for label, key in (
            ("New", "new"),
            ("Save As", "save_as"),
            ("Save", "save"),
            ("Load", "load"),
        ):
            if key in self.callbacks:
                layout.addWidget(self._create_action_button(label, self.callbacks[key]))

        layout.addWidget(self._separator())
        for label, key in (
            ("Undo", "undo"),
            ("Redo", "redo"),
        ):
            if key in self.callbacks:
                button = self._create_action_button(label, self.callbacks[key])
                if key == "undo":
                    self.undo_btn = button
                elif key == "redo":
                    self.redo_btn = button
                layout.addWidget(button)

        self.add_connection_btn = self._create_action_button(
            "Add Connection", self.callbacks["add_connection"], checkable=True
        )
        self.edit_component_btn = self._create_action_button(
            "Edit Component", self.callbacks["edit_component"], checkable=True
        )
        self.delete_connection_btn = self._create_action_button(
            "Delete Connection", self.callbacks["delete_connection"], checkable=True
        )
        self.delete_component_btn = self._create_action_button(
            "Delete Component", self.callbacks["delete_component"], checkable=True
        )
        self.area_delete_btn = self._create_action_button(
            "Delete Area", self.callbacks["area_delete"], checkable=True
        )
        for button in (
            self.add_connection_btn,
            self.delete_connection_btn,
            self.edit_component_btn,
            self.delete_component_btn,
            self.area_delete_btn,
        ):
            layout.addWidget(button)
        layout.addStretch(1)

        self._apply_toolbar_style(1.0)
        self._sync_responsive_layout()

    def _apply_toolbar_style(self, scale):
        title_font = round(13 * scale)
        button_font = round(11 * scale)
        radius = round(5 * scale)
        pad_v = round(4 * scale)
        pad_h = round(7 * scale)
        self.setStyleSheet(f"""
            HeaderBar {{
                background: #f7f8fb;
                border-bottom: 1px solid #d8ddeb;
            }}
            QLabel#appTitle {{
                background: transparent;
                color: #1f2a44;
                font-size: {title_font}px;
                font-weight: 700;
                padding: 0 4px;
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: {radius}px;
                color: #000000;
                font-size: {button_font}px;
                padding: {pad_v}px {pad_h}px;
            }}
            QToolButton:hover {{
                background: transparent;
                border-color: #8fb0df;
            }}
            QToolButton:pressed {{
                background: transparent;
                border-color: #4878C8;
            }}
            QToolButton:checked {{
                background: transparent;
                border-color: #4878C8;
                color: #000000;
            }}
            QToolButton:disabled {{
                color: #9aa4bd;
            }}
            QToolButton:checked:disabled {{
                background: transparent;
                border-color: #4878C8;
                color: #4a5578;
            }}
            QFrame#toolbarSeparator {{
                background: #d8ddeb;
                min-width: 3px;
                max-width: 3px;
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_responsive_layout()

    def _sync_responsive_layout(self):
        """Summary: Sync responsive layout."""
        width = self.width()
        if self._toolbar_layout is None or width <= 0:
            return
        compact = width < 1180
        very_compact = width < 820
        scale = 0.9 if compact else min(1.45, max(1.0, width / BASE_TOOLBAR_WIDTH))
        scale_key = round(scale, 2)
        if scale_key != self._last_scale_key:
            self._apply_toolbar_style(scale)
            self._last_scale_key = scale_key
        self._toolbar_layout.setContentsMargins(
            6 if very_compact else round(10 * scale),
            4 if compact else round(5 * scale),
            6 if very_compact else round(10 * scale),
            4 if compact else round(5 * scale),
        )
        self._toolbar_layout.setSpacing(3 if compact else round(6 * scale))
        if self._title_label is not None:
            self._title_label.setVisible(not very_compact)
        button_style = (
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if compact
            else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        icon_edge = 20 if compact else round(ICON_SIZE.width() * scale)
        icon_size = QSize(icon_edge, icon_edge)
        button_height = 30 if compact else round(32 * scale)
        self.setMinimumHeight(round(42 * scale))
        for button in self.action_buttons:
            if isinstance(button, QToolButton):
                button.setToolButtonStyle(button_style)
                button.setIconSize(icon_size)
                button.setMinimumHeight(button_height)
                button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def _separator(self):
        separator = QFrame()
        separator.setObjectName("toolbarSeparator")
        separator.setFixedHeight(26)
        return separator

    def _create_action_button(self, label, callback, *icon_names, checkable=False):
        """
        Summary: Create action button.
        Args: callback, checkable, *icon_names
        Returns: Return the computed value.
        """
        button = QToolButton()
        button.setText(label)
        button.setToolTip("")
        names = icon_names or ACTION_ICONS.get(label, (label,))
        button.setIcon(self.icons.icon(*names, fallback_text=label))
        button.setIconSize(ICON_SIZE)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setAutoRaise(False)
        button.setCheckable(checkable)
        button.setMinimumHeight(32)
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        button.clicked.connect(callback)
        self.action_buttons.append(button)
        return button
