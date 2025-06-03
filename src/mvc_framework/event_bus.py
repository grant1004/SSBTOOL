# src/mvc_framework/event_bus.py
"""
事件總線 - 用於組件間鬆耦合通信
"""

from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal
import logging


class EventBus(QObject):
    """事件總線單例"""

    _instance = None

    # 全局事件信號
    event_published = Signal(str, object)  # (event_name, event_data)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._subscribers: Dict[str, List[Callable]] = {}
            self._logger = logging.getLogger(self.__class__.__name__)
            self._initialized = True

    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """訂閱事件"""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
            self._logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """取消訂閱事件"""
        if event_name in self._subscribers:
            if callback in self._subscribers[event_name]:
                self._subscribers[event_name].remove(callback)
                self._logger.debug(f"Unsubscribed from event: {event_name}")

                # 如果沒有訂閱者了，移除事件
                if not self._subscribers[event_name]:
                    del self._subscribers[event_name]

    def publish(self, event_name: str, event_data: Any = None) -> None:
        """發布事件"""
        self._logger.debug(f"Publishing event: {event_name}")

        # 發出 Qt 信號
        self.event_published.emit(event_name, event_data)

        # 通知直接訂閱者
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name].copy():  # 複製列表避免修改問題
                try:
                    callback(event_data)
                except Exception as e:
                    self._logger.error(f"Event callback failed for {event_name}: {e}")

    def get_subscribers_count(self, event_name: str) -> int:
        """獲取事件訂閱者數量"""
        return len(self._subscribers.get(event_name, []))

    def get_all_events(self) -> List[str]:
        """獲取所有事件名稱"""
        return list(self._subscribers.keys())

    def clear_all_subscriptions(self) -> None:
        """清除所有訂閱"""
        self._subscribers.clear()
        self._logger.info("All event subscriptions cleared")


# 全局事件總線實例
event_bus = EventBus()