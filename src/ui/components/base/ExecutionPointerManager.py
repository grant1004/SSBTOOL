# src/ui/components/base/ExecutionPointerManager.py - Level-based 版本

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from collections import deque
import time
import re

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

    def matches_robot_keyword(self, robot_keyword_name: str) -> bool:
        """檢查是否匹配 Robot Framework 關鍵字名稱"""
        # 正規化關鍵字名稱進行比較
        normalized_robot = self._normalize_keyword_name(robot_keyword_name)
        normalized_self = self._normalize_keyword_name(self.name)

        # 直接匹配
        if normalized_robot == normalized_self:
            return True

        # 處理 testcase 格式的特殊匹配
        if self.step_type == StepType.TESTCASE:
            # 移除 [Testcase] 前綴進行匹配
            testcase_name = self.name.replace('[Testcase] ', '').strip()
            normalized_testcase = self._normalize_keyword_name(testcase_name)
            if normalized_robot == normalized_testcase:
                return True

        # 處理 Robot Framework 可能將下劃線轉為空格的情況
        robot_with_underscores = robot_keyword_name.lower().replace(' ', '_')
        self_with_underscores = self.name.lower().replace(' ', '_')
        if robot_with_underscores == self_with_underscores:
            return True

        return False

    def _normalize_keyword_name(self, name: str) -> str:
        """正規化關鍵字名稱"""
        if not name:
            return ""

        # 轉為小寫
        normalized = name.lower().strip()

        # 處理特殊的 testcase 格式：[testcase] name -> testcase_name
        if normalized.startswith('[testcase]'):
            normalized = normalized.replace('[testcase]', '').strip()
        elif normalized.startswith('[testcase'):
            normalized = normalized.replace('[testcase', '').strip()
            if normalized.endswith(']'):
                normalized = normalized[:-1].strip()

        # 統一空格和下劃線
        normalized = normalized.replace(' ', '_')

        # 移除特殊字符，只保留字母、數字、下劃線和中文
        normalized = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', normalized)

        # 清理多餘的下劃線
        normalized = re.sub(r'_+', '_', normalized).strip('_')

        return normalized

    def __str__(self):
        indent = "  " * self.level
        return f"{indent}[{self.index}] {self.name} ({self.status.value})"


@dataclass
class LevelContext:
    """層級執行上下文"""
    parent_index: Optional[int]  # 父步驟索引，None 表示頂層
    children_indices: List[int]  # 子步驟索引列表
    current_pointer: int = 0  # 當前子步驟指針

    def get_current_child_index(self) -> Optional[int]:
        """獲取當前應該執行的子步驟索引"""
        if 0 <= self.current_pointer < len(self.children_indices):
            return self.children_indices[self.current_pointer]
        return None

    def advance_pointer(self) -> bool:
        """推進指針到下一個子步驟"""
        if self.current_pointer < len(self.children_indices) - 1:
            self.current_pointer += 1
            return True
        return False


class ExecutionPointerManager:
    """基於 Level 的多層執行指針管理器"""

    def __init__(self, steps_data: List[dict]):
        self.execution_sequence: List[ExecutionStep] = []  # 扁平化的執行序列
        self.level_contexts: Dict[Optional[int], LevelContext] = {}  # 每個層級的執行上下文
        self.execution_stack: List[int] = []  # 當前執行路徑（父步驟索引堆疊）
        self.completed_steps: set = set()  # 已完成的步驟索引
        # 添加時間追蹤變數
        self.test_start_time: Optional[float] = None
        self.test_end_time: Optional[float] = None

        # 建立扁平化執行序列
        self._build_execution_sequence(steps_data)

        # 建立層級上下文
        self._build_level_contexts()

        print(f"[ExecutionPointerManager] Built execution sequence with {len(self.execution_sequence)} steps")
        for step in self.execution_sequence:
            print(f"  {step}")

        print(f"[ExecutionPointerManager] Built level contexts:")
        for parent_index, context in self.level_contexts.items():
            parent_name = f"Step {parent_index}" if parent_index is not None else "ROOT"
            print(f"  {parent_name}: children={context.children_indices}")

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

    def _build_level_contexts(self):
        """建立層級執行上下文"""
        # 為每個父步驟（包括 None 表示根層級）建立上下文
        parent_children_map = {}

        for step in self.execution_sequence:
            parent_index = step.parent_index
            if parent_index not in parent_children_map:
                parent_children_map[parent_index] = []
            parent_children_map[parent_index].append(step.index)

        # 建立層級上下文
        for parent_index, children_indices in parent_children_map.items():
            self.level_contexts[parent_index] = LevelContext(
                parent_index=parent_index,
                children_indices=children_indices
            )

    def get_current_expected_step(self) -> Optional[ExecutionStep]:
        """獲取當前應該執行的步驟（基於層級上下文）"""
        # 獲取當前層級的上下文
        current_parent = self.execution_stack[-1] if self.execution_stack else None
        context = self.level_contexts.get(current_parent)

        if context is None:
            return None

        # 獲取當前應該執行的子步驟
        current_child_index = context.get_current_child_index()
        if current_child_index is not None:
            return self.execution_sequence[current_child_index]

        return None

    def find_step_by_robot_keyword(self, robot_keyword_name: str) -> Optional[ExecutionStep]:
        """根據 Robot Framework 關鍵字名稱查找對應的步驟"""

        print(f"[ExecutionPointerManager] 🔍 Searching for keyword: '{robot_keyword_name}'")
        print(f"[ExecutionPointerManager] Current execution stack: {self.execution_stack}")

        # 首先檢查當前層級的預期步驟
        expected_step = self.get_current_expected_step()
        if expected_step and expected_step.matches_robot_keyword(robot_keyword_name):
            print(f"[ExecutionPointerManager] ✅ Found expected step: Step {expected_step.index} - {expected_step.name}")
            return expected_step

        # 如果預期步驟不匹配，檢查是否是新的 testcase 開始（可能在不同層級）
        for step in self.execution_sequence:
            if (step.status == ExecutionStatus.WAITING and
                    step.matches_robot_keyword(robot_keyword_name)):
                print(f"[ExecutionPointerManager] ✅ Found matching step: Step {step.index} - {step.name}")
                return step

        print(f"[ExecutionPointerManager] ❌ No matching step found for: '{robot_keyword_name}'")
        return None

    def handle_keyword_start(self, robot_keyword_name: str) -> Optional[ExecutionStep]:
        """處理關鍵字開始"""
        # 根據關鍵字名稱查找對應的步驟
        step = self.find_step_by_robot_keyword(robot_keyword_name)

        if step is None:
            print(f"[ExecutionPointerManager] ❌ Could not find step for keyword: '{robot_keyword_name}'")
            return None

        # 檢查步驟是否已經在運行
        if step.status == ExecutionStatus.RUNNING:
            print(f"[ExecutionPointerManager] ⚠️ Step {step.index} is already running: {step.name}")
            return step

        # 更新步驟狀態
        step.update_status(ExecutionStatus.RUNNING)

        # 如果是 testcase，進入新的層級
        if step.step_type == StepType.TESTCASE:
            self.execution_stack.append(step.index)
            print(f"[ExecutionPointerManager] 📥 Entered testcase level: Step {step.index}")
            print(f"[ExecutionPointerManager] Execution stack: {self.execution_stack}")

        print(f"[ExecutionPointerManager] ✅ Step {step.index} started: {step.name}")
        return step

    def handle_keyword_end(self, robot_keyword_name: str, robot_status: str, error_message: str = "") -> Optional[
        ExecutionStep]:
        """處理關鍵字結束"""
        print(f"[ExecutionPointerManager] 🔍 Looking for running step matching: '{robot_keyword_name}'")

        # 查找對應的運行中步驟
        step = None
        for s in self.execution_sequence:
            if (s.status == ExecutionStatus.RUNNING and
                    s.matches_robot_keyword(robot_keyword_name)):
                step = s
                break

        if step is None:
            print(f"[ExecutionPointerManager] ❌ Could not find running step for keyword: '{robot_keyword_name}'")
            return None

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
        step.update_status(status, progress, error_message)
        self.completed_steps.add(step.index)

        # 處理層級邏輯
        if step.step_type == StepType.TESTCASE:
            # testcase 結束，退出該層級
            if self.execution_stack and self.execution_stack[-1] == step.index:
                self.execution_stack.pop()
                print(f"[ExecutionPointerManager] 📤 Exited testcase level: Step {step.index}")
                print(f"[ExecutionPointerManager] Execution stack: {self.execution_stack}")

                # 推進父層級的指針
                self._advance_parent_pointer(step.parent_index)
        else:
            # keyword 結束，推進當前層級的指針
            self._advance_current_level_pointer()

        print(f"[ExecutionPointerManager] ✅ Step {step.index} ended: {step.name} ({robot_status})")
        return step

    def _advance_current_level_pointer(self):
        """推進當前層級的指針"""
        current_parent = self.execution_stack[-1] if self.execution_stack else None
        context = self.level_contexts.get(current_parent)

        if context:
            advanced = context.advance_pointer()
            print(
                f"[ExecutionPointerManager] 📈 Advanced pointer in level {current_parent}: {context.current_pointer}/{len(context.children_indices)} (advanced={advanced})")

    def _advance_parent_pointer(self, parent_index: Optional[int]):
        """推進父層級的指針"""
        context = self.level_contexts.get(parent_index)

        if context:
            advanced = context.advance_pointer()
            print(
                f"[ExecutionPointerManager] 📈 Advanced pointer in parent level {parent_index}: {context.current_pointer}/{len(context.children_indices)} (advanced={advanced})")

    def handle_test_start(self, test_name: str):
        """處理測試開始"""
        print(f"[ExecutionPointerManager] Test started: {test_name}")
        self.test_start_time = time.time()  # 記錄測試開始時間
        self.test_end_time = None
        self.reset_execution()

    def handle_test_end(self, test_name: str, test_status: str):
        """處理測試結束"""
        print(f"[ExecutionPointerManager] Test ended: {test_name} ({test_status})")
        self.test_end_time = time.time()  # 記錄測試結束時間

    def reset_execution(self):
        """重置執行狀態"""
        self.execution_stack.clear()
        self.completed_steps.clear()

        # 重置所有步驟狀態
        for step in self.execution_sequence:
            step.update_status(ExecutionStatus.WAITING, 0, "")

        # 重置所有層級上下文的指針
        for context in self.level_contexts.values():
            context.current_pointer = 0

        # 重置時間追蹤（但保留 test_start_time）
        # self.test_start_time = None  # 不重置，因為測試正在進行
        self.test_end_time = None

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

        # 計算當前指針位置（基於當前層級的預期步驟）
        current_step = self.get_current_expected_step()
        current_pointer = current_step.index if current_step else total

        return {
            'total': total,
            'completed': completed,
            'current_pointer': current_pointer,
            'progress_percent': int((completed / total) * 100) if total > 0 else 0,
            'status_counts': status_counts
        }

    def get_current_step(self) -> Optional[ExecutionStep]:
        """獲取當前步驟（為了兼容性保留）"""
        return self.get_current_expected_step()

    def debug_execution_state(self):
        """調試方法：打印當前執行狀態"""
        print(f"\n=== ExecutionPointerManager Debug ===")
        print(f"Execution stack: {self.execution_stack}")
        print(f"Completed steps: {self.completed_steps}")

        print("Level contexts:")
        for parent_index, context in self.level_contexts.items():
            parent_name = f"Step {parent_index}" if parent_index is not None else "ROOT"
            current_child = context.get_current_child_index()
            current_child_name = f"Step {current_child}" if current_child is not None else "None"
            print(
                f"  {parent_name}: pointer={context.current_pointer}/{len(context.children_indices)}, current={current_child_name}")

        print("All steps:")
        for step in self.execution_sequence:
            status_symbol = {
                ExecutionStatus.WAITING: "⏳",
                ExecutionStatus.RUNNING: "🔄",
                ExecutionStatus.PASSED: "✅",
                ExecutionStatus.FAILED: "❌",
                ExecutionStatus.NOT_RUN: "⏸️"
            }.get(step.status, "❓")
            print(f"  {status_symbol} {step}")
        print("=" * 40)

    def get_top_level_progress(self) -> dict:
        """獲取只計算頂層步驟的執行進度統計"""
        # 獲取頂層步驟（level = 0）
        top_level_steps = [step for step in self.execution_sequence if step.level == 0]

        total = len(top_level_steps)
        completed = len([step for step in top_level_steps if step.index in self.completed_steps])

        status_counts = {
            'waiting': 0,
            'running': 0,
            'passed': 0,
            'failed': 0,
            'not_run': 0
        }

        for step in top_level_steps:
            status_counts[step.status.value] += 1

        # 計算當前頂層步驟的指針位置
        current_top_level_step = None
        for step in top_level_steps:
            if step.status == ExecutionStatus.RUNNING:
                current_top_level_step = step
                break

        if current_top_level_step is None:
            # 找下一個待執行的頂層步驟
            for step in top_level_steps:
                if step.status == ExecutionStatus.WAITING:
                    current_top_level_step = step
                    break

        # 計算在頂層步驟中的位置
        current_pointer = 0
        if current_top_level_step:
            for i, step in enumerate(top_level_steps):
                if step.index == current_top_level_step.index:
                    current_pointer = i
                    break
        else:
            current_pointer = total  # 全部完成

        return {
            'total': total,
            'completed': completed,
            'current_pointer': current_pointer,
            'progress_percent': int((completed / total) * 100) if total > 0 else 0,
            'status_counts': status_counts,
            'top_level_steps': top_level_steps
        }

    def get_total_execution_time(self) -> float:
        """獲取總執行時間（秒）"""
        if self.test_start_time is None:
            return 0.0

        # 如果測試已結束，使用結束時間
        if self.test_end_time is not None:
            return self.test_end_time - self.test_start_time

        # 如果測試還在進行中，使用當前時間
        return time.time() - self.test_start_time

    def get_estimated_remaining_time(self) -> float:
        """估算剩餘執行時間（基於已完成步驟的平均時間）"""
        top_level_progress = self.get_top_level_progress()
        completed_count = top_level_progress['completed']
        total_count = top_level_progress['total']

        if completed_count == 0 or total_count == 0:
            return 0.0

        # 計算已完成頂層步驟的平均執行時間
        completed_top_level_steps = [step for step in top_level_progress['top_level_steps']
                                     if step.index in self.completed_steps]

        if not completed_top_level_steps:
            return 0.0

        total_completed_time = sum(step.get_execution_time() for step in completed_top_level_steps)
        average_time_per_step = total_completed_time / len(completed_top_level_steps)

        remaining_steps = total_count - completed_count
        return remaining_steps * average_time_per_step

    def format_time(self, seconds: float) -> str:
        """格式化時間顯示"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
