# src/mvc_framework/base_model.py
"""
MVC 框架基礎 Model 類
提供通用的業務模型功能
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Any, Dict, Optional
from PySide6.QtCore import QObject, Signal
import logging
from .metaclass_utils import QObjectABCMeta


class BaseBusinessModel(QObject, metaclass=QObjectABCMeta):
    """業務模型基類"""

    # 通用信號
    data_changed = Signal(str, object)  # (data_type, data)
    error_occurred = Signal(str, str)  # (error_code, error_message)
    operation_started = Signal(str)  # (operation_name)
    operation_completed = Signal(str, bool)  # (operation_name, success)

    def __init__(self):
        super().__init__()
        self._observers = []
        self._logger = logging.getLogger(self.__class__.__name__)
        self._operation_cache = {}
        self._validation_rules = {}

    def register_observer(self, observer: Callable[[str, Any], None]) -> None:
        """註冊觀察者"""
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister_observer(self, observer: Callable[[str, Any], None]) -> None:
        """取消註冊觀察者"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, event_type: str, data: Any = None) -> None:
        """通知所有觀察者"""
        for observer in self._observers:
            try:
                observer(event_type, data)
            except Exception as e:
                self._logger.error(f"Observer notification failed: {e}")

    def add_validation_rule(self, field: str, rule: Callable[[Any], bool], error_message: str) -> None:
        """添加驗證規則"""
        if field not in self._validation_rules:
            self._validation_rules[field] = []
        self._validation_rules[field].append((rule, error_message))

    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """驗證數據，返回錯誤信息列表"""
        errors = []
        for field, value in data.items():
            if field in self._validation_rules:
                for rule, error_message in self._validation_rules[field]:
                    if not rule(value):
                        errors.append(f"{field}: {error_message}")
        return errors

    def cache_operation_result(self, operation_key: str, result: Any, ttl: int = 300) -> None:
        """緩存操作結果"""
        import time
        self._operation_cache[operation_key] = {
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl
        }

    def get_cached_result(self, operation_key: str) -> Optional[Any]:
        """獲取緩存的操作結果"""
        import time
        if operation_key in self._operation_cache:
            cached = self._operation_cache[operation_key]
            if time.time() - cached['timestamp'] < cached['ttl']:
                return cached['result']
            else:
                del self._operation_cache[operation_key]
        return None

    def clear_cache(self) -> None:
        """清除所有緩存"""
        self._operation_cache.clear()

    def log_operation(self, operation_name: str, success: bool, details: str = "") -> None:
        """記錄操作日誌"""
        level = logging.INFO if success else logging.ERROR
        message = f"Operation '{operation_name}' {'succeeded' if success else 'failed'}"
        if details:
            message += f": {details}"
        self._logger.log(level, message)









