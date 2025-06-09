from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json

from src.utils import Utils, get_icon_path


class BaseKeywordProgressCard(QFrame):
    """關鍵字進度卡片元件 - 重構版本，支持參數選項顯示"""
    STATUS_COLORS = {
        'waiting': '#FFA000',  # 黃色
        'running': '#2196F3',  # 藍色
        'passed': '#4CAF50',  # 綠色
        'failed': '#F44336',  # 紅色
        'not_run': '#FF9800'  # 橙色
    }

    parameter_changed = Signal(str, str)  # (參數名, 新值)

    # 新增信號用於菜單操作
    delete_requested = Signal(QObject)  # 刪除請求信號
    move_up_requested = Signal(QObject)  # 向上移動請求信號
    move_down_requested = Signal(QObject)  # 向下移動請求信號

    def __init__(self, keyword_config: dict, parent=None):
        super().__init__(parent)

        # print(keyword_config)

        self.keyword_config = keyword_config
        self.status = 'waiting'
        self.progress = 0
        self.execution_time = 0

        # 初始化參數值字典
        self.param_values = {}
        self._init_param_values()

        # UI 初始化
        self._setup_ui()
        self.setObjectName("keyword-progress-card")

        self.setStyleSheet("""
            #keyword-progress-card {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin: 4px 4px 0px 4px;
            }
        """)

        # 動態計算高度
        self._calculate_height()

        # running Timer
        self.timer = QTimer()
        self.timer.setInterval(100)  # 每0.1秒更新一次
        self.timer.timeout.connect(self._update_running_time)
        self.start_time = None

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _calculate_height(self):
        """動態計算高度 - 確保按鈕顯示正確"""
        base_height = 160  # 【調整】增加基礎高度以容納按鈕
        param_count = len(self.keyword_config.get('arguments', []))
        param_height = param_count * 36 if param_count > 0 else 0
        total_height = base_height + param_height
        self.setMinimumHeight(total_height)

    def _setup_ui(self):
        """初始化 UI - 重構版本"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)  # 與 CollapsibleProgressPanel 一致的間距
        layout.setSpacing(4)  # 緊湊的間距

        # 創建各個區域
        header_section = self._create_header_section()
        params_section = self._create_params_section()
        progress_section = self._create_progress_section()
        error_section = self._create_error_section()

        # 添加到主布局
        layout.addWidget(header_section)
        if params_section:
            layout.addWidget(params_section)
        layout.addWidget(progress_section)
        layout.addWidget(error_section)

    def _create_header_section(self):
        """創建標題區域 - 重構版本"""
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #F0F8FF;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }
        """)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        # Keyword 名稱 - 標題樣式
        name_label = QLabel(self.keyword_config.get('name', ''))
        name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #2C3E50;
            background: transparent;
        """)
        header_layout.addWidget(name_label, 1)  # 讓名稱占據剩餘空間

        # 類別標籤 - 重新設計
        category = self.keyword_config.get('category', '')
        category_label = QLabel(category)
        category_label.setStyleSheet("""
            background-color: #1976D2;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        """)
        header_layout.addWidget(category_label)

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

        return header_widget

    def _create_params_section(self):
        """創建參數輸入區域 - 重構版本，支持選項顯示"""
        arguments = self.keyword_config.get('arguments', [])
        if not arguments:
            return None

        params_widget = QWidget()
        params_widget.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border: none;
                border-radius: 4px;
            }
        """)

        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(10, 8, 10, 8)
        params_layout.setSpacing(6)

        # 參數標題 - 標題樣式
        params_title = QLabel("參數設定")
        params_title.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #34495E;
            background: transparent;
        """)
        params_layout.addWidget(params_title)

        # 存儲參數輸入框的引用
        self.param_inputs = {}

        for arg in arguments:
            param_row = self._create_param_row(arg)
            params_layout.addWidget(param_row)

        return params_widget

    def _create_param_row(self, arg):
        """創建單個參數行，支持選項和示例顯示"""
        param_row = QWidget()
        param_row.setStyleSheet("background: transparent;")

        row_layout = QVBoxLayout(param_row)  # 改為垂直布局以容納更多信息
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        # 第一行：參數名稱、類型和輸入框
        main_row = QWidget()
        main_row_layout = QHBoxLayout(main_row)
        main_row_layout.setContentsMargins(0, 0, 0, 0)
        main_row_layout.setSpacing(8)

        # 參數名稱和類型 - 內文樣式
        name_text = f"{arg.get('name', '')} ({arg.get('type', 'str')})"
        name_label = QLabel(name_text)
        name_label.setFixedWidth(130)
        name_label.setStyleSheet("""
            color: #5D6D7E;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)

        # 參數輸入框
        input_field = self._create_input_field(arg)
        input_field.setFixedHeight(28)  # 配合更大字體調整高度
        self.param_inputs[arg['name']] = input_field

        main_row_layout.addWidget(name_label)
        main_row_layout.addWidget(input_field, 1)

        row_layout.addWidget(main_row)

        # 第二行：選項提示和示例（如果有的話）
        info_row = self._create_param_info_row(arg)
        if info_row:
            row_layout.addWidget(info_row)

        return param_row

    def _create_param_info_row(self, arg):
        """創建參數信息行（選項和示例）"""
        options = arg.get('options', [])
        example = arg.get('example', '')
        description = arg.get('description', '')

        if not options and not example and not description:
            return None

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(130, 0, 0, 0)  # 與參數名稱對齊
        info_layout.setSpacing(2)

        # 顯示描述
        if description:
            desc_label = QLabel(f"💬 {description}")
            desc_label.setStyleSheet("""
                color: #7F8C8D;
                font-size: 10px;
                font-style: italic;
                background: transparent;
            """)
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

        # 顯示選項
        if options:
            options_text = " | ".join(options)
            options_label = QLabel(f"📋 選項: {options_text}")
            options_label.setStyleSheet("""
                color: #3498DB;
                font-size: 10px;
                font-weight: 500;
                background: transparent;
            """)
            options_label.setWordWrap(True)
            info_layout.addWidget(options_label)

        # 顯示示例
        if example:
            example_label = QLabel(f"💡 範例: {example}")
            example_label.setStyleSheet("""
                color: #E67E22;
                font-size: 10px;
                font-style: italic;
                background: transparent;
            """)
            example_label.setWordWrap(True)
            info_layout.addWidget(example_label)

        return info_widget

    def _create_input_field(self, arg):
        """創建適合參數類型的輸入框 - 重構版本，支持選項下拉框"""
        # print( arg )
        arg_type = arg.get('type', 'str').lower()
        name = arg.get('name')
        default = arg.get('default')
        options = arg.get('options', [])  # 獲取選項列表
        current_value = self.param_values.get(name, default)

        base_style = """
            border: 1px solid #E0E0E0;
            border-radius: 3px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: 400;
            background-color: #FFFFFF;
        """

        # 如果有選項，創建下拉框
        if options:
            input_field = QComboBox()

            # 添加選項到下拉框
            input_field.addItems(options)

            # 設置當前值
            if current_value and str(current_value) in options:
                input_field.setCurrentText(str(current_value))
            elif default and str(default) in options:
                input_field.setCurrentText(str(default))
            elif options:  # 如果沒有匹配的值，選擇第一個選項
                input_field.setCurrentText(options[0])

            # 設置樣式
            input_field.setStyleSheet(f"QComboBox {{{base_style}}}")

            # 連接信號
            input_field.currentTextChanged.connect(
                lambda text, n=name: self._handle_value_changed(n, text)
            )

            # 設置工具提示
            if options:
                tooltip = f"可選值: {', '.join(options)}"
                input_field.setToolTip(tooltip)

        elif arg_type == 'bool':
            # 布爾類型仍用下拉框
            input_field = QComboBox()
            input_field.addItems(['True', 'False'])
            input_field.setCurrentText(str(current_value) if current_value is not None else 'False')
            input_field.setStyleSheet(f"QComboBox {{{base_style}}}")
            # 連接信號
            input_field.currentTextChanged.connect(
                lambda text, n=name: self._handle_value_changed(n, text == 'True')
            )
        else:
            # 其他類型用文本輸入框
            input_field = QLineEdit()
            if current_value is not None:
                input_field.setText(str(current_value))
            if default is not None:
                input_field.setPlaceholderText(f"Default: {default}")
            input_field.setStyleSheet(f"QLineEdit {{{base_style}}}")
            # 連接信號
            input_field.textChanged.connect(
                lambda text, n=name: self._handle_value_changed(n, text)
            )

            # 為沒有選項的參數添加提示
            example = arg.get('example', '')
            if example:
                current_tooltip = input_field.toolTip()
                tooltip = f"範例: {example}"
                if current_tooltip:
                    tooltip = f"{current_tooltip}\n{tooltip}"
                input_field.setToolTip(tooltip)

        return input_field

    def _create_progress_section(self):
        """創建進度顯示區域 - 重構版本"""
        progress_widget = QWidget()
        progress_widget.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border: none;
                border-radius: 4px;
            }
        """)

        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(10, 8, 10, 8)
        progress_layout.setSpacing(6)

        # 狀態行
        status_row = QWidget()
        status_row.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        # 狀態標籤
        self.status_label = QLabel("WAITING")
        self.status_label.setFixedWidth(80)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            background-color: {self.STATUS_COLORS['waiting']};
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        """)

        # 執行時間 - 內文樣式
        self.time_label = QLabel("0.0s")
        self.time_label.setStyleSheet("""
            color: #5D6D7E;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.time_label)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)  # 稍微增加高度配合字體
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)

        progress_layout.addWidget(status_row)
        progress_layout.addWidget(self.progress_bar)

        return progress_widget

    def _create_error_section(self):
        """創建錯誤訊息區域 - 重構版本"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(0, 0, 0, 0)
        error_layout.setSpacing(0)

        self.error_label = QLabel()
        self.error_label.setText("")
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                padding: 8px;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 400;
                background-color: #FFEBEE;
            }
        """)
        self.error_label.hide()  # 預設隱藏

        error_layout.addWidget(self.error_label)
        return error_widget

    # ============ 保持原有的功能方法 ============

    def _init_param_values(self):
        """初始化參數值，使用默認值"""
        for arg in self.keyword_config.get('arguments', []):
            name = arg.get('name')
            default = arg.get('default')
            options = arg.get('options', [])

            # 如果有選項且默認值不在選項中，使用第一個選項
            if options and default not in options:
                default = options[0]

            self.param_values[name] = default

    def _handle_value_changed(self, name: str, value):
        """處理值變更"""
        self.param_values[name] = value
        for arg in self.keyword_config['arguments']:
            if arg['name'] == name:
                arg['value'] = value
                break
        self.parameter_changed.emit(name, str(value))

    def get_parameter_values(self):
        """獲取所有參數的當前值"""
        return self.param_values.copy()

    def set_parameter_value(self, name: str, value):
        """設置特定參數的值"""
        if name in self.param_values:
            self.param_values[name] = value
            if hasattr(self, 'param_inputs') and name in self.param_inputs:
                input_field = self.param_inputs[name]
                if isinstance(input_field, QComboBox):
                    input_field.setCurrentText(str(value))
                else:
                    input_field.setText(str(value))

    def reset_parameter_values(self):
        """重置所有參數值為默認值"""
        self._init_param_values()
        if hasattr(self, 'param_inputs'):
            for name, value in self.param_values.items():
                if name in self.param_inputs:
                    input_field = self.param_inputs[name]
                    if isinstance(input_field, QComboBox):
                        input_field.setCurrentText(str(value if value is not None else 'False'))
                    else:
                        input_field.setText(str(value) if value is not None else '')

    def update_execution_time(self, time_in_seconds: float):
        """更新執行時間"""
        self.execution_time = time_in_seconds
        self.time_label.setText(f"{time_in_seconds:.1f}s")

    def reset_status(self):
        """重置狀態為初始值"""
        try:
            self.status = 'waiting'
            self.progress = 0
            self.execution_time = 0.0

            self.stop_timer()
            self.start_time = None

            self._update_status_display('waiting', 0)
            self.clear_error()
            self.update_execution_time(0.0)

        except Exception as e:
            print(f"[BaseKeywordProgressCard] Error resetting status: {e}")

    def update_status(self, message: dict):
        """更新執行狀態 - 基於完整 message"""
        try:
            msg_type = message.get('type', '')
            data = message.get('data', {})

            if msg_type == 'keyword_start':
                self._handle_keyword_start(data)
            elif msg_type == 'keyword_end':
                self._handle_keyword_end(data)
            elif msg_type == 'test_start':
                self._handle_test_start(data)
            elif msg_type == 'test_end':
                self._handle_test_end(data)
            elif msg_type == 'log':
                self._handle_log(data)

        except Exception as e:
            print(f"[BaseKeywordProgressCard] Error updating status: {e}")
            self.update_error(f"Status update error: {str(e)}")

    def _handle_keyword_start(self, data):
        """處理關鍵字開始"""
        keyword_name = data.get('keyword_name', '')

        if self._is_current_keyword(keyword_name):
            self.status = 'running'
            self._update_status_display('running')
            self.start_timer()
            # self.update_error("")

    def _handle_keyword_end(self, data):
        """處理關鍵字結束"""
        keyword_name = data.get('keyword_name', '')
        robot_status = data.get('status', 'UNKNOWN')
        error_message = data.get('message', '')

        if self._is_current_keyword(keyword_name):
            if robot_status == 'PASS':
                self.status = 'passed'
                progress = 100
                # self.update_error("")
            elif robot_status == 'FAIL':
                self.status = 'failed'
                progress = 100
                # self.update_error(error_message)
            elif robot_status == 'NOT RUN':
                self.status = 'not_run'
                progress = 100
                # self.update_error("")
            else:
                self.status = 'waiting'
                progress = 0

            self._update_status_display(self.status, progress)
            self.stop_timer()

    def _handle_test_start(self, data):
        """處理測試開始"""
        self.reset_status()

    def _handle_test_end(self, data):
        """處理測試結束"""
        if self.status == 'running':
            test_status = data.get('status', '')
            if test_status == 'FAIL':
                self.status = 'failed'
                self._update_status_display(self.status, 100)
            elif test_status == 'PASS':
                self.status = 'passed'
                self._update_status_display(self.status, 100)

    def _handle_log(self, data):
        """處理日誌訊息"""
        level = data.get('level', '')
        message = data.get('message', '')

        if level in ['ERROR', 'FAIL']:
            self.update_error(message)

    def _is_current_keyword(self, robot_keyword_name):
        """檢查是否是當前卡片的關鍵字"""
        current_keyword = self.keyword_config.get('name', '')
        current_keyword = current_keyword.replace("_", " ")

        # 直接匹配
        if robot_keyword_name == current_keyword:
            return True

        # 模糊匹配 (處理 Robot Framework 的命名格式)
        if (robot_keyword_name.lower().endswith(current_keyword.lower()) or
                current_keyword.lower() in robot_keyword_name.lower()):
            return True

        return False

    def _update_status_display(self, status, progress=None):
        """更新狀態顯示的內部方法 - 支援進度條跑動"""
        self.status_label.setText(status.upper().replace('_', ' '))
        self.status_label.setStyleSheet(f"""
            background-color: {self.STATUS_COLORS[status]};
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        """)

        if status == 'running':
            # 設置為無限進度條（持續跑動）
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)

            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.STATUS_COLORS[status]};
                    border-radius: 4px;
                }}
            """)
        else:
            # 恢復正常進度條模式
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)

            if progress is not None:
                self.progress = progress
                self.progress_bar.setValue(progress)

            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.STATUS_COLORS[status]};
                    border-radius: 4px;
                }}
            """)

    def clear_error(self):
        if hasattr(self, 'error_label') and self.error_label:
            self.error_label.clear()
            self.error_label.hide()

    def update_error(self, error_msg: str):
        """更新錯誤訊息"""
        if hasattr(self, 'error_label') and self.error_label:
            self.error_label.setText(error_msg)
            self.error_label.show()

    def _update_running_time(self):
        """更新運行時間"""
        if self.start_time is not None:
            elapsed = (QDateTime.currentDateTime().toMSecsSinceEpoch() - self.start_time) / 1000.0
            self.update_execution_time(elapsed)

    def start_timer(self):
        """開始計時"""
        self.start_time = QDateTime.currentDateTime().toMSecsSinceEpoch()
        self.timer.start()

    def stop_timer(self):
        """停止計時"""
        self.timer.stop()

    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)

        delete_action = context_menu.addAction("刪除")
        move_up_action = context_menu.addAction("向上移動")
        move_down_action = context_menu.addAction("向下移動")

        try:
            from src.utils import get_icon_path
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


