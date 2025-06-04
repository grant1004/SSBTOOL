# src/ui/components/StatusButton.py
"""
現代化的 ComponentStatusButton - 直接替換版本
移除所有向後兼容代碼，提供更簡潔的實現
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from enum import Enum
from typing import Dict, Optional, Any
from src.utils import get_icon_path, Utils
from src.interfaces.device_interface import DeviceStatus
import math


class ComponentStatusButton(QPushButton):
    """
    特性：
    - 多種狀態支持（斷開、連接中、已連接、錯誤、忙碌）
    - 進度指示器和流暢動畫
    - 自動主題適配
    - 直接集成 MVC 架構
    """

    # 信號
    status_changed = Signal(DeviceStatus, DeviceStatus)  # old_status, new_status
    connection_progress = Signal(int)  # progress (0-100)

    # 狀態顏色配置
    STATUS_COLORS = {
        DeviceStatus.DISCONNECTED: {
            'primary': '#FF5722',
            'light': '#FFCDD2',
            'text': '#D32F2F'
        },
        DeviceStatus.CONNECTING: {
            'primary': '#FF9800',
            'light': '#FFE0B2',
            'text': '#F57C00'
        },
        DeviceStatus.CONNECTED: {
            'primary': '#4CAF50',
            'light': '#C8E6C9',
            'text': '#388E3C'
        },
        DeviceStatus.ERROR: {
            'primary': '#F44336',
            'light': '#FFEBEE',
            'text': '#C62828'
        },
        DeviceStatus.BUSY: {
            'primary': '#2196F3',
            'light': '#BBDEFB',
            'text': '#1976D2'
        }
    }

    def __init__(self, component_name: str, icon_path: str, parent=None):
        super().__init__(parent)

        # 基本屬性
        self.component_name = component_name
        self.icon_path = icon_path
        self.parent_widget = parent

        # 狀態管理
        self.current_status = DeviceStatus.DISCONNECTED
        self.progress_value = 0

        # 獲取主題管理器
        self.theme_manager = self._get_theme_manager()

        # 設置 UI
        self._setup_ui()
        self._setup_animations()

        # 連接主題變更
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_theme)

        # 設置初始狀態
        self.update_status(DeviceStatus.DISCONNECTED)

    def _setup_ui(self):
        """設置 UI"""
        self.setFixedSize(220, 44)
        self.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 主布局
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 6, 12, 6)
        self.main_layout.setSpacing(10)

        # 狀態指示器
        self.status_indicator = StatusIndicator(self)
        self.status_indicator.setFixedSize(12, 12)
        self.main_layout.addWidget(self.status_indicator)

        # 設備圖標
        self.device_icon = QLabel()
        self.device_icon.setFixedSize(20, 20)
        self.device_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.device_icon)

        # 設備名稱
        self.name_label = QLabel(self.component_name)
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #2C3E50;
            }
        """)
        self.main_layout.addWidget(self.name_label, 1)

        # 狀態文本
        self.status_label = QLabel("Offline")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 500;
                color: #7F8C8D;
                min-width: 60px;
            }
        """)
        self.main_layout.addWidget(self.status_label)

        # 設置基本樣式
        self.setStyleSheet("""
            ComponentStatusButton {
                border: none;
                border-radius: 8px;
                background-color: transparent;
                text-align: left;
            }
        """)

    def _setup_animations(self):
        """設置動畫"""
        # 連接動畫定時器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_phase = 0

        # 懸停動畫
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def update_status(self, status: DeviceStatus, progress: int = 0):
        """更新設備狀態"""
        old_status = self.current_status
        self.current_status = status
        self.progress_value = max(0, min(100, progress))

        # 更新狀態文本
        status_texts = {
            DeviceStatus.DISCONNECTED: "Offline",
            DeviceStatus.CONNECTING: f"Connecting{f' {progress}%' if progress > 0 else '...'}",
            DeviceStatus.CONNECTED: "Online",
            DeviceStatus.ERROR: "Error",
            DeviceStatus.BUSY: "Busy"
        }

        self.status_label.setText(status_texts.get(status, "Unknown"))

        # 更新視覺狀態
        self._update_visual_state()

        # 處理動畫
        if status == DeviceStatus.CONNECTING:
            self._start_animation()
        else:
            self._stop_animation()

        # 發送信號
        if old_status != status:
            self.status_changed.emit(old_status, status)

        if progress > 0:
            self.connection_progress.emit(progress)

        self.setEnabled(True)

    def set_connection_progress(self, progress: int):
        """設置連接進度"""
        if self.current_status == DeviceStatus.CONNECTING:
            self.update_status(DeviceStatus.CONNECTING, progress)

    def _update_visual_state(self):
        """更新視覺狀態"""
        colors = self.STATUS_COLORS[self.current_status]

        # 更新狀態指示器
        self.status_indicator.set_status(self.current_status, self.progress_value)

        # 更新設備圖標
        self._update_device_icon(colors['primary'])

        # 更新按鈕樣式
        self._update_button_style(colors)

        # 更新文本顏色（根據主題）
        self._update_text_colors(colors)

    def _update_device_icon(self, color: str):
        """更新設備圖標"""
        try:
            icon = QIcon(get_icon_path(self.icon_path))
            colored_icon = Utils.change_icon_color(icon, color)
            pixmap = colored_icon.pixmap(20, 20)
            self.device_icon.setPixmap(pixmap)
        except Exception as e:
            print(f"Error updating device icon: {e}")

    def _update_button_style(self, colors: Dict[str, str]):
        """更新按鈕樣式"""
        # 根據主題獲取背景色
        if self.theme_manager:
            current_theme = self.theme_manager._themes[self.theme_manager._current_theme]
            bg_color = current_theme.SURFACE
            hover_color = current_theme.HOVER
        else:
            bg_color = colors['light']
            hover_color = colors['primary']

        self.setStyleSheet(f"""
            ComponentStatusButton {{
                border: none;
                border-radius: 8px;
                background-color: {bg_color};
                border-left: 3px solid {colors['primary']};
                text-align: left;
            }}
            ComponentStatusButton:hover {{
                background-color: {hover_color};
            }}
            ComponentStatusButton:pressed {{
                background-color: {colors['primary']};
            }}
        """)

    def _update_text_colors(self, colors: Dict[str, str]):
        """更新文本顏色"""
        if self.theme_manager:
            current_theme = self.theme_manager._themes[self.theme_manager._current_theme]
            name_color = current_theme.TEXT_PRIMARY
            status_color = current_theme.TEXT_SECONDARY
        else:
            name_color = colors['text']
            status_color = colors['text']

        self.name_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: 600;
                color: {name_color};
            }}
        """)

        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                font-weight: 500;
                color: {status_color};
                min-width: 60px;
            }}
        """)

    def _start_animation(self):
        """開始動畫"""
        self.animation_timer.start(100)

    def _stop_animation(self):
        """停止動畫"""
        self.animation_timer.stop()
        self.animation_phase = 0

    def _update_animation(self):
        """更新動畫"""
        self.animation_phase = (self.animation_phase + 1) % 60
        self.status_indicator.set_animation_phase(self.animation_phase)

    def _get_theme_manager(self):
        """獲取主題管理器"""
        parent = self.parent_widget
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent() if hasattr(parent, 'parent') else None
        return None

    def _update_theme(self):
        """更新主題"""
        self._update_visual_state()

    def get_device_info(self) -> Dict[str, Any]:
        """獲取設備信息"""
        return {
            'device_name': self.component_name,
            'current_status': self.current_status,
            'progress': self.progress_value,
            'is_connected': self.current_status == DeviceStatus.CONNECTED,
            'is_busy': self.current_status in [DeviceStatus.CONNECTING, DeviceStatus.BUSY]
        }


class StatusIndicator(QWidget):
    """狀態指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = DeviceStatus.DISCONNECTED
        self.progress = 0
        self.animation_phase = 0

    def set_status(self, status: DeviceStatus, progress: int = 0):
        """設置狀態"""
        self.status = status
        self.progress = progress
        self.update()

    def set_animation_phase(self, phase: int):
        """設置動畫相位"""
        self.animation_phase = phase
        self.update()

    def paintEvent(self, event):
        """繪製指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2 - 1

        colors = ComponentStatusButton.STATUS_COLORS[self.status]

        if self.status == DeviceStatus.CONNECTING:
            self._draw_connecting(painter, center, radius, colors)
        elif self.status == DeviceStatus.CONNECTED:
            self._draw_connected(painter, center, radius, colors)
        elif self.status == DeviceStatus.ERROR:
            self._draw_error(painter, center, radius, colors)
        elif self.status == DeviceStatus.BUSY:
            self._draw_busy(painter, center, radius, colors)
        else:  # DISCONNECTED
            self._draw_disconnected(painter, center, radius, colors)

    def _draw_connecting(self, painter, center, radius, colors):
        """繪製連接中"""
        # 背景圓
        painter.setBrush(QBrush(QColor(colors['light'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # 進度弧或旋轉動畫
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(colors['primary']), 2)
        painter.setPen(pen)

        if self.progress > 0:
            # 顯示進度
            start_angle = -90 * 16
            span_angle = int((self.progress / 100) * 360 * 16)
            painter.drawArc(center.x() - radius, center.y() - radius,
                            radius * 2, radius * 2, start_angle, span_angle)
        else:
            # 旋轉動畫
            angle = (self.animation_phase * 6) % 360
            start_angle = (angle - 90) * 16
            span_angle = 90 * 16
            painter.drawArc(center.x() - radius, center.y() - radius,
                            radius * 2, radius * 2, start_angle, span_angle)

    def _draw_connected(self, painter, center, radius, colors):
        """繪製已連接"""
        painter.setBrush(QBrush(QColor(colors['primary'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # 對勾
        painter.setPen(QPen(QColor("white"), 1.5))
        check_size = radius // 2
        painter.drawLine(center.x() - check_size // 2, center.y(),
                         center.x() - check_size // 4, center.y() + check_size // 2)
        painter.drawLine(center.x() - check_size // 4, center.y() + check_size // 2,
                         center.x() + check_size // 2, center.y() - check_size // 2)

    def _draw_error(self, painter, center, radius, colors):
        """繪製錯誤"""
        painter.setBrush(QBrush(QColor(colors['primary'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # X 符號
        painter.setPen(QPen(QColor("white"), 1.5))
        cross_size = radius // 2
        painter.drawLine(center.x() - cross_size, center.y() - cross_size,
                         center.x() + cross_size, center.y() + cross_size)
        painter.drawLine(center.x() + cross_size, center.y() - cross_size,
                         center.x() - cross_size, center.y() + cross_size)

    def _draw_busy(self, painter, center, radius, colors):
        """繪製忙碌"""
        painter.setBrush(QBrush(QColor(colors['light'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # 旋轉點
        painter.setBrush(QBrush(QColor(colors['primary'])))
        angle = (self.animation_phase * 12) % 360
        dot_radius = radius // 3
        dot_distance = radius - dot_radius

        dot_x = center.x() + dot_distance * math.cos(math.radians(angle))
        dot_y = center.y() + dot_distance * math.sin(math.radians(angle))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_radius, dot_radius)

    def _draw_disconnected(self, painter, center, radius, colors):
        """繪製斷開"""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(colors['primary']), 2))
        painter.drawEllipse(center, radius, radius)