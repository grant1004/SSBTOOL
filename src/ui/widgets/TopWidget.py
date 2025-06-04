# src/ui/widgets/TopWidget.py - 直接更新版本
"""
TopWidget 直接使用新的 ComponentStatusButton
簡潔的 MVC 架構集成，移除所有向後兼容代碼
"""

import asyncio
from typing import Dict, Any, Optional

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# 導入 MVC 架構
from src.interfaces.device_interface import IDeviceView, IDeviceViewEvents, DeviceType, DeviceStatus
from src.mvc_framework.base_view import BaseView
from src.controllers.device_controller import DeviceController

# 導入新的狀態按鈕
from src.ui.components.StatusButton import ComponentStatusButton


class TopWidget(BaseView, IDeviceView, IDeviceViewEvents):
    """
    現代化的 TopWidget
    直接使用新的 ComponentStatusButton，無向後兼容負擔
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._device_controller: Optional[DeviceController] = None

        # 設備配置
        self.devices = {
            DeviceType.USB: {'icon': 'parts_cable', 'name': 'USB'},
            DeviceType.POWER: {'icon': 'show_chart', 'name': 'Power'},
            DeviceType.LOADER: {'icon': 'parts_charger', 'name': 'Loader'}
        }

        self.status_buttons: Dict[DeviceType, ComponentStatusButton] = {}

        self.setup_ui()
        self._logger.info("TopWidget initialized with modern ComponentStatusButton")

    def set_device_controller(self, controller: DeviceController) -> None:
        """設置設備控制器"""
        self._device_controller = controller
        if controller:
            # 立即註冊到控制器
            controller.register_view(self)
        self._logger.info("Device controller set and view registered")

    # ==================== UI 設置 ====================

    def setup_ui(self):
        """設置 UI"""
        self.setFixedHeight(52)
        self.setContentsMargins(0, 0, 0, 0)
        self._setup_shadow()

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 4, 16, 4)
        main_layout.setSpacing(8)


        # 創建設備按鈕
        for device_type, config in self.devices.items():
            button = ComponentStatusButton(config['name'], config['icon'], self.main_window)
            self.status_buttons[device_type] = button

            # 連接事件
            button.clicked.connect(lambda checked, dt=device_type: self._handle_device_click(dt))
            button.status_changed.connect(lambda old, new, dt=device_type:
                                          self._on_status_changed(dt, old, new))

            main_layout.addWidget(button)

        # 添加彈性空間
        main_layout.addStretch()

    def _setup_shadow(self):
        """設置陰影效果"""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ==================== 事件處理 ====================

    def _handle_device_click(self, device_type: DeviceType):
        """處理設備點擊"""
        if not self._device_controller:
            self._logger.error("No device controller available")
            return

        current_status = self.status_buttons[device_type].current_status
        self._logger.info(f"Device {device_type.value} status: {current_status.value}")
        if current_status == DeviceStatus.DISCONNECTED or current_status == DeviceStatus.ERROR:
            # 請求連接
            asyncio.create_task(self._device_controller.handle_connect_request(device_type))
        elif current_status == DeviceStatus.CONNECTED:
            # 請求斷開
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))
        # 連接中或忙碌狀態不響應點擊

    def _on_status_changed(self, device_type: DeviceType, old_status: DeviceStatus, new_status: DeviceStatus):
        """狀態變更回調"""
        self._logger.debug(f"Device {device_type.value} status: {old_status.value} -> {new_status.value}")

    # ==================== IDeviceView 接口實現 ====================

    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態顯示"""
        self._logger.debug(f"Updating {device_type.value} to {status.value}")

        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(status)
        else:
            self._logger.warning(f"No button found for device: {device_type.value}")

    def show_connection_progress(self, device_type: DeviceType, progress: int) -> None:
        """顯示連接進度"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].set_connection_progress(progress)

    def show_connection_success(self, device_type: DeviceType) -> None:
        """顯示連接成功"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.CONNECTED)

        device_name = self.devices[device_type]['name']
        self.show_success_message(f"{device_name} 連接成功")

    def show_connection_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示連接錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        self.show_error_message(f"{device_name} 連接失敗: {error_message}")

    def show_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示設備錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        self.show_error_message(f"{device_name} 錯誤: {error_message}")

    def enable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """啟用設備控制項"""
        if device_type is None:
            for button in self.status_buttons.values():
                button.setEnabled(True)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(True)

    def disable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """禁用設備控制項"""
        if device_type is None:
            for button in self.status_buttons.values():
                button.setEnabled(False)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(False)

    def update_device_info(self, device_type: DeviceType, info: Dict[str, Any]) -> None:
        """更新設備詳細信息"""
        if device_type in self.status_buttons:
            device_name = self.devices[device_type]['name']
            tooltip = f"{device_name}\n狀態: {info.get('status', 'Unknown')}"

            if 'connection_time' in info:
                tooltip += f"\n連接時間: {info['connection_time']:.1f}s"

            self.status_buttons[device_type].setToolTip(tooltip)

    def request_user_confirmation(self, message: str) -> bool:
        """請求用戶確認"""
        return self.ask_user_confirmation(message, "設備操作確認")

    async def request_user_confirmation_async(self, message: str) -> bool:
        """異步請求用戶確認"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.request_user_confirmation, message
        )

    # ==================== IDeviceViewEvents 接口實現 ====================

    def on_connect_requested(self, device_type: DeviceType) -> None:
        """連接請求"""
        if self._device_controller:
            asyncio.create_task(self._device_controller.handle_connect_request(device_type))

    def on_disconnect_requested(self, device_type: DeviceType) -> None:
        """斷開請求"""
        if self._device_controller:
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))

    def on_refresh_requested(self) -> None:
        """刷新請求"""
        if self._device_controller:
            self._device_controller.refresh_device_status()

    def on_device_settings_requested(self, device_type: DeviceType) -> None:
        """設備設置請求"""
        self.emit_user_action("device_settings_requested", device_type)

    # ==================== 便利方法 ====================

    def get_all_device_status(self) -> Dict[DeviceType, DeviceStatus]:
        """獲取所有設備狀態"""
        return {dt: btn.current_status for dt, btn in self.status_buttons.items()}

    def set_all_disconnected(self) -> None:
        """設置所有設備為斷開狀態"""
        for button in self.status_buttons.values():
            button.update_status(DeviceStatus.DISCONNECTED)

    def get_connection_summary(self) -> Dict[str, int]:
        """獲取連接摘要"""
        summary = {'total': 0, 'connected': 0, 'error': 0, 'connecting': 0}

        for button in self.status_buttons.values():
            summary['total'] += 1
            status = button.current_status

            if status == DeviceStatus.CONNECTED:
                summary['connected'] += 1
            elif status == DeviceStatus.ERROR:
                summary['error'] += 1
            elif status == DeviceStatus.CONNECTING:
                summary['connecting'] += 1

        return summary
# ==================== 功能開關配置 ====================

class TopWidgetConfig:

    """TopWidget 配置類"""
    USE_NEW_ARCHITECTURE = True
    ENABLE_AUTO_FALLBACK = True
    ENABLE_STATUS_LOGGING = True
    REFRESH_INTERVAL = 30  # 秒

    @classmethod
    def enable_new_architecture(cls):
        cls.USE_NEW_ARCHITECTURE = True

    @classmethod
    def disable_new_architecture(cls):
        cls.USE_NEW_ARCHITECTURE = False

