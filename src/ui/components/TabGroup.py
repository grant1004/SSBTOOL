from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from typing import Dict
from src.ui.components.base import BaseTab

class TabsGroup(QWidget):
    """標籤組管理類"""
    tab_changed = Signal(str)  # 發送當前選中的標籤ID

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.tabs: Dict[str, BaseTab] = {}
        self.current_tab_id = None

        # 獲取 theme manager
        self.theme_manager = self.get_theme_manager()
        # 連接主題變更信號
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

        self._setup_ui()

    def _setup_ui(self):
        # 創建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 創建滾動區域
        self.scroll_area = QScrollArea()
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidgetResizable(True)
        # 設置滾動區域和其內部視圖的背景為透明
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: transparent;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical {
                background:transparent;
                height: 0px;
            }
            QScrollBar::add-page:vertical, 
            QScrollBar::sub-page:vertical {
            
                background: transparent;
            }
        """)

        # 確保滾動區域的viewport也是透明的
        self.scroll_area.viewport().setStyleSheet("background-color: transparent;")



        # 創建容器 widget 用於放置標籤按鈕
        self.container = QWidget()
        # 確保容器widget也是透明的
        self.container.setStyleSheet("background-color: transparent;")
        self.container.setObjectName("tabs-container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 8, 8, 0)  # 右側留出滾動條的空間
        container_layout.setSpacing(10)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 使用 QButtonGroup 來管理互斥選擇
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        # 創建標籤按鈕
        for tab_id, tab_config in self.config.get('tabs', {}).items():
            tab = BaseTab(tab_id, tab_config, self)
            self.tabs[tab_id] = tab
            self.button_group.addButton(tab)
            container_layout.addWidget(tab, alignment=Qt.AlignmentFlag.AlignRight)
            tab.tab_clicked.connect(self._handle_tab_change)

        # 添加彈性空間到底部
        container_layout.addStretch()

        # 設置滾動區域的widget
        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area)

        # 設置默認選中項
        default_tab = self.config.get('default_tab')
        if default_tab and default_tab in self.tabs:
            self.tabs[default_tab].setChecked(True)
            self.current_tab_id = default_tab
            # 使用 QTimer 確保在布局完成後滾動到默認標籤
            QTimer.singleShot(0, lambda: self._ensure_tab_visible(default_tab))

    def _ensure_tab_visible(self, tab_id: str):
        """確保指定的標籤在可視區域內"""
        if tab_id in self.tabs:
            tab = self.tabs[tab_id]
            # 計算標籤在滾動區域中的位置
            pos = tab.mapTo(self.scroll_area.widget(), QPoint(0, 0))
            # 滾動到標籤位置
            self.scroll_area.ensureVisible(pos.x(), pos.y(), 0, 50)

    def _handle_tab_change(self, tab_id: str):
        """處理標籤切換"""
        if tab_id != self.current_tab_id:
            # 取消之前選中的標籤
            if self.current_tab_id and self.current_tab_id in self.tabs:
                self.tabs[self.current_tab_id].setChecked(False)

            # 設置新的標籤
            self.current_tab_id = tab_id
            self.tabs[tab_id].setChecked(True)

            # 確保新選中的標籤可見
            self._ensure_tab_visible(tab_id)

            # 發送信號
            self.tab_changed.emit(tab_id)

            # 強制重繪整個組件
            self.update()

    def sizeHint(self):
        """提供建議的大小"""
        return QSize(56, 300)  # 適當的默認大小

    def minimumSizeHint(self):
        """提供最小建議大小"""
        return QSize(56, 100)  # 最小高度

    def wheelEvent(self, event: QWheelEvent):
        """處理滾輪事件"""
        # 將滾輪事件傳遞給滾動區域
        self.scroll_area.wheelEvent(event)


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
        # print( "Update Theme" )
        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        # 更新 ScrollArea 樣式
        self.scroll_area.setStyleSheet(f"""
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

        # 更新容器樣式
        self.container.setStyleSheet(f"""
            QWidget#tabs-container {{
                background-color: transparent;
            }}
        """)

        # 更新容器的背景色
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {current_theme.SURFACE};
            }}
        """)

        # 確保 viewport 保持透明
        self.scroll_area.viewport().setStyleSheet(
            "background-color: transparent;"
        )
