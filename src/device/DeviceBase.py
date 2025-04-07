from abc import ABC, abstractmethod
from typing import Optional
import os, logging
from datetime import datetime
from src.utils import MessageListener
from typing import Callable


class DeviceBase(ABC):
    """設備基類，新增監聽機制"""

    def __init__(self):
        self._connected = False
        self._listener = None
        self._listener_callbacks = []

        # 設置記錄目錄
        self._log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(self._log_dir, exist_ok=True)

        # 基本日誌記錄器
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(logging.INFO)

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
        """清理資源"""
        pass

    @abstractmethod
    def receive_data(self) -> bytes:
        """接收設備數據

        這個方法必須由子類實現，用於從設備接收數據

        Returns:
            bytes: 接收到的數據，如果沒有數據則返回None
        """
        pass

    def start_listening(self, callback: Callable = None) -> bool:
        """開始監聽設備訊息

        Args:
            callback: 接收到訊息時的回調函數

        Returns:
            bool: 是否成功啟動監聽
        """
        if not self._connected:
            self._logger.error("Cannot start listening: device not connected")
            return False

        if self._listener and self._listener.is_alive():
            self._logger.warning("Listener already running")
            return True

        try:
            # 生成日誌文件名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            device_name = self.__class__.__name__
            log_file = os.path.join(self._log_dir, f"{device_name}_{timestamp}.txt")

            # 如果提供了回調，添加到回調列表
            if callback:
                self._listener_callbacks.append(callback)

            # 創建並啟動監聽器
            self._listener = MessageListener(
                device_id=f"{device_name}",
                receive_func=self.receive_data,
                log_file=log_file,
                callback=self._handle_message
            )
            self._listener.start()

            self._logger.info(f"Started listening to {device_name}, log file: {log_file}")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start listener: {e}")
            return False

    def stop_listening(self) -> bool:
        """停止監聽設備訊息

        Returns:
            bool: 是否成功停止監聽
        """
        if not self._listener:
            return True

        try:
            self._listener.stop()
            self._listener = None
            self._logger.info("Stopped listening")
            return True
        except Exception as e:
            self._logger.error(f"Failed to stop listener: {e}")
            return False

    def _handle_message(self, message: bytes):
        """處理接收到的訊息

        這個方法會調用所有註冊的回調函數

        Args:
            message: 接收到的訊息
        """
        for callback in self._listener_callbacks:
            try:
                callback(message)
            except Exception as e:
                self._logger.error(f"Error in message callback: {e}")

    def register_message_callback(self, callback: Callable) -> None:
        """註冊訊息回調函數

        Args:
            callback: 接收到訊息時的回調函數
        """
        if callback not in self._listener_callbacks:
            self._listener_callbacks.append(callback)

    def unregister_message_callback(self, callback: Callable) -> None:
        """解除註冊訊息回調函數

        Args:
            callback: 要解除的回調函數
        """
        if callback in self._listener_callbacks:
            self._listener_callbacks.remove(callback)

    def get_recent_messages(self, count: int = 10) -> list:
        """獲取最近的訊息

        Args:
            count: 要獲取的訊息數量

        Returns:
            list: 訊息列表
        """
        if not self._listener:
            return []

        return self._listener.get_messages(count)

    def is_listening(self) -> bool:
        """檢查是否正在監聽

        Returns:
            bool: 是否正在監聽
        """
        return self._listener is not None and self._listener.is_alive()

    @property
    def status(self) -> str:
        """取得設備狀態"""
        status_str = "connected" if self._connected else "disconnected"
        if self.is_listening():
            status_str += "_listening"
        return status_str

    @property
    def is_connected(self) -> bool:
        """檢查是否連接"""
        return self._connected