from PySide6.QtWidgets import QApplication
from robot import run
from robot.api import ExecutionResult
from PySide6.QtCore import QThread, Signal
from src.utils import ProgressListener
import os


class RobotTestWorker(QThread):
    finished = Signal(bool)  # 測試完成信號
    progress = Signal(str)  # 進度更新信號

    def __init__(self, robot_file_path, project_root, lib_path, output_dir):
        super().__init__()
        self.robot_file_path = robot_file_path
        self.project_root = project_root
        self.lib_path = lib_path
        self.output_dir = output_dir

    def run(self):
        try:
            # 執行 Robot Framework 測試
            print(f"Running in thread: {QThread.currentThread()}")
            print(f"Main thread: {QApplication.instance().thread()}")
            result = run(
                self.robot_file_path,
                outputdir=self.output_dir,
                pythonpath=[self.project_root, self.lib_path],
                variable=['TIMEOUT:30s'],
                loglevel='DEBUG',
                listener=ProgressListener(self.progress),
                console='none',  # 關閉 Robot Framework 的控制台輸出
                # stdout=None,  # 關閉標準輸出
                # stderr=None,  # 關閉錯誤輸出
            )
            self.finished.emit(result == 0)

        except Exception as e:
            print(f"Error running test case: {os.path.basename(self.robot_file_path)}")
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit(False)
