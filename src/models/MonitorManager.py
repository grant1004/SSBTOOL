from src.utils import ComponentMonitor, get_icon_path



class MonitorManager:
    """
    監控器管理類
    """

    def __init__(self, controller):
        self.controller = controller
        self.monitors = {}
        self._setup_monitors()

    def _setup_monitors(self):
        # 配置各個監控器
        monitor_configs = {
            "USB": {
                "func": self.controller.check_usb_status,
                "interval": 1000  # 1秒
            },
            "Power": {
                "func": self.controller.check_power_status,
                "interval": 2000  # 2秒
            },
            "Loader": {
                "func": self.controller.check_loader_status,
                "interval": 1500  # 1.5秒
            }
        }

        # 創建監控器
        for name, config in monitor_configs.items():
            monitor = ComponentMonitor(
                name,
                config["func"],
                config["interval"]
            )
            self.monitors[name] = monitor

    def start_all(self):
        """啟動所有監控器"""
        for monitor in self.monitors.values():
            monitor.start()

    def stop_all(self):
        """停止所有監控器"""
        for monitor in self.monitors.values():
            monitor.stop()

    def get_monitor(self, component_name):
        """獲取指定監控器"""
        return self.monitors.get(component_name)