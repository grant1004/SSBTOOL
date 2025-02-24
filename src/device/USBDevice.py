import usb.core
import usb.util
import asyncio
from src.device import DeviceBase
import logging



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

    def send_command(self, command: bytes) -> bool:
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

    # @property
    # def is_connected(self) -> bool:
    #     """檢查設備是否已連接"""
    #     try:
    #         if not self.device or not self._connected:
    #             return False
    #
    #         try:
    #             # 請求設備狀態
    #             self.device.ctrl_transfer(
    #                 bmRequestType=0x80,  # Device to Host
    #                 bRequest=0x00,  # GET_STATUS
    #                 wValue=0x0000,
    #                 wIndex=0x0000,
    #                 data_or_wLength=2
    #             )
    #             return True
    #
    #         except usb.core.USBError:
    #             self._connected = False
    #             self.device = None
    #             return False
    #
    #     except Exception as e:
    #         self._logger.error(f"Error checking USB connection: {str(e)}")
    #         self._connected = False
    #         self.device = None
    #         return False

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
