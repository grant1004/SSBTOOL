import os
import json
from robot import run
from PySide6.QtCore import Signal, QEventLoop, QObject, Slot, QThread
from src.utils import ProgressListener


class RobotTestWorker(QObject):
    finished = Signal(bool)
    progress = Signal(dict)

    def __init__(self, robot_file_path, project_root, lib_path, output_dir, mapping_file_path=None):
        super().__init__()
        self.progress_listener = None
        self.robot_file_path = robot_file_path
        self.project_root = project_root
        self.lib_path = lib_path
        self.output_dir = output_dir
        self.mapping_file_path = mapping_file_path  # **新增**

    @Slot()
    def start_work(self):
        """開始執行工作的槽函數"""
        # print(f"[WORKER] Starting Robot test execution in thread: {QThread.currentThread()}")

        try:
            # **載入映射關係**
            keyword_mapping = None
            if self.mapping_file_path and os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    keyword_mapping = json.load(f)

            # **傳遞映射給 ProgressListener**
            self.progress_listener = ProgressListener(self.progress, keyword_mapping)

            result = run(
                self.robot_file_path,
                outputdir=self.output_dir,
                pythonpath=[self.project_root, self.lib_path],
                variable=['TIMEOUT:30s'],
                loglevel='DEBUG',
                listener=self.progress_listener,
                console='none'
            )

            self.finished.emit(result == 0)

        except Exception as e:
            print(f"[WORKER] Error running test case: {os.path.basename(self.robot_file_path)}")
            print(f"[WORKER] Exception: {str(e)}")

            # 發射錯誤進度信息
            error_dict = {"error": f"Error: {str(e)}"}
            self.progress.emit(error_dict)
            self.finished.emit(False)

    # 保留原來的 run 方法作為備用（如果需要）
    def run(self):
        """備用方法 - 建議使用 start_work() 槽函數"""
        # print("[WORKER] Warning: run() called directly. Consider using start_work() slot instead.")
        self.start_work()