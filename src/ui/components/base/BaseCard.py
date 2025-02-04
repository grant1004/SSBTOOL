# components/base/BaseCard.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import random


class BaseCard(QFrame):

    """基礎卡片元件"""
    clicked = Signal(str)

    PRIORITIES = ['required', 'standard', 'optional']

    PRIORITY_COLORS = {
        'required': '#FF3D00',
        'standard': '#0099FF',
        'optional': '#4CAF50'
    }

    def __init__(self, card_id: str, config: dict, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.config = config
        self.is_hovered = False
        self._setup_ui()
        self.setObjectName("base-card")
        self.priority = self.config.get('priority', 'standard').lower()


        self.title_label.setProperty("class", "title")  # 可以用 .title 選擇器匹配'
        self.info_label.setProperty("class", "description")  # 可以用 .description 選擇器匹配
        self.priority_label.setProperty("class", f"priority-{self.priority}")  # 可以用 .priority-required 等選擇器匹配


    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._setup_shadow()
        self._setup_layout()

    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

    def _setup_layout(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 中間內容區域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        # 標題行容器
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # 優先級標籤
        priority = self.config.get('priority', 'standard').lower()
        priority_color = self.PRIORITY_COLORS.get(priority, self.PRIORITY_COLORS['standard'])
        self.priority_label = QLabel(priority.capitalize())
        self.priority_label.setStyleSheet(f"""
            background-color: {priority_color};
            color: white;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)

        # 標題容器
        title_container = QWidget()
        title_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_text = self.config.get('title', '')
        self.title_label = QLabel(title_text)
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(self.title_label)

        self.title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #333333;
        """)

        # 處理標題省略
        metrics = QFontMetrics(self.title_label.font())
        self.title_label.setText(metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, 200))
        if metrics.horizontalAdvance(title_text) > 200:
            self.title_label.setToolTip(title_text)

        # 時間標籤
        time_text = f"{self.config.get('estimated_time', '0')} min"
        self.time_label = QLabel(time_text)
        self.time_label.setStyleSheet("""
            font-size: 12px;
            color: #757575;
            padding: 0 4px;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # 添加到標題行
        header_layout.addWidget(self.priority_label)
        header_layout.addWidget(title_container)
        header_layout.addWidget(self.time_label)

        # 描述資訊
        info_text = self.config.get('info', '')
        self.info_label = QLabel(info_text)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            font-size: 12px;
            color: #666666;
        """)

        # 處理描述省略
        metrics = QFontMetrics(self.info_label.font())
        elidedText = metrics.elidedText(info_text, Qt.TextElideMode.ElideRight, 320)
        self.info_label.setText(elidedText)
        if metrics.horizontalAdvance(info_text) > 320:
            self.info_label.setToolTip(info_text)

        # 關鍵字容器
        keywords_widget = QWidget()
        keywords_layout = QHBoxLayout(keywords_widget)
        keywords_layout.setContentsMargins(0, 0, 0, 0)
        keywords_layout.setSpacing(8)

        # 處理關鍵字
        keywords = self.config.get('keywords', [])
        visible_keywords = []
        total_width = 0
        max_width = 300

        for keyword in keywords:
            font = QFont()
            font.setPointSize(11)
            metrics = QFontMetrics(font)
            width = metrics.horizontalAdvance(keyword) + 16

            if total_width + width > max_width:
                visible_keywords.append("...")
                break

            visible_keywords.append(keyword)
            total_width += width

        for keyword in visible_keywords:
            keyword_label = QLabel(keyword)
            keyword_label.setStyleSheet("""
                background-color: #F5F5F5;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                color: #666666;
            """)
            keywords_layout.addWidget(keyword_label)

        keywords_layout.addStretch()

        # 組合佈局
        content_layout.addWidget(header_widget)
        content_layout.addWidget(self.info_label)
        content_layout.addWidget(keywords_widget)

        layout.addLayout(content_layout)

        self.setStyleSheet("""
            BaseCard {
                background-color: white;
                border-radius: 8px;
            }
            BaseCard:hover {
                background-color: #F8F9FA;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card_id)

    def enterEvent(self, event):
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 4)

    def leaveEvent(self, event):
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0, 2)

    @staticmethod
    def random_priority() -> str:
        """隨機生成優先級"""
        return random.choice(BaseCard.PRIORITIES)