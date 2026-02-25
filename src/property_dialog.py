import sys
import torch
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, QFormLayout, QLineEdit

class PropertyDialog(QDialog):
    "pop up window to edit component properties"
    def __init__(self, component, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Properties")
        self.component = component
        self.inputs = {}
        

        QBtn = (
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        component_type = type(component).__name__
        mutablePropertyDict = self.getMutableProperties()
        mutableProperties = mutablePropertyDict[component_type]

        for property in mutableProperties:
            value = getattr(component, property)
            # every value should be a tensor but this is a check just in case
            if isinstance(value, torch.Tensor):
                dimensions = value.ndim
                # if tensor is a scalar
                if dimensions == 0:
                    # since value in this case is the tensor, value.item is the float value of the tensor
                    input_line = QLineEdit(str(value.item()))
                    # save to inputs
                    self.inputs[property] = input_line
                    form_layout.addRow(property, input_line)
                else:
                    # make a hbox layout for multiple boxes
                    hlayout = QHBoxLayout()
                    # list for the inputs list
                    line_list = []
                    # for every value in the dimensions, add a box for it
                    for i, v in enumerate(value):
                        input_line = QLineEdit(str(v.item()))
                        hlayout.addWidget(input_line)
                        line_list.append(input_line)
                    self.inputs[property] = line_list
                    form_layout.addRow(property, hlayout)

        layout.addLayout(form_layout)
        message = QLabel("Would you like to save your changes?")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def accept(self):
        for property, value in self.inputs.items():
            #get the updated value
            text = value.text()
            #get the original value of the property
            attr = getattr(self.component, property)
            #cast the new value to the same type of the original
            casted_value = type(attr)(text)
            #set the new values
            setattr(self.component, property, casted_value)
        super().accept()

    def getMutableProperties(self):
        mutableProperties = {
            "RTU": ["airflow_max", "airflow_oa_min", "Q_coil_max", "fan_power_per_flow", "cooling_COP", "heating_efficiency"],
            "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
            "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max", "reheat_efficiency"],
            "SolarGains": ["window_area", "window_orientation", "window_shgc", "latitude_deg", "max_solar_irradiance"]
            }
        return mutableProperties