# controllers/window_controller.py
class TopWidgetController:
    def __init__(self, main_window):
        self.main_window = main_window

    def minimize_window(self):
        """最小化視窗"""
        self.main_window.showMinimized()

    def toggle_maximize(self):
        """切換視窗最大化狀態"""
        if self.main_window.isMaximized():
            self.main_window.showNormal()
        else:
            self.main_window.showMaximized()

    def close_window(self):
        """關閉視窗"""
        self.main_window.close()