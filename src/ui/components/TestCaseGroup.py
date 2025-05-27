from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
from src.ui.components.base import BaseCard, BaseKeywordCard


class TestCaseGroup(QScrollArea):
    """測試案例組，用於顯示一組測試案例卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_cases = []
        self.cards = []
        self._setup_ui()
        self.theme_manager = self.get_theme_manager()
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

    def _setup_ui(self):
        # 設置滾動區域屬性
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 創建容器widget和布局
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self.container)
        self._setup_style()

    def load_from_data(self, data):
        """從新的 JSON 格式加載測試案例"""
        self.test_cases = []

        if isinstance(data, dict):
            # 處理新的 cards 格式：{"testcase_id": {"data": {"config": {...}}}}
            for testcase_id, testcase_data in data.items():
                if isinstance(testcase_data, dict) and 'data' in testcase_data:
                    config = testcase_data['data'].get('config', {})
                    # 建立卡片所需的格式
                    test_case = {
                        'id': testcase_id,
                        'name': config.get('name', testcase_id),
                        'description': config.get('description', ''),
                        'type': config.get('type', 'testcase'),
                        'category': config.get('category', 'user_defined'),
                        'priority': config.get('priority', 'normal'),
                        'steps': config.get('steps', []),
                        'estimated_time' : config.get('estimated_time', 0),
                        'dependencies': config.get('dependencies', {}),
                        'created_by': config.get('created_by', 'user'),
                        'created_at': config.get('created_at', ''),
                        'metadata': config.get('metadata', {})
                    }
                    self.test_cases.append(test_case)

            # 如果沒有找到 cards 格式，檢查是否為舊格式
            if not self.test_cases and 'test_cases' in data:
                self.test_cases = data['test_cases']
        elif isinstance(data, list):
            # 處理陣列格式（向下兼容）
            self.test_cases = data

        self._create_cards()

    def _create_cards(self):
        """根據測試案例數據創建卡片"""
        self.clear_cards()

        for test_case in self.test_cases:
            # 使用測試案例數據創建卡片

            card = BaseCard(
                card_id=test_case.get('id', f"test_{len(self.cards)}"),
                config=test_case,
                parent=self
            )

            if hasattr(self, 'theme_manager'):
                card.theme_manager = self.theme_manager
                card._update_theme()

            card.clicked.connect(self._click_card)
            self.cards.append(card)
            self.layout.addWidget(card)

    def _setup_style(self):
        """設置基本樣式"""
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, 
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def clear_cards(self):
        """清除所有卡片"""
        for card in self.cards:
            self.layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

    def filter_cards(self, filter_text: str):
        """根據過濾文本顯示/隱藏卡片"""
        filter_text = filter_text.lower()
        for card in self.cards:
            should_show = (
                    filter_text in card.config.get('name', '').lower() or
                    filter_text in card.config.get('description', '').lower() or
                    filter_text in card.config.get('category', '').lower() or
                    any(
                        filter_text in str(step.get('keyword_name', '')).lower()
                        for step in card.config.get('steps', [])
                        if isinstance(step, dict)
                    )
            )
            card.setVisible(should_show)

    def update_card(self, card_id: str, new_data: dict):
        """更新特定卡片的數據"""
        for card in self.cards:
            if card.card_id == card_id:
                card.config.update(new_data)
                break

    def get_visible_cards(self):
        """獲取當前可見的卡片列表"""
        return [card for card in self.cards if card.isVisible()]

    def get_all_cards(self):
        """獲取所有卡片"""
        return self.cards.copy()

    def _click_card(self, card_id: str):
        """卡片點擊處理"""
        print(f"Clicked {card_id}")

    def get_theme_manager(self):
        """遞迴向上查找 theme_manager"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent()
        return None

    def _update_theme(self):
        """更新主題相關的樣式"""
        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        self.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}

            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}

            QScrollBar:vertical {{
                border: none;
                background: {current_theme.SURFACE};
                width: 8px;
                margin: 0;
            }}

            QScrollBar::handle:vertical {{
                background: {current_theme.BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {current_theme.PRIMARY};
            }}

            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical {{
                background: transparent;
                height: 0px;
            }}

            QScrollBar::add-page:vertical, 
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        self.container.setStyleSheet(
            "background-color: transparent;"
        )
        self.viewport().setStyleSheet(
            "background-color: transparent;"
        )