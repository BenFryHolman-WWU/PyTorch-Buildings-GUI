from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QHBoxLayout, QTabWidget, QToolButton, QWidget, QSizePolicy
from .interactive_canvas import DragButton


ICON_WIDTH = 48
ICON_HEIGHT = 32


class HeaderBar(QWidget):
    """Manages the ribbon toolbar with action and component buttons."""
    
    def __init__(self, assets_path, components, component_icon_names, callbacks):
        """Initialize the header bar. Args: assets_path (Path), components (list), component_icon_names (dict), callbacks (dict)."""
        super().__init__()
        self.assets_path = Path(assets_path)
        self.components = components
        self.component_icon_names = component_icon_names
        self.callbacks = callbacks
        self.action_buttons = []
        self.add_connection_btn = None
        self.edit_component_btn = None
        self.delete_component_btn = None
        self.area_delete_btn = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tabs = self._create_ribbon_tabs()
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(tabs, 1)

    def _placeholder_icon(self):
        """Generate a checkered placeholder icon. Returns: QIcon."""
        width = ICON_WIDTH
        height = ICON_HEIGHT
        tile = 8
        pixmap = QPixmap(width, height)
        painter = QPainter(pixmap)
        white = QColor(255, 255, 255)
        black = QColor(0, 0, 0)
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                use_white = ((x // tile) + (y // tile)) % 2 == 0
                painter.fillRect(x, y, tile, tile, white if use_white else black)
        painter.end()
        return QIcon(pixmap)

    def _load_action_icon(self, *icon_names):
        """Load action icon from assets or return placeholder."""
        
        # 1. Try specific icon names first (e.g., save.png)
        for name in icon_names:
            icon_path = self.assets_path / f"{name}.png"
            if icon_path.exists():
                return QIcon(str(icon_path))

        # 2. Fallback: WIP icon
        wip_path = self.assets_path / "WIP_ICON.png"
        if wip_path.exists():
            return QIcon(str(wip_path))

        # 3. Final fallback
        return self._placeholder_icon()

    def _create_action_button(self, label, callback, *icon_names):
        """Create an action button with icon and callback. Args: label (str), callback (function), *icon_names. Returns: QToolButton."""
        button = QToolButton()
        button.setText(label)
        button.setIcon(self._load_action_icon(*icon_names, label.lower().replace(" ", "_")))
        button.setIconSize(QSize(ICON_WIDTH, ICON_HEIGHT))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setAutoRaise(True)
        button.setMinimumSize(92, 66)
        button.setStyleSheet("""QToolButton { border: none; background: transparent; padding: 2px 4px; color: #000000; } QToolButton:hover { background-color: rgba(0, 0, 0, 0.05); border-radius: 6px; } QToolButton:pressed { background-color: rgba(0, 0, 0, 0.09); border-radius: 6px; } QToolButton:checked { background-color: rgba(0, 0, 0, 0.12); border-radius: 6px; }""")
        button.clicked.connect(callback)
        self.action_buttons.append(button)
        return button

    def _create_component_drag_button(self, label, component_name, *icon_names):
        """Create a draggable component button. Args: label (str), component_name (str), *icon_names. Returns: DragButton."""
        button = DragButton(label, component_name)
        button.setIcon(self._load_action_icon(*icon_names, label.lower().replace(" ", "_")))
        button.setIconSize(QSize(ICON_WIDTH, ICON_HEIGHT))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setAutoRaise(True)
        button.setMinimumSize(92, 66)
        button.setStyleSheet("""QToolButton { border: none; background: transparent; padding: 2px 4px; color: #000000; } QToolButton:hover { background-color: rgba(0, 0, 0, 0.05); border-radius: 6px; } QToolButton:pressed { background-color: rgba(0, 0, 0, 0.09); border-radius: 6px; }""")
        self.action_buttons.append(button)
        return button

    def _create_ribbon_tabs(self):
        """Create the ribbon tab widget with Home, Components, and Tools tabs. Returns: QTabWidget."""
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setMovable(False)
        tabs.tabBar().setExpanding(True)
        tabs.addTab(self._create_home_tab(), "Home")
        tabs.addTab(self._create_components_tab(), "Components")
        tabs.addTab(self._create_tools_tab(), "Tools")
        return tabs

    def _create_home_tab(self):
        """Create the Home tab with Save, Load, Run Simulation, and Set Time buttons. Returns: QWidget."""
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        save_btn = self._create_action_button("Save", self.callbacks["save"], "save_asset", "save")
        load_btn = self._create_action_button("Load", self.callbacks["load"], "load_asset", "load")
        run_btn = self._create_action_button("Run Simulation", self.callbacks["run"], "run_simulation_asset", "run_simulation", "run")
        set_time_btn = self._create_action_button("Set Time", self.callbacks["set_time"], "time_asset", "set_time", "time")
        layout.addWidget(save_btn)
        layout.addWidget(load_btn)
        layout.addWidget(run_btn)
        layout.addWidget(set_time_btn)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _create_components_tab(self):
        """Create the Components tab with draggable component buttons. Returns: QWidget."""
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        for cls in self.components:
            icon_names = self.component_icon_names.get(cls.__name__, [f"add_{cls.__name__.lower()}_asset", cls.__name__.lower()])
            button = self._create_component_drag_button(cls.__name__, cls.__name__, *icon_names, cls.__name__.lower())
            layout.addWidget(button)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _create_tools_tab(self):
        """Create the Tools tab with connection, edit, delete, and area delete buttons. Returns: QWidget."""
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        self.add_connection_btn = self._create_action_button("Add Connection", self.callbacks["add_connection"], "add_connection_asset", "add_connection", "connection")
        self.add_connection_btn.setCheckable(True)
        layout.addWidget(self.add_connection_btn)
        self.edit_component_btn = self._create_action_button("Edit Component", self.callbacks["edit_component"], "edit_component_asset", "edit_component", "edit")
        self.edit_component_btn.setCheckable(True)
        layout.addWidget(self.edit_component_btn)
        self.delete_component_btn = self._create_action_button("Delete Component", self.callbacks["delete_component"], "delete_component_asset", "delete_component", "delete")
        self.delete_component_btn.setCheckable(True)
        layout.addWidget(self.delete_component_btn)
        self.area_delete_btn = self._create_action_button("Delete Area", self.callbacks["area_delete"], "delete_area_asset", "delete_area", "delete")
        self.area_delete_btn.setCheckable(True)
        layout.addWidget(self.area_delete_btn)
        layout.addStretch()
        tab.setLayout(layout)
        return tab
