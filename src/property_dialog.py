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
                # if tensor is a vector
                elif dimensions == 1:
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
                # if tensor is a matrix
                elif dimensions == 2:
                    vlayout = QVBoxLayout()
                    input_matrix = []

                    # iterate through the number of rows
                    for i in range(value.shape[0]):
                        # create a box for each row
                        row_layout = QHBoxLayout()
                        row_list = []

                        # iterate through the number of columns
                        for j in range(value.shape[1]):
                            input_line = QLineEdit(str(value[i][j].item()))
                            row_layout.addWidget(input_line)
                            row_list.append(input_line)
                        
                        vlayout.addLayout(row_layout)
                        input_matrix.append(row_list)
                    self.inputs[property] = input_matrix
                    form_layout.addRow(property, vlayout)

        layout.addLayout(form_layout)
        message = QLabel("Would you like to save your changes?")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def accept(self):
        for property, value in self.inputs.items():

            # 2d tensor
            if (isinstance(value, list)) and isinstance(value[0], list):
                updated_list = []
                for row in value:
                    # convert list to floats
                    row_values = []
                    for input_line in row:
                        row_values.append(float(input_line.text()))
                    updated_list.append(row_values)
                setattr(self.component, property, torch.tensor(updated_list))
            
            # 1d tensor
            elif(isinstance(value, list)) and isinstance(value[0], QLineEdit):
                # convert list to floats
                updated_list = []
                for input_line in value:
                    updated_list.append(float(input_line.text()))
                setattr(self.component, property, torch.tensor(updated_list))

            # scalar tensor
            else:
                # get the updated value
                text = value.text()
                # set the new value
                setattr(self.component, property, torch.tensor(float(text)))
        super().accept()

    def getMutableProperties(self):
        mutableProperties = {
            "RTU": ["airflow_max", "airflow_oa_min", "Q_coil_max", "fan_power_per_flow", "cooling_COP", "heating_efficiency"],
            "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
            "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max", "reheat_efficiency"],
            "SolarGains": ["window_area", "window_orientation", "window_shgc", "latitude_deg", "max_solar_irradiance"]
            }
        return mutableProperties