# src/business_models/device_business_model.py
"""
設備業務模型實現
將 DeviceManager 的業務邏輯抽取到純業務層
"""

import asyncio
from typing import Dict, Optional, List, Callable
from enum import Enum
from PySide6.QtCore import QObject, Signal

# 導入接口
from src.interfaces.device_interface import (
    IDeviceBusinessModel, DeviceType, DeviceStatus, DeviceConnectionResult
)

# 導入 MVC 基類
from src.mvc_framework.base_model import BaseBusinessModel

# 導入現有的設備管理器（作為底層基礎設施）
from src.Manager import DeviceManager, DeviceType as OriginalDeviceType


class DeviceBusinessModel(BaseBusinessModel, IDeviceBusinessModel):
    """
    設備業務模型實現

    職責：
    1. 管理設備連接的業務邏輯
    2. 實施設備操作的業務規則
    3. 提供設備狀態的業務接口
    4. 處理設備相關的業務驗證

    設計原則：
    - 不包含 UI 邏輯
    - 不直接依賴 UI 組件
    - 通過信號通知狀態變更
    - 封裝底層的 DeviceManager
    """

    # 業務信號
    device_status_changed = Signal(DeviceType, DeviceStatus)
    device_connection_progress = Signal(DeviceType, int)  # 連接進度 0-100
    device_error_occurred = Signal(DeviceType, str, str)  # device_type, error_code, error_message
    device_operation_completed = Signal(DeviceType, str, bool)  # device_type, operation, success

    def __init__(self):
        super().__init__()

        # 設備狀態管理
        self._device_statuses: Dict[DeviceType, DeviceStatus] = {
            DeviceType.USB: DeviceStatus.DISCONNECTED,
            DeviceType.LOADER: DeviceStatus.DISCONNECTED,
            DeviceType.POWER: DeviceStatus.DISCONNECTED
        }

        # 設備信息緩存
        self._device_info_cache: Dict[DeviceType, Dict[str, any]] = {}

        # 操作狀態追蹤
        self._ongoing_operations: Dict[DeviceType, str] = {}

        # 業務規則配置
        self._max_retry_count = 3
        self._connection_timeout = 30  # 秒
        self._simultaneous_connections_allowed = True

        # 底層設備管理器
        self._device_manager = DeviceManager.instance()

        # 連接底層事件
        self._setup_device_manager_callbacks()

        # 設置業務驗證規則
        self._setup_validation_rules()

        self.log_operation("device_business_model_initialized", True, "設備業務模型初始化完成")

    # ==================== IDeviceBusinessModel 接口實現 ====================

    async def connect_device(self, device_type: DeviceType) -> DeviceConnectionResult:
        """
        連接設備 - 核心業務邏輯

        Business Rules:
        - 檢查設備是否已連接
        - 檢查是否有其他設備操作正在進行
        - 驗證系統狀態是否允許連接
        - 處理連接重試邏輯
        """
        operation_name = f"connect_{device_type.value}"
        self.operation_started.emit(operation_name)

        try:
            # 1. 業務規則檢查
            validation_result = self._validate_connection_request(device_type)
            if not validation_result.success:
                return validation_result

            # 2. 更新狀態為連接中
            self._update_device_status(device_type, DeviceStatus.CONNECTING)
            self._ongoing_operations[device_type] = "connecting"

            # 3. 執行連接邏輯
            connection_result = await self._perform_device_connection(device_type)

            # 4. 處理連接結果
            if connection_result.success:
                self._update_device_status(device_type, DeviceStatus.CONNECTED)
                self._cache_device_info(device_type)
                self.log_operation(operation_name, True, f"設備 {device_type.value} 連接成功")
            else:
                self._update_device_status(device_type, DeviceStatus.ERROR)
                self.log_operation(operation_name, False,
                                   f"設備 {device_type.value} 連接失敗: {connection_result.message}")

            # 5. 清理操作狀態
            self._ongoing_operations.pop(device_type, None)

            # 6. 發送業務事件
            self.device_operation_completed.emit(device_type, "connect", connection_result.success)
            self.operation_completed.emit(operation_name, connection_result.success)

            return connection_result

        except Exception as e:
            # 異常處理
            self._update_device_status(device_type, DeviceStatus.ERROR)
            self._ongoing_operations.pop(device_type, None)

            error_message = f"設備連接過程中發生異常: {str(e)}"
            self.log_operation(operation_name, False, error_message)
            self.device_error_occurred.emit(device_type, "CONNECTION_EXCEPTION", error_message)
            self.operation_completed.emit(operation_name, False)

            return DeviceConnectionResult(False, error_message, "CONNECTION_EXCEPTION")

    async def disconnect_device(self, device_type: DeviceType) -> DeviceConnectionResult:
        """斷開設備連接"""
        operation_name = f"disconnect_{device_type.value}"
        self.operation_started.emit(operation_name)

        try:
            # 1. 檢查設備是否已連接
            if self._device_statuses[device_type] != DeviceStatus.CONNECTED:
                return DeviceConnectionResult(False, f"設備 {device_type.value} 未連接", "NOT_CONNECTED")

            # 2. 檢查是否有正在進行的操作
            if device_type in self._ongoing_operations:
                return DeviceConnectionResult(False, f"設備 {device_type.value} 正在執行操作", "DEVICE_BUSY")

            # 3. 執行斷開邏輯
            self._ongoing_operations[device_type] = "disconnecting"
            original_device_type = self._convert_to_original_device_type(device_type)

            try:
                self._device_manager.worker.disconnect_device(original_device_type)
                self._update_device_status(device_type, DeviceStatus.DISCONNECTED)
                self._device_info_cache.pop(device_type, None)

                result = DeviceConnectionResult(True, f"設備 {device_type.value} 斷開成功")
                self.log_operation(operation_name, True, result.message)

            except Exception as e:
                result = DeviceConnectionResult(False, f"設備斷開失敗: {str(e)}", "DISCONNECT_FAILED")
                self.log_operation(operation_name, False, result.message)

            # 4. 清理狀態
            self._ongoing_operations.pop(device_type, None)
            self.device_operation_completed.emit(device_type, "disconnect", result.success)
            self.operation_completed.emit(operation_name, result.success)

            return result

        except Exception as e:
            error_message = f"設備斷開過程中發生異常: {str(e)}"
            self.log_operation(operation_name, False, error_message)
            self.device_error_occurred.emit(device_type, "DISCONNECT_EXCEPTION", error_message)
            self.operation_completed.emit(operation_name, False)

            return DeviceConnectionResult(False, error_message, "DISCONNECT_EXCEPTION")

    def get_device_status(self, device_type: DeviceType) -> DeviceStatus:
        """獲取設備當前狀態"""
        return self._device_statuses.get(device_type, DeviceStatus.DISCONNECTED)

    def get_all_device_status(self) -> Dict[DeviceType, DeviceStatus]:
        """獲取所有設備狀態"""
        return self._device_statuses.copy()

    def is_device_available(self, device_type: DeviceType) -> bool:
        """檢查設備是否可用（業務規則檢查）"""
        status = self._device_statuses.get(device_type, DeviceStatus.DISCONNECTED)

        # 業務規則：設備必須已連接且沒有正在進行的操作
        return (status == DeviceStatus.CONNECTED and
                device_type not in self._ongoing_operations)

    def can_perform_operation(self, device_type: DeviceType, operation: str) -> bool:
        """檢查是否可以執行特定操作（業務規則驗證）"""
        # 基本檢查：設備必須可用
        if not self.is_device_available(device_type):
            return False

        # 特定操作的業務規則
        if operation == "test_execution":
            # 測試執行需要所有相關設備都連接
            return self._check_test_execution_prerequisites(device_type)
        elif operation == "firmware_update":
            # 固件更新需要設備空閒
            return device_type not in self._ongoing_operations
        elif operation == "configuration":
            # 配置操作需要設備連接但不一定空閒
            return self._device_statuses[device_type] == DeviceStatus.CONNECTED

        return True

    def get_device_info(self, device_type: DeviceType) -> Optional[Dict[str, any]]:
        """獲取設備詳細信息"""
        return self._device_info_cache.get(device_type)

    def register_status_observer(self, callback: Callable[[DeviceType, DeviceStatus], None]):
        """註冊設備狀態變更觀察者"""
        self.device_status_changed.connect(callback)

    def unregister_status_observer(self, callback: Callable[[DeviceType, DeviceStatus], None]):
        """取消註冊設備狀態變更觀察者"""
        self.device_status_changed.disconnect(callback)

    # ==================== 業務邏輯實現方法 ====================

    def _validate_connection_request(self, device_type: DeviceType) -> DeviceConnectionResult:
        """驗證連接請求的業務規則"""

        # 1. 檢查設備是否已連接
        current_status = self._device_statuses[device_type]
        if current_status == DeviceStatus.CONNECTED:
            return DeviceConnectionResult(False, f"設備 {device_type.value} 已經連接", "ALREADY_CONNECTED")

        # 2. 檢查是否有正在進行的操作
        if device_type in self._ongoing_operations:
            ongoing_op = self._ongoing_operations[device_type]
            return DeviceConnectionResult(False, f"設備 {device_type.value} 正在執行 {ongoing_op}", "DEVICE_BUSY")

        # 3. 檢查系統狀態（如果有其他系統級限制）
        if not self._is_system_ready_for_connection():
            return DeviceConnectionResult(False, "系統未準備好進行設備連接", "SYSTEM_NOT_READY")

        # 4. 檢查設備特定的前置條件
        device_specific_check = self._check_device_specific_prerequisites(device_type)
        if not device_specific_check.success:
            return device_specific_check

        return DeviceConnectionResult(True, "連接請求驗證通過")

    async def _perform_device_connection(self, device_type: DeviceType) -> DeviceConnectionResult:
        """執行實際的設備連接"""
        original_device_type = self._convert_to_original_device_type(device_type)

        retry_count = 0
        while retry_count < self._max_retry_count:
            try:
                # 報告進度
                progress = int((retry_count / self._max_retry_count) * 50)
                self.device_connection_progress.emit(device_type, progress)

                # 嘗試連接
                result = await self._device_manager.connect_device(original_device_type)

                if result:
                    # 連接成功，完成進度
                    self.device_connection_progress.emit(device_type, 100)
                    return DeviceConnectionResult(True, f"設備 {device_type.value} 連接成功")
                else:
                    retry_count += 1
                    if retry_count < self._max_retry_count:
                        # 等待後重試
                        await asyncio.sleep(1)
                        continue
                    else:
                        return DeviceConnectionResult(False,
                                                      f"設備 {device_type.value} 連接失敗，已重試 {self._max_retry_count} 次",
                                                      "CONNECTION_FAILED")

            except Exception as e:
                retry_count += 1
                if retry_count < self._max_retry_count:
                    await asyncio.sleep(1)
                    continue
                else:
                    return DeviceConnectionResult(False, f"設備連接異常: {str(e)}", "CONNECTION_EXCEPTION")

        return DeviceConnectionResult(False, "連接失敗", "UNKNOWN_ERROR")

    def _update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態並發送通知"""
        old_status = self._device_statuses[device_type]
        if old_status != status:
            self._device_statuses[device_type] = status
            self.device_status_changed.emit(device_type, status)
            self.data_changed.emit("device_status", {
                'device_type': device_type,
                'old_status': old_status,
                'new_status': status
            })

    def _cache_device_info(self, device_type: DeviceType) -> None:
        """緩存設備信息"""
        try:
            # 從底層設備管理器獲取設備信息
            original_device_type = self._convert_to_original_device_type(device_type)
            device_instance = self._device_manager.worker.get_device(original_device_type)

            if device_instance:
                info = {
                    'device_type': device_type.value,
                    'status': device_instance.status,
                    'is_connected': device_instance.is_connected,
                    'connection_time': asyncio.get_event_loop().time(),
                }

                # 根據設備類型添加特定信息
                if device_type == DeviceType.USB:
                    info.update({
                        'vendor_id': getattr(device_instance, 'vendor_id', None),
                        'product_id': getattr(device_instance, 'product_id', None),
                    })

                self._device_info_cache[device_type] = info

        except Exception as e:
            self._logger.warning(f"Failed to cache device info for {device_type.value}: {e}")

    def _convert_to_original_device_type(self, device_type: DeviceType) -> OriginalDeviceType:
        """轉換設備類型到原始枚舉"""
        mapping = {
            DeviceType.USB: OriginalDeviceType.USB,
            DeviceType.LOADER: OriginalDeviceType.LOADER,
            DeviceType.POWER: OriginalDeviceType.POWER
        }
        return mapping[device_type]

    def _convert_from_original_device_type(self, original_device_type: OriginalDeviceType) -> DeviceType:
        """從原始設備類型轉換"""
        mapping = {
            OriginalDeviceType.USB: DeviceType.USB,
            OriginalDeviceType.LOADER: DeviceType.LOADER,
            OriginalDeviceType.POWER: DeviceType.POWER
        }
        return mapping[original_device_type]

    def _setup_device_manager_callbacks(self) -> None:
        """設置底層設備管理器的回調"""
        self._device_manager.register_status_callback(self._on_underlying_status_changed)
        self._device_manager.register_error_callback(self._on_underlying_error)

    def _on_underlying_status_changed(self, device_type_str: str, connected: bool) -> None:
        """處理底層設備狀態變更"""
        try:
            # 轉換設備類型
            original_device_type = OriginalDeviceType(device_type_str)
            device_type = self._convert_from_original_device_type(original_device_type)

            # 更新業務層狀態
            new_status = DeviceStatus.CONNECTED if connected else DeviceStatus.DISCONNECTED
            self._update_device_status(device_type, new_status)

            # 如果設備斷開，清理相關信息
            if not connected:
                self._device_info_cache.pop(device_type, None)
                self._ongoing_operations.pop(device_type, None)

        except Exception as e:
            self._logger.error(f"Error handling underlying status change: {e}")

    def _on_underlying_error(self, device_type_str: str, error_message: str) -> None:
        """處理底層設備錯誤"""
        try:
            original_device_type = OriginalDeviceType(device_type_str)
            device_type = self._convert_from_original_device_type(original_device_type)

            self._update_device_status(device_type, DeviceStatus.ERROR)
            self.device_error_occurred.emit(device_type, "UNDERLYING_ERROR", error_message)

        except Exception as e:
            self._logger.error(f"Error handling underlying error: {e}")

    def _setup_validation_rules(self) -> None:
        """設置業務驗證規則"""
        # 設備類型驗證
        self.add_validation_rule(
            "device_type",
            lambda x: x in [dt for dt in DeviceType],
            "無效的設備類型"
        )

    def _is_system_ready_for_connection(self) -> bool:
        """檢查系統是否準備好進行設備連接"""
        # 可以在這裡添加系統級檢查
        # 例如：檢查是否有測試正在運行、系統資源是否充足等
        return True

    def _check_device_specific_prerequisites(self, device_type: DeviceType) -> DeviceConnectionResult:
        """檢查設備特定的前置條件"""
        if device_type == DeviceType.USB:
            # USB 設備特定檢查
            # 例如：檢查 USB 驅動是否安裝
            pass
        elif device_type == DeviceType.POWER:
            # 電源設備特定檢查
            # 例如：檢查電源連接
            pass
        elif device_type == DeviceType.LOADER:
            # 載入器設備特定檢查
            pass

        return DeviceConnectionResult(True, "設備前置條件檢查通過")

    def _check_test_execution_prerequisites(self, device_type: DeviceType) -> bool:
        """檢查測試執行的前置條件"""
        # 根據測試需求檢查相關設備
        # 例如：如果要測試 USB，可能還需要 Power 設備連接
        return True

    # ==================== 公共業務方法 ====================

    def refresh_all_device_status(self) -> None:
        """刷新所有設備狀態"""
        for device_type in DeviceType:
            try:
                original_device_type = self._convert_to_original_device_type(device_type)
                device_instance = self._device_manager.worker.get_device(original_device_type)

                if device_instance:
                    connected = device_instance.is_connected
                    new_status = DeviceStatus.CONNECTED if connected else DeviceStatus.DISCONNECTED
                    self._update_device_status(device_type, new_status)

                    if connected:
                        self._cache_device_info(device_type)

            except Exception as e:
                self._logger.warning(f"Failed to refresh status for {device_type.value}: {e}")
                self._update_device_status(device_type, DeviceStatus.ERROR)

    def get_connection_statistics(self) -> Dict[str, any]:
        """獲取連接統計信息"""
        connected_count = sum(1 for status in self._device_statuses.values()
                              if status == DeviceStatus.CONNECTED)

        return {
            'total_devices': len(DeviceType),
            'connected_devices': connected_count,
            'disconnected_devices': len(DeviceType) - connected_count,
            'devices_with_errors': sum(1 for status in self._device_statuses.values()
                                       if status == DeviceStatus.ERROR),
            'ongoing_operations': len(self._ongoing_operations)
        }

    def is_any_device_busy(self) -> bool:
        """檢查是否有任何設備正在忙碌"""
        return len(self._ongoing_operations) > 0

    def get_available_devices(self) -> List[DeviceType]:
        """獲取所有可用設備列表"""
        return [device_type for device_type in DeviceType
                if self.is_device_available(device_type)]

    # ==================== 生命週期管理 ====================

    def stop(self) -> None:
        """停止設備業務模型"""
        try:
            # 斷開所有連接的設備
            for device_type in DeviceType:
                if self._device_statuses[device_type] == DeviceStatus.CONNECTED:
                    asyncio.create_task(self.disconnect_device(device_type))

            # 清理緩存
            self._device_info_cache.clear()
            self._ongoing_operations.clear()

            # 清理觀察者
            self.clear_cache()

            self.log_operation("device_business_model_stopped", True, "設備業務模型已停止")

        except Exception as e:
            self._logger.error(f"Error stopping device business model: {e}")


# ==================== 工廠方法 ====================

class DeviceBusinessModelFactory:
    """設備業務模型工廠"""

    @staticmethod
    def create_model() -> DeviceBusinessModel:
        """創建設備業務模型實例"""
        return DeviceBusinessModel()

    @staticmethod
    def create_model_with_config(config: Dict[str, any]) -> DeviceBusinessModel:
        """使用配置創建設備業務模型"""
        model = DeviceBusinessModel()

        # 應用配置
        if 'max_retry_count' in config:
            model._max_retry_count = config['max_retry_count']
        if 'connection_timeout' in config:
            model._connection_timeout = config['connection_timeout']
        if 'simultaneous_connections_allowed' in config:
            model._simultaneous_connections_allowed = config['simultaneous_connections_allowed']

        return model