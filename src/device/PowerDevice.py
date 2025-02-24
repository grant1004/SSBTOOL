# src/core/device/PowerDevice.py
from src.device import DeviceBase
from typing import Optional


class PowerDevice(DeviceBase):
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



    def cleanup(self) -> bool:
        """清空"""
        pass
    @property
    def status(self) -> str:
        return "connected" if self._connected else "disconnected"