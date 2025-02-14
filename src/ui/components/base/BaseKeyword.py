# components/base/BaseKeyWordCard.py
from typing import Any

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json

class BaseKeywordCard(QFrame):
    """關鍵字卡片元件"""
    clicked = Signal(str)
    PRIORITY_COLORS = {
        'required': '#FF3D00',
        'normal': '#0099FF',
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
    CATEGORY_STYLESHEET = """
        color: white;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 14px;
        font-weight: bold;
    """
    PARAM_STYLESHEET = """
        font-size: 12px;
        color: #666666;
        padding: 4px 8px;
        background: #F5F5F5;
        border-radius: 4px;
    """
    CARD_STYLESHEET = """
        KeywordCard {
            background-color: white;
            border-radius: 8px;
        }
        KeywordCard:hover {
            background-color: #F8F9FA;
        }
    """

    def __init__(self, card_id: str, config: dict, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.drag_start_position = None
        self.card_id = card_id
        self.config = config
        self.is_expanded = False

        # Initialize argument values with defaults
        self.argument_values = {}
        self._init_argument_values()

        # UI 初始化
        self._setup_ui()
        self.setObjectName("keyword-card")
        self.setStyleSheet(self.CARD_STYLESHEET)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # 高度設置
        self.collapsed_height = 100
        self.setFixedHeight(self.collapsed_height)
        self.setMinimumHeight(self.collapsed_height)
        self.setMaximumHeight(self.collapsed_height)

        # 動畫初始化
        self.height_animation = QPropertyAnimation(self, b"maximumHeight")
        self.height_animation.setDuration(200)
        self.min_height_animation = QPropertyAnimation(self, b"minimumHeight")
        self.min_height_animation.setDuration(200)

        # 主題管理
        self.theme_manager = self.get_theme_manager()
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

    def _init_argument_values(self):
        """Initialize argument values with their defaults"""
        for arg in self.config.get('arguments', []):
            self.argument_values[arg['name']] = arg.get('default')

    def _setup_ui(self):
        """初始化 UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setContentsMargins(8,8,8,8)
        self._setup_shadow()
        self._setup_layout()

    def _setup_shadow(self):
        """設置陰影效果"""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

    def _create_header(self):
        """創建標題區域"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Keyword 名稱
        self.title_label = QLabel(self.config.get('name', ''))
        self.title_label.setStyleSheet(self.TITLE_STYLESHEET)
        self.title_label.setFixedWidth(300)
        self.title_label.setWordWrap(True)

        # 分類標籤
        self.category_label = QLabel(self.config.get('category', ''))
        self.category_label.setStyleSheet(f"""
            background-color: #0077EE;
            {self.CATEGORY_STYLESHEET}
        """)

        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.category_label, 0)

        return header_widget

    def _setup_layout(self):
        """設置主布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 標題區域
        self.header_widget = self._create_header()
        layout.addWidget(self.header_widget)

        # 簡短描述
        self.description_label = QLabel()
        self.description_label.setStyleSheet(self.INFO_STYLESHEET)
        self.description_label.setWordWrap(True)
        self.description_label.setFixedWidth(300)
        self.description_label.setContentsMargins(16, 0, 0, 0)
        self.description_label.font().setPixelSize(14)
        self._update_description_text()

        layout.addWidget(self.description_label)

        # 參數預覽
        self.params_preview = self._create_params_preview()
        layout.addWidget(self.params_preview)

        # 展開時顯示的詳細信息
        self.details_widget = self._create_details_widget()
        self.details_widget.hide()
        layout.addWidget(self.details_widget)

        layout.addStretch()

    def _create_params_preview(self):
        """創建參數預覽"""
        params = self.config.get('arguments', [])
        label = QLabel(f"{len(params)} Arguments")
        label.setStyleSheet(f"""
            background-color: #E0E0E0;
            color: #333333;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 14px;
            font-weight: bold;
            margin-left: 16px;
        """)
        return label

    def _create_details_widget(self):
        """創建詳細信息區域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # 完整描述
        if description := self.config.get('description', ''):
            desc_label = QLabel("Description")
            desc_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(desc_label)

            desc_content = QLabel(description)
            desc_content.setStyleSheet(self.INFO_STYLESHEET)
            desc_content.setWordWrap(True)
            layout.addWidget(desc_content)

        # 參數列表
        if arguments := self.config.get('arguments', []):
            args_label = QLabel("Arguments")
            args_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(args_label)

            args_widget = QWidget()
            args_layout = QVBoxLayout(args_widget)
            args_layout.setContentsMargins(0, 0, 0, 0)
            args_layout.setSpacing(4)

            for arg in arguments:
                arg_widget = self._create_argument_widget(arg)
                args_layout.addWidget(arg_widget)

            layout.addWidget(args_widget)

        # 返回值
        if returns := self.config.get('returns', ''):
            returns_label = QLabel("Returns")
            returns_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(returns_label)

            returns_content = QLabel(returns)
            returns_content.setStyleSheet(self.INFO_STYLESHEET)
            returns_content.setWordWrap(True)
            layout.addWidget(returns_content)

        return widget

    def _update_description_text(self):
        """更新描述文字"""
        description = self.config.get('description', '')
        metrics = QFontMetrics(self.description_label.font())
        elided_text = metrics.elidedText(
            description,
            Qt.TextElideMode.ElideRight,
            300
        )
        self.description_label.setText(elided_text)
        self.description_label.setToolTip(description)

    def _calculate_expanded_height(self):
        """計算展開後需要的總高度"""
        self.details_widget.show()
        height = (self.header_widget.height() +
                  self.description_label.height() +
                  self.params_preview.height() +
                  self.details_widget.sizeHint().height() +
                  40)  # 額外空間
        return height

    def get_theme_manager(self):
        """獲取主題管理器"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent()
        return None

    def _update_theme(self):
        """更新主題"""
        if not self.theme_manager:
            return

        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        self.setStyleSheet(f"""
            KeywordCard {{
                background-color: {current_theme.SURFACE};
                border-radius: 8px;
            }}
            KeywordCard:hover {{
                background-color: {current_theme.SURFACE_VARIANT};
            }}
        """)

        self.title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {current_theme.TEXT_PRIMARY};
        """)

        self.description_label.setStyleSheet(f"""
            font-size: 12px;
            color: {current_theme.TEXT_SECONDARY};
        """)

    def mousePressEvent(self, event):
        """滑鼠按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.clicked.emit(self.card_id)

    def mouseMoveEvent(self, event):
        """滑鼠移動事件 - 處理拖放"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if not self.drag_start_position:
            return

        distance = (event.pos() - self.drag_start_position).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        card_data = {
            'id': self.card_id,
            'config': self.config
        }
        mime_data.setData('application/x-keyword',
                          QByteArray(json.dumps(card_data).encode()))

        pixmap = self.grab()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 127))
        painter.end()

        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec_(Qt.DropAction.CopyAction)

    def focusInEvent(self, event):
        """獲得焦點時展開"""
        self.is_expanded = True
        self.details_widget.show()
        target_height = self._calculate_expanded_height()

        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(target_height)
        self.min_height_animation.setStartValue(self.height())
        self.min_height_animation.setEndValue(target_height)

        self.height_animation.start()
        self.min_height_animation.start()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """失去焦點時收起"""
        self.is_expanded = False
        self.details_widget.hide()
        target_height = self.collapsed_height

        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(target_height)
        self.min_height_animation.setStartValue(self.height())
        self.min_height_animation.setEndValue(target_height)

        self.height_animation.start()
        self.min_height_animation.start()
        super().focusOutEvent(event)

    def _create_argument_widget(self, arg: dict):
        """創建參數顯示組件，添加值編輯功能"""
        # print( "_create_argument_widget")
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)

        # 參數名稱和類型標籤
        name = arg.get('name', '')
        arg_type = arg.get('type', 'any')
        param_text = f"{name}: {arg_type}"
        param_label = QLabel(param_text)
        param_label.setStyleSheet(self.PARAM_STYLESHEET)
        layout.addWidget(param_label)
        layout.addStretch()

        return widget