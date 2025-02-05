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
    TITLE_STYLESHEET = """
        font-size: 14px;
        font-weight: bold;
        color: #333333;
    """
    INFO_STYLESHEET = """
        font-size: 12px;
        color: #666666;
    """
    PRIORITY_STYLESHEET = """
        color: white;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: bold;
    """
    TIME_STYLESHEET = """
        font-size: 12px;
        color: #757575;
        padding: 0 4px;
    """
    KEYWORD_STYLESHEET = """
        background-color: #F5F5F5;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        color: #666666;
    """
    CARD_STYLESHEET = """
        BaseCard {
            background-color: white;
            border-radius: 8px;
        }
        BaseCard:hover {
            background-color: #F8F9FA;
        }
    """

    def __init__(self, card_id: str, config: dict, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.config = config
        self.is_hovered = False
        self.priority = self.config.get('priority', 'standard').lower()

        self._setup_ui()
        self.setObjectName("base-card")
        self.setStyleSheet(self.CARD_STYLESHEET)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # 初始高度
        self.collapsed_height = 140
        self.expanded_height = 240  # 可以根據內容調整
        self.setFixedHeight(self.collapsed_height)
        self.setMinimumHeight(self.collapsed_height)
        self.setMaximumHeight(self.collapsed_height)

        # 創建兩個動畫對象
        self.height_animation = QPropertyAnimation(self, b"maximumHeight")
        self.height_animation.setDuration(200)

        self.min_height_animation = QPropertyAnimation(self, b"minimumHeight")
        self.min_height_animation.setDuration(200)

        # 獲取 theme manager
        self.theme_manager = self.get_theme_manager()
        # 連接主題變更信號
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)





    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self._setup_shadow()
        self._setup_layout()

    def _setup_shadow(self):
        """設置卡片的陰影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        self.shadow = shadow

    def _create_priority_label(self):
        priority_text = self.priority.capitalize()
        priority_color = self.PRIORITY_COLORS.get(self.priority, self.PRIORITY_COLORS['standard'])

        label = QLabel(priority_text)
        label.setStyleSheet(f"""
            background-color: {priority_color};
            {self.PRIORITY_STYLESHEET}
        """)
        return label

    def _create_header(self):
        """創建固定位置的標題行"""
        header_widget = QWidget()
        # 使用 QGridLayout 代替 QHBoxLayout
        header_layout = QGridLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # 創建各個元素
        self.priority_label = self._create_priority_label()
        self.title_label = self._create_title_label()
        self.time_label = self._create_time_label()

        # 設置固定寬度
        self.priority_label.setFixedWidth(70)
        self.time_label.setFixedWidth(60)

        # 使用 Grid 布局設置固定位置
        # addWidget(widget, row, column, rowSpan, columnSpan)
        header_layout.addWidget(self.priority_label, 0, 0)  # 左側
        header_layout.addWidget(self.title_label, 0, 1)  # 中間
        header_layout.addWidget(self.time_label, 0, 2)  # 右側

        # 設置列（column）的拉伸因子
        header_layout.setColumnStretch(0, 0)  # priority 列不拉伸
        header_layout.setColumnStretch(1, 1)  # title 列可以拉伸
        header_layout.setColumnStretch(2, 0)  # time 列不拉伸

        # 最小高度設定
        header_widget.setMinimumHeight(36)

        return header_widget

    def _create_title_label(self):
        """創建標題標籤"""
        title_text = self.config.get('title', '')
        label = QLabel()

        # 設置初始文字（帶省略號）
        label.setText(self._get_elided_text(title_text, max_width=220))

        # 設置對齊和樣式
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(self.TITLE_STYLESHEET)

        # 設置大小策略
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 設置工具提示（當文字被截斷時顯示完整文字）
        label.setToolTip(title_text)

        return label

    @staticmethod
    def _get_elided_text(text: str, max_width: int) -> str:
        """獲取帶省略號的文字"""
        metrics = QFontMetrics(QFont())
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_width)

    def _create_time_label(self):
        time_text = f"{self.config.get('estimated_time', '0')} min"
        label = QLabel(time_text)
        label.setStyleSheet(self.TIME_STYLESHEET)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _create_info_label(self):
        """創建描述信息區域"""
        info_text = self.config.get('info', '')
        label = QLabel(self._get_elided_text(info_text, max_width=320))
        label.setToolTip(info_text if len(info_text) > 0 else '')
        label.setWordWrap(True)
        label.setStyleSheet(self.INFO_STYLESHEET)
        return label

    def _create_keywords_widget(self):
        """創建關鍵字列表"""
        keywords_widget = QWidget()
        keywords_widget.setFixedHeight(26)
        keywords_layout = QHBoxLayout(keywords_widget)
        keywords_layout.setContentsMargins(0, 0, 0, 0)
        keywords_layout.setSpacing(8)

        keywords = self._get_visible_keywords()
        for keyword in keywords:
            label = QLabel(keyword)
            label.setStyleSheet(self.KEYWORD_STYLESHEET)
            keywords_layout.addWidget(label)

        keywords_layout.addStretch()
        return keywords_widget

    def _setup_layout(self):
        """設置卡片主要布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(8)

        # 標題區域：最小高度36px，但可以根據內容增長
        self.header_widget = self._create_header()
        self.header_widget.layout().setContentsMargins(0, 0, 0, 8)
        content_layout.addWidget(self.header_widget)

        # info 區域自適應
        self.info_label = self._create_info_label()
        content_layout.addWidget(self.info_label, 1)

        # keywords 固定高度
        self.keywords_widget = self._create_keywords_widget()
        self.keywords_widget.setFixedHeight(32)
        content_layout.addWidget(self.keywords_widget, 0)

        layout.addLayout(content_layout)


    def _get_visible_keywords(self):
        """計算關鍵字的可見範圍"""
        keywords = self.config.get('keywords', [])
        visible_keywords = []
        total_width = 0
        max_width = 300

        for keyword in keywords:
            font_metrics = QFontMetrics(QFont())
            width = font_metrics.horizontalAdvance(keyword) + 16
            if total_width + width > max_width:
                visible_keywords.append("...")
                break
            visible_keywords.append(keyword)
            total_width += width

        return visible_keywords

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

        # 更新卡片基本樣式
        self.setStyleSheet(f"""
            BaseCard {{
                background-color: {current_theme.SURFACE};
                border-radius: 8px;
            }}
            BaseCard:hover {{
                background-color: {current_theme.SURFACE_VARIANT};
            }}
        """)

        # 更新標題樣式
        self.title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {current_theme.TEXT_PRIMARY};
        """)

        # 更新描述文字樣式
        self.info_label.setStyleSheet(f"""
            font-size: 12px;
            color: {current_theme.TEXT_SECONDARY};
        """)

        # 更新時間標籤樣式
        self.time_label.setStyleSheet(f"""
            font-size: 12px;
            color: {current_theme.TEXT_SECONDARY};
            padding: 0 4px;
        """)

        # 更新關鍵字標籤樣式
        for i in range(self.keywords_widget.layout().count()):
            widget = self.keywords_widget.layout().itemAt(i).widget()
            if isinstance(widget, QLabel):
                widget.setStyleSheet(f"""
                    background-color: {current_theme.BACKGROUND};
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    color: {current_theme.TEXT_SECONDARY};
                """)

        # 更新優先級標籤樣式 (保持原有顏色方案)
        priority_color = self.PRIORITY_COLORS.get(self.priority, self.PRIORITY_COLORS['standard'])
        self.priority_label.setStyleSheet(f"""
            background-color: {priority_color};
            color: white;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)


    @staticmethod
    def _get_elided_text(text, max_width):
        """處理字符串超出布局的省略處理"""
        font_metrics = QFontMetrics(QFont())
        return font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, max_width)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card_id)

    def enterEvent(self, event):
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 4)

    def leaveEvent(self, event):
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0, 2)

    def focusInEvent(self, event):
        """獲得焦點時展開"""
        self.is_expanded = True
        QTimer.singleShot(0, self._update_expansion)  # 使用 Timer 延遲執行
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """失去焦點時收起"""
        self.is_expanded = False
        QTimer.singleShot(0, self._update_expansion)  # 使用 Timer 延遲執行
        super().focusOutEvent(event)

    @staticmethod
    def random_priority() -> str:
        """隨機生成優先級"""
        return random.choice(BaseCard.PRIORITIES)

    def _calculate_expanded_height(self):
        """計算展開狀態下所需的總高度"""
        total_height = 0
        margins = 24  # top + bottom margins (12 + 12)

        # 1. 計算標題區域高度
        title_text = self.config.get('title', '')
        title_font = self.title_label.font()
        title_font.setPointSize(16)  # 展開時的字體大小
        title_metrics = QFontMetrics(title_font)
        title_rect = title_metrics.boundingRect(
            QRect(0, 0, self.title_label.width() - 20, 0),  # -20 為了留出一些邊距
            Qt.TextFlag.TextWordWrap,
            title_text
        )
        header_height = max(52, title_rect.height() + 20)  # 至少52px，或根據文字高度調整
        total_height += header_height

        # 2. 計算描述文字所需高度
        info_text = self.config.get('info', '')
        info_font = self.info_label.font()
        info_font.setPointSize(14)  # 展開時的字體大小
        info_metrics = QFontMetrics(info_font)
        info_rect = info_metrics.boundingRect(
            QRect(0, 0, self.info_label.width() - 32, 0),  # -32 為了留出左右邊距
            Qt.TextFlag.TextWordWrap,
            info_text
        )
        info_height = info_rect.height() + 40  # 額外空間用於間距
        total_height += info_height

        # 3. 關鍵字區域高度（固定）
        keywords_height = 32
        total_height += keywords_height

        # 4. 添加間距
        spacing = 24  # 組件之間的總間距
        total_height += spacing

        # 5. 確保最小高度
        min_expanded_height = 240  # 最小展開高度
        return max(total_height + margins, min_expanded_height)

    def _update_expansion(self):
        """更新展開狀態下的內容顯示"""
        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        if self.is_expanded:
            # 計算目標高度
            target_height = self._calculate_expanded_height()

            # 設置展開動畫
            self.height_animation.setStartValue(self.height())
            self.height_animation.setEndValue(target_height)
            self.min_height_animation.setStartValue(self.height())
            self.min_height_animation.setEndValue(target_height)

            # 更新文字內容 - 完整顯示
            self.title_label.setText(self.config.get('title', ''))
            self.info_label.setText(self.config.get('info', ''))

            # 調整布局空間
            self.header_widget.layout().setContentsMargins(0, 0, 0, 8)  # 增加下方間距
            self.info_label.setContentsMargins(0, 0, 0, 16)  # 增加與關鍵字的間距

            # 標題樣式強化
            self.title_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: bold;
                color: {current_theme.TEXT_PRIMARY};
            """)
            self.title_label.setWordWrap(True)

            # 描述文字改進 - 給予更多空間
            self.info_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: semi-bold;
                color: {current_theme.TEXT_PRIMARY};
                padding: 4px 0;
            """)
            self.info_label.setWordWrap(True)

            # 關鍵字標籤保持原樣，只改變顏色
            for i in range(self.keywords_widget.layout().count()):
                widget = self.keywords_widget.layout().itemAt(i).widget()
                if isinstance(widget, QLabel):
                    widget.setStyleSheet(f"""
                        background-color: {current_theme.BACKGROUND};
                        border-radius: 4px;
                        padding: 2px 8px;
                        font-size: 11px;
                        color: {current_theme.TEXT_PRIMARY};
                    """)

            # 更新陰影
            self.shadow.setBlurRadius(15)
            self.shadow.setOffset(0, 4)
            self.shadow.setColor(QColor(0, 0, 0, 25))

            # 卡片樣式更新
            self.setStyleSheet(f"""
                BaseCard {{
                    background-color: {current_theme.SURFACE};
                    border-radius: 8px;
                }}
                BaseCard:hover {{
                    background-color: {current_theme.SURFACE_VARIANT};
                }}
            """)

        else:
            # 設置收縮動畫
            target_height = self.collapsed_height
            self.height_animation.setStartValue(self.height())
            self.height_animation.setEndValue(target_height)
            self.min_height_animation.setStartValue(self.height())
            self.min_height_animation.setEndValue(target_height)

            # 更新文字內容 - 省略模式
            self.title_label.setText(self._get_elided_text(
                self.config.get('title', ''),
                max_width=200
            ))
            self.info_label.setText(self._get_elided_text(
                self.config.get('info', ''),
                max_width=320
            ))

            # 恢復原本間距
            self.header_widget.layout().setContentsMargins(0, 0, 0, 8)
            self.info_label.setContentsMargins(0, 0, 0, 0)

            # 恢復標題樣式
            self.title_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {current_theme.TEXT_PRIMARY};
            """)
            self.title_label.setWordWrap(False)

            # 恢復描述文字樣式
            self.info_label.setStyleSheet(f"""
                font-size: 12px;
                color: {current_theme.TEXT_SECONDARY};
                min-height: 20px;
            """)
            self.info_label.setWordWrap(False)

            # 恢復關鍵字標籤樣式
            for i in range(self.keywords_widget.layout().count()):
                widget = self.keywords_widget.layout().itemAt(i).widget()
                if isinstance(widget, QLabel):
                    widget.setStyleSheet(f"""
                        background-color: {current_theme.BACKGROUND};
                        border-radius: 4px;
                        padding: 2px 8px;
                        font-size: 11px;
                        color: {current_theme.TEXT_SECONDARY};
                    """)

            # 恢復陰影
            self.shadow.setBlurRadius(10)
            self.shadow.setOffset(0, 2)
            self.shadow.setColor(QColor(0, 0, 0, 30))

            # 恢復卡片樣式
            self.setStyleSheet(f"""
                BaseCard {{
                    background-color: {current_theme.SURFACE};
                    border-radius: 8px;
                }}
                BaseCard:hover {{
                    background-color: {current_theme.SURFACE_VARIANT};
                }}
            """)

        # 同時開始兩個動畫
        self.height_animation.start()
        self.min_height_animation.start()