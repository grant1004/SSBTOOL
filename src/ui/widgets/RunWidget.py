from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import get_icon_path
from src.utils import Utils
from src.controllers import RunWidgetController
from src.models import RunWidget_Model


class RunWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #2D2D2D;"
                           "border-radius: 4px")  # 改為白色背景更符合設計
        self.setFixedHeight(60)
        self.model = RunWidget_Model()
        self.controller = RunWidgetController( self.model, self)

        self._setup_shadow()


        # 創建主佈局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 8, 8)

        # 按鈕配置
        buttons_config = {
            "generate": {  # 調整按鈕順序以符合設計
                "icon": get_icon_path("doc"),
                "slot": self.controller.GenerateCommand,
                "tooltip": "Generate Robot file",
                "text": "Generate Robot"  # 添加按鈕文字
            },
            "run": {
                "icon": get_icon_path("play_circle"),
                "slot": self.controller.RunCommand,
                "tooltip": "Run Robot framework",
                "text": "Run"
            },
            "report": {
                "icon": get_icon_path("picture_as_pdf"),
                "slot": self.controller.ReportCommand,
                "tooltip": "Get Report file (PDF)",
                "text": "Report"
            }
        }

        # 創建按鈕容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(8, 0, 8, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()  # 添加彈性空間將按鈕推到右側

        # 創建按鈕
        for button_type, config in buttons_config.items():
            btn = QPushButton(config["text"])  # 設置按鈕文字

            # 設置按鈕大小（根據設計調整）
            if button_type == "generate":
                btn.setFixedSize(140, 40)
            elif button_type == "run":
                btn.setFixedSize(70, 40)
            else:
                btn.setFixedSize(90, 40)

            # 設置圖標
            icon = QIcon(config["icon"])
            colored_icon = Utils.change_icon_color(icon, "#1A1A1A")
            btn.setIcon(colored_icon)
            btn.setIconSize(QSize(16, 16))
            btn.setToolTip(config["tooltip"])


            # 根據按鈕類型設置不同的樣式
            style = """
                QPushButton {
                    color: black;
                    border: none;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 5px 10px;
                    %s
                }
                QPushButton:hover {
                    %s
                }
            """

            if button_type == "generate":
                btn.setStyleSheet(style % ("background-color: #FDB813;",
                                           "background-color: #936B09;"))
            elif button_type == "run":
                btn.setStyleSheet(style % ("background-color: #4CAF50;",
                                           "background-color: #3C9F40;"))
            else:
                btn.setStyleSheet(style % ("background-color: #666666;",
                                           "background-color: #555555;"))

            btn.clicked.connect(config["slot"])
            btn = Utils.setup_click_animation(btn)
            button_layout.addWidget(btn)

        self.main_layout.addWidget(button_container)


    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)