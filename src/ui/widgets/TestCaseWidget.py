from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class TestCaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: red;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8,8,4,8)
        label = QLabel("Test Case Widget")
        label.setStyleSheet("color: black; font-size: 20px; font-weight: semibold;")
        label.setContentsMargins(16, 0, 0, 0)
        layout.addWidget(label)