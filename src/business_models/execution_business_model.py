# src/business_models/execution_business_model.py
"""
整合原有 RunWidget_Model 功能到新的 MVC 架構
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any, Union, Set
from dataclasses import dataclass, field
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, Slot, Qt
import uuid

# 導入接口
from src.interfaces.execution_interface import (
    ITestCompositionModel, ExecutionConfiguration, TestItem, TestItemType,
    ITestExecutionBusinessModel, IReportGenerationModel, ExecutionResult,
    ExecutionProgress, ExecutionState, TestItemStatus
)

# 導入 MVC 基類
from src.mvc_framework.base_model import BaseBusinessModel

# 導入原有的 Worker（保持兼容）
from src.worker import RobotTestWorker


class TestExecutionBusinessModel(BaseBusinessModel, ITestCompositionModel,
                                 ITestExecutionBusinessModel, IReportGenerationModel):
    """
    整合原有 RunWidget_Model 功能的業務模型

    映射關係：
    - run_command → start_execution + 內部方法
    - generate_user_composition → _generate_user_composition
    - generate_robot_from_json → _generate_robot_from_json
    - generate_command → generate_execution_config + export_test_composition
    """

    # 信號定義（保持原有的信號）
    test_progress = Signal(dict, int)  # 測試進度信號
    test_finished = Signal(bool)  # 測試完成信號
    test_item_added = Signal(TestItem)
    test_item_removed = Signal(str)
    test_item_order_changed = Signal(list)
    all_items_cleared = Signal()
    execution_state_changed = Signal(str, ExecutionState)
    execution_progress_updated = Signal(str, ExecutionProgress)

    def __init__(self):
        super().__init__()

        # === 數據存儲（新架構） ===
        self._test_items: Dict[str, TestItem] = {}  # {item_id: TestItem}
        self._item_order: List[str] = []  # 項目順序
        self._execution_history: List[Dict[str, Any]] = []

        # === 執行狀態管理（新架構） ===
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._current_execution_id: Optional[str] = None
        self._execution_states: Dict[str, ExecutionState] = {}
        self._execution_progress: Dict[str, ExecutionProgress] = {}
        self._execution_start_times: Dict[str, datetime] = {}

        # === 原有的執行管理（保持兼容） ===
        self.thread: Optional[QThread] = None
        self.worker: Optional[RobotTestWorker] = None
        self.test_id: Optional[int] = None
        self.now_TestCase = None
        self.isRunning = False

        # === 進度觀察者 ===
        self._progress_observers: List[Callable] = []
        self._result_observers: List[Callable] = []

    # ==================== ITestCompositionModel 實現 ====================

    def add_test_item(self, item: TestItem) -> bool:
        """添加測試項目"""
        try:
            if item.id in self._test_items:
                self._logger.warning(f"Test item {item.id} already exists")
                return False

            self._test_items[item.id] = item
            self._item_order.append(item.id)

            self.test_item_added.emit(item)
            self.data_changed.emit("test_items", self.get_test_items())

            return True
        except Exception as e:
            self._logger.error(f"Failed to add test item: {e}")
            return False

    def remove_test_item(self, item_id: str) -> bool:
        """移除測試項目"""
        if item_id in self._test_items:
            del self._test_items[item_id]
            self._item_order.remove(item_id)

            self.test_item_removed.emit(item_id)
            self.data_changed.emit("test_items", self.get_test_items())

            return True
        return False

    def move_test_item(self, item_id: str, new_position: int) -> bool:
        """移動測試項目位置"""
        if item_id not in self._test_items:
            return False

        try:
            current_index = self._item_order.index(item_id)
            self._item_order.pop(current_index)
            self._item_order.insert(new_position, item_id)

            self.test_item_order_changed.emit(self._item_order.copy())
            return True
        except (ValueError, IndexError) as e:
            self._logger.error(f"Failed to move test item: {e}")
            return False

    def get_test_items(self) -> List[TestItem]:
        """獲取所有測試項目（按順序）"""
        return [self._test_items[item_id] for item_id in self._item_order
                if item_id in self._test_items]

    def clear_test_items(self) -> None:
        """清空所有測試項目"""
        items_before_clear = len(self._test_items)

        if items_before_clear > 0:
            self._save_to_history({
                "action": "clear_all",
                "items_count": items_before_clear,
                "items": self.get_test_items(),
                "timestamp": datetime.now().isoformat()
            })

        self._test_items.clear()
        self._item_order.clear()
        self._reset_execution_state()

        self.all_items_cleared.emit()
        self.data_changed.emit("test_items", [])

    def validate_composition(self) -> List[str]:
        """驗證測試組合"""
        errors = []

        if not self._test_items:
            errors.append("沒有添加任何測試項目")

        # 檢查依賴關係
        for item in self.get_test_items():
            if item.type == TestItemType.TEST_CASE:
                # 檢查測試案例的步驟
                config = item.config
                steps = config.get('steps', [])
                if not steps:
                    errors.append(f"測試案例 '{item.name}' 沒有步驟")

        return errors

    def generate_execution_config(self, test_name: str) -> ExecutionConfiguration:
        """生成執行配置（映射原有的 generate_command 功能）"""
        # 轉換測試項目為原有格式
        testcase_dict = self._convert_items_to_legacy_format()

        # 使用原有邏輯生成 user composition
        success, msg, json_path = self._generate_user_composition_internal(
            testcase_dict, test_name
        )

        if not success:
            raise ValueError(f"Failed to generate user composition: {msg}")

        # 創建執行配置
        return ExecutionConfiguration(
            test_name=test_name,
            test_items=self.get_test_items(),
            execution_mode="sequential",
            timeout=300,
            retry_count=0,
            continue_on_failure=True,
            generate_report=True,
            output_directory=os.path.join(self._get_project_root(), "report"),
            metadata={
                "user_composition_path": json_path,
                "created_at": datetime.now().isoformat()
            }
        )

    # ==================== ITestExecutionBusinessModel 實現 ====================

    def prepare_execution(self, config: ExecutionConfiguration) -> bool:
        """準備執行環境"""
        try:
            # 檢查是否有正在執行的任務
            if self.isRunning:
                self._logger.warning("Another execution is already running")
                return False

            # 驗證配置
            errors = self.validate_execution_prerequisites(config)
            if errors:
                self._logger.error(f"Execution prerequisites not met: {errors}")
                return False

            # 創建輸出目錄
            os.makedirs(config.output_directory, exist_ok=True)

            return True

        except Exception as e:
            self._logger.error(f"Failed to prepare execution: {e}")
            return False

    async def start_execution(self, config: ExecutionConfiguration) -> str:
        """
        開始執行測試（映射原有的 run_command）

        這是異步方法，但內部使用 QThread 來保持兼容性
        """
        execution_id = str(uuid.uuid4())

        try:
            # 準備執行
            if not self.prepare_execution(config):
                raise ValueError("Failed to prepare execution")

            # 更新狀態
            self._current_execution_id = execution_id
            self._update_execution_state(execution_id, ExecutionState.PREPARING)
            self.isRunning = True

            # 轉換為原有格式
            testcase_dict = self._convert_items_to_legacy_format()

            # === 執行原有的三階段流程 ===

            # 第一階段：生成 user composition JSON
            user_json_success, user_json_msg, user_json_path = \
                self._generate_user_composition_internal(testcase_dict, config.test_name)

            if not user_json_success:
                raise ValueError(f"Failed to generate user composition: {user_json_msg}")

            # 第二階段：從 JSON 生成 robot file
            robot_success, robot_msg, robot_result = \
                self._generate_robot_from_json_internal(user_json_path)

            if not robot_success:
                raise ValueError(f"Failed to generate robot file: {robot_msg}")

            robot_path, mapping_path = robot_result

            # 第三階段：在線程中執行 robot file
            await self._execute_robot_in_thread(
                execution_id, robot_path, mapping_path, config
            )

            return execution_id

        except Exception as e:
            self._logger.error(f"Failed to start execution: {e}")
            self._update_execution_state(execution_id, ExecutionState.FAILED)
            self.isRunning = False
            raise

    async def _execute_robot_in_thread(self, execution_id: str, robot_path: str,
                                       mapping_path: str, config: ExecutionConfiguration):
        """在 QThread 中執行 Robot Framework（保持原有邏輯）"""
        project_root = self._get_project_root()
        lib_path = os.path.join(project_root, "Lib")
        output_dir = config.output_directory

        # 創建 worker
        self.worker = RobotTestWorker(
            robot_path, project_root, lib_path, output_dir, mapping_path
        )

        # 連接信號（保持原有邏輯）
        self.worker.progress.connect(
            self._handle_worker_progress, Qt.ConnectionType.QueuedConnection
        )
        self.worker.finished.connect(
            lambda success: self._handle_worker_finished(execution_id, success),
            Qt.ConnectionType.QueuedConnection
        )

        # 創建線程
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # 連接線程信號
        self.thread.started.connect(self.worker.start_work)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # 更新狀態為運行中
        self._update_execution_state(execution_id, ExecutionState.RUNNING)

        # 啟動線程
        self.thread.start()

        # 等待完成（使用 asyncio）
        while self.thread and self.thread.isRunning():
            await asyncio.sleep(0.1)

    async def stop_execution(self, execution_id: str, force: bool = False) -> bool:
        """停止執行"""
        try:
            if execution_id != self._current_execution_id:
                return False

            self._update_execution_state(execution_id, ExecutionState.STOPPING)

            # 停止 worker
            if self.worker:
                # 這裡需要實現 worker 的停止方法
                pass

            # 停止線程
            if self.thread and self.thread.isRunning():
                self.thread.quit()
                if force:
                    self.thread.terminate()
                else:
                    self.thread.wait(5000)  # 等待 5 秒

            self._update_execution_state(execution_id, ExecutionState.CANCELLED)
            self.isRunning = False

            return True

        except Exception as e:
            self._logger.error(f"Failed to stop execution: {e}")
            return False

    # ==================== 原有方法的內部實現（保持兼容） ====================

    def _generate_user_composition_internal(self, test_cases: Dict, name_text: str):
        """內部方法：生成 user composition（原 generate_user_composition）"""
        try:
            project_root = self._get_project_root()
            user_dir = os.path.join(project_root, "data", "robot", "user")
            os.makedirs(user_dir, exist_ok=True)

            # 使用原有邏輯建立 composition
            composition = self._build_user_composition(test_cases, name_text)

            filename = f"user_{name_text}.json"
            json_path = os.path.join(user_dir, filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(composition, f, indent=4, ensure_ascii=False)

            return True, f"User composition generated: {json_path}", json_path

        except Exception as e:
            return False, f"Error generating user composition: {e}", ""

    def _generate_robot_from_json_internal(self, json_path: str):
        """內部方法：從 JSON 生成 robot file（原 generate_robot_from_json）"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                composition = json.load(f)

            nested_testcases = self._collect_nested_testcases(composition)
            keyword_mapping = self._build_keyword_mapping(nested_testcases, composition)
            robot_content = self._generate_robot_content_from_composition(composition)

            project_root = self._get_project_root()
            robot_dir = os.path.join(project_root, "data", "robot", "run")
            os.makedirs(robot_dir, exist_ok=True)

            output_filename = composition.get('runtime_config', {}).get(
                'output_filename', 'generated_test.robot'
            )
            robot_file_path = os.path.join(robot_dir, output_filename)
            mapping_file_path = robot_file_path.replace('.robot', '_mapping.json')

            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(keyword_mapping, f, indent=4, ensure_ascii=False)

            with open(robot_file_path, 'w', encoding='utf-8') as f:
                f.write(robot_content)

            return True, f"Robot file generated: {robot_file_path}", \
                (robot_file_path, mapping_file_path)

        except Exception as e:
            return False, f"Error generating robot file: {e}", ""

    def _convert_items_to_legacy_format(self) -> Dict[str, Any]:
        """將新格式的 TestItem 轉換為原有格式"""
        legacy_format = {}

        for item_id, item in self._test_items.items():
            legacy_format[item_id] = {
                'data': {
                    'config': item.config
                },
                'panel': None  # View 相關的不需要
            }

        return legacy_format

    @Slot(dict)
    def _handle_worker_progress(self, message: dict):
        """處理 worker 進度（保持原有邏輯）"""
        try:
            test_name = message.get('data', {}).get('test_name', '')
            self.test_id = int(self._get_id_from_testName(test_name))

            # 發送原有格式的信號
            self.test_progress.emit(message, self.test_id)

            # 同時更新新格式的進度
            if self._current_execution_id:
                progress = self._create_execution_progress(message)
                self._update_execution_progress(self._current_execution_id, progress)

        except Exception as e:
            self._logger.error(f"Error handling progress: {e}")

    def _handle_worker_finished(self, execution_id: str, success: bool):
        """處理 worker 完成"""
        try:
            # 發送原有格式的信號
            if self.test_id is not None:
                self.test_finished.emit(success)

            # 更新執行狀態
            final_state = ExecutionState.COMPLETED if success else ExecutionState.FAILED
            self._update_execution_state(execution_id, final_state)

            # 清理
            self.worker = None
            self.isRunning = False
            self._current_execution_id = None

        except Exception as e:
            self._logger.error(f"Error handling finished: {e}")

    # ==================== 其他必要的方法（從原文件複製） ====================


    def _build_user_composition(self, test_cases, name_text):
        """建立 user composition 結構"""
        # [從原文件複製相同的實現]
        libraries = set()
        individual_testcases = []

        for key, test in test_cases.items():
            config = test.get('data', {}).get('config', {})

            if category := config.get('category'):
                libraries.add(category)

            if libraries_in_setup := config.get('setup', {}).get('library'):
                libraries.update(libraries_in_setup)

            steps = config.get('steps', [])
            self._collect_libraries_from_steps(steps, libraries)

            casetype = config.get('type', '')
            if casetype == "testcase":
                testcase = self._build_individual_testcase(key, test)
            else:
                testcase = self._build_individual_keyword_testcase(key, test)

            if testcase:
                individual_testcases.append(testcase)

        composition = {
            "meta": {
                "version": "1.0",
                "type": "user_composition",
                "test_name": name_text,
                "created_by": "robot_app",
                "created_at": datetime.now().isoformat(),
                "description": f"Generated test composition: {name_text}"
            },
            "selected_settings": {
                "documentation": name_text,
                "libraries": self._build_library_configs(libraries),
                "suite_setup": None,
                "suite_teardown": None
            },
            "selected_variables": [
                {
                    "name": "TIMEOUT",
                    "value": "30s",
                    "data_type": "string"
                }
            ],
            "individual_testcases": individual_testcases,
            "keyword_dependencies": self._build_keyword_dependencies(libraries),
            "runtime_config": {
                "output_filename": f"{name_text}.robot",
                "execution_mode": "multiple_tests",
                "parallel": False,
                "tags_to_run": ["auto-generated"],
                "variables_file": None
            }
        }

        return composition


    def _collect_libraries_from_steps(self, steps, libraries):
        """遞迴收集 steps 中所有 keyword 的 keyword_category"""
        for step in steps:
            if not isinstance(step, dict):
                continue

            step_type = step.get('step_type', 'keyword')

            if step_type == 'keyword':
                # 收集 keyword 的 category
                if keyword_category := step.get('keyword_category'):
                    libraries.add(keyword_category)

            elif step_type == 'testcase':
                # 如果是嵌套的 testcase，遞迴收集其內部 steps
                nested_steps = step.get('steps', [])
                if nested_steps:
                    self._collect_libraries_from_steps(nested_steps, libraries)

    def _build_library_configs(self, libraries):
        """建立 library 配置"""
        library_configs = []

        # 庫名和文件對應
        library_files = {
            'common': 'Lib.CommonLibrary',
            'battery': 'Lib.BatteryLibrary',
            'hmi': 'Lib.HMILibrary',
            'motor': 'Lib.MotorLibrary',
            'controller': 'Lib.ControllerLibrary'
        }

        for category in sorted(libraries):
            library_name = library_files.get(category.lower())
            if library_name:
                library_configs.append({
                    "library_name": library_name,
                    "category": category,
                    "config": {}
                })

        return library_configs

    def _build_individual_keyword_testcase(self, key, test):
        """建立獨立的 keyword test case"""
        config = test.get('data', {}).get('config', {})

        # 處理參數
        parameters = {}
        for arg in config.get('arguments', []):
            arg_name = arg.get('name', '')
            default_value = arg.get('value')

            if default_value is not None:
                if arg.get('type') == 'str':
                    parameters[arg_name] = f'"{default_value}"'
                else:
                    parameters[arg_name] = str(default_value)
            else:
                parameters[arg_name] = "None"

        return {
            "test_id": key,
            "test_name": f"Execute Keyword - {config.get('name', 'Unknown')} [id]{key}",
            "type": "keyword",
            "keyword_name": config.get('name', 'Unknown'),
            "keyword_category": config.get('category', 'unknown'),
            "priority": config.get('priority', 'optional'),
            "description": config.get('description', ''),
            "parameters": parameters
        }

    def _build_individual_testcase(self, key, test):
        """建立獨立的 testcase test case"""
        config = test.get('data', {}).get('config', {})

        return {
            "test_id": key,
            "test_name": f"Execute TestCase - {config.get('name', 'Unknown')} [id]{key}",
            "type": "testcase",
            "testcase_name": config.get('name', 'Unknown'),
            "priority": config.get('priority', 'normal'),
            "description": config.get('description', ''),
            "steps": config.get('steps', [])
        }

    def _build_keyword_dependencies(self, libraries):
        """建立 keyword 依賴資訊"""
        dependencies = []

        library_mapping = {
            'common': 'Lib.CommonLibrary',
            'battery': 'Lib.BatteryLibrary',
            'hmi': 'Lib.HMILibrary',
            'motor': 'Lib.MotorLibrary',
            'controller': 'Lib.ControllerLibrary'
        }

        for category in libraries:
            library_name = library_mapping.get(category.lower())
            if library_name:
                dependencies.append({
                    "category": category,
                    "library_name": library_name,
                    "required_keywords": []  # 可以後續補充具體的 keyword 列表
                })

        return dependencies

    def _get_project_root(self):
        """獲取專案根目錄"""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_id_from_testName(self, data: str) -> str:
        """從測試名稱中提取 ID"""
        try:
            if "[id]" in data:
                id_start = data.find("[id]") + len("[id]")
                id_value = data[id_start:]
                return id_value.split()[0].strip()
            return ""
        except Exception as e:
            self._logger.error(f"Error extracting ID: {e}")
            return ""