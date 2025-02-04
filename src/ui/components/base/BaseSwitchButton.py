# components/base/BaseSwitchButton.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class BaseSwitchButton(QWidget):
    """基礎切換按鈕類"""
    switched = Signal(str)  # 發送切換後的模式

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_mode = self.config.get('default_mode', '')
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        self.setFixedHeight(60)

        # 創建容器
        self.container = QFrame()
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(4, 4, 4, 4)

        # 創建按鈕
        self.buttons = {}
        for mode_id, mode_config in self.config.get('modes', {}).items():
            btn = QPushButton(mode_config.get('text', ''))
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, m=mode_id: self._handle_switch(m))
            self.buttons[mode_id] = btn
            container_layout.addWidget(btn)

        layout.addWidget(self.container)
        self._update_styles()

    def _handle_switch(self, mode_id):
        if mode_id != self.current_mode:
            self.current_mode = mode_id
            self._update_styles()
            self.switched.emit(mode_id)

    def _update_styles(self):
        self.container.setStyleSheet("""
            QFrame {
                background-color: #EEEEEE;
                border-radius: 20px;
            }
        """)

        for mode_id, btn in self.buttons.items():
            btn.setStyleSheet(self._get_button_style(mode_id == self.current_mode))

    def _get_button_style(self, is_active):
        return """
            QPushButton {
                border: none;
                border-radius: 16px;
                padding: 8px 16px;
                font-size: 14px;
                background-color: %s;
                color: %s;
                font-weight: %s;
            }
        """ % (
            '#006C4D' if is_active else 'transparent',
            'white' if is_active else '#666666',
            'bold' if is_active else 'normal'
        )
