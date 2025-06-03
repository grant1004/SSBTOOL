import asyncio

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.ui.components import *
from src.Manager import DeviceManager, DeviceType


class TopWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # 初始化 DeviceManager
        self.device_manager = DeviceManager.instance()
        self.device_manager.register_status_callback(self.update_device_status)
        self.device_manager.register_error_callback(self.handle_device_error)

        self.status_buttons = {}
        self.devices = {
            DeviceType.USB: {'icon': 'parts_cable', 'name': 'USB'},
            DeviceType.POWER: {'icon': 'show_chart', 'name': 'Power'},
            DeviceType.LOADER: {'icon': 'parts_charger', 'name': 'Loader'}
        }

        self.setup_ui()

    def setup_ui(self):
        self.setFixedHeight(44)
        self.setContentsMargins(0, 0, 0, 0)
        self._setup_shadow()
        self.init_ui()

    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(parent=self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("TagContainer")

        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for device_type, config in self.devices.items():
            device_container = self._create_device_container(device_type, config)
            container_layout.addWidget(device_container)

        main_layout.addWidget(container)

    def _create_device_container(self, device_type, config):
        device_container = QWidget()
        device_layout = QHBoxLayout(device_container)
        device_layout.setContentsMargins(16, 0, 8, 0)
        device_layout.setSpacing(0)
        device_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        button = ComponentStatusButton(config['name'], config['icon'], self.main_window)
        button.setFixedSize(200, 30)
        self.status_buttons[device_type] = button

        # 將按鈕點擊事件連接到裝置管理器
        button.clicked.connect(
            lambda: asyncio.create_task(self._handle_button_click(device_type))
        )

        device_layout.addWidget(button, 0)
        return device_container

    async def _handle_button_click(self, device_type: DeviceType):
        """處理按鈕點擊"""
        try:
            await self.device_manager.connect_device(device_type)
        except Exception as e:
            print(f"Error connecting {device_type.value}: {str(e)}")

    def update_device_status(self, device_type: str, status: bool):
        """更新設備狀態顯示"""
        device_type = DeviceType(device_type)  # 將字串轉換為 enum
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(status)

    def handle_device_error(self, device_type: str, error_msg: str):
        """處理設備錯誤"""
        print(f"Error in {device_type}: {error_msg}")
        # 可以添加錯誤提示UI等
