# src/worker/RobotTestWorker.py

import os
import json
import threading
from robot import run
from PySide6.QtCore import Signal, QObject, Slot, QThread
from src.utils import ProgressListener


class RobotTestWorker(QObject):
    finished = Signal(bool)
    progress = Signal(dict)
    error = Signal(str)  # 新增錯誤信號

    def __init__(self, robot_file_path, project_root, lib_path, output_dir, mapping_file_path=None):
        super().__init__()
        self.progress_listener = None
        self.robot_file_path = robot_file_path
        self.project_root = project_root
        self.lib_path = lib_path
        self.output_dir = output_dir
        self.mapping_file_path = mapping_file_path

        # 停止控制
        self._stop_requested = threading.Event()
        self._is_running = threading.Event()

    @Slot()
    def start_work(self):
        """開始執行工作的槽函數"""
        try:
            self._is_running.set()
            self._stop_requested.clear()

            # 檢查是否在開始前就被停止
            if self._stop_requested.is_set():
                self.finished.emit(False)
                return

            # 載入映射關係
            keyword_mapping = None
            if self.mapping_file_path and os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    keyword_mapping = json.load(f)

            # 創建 ProgressListener 並傳遞停止檢查
            self.progress_listener = ProgressListener(
                self.progress,
                keyword_mapping,
                stop_check_func=self._should_stop  # 傳遞停止檢查函數
            )

            # 執行 Robot Framework
            result = run(
                self.robot_file_path,
                outputdir=self.output_dir,
                pythonpath=[self.project_root, self.lib_path],
                variable=['TIMEOUT:30s'],
                loglevel='DEBUG',
                listener=self.progress_listener,
                console='none'
            )

            # 檢查是否因停止而結束
            if self._stop_requested.is_set():
                self.finished.emit(False)  # 停止視為失敗
            else:
                self.finished.emit(result == 0)

        except Exception as e:
            print(f"[WORKER] Error running test case: {os.path.basename(self.robot_file_path)}")
            print(f"[WORKER] Exception: {str(e)}")

            self.error.emit(str(e))
            self.finished.emit(False)
        finally:
            self._is_running.clear()

    @Slot()
    def stop_work(self):
        """停止工作 - 設置停止標誌"""
        print("[WORKER] Stop requested")
        self._stop_requested.set()

        # 如果 ProgressListener 支持停止，也通知它
        if self.progress_listener and hasattr(self.progress_listener, 'request_stop'):
            self.progress_listener.request_stop()

    def _should_stop(self) -> bool:
        """檢查是否應該停止"""
        return self._stop_requested.is_set()

    def is_running(self) -> bool:
        """檢查是否正在運行"""
        return self._is_running.is_set()

