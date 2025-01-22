
# models.py
class TopWidget_Model:
    """設備連接的Model層：管理所有設備的狀態和連接邏輯"""

    def __init__(self):
        self.device_status = {
            'USB': False,
            'Power': False,
            'Loader': False
        }
        self.connection_callbacks = []

    def get_status(self, device_type):
        """獲取設備狀態"""
        return self.device_status.get(device_type, False)

    def set_status(self, device_type, status):
        """設置設備狀態"""
        if device_type in self.device_status:
            self.device_status[device_type] = status
            self._notify_status_change(device_type, status)

    def register_callback(self, callback):
        """註冊狀態改變的回調"""
        self.connection_callbacks.append(callback)

    def _notify_status_change(self, device_type, status):
        """通知所有觀察者狀態改變"""
        for callback in self.connection_callbacks:
            callback(device_type, status)

    def connect_device(self, device_type):
        """連接設備的具體邏輯"""
        if device_type == 'USB':
            success = self._connect_usb()
        elif device_type == 'Power':
            success = self._connect_power()
        elif device_type == 'Loader':
            success = self._connect_loader()
        else:
            return False

        if success:
            self.set_status(device_type, True)
        return success

    def _connect_usb(self):
        # USB 連接的具體實現
        return True

    def _connect_power(self):
        # Power 連接的具體實現
        return True

    def _connect_loader(self):
        # Loader 連接的具體實現
        return True
