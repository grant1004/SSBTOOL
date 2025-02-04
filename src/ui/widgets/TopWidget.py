from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.models import *
from src.ui.components import *

from src.controllers import TopWidgetController, WindowBehaviorController


class TopWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # 基本設置
        self.main_window = parent
        self.model = TopWidget_Model()
        self.controller = TopWidgetController(self.model, self)


        self.status_buttons = {}

        self.devices = {
            'USB': {'icon': 'parts_cable'},
            'Power': {'icon': 'show_chart'},
            'Loader': {'icon': 'parts_charger'}
        }

        self.setup_ui() # Widget 樣式設定
        self.init_ui()  # Widget main_layout init


    def setup_ui(self):
        self.setFixedHeight(44)
        self.setContentsMargins(0,0,0,0)
        self._setup_shadow()

    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def init_ui(self):
        # 創建主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 將容器添加到主布局
        container = QFrame()
        container.setObjectName("TagContainer")

        # 容器的布局
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for device_type, config in self.devices.items():
            device_container = self._create_device_container(device_type, config)
            container_layout.addWidget(device_container)

        switch_color_btn = SwitchThemeButton(self.main_window.theme_manager)
        container_layout.addWidget(switch_color_btn, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(container)


    def _create_device_container(self, device_type, config):
        device_container = QWidget()
        device_layout = QHBoxLayout(device_container)
        device_layout.setContentsMargins(16, 0, 8, 0)
        device_layout.setSpacing(0)
        device_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        button = self._create_device_button(device_type, config)
        button.setFixedSize(200, 30)
        self.status_buttons[device_type] = button

        device_layout.addWidget(button,0)

        return device_container

    def _create_device_button(self, device_type, config):
        """創建設備按鈕"""
        button = ComponentStatusButton(device_type, config['icon'], self.main_window)
        button.clicked.connect(
            lambda: self._handle_button_click(device_type)
        )
        return button

    def _handle_button_click(self, device_type):
        """處理按鈕點擊"""
        if device_type == 'USB':
            self.controller.connect_usb()
        elif device_type == 'Power':
            self.controller.connect_power()
        elif device_type == 'Loader':
            self.controller.connect_loader()

    def update_device_status(self, device_type, status):
        """更新設備狀態顯示"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(status)
