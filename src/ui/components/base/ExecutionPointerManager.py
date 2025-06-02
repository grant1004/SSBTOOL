# src/ui/components/base/BaseProgress.py - 整合ExecutionPointerManager版本

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from collections import deque
import time

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import get_icon_path, Utils


class StepType(Enum):
    KEYWORD = "keyword"
    TESTCASE = "testcase"


class ExecutionStatus(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


@dataclass
class ExecutionStep:
    """扁平化的執行步驟"""
    index: int  # 在執行序列中的索引位置
    step_type: StepType  # 步驟類型
    name: str  # 步驟名稱
    original_data: dict  # 原始步驟數據
    parent_index: Optional[int]  # 父步驟索引（用於嵌套顯示）
    level: int  # 嵌套層級
    ui_widget: Optional[object] = None  # 對應的UI元件

    # 執行狀態
    status: ExecutionStatus = ExecutionStatus.WAITING
    progress: int = 0
    error_message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def update_status(self, status: ExecutionStatus, progress: int = None, error_message: str = ""):
        """更新步驟狀態"""
        self.status = status
        if progress is not None:
            self.progress = progress
        self.error_message = error_message

        # 記錄時間
        if status == ExecutionStatus.RUNNING:
            self.start_time = time.time()
        elif status in [ExecutionStatus.PASSED, ExecutionStatus.FAILED, ExecutionStatus.NOT_RUN]:
            self.end_time = time.time()

        # 更新UI
        if self.ui_widget and hasattr(self.ui_widget, 'update_display'):
            self.ui_widget.update_display(status, progress, error_message)

    def get_execution_time(self) -> float:
        """獲取執行時間"""
        if self.start_time is None:
            return 0.0
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def __str__(self):
        indent = "  " * self.level
        return f"{indent}[{self.index}] {self.name} ({self.status.value})"


class ExecutionPointerManager:
    """執行指針式步驟管理器"""

    def __init__(self, steps_data: List[dict]):
        self.execution_sequence: List[ExecutionStep] = []  # 扁平化的執行序列
        self.execution_pointer: int = 0  # 當前執行指針
        self.execution_stack: List[int] = []  # 執行堆疊（處理嵌套）
        self.completed_steps: set = set()  # 已完成的步驟索引

        # 建立扁平化執行序列
        self._build_execution_sequence(steps_data)

        print(f"[ExecutionPointerManager] Built execution sequence with {len(self.execution_sequence)} steps")

    def _build_execution_sequence(self, steps_data: List[dict], parent_index: Optional[int] = None, level: int = 0):
        """將嵌套步驟結構扁平化為線性執行序列"""

        for step_data in steps_data:
            current_index = len(self.execution_sequence)
            step_type = StepType(step_data.get('step_type', 'keyword'))

            # 提取步驟名稱
            if step_type == StepType.KEYWORD:
                name = step_data.get('keyword_name', 'Unknown Keyword')
            elif step_type == StepType.TESTCASE:
                name = f"[Testcase] {step_data.get('testcase_name', 'Unknown Testcase')}"
            else:
                name = 'Unknown Step'

            # 創建執行步驟
            exec_step = ExecutionStep(
                index=current_index,
                step_type=step_type,
                name=name,
                original_data=step_data,
                parent_index=parent_index,
                level=level
            )

            self.execution_sequence.append(exec_step)

            # 如果是 testcase 類型，遞歸處理子步驟
            if step_type == StepType.TESTCASE:
                child_steps = step_data.get('steps', [])
                if child_steps:
                    self._build_execution_sequence(child_steps, current_index, level + 1)

    def get_current_step(self) -> Optional[ExecutionStep]:
        """獲取當前執行指針指向的步驟"""
        if 0 <= self.execution_pointer < len(self.execution_sequence):
            return self.execution_sequence[self.execution_pointer]
        return None

    def advance_pointer(self) -> bool:
        """推進執行指針到下一個步驟"""
        if self.execution_pointer < len(self.execution_sequence) - 1:
            self.execution_pointer += 1
            return True
        return False

    def handle_keyword_start(self, robot_keyword_name: str) -> Optional[ExecutionStep]:
        """處理關鍵字開始"""
        current_step = self.get_current_step()

        if current_step is None:
            print(f"[ExecutionPointerManager] No current step available for: {robot_keyword_name}")
            return None

        # 更新步驟狀態
        current_step.update_status(ExecutionStatus.RUNNING)
        self.execution_stack.append(current_step.index)

        print(f"[ExecutionPointerManager] Step {current_step.index} started: {current_step.name}")
        return current_step

    def handle_keyword_end(self, robot_keyword_name: str, robot_status: str, error_message: str = "") -> Optional[
        ExecutionStep]:
        """處理關鍵字結束"""
        if not self.execution_stack:
            print(f"[ExecutionPointerManager] No step in execution stack for: {robot_keyword_name}")
            return None

        # 從執行堆疊獲取當前步驟
        current_step_index = self.execution_stack.pop()
        current_step = self.execution_sequence[current_step_index]

        # 映射 Robot Framework 狀態
        if robot_status == 'PASS':
            status = ExecutionStatus.PASSED
            progress = 100
        elif robot_status == 'FAIL':
            status = ExecutionStatus.FAILED
            progress = 100
        elif robot_status == 'NOT RUN':
            status = ExecutionStatus.NOT_RUN
            progress = 100
        else:
            status = ExecutionStatus.WAITING
            progress = 0

        # 更新步驟狀態
        current_step.update_status(status, progress, error_message)
        self.completed_steps.add(current_step_index)

        # 推進執行指針（如果當前步驟完成）
        if current_step_index == self.execution_pointer:
            self.advance_pointer()

        print(f"[ExecutionPointerManager] Step {current_step.index} ended: {current_step.name} ({robot_status})")
        return current_step

    def handle_test_start(self, test_name: str):
        """處理測試開始"""
        print(f"[ExecutionPointerManager] Test started: {test_name}")
        self.reset_execution()

    def handle_test_end(self, test_name: str, test_status: str):
        """處理測試結束"""
        print(f"[ExecutionPointerManager] Test ended: {test_name} ({test_status})")

    def reset_execution(self):
        """重置執行狀態"""
        self.execution_pointer = 0
        self.execution_stack.clear()
        self.completed_steps.clear()

        # 重置所有步驟狀態
        for step in self.execution_sequence:
            step.update_status(ExecutionStatus.WAITING, 0, "")

        print(f"[ExecutionPointerManager] Execution reset")

    def get_execution_progress(self) -> dict:
        """獲取執行進度統計"""
        total = len(self.execution_sequence)
        completed = len(self.completed_steps)

        status_counts = {
            'waiting': 0,
            'running': 0,
            'passed': 0,
            'failed': 0,
            'not_run': 0
        }

        for step in self.execution_sequence:
            status_counts[step.status.value] += 1

        return {
            'total': total,
            'completed': completed,
            'current_pointer': self.execution_pointer,
            'progress_percent': int((completed / total) * 100) if total > 0 else 0,
            'status_counts': status_counts
        }




# # 測試用例
# if __name__ == "__main__":
#     import sys
#     from PySide6.QtWidgets import QApplication, QVBoxLayout, QMainWindow
#
#     app = QApplication(sys.argv)
#
#     # 測試配置
#     test_config = {
#         'name': 'Test Execution Panel',
#         'steps': [
#             {"step_type": "keyword", "keyword_name": "start_listening"},
#             {"step_type": "keyword", "keyword_name": "send_can_message"},
#             {
#                 "step_type": "testcase",
#                 "testcase_name": "nested_test",
#                 "steps": [
#                     {"step_type": "keyword", "keyword_name": "process_data"},
#                     {"step_type": "keyword", "keyword_name": "validate_result"}
#                 ]
#             },
#             {"step_type": "keyword", "keyword_name": "stop_listening"}
#         ]
#     }
#
#     # 創建主窗口
#     window = QMainWindow()
#     central_widget = QWidget()
#     layout = QVBoxLayout(central_widget)
#
#     # 創建進度面板
#     panel = CollapsibleProgressPanel(test_config)
#     layout.addWidget(panel)
#
#     window.setCentralWidget(central_widget)
#     window.resize(600, 400)
#     window.show()
#
#
#     # 模擬測試執行
#     def simulate_execution():
#         import time
#         QTimer.singleShot(1000, lambda: panel.update_status({
#             "type": "test_start",
#             "data": {"test_name": "Test Execution"}
#         }))
#
#         QTimer.singleShot(2000, lambda: panel.update_status({
#             "type": "keyword_start",
#             "data": {"keyword_name": "start_listening"}
#         }))
#
#         QTimer.singleShot(3000, lambda: panel.update_status({
#             "type": "keyword_end",
#             "data": {"keyword_name": "start_listening", "status": "PASS"}
#         }))
#
#
#     simulate_execution()
#
#     sys.exit(app.exec())