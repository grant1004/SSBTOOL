# src/device/PowerDevice.py
from src.device import DeviceBase
from typing import Optional, Union
from Lib.UDP6730 import UDP6730
import asyncio
import logging

logger = logging.getLogger(__name__)


class PowerDevice(DeviceBase):
    """整合 UDP6730 電源供應器的 PowerDevice 實作"""

    def __init__(self):
        super().__init__()
        self._udp6730: Optional[UDP6730] = None
        self._port: Optional[str] = None
        self._connected = False

    async def connect(self, port: str = "COM32") -> bool:
        """
        連接到電源供應器

        Args:
            port: COM port (例如 'COM32')

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        try:
            # 如果已經連接，先斷開
            if self._connected:
                await self.disconnect()

            # 創建 UDP6730 實例
            self._udp6730 = UDP6730()
            self._port = port

            # 測試連接
            idn = self.get_idn()
            if idn:
                self._connected = True
                logger.info(f"成功連接到電源供應器: {idn}")
                return True
            else:
                raise ConnectionError("無法獲取設備識別信息")

        except Exception as e:
            logger.error(f"連接電源供應器失敗: {str(e)}")
            self._connected = False
            self._udp6730 = None
            return False

    async def disconnect(self) -> None:
        """斷開電源供應器連接"""
        try:
            if self._udp6730:
                # 關閉輸出
                await self._async_output_off()
                # 關閉串口連接
                self._udp6730.close()
        except Exception as e:
            logger.error(f"斷開連接時發生錯誤: {str(e)}")
        finally:
            self._connected = False
            self._udp6730 = None
            self._port = None

    def send_command(self, cmd: Union[str, bytes]) -> bool:
        """
        發送命令到設備

        Args:
            cmd: 命令字串或位元組

        Returns:
            bool: 發送成功返回 True
        """
        if not self._connected or not self._udp6730:
            raise ConnectionError("Device not connected")

        try:
            if isinstance(cmd, bytes):
                cmd = cmd.decode()
            self._udp6730.send_command(cmd)
            return True
        except Exception as e:
            logger.error(f"發送命令失敗: {str(e)}")
            return False

    def receive_data(self) -> Optional[str]:
        """
        接收設備返回的數據

        Returns:
            str: 接收到的數據，如果失敗返回 None
        """
        if not self._connected or not self._udp6730:
            raise ConnectionError("Device not connected")

        try:
            # UDP6730 的 send_command 已經處理了接收
            # 這裡可能需要單獨實作接收邏輯
            return self._udp6730.ser.readline().decode().strip()
        except Exception as e:
            logger.error(f"接收數據失敗: {str(e)}")
            return None

    def cleanup(self) -> bool:
        """清理資源"""
        try:
            if self._udp6730:
                self._udp6730.close()
            return True
        except Exception as e:
            logger.error(f"清理資源失敗: {str(e)}")
            return False

    @property
    def status(self) -> str:
        """獲取設備狀態"""
        if self._connected and self._udp6730:
            try:
                output_state = self._udp6730.get_output_state()
                return f"connected (output: {'ON' if output_state else 'OFF'})"
            except:
                return "connected"
        return "disconnected"

    # ===== 同步方法 (原有 UDP6730 功能) =====

    def get_idn(self) -> Optional[str]:
        """獲取設備識別信息"""
        if not self._check_connection():
            return None
        return self._udp6730.get_idn()

    def set_voltage(self, voltage: float) -> bool:
        """
        設置輸出電壓

        Args:
            voltage: 電壓值 (V)

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._udp6730.set_voltage(voltage)
            return True
        except Exception as e:
            logger.error(f"設置電壓失敗: {str(e)}")
            return False

    def set_current(self, current: float) -> bool:
        """
        設置輸出電流

        Args:
            current: 電流值 (A)

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._udp6730.set_current(current)
            return True
        except Exception as e:
            logger.error(f"設置電流失敗: {str(e)}")
            return False

    def output_on(self) -> bool:
        """開啟電源輸出"""
        if not self._check_connection():
            return False
        try:
            self._udp6730.output_on()
            return True
        except Exception as e:
            logger.error(f"開啟輸出失敗: {str(e)}")
            return False

    def output_off(self) -> bool:
        """關閉電源輸出"""
        if not self._check_connection():
            return False
        try:
            self._udp6730.output_off()
            return True
        except Exception as e:
            logger.error(f"關閉輸出失敗: {str(e)}")
            return False

    def measure_voltage(self) -> Optional[float]:
        """測量當前電壓 (V)"""
        if not self._check_connection():
            return None
        return self._udp6730.measure_voltage()

    def measure_current(self) -> Optional[float]:
        """測量當前電流 (A)"""
        if not self._check_connection():
            return None
        return self._udp6730.measure_current()

    def measure_power(self) -> Optional[float]:
        """測量當前功率 (W)"""
        if not self._check_connection():
            return None
        return self._udp6730.measure_power()

    def get_voltage_setting(self) -> Optional[float]:
        """獲取電壓設定值 (V)"""
        if not self._check_connection():
            return None
        return self._udp6730.get_voltage_setting()

    def get_current_setting(self) -> Optional[float]:
        """獲取電流設定值 (A)"""
        if not self._check_connection():
            return None
        return self._udp6730.get_current_setting()

    def get_output_state(self) -> Optional[bool]:
        """獲取輸出狀態"""
        if not self._check_connection():
            return None
        return self._udp6730.get_output_state()

    # ===== 輔助方法 =====

    def _check_connection(self) -> bool:
        """檢查連接狀態"""
        if not self._connected or not self._udp6730:
            logger.error("設備未連接")
            return False
        return True

    def get_device_info(self) -> dict:
        """
        獲取設備詳細信息

        Returns:
            dict: 包含設備信息的字典
        """
        if not self._check_connection():
            return {
                "connected": False,
                "port": self._port,
                "status": "disconnected"
            }

        return {
            "connected": True,
            "port": self._port,
            "idn": self.get_idn(),
            "output_state": self.get_output_state(),
            "voltage_setting": self.get_voltage_setting(),
            "current_setting": self.get_current_setting(),
            "measured_voltage": self.measure_voltage(),
            "measured_current": self.measure_current(),
            "measured_power": self.measure_power()
        }


# 使用範例
# if __name__ == "__main__":
#     # device = UDP6730()
#
#     async def test_power_device():
#         device = PowerDevice()
#
#         # 連接設備
#         if await device.connect("COM32"):
#             print("設備連接成功")
#
#             # 獲取設備信息
#             print(f"設備 ID: {device.get_idn()}")
#
#             # 設置電壓和電流
#             device.set_voltage(5.0)  # 5V
#             device.set_current(1.0)  # 1A
#
#             # 開啟輸出
#             device.output_on()
#
#             # 測量值
#             print(f"電壓: {device.measure_voltage()} V")
#             print(f"電流: {device.measure_current()} A")
#             print(f"功率: {device.measure_power()} W")
#
#             # 關閉輸出
#             device.output_off()
#
#             # 斷開連接
#             await device.disconnect()
#         else:
#             print("設備連接失敗")
#
#
#     # # 執行測試
#     asyncio.run(test_power_device())