# components/base/BaseKeywordCard.py
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
            BaseKeywordCard {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid transparent;                
            }
            BaseKeywordCard:hover {
                background-color: #F8F9FA;
                border: 1px solid #006C4D;
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

        self._setup_shadow()

        # UI 初始化
        self.setMaximumWidth(400)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setContentsMargins(16, 16, 16, 16)
        self._setup_layout()

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

        self.setObjectName("keyword-card")
        self.setStyleSheet(self.CARD_STYLESHEET)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def _init_argument_values(self):
        """Initialize argument values with their defaults"""
        for arg in self.config.get('arguments', []):
            self.argument_values[arg['name']] = arg.get('default')

    def _setup_shadow(self):
        """設置陰影效果"""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

    def _setup_layout(self):
        """設置主布局"""
        layout = QVBoxLayout(self)
        # 將主布局的邊距設為 0，而是由卡片的 contentsMargins 來控制
        layout.setContentsMargins(0, 0, 0, 0)
        # 為每個元素之間設置統一的間距
        layout.setSpacing(8)

        # 標題區域
        self.header_widget = self._create_header()
        layout.addWidget(self.header_widget)

        # 簡短描述區域 - 折疊時顯示
        self.description_container = QWidget()
        description_layout = QHBoxLayout(self.description_container)
        description_layout.setContentsMargins(0, 0, 0, 0)

        self.collapsed_description_label = QLabel()
        self.collapsed_description_label.setStyleSheet(self.INFO_STYLESHEET)
        self.collapsed_description_label.setWordWrap(True)
        self.collapsed_description_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        description_layout.addWidget(self.collapsed_description_label)

        layout.addWidget(self.description_container)

        # 參數預覽
        params_container = QWidget()
        params_layout = QHBoxLayout(params_container)
        params_layout.setContentsMargins(0, 0, 0, 0)

        self.params_preview = self._create_params_preview()
        params_layout.addWidget(self.params_preview)

        layout.addWidget(params_container)

        # 展開時顯示的詳細信息
        self.details_widget = self._create_details_widget()
        self.details_widget.hide()
        layout.addWidget(self.details_widget)

        layout.addStretch()

        # 更新描述文字
        self._update_description_text()

    # region UI
    def _create_header(self):
        """創建標題區域"""
        header_widget = QWidget()
        # 將 header 內部的邊距設為 0，而是通過布局的 spacing 來控制間距
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_layout.setSpacing(12)  # 設置標題與分類標籤之間的間距

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
        self.category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.category_label, 0)

        return header_widget

    def _create_params_preview(self):
        """創建參數預覽"""
        params = self.config.get('arguments', [])
        label = QLabel(f"{len(params)} Arguments")
        label.setStyleSheet(f"""
            background-color: #E0E0E0;
            color: #333333;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 14px;
            font-weight: bold;
        """)
        return label

    def _create_details_widget(self):
        """創建詳細信息區域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # 詳細信息區不需要額外的邊距，因為卡片已有邊距
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)  # 增加詳細區域的元素間距

        # 完整描述
        if description := self.config.get('description', ''):
            desc_section = QWidget()
            desc_layout = QVBoxLayout(desc_section)
            desc_layout.setContentsMargins(0, 0, 0, 0)
            desc_layout.setSpacing(4)

            desc_label = QLabel("Description")
            desc_label.setStyleSheet("font-weight: bold;")
            desc_layout.addWidget(desc_label)

            # 創建完整描述的標籤
            desc_content = QLabel(description)
            desc_content.setStyleSheet(self.INFO_STYLESHEET)
            desc_content.setWordWrap(True)  # 確保可以自動換行
            desc_content.setTextFormat(Qt.TextFormat.PlainText)  # 使用純文本格式
            desc_layout.addWidget(desc_content)

            layout.addWidget(desc_section)

        # 參數列表
        if arguments := self.config.get('arguments', []):
            args_section = QWidget()
            args_section_layout = QVBoxLayout(args_section)
            args_section_layout.setContentsMargins(0, 0, 0, 0)
            args_section_layout.setSpacing(0)

            args_label = QLabel("Arguments")
            args_label.setStyleSheet("font-weight: bold;")
            args_section_layout.addWidget(args_label)

            args_widget = QWidget()
            args_layout = QVBoxLayout(args_widget)
            args_layout.setContentsMargins(0, 0, 0, 0)
            args_layout.setSpacing(0)  # 增加參數項之間的間距

            for arg in arguments:
                arg_widget = self._create_argument_widget(arg)
                args_layout.addWidget(arg_widget)

            args_section_layout.addWidget(args_widget)
            layout.addWidget(args_section)

        # 返回值
        if returns := self.config.get('returns', ''):
            returns_section = QWidget()
            returns_layout = QVBoxLayout(returns_section)
            returns_layout.setContentsMargins(0, 0, 0, 0)
            returns_layout.setSpacing(4)

            returns_label = QLabel("Returns")
            returns_label.setStyleSheet("font-weight: bold;")
            returns_layout.addWidget(returns_label)

            returns_content = QLabel(returns)
            returns_content.setStyleSheet(self.INFO_STYLESHEET)
            returns_content.setWordWrap(True)
            returns_layout.addWidget(returns_content)

            layout.addWidget(returns_section)

        return widget

    def _update_description_text(self):
        """更新描述文字"""
        description = self.config.get('description', '')

        # 設置摺疊狀態的描述 (截斷版本)
        metrics = QFontMetrics(self.collapsed_description_label.font())
        elided_text = metrics.elidedText(
            description,
            Qt.TextElideMode.ElideRight,
            300
        )
        self.collapsed_description_label.setText(elided_text)
        self.collapsed_description_label.setToolTip(description)

        # 確保描述容器的高度適合
        self.collapsed_description_label.setMinimumHeight(40)
        self.collapsed_description_label.setMaximumHeight(40)

    def _calculate_expanded_height(self):
        """計算展開後需要的總高度"""
        # 確保詳細部分可見以計算高度
        self.details_widget.show()

        # 計算總高度
        height = (self.header_widget.height() +
                  self.params_preview.height() +
                  self.details_widget.sizeHint().height() +
                  60)  # 額外空間

        # 計算完成後再隱藏詳細部分（如果當前未展開）
        if not self.is_expanded:
            self.details_widget.hide()

        return height

    def _create_argument_widget(self, arg: dict):
        """創建參數顯示組件，添加值編輯功能"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        # 減少參數內部的左右邊距，使其更緊湊
        widget.setMinimumHeight(40)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)

        # 參數名稱和類型標籤
        name = arg.get('name', '')
        arg_type = arg.get('type', 'any')
        param_text = f"{name}: {arg_type}"
        param_label = QLabel(param_text)
        param_label.setStyleSheet(self.PARAM_STYLESHEET)
        layout.addWidget(param_label)
        layout.addStretch()

        return widget

    # endregion

    # region EVENT
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

        # 隱藏摺疊時的描述
        self.description_container.hide()

        # 顯示詳細信息
        self.details_widget.show()

        # 計算並設置新高度
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

        # 關閉詳細信息並顯示摺疊的描述
        self.details_widget.hide()
        self.description_container.show()

        # 回到摺疊高度
        target_height = self.collapsed_height

        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(target_height)
        self.min_height_animation.setStartValue(self.height())
        self.min_height_animation.setEndValue(target_height)

        self.height_animation.start()
        self.min_height_animation.start()
        super().focusOutEvent(event)
    # endregion