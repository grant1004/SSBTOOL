from PySide6.QtCore import QMetaObject, Qt, Q_ARG


class ProgressListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, signal):
        self.signal = signal
        self.current_test = None
        self.current_keyword = None


    def start_test(self, name, attrs):
        """測試案例開始時的處理"""
        self.current_test = name
        message = {
            "type": "test_start",
            "data": {
                "test_name": name,
                "status": "RUNNING"
            }
        }
        self._emit_message(message)

    def end_test(self, name, attrs):
        """測試案例結束時的處理"""
        status = "PASS" if attrs['status'] == 'PASS' else "FAIL"
        message = {
            "type": "test_end",
            "data": {
                "test_name": name,
                "status": status,
                "message": attrs.get('message', '')
            }
        }
        self._emit_message(message)

    def start_keyword(self, name, attrs):
        """關鍵字開始時的處理"""
        if attrs.get('type', '') == 'KEYWORD':
            self.current_keyword = name
            message = {
                "type": "keyword_start",
                "data": {
                    "test_name": self.current_test,
                    "keyword_name": name,
                    "status": "RUNNING"
                }
            }
            # print( message )
            self._emit_message(message)

    def end_keyword(self, name, attrs):
        """關鍵字結束時的處理"""
        if attrs.get('type', '') == 'KEYWORD':
            status = attrs['status']
            message = {
                "type": "keyword_end",
                "data": {
                    "test_name": self.current_test,
                    "keyword_name": name,
                    "status": status,
                    "message": attrs.get('message', '')
                }
            }
            self._emit_message(message)

    def log_message(self, message):
        """記錄訊息的處理"""
        level = message['level']
        if level in ('ERROR', 'FAIL'):
            message = {
                "type": "log",
                "data": {
                    "test_name": self.current_test,
                    "keyword_name": self.current_keyword,
                    "level": level,
                    "message": message['message']
                }
            }
            self._emit_message(message)

    def _emit_message(self, message:dict):
        """統一的消息發送處理"""
        try:
            # 直接使用 signal 的 emit 方法
            self.signal.emit(message)

            # 添加調試輸出
            # print(f"Emitting message: {message}")

        except Exception as e:
            print(f"Error emitting message: {e}")
