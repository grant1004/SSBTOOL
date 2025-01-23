from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtSvg import QSvgRenderer
from src.utils import get_icon_path
from src.utils import Utils
from ..Theme import Theme


class ComponentStatusButton(QPushButton):
    """
    組件狀態按鈕
    """

    def __init__(self, component_name, icon_path, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.icon_path = icon_path
        self.setFixedSize(200, 30)
        self._setup_ui()

    def _setup_ui(self):
        self.inner_layout = QHBoxLayout(self)
        self.inner_layout.setContentsMargins(15, 0, 15, 0)
        self.inner_layout.setSpacing(10)

        # 創建 SVG 圖標
        self.component_icon = QLabel()
        self.icon_obj = QIcon( get_icon_path(self.icon_path) )
        self.icon_obj = Utils.change_icon_color(self.icon_obj, Theme.PRIMARY_COLOR )
        # 選擇想要的圖示大小，比如 32x32
        self.pixmap = self.icon_obj.pixmap(16, 16)
        # 將 QPixmap 指定給 QLabel
        self.component_icon.setPixmap(self.pixmap)
        self.component_icon.setFixedSize(16, 16)


        # 創建組件名稱
        self.name_label = QLabel(self.component_name)
        self.name_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }
        """)

        # 創建狀態指示燈
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(10, 10)

        # 創建狀態文字
        self.status_text = QLabel("Offline")
        self.status_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }
        """)

        # 添加到佈局
        self.inner_layout.addWidget(self.component_icon)
        self.inner_layout.addWidget(self.name_label)
        self.inner_layout.addWidget(self.status_indicator)
        self.inner_layout.addWidget(self.status_text)

        # 設置按鈕樣式
        self.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D60;
                border: none;
                border-radius: 15px;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #333333FA;
            }
        """)

        # 初始化為離線狀態
        self.update_status(False)

    def update_status(self, is_connected):
        """更新按鈕狀態"""
        color = "#4CAF50" if is_connected else "#FF3D00"
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)
        self.status_text.setText("Online" if is_connected else "Offline")

