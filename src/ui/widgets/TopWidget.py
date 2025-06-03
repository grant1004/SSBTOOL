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

# 導入舊的 DeviceManager（作為回退）
from src.Manager import DeviceManager, DeviceType as OldDeviceType


class TopWidgetAdapter(BaseView, IDeviceView, IDeviceViewEvents):
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

        # 舊架構支持（回退機制）
        self._old_device_manager = None

        # 初始化
        self._setup_mvc_architecture()
        self.setup_ui()

        self._logger.info("TopWidget initialized with MVC adapter")

    def _setup_mvc_architecture(self) -> None:
        """設置 MVC 架構"""
        try:
            if self._use_new_architecture:
                # 創建或獲取業務模型
                device_model = DeviceBusinessModel()

                # 創建控制器
                self._device_controller = DeviceController(device_model)

                # 註冊視圖到控制器
                self._device_controller.register_view(self)

                # 註冊控制器到視圖
                self.register_controller("device", self._device_controller)

                self._logger.info("New MVC architecture initialized successfully")
            else:
                self._setup_fallback_architecture()

        except Exception as e:
            self._logger.error(f"Failed to setup MVC architecture: {e}")
            self._setup_fallback_architecture()

    def _setup_fallback_architecture(self) -> None:
        """設置回退架構（使用舊的 DeviceManager）"""
        self._use_new_architecture = False
        self._old_device_manager = DeviceManager.instance()
        self._old_device_manager.register_status_callback(self._on_old_device_status_update)
        self._old_device_manager.register_error_callback(self._on_old_device_error)
        self._logger.info("Fallback to old architecture")

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
            if self._use_new_architecture and self._device_controller:
                # 使用新架構
                self.on_connect_requested(device_type)
            else:
                # 回退到舊架構
                asyncio.create_task(self._handle_old_button_click(device_type))

        except Exception as e:
            self._logger.error(f"Error handling button click: {e}")
            # 緊急回退
            asyncio.create_task(self._handle_old_button_click(device_type))

    async def _handle_old_button_click(self, device_type: DeviceType) -> None:
        """舊架構的按鈕點擊處理（回退機制）"""
        try:
            old_device_type = self._convert_to_old_device_type(device_type)
            await self._old_device_manager.connect_device(old_device_type)
        except Exception as e:
            self._logger.error(f"Error in old button click handling: {e}")

    # ==================== IDeviceView 接口實現 ====================

    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態顯示"""
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

    # ==================== 舊架構兼容方法 ====================

    def _on_old_device_status_update(self, device_type_str: str, status: bool) -> None:
        """處理舊架構的設備狀態更新"""
        try:
            device_type = self._convert_from_old_device_type_str(device_type_str)
            if device_type in self.status_buttons:
                self.status_buttons[device_type].update_status(status)
        except Exception as e:
            self._logger.error(f"Error handling old device status update: {e}")

    def _on_old_device_error(self, device_type_str: str, error_message: str) -> None:
        """處理舊架構的設備錯誤"""
        device_name = device_type_str
        self.show_error_message(f"{device_name} 設備錯誤: {error_message}")

    def _convert_to_old_device_type(self, device_type: DeviceType) -> OldDeviceType:
        """轉換到舊的設備類型"""
        mapping = {
            DeviceType.USB: OldDeviceType.USB,
            DeviceType.LOADER: OldDeviceType.LOADER,
            DeviceType.POWER: OldDeviceType.POWER
        }
        return mapping[device_type]

    def _convert_from_old_device_type_str(self, device_type_str: str) -> DeviceType:
        """從舊的設備類型字符串轉換"""
        mapping = {
            "USB": DeviceType.USB,
            "LOADER": DeviceType.LOADER,
            "POWER": DeviceType.POWER
        }
        return mapping.get(device_type_str, DeviceType.USB)

    # ==================== 公共方法（保持向後兼容） ====================

    def update_device_status_legacy(self, device_type: str, status: bool) -> None:
        """舊的設備狀態更新方法（向後兼容）"""
        try:
            new_device_type = self._convert_from_old_device_type_str(device_type)
            new_status = DeviceStatus.CONNECTED if status else DeviceStatus.DISCONNECTED
            self.update_device_status(new_device_type, new_status)
        except Exception as e:
            self._logger.error(f"Error in legacy status update: {e}")

    def handle_device_error_legacy(self, device_type: str, error_msg: str) -> None:
        """舊的設備錯誤處理方法（向後兼容）"""
        self._on_old_device_error(device_type, error_msg)

    # ==================== 配置和診斷方法 ====================

    def switch_to_new_architecture(self) -> bool:
        """切換到新架構"""
        try:
            if not self._use_new_architecture:
                self._setup_mvc_architecture()
                return self._use_new_architecture
            return True
        except Exception as e:
            self._logger.error(f"Failed to switch to new architecture: {e}")
            return False

    def switch_to_old_architecture(self) -> None:
        """切換到舊架構"""
        self._use_new_architecture = False
        if self._device_controller:
            self._device_controller.unregister_view(self)
        self._setup_fallback_architecture()

    def get_architecture_status(self) -> Dict[str, Any]:
        """獲取架構狀態"""
        return {
            'using_new_architecture': self._use_new_architecture,
            'controller_available': self._device_controller is not None,
            'old_manager_available': self._old_device_manager is not None,
            'registered_devices': list(self.devices.keys()),
            'button_count': len(self.status_buttons)
        }

    def force_status_refresh(self) -> None:
        """強制刷新所有設備狀態"""
        if self._use_new_architecture and self._device_controller:
            self._device_controller.refresh_device_status()
        elif self._old_device_manager:
            # 舊架構的狀態刷新邏輯
            for device_type in self.devices.keys():
                old_device_type = self._convert_to_old_device_type(device_type)
                try:
                    # 這裡可以添加舊架構的狀態檢查邏輯
                    pass
                except Exception as e:
                    self._logger.error(f"Error refreshing old device status: {e}")

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
            results['architecture_ok'] = (
                                                 self._use_new_architecture and self._device_controller is not None
                                         ) or (
                                                 not self._use_new_architecture and self._old_device_manager is not None
                                         )

        except Exception as e:
            self._logger.error(f"Error verifying UI behavior: {e}")
            results['verification_error'] = str(e)

        return results


# ==================== 兼容性工廠方法 ====================

class TopWidget(TopWidgetAdapter):
    """
    TopWidget 的兼容性別名
    確保現有代碼不需要修改
    """
    pass


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


# ==================== 使用示例 ====================
"""
# 使用新架構（默認）
top_widget = TopWidget(parent)

# 檢查狀態
status = top_widget.get_architecture_status()
print(f"Using new architecture: {status['using_new_architecture']}")

# 手動切換架構（如果需要）
if not top_widget.switch_to_new_architecture():
    print("Failed to switch to new architecture, using fallback")

# 驗證 UI 行為
behavior_check = top_widget.verify_ui_behavior()
if not all(behavior_check.values()):
    print(f"UI behavior issues detected: {behavior_check}")

# 強制刷新狀態
top_widget.force_status_refresh()
"""