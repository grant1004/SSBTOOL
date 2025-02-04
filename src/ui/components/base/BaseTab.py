from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from typing import Dict


class BaseTab(QPushButton):
    """基礎標籤按鈕類"""
    tab_clicked = Signal(str)  # 改名為 tab_clicked 避免與 QPushButton 的 clicked 信號衝突

    def __init__(self, tab_id: str, config: dict, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.config = config
        self._setup_ui()
        # 連接原生的 clicked 信號到我們的處理函數
        super().clicked.connect(self._handle_click)

    def _handle_click(self):
        """處理點擊事件"""
        self.tab_clicked.emit(self.tab_id)

    def setChecked(self, checked: bool):
        """重寫 setChecked 以確保正確的重繪"""
        super().setChecked(checked)
        # 強制更新寬度
        width = 40 if checked else 32
        self.setFixedWidth(width)
        # 強制重繪
        self.update()
        # 更新父組件
        if self.parent():
            self.parent().update()

    def _setup_ui(self):
        self.setText(self.config.get('text', ''))
        # 初始高度固定，寬度會在 paintEvent 中動態設置
        self.setFixedHeight(self.config.get('height', 100))
        self.setCheckable(True)
        self.setAutoExclusive(True)  # 設置自動互斥
        self.setStyleSheet(self._get_style())

    def resizeEvent(self, event):
        """處理大小改變事件"""
        super().resizeEvent(event)
        # 根據選中狀態動態設置寬度
        width = 40 if self.isChecked() else 32
        self.setFixedSize(width, 100)

    def paintEvent(self, event):
        """重寫繪製事件來實現垂直文字"""
        # 先調整大小
        width = 40 if self.isChecked() else 32
        if self.width() != width:
            self.setFixedWidth(width)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 繪製背景
        if self.isChecked():
            painter.fillRect(self.rect(), QColor(self.config.get('active_bg', '#F5F5F5')))
        else:
            painter.fillRect(self.rect(), QColor(self.config.get('inactive_bg', '#EEEEEE')))

        # 設置字體
        font = self.font()
        font.setPointSize(10)
        if self.isChecked():
            font.setBold(True)
        painter.setFont(font)

        # 設置文字顏色
        if self.isChecked():
            painter.setPen(QColor(self.config.get('active_color', '#006C4D')))
        else:
            painter.setPen(QColor(self.config.get('inactive_color', '#666666')))

        # 保存當前狀態
        painter.save()

        # 計算文字區域
        text_rect = self.rect()
        painter.translate(text_rect.center())
        painter.rotate(90)  # 旋轉90度使文字垂直

        # 獲取文字尺寸
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        text_height = fm.height()

        # 繪製文字
        painter.drawText(
            -text_width // 2,
            text_height // 3,
            self.text()
        )

        # 恢復狀態
        painter.restore()

    def _get_style(self):
        return """
            QPushButton {
                border: none;
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
                text-weight: bold;
                text-size: 20px;
                font-size: 24px;
                font-weight: bold;
                padding: 0px;
            }
        """

    def sizeHint(self):
        """提供建議的大小"""
        return QSize(40 if self.isChecked() else 32, 60)

