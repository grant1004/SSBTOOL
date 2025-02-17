from src.device import DeviceBase
from typing import Optional
import serial_asyncio
import serial
from serial import SerialException
import asyncio
import logging
import ctypes


class USBDevice(DeviceBase):
    def __init__(self):
        super().__init__()
        self._port = None
        self._reader = None
        self._writer = None
        self._connected = False
        self._logger = logging.getLogger(__name__)
        self._connection_lost = False
        self._transport = None

    async def connect(self, port: str = "COM30") -> bool:
        try:
            if self._connected:
                return True

            self._port = port
            self._transport, protocol = await serial_asyncio.create_serial_connection(
                asyncio.get_event_loop(),
                lambda: SerialProtocol(self._handle_connection_lost),
                port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )

            self._reader, self._writer = protocol, self._transport
            self._connected = True
            self._connection_lost = False
            self._logger.info(f"Successfully connected to device on port {port}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to connect to device: {str(e)}")
            await self.disconnect()
            return False

    def _handle_connection_lost(self, exc=None):
        """
        處理連接丟失的內部方法
        """
        try:
            if exc:
                error_msg = str(exc)
                if isinstance(exc, SerialException) and "ClearCommError failed" in error_msg:
                    self._logger.warning("USB device disconnected: ClearCommError")
                else:
                    self._logger.error(f"Connection lost with error: {error_msg}")
            else:
                self._logger.warning("Connection lost detected")

            if self._connected:
                self._connection_lost = True
                self._connected = False
                asyncio.create_task(self._cleanup_after_disconnect())

        except Exception as e:
            self._logger.error(f"Error in connection lost handler: {str(e)}")

    async def _cleanup_after_disconnect(self):
        """
        在連接丟失後執行清理工作
        """
        try:
            if self._transport:
                try:
                    # 安全地關閉 transport
                    self._transport.abort()  # 使用 abort 而不是 close 來避免阻塞
                except Exception as e:
                    self._logger.debug(f"Transport abort error (expected): {str(e)}")

            self._reader = None
            self._writer = None
            self._transport = None

        except Exception as e:
            self._logger.error(f"Error during cleanup after disconnect: {str(e)}")
        finally:
            self._connected = False
            self._connection_lost = False

    def disconnect(self) -> bool:
        try:
            if not self._connected and not self._transport:
                return True

            if self._transport:
                try:
                    self._transport.abort()  # 使用 abort 來避免阻塞
                except Exception as e:
                    self._logger.debug(f"Transport abort error (expected): {str(e)}")

            self._reader = None
            self._writer = None
            self._transport = None
            self._connected = False
            self._connection_lost = False
            self._logger.info("Device disconnected")
            return True

        except Exception as e:
            self._logger.error(f"Error during disconnect: {str(e)}")
            return False

    async def send_command(self, cmd: str, data: Optional[bytes] = None) -> bool:
        if not self._connected or self._connection_lost:
            raise ConnectionError("Device not connected")

        try:
            command = cmd.encode('utf-8')
            if data:
                command += data

            self._writer.write(command)
            await self._writer.drain()

            self._logger.debug(f"Command sent: {cmd}")
            return True

        except SerialException as e:
            if "ClearCommError failed" in str(e):
                self._logger.warning("USB device disconnected during command send")
                self._handle_connection_lost(e)
            else:
                self._logger.error(f"Serial error during command send: {str(e)}")
                self._handle_connection_lost(e)
            return False

        except Exception as e:
            self._logger.error(f"Error sending command: {str(e)}")
            self._handle_connection_lost(e)
            return False

    def cleanup(self) -> bool:
        try:
            self.disconnect()
            self._port = None
            return True

        except Exception as e:
            self._logger.error(f"Error during cleanup: {str(e)}")
            return False

    @property
    def is_connected(self) -> bool:
        """
        取得當前連接狀態

        Returns:
            bool: 是否已連接
        """
        try:
            if self._transport and not self._connection_lost:
                # 嘗試檢查 serial port 狀態
                serial_instance = self._transport.serial
                if serial_instance and serial_instance.is_open:
                    return True
        except (SerialException, AttributeError, IOError) as e:
            self._logger.debug(f"Connection check error (expected): {str(e)}")
            return False
        except Exception as e:
            self._logger.error(f"Unexpected error in is_connected: {str(e)}")
            return False

        return False

    @property
    def status(self) -> str:
        """
        取得當前連接狀態字串

        Returns:
            str: 'connected' 或 'disconnected'
        """
        return "connected" if self.is_connected else "disconnected"


class SerialProtocol(asyncio.Protocol):
    def __init__(self, connection_lost_callback):
        self._connection_lost_callback = connection_lost_callback
        super().__init__()

    def connection_lost(self, exc):
        """
        當連接丟失時調用
        """
        if self._connection_lost_callback:
            self._connection_lost_callback(exc)  # 傳遞異常到回調