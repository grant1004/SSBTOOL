from PySide6.QtCore import QMetaObject, Qt, Q_ARG
import threading
import time


class ProgressListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, signal):
        self.signal = signal
        self.current_test = None
        self.current_keyword = None
        self._lock = threading.Lock()  # 新增：線程安全鎖

    def start_test(self, name, attrs):
        """測試案例開始時的處理"""
        with self._lock:
            self.current_test = name
            message = {
                "type": "test_start",
                "data": {
                    "test_name": name,
                    "status": "RUNNING"
                }
            }
            # print(f"[LISTENER] Test Start: {name}")  # 新增：調試信息
            self._emit_message(message)

    def end_test(self, name, attrs):
        """測試案例結束時的處理"""
        with self._lock:
            status = "PASS" if attrs['status'] == 'PASS' else "FAIL"
            message = {
                "type": "test_end",
                "data": {
                    "test_name": name,
                    "status": status,
                    "message": attrs.get('message', '')
                }
            }
            # print(f"[LISTENER] Test End: {name} - {status}")  # 新增：調試信息
            self._emit_message(message)

    def start_keyword(self, name, attrs):
        """關鍵字開始時的處理"""
        # print(f"[LISTENER] Keyword Start Called: {name}, Type: {attrs.get('type', 'UNKNOWN')}")  # 新增：調試信息

        # 改進：更寬鬆的條件檢查
        if attrs.get('type', '') in ['KEYWORD', 'LIBRARY']:  # 擴展支持的類型
            with self._lock:
                self.current_keyword = name
                message = {
                    "type": "keyword_start",
                    "data": {
                        "test_name": self.current_test,
                        "keyword_name": name,
                        "status": "RUNNING"
                    }
                }
                # print(f"[LISTENER] Emitting Keyword Start: {name}")  # 新增：調試信息
                self._emit_message(message)

    def end_keyword(self, name, attrs):
        """關鍵字結束時的處理"""
        # print(f"[LISTENER] Keyword End Called: {name}, Type: {attrs.get('type', 'UNKNOWN')}")  # 新增：調試信息

        if attrs.get('type', '') in ['KEYWORD', 'LIBRARY']:  # 擴展支持的類型
            with self._lock:
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
                # print(f"[LISTENER] Emitting Keyword End: {name} - {status}")  # 新增：調試信息
                self._emit_message(message)

    def log_message(self, message):
        """記錄訊息的處理"""
        level = message['level']
        if level in ('ERROR', 'FAIL'):
            with self._lock:
                message_data = {
                    "type": "log",
                    "data": {
                        "test_name": self.current_test,
                        "keyword_name": self.current_keyword,
                        "level": level,
                        "message": message['message']
                    }
                }
                self._emit_message(message_data)

    """
    def _emit_message(self, message: dict):
        try:
            # 新增：重試機制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 直接使用 signal 的 emit 方法
                    self.signal.emit(message)
                    print(f"[LISTENER] Message emitted successfully: {message['type']}")
                    break
                except Exception as e:
                    print(f"[LISTENER] Emit attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(0.01)  # 短暫延遲後重試

        except Exception as e:
            print(f"[LISTENER] Critical error emitting message: {e}")
            print(f"[LISTENER] Message content: {message}")
            # 不再拋出異常，避免中斷測試執行
    """

    def _emit_message(self, message: dict):
        try:
            print( "="*100 + f"\n[LISTENER] 🔥 Emitting: {message['type']} - {message}")
            self.signal.emit(message)
            print(f"[LISTENER] ✅ Emit successful\n" + "="*100)
        except Exception as e:
            print(f"[LISTENER] ❌ Emit failed: {e}")