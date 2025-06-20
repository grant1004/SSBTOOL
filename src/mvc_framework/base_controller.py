# src/mvc_framework/base_controller.py
# MVC 框架基礎 Controller 類
# 提供通用的控制器功能

import inspect
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal, Slot
import logging
import asyncio
from .metaclass_utils import QObjectABCMeta


class BaseController(QObject, metaclass=QObjectABCMeta):
    """控制器基類"""

    # 通用信號
    operation_started = Signal(str)  # (operation_name)
    operation_completed = Signal(str, bool)  # (operation_name, success)

    def __init__(self):
        super().__init__()
        self._models = {}
        self._device_views = []
        self._logger = logging.getLogger(self.__class__.__name__)
        self._operation_queue = []
        self._is_processing = False

    def register_model(self, name: str, model: QObject) -> None:
        """註冊模型"""
        self._models[name] = model
        # 連接模型的通用信號
        if hasattr(model, 'data_changed'):
            model.data_changed.connect(self._on_model_data_changed)
        if hasattr(model, 'error_occurred'):
            model.error_occurred.connect(self._on_model_error)

    def register_view(self, view: QObject) -> None:
        """註冊視圖"""
        if view not in self._device_views:
            self._device_views.append(view)
            self._connect_view_signals(view)

    def unregister_view(self, view: QObject) -> None:
        """取消註冊視圖"""
        if view in self._device_views:
            self._device_views.remove(view)

    def get_model(self, name: str) -> Optional[QObject]:
        """獲取模型"""
        return self._models.get(name)

    def notify_views(self, method_name: str, *args, **kwargs) -> None:
        """通知所有視圖"""
        for view in self._device_views:
            if hasattr(view, method_name):
                try:
                    method = getattr(view, method_name)
                    method(*args, **kwargs)
                except Exception as e:
                    self._logger.error(f"View notification failed for {method_name}: {e}")

    async def execute_operation(self, operation_name: str, operation_func: Callable, *args, **kwargs) -> Any:
        """執行操作並管理狀態"""
        self.operation_started.emit(operation_name)
        self._logger.info(f"Starting operation: {operation_name}")

        try:
            if asyncio.iscoroutinefunction(operation_func):
                result = await operation_func(*args, **kwargs)
            else:
                result = operation_func(*args, **kwargs)

            self.operation_completed.emit(operation_name, True)
            self._logger.info(f"Operation completed successfully: {operation_name}")
            return result

        except Exception as e:
            self.operation_completed.emit(operation_name, False)
            self._logger.error(f"Operation failed: {operation_name}, Error: {e}")
            self._handle_operation_error(operation_name, e)
            raise

    def queue_operation(self, operation_func: Callable, *args, **kwargs) -> None:
        """將操作加入隊列"""
        self._operation_queue.append((operation_func, args, kwargs))
        if not self._is_processing:
            asyncio.create_task(self._process_operation_queue())

    async def _process_operation_queue(self) -> None:
        """處理操作隊列"""
        self._is_processing = True
        try:
            while self._operation_queue:
                operation_func, args, kwargs = self._operation_queue.pop(0)
                await self.execute_operation(operation_func.__name__, operation_func, *args, **kwargs)
        finally:
            self._is_processing = False

    def validate_prerequisites(self, prerequisites: Dict[str, Callable[[], bool]]) -> List[str]:
        """驗證前置條件"""
        errors = []
        for name, check_func in prerequisites.items():
            try:
                if not check_func():
                    errors.append(f"前置條件未滿足: {name}")
            except Exception as e:
                errors.append(f"前置條件檢查失敗: {name} - {e}")
        return errors

    def _connect_view_signals(self, view: QObject) -> None:
        """連接視圖信號 - 子類可覆蓋"""
        pass

    def _on_model_data_changed(self, data_type: str, data: Any) -> None:
        """處理模型數據變更 - 子類可覆蓋"""
        pass

    def _on_model_error(self, error_code: str, error_message: str) -> None:
        """處理模型錯誤 - 子類可覆蓋"""
        self.notify_views('show_error_message', error_message)


    def _handle_operation_error(self, operation_name: str, error: Exception) -> None:
        """處理操作錯誤 - 子類可覆蓋"""
        self.notify_views('show_error_message', f"操作失敗: {operation_name}")

    @Slot(str, object)
    def handle_user_action(self, action_name: str, action_data: Any = None):
        """
        處理來自視圖的用戶操作 - 通用路由機制
        路由到子類實現的具體接口方法
        """
        self._logger.info(f"Routing user action: {action_name}")

        # 🔑 關鍵：路由到接口定義的方法，而不是在這裡實現具體邏輯
        handler_map = self._get_action_handler_map()

        handler = handler_map.get(action_name)
        if handler:
            sig = inspect.signature(handler)
            params = list(sig.parameters.values())

            # 移除 self 參數
            if params and params[0].name == 'self':
                params = params[1:]
                # 準備調用參數
            call_kwargs = self._prepare_call_arguments(params, action_data)
            try:
                # 如果是異步方法，使用 asyncio 處理
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(**call_kwargs))
                else:
                    handler(**call_kwargs)
            except Exception as e:
                self._logger.error(f"Error handling action {action_name}: {e}")
                self._handle_action_error(action_name, e)
        else:
            self._logger.warning(f"No handler found for action: {action_name}")

    def _get_action_handler_map(self) -> Dict[str, callable]:
        """
        獲取操作處理器映射 - 子類需要重寫此方法
        將用戶操作映射到接口定義的具體方法
        """
        return {}

    def _handle_action_error(self, action_name: str, error: Exception):
        """處理操作執行錯誤 - 子類可以重寫"""
        self._logger.error(f"Action {action_name} failed: {error}")

    def _prepare_call_arguments(self, params: list, action_data: Any) -> Dict[str, Any]:
        """
        根據方法參數準備調用參數

        Args:
            params: 方法參數列表
            action_data: 動作數據

        Returns:
            準備好的關鍵字參數字典
        """
        call_kwargs = {}

        for param in params:
            param_name = param.name
            param_type = param.annotation
            has_default = param.default is not inspect.Parameter.empty

            # 策略 1: 如果 action_data 是字典且包含參數名
            if isinstance(action_data, dict) and param_name in action_data:
                call_kwargs[param_name] = action_data[param_name]
                continue

            # 策略 2: 特殊參數名處理
            if param_name in ['action_data', 'data', 'payload']:
                call_kwargs[param_name] = action_data
                continue

            # 策略 3: 根據參數名稱匹配 action_data 的屬性
            if hasattr(action_data, param_name):
                call_kwargs[param_name] = getattr(action_data, param_name)
                continue


            # 策略 5: 如果只有一個參數，直接傳遞 action_data
            if len(params) == 1:
                call_kwargs[param_name] = action_data
                continue

            # 策略 6: 使用默認值
            if has_default:
                # 有默認值的參數不需要傳遞
                continue

            # 策略 7: 最後手段，傳遞 None 或 action_data
            call_kwargs[param_name] = action_data

        return call_kwargs