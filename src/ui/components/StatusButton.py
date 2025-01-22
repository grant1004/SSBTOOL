from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

class ComponentStatusButton(QPushButton):
    """
    組件狀態按鈕
    """

    def __init__(self, component_name, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.setFixedSize(130, 24)
        self._setup_ui()

    def _setup_ui(self):
        # 創建內部佈局
        self.inner_layout = QHBoxLayout(self)
        self.inner_layout.setContentsMargins(8, 0, 0, 0)
        self.inner_layout.setSpacing(8)

        # 創建狀態指示燈
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)

        # 創建狀態文字
        self.status_text = QLabel("Disconnected")
        self.status_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background: transparent;
            }
        """)

        # 添加到佈局
        self.inner_layout.addWidget(self.status_indicator)
        self.inner_layout.addWidget(self.status_text)

        # 設置按鈕樣式
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid white;
                border-radius: 12px;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)

        # 初始化為未連接狀態
        self.update_status(False)

    def update_status(self, is_connected):
        """更新按鈕狀態"""
        # 更新指示燈顏色
        color = "#4CAF50" if is_connected else "#B22222"
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

        # 更新文字
        self.status_text.setText("Connected" if is_connected else "Disconnected")
