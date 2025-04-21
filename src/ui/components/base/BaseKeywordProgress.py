from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json

from src.utils import Utils


class BaseKeywordProgressCard(QFrame):
    """關鍵字進度卡片元件"""
    STATUS_COLORS = {
        'waiting': '#FFA000',  # 黃色
        'running': '#2196F3',  # 藍色
        'passed': '#4CAF50',  # 綠色
        'failed': '#F44336'  # 紅色
    }

    parameter_changed = Signal(str, str)  # (參數名, 新值)

    # 新增信號用於菜單操作
    delete_requested = Signal(QObject)  # 刪除請求信號
    move_up_requested = Signal(QObject)  # 向上移動請求信號
    move_down_requested = Signal(QObject)  # 向下移動請求信號

    def __init__(self, keyword_config: dict, parent=None):
        super().__init__(parent)

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
                            border: 2px solid #A0A0A0;
                            margin: 8px 8px 0px 8px  ;  
                        }
                    """)

        # 設置固定高度 (根據參數數量動態調整)
        base_height = 140  # 基礎高度
        param_height = len(self.keyword_config.get('arguments', [])) * 40
        self.setMinimumHeight(base_height + param_height)

        # running Timer
        self.timer = QTimer()
        self.timer.setInterval(100)  # 每0.1秒更新一次
        self.timer.timeout.connect(self._update_running_time)
        self.start_time = None

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def _setup_ui(self):
        """初始化 UI"""
        self._setup_shadow()
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)

        # 建立一個容器來包含所有內容
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 添加各個區域到容器中
        header = self._create_header()
        params = self._create_params_section()
        progress = self._create_progress_section()
        error = self._create_error_section()

        # 設置各區域的大小策略
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        params.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        error.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # 添加到容器布局
        content_layout.addWidget(header)
        content_layout.addWidget(params)
        content_layout.addWidget(progress)
        content_layout.addWidget(error)

        # 設置容器的大小策略
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # 將容器添加到主布局
        layout.addWidget(content_widget)

    def _get_base_stylesheet(self):
        """獲取基本樣式表"""
        return """
            KeywordProgressCard {
                background-color: #FF0000;
                border: 2px solid #A0A0A0;
                margin: 8px 8px 0px 8px  ;  
            }
        """

    # region UI
    def _setup_shadow(self):
        """設置陰影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def _create_header(self):
        """創建標題區域"""
        header = QWidget()
        header.setFixedHeight(36)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)

        # Keyword 名稱
        name_label = QLabel(self.keyword_config.get('name', ''))
        name_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #333333;
        """)

        # 類別標籤
        category = self.keyword_config.get('category', '')
        category_label = QLabel(category)
        category_label.setStyleSheet("""
            background-color: #0077CC;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: bold;
        """)

        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(category_label)

        return header

    def _create_progress_section(self):
        """創建進度顯示區域"""
        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setSpacing(12)
        progress_layout.setContentsMargins(8, 8, 8, 8)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F5F5F5;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)

        # 狀態行
        # status_row = QWidget()
        # status_layout = QHBoxLayout(status_row)
        # status_layout.setContentsMargins(0, 0, 0, 0)

        # 狀態標籤
        self.status_label = QLabel("WAITING")
        self.status_label.setStyleSheet(f"""
            background-color: #FFA000;
            color: white;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
        """)

        # 執行時間
        self.time_label = QLabel("0.0s")
        self.time_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
        """)

        # 正確的添加順序
        progress_layout.addWidget(self.status_label)  # 先加入狀態標籤
        progress_layout.addWidget(self.progress_bar)  # 加入進度條
        progress_layout.addWidget(self.time_label)  # 加入時間標籤

        return progress_widget

    def _create_params_section(self):
        """創建參數輸入區域"""
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setSpacing(8)
        params_layout.setContentsMargins(8, 8, 8, 8)

        self.param_inputs = {}  # 存儲參數輸入框的引用

        for arg in self.keyword_config.get('arguments', []):
            param_row = QWidget()
            row_layout = QGridLayout(param_row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # 參數名稱
            name_label = QLabel(f"{arg['name']} ({arg['type'] if 'type' in arg else 'str'}):")
            name_label.setStyleSheet("""
                color: #666666;
                font-size: 12px;
            """)

            # 參數輸入框
            input_field = self._create_input_field(arg)
            self.param_inputs[arg['name']] = input_field

            # row: int, column: int, rowSpan: int, columnSpan: int,
            row_layout.addWidget(name_label, 0, 0)
            row_layout.addWidget(input_field, 0, 1)
            row_layout.setColumnStretch(0, 1)
            row_layout.setColumnStretch(1, 1)

            params_layout.addWidget(param_row)

        return params_widget

    def _create_input_field(self, arg):
        """創建適合參數類型的輸入框"""
        arg_type = arg.get('type', 'str').lower()
        name = arg.get('name')
        default = arg.get('default')
        current_value = self.param_values.get(name, default)

        if arg_type == 'bool':
            input_field = QComboBox()
            input_field.addItems(['True', 'False'])
            input_field.setCurrentText(str(current_value) if current_value is not None else 'False')
            # 連接信號
            input_field.currentTextChanged.connect(
                lambda text, n=name: self._handle_value_changed(n, text == 'True')
            )
        else:
            input_field = QLineEdit()
            if current_value is not None:
                input_field.setText(str(current_value))
            if default is not None:
                input_field.setPlaceholderText(f"Default: {default}")
            # 連接信號
            input_field.textChanged.connect(
                lambda text, n=name: self._handle_value_changed(n, text)
            )

        return input_field

    def _create_error_section(self):
        """創建錯誤訊息區域"""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setContentsMargins(8, 0, 8, 8)  # 減少上下邊距

        self.error_label = QLabel()
        self.error_label.setText("")
        self.error_label.setWordWrap(True)  # 允許文字換行
        self.error_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)  # 允許水平擴展
        self.error_label.setStyleSheet("""
            QLabel {
                color: #8B0000;
                padding: 8px;
                border: 1px solid #8B0000;
                border-radius: 4px;
                font-size: 12px;
                background-color: #FFF0F0;
            }
        """)
        self.error_label.hide()  # 預設隱藏

        error_layout.addWidget(self.error_label)
        return error_widget

    # endregion

    # region Parameter Management Methods

    def _init_param_values(self):
        """初始化參數值，使用默認值"""
        for arg in self.keyword_config.get('arguments', []):
            name = arg.get('name')
            default = arg.get('default')
            self.param_values[name] = default

    def _handle_value_changed(self, name: str, value):
        """處理值變更"""
        # 更新內部存儲
        # print(f"Setting Parametere >>>> name: {name}, value: {value}")
        self.param_values[name] = value
        # 更新 config
        for arg in self.keyword_config['arguments']:
            if arg['name'] == name:
                arg['value'] = value
                break
        # 發出信號
        self.parameter_changed.emit(name, str(value))

    def _update_param_value(self, name: str, value):
        """更新參數值"""
        self.param_values[name] = value

    def get_parameter_values(self):
        """獲取所有參數的當前值"""
        return self.param_values.copy()

    def set_parameter_value(self, name: str, value):
        """設置特定參數的值"""
        if name in self.param_values:
            self.param_values[name] = value
            if name in self.param_inputs:
                input_field = self.param_inputs[name]
                if isinstance(input_field, QComboBox):
                    input_field.setCurrentText(str(value))
                else:
                    input_field.setText(str(value))

    def reset_parameter_values(self):
        """重置所有參數值為默認值"""
        self._init_param_values()
        for name, value in self.param_values.items():
            if name in self.param_inputs:
                input_field = self.param_inputs[name]
                if isinstance(input_field, QComboBox):
                    input_field.setCurrentText(str(value if value is not None else 'False'))
                else:
                    input_field.setText(str(value) if value is not None else '')

    # endregion

    # region STATUS UPDATE

    def update_execution_time(self, time_in_seconds: float):
        """更新執行時間"""
        self.execution_time = time_in_seconds
        self.time_label.setText(f"{time_in_seconds:.1f}s")

    def reset_status(self):
        """重置狀態為初始值"""
        self.update_status('waiting', 0)
        self.update_execution_time(0.0)
        self.stop_timer()
        self.start_time = None

    def update_status(self, status: str, progress: int = None, error_msg: str = None):
        """更新執行狀態"""
        self.status = status

        # 更新狀態標籤
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"""
            background-color: {self.STATUS_COLORS[status]};
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        """)

        # 更新進度條
        if progress is not None:
            self.progress = progress
            self.progress_bar.setValue(progress)
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F5F5F5;
                    border: none;
                    border-radius: 4px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.STATUS_COLORS[status]};
                    border-radius: 4px;
                }}
            """)
            if status == 'running':
                self.set_progress_start()
                self.start_timer()
            else:
                self.set_progress_normal()
                self.stop_timer()

            # 更新錯誤訊息
            self.update_error(error_msg)

    def update_error(self, error_msg: str):
        """更新錯誤訊息
        Args:
            error_msg (str): 錯誤訊息文字，如果是空字串則隱藏錯誤訊息區塊
        """
        if self.error_label:  # 添加檢查
            if error_msg:
                self.error_label.setText(error_msg)
                self.error_label.show()
            else:
                self.error_label.clear()
                self.error_label.hide()

    # endregion

    # region PROGRESS BAR
    def set_progress_start(self):
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)

    def set_progress_normal(self):
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)

    # endregion

    # region RUNNING TIMER
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

    # endregion

    # region CONTEXT MENU
    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)

        # 新增選單項目
        delete_action = context_menu.addAction("刪除")
        move_up_action = context_menu.addAction("向上移動")
        move_down_action = context_menu.addAction("向下移動")

        # 設置圖標（可從 src/assets/Icons 獲取）
        try:
            from src.utils import get_icon_path
            delete_icon = QIcon(get_icon_path("delete.svg"))
            delete_action.setIcon(Utils.change_icon_color(delete_icon, "#000000"))

            upward_icon = QIcon(get_icon_path("arrow_drop_up.svg"))
            move_up_action.setIcon(Utils.change_icon_color(upward_icon, "#000000"))

            downward_icon = QIcon(get_icon_path("arrow_drop_down.svg"))
            move_down_action.setIcon(Utils.change_icon_color(downward_icon, "#000000"))

        except ImportError:
            # 如果無法導入圖標，繼續而不設置圖標
            pass

        # 獲取所選操作
        action = context_menu.exec_(self.mapToGlobal(position))

        # 處理所選操作
        if action == delete_action:
            self.delete_requested.emit(self)
        elif action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)
    # endregion