from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from src.utils import get_icon_path, Utils


class SwitchThemeButton(QPushButton):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setFixedSize(30, 30)
        self.setObjectName("theme-switch")
        Utils.setup_click_animation(self)
        # 連接點擊事件
        self.clicked.connect(self.switch_theme)

        # 初始化圖標
        self._update_button()

    def switch_theme(self):
        self.theme_manager.switch_theme()
        self._update_button()

    def _update_button(self):
        is_dark = self.theme_manager.current_theme.value == "industrial"
        icon_name = "star" if is_dark else "weather_clear sky.svg"
        color = "#FFFFFF" if is_dark else "#000000"
        icon = QIcon(get_icon_path(icon_name))
        icon = Utils.change_icon_color(icon, color)
        self.setIcon(icon)
        self.setIconSize(QSize(20, 20))