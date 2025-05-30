# src/core/device/Loader_device.py
from src.device import DeviceBase
from typing import Optional


class LoaderDevice(DeviceBase):
    def __init__(self):
        super().__init__()

    async def connect(self, port: str = "COM19") -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    def send_command(self, cmd: bytes) -> bool:
        if not self._connected:
            raise ConnectionError("Device not connected")
        return True

    def receive_data(self) -> bytes:
        pass

    def cleanup(self) -> bool:
        """清空"""
        pass

    @property
    def status(self) -> str:
        return "connected" if self._connected else "disconnected"