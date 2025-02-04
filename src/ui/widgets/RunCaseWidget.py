from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import get_icon_path
from src.utils import Utils
from src.controllers import RunWidgetController
from src.models import RunWidget_Model


class RunCaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = RunWidget_Model()
        self.controller = RunWidgetController( self.model, self)
        self._setup_shadow()
        self.main_layout = QHBoxLayout(self)
        self.init_ui()

    def init_ui(self):
        self.main_container = QWidget()
        self.main_layout.addWidget(self.main_container)
        self.main_layout.setContentsMargins(4, 8, 8, 4)
        self.main_layout.setSpacing(0)

    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)