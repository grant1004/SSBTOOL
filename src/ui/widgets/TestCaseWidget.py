from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.controllers import TestCaseWidgetController
from src.models import TestCaseWidget_Model
from src.ui.components import *
from src.ui.components.base import *

# TestCaseWidget.py
class TestCaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_shadow()
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(500)

        # 初始化 MVC
        self.model = TestCaseWidget_Model()
        self.controller = TestCaseWidgetController(self.model, self)

        # 初始化 UI
        self._setup_config()
        self.init_ui()



    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)



    def _setup_config(self):
        # 可以從配置文件或其他來源加載
        self.config = {
            'tabs': {
                'battery': {'text': 'Battery'},
                'hmi': {'text': 'HMI'},
                'motor': {'text': 'Motor'},
                'controller': {'text': 'Controller'},
                'torque': {'text': 'Torque'},
                'torque1': {'text': 'Torque1'},
                'torque2': {'text': 'Torque2'}

            },
            'default_tab': 'battery',
            'switch_modes': {
                'test_cases': {
                    'text': 'Test Cases'
                },
                'keywords': {
                    'text': 'Keywords'
                }
            },
            'default_mode': 'test_cases'
        }


    def init_ui(self):
        """初始化 UI"""
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 4, 8)
        self.main_layout.setSpacing(0)

        # 創建 Tabs
        self.tabs_group = TabsGroup(self.config, self)
        self.tabs_group.tab_changed.connect(self.controller.handle_category_change)

        # 創建內容區域
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setContentsMargins(8, 0, 8, 0)
        self.content_layout.setSpacing(8)

        # 創建模式切換按鈕
        self.switch_button = BaseSwitchButton({
            'modes': self.config['switch_modes'],
            'default_mode': self.config['default_mode']
        })
        self.switch_button.switched.connect(self.controller.handle_mode_switch)
        self.content_layout.addWidget(self.switch_button)

        # 創建搜索欄
        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self.controller.handle_search)
        self.content_layout.addWidget(self.search_bar)

        # 創建測試案例組
        self.test_case_group = TestCaseGroup(self)
        self.content_layout.addWidget(self.test_case_group)

        # 添加到主布局
        self.main_layout.addWidget(self.tabs_group)
        self.main_layout.addWidget(self.content, 1)

        # 載入初始數據
        self.controller.initialize()


