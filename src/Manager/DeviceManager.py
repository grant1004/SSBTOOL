import asyncio
import time
from typing import Dict, Union, Optional

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer, QEventLoop
from PySide6.QtCore import QThread
from enum import Enum
from src.device import USBDevice, LoaderDevice, PowerDevice


class DeviceType(Enum):
    USB = "USB"
    LOADER = "LOADER"
    POWER = "POWER"

class DeviceNotConnectedError(Exception):
    """當嘗試操作未連接的設備時拋出的自定義異常"""
    pass

class ConnectionError(Exception):
    """設備連接失敗時拋出的自定義異常"""
    pass

class DeviceMonitorWorker(QObject):
    device_status_changed = Signal(DeviceType, bool)
    device_error_occurred = Signal(DeviceType, str)

    def __init__(self, device: Union[USBDevice, LoaderDevice, PowerDevice], device_type: DeviceType):
        super().__init__()
        self._device = device
        self._device_type = device_type
        self._last_status = device.is_connected
        self._is_monitoring = False
        self._monitor_loop = None  # Add a reference to the monitoring loop
        # print(f"DeviceMonitorWorker initialized for {device_type.name}")
        # print(f"Initial device status: {self._last_status}")

    def start_monitoring(self):
        """
        Explicitly start monitoring method
        """
        print(f"Start monitoring {self._device_type.name} device in thread" )
        self._is_monitoring = True
        self._monitor_loop = QTimer()
        self._monitor_loop.timeout.connect(self._check_device_status)
        self._monitor_loop.start(1000)  # Check every 1000 ms (1 second)

        # Initial status check
        initial_status = self._device.is_connected
        self.device_status_changed.emit(self._device_type, initial_status)

    def stop_monitoring(self):
        """
        Explicitly stop monitoring method
        """
        if self._monitor_loop:
            self._monitor_loop.stop()
        self._is_monitoring = False

    def _check_device_status(self):
        """
        Periodic status check method
        """
        try:
            current_status = self._device.is_connected
            print(f"Monitor >>> Device {self._device_type.name} status: {current_status}")

            # Only emit if status changed
            if current_status != self._last_status:
                self.device_status_changed.emit(self._device_type, current_status)
                self._last_status = current_status

        except Exception as e:
            print(f"Device monitoring error: {e}")
            self.device_error_occurred.emit(self._device_type, str(e))
            self.stop_monitoring()


class DeviceManagerWorker(QObject):
    """
    DeviceManager 工作器，負責管理系統中的不同設備連接、狀態監控和通訊

    主要職責:
    1. 管理不同類型設備的連接和斷開
    2. 監控設備的即時狀態
    3. 提供設備狀態變更和錯誤通知的信號

    支持的設備類型:
    - USB
    - loader
    - power
    """

    # 狀態和錯誤信號
    status_changed = Signal(str, bool)  # 設備狀態變更信號
    error_occurred = Signal(str, str)  # 設備錯誤信號

    def __init__(self):
        """
        初始化 DeviceManagerWorker

        """
        super().__init__()

        # 初始化具體設備實例
        self._usb = USBDevice()
        self._loader = LoaderDevice()
        self._power = PowerDevice()

        # 設備連接狀態映射
        self._device_status: Dict[DeviceType, bool] = {
            DeviceType.USB: False,
            DeviceType.LOADER: False,
            DeviceType.POWER: False
        }

        # 設備監控線程
        self._monitor_threads: Dict[DeviceType, QThread] = {}


    def _get_device(self, device_type: DeviceType) -> Union[USBDevice, LoaderDevice, PowerDevice]:
        """
        根據設備類型獲取對應的設備實例

        Args:
            device_type (DeviceType): 設備類型

        Returns:
            設備實例（USBDevice, LoaderDevice 或 PowerDevice）

        Raises:
            ValueError: 如果提供了無效的設備類型
        """
        device_map = {
            DeviceType.USB: self._usb,
            DeviceType.LOADER: self._loader,
            DeviceType.POWER: self._power
        }

        if device_type not in device_map:
            raise ValueError(f"Invalid device type: {device_type}")

        return device_map[device_type]

    async def connect_device(self, device_type: DeviceType) -> None:
        """
        連接指定類型的設備

        此方法負責：
        1. 嘗試連接指定類型的設備
        2. 啟動設備狀態監控線程
        3. 更新設備連接狀態
        4. 發出狀態變更信號

        Args:
            device_type (DeviceType): 要連接的設備類型

        Raises:
            ConnectionError: 設備連接失敗時拋出
            ValueError: 傳入無效的設備類型
        """
        device = self._get_device(device_type)
        # print( f"Click {device} Connect button")
        try:
            # 嘗試連接設備
            connection_result = await device.connect()

            if connection_result:
                # 更新設備狀態
                # print(f"Connected {device_type.name} device")
                self._device_status[device_type] = True

                # 啟動狀態監控線程
                self._start_device_monitoring(device_type)

                # 發出狀態變更信號
                self.status_changed.emit(device_type.name, True)

            else:
                raise ConnectionError(f"Failed to connect {device_type.name} device")

        except Exception as e:
            self.error_occurred.emit(device_type.name, str(e))
            raise

    def disconnect_device(self, device_type: DeviceType) -> None:
        """
        斷開指定類型的設備連接

        此方法負責：
        1. 停止設備監控線程
        2. 斷開設備連接
        3. 更新設備連接狀態
        4. 發出狀態變更信號

        Args:
            device_type (DeviceType): 要斷開的設備類型

        Raises:
            DeviceNotConnectedError: 當嘗試斷開未連接的設備
            ValueError: 傳入無效的設備類型
        """
        if not self._device_status.get(device_type, False):
            raise DeviceNotConnectedError(f"{device_type.name} device is not connected")

        device = self._get_device(device_type)

        try:
            # 停止監控線程
            self._stop_device_monitoring(device_type)

            # 斷開設備連接
            disconnect_result = device.disconnect()

            if disconnect_result:
                # 更新設備狀態
                self._device_status[device_type] = False

                # 發出狀態變更信號
                self.status_changed.emit(device_type.name, False)

            else:
                raise ConnectionError(f"Failed to disconnect {device_type.name} device")

        except Exception as e:
            # 記錄錯誤並拋出
            self.error_occurred.emit(device_type.name, str(e))
            raise

    def _create_device_monitor_thread(self, device_type: DeviceType) -> QThread:
        # print(f"Creating monitor thread for {device_type.name}")

        device = self._get_device(device_type)
        monitor_worker = DeviceMonitorWorker(
            device=device,
            device_type=device_type
        )

        thread = QThread()
        monitor_worker.moveToThread(thread)

        # 直接在这里调用 start_monitoring
        def call_start_monitoring():
            print(f"[DEBUG] Explicitly calling start_monitoring in thread for {device_type.name}")
            monitor_worker.start_monitoring()

        # 确保在线程启动时调用 start_monitoring
        thread.started.connect(call_start_monitoring)

        # 连接状态变化和错误信号
        monitor_worker.device_status_changed.connect(self._on_device_status_changed)
        monitor_worker.device_error_occurred.connect(self._on_device_error)

        # 确保停止和清理
        thread.finished.connect(monitor_worker.stop_monitoring)
        thread.finished.connect(monitor_worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        return thread

    def _start_device_monitoring(self, device_type: DeviceType) -> None:
        """
        為指定設備類型啟動監控線程

        Args:
            device_type (DeviceType): 要監控的設備類型

        Raises:
            ValueError: 如果設備類型已有正在運行的監控線程
        """
        # print( f"Start monitoring {device_type.name} device")
        # 檢查是否已存在該設備類型的監控線程

        if device_type in self._monitor_threads:
            # 如果線程已存在且正在運行，拋出異常
            if self._monitor_threads[device_type].isRunning():
                raise ValueError(f"Monitoring thread for {device_type.name} is already running")

        # print(f"Attempting to start monitoring {device_type.name} device")

        thread = self._create_device_monitor_thread(device_type)
        # print(f"Thread created for {device_type.name}")

        self._monitor_threads[device_type] = thread

        try:
            thread.start()
            # print(f"Thread started for {device_type.name}")
        except Exception as e:
            print(f"Failed to start thread for {device_type.name}: {e}")
            raise

    def _stop_device_monitoring(self, device_type: DeviceType) -> None:
        """
        停止指定設備類型的監控線程

        Args:
            device_type (DeviceType): 要停止監控的設備類型

        Raises:
            ValueError: 如果該設備類型沒有運行中的監控線程
        """
        print(f"Stop monitoring {device_type.name} device")
        if device_type not in self._monitor_threads:
            raise ValueError(f"No monitoring thread found for {device_type.name}")

        thread = self._monitor_threads[device_type]

        try:
            if thread.isRunning():
                # 請求線程停止
                thread.quit()

                # 等待線程結束（設置超時時間，避免永久等待）
                if not thread.wait(3000):  # 等待最多 3 秒
                    thread.terminate()  # 如果等待超時，強制終止
                    thread.wait()  # 確保線程完全停止

            # 從監控線程字典中移除
            del self._monitor_threads[device_type]

        except Exception as e:
            self.error_occurred.emit(device_type.name, f"Error stopping monitoring thread: {str(e)}")
            raise

    def get_device_status(self, device_type: Optional[DeviceType] = None) -> Union[Dict[DeviceType, bool], bool]:
        """
        獲取設備連接狀態

        Args:
            device_type (Optional[DeviceType], optional):
                如果提供，返回特定設備的連接狀態；
                如果為 None，返回所有設備的連接狀態。

        Returns:
            如果提供 device_type，返回該設備的連接狀態（bool）；
            如果未提供 device_type，返回所有設備的連接狀態（Dict）

        Raises:
            ValueError: 如果提供了無效的設備類型
        """
        if device_type is None:
            return self._device_status.copy()

        if device_type not in self._device_status:
            raise ValueError(f"Invalid device type: {device_type}")

        return self._device_status[device_type]

    def _on_device_status_changed(self, device_type, status:bool):
        print(f"Device {device_type.name} status changed to {status}")
        if status is False :
            # self._stop_device_monitoring(device_type)
            self.disconnect_device(device_type)

        self.status_changed.emit(device_type.name, status)

    def _on_device_error(self, device_type, error_msg:str):
        print(f"Device {device_type.name} error: {error_msg}")
        self.error_occurred.emit(device_type.name, error_msg)

    def stop(self) -> None:
        """
        停止所有設備連接，清理所有資源

        此方法執行以下操作：
        1. 斷開所有已連接的設備
        2. 停止所有監控線程
        3. 重置所有設備狀態
        4. 清理相關資源

        使用場景：
        - 應用程式退出時
        - 緊急停止所有設備
        - 重置系統狀態
        """
        try:
            # 停止並斷開所有已連接的設備
            for device_type in list(self._device_status.keys()):
                try:
                    # 如果設備已連接，則斷開連接
                    if self._device_status[device_type]:
                        self.disconnect_device(device_type)
                except Exception as e:
                    # 記錄單個設備斷開連接時的錯誤，但不阻止其他設備的處理
                    print(f"Error stopping device {device_type.name}: {str(e)}")

            # 停止所有監控線程
            for device_type, thread in list(self._monitor_threads.items()):
                try:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait()  # 等待線程完全停止
                except Exception as e:
                    print(f"Error stopping monitor thread for {device_type.name}: {str(e)}")

            # 清空監控線程字典
            self._monitor_threads.clear()

            # 重置設備狀態
            for device_type in self._device_status:
                self._device_status[device_type] = False

            # 可能的額外清理邏輯（如果需要）
            self._usb.cleanup()
            self._loader.cleanup()
            self._power.cleanup()


        except Exception as e:
            # 捕獲並記錄任何未預期的全局錯誤
            self.error_occurred.emit("SYSTEM", f"Failed to stop all devices: {str(e)}")
            raise

class DeviceManagerThread(QThread):
    def __init__(self):
        super().__init__()
        self.worker = DeviceManagerWorker()
        self.worker.moveToThread(self)

    def run(self):
        """線程運行"""
        # 可以在這裡執行初始化操作
        self.exec()  # 啟動事件循環

    def stop(self):
        """停止線程"""
        self.worker.stop()
        self.quit()  # 退出線程的事件循環
        self.wait()  # 等待線程結束

class DeviceManager:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if DeviceManager._instance is not None:
            raise Exception("DeviceManager is a singleton and It's already initialized!")

        self.thread = DeviceManagerThread()
        self.worker = self.thread.worker
        self.thread.start()

    async def connect_device(self, device_type: DeviceType):
        """
        調用連線方法
        """
        await self.worker.connect_device(device_type)

    def register_status_callback(self, callback):
        self.worker.status_changed.connect(callback)

    def register_error_callback(self, callback):
        self.worker.error_occurred.connect(callback)