from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from .HierarchicalStepSystem import (
    HierarchicalStepManager, ExecutionStatus, StepType, HierarchicalStep
)
from src.utils import get_icon_path, Utils


class HierarchicalStepUIWidget(QWidget):
    """階層式步驟的UI元件"""

    def __init__(self, step: HierarchicalStep, parent=None):
        super().__init__(parent)
        self.step = step
        self.step.ui_widget = self  # 建立雙向引用

        self._setup_ui()

    def _setup_ui(self):
        """設置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 根據嵌套層級添加縮排
        indent_width = self.step.path.level * 20
        if indent_width > 0:
            indent_spacer = QSpacerItem(indent_width, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            layout.addItem(indent_spacer)

        # 狀態指示燈
        self.status_light = QLabel()
        self.status_light.setFixedSize(8, 8)
        self.status_light.setStyleSheet("background-color: #E0E0E0; border-radius: 4px;")
        layout.addWidget(self.status_light)

        # 步驟名稱（包含層級信息）
        display_name = self.step.name
        if self.step.path.level > 0:
            display_name = f"{self.step.name}"  # 可以添加層級前綴如 "L{self.step.path.level}: "

        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet(f"""
            font-size: {14 - self.step.path.level}px;
            font-weight: {'bold' if self.step.path.level == 0 else 'normal'};
            color: {'#333333' if self.step.path.level == 0 else '#666666'};
        """)
        layout.addWidget(self.name_label, 1)

        # 路徑信息（調試用，可選）
        if self.step.path.level > 0:
            path_label = QLabel(f"({self.step.path})")
            path_label.setStyleSheet("font-size: 10px; color: #999999;")
            layout.addWidget(path_label)

        # 狀態標籤
        self.status_label = QLabel("WAITING")
        self.status_label.setFixedWidth(70)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #999999;
            font-size: 10px;
            font-weight: bold;
            background-color: #F0F0F0;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        layout.addWidget(self.status_label)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(60, 4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 設置整體樣式
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {'#FAFAFA' if self.step.path.level == 0 else '#F5F5F5'};
                border-radius: 4px;
                margin: 1px 0;
            }}
        """)

    def update_display(self, status: ExecutionStatus, progress: int = None, error_message: str = ""):
        """更新顯示"""
        # 狀態顏色映射
        colors = {
            ExecutionStatus.WAITING: "#E0E0E0",
            ExecutionStatus.RUNNING: "#2196F3",
            ExecutionStatus.PASSED: "#4CAF50",
            ExecutionStatus.FAILED: "#F44336",
            ExecutionStatus.NOT_RUN: "#FF9800"
        }

        # 更新狀態指示燈
        self.status_light.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 4px;
        """)

        # 更新狀態文本
        status_text = {
            ExecutionStatus.WAITING: "WAITING",
            ExecutionStatus.RUNNING: "RUNNING",
            ExecutionStatus.PASSED: "PASSED",
            ExecutionStatus.FAILED: "FAILED",
            ExecutionStatus.NOT_RUN: "NOT RUN"
        }
        self.status_label.setText(status_text[status])
        self.status_label.setStyleSheet(f"""
            color: {colors[status]};
            font-size: 10px;
            font-weight: bold;
            background-color: #F0F0F0;
            padding: 2px 6px;
            border-radius: 3px;
        """)

        # 更新進度條
        if progress is not None:
            self.progress_bar.setValue(progress)
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {colors[status]};
                    border-radius: 2px;
                }}
            """)

        # 錯誤信息處理
        if error_message:
            self.setToolTip(f"錯誤: {error_message}")
        else:
            self.setToolTip("")


class CollapsibleProgressPanel(QFrame):
    """使用階層式步驟系統的進度面板"""

    # 信號定義
    delete_requested = Signal(QObject)
    move_up_requested = Signal(QObject)
    move_down_requested = Signal(QObject)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)

        self.setObjectName("EnhancedCollapsibleProgressPanel")
        self.config = config
        self.is_expanded = False

        # 建立階層式步驟管理器
        steps_data = config.get('steps', [])
        self.step_manager = HierarchicalStepManager(steps_data)

        # UI元件列表
        self.ui_widgets = []

        self._setup_ui()

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 設置樣式
        self.setStyleSheet("""
            #EnhancedCollapsibleProgressPanel {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin: 4px 4px 0px 4px;
            }
        """)

    def _setup_ui(self):
        """設置UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(6)

        # 創建標題欄
        self.header = self._create_header()
        self.main_layout.addWidget(self.header)

        # 整體進度條
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(4)
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        self.main_layout.addWidget(self.overall_progress)

        # 步驟容器
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(2)

        # 創建所有步驟的UI
        self._create_step_ui_widgets()

        self.main_layout.addWidget(self.steps_container)

        # 初始狀態
        self.steps_container.hide()
        self._update_expand_icon()
        self._update_statistics_display()

    def _create_header(self):
        """創建標題欄"""
        header = QWidget()
        header.setStyleSheet("background-color: #FAFAFA; border-radius: 4px;")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 4, 6, 4)
        header_layout.setSpacing(8)

        # 狀態指示燈
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(10, 10)
        self.status_indicator.setStyleSheet("background-color: #FFC107; border-radius: 5px;")
        header_layout.addWidget(self.status_indicator)

        # 標題
        self.title_label = QLabel(self.config.get('name', ''))
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        header_layout.addWidget(self.title_label, 1)

        # 統計信息
        self.stats_label = QLabel("0/0")
        self.stats_label.setStyleSheet("""
            font-size: 11px;
            color: #666666;
            background-color: #E9ECEF;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
        """)
        header_layout.addWidget(self.stats_label)

        # 展開按鈕
        self.expand_button = QPushButton()
        self.expand_button.setFixedSize(20, 20)
        self.expand_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 3px;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.expand_button.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_button)

        return header

    def _create_step_ui_widgets(self):
        """創建所有步驟的UI元件"""
        self.ui_widgets.clear()

        for root_step in self.step_manager.root_steps:
            self._create_ui_for_step_recursively(root_step)

    def _create_ui_for_step_recursively(self, step: HierarchicalStep):
        """遞歸創建步驟UI元件"""
        # 為當前步驟創建UI
        ui_widget = HierarchicalStepUIWidget(step, self.steps_container)
        self.ui_widgets.append(ui_widget)
        self.steps_layout.addWidget(ui_widget)

        # 遞歸為子步驟創建UI
        for child_step in step.children:
            self._create_ui_for_step_recursively(child_step)

    def update_status(self, message: dict):
        """更新狀態 - 使用階層式步驟系統"""
        try:
            msg_type = message.get('type', '')
            data = message.get('data', {})

            print(f"[EnhancedCollapsibleProgressPanel] Processing {msg_type}")

            if msg_type == 'test_start':
                self._handle_test_start(data)
            elif msg_type == 'keyword_start':
                self._handle_keyword_start(data)
            elif msg_type == 'keyword_end':
                self._handle_keyword_end(data)
            elif msg_type == 'log':
                self._handle_log(data)
            elif msg_type == 'test_end':
                self._handle_test_end(data)

            # 更新統計顯示
            self._update_statistics_display()
            self._update_overall_progress()

        except Exception as e:
            print(f"[EnhancedCollapsibleProgressPanel] Error updating status: {e}")
            import traceback
            traceback.print_exc()

    def _handle_test_start(self, data):
        """處理測試開始"""
        print(f"[EnhancedCollapsibleProgressPanel] Test started")
        self.step_manager.reset_all_status()
        self._update_overall_status_indicator(ExecutionStatus.RUNNING)

    def _handle_keyword_start(self, data):
        """處理關鍵字開始"""
        robot_keyword_name = data.get('original_keyword_name', data.get('keyword_name', ''))
        print(f"[EnhancedCollapsibleProgressPanel] Keyword started: {robot_keyword_name}")

        step = self.step_manager.handle_keyword_start(robot_keyword_name)
        if step:
            print(f"[EnhancedCollapsibleProgressPanel] ✅ Found and updated step: {step.path}")
        else:
            print(f"[EnhancedCollapsibleProgressPanel] ❌ Could not find step for: {robot_keyword_name}")
            self._debug_print_available_steps()

    def _handle_keyword_end(self, data):
        """處理關鍵字結束"""
        robot_keyword_name = data.get('original_keyword_name', data.get('keyword_name', ''))
        robot_status = data.get('status', 'UNKNOWN')
        error_message = data.get('message', '')

        print(f"[EnhancedCollapsibleProgressPanel] Keyword ended: {robot_keyword_name} - {robot_status}")

        step = self.step_manager.handle_keyword_end(robot_keyword_name, robot_status, error_message)
        if step:
            print(f"[EnhancedCollapsibleProgressPanel] ✅ Updated step: {step.path} -> {robot_status}")
        else:
            print(f"[EnhancedCollapsibleProgressPanel] ❌ Could not find step for: {robot_keyword_name}")

    def _handle_log(self, data):
        """處理日誌"""
        level = data.get('level', '')
        message = data.get('message', '')

        if level in ['ERROR', 'FAIL']:
            print(f"[EnhancedCollapsibleProgressPanel] Error log: {message}")

    def _handle_test_end(self, data):
        """處理測試結束"""
        test_status = data.get('status', '')
        print(f"[EnhancedCollapsibleProgressPanel] Test ended: {test_status}")

        if test_status == 'PASS':
            self._update_overall_status_indicator(ExecutionStatus.PASSED)
        elif test_status == 'FAIL':
            self._update_overall_status_indicator(ExecutionStatus.FAILED)

    def _debug_print_available_steps(self):
        """調試用：打印所有可用步驟"""
        print(f"[DEBUG] Available steps in step_manager:")
        for path_id, step in self.step_manager.step_registry.items():
            completed = self.step_manager.execution_context.is_step_completed(step.path)
            print(f"  - {path_id}: {step.name} (type: {step.step_type.value}, completed: {completed})")

    def _update_statistics_display(self):
        """更新統計顯示"""
        stats = self.step_manager.get_step_statistics()
        completed = stats['passed'] + stats['failed'] + stats['not_run']
        total = stats['total']

        # 基本進度信息
        base_info = f"{completed}/{total}"

        # 詳細狀態計數
        details = []
        if stats['passed'] > 0:
            details.append(f"✓{stats['passed']}")
        if stats['failed'] > 0:
            details.append(f"✗{stats['failed']}")
        if stats['not_run'] > 0:
            details.append(f"◦{stats['not_run']}")

        if details:
            self.stats_label.setText(f"{base_info} ({' '.join(details)})")
        else:
            self.stats_label.setText(base_info)

    def _update_overall_progress(self):
        """更新整體進度條"""
        stats = self.step_manager.get_step_statistics()
        completed = stats['passed'] + stats['failed'] + stats['not_run']
        total = stats['total']

        if total > 0:
            progress_percent = int((completed / total) * 100)
            self.overall_progress.setValue(progress_percent)

            # 根據狀態設置進度條顏色
            if stats['failed'] > 0:
                chunk_color = "#F44336"  # 紅色
            elif stats['not_run'] > 0 and stats['passed'] > 0:
                chunk_color = "#FF9800"  # 橙色
            elif stats['passed'] > 0:
                chunk_color = "#4CAF50"  # 綠色
            else:
                chunk_color = "#2196F3"  # 藍色

            self.overall_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 2px;
                }}
            """)

    def _update_overall_status_indicator(self, status: ExecutionStatus):
        """更新整體狀態指示燈"""
        colors = {
            ExecutionStatus.WAITING: "#FFC107",
            ExecutionStatus.RUNNING: "#2196F3",
            ExecutionStatus.PASSED: "#4CAF50",
            ExecutionStatus.FAILED: "#F44336",
            ExecutionStatus.NOT_RUN: "#FF9800"
        }

        self.status_indicator.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 5px;
        """)

    def reset_status(self):
        """重置狀態"""
        print(f"[EnhancedCollapsibleProgressPanel] Resetting all status")
        self.step_manager.reset_all_status()
        self._update_statistics_display()
        self._update_overall_progress()
        self._update_overall_status_indicator(ExecutionStatus.WAITING)

    def toggle_expand(self):
        """切換展開/收起狀態"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.steps_container.show()
        else:
            self.steps_container.hide()

        self.updateGeometry()
        self.adjustSize()

        # 更新父級ScrollArea
        scroll_area = None
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scroll_area = parent
                break
            parent = parent.parent()

        if scroll_area:
            scroll_area.viewport().update()

        self._update_expand_icon()

    def _update_expand_icon(self):
        """更新展開圖標"""
        icon_name = "navigate_up.svg" if self.is_expanded else "navigate_down.svg"
        icon = QIcon(get_icon_path(icon_name))
        colored_icon = Utils.change_icon_color(icon, "#666666")
        self.expand_button.setIcon(colored_icon)
        self.expand_button.setIconSize(QSize(12, 12))

    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)

        delete_action = context_menu.addAction("刪除")
        move_up_action = context_menu.addAction("向上移動")
        move_down_action = context_menu.addAction("向下移動")

        try:
            delete_icon = QIcon(get_icon_path("delete.svg"))
            delete_action.setIcon(Utils.change_icon_color(delete_icon, "#000000"))

            upward_icon = QIcon(get_icon_path("arrow_drop_up.svg"))
            move_up_action.setIcon(Utils.change_icon_color(upward_icon, "#000000"))

            downward_icon = QIcon(get_icon_path("arrow_drop_down.svg"))
            move_down_action.setIcon(Utils.change_icon_color(downward_icon, "#000000"))
        except ImportError:
            pass

        action = context_menu.exec_(self.mapToGlobal(position))

        if action == delete_action:
            self.delete_requested.emit(self)
        elif action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)
