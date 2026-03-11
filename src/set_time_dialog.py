from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, QFormLayout, QLineEdit

class SetTimeDialog(QDialog):
    def __init__(self, building_model, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Set time in seconds")
        self.inputs = {}
        self.building_model = building_model

        QBtn = (
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
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
        message = QLabel("Would you like to save your changes?")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def accept(self):
        for parameter, value in self.inputs.items():
            text = value.text()
            setattr(self.building_model, parameter, float(text))
        super().accept()