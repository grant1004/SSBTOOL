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

        self.theme_manager = self.parent().theme_manager



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
                'common': {'text': 'Common'},
                'battery': {'text': 'Battery'},
                'hmi': {'text': 'HMI'},
                'motor': {'text': 'Motor'},
                'controller': {'text': 'Controller'}

            },
            'default_tab': 'common',
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
        }, parent=self)
        self.switch_button.switched.connect(self.controller.handle_mode_switch)
        self.content_layout.addWidget(self.switch_button)

        # 創建搜索欄
        self.search_bar = SearchBar(parent=self)
        self.search_bar.search_changed.connect(self.controller.handle_search)
        self.content_layout.addWidget(self.search_bar)

        # 創建堆疊部件來管理不同模式的內容
        self.stacked_widget = QStackedWidget()

        # 創建測試案例組
        self.test_case_group = TestCaseGroup(self)
        self.stacked_widget.addWidget(self.test_case_group)

        # 創建關鍵字組
        self.keyword_group = KeywordGroup(self)  # 需要創建新的 KeywordGroup 組件
        self.stacked_widget.addWidget(self.keyword_group)

        self.content_layout.addWidget(self.stacked_widget)

        # 添加到主布局
        self.main_layout.addWidget(self.tabs_group)
        self.main_layout.addWidget(self.content, 1)

        # 載入初始數據
        self.controller.initialize()

    def switch_mode(self, mode: str):
        """切換顯示模式"""
        if mode == 'test_cases':
            self.stacked_widget.setCurrentWidget(self.test_case_group)
        elif mode == 'keywords':
            self.stacked_widget.setCurrentWidget(self.keyword_group)


