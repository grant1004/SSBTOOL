# components/base/BaseCard.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json


class BaseCard(QFrame):
    """基礎卡片元件"""
    clicked = Signal(str)
    delete_requested = Signal(str)  # 新增刪除信號，傳遞 card_id

    PRIORITIES = ['required', 'normal', 'optional']
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
        self.setAcceptDrops(True)
        self.drag_start_position = None
        self.card_id = card_id
        self.config = config
        self.is_expanded = False
        self.priority = self.config.get('priority', 'normal').lower()

        # UI 初始化
        self._setup_ui()
        self.setObjectName("base-card")
        self.setStyleSheet(self.CARD_STYLESHEET)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # 高度設置
        self.collapsed_height = 100
        self.expanded_height = 800
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

    def _setup_ui(self):
        """初始化 UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
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

        # 標題
        self.title_label = QLabel(self.config.get('name', ''))
        self.title_label.setStyleSheet(self.TITLE_STYLESHEET)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.title_label.setFixedWidth(180)  # 調整寬度為刪除按鈕騰出空間
        self.title_label.setWordWrap(True)  # 啟用自動換行

        # 右側資訊容器
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        # 預估時間
        self.time_label = self._create_time_label()
        info_layout.addWidget(self.time_label)

        # 優先級
        self.priority_label = self._create_priority_label()
        info_layout.addWidget(self.priority_label)

        # 刪除按鈕
        self.delete_button = self._create_delete_button()
        info_layout.addWidget(self.delete_button)

        header_layout.addWidget(self.title_label, 1)  # 1表示可伸縮
        header_layout.addWidget(info_widget, 0)  # 0表示固定大小

        return header_widget

    def _create_delete_button(self):
        """創建刪除按鈕"""
        delete_button = QPushButton()
        delete_button.setFixedSize(20, 20)
        delete_button.setToolTip("刪除此測試案例")
        delete_button.clicked.connect(self._on_delete_clicked)

        # 設置刪除圖標 (如果有圖標系統的話)
        try:
            from src.utils import get_icon_path, Utils
            delete_icon = QIcon(get_icon_path("delete.svg"))
            delete_button.setIcon(Utils.change_icon_color(delete_icon, "#F44336"))
            delete_button.setIconSize(QSize(14, 14))
        except ImportError:
            # 如果沒有圖標系統，使用文字
            delete_button.setText("×")
            delete_button.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                    color: #F44336;
                }
            """)

        # 設置按鈕樣式
        delete_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 10px;
                background: transparent;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #FFEBEE;
            }
            QPushButton:pressed {
                background-color: #FFCDD2;
            }
        """)

        return delete_button

    def _on_delete_clicked(self):
        """處理刪除按鈕點擊事件"""
        # 顯示確認對話框
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"您確定要刪除測試案例 '{self.config.get('name', self.card_id)}' 嗎？\n\n此操作無法復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 發出刪除請求信號
            self.delete_requested.emit(self.card_id)

    def _create_time_label(self):
        """創建時間標籤"""
        time_value = self.config.get('estimated_time', '0min')
        # 移除 'min' 後綴並轉換為整數
        if isinstance(time_value, str):
            time_value = time_value.replace('min', '')
        try:
            minutes = int(time_value)
            # 如果超過60分鐘，轉換為小時表示
            if minutes >= 60:
                hours = minutes / 60
                time_text = f"{hours:.1f}h"
            else:
                time_text = f"{minutes}min"
        except (ValueError, TypeError):
            time_text = "0min"

        label = QLabel(time_text)
        label.setStyleSheet(f"""
            background-color: #E0E0E0;
            color: #333333;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        return label

    def _setup_layout(self):
        """設置主布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 標題區域
        self.header_widget = self._create_header()
        layout.addWidget(self.header_widget)

        # 描述文字
        self.description_label = QLabel()
        self.description_label.setStyleSheet(self.INFO_STYLESHEET)
        self.description_label.setWordWrap(True)
        self._update_description_text()
        layout.addWidget(self.description_label)

        # 步驟信息
        self.steps_info = self._create_steps_info()
        layout.addWidget(self.steps_info)

        # 展開時顯示的詳細信息容器
        self.details_widget = self._create_details_widget()
        self.details_widget.hide()
        layout.addWidget(self.details_widget)

        layout.addStretch()

    def _create_priority_label(self):
        """創建優先級標籤"""
        priority_text = self.priority.capitalize()
        priority_color = self.PRIORITY_COLORS.get(self.priority, self.PRIORITY_COLORS['normal'])

        label = QLabel(priority_text)
        label.setStyleSheet(f"""
            background-color: {priority_color};
            {self.PRIORITY_STYLESHEET}
        """)
        return label

    def _create_steps_info(self):
        """創建步驟信息標籤"""
        steps_count = len(self.config.get('steps', []))
        label = QLabel(f"{steps_count} Steps")
        label.setStyleSheet(f"""
                    background-color: #E0E0E0;
                    color: #333333;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                    font-weight: bold;
                """)
        return label

    def _create_details_widget(self):
        """創建詳細信息區域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 處理新格式的依賴信息
        dependencies = self.config.get('dependencies', {})

        # 前置條件（保持向下兼容）
        preconditions = self.config.get('setup', {}).get('preconditions', [])
        if preconditions:
            precond_label = QLabel("Preconditions:")
            precond_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(precond_label)

            for precond in preconditions:
                item_label = QLabel(f"    • {precond}")
                item_label.setStyleSheet(self.INFO_STYLESHEET)
                layout.addWidget(item_label)

        # 新格式的 libraries 依賴
        libraries = dependencies.get('libraries', [])
        if not libraries:
            # 向下兼容舊格式
            libraries = self.config.get('setup', {}).get('library', [])

        if libraries:
            library_label = QLabel("Required Libraries:")
            library_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(library_label)

            for lib in libraries:
                item_label = QLabel(f"    • {lib}")
                item_label.setStyleSheet(self.INFO_STYLESHEET)
                layout.addWidget(item_label)

        # 新格式的 keywords 依賴
        keywords = dependencies.get('keywords', [])
        if keywords:
            keywords_label = QLabel("Required Keywords:")
            keywords_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(keywords_label)

            for keyword in keywords:
                item_label = QLabel(f"    • {keyword}")
                item_label.setStyleSheet(self.INFO_STYLESHEET)
                layout.addWidget(item_label)

        # 步驟詳情
        steps = self.config.get('steps', [])
        if steps:
            steps_label = QLabel("Steps:")
            steps_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(steps_label)

            for i, step in enumerate(steps, 1):
                step_widget = self._create_step_widget(step, i)
                layout.addWidget(step_widget)

        return widget

    def _create_step_widget(self, step: dict, step_number: int):
        """創建單個步驟的顯示組件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)

        # 判斷步驟類型並顯示相應信息
        step_type = step.get('step_type', step.get('type', 'unknown'))

        if step_type == 'keyword':
            # 新格式的 keyword 步驟
            keyword_name = step.get('keyword_name', 'Unknown Keyword')
            keyword_category = step.get('keyword_category', '')
            parameters = step.get('parameters', {})

            # 步驟標題
            title_text = f"{step_number}. {keyword_name}"
            if keyword_category:
                title_text += f" ({keyword_category})"

            title = QLabel(title_text)
            title.setStyleSheet("font-weight: bold;")
            layout.addWidget(title)

            # 參數信息
            if parameters:
                params_text = ", ".join([f"{k}={v}" for k, v in parameters.items()])
                param_label = QLabel(f"Parameters: {params_text}")
                param_label.setStyleSheet(self.INFO_STYLESHEET)
                layout.addWidget(param_label)

        elif step_type == 'testcase':
            # 嵌套的 testcase 步驟
            testcase_name = step.get('testcase_name', step.get('name', 'Unknown Testcase'))

            title = QLabel(f"{step_number}. [Testcase] {testcase_name}")
            title.setStyleSheet("font-weight: bold; color: #0066CC;")
            layout.addWidget(title)

        else:
            # 舊格式或其他格式的步驟（向下兼容）
            step_name = step.get('name', step.get('action', f'Step {step_number}'))
            title = QLabel(f"{step_number}. {step_name}")
            title.setStyleSheet("font-weight: bold;")
            layout.addWidget(title)

            # 動作信息（舊格式）
            if action := step.get('action'):
                action_label = QLabel(f"Action: {action}")
                action_label.setStyleSheet(self.INFO_STYLESHEET)
                layout.addWidget(action_label)

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

        # 更新卡片樣式
        self.setStyleSheet(f"""
            BaseCard {{
                background-color: {current_theme.SURFACE};
                border-radius: 8px;
            }}
            BaseCard:hover {{
                background-color: {current_theme.SURFACE_VARIANT};
            }}
        """)

        # 更新文字顏色
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
        mime_data.setData('application/x-testcase',
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

    def _calculate_height(self):
        # 基礎高度（標題+ 描述 + 步驟數量）
        base_height = self.collapsed_height
        # 獲取詳細信息區域實際需要的高度
        self.details_widget.show()  # 暫時顯示以計算高度
        details_height = self.details_widget.sizeHint().height()
        # self.details_widget.hide()  # 恢復隱藏狀態

        # 計算總高度（基礎高度 + 詳細信息高度 + 邊距）
        total_height = base_height + details_height + 20  # 20是額外邊距

        # print( total_height )

        return total_height

    def focusInEvent(self, event):
        """獲得焦點時展開"""
        self.is_expanded = True
        self.details_widget.show()
        target_height = self._calculate_height()

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