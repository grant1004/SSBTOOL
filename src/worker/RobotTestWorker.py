import asyncio
import os
from robot import run
from PySide6.QtCore import Signal, QEventLoop, QObject, Slot, QThread
from src.utils import ProgressListener


class RobotTestWorker(QObject):
    finished = Signal(bool)  # 測試完成信號
    progress = Signal(dict)  # 進度更新信號

    def __init__(self, robot_file_path, project_root, lib_path, output_dir):
        super().__init__()
        self.progress_listener = None
        self.robot_file_path = robot_file_path
        self.project_root = project_root
        self.lib_path = lib_path
        self.output_dir = output_dir
        self.event_loop = QEventLoop()

    @Slot()
    def start_work(self):
        """開始執行工作的槽函數"""
        print(f"[WORKER] Starting Robot test execution in thread: {QThread.currentThread()}")

        try:
            # 確保在同一個線程中創建 ProgressListener
            self.progress_listener = ProgressListener(self.progress)
            result = run(
                self.robot_file_path,
                outputdir=self.output_dir,
                pythonpath=[self.project_root, self.lib_path],
                variable=['TIMEOUT:30s'],
                loglevel='DEBUG',
                listener=self.progress_listener,
                console='none'
            )


            # 發射完成信號
            self.finished.emit(result == 0)

        except Exception as e:
            print(f"[WORKER] Error running test case: {os.path.basename(self.robot_file_path)}")
            print(f"[WORKER] Exception: {str(e)}")

            # 發射錯誤進度信息
            error_dict = {"error": f"Error: {str(e)}"}
            self.progress.emit(error_dict)

            # 發射完成信號（失敗）
            self.finished.emit(False)

    # 保留原來的 run 方法作為備用（如果需要）
    def run(self):
        """備用方法 - 建議使用 start_work() 槽函數"""
        print("[WORKER] Warning: run() called directly. Consider using start_work() slot instead.")
        self.start_work()