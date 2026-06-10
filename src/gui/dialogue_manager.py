"""Dialogs and file prompts for the PyTorch Buildings GUI."""

from pathlib import Path
import torch
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QHBoxLayout, QWidget, QSizePolicy, QLayout, QComboBox
from PyQt6.QtCore import Qt


COMPONENT_MUTABLE_PROPERTIES = {
    "RTU": ["airflow_max", "airflow_oa_min", "Q_coil_max", "fan_power_per_flow", "cooling_COP", "heating_efficiency"],
    "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
    "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max", "reheat_efficiency"],
    "SolarGains": ["window_area", "window_orientation", "window_shgc", "latitude_deg", "max_solar_irradiance"],
    "ControlPolicy": ["tu_T_supply_setpoint", "rtu_supply_airflow_setpoint"]
}


class SetTimeDialog(QDialog):

    def __init__(self, building_model, parent = None):
        """
        Summary: Init.
        Args: building_model
        """
        super().__init__(parent)
        self.setWindowTitle("Set time in seconds")
        self.inputs = {}
        self.building_model = building_model
        buttons = QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        start_input = QLineEdit(str(self.building_model.t_start))
        form_layout.addRow("Start time", start_input)
        self.inputs["t_start"] = start_input
        duration_input = QLineEdit(str(self.building_model.t_duration))
        form_layout.addRow("Duration", duration_input)
        self.inputs["t_duration"] = duration_input
        dt_input = QLineEdit(str(self.building_model.dt))
        form_layout.addRow("Time step", dt_input)
        self.inputs["dt"] = dt_input
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Would you like to save your changes?"))
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


    def accept(self):
        try:
            values = {parameter: float(value.text()) for parameter, value in self.inputs.items()}
        except ValueError:
            show_error_dialog(self, "Invalid Time Settings", "Enter a valid number for each time setting.")
            return
        if values["t_start"] < 0 or values["t_duration"] <= 0 or values["dt"] <= 0:
            show_error_dialog(self, "Invalid Time Settings", "Start time cannot be negative, and duration and time step must be positive.")
            return
        if values["dt"] > values["t_duration"]:
            show_error_dialog(self, "Invalid Time Settings", "The time step cannot exceed the simulation duration.")
            return
        for parameter, value in values.items():
            setattr(self.building_model, parameter, value)
        super().accept()


class PropertyDialog(QDialog):

    def __init__(self, component, n_zones = 1, parent = None):
        """
        Summary: Init.
        Args: component, n_zones
        Returns: Return the computed value.
        """
        super().__init__(parent)
        component_type = type(component).__name__
        self.setWindowTitle(f"Edit {component_type}")
        self.setMinimumWidth(0)
        self.setSizeGripEnabled(False)
        self.component = component
        self.inputs = {}
        buttons = QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.setStyleSheet("""
            QDialog {
                background: #f0f2f8;
                color: #2c3454;
            }
            QLabel#dialogTitle {
                color: #1f2a44;
                font-size: 14px;
                font-weight: 700;
                padding-bottom: 2px;
            }
            QLabel#dialogSubtitle {
                color: #6a7695;
                font-size: 11px;
                padding-bottom: 6px;
            }
            QLabel {
                color: #3a4468;
                font-size: 11px;
                background: transparent;
            }
            QLineEdit {
                background: #ffffff;
                border: 1px solid #c8ccdc;
                border-radius: 4px;
                padding: 3px 5px;
                color: #2c3454;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #4a7fc1;
            }
            QWidget#propertyPanel {
                background: #f8f9fc;
                border: 1px solid #d0d4e8;
                border-radius: 6px;
            }
            QDialogButtonBox QPushButton {
                background: #fafbfd;
                color: #3a4468;
                border: 1px solid #c4c9dc;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QDialogButtonBox QPushButton:hover {
                background: #eaecf5;
                border-color: #a8b0cc;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        title = QLabel(f"Edit {component_type}")
        title.setObjectName("dialogTitle")
        subtitle = QLabel("Adjust simulation properties.")
        subtitle.setObjectName("dialogSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        panel = QWidget()
        panel.setObjectName("propertyPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        form_layout = QFormLayout()
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setHorizontalSpacing(6)
        form_layout.setVerticalSpacing(4)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        def _number_input(value, width):
            input_line = QLineEdit(str(value))
            input_line.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            input_line.setMinimumWidth(width)
            input_line.setMaximumWidth(width)
            input_line.setCursorPosition(0)
            return input_line

        mutable_properties = COMPONENT_MUTABLE_PROPERTIES.get(component_type, [])
        for prop in mutable_properties:
            value = getattr(component, prop)
            if isinstance(value, torch.Tensor):
                dimensions = value.ndim
                if dimensions == 0:
                    input_line = _number_input(value.item(), 112)
                    self.inputs[prop] = input_line
                    form_layout.addRow(prop, input_line)
                elif dimensions == 1:
                    h_layout = QHBoxLayout()
                    h_layout.setSpacing(4)
                    line_list = []
                    for i in range(n_zones):
                        val = value[i].item() if i < value.shape[0] else value[-1].item()
                        input_line = _number_input(val, 92)
                        h_layout.addWidget(input_line)
                        line_list.append(input_line)
                    self.inputs[prop] = line_list
                    form_layout.addRow(prop, h_layout)
                elif dimensions == 2:
                    v_layout = QVBoxLayout()
                    v_layout.setSpacing(4)
                    input_matrix = []
                    for i in range(n_zones):
                        row_layout = QHBoxLayout()
                        row_layout.setSpacing(4)
                        row_list = []
                        for j in range(n_zones):
                            if i < value.shape[0] and j < value.shape[1]:
                                val = value[i][j].item()
                            else:
                                val = 1.0 if i == j else 0.0
                            input_line = _number_input(val, 80)
                            row_layout.addWidget(input_line)
                            row_list.append(input_line)
                        v_layout.addLayout(row_layout)
                        input_matrix.append(row_list)
                    self.inputs[prop] = input_matrix
                    form_layout.addRow(prop, v_layout)
        panel.setLayout(form_layout)
        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(8)
        layout.addWidget(self.buttonBox, 0, Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)
        self.adjustSize()


    def accept(self):
        """Summary: Accept."""
        try:
            updated_values = {}
            for prop, value in self.inputs.items():
                if isinstance(value, list) and value and isinstance(value[0], list):
                    updated_values[prop] = torch.tensor([
                        [float(input_line.text()) for input_line in row]
                        for row in value
                    ])
                elif isinstance(value, list) and value and isinstance(value[0], QLineEdit):
                    updated_values[prop] = torch.tensor([float(input_line.text()) for input_line in value])
                else:
                    updated_values[prop] = torch.tensor(float(value.text()))
        except ValueError:
            show_error_dialog(self, "Invalid Component Value", "Enter valid numeric values for every component property.")
            return
        for prop, value in updated_values.items():
            setattr(self.component, prop, value)
        super().accept()


class ConfirmDeleteDialog(QDialog):

    def __init__(self, labels, parent=None):
        """Summary: Init."""
        super().__init__(parent)
        self.setWindowTitle("Confirm Area Delete")
        self.setMinimumWidth(0)
        self.setSizeGripEnabled(False)
        self.setStyleSheet("""
            QDialog {
                background: #f0f2f8;
                color: #2c3454;
            }
            QLabel#dialogTitle {
                color: #1f2a44;
                font-size: 14px;
                font-weight: 700;
                padding-bottom: 2px;
            }
            QLabel#dialogSubtitle {
                color: #6a7695;
                font-size: 11px;
                padding-bottom: 6px;
            }
            QLabel {
                color: #3a4468;
                font-size: 11px;
                background: transparent;
            }
            QWidget#deletePanel {
                background: #f8f9fc;
                border: 1px solid #d0d4e8;
                border-radius: 6px;
            }
            QLabel#deleteItem {
                color: #2c3454;
                padding: 1px 0;
            }
            QDialogButtonBox QPushButton {
                background: #fafbfd;
                color: #3a4468;
                border: 1px solid #c4c9dc;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QDialogButtonBox QPushButton:hover {
                background: #eaecf5;
                border-color: #a8b0cc;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        title = QLabel("Delete Selected Components")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(f"Delete {len(labels)} component(s)?")
        subtitle.setObjectName("dialogSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        panel = QWidget()
        panel.setObjectName("deletePanel")
        panel.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(3)
        for label in labels:
            item_label = QLabel(f"- {label}")
            item_label.setObjectName("deleteItem")
            panel_layout.addWidget(item_label)
        layout.addWidget(panel, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(8)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("Delete")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 0, Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)
        self.adjustSize()


_UNSAVED_STYLESHEET = """
    QDialog {
        background: #f0f2f8;
        color: #2c3454;
    }
    QLabel#dialogTitle {
        color: #1f2a44;
        font-size: 14px;
        font-weight: 700;
        padding-bottom: 2px;
    }
    QLabel#dialogSubtitle {
        color: #6a7695;
        font-size: 11px;
        padding-bottom: 4px;
    }
    QLabel#dialogWarning {
        color: #2c3454;
        font-size: 11px;
        font-weight: 700;
        padding-bottom: 6px;
        background: transparent;
    }
    QLabel {
        color: #3a4468;
        font-size: 11px;
        background: transparent;
    }
    QDialogButtonBox QPushButton {
        background: #fafbfd;
        color: #3a4468;
        border: 1px solid #c4c9dc;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: 600;
    }
    QDialogButtonBox QPushButton:hover {
        background: #eaecf5;
        border-color: #a8b0cc;
    }
"""


def _make_unsaved_dialog(parent, window_title, title_text, subtitle_text, ok_text, show_warning):
    """
    Summary: Make unsaved dialog.
    Args: window_title, title_text, subtitle_text, ok_text, show_warning
    Returns: Return the computed value.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(window_title)
    dialog.setMinimumWidth(0)
    dialog.setSizeGripEnabled(False)
    dialog.setStyleSheet(_UNSAVED_STYLESHEET)
    layout = QVBoxLayout()
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    title = QLabel(title_text)
    title.setObjectName("dialogTitle")
    subtitle = QLabel(subtitle_text)
    subtitle.setObjectName("dialogSubtitle")
    layout.addWidget(title)
    layout.addWidget(subtitle)

    if show_warning:
        warn = QLabel("Unsaved changes will be lost.")
        warn.setObjectName("dialogWarning")
        layout.addWidget(warn)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    if ok_button is not None:
        ok_button.setText(ok_text)
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    if cancel_button is not None:
        cancel_button.setText("Cancel")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons, 0, Qt.AlignmentFlag.AlignHCenter)
    dialog.setLayout(layout)
    dialog.adjustSize()
    return dialog


def show_error_dialog(parent, title, message):
    """Show a styled, user-facing error without exposing a Python traceback."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(0)
    dialog.setSizeGripEnabled(False)
    dialog.setStyleSheet(_UNSAVED_STYLESHEET)
    layout = QVBoxLayout()
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(6)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
    title_label = QLabel(title)
    title_label.setObjectName("dialogTitle")
    message_label = QLabel(str(message))
    message_label.setObjectName("dialogSubtitle")
    message_label.setWordWrap(True)
    message_label.setMaximumWidth(520)
    layout.addWidget(title_label)
    layout.addWidget(message_label)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons, 0, Qt.AlignmentFlag.AlignHCenter)
    dialog.setLayout(layout)
    dialog.adjustSize()
    dialog.exec()


class ConfirmLoadProjectDialog(QDialog):

    def __new__(cls, parent=None):
        return _make_unsaved_dialog(
            parent,
            window_title="Load Project",
            title_text="Load Project",
            subtitle_text="This will replace the current project.",
            ok_text="Load Anyway",
            show_warning=True,
        )


class ConfirmNewProjectDialog(QDialog):

    def __new__(cls, has_unsaved_changes, parent=None):
        return _make_unsaved_dialog(
            parent,
            window_title="New Project",
            title_text="New Project",
            subtitle_text="This will clear the current project.",
            ok_text="Create New",
            show_warning=has_unsaved_changes,
        )


class ConfirmExitDialog(QDialog):

    def __new__(cls, parent=None):
        return _make_unsaved_dialog(
            parent,
            window_title="Exit",
            title_text="Exit",
            subtitle_text="Are you sure you want to exit?",
            ok_text="Exit Anyway",
            show_warning=True,
        )


class ConnectionMappingDialog(QDialog):

    def __init__(self, mappings, parent=None):
        """
        Summary: Init.
        Args: mappings
        """
        super().__init__(parent)
        self.setWindowTitle("Select Connection")
        self.mappings = list(mappings)
        self.selected_mappings = list(mappings)
        self.setStyleSheet("""
            QDialog {
                background: #f0f2f8;
                color: #2c3454;
            }
            QLabel#dialogTitle {
                color: #1f2a44;
                font-size: 14px;
                font-weight: 700;
                padding-bottom: 2px;
            }
            QLabel#dialogSubtitle {
                color: #6a7695;
                font-size: 11px;
                padding-bottom: 6px;
            }
            QComboBox {
                background: #ffffff;
                color: #2c3454;
                border: 1px solid #c4c9dc;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 300px;
            }
            QDialogButtonBox QPushButton {
                background: #fafbfd;
                color: #3a4468;
                border: 1px solid #c4c9dc;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QDialogButtonBox QPushButton:hover {
                background: #eaecf5;
                border-color: #a8b0cc;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        title = QLabel("Select Connection")
        title.setObjectName("dialogTitle")
        subtitle = QLabel("Default uses all recommended signal mappings.")
        subtitle.setObjectName("dialogSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.mapping_combo = QComboBox()
        self.mapping_combo.addItem("Default: all recommended mappings", list(self.mappings))
        for src_key, dst_key in self.mappings:
            self.mapping_combo.addItem(f"{src_key} -> {dst_key}", [(src_key, dst_key)])
        layout.addWidget(self.mapping_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 0, Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


    def accept(self):
        self.selected_mappings = list(self.mapping_combo.currentData() or self.mappings)
        super().accept()


class DialogueManager:

    def __init__(self, parent, building_model):
        self.parent = parent
        self.building_model = building_model


    def show_info(self, title, message):
        QMessageBox.information(self.parent, title, message)

    def show_error(self, title, message):
        show_error_dialog(self.parent, title, message)


    def open_set_time_dialog(self):
        SetTimeDialog(self.building_model, self.parent).exec()


    def confirm_load_project(self):
        return ConfirmLoadProjectDialog(self.parent).exec() == QDialog.DialogCode.Accepted


    def confirm_exit(self):
        return ConfirmExitDialog(self.parent).exec() == QDialog.DialogCode.Accepted


    def confirm_new_project(self, has_unsaved_changes):
        return ConfirmNewProjectDialog(has_unsaved_changes, self.parent).exec() == QDialog.DialogCode.Accepted


    def confirm_delete_items(self, labels):
        if not labels:
            return False
        return ConfirmDeleteDialog(labels, self.parent).exec() == QDialog.DialogCode.Accepted


    def prompt_connection_mappings(self, mappings):
        if len(mappings) <= 1:
            return list(mappings)
        dialog = ConnectionMappingDialog(mappings, self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_mappings


    def prompt_load_layout_path(self, start_dir):
        load_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Layout",
            str(start_dir if Path(start_dir).exists() else Path.cwd()),
            "JSON Files (*.json)",
        )
        if not load_path:
            return None
        return load_path


    def prompt_input_data_path(self, start_dir):
        load_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Input Data",
            str(start_dir if Path(start_dir).exists() else Path.cwd()),
            "Data Files (*.csv *.db *.sqlite *.sqlite3);;CSV Files (*.csv);;Database Files (*.db *.sqlite *.sqlite3);;All Files (*)",
        )
        if not load_path:
            return None
        return load_path

    def prompt_save_layout_path(self, start_dir):
        """
        Summary: Prompt save layout path.
        Args: start_dir
        Returns: Return the computed value.
        """
        save_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Layout",
            str(start_dir if Path(start_dir).exists() else Path.cwd()),
            "JSON Files (*.json)",
        )
        if not save_path:
            return None
        save_path = str(Path(save_path).with_suffix(".json"))
        return save_path
