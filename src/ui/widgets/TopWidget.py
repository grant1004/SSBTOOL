from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import *
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
        self.setFixedHeight(40)
        self.setContentsMargins(8, 8, 8, 0)
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

        # 只設定容器的樣式，使用 QFrame 的特性來處理背景和邊框
        container.setStyleSheet("""
                            #TagContainer {
                                background-color: #006C4D;
                                border-radius: 8px;
                            }
                        """)

        # 容器的布局
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for device_type, config in self.devices.items():

            device_container = self._create_device_container(device_type, config)
            container_layout.addWidget(device_container)

            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setStyleSheet("""
                            QFrame {
                                background: none;
                                border: none;
                                border-left: 2px solid rgba(255, 255, 255, 0.2);
                            }
                        """)
            separator.setFixedHeight(24)  # 設置分隔線高度
            container_layout.addWidget(separator)

        main_layout.addWidget(container)


    def _create_device_container(self, device_type, config):
        device_container = QWidget()
        device_layout = QHBoxLayout(device_container)
        device_layout.setContentsMargins(16, 0, 8, 0)
        device_layout.setSpacing(0)
        device_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)


        icon_label = QLabel()
        icon_path = get_icon_path(config['icon'])  # 取得 icon 的檔案路徑
        icon_obj = QIcon(icon_path)
        # 選擇想要的圖示大小，比如 32x32
        pixmap = icon_obj.pixmap(16, 16)
        # 將 QPixmap 指定給 QLabel
        icon_label.setPixmap(pixmap)
        icon_label.setFixedSize(16, 16)
        device_layout.addWidget(icon_label,0)

        text_Label = QLabel(device_type)
        text_Label.setStyleSheet("""
                                color: white;
                                font-size: 14px;
                                font-weight: bold;
                                padding: 0px;
                            """)
        text_Label.setContentsMargins(4, 0, 8, 0)
        # 設置 text_label 的大小策略
        text_Label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # 設置文字自適應寬度
        text_Label.adjustSize()
        device_layout.addWidget(text_Label,0)

        button = self._create_device_button(device_type, config)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.status_buttons[device_type] = button

        device_layout.addWidget(button,0)







        return device_container

    def _create_device_button(self, device_type, config):
        """創建設備按鈕"""
        button = ComponentStatusButton(device_type)
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
