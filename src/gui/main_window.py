"""Main application window for project editing and simulation workflows."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QUndoStack
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QSplitter, QStatusBar, QTreeWidget, QVBoxLayout, QWidget

from models.building_model import BuildingModel
from .dialogue_manager import DialogueManager
from .file_manager import FileManager
from .header_bar import HeaderBar
from .icons import IconProvider
from .interactive_canvas import InteractiveCanvas
from .state_manager import StateManager
from .main_window_helpers import COMPONENTS, COMPONENT_ICON_NAMES
from .main_window_plots import MainWindowPlotMixin
from .main_window_project import MainWindowProjectMixin
from .main_window_simulation import MainWindowSimulationMixin
from .main_window_ui import MainWindowUiMixin


class MainWindow(MainWindowUiMixin, MainWindowPlotMixin, MainWindowSimulationMixin, MainWindowProjectMixin, QMainWindow):

    def __init__(self):
        """Summary: Init."""
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1500, 900)
        self.building_model = BuildingModel("Model")
        self.stack = QUndoStack()
        self.canvas = InteractiveCanvas(self.building_model, self.set_dirty, self.stack)
        self.canvas.zoom_changed.connect(self.on_canvas_zoom_changed)
        self.canvas.component_click_handler = self.handle_component_click_action
        self.canvas.canvas_click_handler = self.handle_canvas_click_action
        self.canvas.component_added_handler = self.on_component_added
        self.canvas.area_delete_handler = self.on_area_deleted
        self.canvas.area_delete_confirm_handler = self.confirm_area_delete_items
        self.canvas.connection_deleted_handler = self.on_connection_deleted
        self.file_manager = FileManager(self.building_model)
        self.dialogue_manager = DialogueManager(self, self.building_model)
        self.pending_component_action = None
        self.pending_connection_items = []
        self._simulation_running = False
        self.next_component_id = 1
        self.action_buttons = []
        self._component_palette_buttons = []
        self.add_connection_btn = None
        self.area_delete_btn = None
        self.edit_component_btn = None
        self.delete_component_btn = None
        self.delete_connection_btn = None
        self.mode_status_label = None
        self.zone_value_display = None
        self.zoom_value_display = None
        self.component_list = QTreeWidget()
        self.component_list.setColumnCount(1)
        self.component_list.setHeaderLabels(["Component"])
        self.component_list.setAlternatingRowColors(True)
        self.component_list.setRootIsDecorated(True)
        self.component_list.setIndentation(12)
        self.component_list.header().setStretchLastSection(True)
        self.connection_list = QTreeWidget()
        self.connection_list.setColumnCount(1)
        self.connection_list.setHeaderLabels(["Connection"])
        self.connection_list.setAlternatingRowColors(True)
        self.connection_list.setRootIsDecorated(True)
        self.connection_list.header().setStretchLastSection(True)
        self.assets_path = Path(__file__).resolve().parents[2] / "assets"
        self.icons = IconProvider(self.assets_path)
        central_widget = QWidget()
        self._central_widget = central_widget
        self.setCentralWidget(central_widget)
        self._apply_window_style(1.0)
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        central_widget.setLayout(root_layout)
        self._last_window_style_scale_key = None
        self._main_splitter = None
        self._finish_init(root_layout)

    def _apply_window_style(self, scale):
        tree_font = round(11 * scale)
        status_font = round(11 * scale)
        tab_font = round(11 * scale)
        header_font = round(11 * scale)
        tab_v = round(5 * scale)
        tab_h = round(14 * scale)
        item_v = round(3 * scale)
        item_h = round(4 * scale)
        handle_width = round(5 * scale)
        self._central_widget.setStyleSheet(f"""
            QWidget {{ color: #1e2437; }}
            QTreeWidget {{
                background: #fafbfd; border: 1px solid #d0d4e8;
                border-radius: 5px; color: #2c3454;
                alternate-background-color: #f2f4f9; outline: 0;
                font-size: {tree_font}px;
            }}
            QTreeWidget::item {{ padding: {item_v}px {item_h}px; }}
            QTreeWidget::item:selected {{ background: #dce3f5; color: #1a2240; }}
            QTreeWidget::item:hover:!selected {{ background: #eaedf8; }}
            QHeaderView::section {{
                background: #e2e6f2; color: #3a4468;
                font-weight: 600; font-size: {header_font}px;
                padding: {round(4 * scale)}px {round(6 * scale)}px; border: none;
                border-right: 1px solid #d0d4e8;
                border-bottom: 1px solid #d0d4e8;
            }}
            QSplitter::handle {{ background: #d4d8ea; width: {handle_width}px; }}
            QStatusBar {{
                background: #e8ebf5; color: #3a4468;
                border-top: 1px solid #d0d4e8; font-size: {status_font}px;
            }}
            QStatusBar::item {{ border: none; }}
            QTabWidget::pane {{ border: none; background: #f0f2f8; }}
            QTabBar::tab {{
                background: #e0e4f0; color: #5a6280;
                padding: {tab_v}px {tab_h}px; border: none;
                font-size: {tab_font}px; font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: #f0f2f8; color: #1e2437;
                font-weight: 600; border-top: 2px solid #4878C8;
            }}
            QTabBar::tab:hover:!selected {{ background: #d4d8ec; }}
            QScrollBar:vertical {{
                background: #f0f2f8; width: 8px; border-radius: 4px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #c0c6dc; border-radius: 4px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #a0aac8; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: #f0f2f8; height: 8px; border-radius: 4px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: #c0c6dc; border-radius: 4px; min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: #a0aac8; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """)
        
    def _sync_window_style_scale(self):
        if self.width() < 1180:
            scale = 0.95
        else:
            screen = self.screen()
            screen_width = screen.availableGeometry().width() if screen is not None else self.width()
            width_ratio = self.width() / max(1, screen_width)
            scale = min(1.18, max(1.0, 0.96 + width_ratio * 0.24))
        scale_key = round(scale, 2)
        if scale_key == getattr(self, "_last_window_style_scale_key", None):
            return
        self._last_window_style_scale_key = scale_key
        self._apply_window_style(scale)

    def _finish_init(self, root_layout):
        self._last_results = None
        self._last_t_start = 0
        self._multi_charts: list = []
        self._plot_tabs = None
        self._plot_results_shown = None
        self._left_tabs = None
        self._settings_layout = None
        self._var_list = None
        self._plot_selected_by_group: dict = {}
        self._plot_order_by_group: dict = {}
        self._sim_thread = None
        self._sim_stop_requested = False
        self._sim_reset_requested = False
        self._sim_current_step = 0
        self._sim_total_steps = 0
        self._sim_resume_results = None
        self._sim_resume_step = 0
        self._run_btn = None
        self._stop_btn = None
        self._sim_progress_bar = None
        self._plot_progress_bar = None
        self._setup_issue_list = None
        self._input_data_label = None
        self._control_policy_inputs = {}
        self._control_policy_toggle_btn = None
        self._control_policy_toggle_label = None
        self._component_palette_header = None
        self._last_sidebar_scale_key = None
        self._run_btn_run_style = (
            "QPushButton { background: #4a7fc1; color: #fff; border: none;"
            " border-radius: 5px; padding: 8px 0; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background: #5a8fd1; }"
            "QPushButton:pressed { background: #3a6fb1; }"
        )
        self._run_btn_stop_style = (
            "QPushButton { background: #c04040; color: #fff; border: none;"
            " border-radius: 5px; padding: 8px 0; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background: #d05050; }"
            "QPushButton:pressed { background: #a03030; }"
            "QPushButton:disabled { background: #d4d8e5; color: #ffffff; }"
        )
        self._run_btn_resume_style = (
            "QPushButton { background: #2f9d68; color: #fff; border: none;"
            " border-radius: 5px; padding: 8px 0; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background: #38ad75; }"
            "QPushButton:pressed { background: #287f57; }"
        )
        self.header_bar = HeaderBar(
            self.assets_path,
            COMPONENTS,
            COMPONENT_ICON_NAMES,
            callbacks = {
                "save_as": self.save_as_layout,
                "save": self.save_layout,
                "new": self.new_page,
                "load": self.load_layout,
                "undo": self.stack.undo,
                "redo": self.stack.redo,
                "add_connection": self.add_connection,
                "edit_component": self.arm_edit_component,
                "delete_component": self.arm_delete_component,
                "delete_connection": self.arm_delete_connection,
                "area_delete": self.arm_area_delete,
            },
        )
        self.action_buttons = self.header_bar.action_buttons
        self.add_connection_btn = self.header_bar.add_connection_btn
        self.edit_component_btn = self.header_bar.edit_component_btn
        self.delete_component_btn = self.header_bar.delete_component_btn
        self.delete_connection_btn = self.header_bar.delete_connection_btn
        self.area_delete_btn = self.header_bar.area_delete_btn
        self.undo_btn = self.header_bar.undo_btn
        self.redo_btn = self.header_bar.redo_btn
        root_layout.addWidget(self.header_bar)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter = splitter
        splitter.addWidget(self.create_left_panel())
        splitter.addWidget(self.create_right_panel())
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(5)
        splitter.setSizes([286, 1214])
        root_layout.addWidget(splitter)
        self.state_manager = StateManager(
            self.building_model,
            self.canvas,
            self.component_list,
            self.connection_list,
            self.zone_value_display,
        )
        self.state_manager.set_zone_value_display(self.zone_value_display)
        self.setStatusBar(QStatusBar())
        self.setup_mode_status_label()
        self.set_component_action_mode(None)
        self.refresh_component_list()
        self.file_path = None
        self.is_dirty = False
        self.last_dir = None
        save_action = QAction(self)
        save_action.setShortcut("Ctrl+S")
        save_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        save_action.triggered.connect(self.save_layout)
        self.addAction(save_action)


        self.undo_action = self.stack.createUndoAction(self, "Undo")
        self.undo_action.setObjectName("undo_action")
        self.undo_action.setShortcuts([QKeySequence("Ctrl+Z"), QKeySequence("Meta+Z")])
        self.undo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        self.redo_action = self.stack.createRedoAction(self, "Redo")
        self.redo_action.setObjectName("redo_action")
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Meta+Y")])
        self.redo_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        self.addAction(self.undo_action)
        self.addAction(self.redo_action)
        self.stack.canUndoChanged.connect(self._set_undo_enabled)
        self.stack.canRedoChanged.connect(self._set_redo_enabled)
        self.stack.indexChanged.connect(self._on_undo_stack_changed)
        self._set_undo_enabled(self.stack.canUndo())
        self._set_redo_enabled(self.stack.canRedo())

    def _on_undo_stack_changed(self):
        try:
            self._invalidate_plots()
            self.refresh_component_list()
            self.refresh_connection_list()
            self._sync_action_button_availability()
        except RuntimeError:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_responsive_ui_scale()
