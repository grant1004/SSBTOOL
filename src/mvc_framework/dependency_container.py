# src/mvc_framework/dependency_container.py
"""
依賴注入容器
"""

from typing import Dict, Any, Callable, TypeVar, Type, Optional
import logging

T = TypeVar('T')


class DependencyContainer:
    """依賴注入容器"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def register_instance(self, name: str, instance: Any) -> None:
        """註冊實例"""
        self._services[name] = instance
        self._logger.debug(f"Registered instance: {name}")

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """註冊工廠方法"""
        self._factories[name] = factory
        self._logger.debug(f"Registered factory: {name}")

    def register_singleton(self, name: str, factory: Callable[[], Any]) -> None:
        """註冊單例工廠"""
        self._factories[name] = factory
        self._singletons[name] = None  # 標記為單例
        self._logger.debug(f"Registered singleton: {name}")

    def get(self, name: str) -> Optional[Any]:
        """獲取服務"""
        # 優先返回直接註冊的實例
        if name in self._services:
            return self._services[name]

        # 檢查是否有工廠方法
        if name in self._factories:
            # 如果是單例且已創建，返回現有實例
            if name in self._singletons:
                if self._singletons[name] is not None:
                    return self._singletons[name]

                # 創建單例實例
                instance = self._factories[name]()
                self._singletons[name] = instance
                return instance
            else:
                # 每次創建新實例
                return self._factories[name]()

        self._logger.warning(f"Service not found: {name}")
        return None

    def get_required(self, name: str) -> Any:
        """獲取必需的服務（找不到會拋異常）"""
        service = self.get(name)
        if service is None:
            raise ValueError(f"Required service not found: {name}")
        return service

    def has(self, name: str) -> bool:
        """檢查是否有指定服務"""
        return name in self._services or name in self._factories

    def remove(self, name: str) -> None:
        """移除服務"""
        if name in self._services:
            del self._services[name]
        if name in self._factories:
            del self._factories[name]
        if name in self._singletons:
            del self._singletons[name]
        self._logger.debug(f"Removed service: {name}")

    def clear(self) -> None:
        """清除所有服務"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        self._logger.info("All services cleared")

    def get_service_names(self) -> list:
        """獲取所有服務名稱"""
        return list(set(self._services.keys()) | set(self._factories.keys()))