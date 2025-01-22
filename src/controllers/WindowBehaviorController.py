from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

class WindowBehaviorController:
    def __init__(self, main_window):
        self.main_window = main_window
        self.is_maximized = False
        # 設定視窗行為標誌
        self.main_window.setWindowFlags(
            Qt.WindowType.Window |  # 基本視窗標誌
            Qt.WindowType.FramelessWindowHint |  # 無邊框
            Qt.WindowType.WindowMinimizeButtonHint |  # 支援最小化
            Qt.WindowType.WindowMaximizeButtonHint  # 支援最大化
        )

    def handle_window_states(self, event, window_state):
        """處理視窗狀態變化，比如拖放到螢幕頂部最大化"""
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor)
        if not screen:
            return

        # 獲取螢幕尺寸
        screen_geometry = screen.availableGeometry()

        if window_state == "top":
            # 如果拖到螢幕頂部，最大化視窗
            if cursor.y() <= screen_geometry.top():
                self.maximize_window()

        elif window_state == "left":
            # 靠左半屏
            new_geometry = QRect(
                screen_geometry.left(),
                screen_geometry.top(),
                screen_geometry.width() // 2,
                screen_geometry.height()
            )
            self.main_window.setGeometry(new_geometry)

        elif window_state == "right":
            # 靠右半屏
            new_geometry = QRect(
                screen_geometry.left() + screen_geometry.width() // 2,
                screen_geometry.top(),
                screen_geometry.width() // 2,
                screen_geometry.height()
            )
            self.main_window.setGeometry(new_geometry)

    def maximize_window(self):
        """最大化視窗"""
        if not self.is_maximized:
            # 保存當前位置和大小以便還原
            self.normal_geometry = self.main_window.geometry()
            screen = QApplication.screenAt(QCursor.pos())
            if screen:
                self.main_window.setGeometry(screen.availableGeometry())
                self.is_maximized = True
        else:
            # 還原視窗
            self.main_window.setGeometry(self.normal_geometry)
            self.is_maximized = False