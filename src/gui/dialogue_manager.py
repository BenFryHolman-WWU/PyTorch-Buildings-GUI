from pathlib import Path
import torch
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QHBoxLayout
from PyQt6.QtCore import Qt


COMPONENT_MUTABLE_PROPERTIES = {
    "RTU": ["airflow_max", "airflow_oa_min", "Q_coil_max", "fan_power_per_flow", "cooling_COP", "heating_efficiency"],
    "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
    "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max", "reheat_efficiency"],
    "SolarGains": ["window_area", "window_orientation", "window_shgc", "latitude_deg", "max_solar_irradiance"],
}

class SetTimeDialog(QDialog):
    def __init__(self, building_model, parent = None):
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
        for parameter, value in self.inputs.items():
            setattr(self.building_model, parameter, float(value.text()))
        super().accept()

class PropertyDialog(QDialog):
    def __init__(self, component, parent = None):
        super().__init__(parent)
        self.setWindowTitle("Properties")
        self.setMinimumWidth(820)
        self.resize(920, 460)
        self.setSizeGripEnabled(True)
        self.component = component
        self.inputs = {}
        buttons = QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        component_type = type(component).__name__
        mutable_properties = COMPONENT_MUTABLE_PROPERTIES.get(component_type, [])
        for prop in mutable_properties:
            value = getattr(component, prop)
            if isinstance(value, torch.Tensor):
                dimensions = value.ndim
                if dimensions == 0:
                    input_line = QLineEdit(str(value.item()))
                    self.inputs[prop] = input_line
                    form_layout.addRow(prop, input_line)
                elif dimensions == 1:
                    h_layout = QHBoxLayout()
                    line_list = []
                    for tensor_value in value:
                        input_line = QLineEdit(str(tensor_value.item()))
                        h_layout.addWidget(input_line)
                        line_list.append(input_line)
                    self.inputs[prop] = line_list
                    form_layout.addRow(prop, h_layout)
                elif dimensions == 2:
                    v_layout = QVBoxLayout()
                    input_matrix = []
                    for i in range(value.shape[0]):
                        row_layout = QHBoxLayout()
                        row_list = []
                        for j in range(value.shape[1]):
                            input_line = QLineEdit(str(value[i][j].item()))
                            row_layout.addWidget(input_line)
                            row_list.append(input_line)
                        v_layout.addLayout(row_layout)
                        input_matrix.append(row_list)
                    self.inputs[prop] = input_matrix
                    form_layout.addRow(prop, v_layout)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Would you like to save your changes?"))
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def accept(self):
        for prop, value in self.inputs.items():
            if isinstance(value, list) and value and isinstance(value[0], list):
                updated_list = []
                for row in value:
                    updated_list.append([float(input_line.text()) for input_line in row])
                setattr(self.component, prop, torch.tensor(updated_list))
            elif isinstance(value, list) and value and isinstance(value[0], QLineEdit):
                setattr(self.component, prop, torch.tensor([float(input_line.text()) for input_line in value]))
            else:
                setattr(self.component, prop, torch.tensor(float(value.text())))
        super().accept()


class DialogueManager:
    def __init__(self, parent, building_model):
        self.parent = parent
        self.building_model = building_model
    def show_info(self, title, message):
        QMessageBox.information(self.parent, title, message)
    def open_set_time_dialog(self):
        SetTimeDialog(self.building_model, self.parent).exec()
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

