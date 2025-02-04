from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import get_icon_path, Utils


class SearchBar(QWidget):
    """搜索欄組件"""
    # 定義信號
    search_changed = Signal(str)  # 當搜索內容改變時發出
    search_submitted = Signal(str)  # 當按下 Enter 鍵時發出

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # 創建主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 創建搜索容器
        self.search_container = QFrame()
        self.search_container.setObjectName("search-container")
        container_layout = QHBoxLayout(self.search_container)
        container_layout.setContentsMargins(12, 0, 12, 0)
        container_layout.setSpacing(0)


        # 創建搜索圖標
        self.search_icon = QLabel()
        icon = QIcon(get_icon_path("search.svg"))
        icon = Utils.change_icon_color(icon, "#000000")
        pixmap = icon.pixmap(16, 16)
        self.search_icon.setPixmap(pixmap)
        self.search_icon.setFixedSize(16, 16)

        # 創建搜索輸入框
        self.search_input = QLineEdit()
        self.search_input.setContentsMargins(0,0,0,0)
        self.search_input.setPlaceholderText("Search test cases...")
        self.search_input.setMinimumHeight(48)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)

        # 創建清除按鈕
        self.clear_button = QPushButton()
        close_icon = QIcon(get_icon_path("close.svg"))
        colse_icon = Utils.change_icon_color(close_icon, "#000000")
        self.clear_button.setIcon(colse_icon)
        self.clear_button.setFixedSize(16, 16)
        self.clear_button.clicked.connect(self.clear_search)
        self.clear_button.hide()  # 初始時隱藏
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # 添加組件到容器
        container_layout.addWidget(self.search_icon)
        container_layout.addWidget(self.search_input, 1)
        container_layout.addWidget(self.clear_button)

        # 添加容器到主布局
        layout.addWidget(self.search_container)

        # 設置樣式
        self.setStyleSheet("""
            #search-container {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }

            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #333333;
            }

            QLineEdit::placeholder {
                color: #999999;
            }

            QPushButton {
                border: none;
                background: transparent;
            }

            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 4px;
            }
        """)

    def _on_text_changed(self, text):
        """處理文本變化"""
        # 控制清除按鈕的顯示/隱藏
        self.clear_button.setVisible(bool(text))
        # 發送信號
        self.search_changed.emit(text)

    def _on_return_pressed(self):
        """處理回車按鍵"""
        self.search_submitted.emit(self.search_input.text())

    def clear_search(self):
        """清除搜索內容"""
        self.search_input.clear()

    def set_placeholder(self, text: str):
        """設置佔位符文本"""
        self.search_input.setPlaceholderText(text)

    def get_text(self) -> str:
        """獲取當前搜索文本"""
        return self.search_input.text()

    def set_text(self, text: str):
        """設置搜索文本"""
        self.search_input.setText(text)


class TestCaseFilter:
    """測試案例過濾器"""

    def __init__(self):
        self.current_filter = ""

    def set_filter(self, filter_text: str):
        """設置過濾條件"""
        self.current_filter = filter_text.lower()

    def matches(self, test_case: dict) -> bool:
        """檢查測試案例是否符合過濾條件"""
        if not self.current_filter:
            return True

        # 檢查名稱
        if self.current_filter in test_case.get('name', '').lower():
            return True

        # 檢查關鍵字
        keywords = test_case.get('keywords', [])
        return any(self.current_filter in keyword.lower() for keyword in keywords)

