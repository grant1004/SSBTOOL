from abc import ABC, abstractmethod
from typing import Optional


class DeviceBase(ABC):
    def __init__(self):
        self._connected = False

    @abstractmethod
    async def connect(self, port: str) -> bool:
        """連接設備"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """斷開連接"""
        pass

    @abstractmethod
    def send_command(self, cmd: bytes) -> bool:
        """發送命令"""
        pass

    @abstractmethod
    def cleanup(self) -> bool:
        """清空"""
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        """取得設備狀態"""
        pass

    @property
    def is_connected(self) -> bool:
        """檢查是否連接"""
        return self._connected