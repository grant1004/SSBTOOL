# src/controllers/device_controller.py

import asyncio
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal

# 導入接口
from src.interfaces.device_interface import (
    IDeviceController, IDeviceView, DeviceType, DeviceStatus,
    DeviceConnectionResult, DeviceStatusChangedEvent, DeviceErrorEvent
)

# 導入 MVC 基類
from src.mvc_framework.base_controller import BaseController
from src.mvc_framework.event_bus import event_bus

# 導入業務模型
from src.business_models.device_business_model import DeviceBusinessModel


class DeviceController(BaseController, IDeviceController):
    """
    設備控制器 - 協調設備業務邏輯和 UI 交互

    職責：
    1. 協調設備連接/斷開的複雜流程
    2. 管理多個 View 的狀態同步
    3. 處理跨組件的設備狀態通信
    4. 管理設備操作的前置條件檢查
    5. 協調錯誤處理和用戶反饋
    """

    # 控制器級別信號
    device_operation_progress = Signal(DeviceType, str, int)  # device_type, operation, progress
    all_devices_status_changed = Signal(dict)  # {device_type: status}

    def __init__(self, device_model: DeviceBusinessModel):
        super().__init__()

        # 註冊業務模型
        self.register_model("device_business", device_model)
        self.device_model = device_model

        # View 管理
        self._device_views: List[IDeviceView] = []

        # 協調狀態管理
        self._connection_states: Dict[DeviceType, str] = {}  # "idle", "connecting", "connected", "error"
        self._pending_operations: Dict[DeviceType, str] = {}
        self._view_states: Dict[object, Dict[str, Any]] = {}

        # 配置協調策略
        self._auto_refresh_enabled = True
        self._batch_update_enabled = True
        self._error_recovery_enabled = True

        # 連接業務模型事件
        self._connect_business_model_signals()

        # 設置定期狀態同步
        self._setup_periodic_sync()

        self._logger.info("DeviceController initialized with coordination capabilities")

    # ==================== IDeviceController 接口實現 ====================

    def register_view(self, view: IDeviceView) -> None:
        """註冊設備視圖"""
        if view not in self._device_views:
            self._device_views.append(view)
            self._view_states[view] = {}

            # 為新視圖同步當前狀態
            self._sync_view_with_current_state(view)

            self._logger.info(f"Registered device view: {type(view).__name__}")

    def unregister_view(self, view: IDeviceView) -> None:
        """取消註冊設備視圖"""
        if view in self._device_views:
            self._device_views.remove(view)
            self._view_states.pop(view, None)
            self._logger.info(f"Unregistered device view: {type(view).__name__}")

    async def handle_connect_request(self, device_type: DeviceType) -> None:
        """
        處理設備連接請求 - 完整的協調邏輯

        協調流程：
        1. 前置條件檢查和用戶確認
        2. 協調多個 View 的狀態更新
        3. 執行業務邏輯
        4. 處理結果和錯誤
        5. 跨組件狀態同步
        """
        operation_name = f"connect_{device_type.value}"

        try:
            # 階段 1: 前置條件檢查
            validation_errors = await self._validate_connect_prerequisites(device_type)
            if validation_errors:
                await self._handle_validation_errors(device_type, validation_errors)
                return

            # 階段 2: 用戶確認（如果需要）
            # if not await self._get_user_confirmation_if_needed(device_type, "connect"):
            #     return

            # 階段 3: 協調 UI 狀態 - 開始連接
            await self._coordinate_connection_start(device_type)

            # 階段 4: 執行業務邏輯
            result = await self.execute_operation(
                operation_name,
                self.device_model.connect_device,
                device_type
            )

            # 階段 5: 協調結果處理
            # await self._coordinate_connection_result(device_type, result)

            # 階段 6: 跨組件事件發布
            event_bus.publish("device_connected", {
                'device_type': device_type,
                'success': result.success,
                'message': result.message
            })

        except Exception as e:
            await self._handle_operation_exception(device_type, "connect", e)

    async def handle_disconnect_request(self, device_type: DeviceType) -> None:
        """處理設備斷開請求"""
        operation_name = f"disconnect_{device_type.value}"

        try:
            # 檢查是否有依賴此設備的操作
            dependent_operations = await self._check_device_dependencies(device_type)
            if dependent_operations:
                user_confirmed = await self._confirm_disconnect_with_dependencies(device_type, dependent_operations)
                if not user_confirmed:
                    return

            # 協調斷開流程
            await self._coordinate_disconnection_start(device_type)

            result = await self.execute_operation(
                operation_name,
                self.device_model.disconnect_device,
                device_type
            )

            await self._coordinate_disconnection_result(device_type, result)

            # 發布跨組件事件
            event_bus.publish("device_disconnected", {
                'device_type': device_type,
                'success': result.success
            })

        except Exception as e:
            await self._handle_operation_exception(device_type, "disconnect", e)

    def handle_status_query(self, device_type: Optional[DeviceType] = None) -> Dict[DeviceType, DeviceStatus]:
        """處理狀態查詢請求"""
        if device_type is None:
            return self.device_model.get_all_device_status()
        else:
            status = self.device_model.get_device_status(device_type)
            return {device_type: status}

    def handle_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """處理設備錯誤"""
        self._logger.error(f"Device error for {device_type.value}: {error_message}")

        # 協調錯誤處理
        self._coordinate_error_handling(device_type, error_message)

        # 如果啟用錯誤恢復，嘗試自動恢復
        if self._error_recovery_enabled:
            asyncio.create_task(self._attempt_error_recovery(device_type, error_message))

    def refresh_device_status(self) -> None:
        """刷新所有設備狀態"""
        self._logger.info("Refreshing all device status")
        self.device_model.refresh_all_device_status()
        # 協調 UI 更新
        self._coordinate_status_refresh()

    def set_device_configuration(self, device_type: DeviceType, config: Dict[str, Any]) -> bool:
        """設置設備配置"""
        try:
            # 驗證配置
            validation_errors = self._validate_device_config(device_type, config)
            if validation_errors:
                self._notify_views_batch('show_device_error', device_type,
                                         f"配置驗證失敗: {'; '.join(validation_errors)}")
                return False

            # 應用配置（這裡可能需要擴展業務模型）
            self._logger.info(f"Setting configuration for {device_type.value}: {config}")

            return True

        except Exception as e:
            self._logger.error(f"Error setting device configuration: {e}")
            return False

    # ==================== 協調邏輯實現 ====================

    async def _validate_connect_prerequisites(self, device_type: DeviceType) -> List[str]:
        """驗證連接前置條件"""
        errors = []

        # 業務模型驗證
        business_errors = self.device_model.validate_data({
            'device_type': device_type,
            'action': 'connect'
        })
        errors.extend(business_errors)

        # 系統級驗證
        if self._is_system_busy():
            errors.append("系統忙碌中，請稍後再試")

        # 設備特定驗證
        device_specific_errors = await self._check_device_specific_prerequisites(device_type)
        errors.extend(device_specific_errors)

        return errors

    async def _coordinate_connection_start(self, device_type: DeviceType) -> None:
        """協調連接開始的 UI 狀態"""
        self._connection_states[device_type] = "connecting"
        self._pending_operations[device_type] = "connect"

        # 協調所有視圖顯示連接中狀態
        self._notify_views_batch('show_connection_progress', device_type, 0)
        self._notify_views_batch('disable_device_controls', device_type)

        # 更新其他相關控制項
        self._coordinate_related_controls_during_operation(device_type, "connect")

    async def _coordinate_connection_result(self, device_type: DeviceType, result: DeviceConnectionResult) -> None:
        """協調連接結果的處理"""
        self._pending_operations.pop(device_type, None)

        if result.success:
            self._connection_states[device_type] = "connected"
            self._notify_views_batch('show_connection_success', device_type)
            self._notify_views_batch('update_device_status', device_type, DeviceStatus.CONNECTED)

            # 啟用相關功能
            self._enable_device_dependent_features(device_type)

        else:
            self._connection_states[device_type] = "error"
            self._notify_views_batch('show_connection_error', device_type, result.message)
            self._notify_views_batch('update_device_status', device_type, DeviceStatus.ERROR)

        # 重新啟用控制項
        self._notify_views_batch('enable_device_controls', device_type)

        # 協調整體狀態更新
        self._coordinate_overall_status_update()

    def _coordinate_error_handling(self, device_type: DeviceType, error_message: str) -> None:
        """協調錯誤處理"""
        self._connection_states[device_type] = "error"

        # 通知所有視圖
        self._notify_views_batch('show_device_error', device_type, error_message)
        self._notify_views_batch('update_device_status', device_type, DeviceStatus.ERROR)

        # 禁用依賴此設備的功能
        self._disable_device_dependent_features(device_type)

        # 發布錯誤事件
        event_bus.publish("device_error", {
            'device_type': device_type,
            'error_message': error_message,
            'timestamp': asyncio.get_event_loop().time()
        })

    def _notify_views_batch(self, method_name: str, *args, **kwargs) -> None:
        """批量通知所有視圖"""
        if self._batch_update_enabled:
            # 使用延遲更新避免 UI 頻繁刷新
            self.defer_batch_update(lambda: self.notify_views(method_name, *args, **kwargs))
        else:
            self.notify_views(method_name, *args, **kwargs)

    def defer_batch_update(self, update_func):
        """延遲批量更新"""
        # 這裡可以實現批量更新邏輯，避免 UI 頻繁刷新
        # 暫時直接執行
        update_func()

    # ==================== 業務模型事件處理 ====================

    def _connect_business_model_signals(self) -> None:
        """連接業務模型信號"""
        self.device_model.device_status_changed.connect(self._on_device_status_changed)
        self.device_model.device_connection_progress.connect(self._on_connection_progress)
        self.device_model.device_error_occurred.connect(self._on_device_error)
        self.device_model.device_operation_completed.connect(self._on_operation_completed)

    def _on_device_status_changed(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """處理設備狀態變更"""
        self._logger.info(f"Device status changed: {device_type.value} -> {status.value}")

        # 協調所有視圖更新
        self._notify_views_batch('update_device_status', device_type, status)

        # 協調相關功能的啟用/禁用
        if status == DeviceStatus.CONNECTED:
            self._enable_device_dependent_features(device_type)
        else:
            self._disable_device_dependent_features(device_type)

        # 發布跨組件事件
        event_bus.publish("device_status_changed", DeviceStatusChangedEvent(
            device_type, self._connection_states.get(device_type, DeviceStatus.ERROR), status.value
        ))

        # 更新整體狀態
        self._coordinate_overall_status_update()

    def _on_connection_progress(self, device_type: DeviceType, progress: int) -> None:
        """處理連接進度更新"""
        self._notify_views_batch('show_connection_progress', device_type, progress)
        self.device_operation_progress.emit(device_type, "connect", progress)

    def _on_device_error(self, device_type: DeviceType, error_code: str, error_message: str) -> None:
        """處理設備錯誤"""
        self._coordinate_error_handling(device_type, error_message)

    def _on_operation_completed(self, device_type: DeviceType, operation: str, success: bool) -> None:
        """處理操作完成"""
        self._logger.info(
            f"Operation completed: {operation} on {device_type.value} -> {'Success' if success else 'Failed'}")

        # 清理操作狀態
        self._pending_operations.pop(device_type, None)

        # 發布操作完成事件
        event_bus.publish("device_operation_completed", {
            'device_type': device_type,
            'operation': operation,
            'success': success
        })

    # ==================== 輔助方法 ====================

    def _sync_view_with_current_state(self, view: IDeviceView) -> None:
        """為新視圖同步當前狀態"""
        all_status = self.device_model.get_all_device_status()
        for device_type, status in all_status.items():
            view.update_device_status(device_type, status)
            # 同步設備信息
            device_info = self.device_model.get_device_info(device_type)
            if device_info:
                view.update_device_info(device_type, device_info)

    def _coordinate_overall_status_update(self) -> None:
        """協調整體狀態更新"""
        all_status = self.device_model.get_all_device_status()

        # 發布整體狀態變更
        self.all_devices_status_changed.emit(all_status)

        # 協調依賴檢查
        self._update_feature_availability_based_on_devices()

    def _enable_device_dependent_features(self, device_type: DeviceType) -> None:
        """啟用依賴此設備的功能"""
        # 發布事件讓其他組件知道可以啟用相關功能
        event_bus.publish("device_features_available", {
            'device_type': device_type,
            'available': True
        })

    def _disable_device_dependent_features(self, device_type: DeviceType) -> None:
        """禁用依賴此設備的功能"""
        event_bus.publish("device_features_available", {
            'device_type': device_type,
            'available': False
        })

    def _update_feature_availability_based_on_devices(self) -> None:
        """根據設備狀態更新功能可用性"""
        stats = self.device_model.get_connection_statistics()

        # 發布整體可用性狀態
        event_bus.publish("system_readiness_changed", {
            'devices_ready': stats['connected_devices'] > 0,
            'all_devices_ready': stats['connected_devices'] == stats['total_devices'],
            'statistics': stats
        })

    async def _handle_validation_errors(self, device_type: DeviceType, errors: List[str]) -> None:
        """處理驗證錯誤"""
        error_message = f"無法連接 {device_type.value}:\n" + "\n".join(errors)
        self._notify_views_batch('show_connection_error', device_type, error_message)

    async def _check_device_dependencies(self, device_type: DeviceType) -> List[str]:
        """檢查設備依賴"""
        # 檢查是否有其他功能依賴此設備
        dependencies = []

        if self._is_test_running() and device_type in [DeviceType.USB, DeviceType.POWER]:
            dependencies.append("正在執行的測試")

        return dependencies

    async def _confirm_disconnect_with_dependencies(self, device_type: DeviceType, dependencies: List[str]) -> bool:
        """確認帶有依賴的斷開操作"""
        message = f"斷開 {device_type.value} 將影響以下功能:\n" + "\n".join(dependencies) + "\n\n確定要繼續嗎？"

        for view in self._device_views:
            if hasattr(view, 'request_user_confirmation'):
                return view.request_user_confirmation(message)

        return False

    def _is_system_busy(self) -> bool:
        """檢查系統是否忙碌"""
        return len(self._pending_operations) > 2  # 最多允許2個並發操作

    def _is_test_running(self) -> bool:
        """檢查是否有測試在運行"""
        # 這裡可以通過事件總線查詢測試執行狀態
        # 暫時返回 False
        return False

    async def _check_device_specific_prerequisites(self, device_type: DeviceType) -> List[str]:
        """檢查設備特定前置條件"""
        errors = []

        if device_type == DeviceType.USB:
            # USB 特定檢查
            pass
        elif device_type == DeviceType.POWER:
            # 電源特定檢查
            pass

        return errors

    def _validate_device_config(self, device_type: DeviceType, config: Dict[str, Any]) -> List[str]:
        """驗證設備配置"""
        errors = []

        # 基本驗證
        if not config:
            errors.append("配置不能為空")

        return errors

    async def _attempt_error_recovery(self, device_type: DeviceType, error_message: str) -> None:
        """嘗試錯誤恢復"""
        self._logger.info(f"Attempting error recovery for {device_type.value}")

        try:
            # 等待一段時間後重試連接
            await asyncio.sleep(5)

            if self.device_model.get_device_status(device_type) == DeviceStatus.ERROR:
                self._logger.info(f"Retrying connection for {device_type.value}")
                await self.handle_connect_request(device_type)

        except Exception as e:
            self._logger.error(f"Error recovery failed for {device_type.value}: {e}")

    async def _coordinate_disconnection_start(self, device_type: DeviceType) -> None:
        """協調斷開開始"""
        self._connection_states[device_type] = "disconnecting"
        self._pending_operations[device_type] = "disconnect"
        self._notify_views_batch('disable_device_controls', device_type)

    async def _coordinate_disconnection_result(self, device_type: DeviceType, result: DeviceConnectionResult) -> None:
        """協調斷開結果"""
        self._pending_operations.pop(device_type, None)

        if result.success:
            self._connection_states[device_type] = "disconnected"
            self._notify_views_batch('update_device_status', device_type, DeviceStatus.DISCONNECTED)
        else:
            self._notify_views_batch('show_device_error', device_type, result.message)

        self._notify_views_batch('enable_device_controls', device_type)
        self._coordinate_overall_status_update()

    def _coordinate_related_controls_during_operation(self, device_type: DeviceType, operation: str) -> None:
        """協調操作期間的相關控制項"""
        # 禁用可能衝突的操作
        if operation == "connect":
            # 連接期間禁用測試執行
            event_bus.publish("device_operation_in_progress", {
                'device_type': device_type,
                'operation': operation,
                'block_operations': ['test_execution']
            })

    def _coordinate_status_refresh(self) -> None:
        """協調狀態刷新"""
        self._notify_views_batch('show_loading_state', True)

        # 延遲後停止載入狀態
        asyncio.get_event_loop().call_later(2.0,
                                            lambda: self._notify_views_batch('show_loading_state', False))

    async def _handle_operation_exception(self, device_type: DeviceType, operation: str, exception: Exception) -> None:
        """處理操作異常"""
        error_message = f"{operation} 操作失敗: {str(exception)}"
        self._logger.error(error_message)

        # 清理狀態
        self._pending_operations.pop(device_type, None)
        self._connection_states[device_type] = "error"

        # 通知視圖
        self._notify_views_batch('show_device_error', device_type, error_message)
        self._notify_views_batch('enable_device_controls', device_type)

    def _setup_periodic_sync(self) -> None:
        """設置定期狀態同步"""
        if self._auto_refresh_enabled:
            # 每30秒同步一次狀態
            def periodic_refresh():
                if not self.device_model.is_any_device_busy():
                    self.refresh_device_status()

                # 設置下次調用
                asyncio.get_event_loop().call_later(30.0, periodic_refresh)

            # 延遲10秒後開始第一次同步
            asyncio.get_event_loop().call_later(10.0, periodic_refresh)

    # ==================== 配置方法 ====================

    def set_auto_refresh(self, enabled: bool) -> None:
        """設置自動刷新"""
        self._auto_refresh_enabled = enabled

    def set_batch_update(self, enabled: bool) -> None:
        """設置批量更新"""
        self._batch_update_enabled = enabled

    def set_error_recovery(self, enabled: bool) -> None:
        """設置錯誤恢復"""
        self._error_recovery_enabled = enabled

    # ==================== 狀態查詢方法 ====================

    def get_coordination_state(self) -> Dict[str, Any]:
        """獲取協調狀態"""
        return {
            'connection_states': self._connection_states.copy(),
            'pending_operations': self._pending_operations.copy(),
            'registered_views': len(self._device_views),
            'auto_refresh_enabled': self._auto_refresh_enabled,
            'batch_update_enabled': self._batch_update_enabled,
            'error_recovery_enabled': self._error_recovery_enabled
        }

    def get_system_health(self) -> Dict[str, Any]:
        """獲取系統健康狀態"""
        device_stats = self.device_model.get_connection_statistics()

        return {
            'device_statistics': device_stats,
            'pending_operations_count': len(self._pending_operations),
            'error_devices': [dt for dt, state in self._connection_states.items() if state == "error"],
            'system_busy': self._is_system_busy(),
            'all_devices_ready': device_stats['connected_devices'] == device_stats['total_devices']
        }