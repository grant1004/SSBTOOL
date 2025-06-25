# src/device/LoaderDevice.py
from src.device import DeviceBase
from typing import Optional, Union
from Lib.PEL500 import PEL500
import asyncio
import logging

logger = logging.getLogger(__name__)


class LoaderDevice(DeviceBase):
    """整合 PEL500 電子負載的 LoaderDevice 實作"""

    def __init__(self):
        super().__init__()
        self._pel500: Optional[PEL500] = None
        self._port: Optional[str] = None
        self._connected = False

    async def connect(self, port: str = "COM19") -> bool:
        """
        連接到電子負載設備

        Args:
            port: COM port (例如 'COM19')

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        try:
            # 如果已經連接，先斷開
            if self._connected:
                await self.disconnect()

            # 創建 PEL500 實例
            self._pel500 = PEL500(port=port, baudrate=115200)
            self._port = port

            # 測試連接 - 嘗試關閉負載以確保設備響應
            self._pel500.load_off()

            self._connected = True
            logger.info(f"成功連接到電子負載設備在端口: {port}")
            return True

        except Exception as e:
            logger.error(f"連接電子負載失敗: {str(e)}")
            self._connected = False
            self._pel500 = None
            return False

    async def disconnect(self) -> None:
        """斷開電子負載連接"""
        try:
            if self._pel500:
                # 關閉負載輸出
                await self._async_load_off()
                # 關閉串口連接
                self._pel500.close()
        except Exception as e:
            logger.error(f"斷開連接時發生錯誤: {str(e)}")
        finally:
            self._connected = False
            self._pel500 = None
            self._port = None

    def send_command(self, cmd: Union[str, bytes]) -> bool:
        """
        發送命令到設備

        Args:
            cmd: 命令字串或位元組

        Returns:
            bool: 發送成功返回 True
        """
        if not self._connected or not self._pel500:
            raise ConnectionError("Device not connected")

        try:
            if isinstance(cmd, bytes):
                cmd = cmd.decode()
            self._pel500.send_command(cmd)
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
        if not self._connected or not self._pel500:
            raise ConnectionError("Device not connected")

        try:
            # PEL500 的 send_command 已經處理了接收
            # 這裡可能需要單獨實作接收邏輯
            return self._pel500.ser.readline().decode().strip()
        except Exception as e:
            logger.error(f"接收數據失敗: {str(e)}")
            return None

    def cleanup(self) -> bool:
        """清理資源"""
        try:
            if self._pel500:
                self._pel500.close()
            return True
        except Exception as e:
            logger.error(f"清理資源失敗: {str(e)}")
            return False

    @property
    def status(self) -> str:
        """獲取設備狀態"""
        if self._connected and self._pel500:
            try:
                # 嘗試測量電壓來確認設備狀態
                voltage = self._pel500.measure_voltage()
                return f"connected (voltage: {voltage}V)" if voltage is not None else "connected"
            except:
                return "connected"
        return "disconnected"

    @property
    def is_connected(self) -> bool:
        """檢查設備是否已連接"""
        if self._pel500 and hasattr(self._pel500, 'ser'):
            return self._pel500.ser.is_open if self._pel500.ser else False
        return False

    # ===== 輔助方法 =====

    def _check_connection(self) -> bool:
        """檢查設備連接狀態"""
        if not self._connected or not self._pel500:
            logger.error("設備未連接")
            return False
        return True

    async def _async_load_off(self) -> None:
        """異步關閉負載輸出"""
        if self._pel500:
            await asyncio.get_event_loop().run_in_executor(
                None, self._pel500.load_off
            )

    # ===== 同步方法 (原有 PEL500 功能) =====

    def set_mode(self, mode: str) -> bool:
        """
        設置操作模式

        Args:
            mode: 'CC', 'CR', 'CV' 或 'CP'

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_mode(mode)
            return True
        except Exception as e:
            logger.error(f"設置模式失敗: {str(e)}")
            return False

    def set_current(self, current: float, level: str = "HIGH") -> bool:
        """
        設置CC模式下的電流

        Args:
            current: 電流值 (A)
            level: "HIGH" 或 "LOW"

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_current(current, level)
            return True
        except Exception as e:
            logger.error(f"設置電流失敗: {str(e)}")
            return False

    def set_resistance(self, resistance: float, level: str = "HIGH") -> bool:
        """
        設置CR模式下的阻抗

        Args:
            resistance: 阻抗值 (Ω)
            level: "HIGH" 或 "LOW"

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_resistance(resistance, level)
            return True
        except Exception as e:
            logger.error(f"設置阻抗失敗: {str(e)}")
            return False

    def set_voltage(self, voltage: float, level: str = "HIGH") -> bool:
        """
        設置CV模式下的電壓

        Args:
            voltage: 電壓值 (V)
            level: "HIGH" 或 "LOW"

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_voltage(voltage, level)
            return True
        except Exception as e:
            logger.error(f"設置電壓失敗: {str(e)}")
            return False

    def set_power(self, power: float, level: str = "HIGH") -> bool:
        """
        設置CP模式下的功率

        Args:
            power: 功率值 (W)
            level: "HIGH" 或 "LOW"

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_power(power, level)
            return True
        except Exception as e:
            logger.error(f"設置功率失敗: {str(e)}")
            return False

    def load_on(self) -> bool:
        """
        開啟負載

        Returns:
            bool: 開啟成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.load_on()
            return True
        except Exception as e:
            logger.error(f"開啟負載失敗: {str(e)}")
            return False

    def load_off(self) -> bool:
        """
        關閉負載

        Returns:
            bool: 關閉成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.load_off()
            return True
        except Exception as e:
            logger.error(f"關閉負載失敗: {str(e)}")
            return False

    def measure_voltage(self) -> Optional[float]:
        """
        測量電壓

        Returns:
            float: 測量的電壓值 (V)，失敗返回 None
        """
        if not self._check_connection():
            return None
        try:
            return self._pel500.measure_voltage()
        except Exception as e:
            logger.error(f"測量電壓失敗: {str(e)}")
            return None

    def measure_current(self) -> Optional[float]:
        """
        測量電流

        Returns:
            float: 測量的電流值 (A)，失敗返回 None
        """
        if not self._check_connection():
            return None
        try:
            return self._pel500.measure_current()
        except Exception as e:
            logger.error(f"測量電流失敗: {str(e)}")
            return None

    def measure_power(self) -> Optional[float]:
        """
        測量功率

        Returns:
            float: 測量的功率值 (W)，失敗返回 None
        """
        if not self._check_connection():
            return None
        try:
            return self._pel500.measure_power()
        except Exception as e:
            logger.error(f"測量功率失敗: {str(e)}")
            return None

    def set_dynamic_parameters(self, t_high: float, t_low: float,
                               rise_rate: float, fall_rate: float) -> bool:
        """
        設置動態模式參數

        Args:
            t_high: 高電平時間 (ms)
            t_low: 低電平時間 (ms)
            rise_rate: 電流上升速率 (A/μs)
            fall_rate: 電流下降速率 (A/μs)

        Returns:
            bool: 設置成功返回 True
        """
        if not self._check_connection():
            return False
        try:
            self._pel500.set_dynamic_parameters(t_high, t_low, rise_rate, fall_rate)
            return True
        except Exception as e:
            logger.error(f"設置動態參數失敗: {str(e)}")
            return False

    # ===== 擴展功能方法 =====

    def get_measurements(self) -> Optional[dict]:
        """
        獲取所有測量值

        Returns:
            dict: 包含電壓、電流、功率的字典，失敗返回 None
        """
        if not self._check_connection():
            return None
        try:
            return {
                'voltage': self.measure_voltage(),
                'current': self.measure_current(),
                'power': self.measure_power()
            }
        except Exception as e:
            logger.error(f"獲取測量值失敗: {str(e)}")
            return None

    def configure_load(self, mode: str, value: float, level: str = "HIGH") -> bool:
        """
        配置負載設定

        Args:
            mode: 操作模式 ('CC', 'CR', 'CV', 'CP')
            value: 設定值
            level: 設定層級 ("HIGH" 或 "LOW")

        Returns:
            bool: 配置成功返回 True
        """
        if not self._check_connection():
            return False

        try:
            # 設置模式
            if not self.set_mode(mode):
                return False

            # 根據模式設置對應的值
            if mode == 'CC':
                return self.set_current(value, level)
            elif mode == 'CR':
                return self.set_resistance(value, level)
            elif mode == 'CV':
                return self.set_voltage(value, level)
            elif mode == 'CP':
                return self.set_power(value, level)
            else:
                logger.error(f"不支援的模式: {mode}")
                return False

        except Exception as e:
            logger.error(f"配置負載失敗: {str(e)}")
            return False