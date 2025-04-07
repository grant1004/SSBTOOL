import usb.core
import usb.util
import asyncio
from src.device import DeviceBase
import logging
import src.CanFrame as CanFrame



class USBDevice(DeviceBase):

    def __init__(self):
        super().__init__()
        self.device = None
        self.ep_out = None
        self.ep_in = None
        self.interface = None
        self._logger = logging.getLogger(__name__)
        self.vendor_id = 0x5458  # 替換為您的設備 vendor ID
        self.product_id = 0x1222  # 替換為您的設備 product ID

    async def connect(self, port: str = None) -> bool:
        """連接 USB 設備

        Args:
            port: 不使用，保留參數僅為相容性

        Returns:
            bool: 連接是否成功
        """
        try:
            # 尋找設備
            self.device = usb.core.find(
                idVendor=self.vendor_id,
                idProduct=self.product_id
            )

            if self.device is None:
                self._logger.error(f'Device not found (VID=0x{self.vendor_id:04X}, PID=0x{self.product_id:04X})')
                return False

            # 設置配置
            self.device.set_configuration()

            # 獲取接口
            cfg = self.device.get_active_configuration()
            self.interface = cfg[(1, 0)]  # 使用第一個接口

            # 找到輸出端點
            self.ep_out = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )

            # 找到輸入端點
            self.ep_in = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )

            if not all([self.ep_out, self.ep_in]):
                self._logger.error('Could not find endpoints')
                return False

            self._connected = True
            self._logger.info('USB device connected successfully')
            return True

        except Exception as e:
            self._logger.error(f'Failed to connect: {str(e)}')
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """斷開 USB 設備連接"""
        try:
            if self.device:
                usb.util.dispose_resources(self.device)

            self.device = None
            self.ep_out = None
            self.ep_in = None
            self.interface = None
            self._connected = False
            self._logger.info('USB device disconnected')

        except Exception as e:
            self._logger.error(f'Error during disconnect: {str(e)}')

    def send_command(self, command: bytes, get: bool = False ) -> bool:
        """發送命令到 USB 設備

        Args:
            command: 要發送的命令（bytes格式）

        Returns:
            bool: 發送是否成功
        """
        if not self._connected:
            raise ConnectionError("Device not connected")

        try:
            bytes_written = self.ep_out.write(command)
            self._logger.debug(f'Sent {bytes_written} bytes: {command.hex(" ").upper()}')
            return True

        except Exception as e:
            self._logger.error(f'Error sending command: {str(e)}')
            self._connected = False
            return False

    def cleanup(self) -> bool:
        """清理資源"""
        try:
            asyncio.get_event_loop().run_until_complete(self.disconnect())
            return True
        except Exception as e:
            self._logger.error(f'Error during cleanup: {str(e)}')
            return False

    @property
    def status(self) -> str:
        """獲取設備狀態"""
        try:
            if self.device and self._connected:
                # 嘗試獲取設備狀態
                cfg = self.device.get_active_configuration()
                return "connected"
        except:
            pass
        return "disconnected"

    @property
    def is_connected(self) -> bool:
        """檢查設備是否已連接"""
        try:
            if not self.device or not self._connected:
                return False

            # 直接檢查設備是否還在系統中
            device = usb.core.find(
                idVendor=self.vendor_id,
                idProduct=self.product_id
            )

            if device is None:
                self._connected = False
                self.device = None
                return False

            return True

        except Exception as e:
            self._logger.error(f"Error checking USB connection: {str(e)}")
            self._connected = False
            self.device = None
            return False

    def receive_data(self):
        """簡單讀取USB設備資料

        Args:
            timeout: 讀取超時時間（毫秒）
            max_size: 一次讀取的最大字節數

        Returns:
            bytes: 接收到的資料，如果沒有資料則返回空bytes
        """
        timeout: int = 1000
        if not self._connected:
            raise ConnectionError("Device not connected")

        try:
            # 直接嘗試讀取資料
            data_dlc = 25
            data = self.ep_in.read( data_dlc, timeout)

            if data:
                data_bytes = bytes(data)
                parse_data = CanFrame.Parser.parse(data_bytes)
                return parse_data

            return b""

        except usb.core.USBError as e:
            # 忽略超時錯誤，這是正常的
            if e.errno == 110:  # 操作超時
                return b""
            else:
                self._logger.error(f'接收資料時發生錯誤: {str(e)}')
                return b""
        except Exception as e:
            self._logger.error(f'接收資料時發生未知錯誤: {str(e)}')
            return b""

