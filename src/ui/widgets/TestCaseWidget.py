# src/ui/widgets/TestCaseWidget.py
"""
重構的測試案例部件 - 完全集成 MVC 架構
實現 ITestCaseView 和 ITestCaseViewEvents 接口，與新的 Controller 和 Model 正確運作
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from typing import Dict, List, Optional, Any

# 導入 MVC 架構
from src.interfaces.test_case_interface import (
    ITestCaseView, ITestCaseViewEvents,
    TestCaseCategory, TestCaseMode, TestCaseInfo, KeywordInfo
)
from src.mvc_framework.base_view import BaseView
from src.controllers.test_case_controller import TestCaseController

# 導入 UI 組件
from src.ui.components import TabsGroup, SearchBar, TestCaseGroup, KeywordGroup
from src.ui.components.base import BaseSwitchButton


class TestCaseWidget(BaseView, ITestCaseView, ITestCaseViewEvents):
    """
    重構的測試案例部件

    特點：
    - 完整實現 MVC 接口
    - 與 TestCaseController 正確集成
    - 支持新的數據格式 (TestCaseInfo, KeywordInfo)
    - 提供載入狀態管理
    - 支持主題系統
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._test_case_controller: Optional[TestCaseController] = None

        # 獲取主題管理器
        self.theme_manager = self._get_theme_manager()

        # 狀態管理
        self._current_category = TestCaseCategory.COMMON
        self._current_mode = TestCaseMode.TEST_CASES
        self._is_loading = False
        self._current_search_text = ""

        # UI 設置
        self._setup_shadow()
        self._setup_config()
        self.init_ui()

        # 連接主題變更
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

        self._logger.info("TestCaseWidget initialized with MVC architecture")

    def set_test_case_controller(self, controller: TestCaseController) -> None:
        """設置測試案例控制器"""
        self._test_case_controller = controller
        if controller:
            controller.register_view(self)
            # 控制器設置完成後，觸發初始數據載入
            self._load_initial_data()
        self._logger.info("Test case controller set and view registered")

    #region ==================== UI 設置 ====================

    def _setup_shadow(self):
        """設置陰影效果"""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _setup_config(self):
        """設置配置"""
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
                'test_cases': {'text': 'Test Cases'},
                'keywords': {'text': 'Keywords'}
            },
            'default_mode': 'test_cases'
        }

    def init_ui(self):
        """初始化 UI"""
        self.setFixedWidth(500)
        self.setContentsMargins(0, 0, 0, 0)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 8, 4, 8)
        self.main_layout.setSpacing(0)

        # 創建標籤組
        self.tabs_group = TabsGroup(self.config, self)
        self.tabs_group.tab_changed.connect(self._on_tab_changed)

        # 創建內容區域
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_layout.setContentsMargins(8, 0, 8, 8)
        self.content_layout.setSpacing(8)

        # 創建模式切換按鈕
        self.switch_button = BaseSwitchButton({
            'modes': self.config['switch_modes'],
            'default_mode': self.config['default_mode']
        }, parent=self)
        self.switch_button.switched.connect(self._on_mode_switched)
        self.content_layout.addWidget(self.switch_button)

        # 創建搜索欄
        self.search_bar = SearchBar(parent=self)
        self.search_bar.search_changed.connect(self._on_search_changed)
        self.content_layout.addWidget(self.search_bar)

        # 創建載入指示器
        self.loading_indicator = self._create_loading_indicator()
        self.loading_indicator.hide()
        self.content_layout.addWidget(self.loading_indicator)

        # 創建空狀態指示器
        self.empty_state_widget = self._create_empty_state_widget()
        self.empty_state_widget.hide()
        self.content_layout.addWidget(self.empty_state_widget)




        # 創建堆疊部件來管理不同模式的內容
        self.stacked_widget = QStackedWidget()

        # 創建測試案例組
        self.test_case_group = TestCaseGroup(self)
        self.stacked_widget.addWidget(self.test_case_group)

        # 創建關鍵字組
        self.keyword_group = KeywordGroup(self)
        self.stacked_widget.addWidget(self.keyword_group)
        self.content_layout.addWidget(self.stacked_widget)

        # 刷新按鈕

        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setFixedSize(60, 24)
        self.refresh_button.clicked.connect(self.on_refresh_requested)
        self.refresh_button.setStyleSheet("""
                                           QPushButton {
                                               background-color: #4CAF50;
                                               color: white;
                                               border: none;
                                               border-radius: 6px;
                                               font-size: 12px;
                                               font-weight: 600;
                                           }
                                           QPushButton:hover {
                                               background-color: #45A049;
                                           }
                                       """)
        self.content_layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # 添加到主布局
        self.main_layout.addWidget(self.tabs_group)
        self.main_layout.addWidget(self.content, 1)

        # 初始化狀態
        self._update_mode_display()

        # 注意：初始數據載入會在控制器設置時觸發

    def _create_loading_indicator(self) -> QWidget:
        """創建載入指示器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 載入動畫標籤
        self.loading_label = QLabel("載入中...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 16px;
                font-weight: 500;
                padding: 20px;
            }
        """)

        # 載入進度條
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)  # 無限進度條
        self.loading_progress.setFixedHeight(4)
        self.loading_progress.setStyleSheet("""
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

        layout.addWidget(self.loading_label)
        layout.addWidget(self.loading_progress)
        return widget

    def _create_empty_state_widget(self) -> QWidget:
        """創建空狀態指示器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_state_label = QLabel("暫無數據")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 16px;
                font-weight: 500;
                padding: 20px;
            }
        """)

        # 刷新按鈕
        # self.refresh_button = QPushButton("刷新")
        # self.refresh_button.setFixedSize(100, 36)
        # self.refresh_button.clicked.connect(self.on_refresh_requested)
        # self.refresh_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: #4CAF50;
        #         color: white;
        #         border: none;
        #         border-radius: 6px;
        #         font-size: 14px;
        #         font-weight: 600;
        #     }
        #     QPushButton:hover {
        #         background-color: #45A049;
        #     }
        # """)

        layout.addWidget(self.empty_state_label)
        # layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget
    #endregion

    #region ==================== ITestCaseView 接口實現 ====================

    def display_test_cases(self, test_cases: List[TestCaseInfo]) -> None:
        """顯示測試案例列表"""
        try:
            if not test_cases:
                self._show_empty_state("暫無測試案例")
                return

            # 轉換為測試案例組件所需的格式
            test_case_data = {}
            for tc in test_cases:
                test_case_data[tc.id] = {
                    'data': {
                        'config': {
                            'id': tc.id,
                            'name': tc.name,
                            'description': tc.description,
                            'type': 'testcase',
                            'category': tc.category.value,
                            'priority': tc.priority.value,
                            'steps': tc.steps,
                            'estimated_time': tc.estimated_time,
                            'dependencies': tc.dependencies,
                            'metadata': tc.metadata
                        }
                    }
                }

            self.test_case_group.load_from_data(test_case_data)
            self._show_content()
            self._logger.info(f"Displayed {len(test_cases)} test cases")

        except Exception as e:
            self._logger.error(f"Error displaying test cases: {e}")
            self.show_error_message(f"顯示測試案例失敗: {str(e)}")

    def display_keywords(self, keywords: List[KeywordInfo]) -> None:
        """顯示關鍵字列表"""
        try:
            if not keywords:
                self._show_empty_state("暫無關鍵字")
                return

            # 轉換為關鍵字組件所需的格式
            keyword_configs = []
            for kw in keywords:
                keyword_config = {
                    'id': kw.id,
                    'name': kw.name,
                    'category': kw.category.value,
                    'description': kw.description,
                    'arguments': kw.arguments,
                    'returns': kw.returns,
                    'priority': kw.priority.value
                }
                keyword_configs.append(keyword_config)

            self.keyword_group.load_from_data(keyword_configs)
            self._show_content()
            self._logger.info(f"Displayed {len(keywords)} keywords")

        except Exception as e:
            self._logger.error(f"Error displaying keywords: {e}")
            self.show_error_message(f"顯示關鍵字失敗: {str(e)}")

    def update_category_selection(self, category: TestCaseCategory) -> None:
        """更新分類選擇"""
        self._current_category = category
        # 更新標籤組的選擇
        if hasattr(self.tabs_group, 'tabs'):
            category_tab_id = category.value
            if category_tab_id in self.tabs_group.tabs:
                tab = self.tabs_group.tabs[category_tab_id]
                if not tab.isChecked():
                    tab.setChecked(True)

    def update_mode_selection(self, mode: TestCaseMode) -> None:
        """更新模式選擇"""
        self._current_mode = mode
        self._update_mode_display()

    def show_loading_state(self, is_loading: bool) -> None:
        """顯示載入狀態"""
        self._is_loading = is_loading

        if is_loading:
            self._show_loading()
            self.disable_controls()
        else:
            self.enable_controls()

    def show_error_message(self, error_message: str) -> None:
        """顯示錯誤信息"""
        super().show_error_message(error_message)
        self._show_empty_state(f"載入失敗: {error_message}")

    def show_empty_state(self, message: str) -> None:
        """顯示空狀態"""
        self._show_empty_state(message)

    def highlight_search_results(self, search_text: str) -> None:
        """高亮搜索結果"""
        self._current_search_text = search_text
        # 可以在這裡實現搜索高亮邏輯
        pass

    def clear_search_highlight(self) -> None:
        """清除搜索高亮"""
        self._current_search_text = ""
        # 可以在這裡實現清除高亮邏輯
        pass

    def enable_controls(self) -> None:
        """啟用控制項"""
        super().enable_controls()
        self.tabs_group.setEnabled(True)
        self.switch_button.setEnabled(True)
        self.search_bar.setEnabled(True)

    def disable_controls(self) -> None:
        """禁用控制項"""
        self.tabs_group.setEnabled(False)
        self.switch_button.setEnabled(False)
        self.search_bar.setEnabled(False)
    #endregion

    #region ==================== ITestCaseViewEvents 接口實現 ====================

    def on_category_changed(self, category: TestCaseCategory) -> None:
        """當分類變更時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_category_change(category)

    def on_mode_switched(self, mode: TestCaseMode) -> None:
        """當模式切換時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_mode_switch(mode)

    def on_search_text_changed(self, search_text: str) -> None:
        """當搜索文本變更時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_search_request(search_text)

    def on_test_case_selected(self, test_case_id: str) -> None:
        """當測試案例被選擇時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_test_case_selection(test_case_id)

    def on_keyword_selected(self, keyword_id: str) -> None:
        """當關鍵字被選擇時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_keyword_selection(keyword_id)

    def on_refresh_requested(self) -> None:
        """當請求刷新時觸發"""
        if self._test_case_controller:
            self._test_case_controller.handle_refresh_request()
    # endregion

    #region ==================== 內部事件處理 ====================

    def _on_tab_changed(self, tab_id: str) -> None:
        """處理標籤變更"""
        try:
            # 將 tab_id 轉換為 TestCaseCategory
            category = TestCaseCategory(tab_id)
            self.on_category_changed(category)
        except ValueError:
            self._logger.warning(f"Invalid category: {tab_id}")

    def _on_mode_switched(self, mode_id: str) -> None:
        """處理模式切換"""
        try:
            # 將 mode_id 轉換為 TestCaseMode
            mode = TestCaseMode(mode_id)
            self.on_mode_switched(mode)
        except ValueError:
            self._logger.warning(f"Invalid mode: {mode_id}")

    def _on_search_changed(self, search_text: str) -> None:
        """處理搜索變更"""
        self.on_search_text_changed(search_text)
    #endregion

    #region ==================== 輔助方法 ====================

    def _update_mode_display(self) -> None:
        """更新模式顯示"""
        if self._current_mode == TestCaseMode.TEST_CASES:
            self.stacked_widget.setCurrentWidget(self.test_case_group)
            self.search_bar.set_placeholder("Search test cases...")
        else:
            self.stacked_widget.setCurrentWidget(self.keyword_group)
            self.search_bar.set_placeholder("Search keywords...")

    def _show_loading(self) -> None:
        """顯示載入狀態"""
        self.loading_indicator.show()
        self.empty_state_widget.hide()
        self.stacked_widget.hide()

    def _show_content(self) -> None:
        """顯示內容"""
        self.loading_indicator.hide()
        self.empty_state_widget.hide()
        self.stacked_widget.show()

    def _show_empty_state(self, message: str) -> None:
        """顯示空狀態"""
        self.empty_state_label.setText(message)
        self.loading_indicator.hide()
        self.stacked_widget.hide()
        self.empty_state_widget.show()

    def _load_initial_data(self) -> None:
        """載入初始數據"""
        if self._test_case_controller:
            self._logger.info(f"Loading initial data for category: {self._current_category.value}")
            # 使用 QTimer.singleShot 延遲執行，確保事件循環已啟動
            QTimer.singleShot(100, lambda: self.on_category_changed(self._current_category))
        else:
            self._logger.warning("Cannot load initial data: no controller set")

    def _get_theme_manager(self):
        """獲取主題管理器"""
        parent = self.main_window
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent() if hasattr(parent, 'parent') else None
        return None

    def _update_theme(self):
        """更新主題"""
        if not self.theme_manager:
            return

        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        # 更新載入指示器樣式
        self.loading_label.setStyleSheet(f"""
            QLabel {{
                color: {current_theme.TEXT_SECONDARY};
                font-size: 16px;
                font-weight: 500;
                padding: 20px;
            }}
        """)

        # 更新空狀態樣式
        self.empty_state_label.setStyleSheet(f"""
            QLabel {{
                color: {current_theme.TEXT_SECONDARY};
                font-size: 16px;
                font-weight: 500;
                padding: 20px;
            }}
        """)
    #endregion

    #region ==================== 狀態查詢方法 ====================

    def get_current_category(self) -> TestCaseCategory:
        """獲取當前分類"""
        return self._current_category

    def get_current_mode(self) -> TestCaseMode:
        """獲取當前模式"""
        return self._current_mode

    def is_loading(self) -> bool:
        """是否正在載入"""
        return self._is_loading

    def get_widget_state(self) -> Dict[str, Any]:
        """獲取部件狀態"""
        return {
            'current_category': self._current_category.value,
            'current_mode': self._current_mode.value,
            'is_loading': self._is_loading,
            'search_text': self.search_bar.get_text() if self.search_bar else "",
            'has_controller': self._test_case_controller is not None
        }
    #endregion

    # ==================== 調試方法 ====================
    def debug_state(self) -> None:
        """調試狀態信息"""
        state = self.get_widget_state()
        self._logger.info(f"TestCaseWidget state: {state}")

        if self._test_case_controller:
            controller_state = self._test_case_controller.get_current_state()
            self._logger.info(f"Controller state: {controller_state}")