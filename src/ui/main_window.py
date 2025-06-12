import asyncio
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from . import widgets
from . import components
from .Theme import Theme, ThemeManager, ThemeType
from src.utils import get_icon_path
import sys
import ctypes
from ctypes.wintypes import DWORD, BOOL, HRGN

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SSB Tool")
        self.desktop = QApplication.primaryScreen().availableGeometry()

        self.setObjectName("main-window")
        self.setWindowIcon(
            QIcon( get_icon_path("parts_default.svg") )
        )

        self.theme_manager = ThemeManager()

        # Windows 深色標題列設定
        if sys.platform == "win32":
            # 啟用自訂標題列顏色
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = self.winId().__int__()
            rendering_policy = DWORD(2)
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                 ctypes.byref(rendering_policy),
                                 ctypes.sizeof(rendering_policy))

        # 設定視窗大小
        self.resize(1000,520)

        # 初始化 UI
        self.init_ui()

        self.theme_manager._update_app_style()

    def init_ui(self):
        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.setContentsMargins(0,0,0,0)
        self.centralWidget().setObjectName("central-widget")

        # 創建網格布局
        grid = QGridLayout(central_widget)
        grid.setContentsMargins(0,0,0,0)  # 移除邊距
        grid.setSpacing(0)  # 移除間距

        # 創建四個主要部件
        self.top_widget = widgets.TopWidget(self)

        self.test_case_widget = widgets.TestCaseWidget(self)

        self.run_case_widget = widgets.RunCaseWidget(self)

        # self.run_widget = widgets.RunWidget(self)

        # 添加到網格布局中
        # addWidget(widget, row, column, rowSpan, columnSpan)
        # Grid : 3 row * 2 column
        grid.addWidget(self.top_widget, 0, 0, 1, 2)  # 頂部跨兩列
        grid.addWidget(self.test_case_widget, 1, 0, 2, 1)  # 左側
        grid.addWidget(self.run_case_widget, 1, 1, 1, 1)  # 右側
        # grid.addWidget(self.run_widget, 2, 1, 1, 1)  # 右下

        # 設置列（column）的比例
        grid.setColumnStretch(0, 3)  # 左側占 3
        grid.setColumnStretch(1, 7)  # 右側占 7

        grid.setRowStretch(0,0)
        grid.setRowMinimumHeight(0,44)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 0)

    def closeEvent(self, event):
        try:
            print("Closing window...")
            loop = asyncio.get_event_loop()

            # 如果事件迴圈正在運行，安全地停止
            if loop.is_running():
                loop.stop()

            # 確保關閉所有非模態的視窗
            for widget in QApplication.topLevelWidgets():
                if widget.isVisible():
                    widget.close()

            event.accept()
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()


