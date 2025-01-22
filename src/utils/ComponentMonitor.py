from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ComponentMonitor(QThread):
    """
    組件監控器基類
    """
    status_changed = Signal(str, bool)  # (組件名稱, 狀態)

    def __init__(self, component_name, check_func, interval=1000):
        super().__init__()
        self.component_name = component_name
        self.check_func = check_func
        self.interval = interval
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                status = self.check_func()
                self.status_changed.emit(self.component_name, status)
            except Exception as e:
                print(f"Error checking {self.component_name} status: {e}")
            self.msleep(self.interval)

    def stop(self):
        self.is_running = False
        self.wait()
