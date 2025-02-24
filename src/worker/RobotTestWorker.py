import asyncio
import os
from robot import run
from PySide6.QtCore import Signal, QEventLoop, QObject
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

    def run(self):
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

            print(f"Run completed with listener: {id(self.progress_listener)}")
            self.finished.emit(result == 0)

        except Exception as e:
            print(f"Error running test case: {os.path.basename(self.robot_file_path)}")
            self.progress.emit(f"Error: {str(e)}")
            self.finished.emit(False)
