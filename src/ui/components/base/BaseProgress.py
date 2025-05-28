from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from enum import Enum
from src.utils import get_icon_path, Utils


class TestStatus(Enum):
    WAITING = "waiting"  # 等待執行
    RUNNING = "running"  # 執行中
    PASSED = "passed"  # 通過
    FAILED = "failed"  # 失敗


class KeywordProgressItem(QWidget):
    """關鍵字進度項組件"""

    def __init__(self, keyword, parent=None):
        super().__init__(parent)
        self.keyword = keyword.get('name', '')
        self.status = TestStatus.WAITING
        self.progress = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 狀態指示燈
        self.status_light = QLabel()
        self.status_light.setFixedSize(8, 8)
        self.status_light.setStyleSheet("""
            background-color: #E0E0E0;
            border-radius: 4px;
        """)

        # 關鍵字文本
        self.keyword_label = QLabel(self.keyword)
        self.keyword_label.setStyleSheet("""
            color: #333333;
            font-size: 12px;
        """)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F5F5F5;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # 狀態文本
        self.status_label = QLabel("WAITING")
        self.status_label.setFixedWidth(70)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("""
            color: #999999;
            font-size: 11px;
            font-weight: bold;
        """)

        # 添加到布局
        layout.addWidget(self.status_light)
        layout.addWidget(self.keyword_label, 1)
        layout.addWidget(self.progress_bar, 2)
        layout.addWidget(self.status_label)

    def update_status(self, status: TestStatus, progress: int = None, error_msg: str = None):
        """更新狀態和進度"""
        self.status = status
        if progress is not None:
            self.progress = progress
            self.progress_bar.setValue(progress)

        # 更新狀態指示燈
        colors = {
            TestStatus.WAITING: "#E0E0E0",  # 灰色
            TestStatus.RUNNING: "#2196F3",  # 藍色
            TestStatus.PASSED: "#4CAF50",  # 綠色
            TestStatus.FAILED: "#F44336"  # 紅色
        }
        self.status_light.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 4px;
        """)

        # 更新進度條顏色
        progress_color = "#4CAF50"  # 默認綠色
        if status == TestStatus.FAILED:
            progress_color = "#F44336"  # 失敗時為紅色
        elif status == TestStatus.RUNNING:
            progress_color = "#2196F3"  # 執行中為藍色

        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #F5F5F5;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {progress_color};
                border-radius: 2px;
            }}
        """)

        # 更新狀態文本
        status_text = {
            TestStatus.WAITING: "WAITING",
            TestStatus.RUNNING: "RUNNING",
            TestStatus.PASSED: "PASSED",
            TestStatus.FAILED: "FAILED"
        }
        self.status_label.setText(status_text[status])

        # 更新狀態文本顏色
        status_colors = {
            TestStatus.WAITING: "#999999",
            TestStatus.RUNNING: "#2196F3",
            TestStatus.PASSED: "#4CAF50",
            TestStatus.FAILED: "#F44336"
        }
        self.status_label.setStyleSheet(f"""
            color: {status_colors[status]};
            font-size: 11px;
            font-weight: bold;
        """)


class CollapsibleProgressPanel(QFrame):
    """可展開的進度面板"""
    # 新增信號用於菜單操作
    delete_requested = Signal(QObject)  # 刪除請求信號
    move_up_requested = Signal(QObject)  # 向上移動請求信號
    move_down_requested = Signal(QObject)  # 向下移動請求信號

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)

        self.setObjectName("CollapsibleProgressPanel")
        self.config = config
        self.is_expanded = False

        # 處理新格式的 steps，轉換為舊格式以保持 UI 兼容
        self.keywords = self._convert_steps_format(config.get('steps', []))
        self.keyword_items = []
        self.current_keyword_index = -1
        self._setup_ui()

        self.setStyleSheet("""
                #CollapsibleProgressPanel {
                    background-color: #FFFFFF;
                    border: 2px solid #A0A0A0;
                    margin: 8px 8px 0px 8px  ;  
                }
            """)
        # margin top right bottom left

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _convert_steps_format(self, steps):
        """將新格式的 steps 轉換為舊格式，保持 UI 兼容性"""
        converted_steps = []

        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                step_type = step.get('step_type', step.get('type', 'unknown'))

                if step_type == 'keyword':
                    # 新格式的 keyword 步驟
                    keyword_name = step.get('keyword_name', 'Unknown Keyword')
                    keyword_category = step.get('keyword_category', '')
                    parameters = step.get('parameters', {})
                    description = step.get('description', '')

                    # 轉換為舊格式
                    converted_step = {
                        'step_id': i,
                        'name': keyword_name,
                        'action': f"{keyword_name} ({keyword_category})" if keyword_category else keyword_name,
                        'params': parameters,
                        'expected': description or f"執行 {keyword_name} 成功"
                    }

                elif step_type == 'testcase':
                    # 嵌套的 testcase 步驟
                    testcase_name = step.get('testcase_name', step.get('name', 'Unknown Testcase'))
                    parameters = step.get('parameters', {})

                    converted_step = {
                        'step_id': i,
                        'name': f"[Testcase] {testcase_name}",
                        'action': f"執行測試案例: {testcase_name}",
                        'params': parameters,
                        'expected': f"測試案例 {testcase_name} 執行成功"
                    }

                else:
                    # 舊格式或其他格式（向下兼容）
                    converted_step = {
                        'step_id': step.get('step_id', i),
                        'name': step.get('name', f'步驟{i}'),
                        'action': step.get('action', f'執行動作{i}'),
                        'params': step.get('params', {}),
                        'expected': step.get('expected', f'預期結果{i}')
                    }

                converted_steps.append(converted_step)

        return converted_steps

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(8)

        # 標題欄
        self.header = QWidget()
        self.header.setStyleSheet("radius: 4px;")
        self.header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 0, 0, 0)
        header_layout.setSpacing(8)

        # 狀態指示燈
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.status_indicator.setStyleSheet("""
            background-color: #FFC107;
            border-radius: 6px;
        """)

        # 標題
        self.title_label = QLabel(self.config.get('name', ''))
        self.title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
        """)

        # 展開/收起按鈕
        self.expand_button = QPushButton()
        self.expand_button.setFixedSize(16, 16)
        self.expand_button.setStyleSheet("""
            QPushButton {
                border: none;
                radius: 4px;
                background: #000000;
            }
        """)
        self.expand_button.clicked.connect(self.toggle_expand)

        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.expand_button)

        # 整體進度條
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(4)
        self.overall_progress.setRange(0, len(self.keywords))
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                background-color: #F5F5F5;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # 關鍵字列表容器
        self.keywords_container = QWidget()
        self.keywords_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.keywords_layout = QVBoxLayout(self.keywords_container)
        self.keywords_layout.setContentsMargins(0, 0, 0, 0)
        self.keywords_layout.setSpacing(8)

        # 創建所有關鍵字項
        for keyword in self.keywords:
            item = KeywordProgressItem(keyword, self)
            self.keyword_items.append(item)
            self.keywords_layout.addWidget(item)

        # 添加到主布局
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.overall_progress)
        self.main_layout.addWidget(self.keywords_container)

        # 初始設置
        self.keywords_container.hide()
        self._update_expand_icon()

    def toggle_expand(self):
        """切換展開/收起狀態"""
        self.is_expanded = not self.is_expanded

        # 更新前先確保所有的尺寸更新已經完成
        QApplication.processEvents()

        if self.is_expanded:
            self.keywords_container.show()
        else:
            self.keywords_container.hide()

        # 更新布局
        self.updateGeometry()
        self.adjustSize()

        # 找到 ScrollArea 父組件
        scroll_area = None
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scroll_area = parent
                break
            parent = parent.parent()

        # 如果找到了 ScrollArea，更新它
        if scroll_area:
            scroll_area.viewport().update()

        self._update_expand_icon()

    def _update_expand_icon(self):
        """更新展開/收起圖標"""
        icon = QIcon(get_icon_path("navigate_down.svg" if not self.is_expanded else "navigate_up.svg"))
        self.expand_button.setIcon(icon)
        self.expand_button.setIconSize(QSize(24, 24))

    def mousePressEvent(self, event):
        """處理整個面板的點擊事件"""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self.header.geometry().contains(event.pos()):
                self.toggle_expand()

    def update_keyword_status(self, index: int, status: TestStatus, progress: int = None):
        """更新特定關鍵字的狀態"""
        if 0 <= index < len(self.keyword_items):
            self.keyword_items[index].update_status(status, progress)

            # 更新整體進度
            if status == TestStatus.PASSED:
                self.overall_progress.setValue(index + 1)

            # 更新整體狀態
            if status == TestStatus.FAILED:
                self.update_overall_status(TestStatus.FAILED)

    def update_overall_status(self, status: TestStatus):
        """更新整體狀態"""
        colors = {
            TestStatus.WAITING: "#FFC107",
            TestStatus.RUNNING: "#2196F3",
            TestStatus.PASSED: "#4CAF50",
            TestStatus.FAILED: "#F44336"
        }

        self.status_indicator.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 6px;
        """)

        if status == TestStatus.FAILED:
            self.overall_progress.setStyleSheet("""
                QProgressBar {
                    background-color: #F5F5F5;
                    border: none;
                    border-radius: 2px;
                }
                QProgressBar::chunk {
                    background-color: #F44336;
                    border-radius: 2px;
                }
            """)

    def reset_status(self):
        """重置所有關鍵字的狀態和進度"""
        for item in self.keyword_items:
            item.update_status(TestStatus.WAITING, 0)

        self.overall_progress.setValue(0)
        self.update_overall_status(TestStatus.WAITING)

    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)

        # 新增選單項目
        delete_action = context_menu.addAction("刪除")
        move_up_action = context_menu.addAction("向上移動")
        move_down_action = context_menu.addAction("向下移動")

        # 設置圖標（可選）
        delete_icon = QIcon(get_icon_path("delete.svg"))
        delete_action.setIcon(Utils.change_icon_color(delete_icon, "#000000"))

        upward_icon = QIcon(get_icon_path("arrow_drop_up.svg"))
        move_up_action.setIcon(Utils.change_icon_color(upward_icon, "#000000"))

        downward_icon = QIcon(get_icon_path("arrow_drop_down.svg"))
        move_down_action.setIcon(Utils.change_icon_color(downward_icon, "#000000"))

        # 獲取所選操作
        action = context_menu.exec_(self.mapToGlobal(position))

        # 處理所選操作
        if action == delete_action:
            self.delete_requested.emit(self)
        elif action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)