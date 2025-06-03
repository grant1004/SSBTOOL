# src/mvc_framework/base_controller.py
"""
MVC 框架基礎 Controller 類
提供通用的控制器功能
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal
import logging
import asyncio
from .metaclass_utils import QObjectABCMeta


class BaseController(QObject, metaclass=QObjectABCMeta):
    """控制器基類"""

    # 通用信號
    operation_started = Signal(str)  # (operation_name)
    operation_completed = Signal(str, bool)  # (operation_name, success)
    state_changed = Signal(str, object)  # (state_name, state_value)

    def __init__(self):
        super().__init__()
        self._models = {}
        self._views = []
        self._state = {}
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
        if view not in self._views:
            self._views.append(view)
            self._connect_view_signals(view)

    def unregister_view(self, view: QObject) -> None:
        """取消註冊視圖"""
        if view in self._views:
            self._views.remove(view)

    def get_model(self, name: str) -> Optional[QObject]:
        """獲取模型"""
        return self._models.get(name)

    def get_state(self, key: str) -> Any:
        """獲取狀態"""
        return self._state.get(key)

    def set_state(self, key: str, value: Any) -> None:
        """設置狀態"""
        old_value = self._state.get(key)
        self._state[key] = value
        if old_value != value:
            self.state_changed.emit(key, value)
            self._on_state_changed(key, old_value, value)

    def notify_views(self, method_name: str, *args, **kwargs) -> None:
        """通知所有視圖"""
        for view in self._views:
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

    def _on_state_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """處理狀態變更 - 子類可覆蓋"""
        pass

    def _handle_operation_error(self, operation_name: str, error: Exception) -> None:
        """處理操作錯誤 - 子類可覆蓋"""
        self.notify_views('show_error_message', f"操作失敗: {operation_name}")
