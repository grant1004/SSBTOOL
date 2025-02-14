class ProgressListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, signal):
        self.signal = signal
        self.current_test = None
        self.current_keyword = None

    def start_test(self, name, attrs):
        self.current_test = name
        message = {
            "type": "test_start",
            "data": {
                "test_name": name,
                "status": "RUNNING"
            }
        }
        self.signal.emit(str(message))

    def end_test(self, name, attrs):
        status = "PASS" if attrs['status'] == 'PASS' else "FAIL"
        message = {
            "type": "test_end",
            "data": {
                "test_name": name,
                "status": status,
                "message": attrs.get('message', '')  # 包含錯誤信息
            }
        }
        self.signal.emit(str(message))

    def start_keyword(self, name, attrs):
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
            self.signal.emit(str(message))

    def end_keyword(self, name, attrs):
        if attrs.get('type', '') == 'KEYWORD':
            status = attrs['status']
            message = {
                "type": "keyword_end",
                "data": {
                    "test_name": self.current_test,
                    "keyword_name": name,
                    "status": status,
                    "message": attrs.get('message', '')  # 包含錯誤信息
                }
            }
            self.signal.emit(str(message))

    def log_message(self, message):
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
            self.signal.emit(str(message))