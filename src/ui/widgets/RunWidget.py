# from PySide6.QtWidgets import *
# from PySide6.QtCore import *
# from PySide6.QtGui import *
# from src.utils import get_icon_path
# from src.utils import Utils
#
#
# class RunWidget(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.mainWindow = parent
#         self.setFixedHeight(80)
#         self.controller = Container.get_run_widget_controller()
#         self._setup_shadow()
#         self.main_layout = QHBoxLayout(self)
#         self.main_layout.setContentsMargins(4,4,8,8)
#         self.main_layout.setSpacing(0)
#
#         # 按鈕配置
#         buttons_config = {
#             "export": {  # 調整按鈕順序以符合設計
#                 "icon": get_icon_path("file_download"),
#                 "slot": self.controller.GenerateCommand,
#                 "tooltip": "Generate Robot file",
#                 "text": "Export"  # 添加按鈕文字
#             },
#             "import": {
#                 "icon": get_icon_path("file import template"),
#                 "slot": self.controller.ImportCommand,
#                 "tooltip": "Load existing Robot file",
#                 "text": "Import"
#             },
#             "run": {
#                 "icon": get_icon_path("play_circle"),
#                 "slot": self.controller.RunCommand,
#                 "tooltip": "Run Robot framework",
#                 "text": "Run"
#             },
#             "report": {
#                 "icon": get_icon_path("picture_as_pdf"),
#                 "slot": self.controller.ReportCommand,
#                 "tooltip": "Get Report file (PDF)",
#                 "text": "Report"
#             }
#         }
#
#         # 創建按鈕容器
#         button_container = QWidget()
#         button_layout = QHBoxLayout(button_container)
#         button_layout.setContentsMargins(8, 0, 8, 0)
#         button_layout.setSpacing(16)
#         button_layout.addStretch()  # 添加彈性空間將按鈕推到右側
#
#         # 創建按鈕
#         for button_type, config in buttons_config.items():
#             btn = QPushButton(config["text"])  # 設置按鈕文字
#
#             # 設置按鈕大小（根據設計調整）
#             if button_type == "export" or button_type == "import":
#                 btn.setFixedSize(90, 40)
#             elif button_type == "run":
#                 btn.setFixedSize(70, 40)
#             else:
#                 btn.setFixedSize(90, 40)
#
#             # 設置圖標
#             icon = QIcon(config["icon"])
#             colored_icon = Utils.change_icon_color(icon, "#000000")
#             btn.setIcon(colored_icon)
#             btn.setIconSize(QSize(16, 16))
#             btn.setToolTip(config["tooltip"])
#
#
#             # 根據按鈕類型設置不同的樣式
#             style = """
#                 QPushButton {
#                     color: #000000;
#                     border: none;
#                     font-weight: bold;
#                     font-size: 14px;
#                     border-radius: 8px;
#                     padding: 5px 10px;
#                     %s
#                 }
#                 QPushButton:hover {
#                     %s
#                 }
#             """
#
#             if button_type == "export" or button_type == "import": #
#                 btn.setStyleSheet(style % (f"background-color: #FDB813;",
#                                            "background-color: #F2AA02;"))
#             elif button_type == "run":
#                 btn.setStyleSheet(style % ("background-color: #4CAF50;",
#                                            "background-color: #3C9F40;"))
#             else:
#                 btn.setStyleSheet(style % ("background-color: #0099ff;",
#                                            "background-color: #0077ff;"))
#
#             btn.clicked.connect(config["slot"])
#             btn = Utils.setup_click_animation(btn)
#             button_layout.addWidget(btn)
#
#         self.main_layout.addWidget(button_container)
#
#
#     def _setup_shadow(self):
#         self.shadow = QGraphicsDropShadowEffect(self)
#         self.shadow.setColor(QColor(0, 0, 0, 60))
#         self.shadow.setBlurRadius(15)
#         self.shadow.setOffset(0, 2)
#         self.setGraphicsEffect(self.shadow)
#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)