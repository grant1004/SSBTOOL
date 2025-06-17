# src/business_models/device_business_model.py - 純新架構版本

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
from src.device.USBDevice import USBDevice
from src.device.PowerDevice import PowerDevice
from src.device.LoaderDevice import LoaderDevice


class DeviceBusinessModel(BaseBusinessModel, IDeviceBusinessModel):
    """
    設備業務模型實現 - 純新架構版本

    移除了所有舊架構適配代碼，直接管理設備實例
    """

    # 業務信號
    device_status_changed = Signal(DeviceType, DeviceStatus)
    device_connection_progress = Signal(DeviceType, int)
    device_error_occurred = Signal(DeviceType, str, str)
    device_operation_completed = Signal(DeviceType, str, bool)

    def __init__(self):
        super().__init__()

        # 設備狀態管理
        self._device_statuses: Dict[DeviceType, DeviceStatus] = {
            DeviceType.USB: DeviceStatus.DISCONNECTED,
            DeviceType.LOADER: DeviceStatus.DISCONNECTED,
            DeviceType.POWER: DeviceStatus.DISCONNECTED
        }

        # 直接管理設備實例（移除 DeviceManager）
        self._device_instances: Dict[DeviceType, object] = {
            DeviceType.USB: USBDevice(),
            DeviceType.LOADER: LoaderDevice(),
            DeviceType.POWER: PowerDevice()
        }

        # 設備信息緩存
        self._device_info_cache: Dict[DeviceType, Dict[str, any]] = {}

        # 操作狀態追蹤
        self._ongoing_operations: Dict[DeviceType, str] = {}

        # 業務規則配置
        self._max_retry_count = 1
        self._connection_timeout = 5
        self._simultaneous_connections_allowed = True

        # 設置設備實例的回調
        self._setup_device_callbacks()

        # 設置業務驗證規則
        self._setup_validation_rules()

        self.log_operation("device_business_model_initialized", True, "純新架構設備業務模型初始化完成")

    # ==================== IDeviceBusinessModel 接口實現 ====================

    async def connect_device(self, device_type: DeviceType) -> DeviceConnectionResult:
        """連接設備 - 純新架構實現"""
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
        """斷開設備連接 - 純新架構實現"""
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
            device_instance = self._device_instances[device_type]

            try:
                await device_instance.disconnect()
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
        """檢查設備是否可用"""
        status = self._device_statuses.get(device_type, DeviceStatus.DISCONNECTED)
        return (status == DeviceStatus.CONNECTED and
                device_type not in self._ongoing_operations)

    def can_perform_operation(self, device_type: DeviceType, operation: str) -> bool:
        """檢查是否可以執行特定操作"""
        if not self.is_device_available(device_type):
            return False

        # 特定操作的業務規則
        if operation == "test_execution":
            return self._check_test_execution_prerequisites(device_type)
        elif operation == "firmware_update":
            return device_type not in self._ongoing_operations
        elif operation == "configuration":
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

    # ==================== 業務邏輯實現方法（純新架構）====================

    async def _perform_device_connection(self, device_type: DeviceType, com_port: str = None ) -> DeviceConnectionResult:
        """執行實際的設備連接 - 直接操作設備實例"""
        device_instance = self._device_instances[device_type]

        retry_count = 0
        while retry_count < self._max_retry_count:
            try:
                # 報告進度
                progress = int((retry_count / self._max_retry_count) * 50)
                self.device_connection_progress.emit(device_type, progress)

                # 直接調用設備實例的連接方法
                if com_port is None:
                    result = await device_instance.connect()  # Power 設備需要端口
                else:
                    result = await device_instance.connect(com_port)  # Power 設備需要端口
                # if device_type == DeviceType.USB:
                #     result = await device_instance.connect()  # USB 設備不需要端口參數
                # elif device_type == DeviceType.POWER:
                #     if com_port is None:
                #         result = await device_instance.connect()  # Power 設備需要端口
                #     else :
                #         result = await device_instance.connect(com_port)  # Power 設備需要端口
                # elif device_type == DeviceType.LOADER:
                #     result = await device_instance.connect("COM19")  # Loader 設備需要端口
                # else:
                #     result = await device_instance.connect()

                if result:
                    # 連接成功，完成進度
                    self.device_connection_progress.emit(device_type, 100)
                    return DeviceConnectionResult(True, f"設備 {device_type.value} 連接成功")
                else:
                    retry_count += 1
                    if retry_count < self._max_retry_count:
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

    def _setup_device_callbacks(self) -> None:
        """設置設備實例的回調 - 純新架構"""
        for device_type, device_instance in self._device_instances.items():
            # 如果設備支持狀態回調，可以在這裡設置
            # 注意：這取決於您的設備基類是否提供回調機制
            if hasattr(device_instance, 'register_status_callback'):
                device_instance.register_status_callback(
                    lambda connected, dt=device_type: self._on_device_status_changed(dt, connected)
                )

    def _on_device_status_changed(self, device_type: DeviceType, connected: bool) -> None:
        """處理設備狀態變更"""
        new_status = DeviceStatus.CONNECTED if connected else DeviceStatus.DISCONNECTED
        self._update_device_status(device_type, new_status)

        if not connected:
            self._device_info_cache.pop(device_type, None)
            self._ongoing_operations.pop(device_type, None)

    def _cache_device_info(self, device_type: DeviceType) -> None:
        """緩存設備信息 - 純新架構"""
        try:
            device_instance = self._device_instances[device_type]

            if device_instance and device_instance.is_connected:
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

    def refresh_all_device_status(self) -> None:
        """刷新所有設備狀態 - 純新架構"""
        for device_type, device_instance in self._device_instances.items():
            try:
                if device_instance:
                    connected = device_instance.is_connected
                    new_status = DeviceStatus.CONNECTED if connected else DeviceStatus.DISCONNECTED
                    self._update_device_status(device_type, new_status)

                    if connected:
                        self._cache_device_info(device_type)

            except Exception as e:
                self._logger.warning(f"Failed to refresh status for {device_type.value}: {e}")
                self._update_device_status(device_type, DeviceStatus.ERROR)

    # ==================== 輔助方法（保持不變）====================

    def _validate_connection_request(self, device_type: DeviceType) -> DeviceConnectionResult:
        """驗證連接請求的業務規則"""
        current_status = self._device_statuses[device_type]
        if current_status == DeviceStatus.CONNECTED:
            return DeviceConnectionResult(False, f"設備 {device_type.value} 已經連接", "ALREADY_CONNECTED")

        if device_type in self._ongoing_operations:
            ongoing_op = self._ongoing_operations[device_type]
            return DeviceConnectionResult(False, f"設備 {device_type.value} 正在執行 {ongoing_op}", "DEVICE_BUSY")

        return DeviceConnectionResult(True, "連接請求驗證通過")

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

    def _setup_validation_rules(self) -> None:
        """設置業務驗證規則"""
        self.add_validation_rule(
            "device_type",
            lambda x: x in [dt for dt in DeviceType],
            "無效的設備類型"
        )

    def _check_test_execution_prerequisites(self, device_type: DeviceType) -> bool:
        """檢查測試執行的前置條件"""
        return True

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

            self.log_operation("device_business_model_stopped", True, "純新架構設備業務模型已停止")

        except Exception as e:
            self._logger.error(f"Error stopping device business model: {e}")


# ==================== 工廠方法 ====================

class DeviceBusinessModelFactory:
    """設備業務模型工廠"""

    @staticmethod
    def create_model() -> DeviceBusinessModel:
        """創建純新架構的設備業務模型實例"""
        return DeviceBusinessModel()