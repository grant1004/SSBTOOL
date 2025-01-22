from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class SelectCaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: white;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4,8,8,4)
        label = QLabel("Select Case Widget")
        label.setStyleSheet("color: black; font-size: 20px; font-weight: semibold;")
        label.setContentsMargins(16, 0, 0, 0)
        layout.addWidget(label)