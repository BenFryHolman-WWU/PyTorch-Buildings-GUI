import torch
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFormLayout,
    QLineEdit,
)

class PropertyDialog(QDialog):
    def __init__(self, component, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Properties")
        self.component = component
        self.inputs = {}
        buttons = (QDialogButtonBox.StandardButton.Save or QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        component_type = type(component).__name__
        mutable_property_dict = self.getMutableProperties()
        mutable_properties = mutable_property_dict.get(component_type, [])
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
                    row_values = [float(input_line.text()) for input_line in row]
                    updated_list.append(row_values)
                setattr(self.component, prop, torch.tensor(updated_list))
            elif isinstance(value, list) and value and isinstance(value[0], QLineEdit):
                updated_list = [float(input_line.text()) for input_line in value]
                setattr(self.component, prop, torch.tensor(updated_list))
            else:
                setattr(self.component, prop, torch.tensor(float(value.text())))
        super().accept()

    def getMutableProperties(self):
        return {
            "RTU": [
                "airflow_max",
                "airflow_oa_min",
                "Q_coil_max",
                "fan_power_per_flow",
                "cooling_COP",
                "heating_efficiency",
            ],
            "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
            "VAVBox": [
                "airflow_min",
                "airflow_max",
                "control_gain",
                "Q_reheat_max",
                "reheat_efficiency",
            ],
            "SolarGains": [
                "window_area",
                "window_orientation",
                "window_shgc",
                "latitude_deg",
                "max_solar_irradiance",
            ],
        }
