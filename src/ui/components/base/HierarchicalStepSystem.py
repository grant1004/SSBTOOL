# src/ui/components/base/HierarchicalStepSystem.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


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
class StepPath:
    """步驟路徑，用於唯一標識嵌套結構中的每個步驟"""
    path: List[str]  # 路徑數組，例如 ["testcase2", "testcase1", "delay"]
    level: int  # 嵌套層級，0為頂層

    def __str__(self):
        return " > ".join(self.path)

    def get_path_id(self):
        """獲取唯一的路徑ID"""
        return "__".join(self.path)

    def is_ancestor_of(self, other_path: 'StepPath') -> bool:
        """檢查是否為另一個路徑的祖先"""
        if len(self.path) >= len(other_path.path):
            return False
        return other_path.path[:len(self.path)] == self.path

    def is_descendant_of(self, other_path: 'StepPath') -> bool:
        """檢查是否為另一個路徑的後代"""
        return other_path.is_ancestor_of(self)


class HierarchicalStep:
    """階層式步驟物件"""

    def __init__(self, step_data: dict, path: StepPath, parent: Optional['HierarchicalStep'] = None):
        self.step_data = step_data
        self.path = path
        self.parent = parent
        self.children: List['HierarchicalStep'] = []
        self.status = ExecutionStatus.WAITING
        self.progress = 0
        self.error_message = ""
        self.ui_widget = None  # 對應的UI元件

        # 從step_data提取信息
        self.step_type = StepType(step_data.get('step_type', 'keyword'))
        self.name = self._extract_name()
        self.unique_id = step_data.get('unique_id', step_data.get('keyword_id', step_data.get('testcase_id')))
        self.parameters = step_data.get('parameters', {})

        # 如果是testcase類型，遞歸建立子步驟
        if self.step_type == StepType.TESTCASE:
            self._build_children()

    def _extract_name(self) -> str:
        """提取步驟名稱"""
        if self.step_type == StepType.KEYWORD:
            return self.step_data.get('keyword_name', 'Unknown Keyword')
        elif self.step_type == StepType.TESTCASE:
            return f"[Testcase] {self.step_data.get('testcase_name', 'Unknown Testcase')}"
        return 'Unknown Step'

    def _build_children(self):
        """建立子步驟（僅對testcase類型）"""
        if self.step_type != StepType.TESTCASE:
            return

        child_steps = self.step_data.get('steps', [])
        for i, child_step_data in enumerate(child_steps):
            # 建立子路徑
            child_name = self._get_child_step_name(child_step_data, i)
            child_path = StepPath(
                path=self.path.path + [child_name],
                level=self.path.level + 1
            )

            # 建立子步驟物件
            child_step = HierarchicalStep(child_step_data, child_path, self)
            self.children.append(child_step)

    def _get_child_step_name(self, child_step_data: dict, index: int) -> str:
        """獲取子步驟名稱，用於路徑建立"""
        step_type = child_step_data.get('step_type', 'keyword')
        if step_type == 'keyword':
            return f"kw_{child_step_data.get('keyword_name', f'step_{index}')}"
        elif step_type == 'testcase':
            return f"tc_{child_step_data.get('testcase_name', f'testcase_{index}')}"
        return f"step_{index}"

    def update_status(self, status: ExecutionStatus, progress: int = None, error_message: str = ""):
        """更新步驟狀態"""
        self.status = status
        if progress is not None:
            self.progress = progress
        self.error_message = error_message

        # 更新UI
        if self.ui_widget:
            self.ui_widget.update_display(status, progress, error_message)

    def get_all_descendants(self) -> List['HierarchicalStep']:
        """獲取所有後代步驟（深度優先）"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    def find_step_by_path(self, target_path: StepPath) -> Optional['HierarchicalStep']:
        """根據路徑查找步驟"""
        if self.path.get_path_id() == target_path.get_path_id():
            return self

        # 在子步驟中查找
        for child in self.children:
            result = child.find_step_by_path(target_path)
            if result:
                return result
        return None

    def find_step_by_keyword_name(self, keyword_name: str, context_path: StepPath = None) -> Optional[
        'HierarchicalStep']:
        """根據關鍵字名稱查找步驟，可指定上下文路徑"""
        # 優先在指定上下文中查找
        if context_path and context_path.is_ancestor_of(self.path):
            if self._matches_keyword_name(keyword_name):
                return self

        # 在子步驟中查找
        for child in self.children:
            result = child.find_step_by_keyword_name(keyword_name, context_path)
            if result:
                return result

        # 如果沒有指定上下文，進行普通匹配
        if not context_path and self._matches_keyword_name(keyword_name):
            return self

        return None

    def _matches_keyword_name(self, keyword_name: str) -> bool:
        """檢查是否匹配關鍵字名稱"""
        # 精確匹配
        if self.step_type == StepType.KEYWORD:
            step_keyword_name = self.step_data.get('keyword_name', '')
            if step_keyword_name == keyword_name:
                return True

        # 模糊匹配（處理Robot Framework的命名變換）
        normalized_target = self._normalize_keyword_name(keyword_name)
        normalized_self = self._normalize_keyword_name(self.name)

        return normalized_target == normalized_self or normalized_target in normalized_self

    def _normalize_keyword_name(self, name: str) -> str:
        """正規化關鍵字名稱以便比較"""
        import re
        # 移除特殊字符，轉為小寫
        normalized = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name.lower())
        # 移除連續的下劃線
        normalized = re.sub(r'_+', '_', normalized).strip('_')
        return normalized


class ExecutionContext:
    """執行上下文，追蹤當前執行路徑"""

    def __init__(self):
        self.current_path: List[str] = []  # 當前執行路徑
        self.execution_stack: List[StepPath] = []  # 執行堆疊
        self.completed_steps: set = set()  # 已完成的步驟路徑ID

    def enter_step(self, step_name: str):
        """進入一個步驟"""
        self.current_path.append(step_name)
        current_step_path = StepPath(self.current_path.copy(), len(self.current_path) - 1)
        self.execution_stack.append(current_step_path)

    def exit_step(self):
        """退出當前步驟"""
        if self.current_path:
            exited_step_path = self.execution_stack.pop() if self.execution_stack else None
            if exited_step_path:
                self.completed_steps.add(exited_step_path.get_path_id())
            self.current_path.pop()

    def get_current_context_path(self) -> Optional[StepPath]:
        """獲取當前上下文路徑"""
        if self.execution_stack:
            return self.execution_stack[-1]
        return None

    def is_step_completed(self, step_path: StepPath) -> bool:
        """檢查步驟是否已完成"""
        return step_path.get_path_id() in self.completed_steps


class HierarchicalStepManager:
    """階層式步驟管理器"""

    def __init__(self, steps_data: List[dict]):
        self.root_steps: List[HierarchicalStep] = []
        self.step_registry: Dict[str, HierarchicalStep] = {}  # path_id -> step
        self.execution_context = ExecutionContext()
        self.ui_container = None

        # 建立步驟樹
        self._build_step_tree(steps_data)

        # 建立註冊表
        self._build_registry()

    def _build_step_tree(self, steps_data: List[dict]):
        """建立步驟樹結構"""
        for i, step_data in enumerate(steps_data):
            step_name = self._get_step_name(step_data, i)
            path = StepPath([step_name], 0)
            step = HierarchicalStep(step_data, path)
            self.root_steps.append(step)

    def _get_step_name(self, step_data: dict, index: int) -> str:
        """獲取步驟名稱"""
        step_type = step_data.get('step_type', 'keyword')
        if step_type == 'keyword':
            return f"kw_{step_data.get('keyword_name', f'step_{index}')}"
        elif step_type == 'testcase':
            return f"tc_{step_data.get('testcase_name', f'testcase_{index}')}"
        return f"step_{index}"

    def _build_registry(self):
        """建立步驟註冊表"""
        for root_step in self.root_steps:
            self._register_step(root_step)

    def _register_step(self, step: HierarchicalStep):
        """註冊步驟到註冊表"""
        self.step_registry[step.path.get_path_id()] = step
        for child in step.children:
            self._register_step(child)

    def find_step_for_robot_keyword(self, robot_keyword_name: str) -> Optional[HierarchicalStep]:
        """為Robot Framework關鍵字找到對應的步驟"""

        # 1. 首先嘗試根據當前執行上下文查找
        current_context = self.execution_context.get_current_context_path()

        if current_context:
            # 在當前上下文的範圍內查找
            for root_step in self.root_steps:
                result = root_step.find_step_by_keyword_name(robot_keyword_name, current_context)
                if result and not self.execution_context.is_step_completed(result.path):
                    return result

        # 2. 如果上下文查找失敗，進行全局查找（找第一個未完成的匹配項）
        for root_step in self.root_steps:
            result = root_step.find_step_by_keyword_name(robot_keyword_name)
            if result and not self.execution_context.is_step_completed(result.path):
                return result

        # 3. 嘗試從Robot關鍵字名稱中提取信息進行精確查找
        extracted_info = self._extract_info_from_robot_keyword(robot_keyword_name)
        if extracted_info:
            return self._find_by_extracted_info(extracted_info)

        return None

    def _extract_info_from_robot_keyword(self, robot_keyword_name: str) -> Optional[dict]:
        """從Robot關鍵字名稱中提取信息"""
        import re

        # 匹配生成的testcase關鍵字格式：Execute_Testcase_NAME_ID
        testcase_match = re.match(r'Execute_Testcase_(.+?)_(\d+)$', robot_keyword_name)
        if testcase_match:
            return {
                'type': 'testcase',
                'name': testcase_match.group(1),
                'id': testcase_match.group(2)
            }

        # 匹配普通關鍵字
        return {
            'type': 'keyword',
            'name': robot_keyword_name,
            'id': None
        }

    def _find_by_extracted_info(self, info: dict) -> Optional[HierarchicalStep]:
        """根據提取的信息查找步驟"""
        for step in self.step_registry.values():
            if self.execution_context.is_step_completed(step.path):
                continue

            if info['type'] == 'testcase' and step.step_type == StepType.TESTCASE:
                if info['id'] and str(step.unique_id) == info['id']:
                    return step
            elif info['type'] == 'keyword' and step.step_type == StepType.KEYWORD:
                if step._matches_keyword_name(info['name']):
                    return step

        return None

    def handle_keyword_start(self, robot_keyword_name: str) -> Optional[HierarchicalStep]:
        """處理關鍵字開始"""
        step = self.find_step_for_robot_keyword(robot_keyword_name)
        if step:
            # 更新執行上下文
            if step.parent:
                # 確保父級上下文已建立
                self._ensure_parent_context(step.parent)

            self.execution_context.enter_step(step.path.path[-1])
            step.update_status(ExecutionStatus.RUNNING)

            print(f"[HierarchicalStepManager] Keyword started: {robot_keyword_name} -> {step.path}")
            return step

        print(f"[HierarchicalStepManager] Could not find step for keyword: {robot_keyword_name}")
        return None

    def handle_keyword_end(self, robot_keyword_name: str, robot_status: str, error_message: str = "") -> Optional[
        HierarchicalStep]:
        """處理關鍵字結束"""
        step = self.find_step_for_robot_keyword(robot_keyword_name)
        if step:
            # 映射Robot狀態
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

            step.update_status(status, progress, error_message)
            self.execution_context.exit_step()

            print(f"[HierarchicalStepManager] Keyword ended: {robot_keyword_name} -> {step.path} ({robot_status})")
            return step

        print(f"[HierarchicalStepManager] Could not find step for keyword end: {robot_keyword_name}")
        return None

    def _ensure_parent_context(self, parent_step: HierarchicalStep):
        """確保父級上下文已建立"""
        if parent_step.parent:
            self._ensure_parent_context(parent_step.parent)

        # 檢查父級是否在當前執行路徑中
        parent_path_segments = parent_step.path.path
        current_path_segments = self.execution_context.current_path

        # 如果父級路徑不在當前路徑中，需要建立
        if len(current_path_segments) < len(parent_path_segments) or \
                current_path_segments[:len(parent_path_segments)] != parent_path_segments:
            # 重建正確的執行路徑
            for segment in parent_path_segments[len(current_path_segments):]:
                self.execution_context.enter_step(segment)

    def reset_all_status(self):
        """重置所有步驟狀態"""
        for step in self.step_registry.values():
            step.update_status(ExecutionStatus.WAITING, 0, "")

        # 重置執行上下文
        self.execution_context = ExecutionContext()

        print(f"[HierarchicalStepManager] Reset all step status")

    def get_step_statistics(self) -> dict:
        """獲取步驟統計信息"""
        stats = {
            'total': len(self.step_registry),
            'waiting': 0,
            'running': 0,
            'passed': 0,
            'failed': 0,
            'not_run': 0
        }

        for step in self.step_registry.values():
            if step.status == ExecutionStatus.WAITING:
                stats['waiting'] += 1
            elif step.status == ExecutionStatus.RUNNING:
                stats['running'] += 1
            elif step.status == ExecutionStatus.PASSED:
                stats['passed'] += 1
            elif step.status == ExecutionStatus.FAILED:
                stats['failed'] += 1
            elif step.status == ExecutionStatus.NOT_RUN:
                stats['not_run'] += 1

        return stats

    def create_ui_widgets(self, parent_widget):
        """為所有步驟創建UI元件"""
        self.ui_container = parent_widget

        for root_step in self.root_steps:
            self._create_ui_for_step(root_step, parent_widget)

    def _create_ui_for_step(self, step: HierarchicalStep, parent_widget):
        """為單個步驟創建UI元件"""
        # 這裡可以根據步驟類型創建不同的UI元件
        # 例如：EnhancedKeywordItem 或其他自定義元件

        if step.step_type == StepType.KEYWORD:
            ui_widget = self._create_keyword_ui(step, parent_widget)
        elif step.step_type == StepType.TESTCASE:
            ui_widget = self._create_testcase_ui(step, parent_widget)
        else:
            ui_widget = self._create_generic_ui(step, parent_widget)

        step.ui_widget = ui_widget

        # 遞歸為子步驟創建UI
        for child_step in step.children:
            self._create_ui_for_step(child_step, ui_widget)

    def _create_keyword_ui(self, step: HierarchicalStep, parent_widget):
        """創建關鍵字UI元件"""
        # 實現關鍵字UI創建邏輯
        pass

    def _create_testcase_ui(self, step: HierarchicalStep, parent_widget):
        """創建測試案例UI元件"""
        # 實現測試案例UI創建邏輯
        pass

    def _create_generic_ui(self, step: HierarchicalStep, parent_widget):
        """創建通用UI元件"""
        # 實現通用UI創建邏輯
        pass


# 使用示例
class EnhancedCollapsibleProgressPanel(QFrame):
    """使用階層式步驟系統的增強進度面板"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)

        self.config = config
        steps_data = config.get('steps', [])

        # 使用新的階層式步驟管理器
        self.step_manager = HierarchicalStepManager(steps_data)

        self._setup_ui()

    def _setup_ui(self):
        """設置UI"""
        layout = QVBoxLayout(self)

        # 創建標題
        title_label = QLabel(self.config.get('name', 'Test Case'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 創建統計信息標籤
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)

        # 創建步驟UI容器
        self.steps_container = QWidget()
        self.step_manager.create_ui_widgets(self.steps_container)
        layout.addWidget(self.steps_container)

        self._update_statistics_display()

    def update_status(self, message: dict):
        """更新狀態"""
        try:
            msg_type = message.get('type', '')
            data = message.get('data', {})

            if msg_type == 'keyword_start':
                robot_keyword_name = data.get('original_keyword_name', data.get('keyword_name', ''))
                self.step_manager.handle_keyword_start(robot_keyword_name)

            elif msg_type == 'keyword_end':
                robot_keyword_name = data.get('original_keyword_name', data.get('keyword_name', ''))
                robot_status = data.get('status', 'UNKNOWN')
                error_message = data.get('message', '')
                self.step_manager.handle_keyword_end(robot_keyword_name, robot_status, error_message)

            elif msg_type == 'test_start':
                self.step_manager.reset_all_status()

            self._update_statistics_display()

        except Exception as e:
            print(f"[EnhancedCollapsibleProgressPanel] Error updating status: {e}")

    def _update_statistics_display(self):
        """更新統計信息顯示"""
        stats = self.step_manager.get_step_statistics()
        completed = stats['passed'] + stats['failed'] + stats['not_run']
        total = stats['total']

        stats_text = f"進度: {completed}/{total} (✓{stats['passed']} ✗{stats['failed']} ◦{stats['not_run']})"
        self.stats_label.setText(stats_text)

    def reset_status(self):
        """重置狀態"""
        self.step_manager.reset_all_status()
        self._update_statistics_display()