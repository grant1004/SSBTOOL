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


        # 獲取 theme manager
        self.theme_manager = self.get_theme_manager()
        # 連接主題變更信號
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

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
        """更新按鈕樣式"""
        if self.theme_manager:
            self._update_theme()  # 使用主題系統的樣式
        else:
            # fallback 到原始樣式（當沒有 theme manager 時）
            self.container.setStyleSheet("""
                QFrame {
                    background-color: #EEEEEE;
                    border-radius: 20px;
                }
            """)

            for mode_id, btn in self.buttons.items():
                is_active = mode_id == self.current_mode
                btn.setStyleSheet(self._get_button_style_fallback(is_active))

    def _get_button_style_fallback(self, is_active):
        """獲取按鈕預設樣式"""
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


    def get_theme_manager(self):
        """遞迴向上查找 theme_manager"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent()
        return None

    def _update_theme(self):
        """更新主題相關的樣式"""
        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        # 更新容器樣式
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {current_theme.SURFACE};
                border-radius: 20px;
            }}
        """)

        # 更新每個按鈕的樣式
        for mode_id, btn in self.buttons.items():
            is_active = mode_id == self.current_mode
            btn.setStyleSheet(self._get_button_style(is_active, current_theme))

    def _get_button_style(self, is_active, theme):
        """獲取按鈕樣式"""
        if is_active:
            return f"""
                QPushButton {{
                    border: none;
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-size: 14px;
                    background-color: {theme.PRIMARY};
                    color: {theme.TEXT_ON_PRIMARY};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme.PRIMARY_DARK};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    border: none;
                    border-radius: 16px;
                    padding: 8px 16px;
                    font-size: 14px;
                    background-color: transparent;
                    color: {theme.TEXT_SECONDARY};
                    font-weight: normal;
                }}
                QPushButton:hover {{
                    background-color: {theme.OVERLAY};
                    color: {theme.TEXT_PRIMARY};
                }}
            """