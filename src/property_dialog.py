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

        for key, value in vars(component).items():
            property = QLineEdit(str(value))
            self.inputs[key] = property
            form_layout.addRow(key, property)

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