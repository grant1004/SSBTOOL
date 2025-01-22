from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import *
from src.controllers import TopWidgetController, WindowBehaviorController


class TopWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # 基本設置
        self.dragPos = None
        self.main_window = parent
        self.window_controller = TopWidgetController( self.main_window )
        self.window_behavior = WindowBehaviorController(self.main_window)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #006C4D;")
        # 創建並設置陰影效果
        self.shadow = QGraphicsDropShadowEffect(self)
        # 設置陰影的顏色（這裡使用半透明的黑色）
        self.shadow.setColor(QColor(0, 0, 0, 60))
        # 設置陰影的模糊半徑（數值越大陰影越模糊）
        self.shadow.setBlurRadius(15)
        # 設置陰影的偏移（x和y方向）
        self.shadow.setOffset(0, 2)
        # 將陰影效果應用到組件上
        self.setGraphicsEffect(self.shadow)
        # 確保組件可以顯示陰影
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


        # 創建主網格布局
        topGrid = QGridLayout(self)
        topGrid.setContentsMargins(0, 0, 0, 0)  # 移除邊距
        topGrid.setSpacing(0)  # 移除間距

        # 第一欄：圖標欄，固定 30px
        topGrid.setColumnMinimumWidth(0, 30)
        # 第二欄：標題欄，固定 80px
        topGrid.setColumnMinimumWidth(1, 80)
        # 第三欄：連接狀態欄，自動擴展（不需要設置）
        # 第四欄：視窗控制按鈕欄，固定 120px
        topGrid.setColumnMinimumWidth(3, 120)

        topGrid.setColumnStretch(0, 0)  # 不伸展
        topGrid.setColumnStretch(1, 0)  # 不伸展
        topGrid.setColumnStretch(2, 1)  # 伸展係數為1
        topGrid.setColumnStretch(3, 0)  # 不伸展

        # 1. 創建左側標題
        toolIcon = QIcon( get_icon_path("gps_fixed.svg"))
        pixmap = toolIcon.pixmap(QSize(24, 24))  # 設定想要的大小
        # 將 pixmap 設置到標籤中
        icon_label = QLabel()
        icon_label.setPixmap(pixmap)
        icon_label.setContentsMargins(8, 0, 0, 0)

        title = QLabel("SSB Tool")
        title.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding-right: 16px;
        """)

        # 2. 創建中間的連線狀態
        connection_status = self._create_connection_status()

        # 3. 創建右側的視窗控制按鈕
        window_controls = self._create_window_controls()

        # 將所有元件添加到布局中
        # addWidget(widget, row, column, rowSpan, columnSpan)
        topGrid.addWidget( icon_label, 0, 0)
        topGrid.addWidget( title, 0, 1 )
        topGrid.addWidget(connection_status, 0, 2)
        topGrid.addWidget(window_controls, 0, 3)

    def _create_window_controls(self):
        """創建視窗控制按鈕"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(10)

        # 定義按鈕和對應的圖標路徑
        buttons_config = {
            "minimize": {
                "icon": get_icon_path("remove"),
                "slot": self.window_controller.minimize_window,  # 最小化視窗
                "tooltip": "Minimize"
            },
            "maximize": {
                "icon": get_icon_path("crop_landscape"),
                "slot": self.window_controller.toggle_maximize,  # 最大化/還原視窗
                "tooltip": "Maximize"
            },
            "close": {
                "icon": get_icon_path("close"),
                "slot": self.window_controller.close_window,  # 關閉視窗
                "tooltip": "Close"
            }
        }

        for button_type, icon_path in buttons_config.items():
            btn = QPushButton()
            btn.setFixedSize(30, 30)

            # 創建並設置圖標
            icon = QIcon(icon_path["icon"])
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))  # 設置圖標大小

            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)

            btn.clicked.connect(icon_path["slot"])

            layout.addWidget(btn)

        return container

    def _create_connection_status(self):
        """
        創建連接狀態組件。這個組件包含：
        - 一個綠色的狀態指示燈
        - "Connected" 文字
        - 懸停時的提示信息
        """
        # 創建容器組件
        container = QWidget()

        # 這個布局將用來放置我們的 frame
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除容器邊距
        main_layout.setSpacing(0)  # 移除間距

        # 創建自定義懸停效果
        container_frame = QFrame()
        container_frame.setFixedSize(130,24)
        container_frame.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.1);
                        border: 1px solid white;
                        border-radius: 12px;
                        
                    }
                    QFrame:hover {
                        background-color: rgba(255, 255, 255, 0.2);
                    }
                """)

        # 創建水平布局
        statuslayout = QHBoxLayout(container_frame)
        statuslayout.setContentsMargins(5, 0, 0, 0)
        statuslayout.setSpacing(8)

        # 創建狀態指示燈
        status_indicator = QLabel()
        status_indicator.setFixedSize(12, 12)
        status_indicator.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;  /* 綠色指示燈 */
                border-radius: 6px;         /* 圓形效果 */
                border: 0px solid white;
            }
        """)

        # 創建狀態文字
        status_text = QLabel("Connected")
        status_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                background: transparent;
                border: 0px solid white;
            }
        """)


        statuslayout.addWidget(status_indicator)
        statuslayout.addWidget(status_text)

        main_layout.addWidget(container_frame, alignment=Qt.AlignmentFlag.AlignLeft)
        container.setLayout(main_layout)
        return container

    def mousePressEvent(self, event):
        """處理滑鼠按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPos()
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """
        當滑鼠移動時被調用。
        如果滑鼠左鍵被按下（正在拖曳），我們計算位置差異並移動視窗。
        """
        # 確保是在拖曳狀態（滑鼠左鍵按下）
        if self.dragPos is not None:
            # 計算滑鼠移動的距離
            delta = event.globalPos() - self.dragPos
            # 移動整個視窗
            self.window().move(self.window().pos() + delta)
            # 更新拖曳位置
            self.dragPos = event.globalPos()


        # 確保事件繼續傳播
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        當滑鼠釋放時被調用。
        我們需要清除拖曳狀態。
        """
        # 如果是左鍵釋放，結束拖曳狀態
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = None

        # 確保事件繼續傳播
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """處理滑鼠雙擊事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.window_controller.toggle_maximize()
