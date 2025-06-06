import time

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from .ExecutionPointerManager import ( ExecutionStatus, ExecutionPointerManager, ExecutionStep )
from src.utils import get_icon_path, Utils


class ExecutionStepUIWidget(QWidget):
    """執行步驟的UI元件 - 適配執行指針模式"""

    def __init__(self, step: ExecutionStep, parent=None):
        super().__init__(parent)
        self.step = step
        self.step.ui_widget = self  # 建立雙向引用

        self._setup_ui()

    def _setup_ui(self):
        """設置UI"""
        # 主垂直布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(2)

        # 第一行：基本信息（執行順序、狀態燈、名稱、時間、狀態、進度條）
        first_row = QWidget()
        first_row_layout = QHBoxLayout(first_row)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        first_row_layout.setSpacing(8)

        # 根據嵌套層級添加縮排
        indent_width = self.step.level * 20
        if indent_width > 0:
            indent_spacer = QSpacerItem(indent_width, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            first_row_layout.addItem(indent_spacer)

        # 執行順序指示器
        self.index_label = QLabel(f"#{self.step.index}")
        self.index_label.setFixedWidth(30)
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index_label.setStyleSheet("""
            color: #666666;
            font-size: 10px;
            font-weight: bold;
            background-color: #F0F0F0;
            border-radius: 3px;
            padding: 2px;
        """)
        first_row_layout.addWidget(self.index_label)

        # 狀態指示燈
        self.status_light = QLabel()
        self.status_light.setFixedSize(8, 8)
        self.status_light.setStyleSheet("background-color: #E0E0E0; border-radius: 4px;")
        first_row_layout.addWidget(self.status_light)

        # 步驟名稱
        self.name_label = QLabel(self.step.name)
        self.name_label.setStyleSheet(f"""
            font-size: {14 - self.step.level}px;
            font-weight: {'bold' if self.step.level == 0 else 'normal'};
            color: {'#333333' if self.step.level == 0 else '#666666'};
        """)
        first_row_layout.addWidget(self.name_label, 1)

        # 執行時間標籤
        self.time_label = QLabel("0.0s")
        self.time_label.setFixedWidth(50)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            color: #999999;
            font-size: 10px;
        """)
        first_row_layout.addWidget(self.time_label)

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
        first_row_layout.addWidget(self.status_label)

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
        first_row_layout.addWidget(self.progress_bar)

        # 添加第一行到主布局
        main_layout.addWidget(first_row)

        # 第二行：參數顯示（如果有參數的話）
        self.parameters_widget = self._create_parameters_widget()
        if self.parameters_widget:
            main_layout.addWidget(self.parameters_widget)

        # 設置整體樣式
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {'#FAFAFA' if self.step.level == 0 else '#F5F5F5'};
                border-radius: 4px;
                margin: 1px 0;
            }}
        """)

        # 啟動時間更新定時器
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time_display)

    def _create_parameters_widget(self):
        """創建參數顯示區域"""
        # 從步驟的原始數據中獲取參數
        parameters = self.step.original_data.get('parameters', {})

        if not parameters:
            return None

        # 創建參數容器
        params_widget = QWidget()
        params_layout = QHBoxLayout(params_widget)
        params_layout.setContentsMargins(40 + self.step.level * 20, 0, 0, 0)  # 與上行對齊
        params_layout.setSpacing(8)

        # 參數標籤
        params_label = QLabel("參數:")
        params_label.setStyleSheet("""
            font-size: 10px;
            color: #888888;
            font-weight: bold;
        """)
        params_layout.addWidget(params_label)

        # 參數值顯示
        param_items = []
        for key, value in parameters.items():
            # 清理參數值（移除多餘的引號）
            clean_value = str(value).strip('"\'')
            if clean_value == 'None':
                continue  # 跳過 None 值
            param_items.append(f"{key}={clean_value}")

        if param_items:
            params_text = ", ".join(param_items)
            params_value_label = QLabel(params_text)
            params_value_label.setStyleSheet("""
                font-size: 10px;
                color: #666666;
                background-color: #F0F8FF;
                padding: 2px 6px;
                border-radius: 3px;
                border: 1px solid #E0E0E0;
            """)
            params_layout.addWidget(params_value_label)

        params_layout.addStretch()  # 推向左側

        return params_widget if param_items else None

    def _update_time_display(self):
        """更新時間顯示"""
        execution_time = self.step.get_execution_time()
        self.time_label.setText(f"{execution_time:.1f}s")

    # 在 ExecutionStepUIWidget 類中修改 update_display() 方法

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

        # 更新執行順序指示器樣式（突出顯示當前執行步驟）
        if status == ExecutionStatus.RUNNING:
            self.index_label.setStyleSheet(f"""
                color: white;
                font-size: 10px;
                font-weight: bold;
                background-color: {colors[status]};
                border-radius: 3px;
                padding: 2px;
            """)
            # 開始時間更新
            self.timer.start(100)  # 每100ms更新一次

            # 【修改這裡】設置進度條為無限進度模式（持續跑動）
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)  # 設置為無限進度條

        else:
            self.index_label.setStyleSheet("""
                color: #666666;
                font-size: 10px;
                font-weight: bold;
                background-color: #F0F0F0;
                border-radius: 3px;
                padding: 2px;
            """)
            # 停止時間更新
            self.timer.stop()

            # 【修改這裡】恢復正常進度條模式
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)

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

        # 更新進度條值和顏色
        if status != ExecutionStatus.RUNNING and progress is not None:
            # 只有在非 RUNNING 狀態時才設置具體進度值
            self.progress_bar.setValue(progress)

        # 更新進度條顏色
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
            self.setToolTip(f"執行順序: #{self.step.index}")

        # 最終時間更新
        self._update_time_display()

class CollapsibleProgressPanel(QFrame):
    """使用執行指針系統的進度面板"""

    # 信號定義
    delete_requested = Signal(QObject)
    move_up_requested = Signal(QObject)
    move_down_requested = Signal(QObject)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)

        self.setObjectName("CollapsibleProgressPanel")
        self.config = config
        self.is_expanded = False

        # 建立執行指針管理器
        steps_data = config.get('steps', [])
        print(f"[CollapsibleProgressPanel] Steps data: {steps_data}")
        self.execution_manager = ExecutionPointerManager(steps_data)

        # UI元件列表
        self.ui_widgets = []

        # ✅ 新增：錯誤訊息管理
        self.current_error_message = ""
        self.error_history = []

        self._setup_ui()

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 設置樣式
        self.setStyleSheet("""
            #CollapsibleProgressPanel {
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

        # ✅ 新增：收縮狀態的錯誤訊息顯示
        self.collapsed_error_widget = self._create_collapsed_error_widget()
        self.main_layout.addWidget(self.collapsed_error_widget)

        # 執行指針指示器
        self.pointer_indicator = self._create_pointer_indicator()
        self.main_layout.addWidget(self.pointer_indicator)

        # 步驟容器
        self.steps_container = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(2)

        # 創建所有步驟的UI
        self._create_step_ui_widgets()
        self.main_layout.addWidget(self.steps_container)

        # ✅ 新增：展開狀態的錯誤訊息顯示
        self.expanded_error_widget = self._create_expanded_error_widget()
        self.main_layout.addWidget(self.expanded_error_widget)

        # 初始狀態設定
        self._set_initial_collapsed_state()
        self._update_expand_icon()
        self._update_statistics_display()
        self._update_pointer_indicator()

        # 時間更新定時器
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self._update_time_display)
        self.time_update_timer.start(1000)  # 每秒更新一次

    def _create_collapsed_error_widget(self):
        """創建收縮狀態的錯誤訊息顯示區域"""
        widget = QWidget()
        widget.setObjectName("collapsed-error")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # 錯誤圖標
        self.collapsed_error_icon = QLabel()
        self.collapsed_error_icon.setFixedSize(16, 16)
        self.collapsed_error_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            from src.utils import get_icon_path, Utils
            error_icon = QIcon(get_icon_path("error.svg"))
            colored_icon = Utils.change_icon_color(error_icon, "#F44336")
            self.collapsed_error_icon.setPixmap(colored_icon.pixmap(16, 16))
        except:
            self.collapsed_error_icon.setText("⚠")
            self.collapsed_error_icon.setStyleSheet("color: #F44336; font-weight: bold;")

        layout.addWidget(self.collapsed_error_icon)

        # 錯誤訊息文字（單行，省略顯示）
        self.collapsed_error_label = QLabel()
        self.collapsed_error_label.setStyleSheet("""
            QLabel {
                color: #F44336;
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }
        """)
        self.collapsed_error_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.collapsed_error_label, 1)

        # 初始隱藏
        widget.hide()
        return widget

    def _create_expanded_error_widget(self):
        """創建展開狀態的錯誤訊息顯示區域"""
        widget = QWidget()
        widget.setObjectName("expanded-error")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # 錯誤標題
        error_title = QLabel("執行錯誤")
        error_title.setStyleSheet("""
            QLabel {
                color: #F44336;
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }
        """)
        layout.addWidget(error_title)

        # 錯誤內容（多行顯示）
        self.expanded_error_label = QLabel()
        self.expanded_error_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                padding: 8px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 400;
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
            }
        """)
        self.expanded_error_label.setWordWrap(True)
        self.expanded_error_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.expanded_error_label)

        # 初始隱藏
        widget.hide()
        return widget

    def _set_initial_collapsed_state(self):
        """設置初始收縮狀態 - 確保UI一致性"""
        self.is_expanded = False

        # 隱藏展開狀態的元件
        self.steps_container.hide()
        # self.pointer_indicator.hide()
        self.expanded_error_widget.hide()

        # 顯示收縮狀態的元件（如果有錯誤的話）
        if self.current_error_message:
            self.collapsed_error_widget.show()
        else:
            self.collapsed_error_widget.hide()

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

        # 執行時間顯示
        self.time_display_label = QLabel("00:00")
        self.time_display_label.setStyleSheet("""
            font-size: 12px;
            color: #666666;
            background-color: #E9ECEF;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
            font-family: 'Courier New', monospace;
        """)
        header_layout.addWidget(self.time_display_label)

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

        # 【新增】功能按鈕群組
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(2)

        # 向上移動按鈕
        self.move_up_button = QPushButton()
        self.move_up_button.setFixedSize(18, 18)
        self.move_up_button.setToolTip("向上移動")
        self.move_up_button.clicked.connect(lambda: self.move_up_requested.emit(self))
        try:
            from src.utils import get_icon_path, Utils
            upward_icon = QIcon(get_icon_path("arrow_drop_up.svg"))
            self.move_up_button.setIcon(Utils.change_icon_color(upward_icon, "#666666"))
            self.move_up_button.setIconSize(QSize(12, 12))
        except ImportError:
            self.move_up_button.setText("↑")

        # 向下移動按鈕
        self.move_down_button = QPushButton()
        self.move_down_button.setFixedSize(18, 18)
        self.move_down_button.setToolTip("向下移動")
        self.move_down_button.clicked.connect(lambda: self.move_down_requested.emit(self))
        try:
            downward_icon = QIcon(get_icon_path("arrow_drop_down.svg"))
            self.move_down_button.setIcon(Utils.change_icon_color(downward_icon, "#666666"))
            self.move_down_button.setIconSize(QSize(12, 12))
        except ImportError:
            self.move_down_button.setText("↓")

        # 刪除按鈕
        self.delete_button = QPushButton()
        self.delete_button.setFixedSize(18, 18)
        self.delete_button.setToolTip("刪除")
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self))
        try:
            delete_icon = QIcon(get_icon_path("delete.svg"))
            self.delete_button.setIcon(Utils.change_icon_color(delete_icon, "#F44336"))
            self.delete_button.setIconSize(QSize(12, 12))
        except ImportError:
            self.delete_button.setText("×")

        # 設置按鈕統一樣式
        button_style = """
            QPushButton {
                border: none;
                border-radius: 2px;
                background: transparent;
                padding: 1px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
        """

        # 為刪除按鈕設置特殊樣式（懸停時紅色背景）
        delete_button_style = """
            QPushButton {
                border: none;
                border-radius: 2px;
                background: transparent;
                padding: 1px;
            }
            QPushButton:hover {
                background-color: #FFEBEE;
            }
            QPushButton:pressed {
                background-color: #FFCDD2;
            }
        """

        self.move_up_button.setStyleSheet(button_style)
        self.move_down_button.setStyleSheet(button_style)
        self.delete_button.setStyleSheet(delete_button_style)

        # 添加按鈕到容器
        buttons_layout.addWidget(self.move_up_button)
        buttons_layout.addWidget(self.move_down_button)
        buttons_layout.addWidget(self.delete_button)

        # 添加按鈕群組到 header
        header_layout.addWidget(buttons_container)

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

    def _create_pointer_indicator(self):
        """創建執行指針指示器"""
        indicator = QWidget()
        indicator.setFixedHeight(20)
        indicator_layout = QHBoxLayout(indicator)
        indicator_layout.setContentsMargins(10, 2, 10, 2)
        indicator_layout.setSpacing(8)

        # 指針圖標
        self.pointer_icon = QLabel("▶")
        self.pointer_icon.setFixedSize(12, 12)
        self.pointer_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pointer_icon.setStyleSheet("""
            color: #2196F3;
            font-weight: bold;
            font-size: 10px;
        """)
        indicator_layout.addWidget(self.pointer_icon)

        # 當前步驟信息
        self.current_step_label = QLabel("準備執行...")
        self.current_step_label.setStyleSheet("""
            color: #333333;
            font-size: 12px;
            font-weight: 500;
        """)
        indicator_layout.addWidget(self.current_step_label, 1)

        # 執行指針位置
        self.pointer_position_label = QLabel("0/0")
        self.pointer_position_label.setStyleSheet("""
            color: #666666;
            font-size: 10px;
            background-color: #F0F0F0;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        indicator_layout.addWidget(self.pointer_position_label)

        return indicator

    def _create_step_ui_widgets(self):
        """創建所有步驟的UI元件"""
        self.ui_widgets.clear()

        for step in self.execution_manager.execution_sequence:
            ui_widget = ExecutionStepUIWidget(step, self.steps_container)
            self.ui_widgets.append(ui_widget)
            self.steps_layout.addWidget(ui_widget)

    def update_status(self, message: dict):
        """更新狀態 - 使用執行指針系統"""
        try:
            msg_type = message.get('type', '')
            data = message.get('data', {})

            print( "="*100 + f"\n[CollapsibleProgressPanel] Processing {msg_type}")

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

            # 更新所有顯示
            self._update_statistics_display()
            self._update_overall_progress()
            self._update_pointer_indicator()
            self._update_time_display()

        except Exception as e:
            print(f"[CollapsibleProgressPanel] Error updating status: {e}")
            import traceback
            traceback.print_exc()

    def _handle_test_start(self, data):
        """處理測試開始"""
        print(f"[CollapsibleProgressPanel] Test started")
        self.execution_manager.handle_test_start(data.get('test_name', ''))
        self._update_overall_status_indicator(ExecutionStatus.RUNNING)
        # ✅ 測試開始時清空錯誤訊息
        self.clear_error_message()

    def _handle_keyword_start(self, data):
        """處理關鍵字開始"""
        robot_keyword_name = data.get('keyword_name', '')
        print(f"[CollapsibleProgressPanel] Keyword started: {robot_keyword_name}")

        step = self.execution_manager.handle_keyword_start(robot_keyword_name)
        if step:
            print(f"[CollapsibleProgressPanel] ✅ Started step #{step.index}: {step.name}")
        else:
            print(f"[CollapsibleProgressPanel] ❌ Could not start step for: {robot_keyword_name}")

    def _handle_keyword_end(self, data):
        """處理關鍵字結束"""
        robot_keyword_name = data.get('keyword_name', '')
        robot_status = data.get('status', 'UNKNOWN')
        error_message = data.get('message', '')

        print(f"[CollapsibleProgressPanel] Keyword ended: {robot_keyword_name} - {robot_status}")

        step = self.execution_manager.handle_keyword_end(robot_keyword_name, robot_status, error_message)
        if step:
            print(f"[CollapsibleProgressPanel] ✅ Completed step #{step.index}: {step.name} -> {robot_status}")

            # ✅ 處理錯誤訊息
            if robot_status == 'FAIL' and error_message.strip():
                self.update_error_message(error_message)
            elif robot_status == 'PASS':
                # 成功時清空錯誤訊息
                self.clear_error_message()

        else:
            print(f"[CollapsibleProgressPanel] ❌ Could not complete step for: {robot_keyword_name}")

    def _handle_log(self, data):
        """處理日誌"""
        level = data.get('level', '')
        message = data.get('message', '')

        if level in ['ERROR', 'FAIL']:
            print(f"[CollapsibleProgressPanel] Error log: {message}")
            # ✅ 從日誌更新錯誤訊息
            self.update_error_message(message)

    def _handle_test_end(self, data):
        """處理測試結束"""
        test_status = data.get('status', '')
        print(f"[CollapsibleProgressPanel] Test ended: {test_status}")

        self.execution_manager.handle_test_end(data.get('test_name', ''), test_status)

        if test_status == 'PASS':
            self._update_overall_status_indicator(ExecutionStatus.PASSED)
        elif test_status == 'FAIL':
            self._update_overall_status_indicator(ExecutionStatus.FAILED)

    def _update_statistics_display(self):
        """更新統計顯示 - 使用頂層步驟計數"""
        # 使用頂層進度統計
        top_level_progress = self.execution_manager.get_top_level_progress()
        status_counts = top_level_progress['status_counts']

        completed = top_level_progress['completed']
        total = top_level_progress['total']

        # 基本進度信息
        base_info = f"{completed}/{total}"

        # 詳細狀態計數
        details = []
        if status_counts['passed'] > 0:
            details.append(f"✓{status_counts['passed']}")
        if status_counts['failed'] > 0:
            details.append(f"✗{status_counts['failed']}")
        if status_counts['not_run'] > 0:
            details.append(f"◦{status_counts['not_run']}")

        if details:
            self.stats_label.setText(f"{base_info} ({' '.join(details)})")
        else:
            self.stats_label.setText(base_info)

    def _update_overall_progress(self):
        """更新整體進度條 - 使用頂層步驟進度，支援 RUNNING 動畫"""
        # 使用頂層進度統計
        top_level_progress = self.execution_manager.get_top_level_progress()
        status_counts = top_level_progress['status_counts']

        # 檢查是否有步驟正在運行
        is_running = status_counts['running'] > 0

        if is_running:
            # 【新增】如果有步驟正在運行，設置為無限進度條（持續跑動）
            self.overall_progress.setMinimum(0)
            self.overall_progress.setMaximum(0)  # 無限進度條
            chunk_color = "#2196F3"  # 運行中的藍色
        else:
            # 【新增】沒有步驟運行時，恢復正常進度條
            self.overall_progress.setMinimum(0)
            self.overall_progress.setMaximum(100)

            # 設置實際進度值
            self.overall_progress.setValue(top_level_progress['progress_percent'])

            # 根據完成狀態設置顏色
            if status_counts['failed'] > 0:
                chunk_color = "#F44336"  # 紅色
            elif status_counts['not_run'] > 0 and status_counts['passed'] > 0:
                chunk_color = "#FF9800"  # 橙色
            elif status_counts['passed'] > 0:
                chunk_color = "#4CAF50"  # 綠色
            else:
                chunk_color = "#E0E0E0"  # 等待中的灰色

        # 更新進度條樣式
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

    def _update_pointer_indicator(self):
        """更新執行指針指示器 - 使用頂層步驟指針"""
        # 使用頂層進度統計
        top_level_progress = self.execution_manager.get_top_level_progress()
        top_level_steps = top_level_progress['top_level_steps']

        # 更新位置信息 - 使用頂層步驟位置
        self.pointer_position_label.setText(f"{top_level_progress['current_pointer']}/{top_level_progress['total']}")

        # 查找當前頂層步驟
        current_top_level_step = None
        for step in top_level_steps:
            if step.status == ExecutionStatus.RUNNING:
                current_top_level_step = step
                break

        if current_top_level_step is None:
            # 找下一個待執行的頂層步驟
            for step in top_level_steps:
                if step.status == ExecutionStatus.WAITING:
                    current_top_level_step = step
                    break

        # 更新當前步驟信息
        if current_top_level_step:
            if current_top_level_step.status == ExecutionStatus.RUNNING:
                self.current_step_label.setText(f"正在執行: {current_top_level_step.name}")
                self.pointer_icon.setStyleSheet("""
                    color: #2196F3;
                    font-weight: bold;
                    font-size: 10px;
                """)
            else:
                self.current_step_label.setText(f"下一步: {current_top_level_step.name}")
                self.pointer_icon.setStyleSheet("""
                    color: #FFC107;
                    font-weight: bold;
                    font-size: 10px;
                """)
        else:
            self.current_step_label.setText("執行完成")
            self.pointer_icon.setStyleSheet("""
                color: #4CAF50;
                font-weight: bold;
                font-size: 10px;
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
        print(f"[CollapsibleProgressPanel] Resetting all status")
        self.execution_manager.reset_execution()
        self._update_statistics_display()
        self._update_overall_progress()
        self._update_pointer_indicator()
        self._update_time_display()
        self._update_overall_status_indicator(ExecutionStatus.WAITING)
        # ✅ 重置時清空錯誤訊息
        self.clear_error_message()

    def toggle_expand(self):
        """切換展開/收起狀態 - 修正版本"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            # 展開狀態
            self.steps_container.show()
            # self.pointer_indicator.show()
            self.collapsed_error_widget.hide()

            # 如果有錯誤訊息，顯示展開版本
            if self.current_error_message:
                self.expanded_error_widget.show()
            else:
                self.expanded_error_widget.hide()

        else:
            # 收縮狀態
            self.steps_container.hide()
            # self.pointer_indicator.hide()
            self.expanded_error_widget.hide()

            # 如果有錯誤訊息，顯示收縮版本
            if self.current_error_message:
                self.collapsed_error_widget.show()
            else:
                self.collapsed_error_widget.hide()

        # 更新幾何和父級ScrollArea
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

    def debug_execution_state(self):
        """調試：打印執行狀態"""
        current_step = self.execution_manager.get_current_step()
        progress = self.execution_manager.get_execution_progress()

        print(f"\n=== {self.config.get('name', 'Panel')} Execution State ===")
        print(f"Current Pointer: {progress['current_pointer']}/{progress['total']}")
        print(f"Completed: {progress['completed']} steps")
        print(f"Progress: {progress['progress_percent']}%")

        if current_step:
            print(f"Current Step: #{current_step.index} - {current_step.name} ({current_step.status.value})")
        else:
            print("Current Step: None (execution complete)")

        print("=" * 50)

    def _update_time_display(self):
        """更新時間顯示"""
        try:
            total_time = self.execution_manager.get_total_execution_time()
            formatted_time = self.execution_manager.format_time(total_time)

            # 根據執行狀態設置不同的顏色
            top_level_progress = self.execution_manager.get_top_level_progress()
            status_counts = top_level_progress['status_counts']

            if status_counts['running'] > 0:
                # 執行中 - 藍色
                time_color = "#2196F3"
                bg_color = "#E3F2FD"
            elif status_counts['failed'] > 0:
                # 有失敗 - 紅色
                time_color = "#F44336"
                bg_color = "#FFEBEE"
            elif status_counts['passed'] > 0 and status_counts['waiting'] == 0:
                # 全部完成且通過 - 綠色
                time_color = "#4CAF50"
                bg_color = "#E8F5E8"
            else:
                # 等待中 - 灰色
                time_color = "#666666"
                bg_color = "#E9ECEF"

            self.time_display_label.setText(formatted_time)
            self.time_display_label.setStyleSheet(f"""
                font-size: 12px;
                color: {time_color};
                background-color: {bg_color};
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: 600;
                font-family: 'Courier New', monospace;
            """)

        except Exception as e:
            print(f"[CollapsibleProgressPanel] Error updating time display: {e}")
            self.time_display_label.setText("--:--")

        # ✅ 新增：錯誤訊息管理方法
        def update_error_message(self, error_msg: str):
            """更新錯誤訊息"""
            try:
                self.current_error_message = error_msg.strip() if error_msg else ""

                if self.current_error_message:
                    # 記錄錯誤歷史
                    self.error_history.append({
                        'timestamp': time.time(),
                        'message': self.current_error_message
                    })

                    # 限制歷史記錄數量
                    if len(self.error_history) > 10:
                        self.error_history.pop(0)

                    # 更新收縮狀態顯示（省略長文字）
                    metrics = QFontMetrics(self.collapsed_error_label.font())
                    elided_text = metrics.elidedText(
                        self.current_error_message,
                        Qt.TextElideMode.ElideRight,
                        200  # 最大寬度
                    )
                    self.collapsed_error_label.setText(elided_text)
                    self.collapsed_error_label.setToolTip(self.current_error_message)

                    # 更新展開狀態顯示（完整文字）
                    self.expanded_error_label.setText(self.current_error_message)

                    # 根據當前狀態顯示對應的錯誤區域
                    if self.is_expanded:
                        self.collapsed_error_widget.hide()
                        self.expanded_error_widget.show()
                    else:
                        self.expanded_error_widget.hide()
                        self.collapsed_error_widget.show()

                    print(f"[CollapsibleProgressPanel] 錯誤訊息已更新: {self.current_error_message}")

                else:
                    # 清空錯誤訊息
                    self.collapsed_error_label.clear()
                    self.expanded_error_label.clear()
                    self.collapsed_error_widget.hide()
                    self.expanded_error_widget.hide()
                    print(f"[CollapsibleProgressPanel] 錯誤訊息已清空")

            except Exception as e:
                print(f"[CollapsibleProgressPanel] 更新錯誤訊息時發生異常: {e}")

        def clear_error_message(self):
            """清空錯誤訊息"""
            self.update_error_message("")

        def get_error_history(self):
            """獲取錯誤歷史"""
            return self.error_history.copy()

    # ✅ 新增：錯誤訊息管理方法
    def update_error_message(self, error_msg: str):
        """更新錯誤訊息"""
        try:
            self.current_error_message = error_msg.strip() if error_msg else ""

            if self.current_error_message:
                # 記錄錯誤歷史
                self.error_history.append({
                    'timestamp': time.time(),
                    'message': self.current_error_message
                })

                # 限制歷史記錄數量
                if len(self.error_history) > 10:
                    self.error_history.pop(0)

                # 更新收縮狀態顯示（省略長文字）
                metrics = QFontMetrics(self.collapsed_error_label.font())
                elided_text = metrics.elidedText(
                    self.current_error_message,
                    Qt.TextElideMode.ElideRight,
                    200  # 最大寬度
                )
                self.collapsed_error_label.setText(elided_text)
                self.collapsed_error_label.setToolTip(self.current_error_message)

                # 更新展開狀態顯示（完整文字）
                self.expanded_error_label.setText(self.current_error_message)

                # 根據當前狀態顯示對應的錯誤區域
                if self.is_expanded:
                    self.collapsed_error_widget.hide()
                    self.expanded_error_widget.show()
                else:
                    self.expanded_error_widget.hide()
                    self.collapsed_error_widget.show()

                print(f"[CollapsibleProgressPanel] 錯誤訊息已更新: {self.current_error_message}")

            else:
                # 清空錯誤訊息
                self.collapsed_error_label.clear()
                self.expanded_error_label.clear()
                self.collapsed_error_widget.hide()
                self.expanded_error_widget.hide()
                print(f"[CollapsibleProgressPanel] 錯誤訊息已清空")

        except Exception as e:
            print(f"[CollapsibleProgressPanel] 更新錯誤訊息時發生異常: {e}")

    def clear_error_message(self):
        """清空錯誤訊息"""
        self.update_error_message("")

    def get_error_history(self):
        """獲取錯誤歷史"""
        return self.error_history.copy()