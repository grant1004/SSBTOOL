from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.ui.components.base import BaseCard


class KeywordGroup(QScrollArea):
    """關鍵字組件，用於顯示和管理關鍵字"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keywords = []
        self.cards = []
        self._setup_ui()

        # 獲取 theme manager
        self.theme_manager = self.get_theme_manager()
        # 連接主題變更信號
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

        # 設置滾動區域樣式
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

    def load_from_data(self, card_configs):
        """
        從卡片配置載入關鍵字

        Args:
            card_configs: List[dict] 卡片配置列表
            每個配置字典應包含:
            {
                'id': str,              # 關鍵字唯一標識
                'title': str,           # 關鍵字名稱
                'info': str,            # 關鍵字描述
                'keywords': List[str],  # 參數列表
                'priority': str         # 優先級 (required/standard/optional)
            }
        """
        # 清除現有卡片
        self.clear_cards()

        # 為每個配置創建新卡片
        for config in card_configs:
            if not isinstance(config, dict):
                print(f"Invalid card config format: {config}")
                continue

            try:
                # 創建卡片
                card = BaseCard(
                    card_id=config.get('id', f"kw_{len(self.cards)}"),
                    config={
                        'title': config.get('title', 'Unnamed Keyword'),
                        'info': config.get('info', ''),
                        'keywords': config.get('keywords', []),
                        'priority': config.get('priority', 'standard')
                    },
                    parent=self
                )

                # 設置主題
                if hasattr(self, 'theme_manager'):
                    card.theme_manager = self.theme_manager
                    card._update_theme()

                # 連接點擊事件
                card.clicked.connect(self._click_card)

                # 添加到卡片列表和布局
                self.cards.append(card)
                self.layout.addWidget(card)

            except Exception as e:
                print(f"Error creating card for config {config}: {e}")

        # 更新關鍵字列表（用於搜索功能）
        self.keywords = card_configs

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

    def _click_card(self, card_id: str):
        """處理卡片點擊事件"""
        print(f"Clicked keyword {card_id}")

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

        # 更新滾動區域樣式
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