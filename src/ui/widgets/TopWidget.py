# src/ui/widgets/TopWidget.py - 重構版本
"""
TopWidget 適配新的 MVC 架構
使用適配器模式確保 UI 行為完全不變，同時內部使用新的架構
"""

import asyncio
from typing import Dict, Any, Optional

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# 導入新的 MVC 架構
from src.interfaces.device_interface import IDeviceView, IDeviceViewEvents, DeviceType, DeviceStatus
from src.mvc_framework.base_view import BaseView
from src.controllers.device_controller import DeviceController
from src.business_models.device_business_model import DeviceBusinessModel

# 導入原有組件（保持 UI 一致性）
from src.ui.components import ComponentStatusButton

class TopWidget(BaseView, IDeviceView, IDeviceViewEvents):
    """
    TopWidget 的 MVC 適配器

    策略：
    1. 實現新的 MVC 接口
    2. 保持原有的 UI 組件和行為
    3. 內部委託給新的 DeviceController
    4. 提供回退機制確保穩定性
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent

        # MVC 架構組件
        self._device_controller: Optional[DeviceController] = None
        self._use_new_architecture = True  # 功能開關

        # 保持原有的 UI 組件
        self.status_buttons = {}
        self.devices = {
            DeviceType.USB: {'icon': 'parts_cable', 'name': 'USB'},
            DeviceType.POWER: {'icon': 'show_chart', 'name': 'Power'},
            DeviceType.LOADER: {'icon': 'parts_charger', 'name': 'Loader'}
        }

        # 初始化
        self.setup_ui()

        self._logger.info("TopWidget initialized with MVC adapter")

    def set_device_controller(self, controller: DeviceController) -> None:
        self._device_controller = controller

    # ==================== 保持原有的 UI 設置 ====================

    def setup_ui(self):
        """保持原有的 UI 設置邏輯完全不變"""
        self.setFixedHeight(44)
        self.setContentsMargins(0, 0, 0, 0)
        self._setup_shadow()
        self.init_ui()

    def _setup_shadow(self):
        """保持原有的陰影設置"""
        self.shadow = QGraphicsDropShadowEffect(parent=self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def init_ui(self):
        """保持原有的 UI 初始化邏輯"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("TagContainer")

        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        for device_type, config in self.devices.items():
            device_container = self._create_device_container(device_type, config)
            container_layout.addWidget(device_container)

        main_layout.addWidget(container)

    def _create_device_container(self, device_type, config):
        """保持原有的設備容器創建邏輯"""
        device_container = QWidget()
        device_layout = QHBoxLayout(device_container)
        device_layout.setContentsMargins(16, 0, 8, 0)
        device_layout.setSpacing(0)
        device_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # 使用原有的 ComponentStatusButton
        button = ComponentStatusButton(config['name'], config['icon'], self.main_window)
        button.setFixedSize(200, 30)
        self.status_buttons[device_type] = button

        # 連接點擊事件到新的處理方法
        button.clicked.connect(lambda: self._handle_device_button_click(device_type))

        device_layout.addWidget(button, 0)
        return device_container

    # ==================== 新的事件處理（適配 MVC） ====================

    def _handle_device_button_click(self, device_type: DeviceType) -> None:
        """處理設備按鈕點擊 - 適配到 MVC 架構"""
        try:
            if self._device_controller:
                self.on_connect_requested(device_type)

        except Exception as e:
            self._logger.error(f"Error handling button click: {e}")

    # ==================== IDeviceView 接口實現 ====================

    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態顯示"""
        print( "Call update_device_status() in TopWidget.py")
        try:
            if device_type in self.status_buttons:
                button = self.status_buttons[device_type]
                is_connected = (status == DeviceStatus.CONNECTED)
                button.update_status(is_connected)

                self._logger.debug(f"Updated UI status for {device_type.value}: {status.value}")

        except Exception as e:
            self._logger.error(f"Error updating device status UI: {e}")

    def show_connection_progress(self, device_type: DeviceType, progress: int) -> None:
        """顯示連接進度"""
        # TopWidget 的按鈕不顯示進度，但可以改變狀態指示
        if device_type in self.status_buttons:
            button = self.status_buttons[device_type]
            # 可以在這裡添加進度顯示邏輯，比如改變按鈕顏色
            if progress < 100:
                # 連接中的視覺反饋
                button.setEnabled(False)

    def show_connection_success(self, device_type: DeviceType) -> None:
        """顯示連接成功"""
        if device_type in self.status_buttons:
            button = self.status_buttons[device_type]
            button.setEnabled(True)
            button.update_status(True)

        # 可以添加成功提示
        self.show_success_message(f"{self.devices[device_type]['name']} 設備連接成功")

    def show_connection_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示連接錯誤"""
        if device_type in self.status_buttons:
            button = self.status_buttons[device_type]
            button.setEnabled(True)
            button.update_status(False)

        # 顯示錯誤消息
        self.show_error_message(f"{self.devices[device_type]['name']} 設備連接失敗: {error_message}")

    def show_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示設備錯誤"""
        self.show_error_message(f"{self.devices[device_type]['name']} 設備錯誤: {error_message}")

    def enable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """啟用設備控制項"""
        if device_type is None:
            # 啟用所有設備控制項
            for button in self.status_buttons.values():
                button.setEnabled(True)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(True)

    def disable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """禁用設備控制項"""
        if device_type is None:
            # 禁用所有設備控制項
            for button in self.status_buttons.values():
                button.setEnabled(False)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(False)

    def update_device_info(self, device_type: DeviceType, info: Dict[str, Any]) -> None:
        """更新設備詳細信息顯示"""
        # TopWidget 不顯示詳細信息，但可以更新工具提示
        if device_type in self.status_buttons:
            button = self.status_buttons[device_type]
            tooltip = f"{self.devices[device_type]['name']} 設備\n"
            tooltip += f"狀態: {info.get('status', 'Unknown')}\n"
            if 'connection_time' in info:
                tooltip += f"連接時間: {info['connection_time']:.1f}s"
            button.setToolTip(tooltip)

    def request_user_confirmation(self, message: str) -> bool:
        """請求用戶確認（同步）"""
        return self.ask_user_confirmation(message, "設備操作確認")

    async def request_user_confirmation_async(self, message: str) -> bool:
        """請求用戶確認（異步）"""
        # 在主線程中顯示對話框
        result = await asyncio.get_event_loop().run_in_executor(
            None, self.request_user_confirmation, message
        )
        return result

    # ==================== IDeviceViewEvents 接口實現 ====================

    def on_connect_requested(self, device_type: DeviceType) -> None:
        """當用戶請求連接設備時觸發"""
        if self._device_controller:
            # 異步調用控制器
            asyncio.create_task(self._device_controller.handle_connect_request(device_type))
        else:
            self._logger.error("Device controller not available")

    def on_disconnect_requested(self, device_type: DeviceType) -> None:
        """當用戶請求斷開設備時觸發"""
        if self._device_controller:
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))

    def on_refresh_requested(self) -> None:
        """當用戶請求刷新狀態時觸發"""
        if self._device_controller:
            self._device_controller.refresh_device_status()

    def on_device_settings_requested(self, device_type: DeviceType) -> None:
        """當用戶請求設備設置時觸發"""
        # TopWidget 不處理設備設置，但可以發送事件
        self.emit_user_action("device_settings_requested", device_type)

    # ==================== 測試和驗證方法 ====================

    def verify_ui_behavior(self) -> Dict[str, bool]:
        """驗證 UI 行為是否正常"""
        results = {}

        try:
            # 檢查所有按鈕是否正常
            results['buttons_created'] = len(self.status_buttons) == len(self.devices)

            # 檢查按鈕是否可點擊
            results['buttons_clickable'] = all(
                button.isEnabled() for button in self.status_buttons.values()
            )

            # 檢查架構是否正常
            results['architecture_ok'] = (self._use_new_architecture and self._device_controller is not None)

        except Exception as e:
            self._logger.error(f"Error verifying UI behavior: {e}")
            results['verification_error'] = str(e)

        return results


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

