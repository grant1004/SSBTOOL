from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import json
from src.ui.components.base import BaseCard


class TestCaseGroup(QScrollArea):
    """測試案例組，用於顯示一組測試案例卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_cases = []
        self.cards = []
        self._setup_ui()

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

        # 設置樣式
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

        self.setWidget(self.container)

    def load_from_json(self, json_path):
        """從JSON文件加載測試案例數據"""
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                self.test_cases = json.load(file)
                self._create_cards()
        except Exception as e:
            print(f"Error loading JSON file: {e}")

    def load_from_data(self, data):
        """直接從數據加載測試案例"""
        self.test_cases = data
        self._create_cards()

    def _create_cards(self):
        """根據測試案例數據創建卡片"""
        # 清除現有卡片
        self.clear_cards()

        # 為每個測試案例創建新卡片
        for test_case in self.test_cases:
            card_config = {
                'title': test_case.get('name', 'Unnamed Test'),
                'info': test_case.get('description', ''),
                'estimated_time': test_case.get('estimated_time', 0),
                'keywords': test_case.get('keywords', []),
                'priority': test_case.get('priority', 'medium')
            }

            card = BaseCard(
                test_case.get('id', f"test_{len(self.cards)}"),
                card_config,
                parent=self
            )
            self.cards.append(card)
            self.layout.addWidget(card)

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
                    filter_text in card.title.lower() or
                    filter_text in card.info.lower() or
                    any(filter_text in keyword.lower() for keyword in card.keywords)
            )
            card.setVisible(should_show)

    def update_card(self, card_id: str, new_data: dict):
        """更新特定卡片的數據"""
        for card in self.cards:
            if card.id == card_id:
                card.update_config(new_data)
                break

    def get_visible_cards(self):
        """獲取當前可見的卡片列表"""
        return [card for card in self.cards if card.isVisible()]

    def get_all_cards(self):
        """獲取所有卡片"""
        return self.cards.copy()