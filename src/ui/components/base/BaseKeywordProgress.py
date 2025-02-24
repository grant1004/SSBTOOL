from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json


class BaseKeywordProgressCard(QFrame):
    """關鍵字進度卡片元件"""
    STATUS_COLORS = {
        'waiting': '#FFA000',  # 黃色
        'running': '#2196F3',  # 藍色
        'passed': '#4CAF50',  # 綠色
        'failed': '#F44336'  # 紅色
    }


    parameter_changed = Signal(str, str)  # (參數名, 新值)

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
        self.setFixedHeight(base_height + param_height)

    def _init_param_values(self):
        """初始化參數值，使用默認值"""
        for arg in self.keyword_config.get('arguments', []):
            name = arg.get('name')
            default = arg.get('default')
            self.param_values[name] = default


    def _setup_ui(self):
        """初始化 UI"""
        self._setup_shadow()
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 添加標題區域
        layout.addWidget(self._create_header())

        # 添加參數輸入區域
        layout.addWidget(self._create_params_section())

        # 添加進度區域
        layout.addWidget(self._create_progress_section())

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

    def _get_base_stylesheet(self):
        """獲取基本樣式表"""
        return """
            KeywordProgressCard {
                background-color: #FF0000;
                border: 2px solid #A0A0A0;
                margin: 8px 8px 0px 8px  ;  
            }
        """

    def update_status(self, status: str, progress: int = None):
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

    def update_execution_time(self, time_in_seconds: float):
        """更新執行時間"""
        self.execution_time = time_in_seconds
        self.time_label.setText(f"{time_in_seconds:.1f}s")

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
            row_layout.setColumnStretch(0,1)
            row_layout.setColumnStretch(1,1)

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

    def reset_status(self):
        """重置狀態為初始值"""
        self.update_status('waiting', 0)
        self.update_execution_time(0.0)

