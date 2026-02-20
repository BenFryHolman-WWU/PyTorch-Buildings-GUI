import sys
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton, QDialogButtonBox, QVBoxLayout, QLabel, QFormLayout, QLineEdit
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
            cur_value = getattr(component, property)
            input_line = QLineEdit(str(cur_value))
            self.inputs[property] = input_line
            form_layout.addRow(property, input_line)

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