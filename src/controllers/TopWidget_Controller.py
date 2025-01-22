# controllers/window_controller.py
from src.models import MonitorManager
from src.utils import get_icon_path, ComponentMonitor


# controllers.py
class TopWidgetController:
    """控制器：處理用戶操作和業務邏輯"""

    def __init__(self, model, view):
        self.model = model
        self.view = view

        # 註冊模型的狀態改變回調
        self.model.register_callback(self._on_status_changed)

    def connect_usb(self):
        """處理 USB 連接請求"""
        return self.model.connect_device('USB')

    def connect_power(self):
        """處理 Power 連接請求"""
        return self.model.connect_device('Power')

    def connect_loader(self):
        """處理 Loader 連接請求"""
        return self.model.connect_device('Loader')

    def _on_status_changed(self, device_type, status):
        """處理設備狀態改變"""
        self.view.update_device_status(device_type, status)

    def start_monitoring(self):
        """啟動設備狀態監控"""
        for device in ['USB', 'Power', 'Loader']:
            self._start_device_monitor(device)

    def _start_device_monitor(self, device_type):
        """啟動單個設備的監控"""
        monitor = ComponentMonitor(
            device_type,
            lambda: self.model.get_status(device_type)
        )
        monitor.status_changed.connect(
            lambda status: self.model.set_status(device_type, status)
        )
        monitor.start()

