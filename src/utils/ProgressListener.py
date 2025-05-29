from PySide6.QtCore import QMetaObject, Qt, Q_ARG
import threading
import time


class ProgressListener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, signal, keyword_mapping=None):
        self.signal = signal
        self.current_test = None
        self.current_keyword = None
        self._lock = threading.Lock()
        self.keyword_mapping = keyword_mapping or {}  # **新增映射**

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
        """關鍵字開始時的處理 - 支援映射轉換"""
        if attrs.get('type', '') in ['KEYWORD', 'LIBRARY']:
            with self._lock:
                self.current_keyword = name

                # **新增：檢查是否為生成的 testcase keyword**
                original_info = self._resolve_keyword_name(name)

                message = {
                    "type": "keyword_start",
                    "data": {
                        "test_name": self.current_test,
                        "keyword_name": original_info['display_name'], # **使用轉換後的名稱**
                        "original_keyword_name": name,  # **保留原始名稱**
                        "is_nested_testcase": original_info['is_nested_testcase'],
                        "status": "RUNNING"
                    }
                }
                self._emit_message(message)

    def end_keyword(self, name, attrs):
        """關鍵字結束時的處理 - 支援映射轉換"""
        if attrs.get('type', '') in ['KEYWORD', 'LIBRARY']:
            with self._lock:
                status = attrs['status']

                # **新增：檢查是否為生成的 testcase keyword**
                original_info = self._resolve_keyword_name(name)

                message = {
                    "type": "keyword_end",
                    "data": {
                        "test_name": self.current_test,
                        "keyword_name": original_info['display_name'],  # **使用轉換後的名稱**
                        "original_keyword_name": name,  # **保留原始名稱**
                        "is_nested_testcase": original_info['is_nested_testcase'],
                        "status": status,
                        "message": attrs.get('message', '')
                    }
                }
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

    def _resolve_keyword_name(self, robot_keyword_name):
        """解析 keyword 名稱，轉換生成的 testcase keyword"""
        # 檢查是否為生成的 testcase keyword
        keyword_to_testcase = self.keyword_mapping.get('keyword_to_testcase', {})

        if robot_keyword_name in keyword_to_testcase:
            # 這是一個生成的 testcase keyword
            testcase_info = keyword_to_testcase[robot_keyword_name]
            return {
                'display_name': testcase_info['testcase_name'],  # 使用原始 testcase 名稱
                'is_nested_testcase': True,
                'testcase_id': testcase_info['testcase_id']
            }
        else:
            # 這是一個普通的 keyword
            return {
                'display_name': robot_keyword_name,
                'is_nested_testcase': False,
                'testcase_id': None
            }

    def _emit_message(self, message: dict):
        try:
            print( "="*100 + f"\n[LISTENER] 🔥 Emitting: {message['type']} - {message}")
            self.signal.emit(message)
            print(f"[LISTENER] ✅ Emit successful\n" + "="*100)
        except Exception as e:
            print(f"[LISTENER] ❌ Emit failed: {e}")


