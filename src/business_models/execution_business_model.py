# src/business_models/execution_business_model.py
"""
整合原有 RunWidget_Model 功能到新的 MVC 架構
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any
from PySide6.QtCore import Signal, QThread, Slot, Qt, QMetaObject

# 導入接口
from src.interfaces.execution_interface import (
    ITestCompositionModel, ExecutionConfiguration, TestItem, TestItemType,
    ITestExecutionBusinessModel, IReportGenerationModel, ExecutionResult,
    ExecutionProgress, ExecutionState
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
    # composition signal
    test_item_added = Signal(TestItem)
    test_item_removed = Signal(str)
    test_item_order_changed = Signal(list)
    all_items_cleared = Signal()
    # test progress, test finished 是 progress card 的訊號
    test_progress = Signal(dict, str)  # 測試進度信號
    test_finished = Signal(bool)  # 測試完成信號

    # state change
    execution_state_changed = Signal(ExecutionState, ExecutionState)  # (old_state, new_state)

    def __init__(self):
        super().__init__()

        # === 數據存儲（新架構） ===
        self._test_items: Dict[str, TestItem] = {}  # {item_id: TestItem}
        self._item_order: List[str] = []  # 項目順序
        self._execution_history: List[Dict[str, Any]] = []

        # === 執行狀態管理（新架構） ===
        self._current_execution_state: ExecutionState = ExecutionState.IDLE

        # === 原有的執行管理（保持兼容） ===
        self.thread: Optional[QThread] = None
        self.worker: Optional[RobotTestWorker] = None
        self.test_id: Optional[int, str] = None
        self.isRunning = False

    # region  ==================== ITestCompositionModel 實現，和拖拉字卡有關的 ====================

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
            print( "Move test item: ", item_id, " to position: ", new_position)
            current_index = self._item_order.index(item_id)
            self._item_order.pop(current_index)
            self._item_order.insert(new_position, item_id)
            self.reorder_test_items()
            self.test_item_order_changed.emit(self._item_order.copy())
            return True
        except (ValueError, IndexError) as e:
            self._logger.error(f"Failed to move test item: {e}")
            return False

    def reorder_test_items(self):
        """
        根據 _item_order 重新排序 _test_items 字典
        簡單直接的版本
        """
        # 創建新的有序字典
        new_test_items = {}

        # 按照 _item_order 的順序重新構建字典
        for item_id in self._item_order:
            if item_id in self._test_items:
                new_test_items[item_id] = self._test_items[item_id]

        # 替換原字典
        self._test_items = new_test_items

    def get_test_items(self) -> List[TestItem]:
        """獲取所有測試項目（按順序）"""
        return [self._test_items[item_id] for item_id in self._item_order
                if item_id in self._test_items]

    def clear_test_items(self) -> None:
        """清空所有測試項目"""
        self._test_items.clear()
        self._item_order.clear()
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
            output_directory=os.path.join(self._get_project_root(),"src", "report"),
            metadata={
                "user_composition_path": json_path,
                "created_at": datetime.now().isoformat()
            }
        )

    def get_item_order(self) -> List[str]:
        """獲取項目順序"""
        return self._item_order.copy()
    # endregion

    # region ==================== ITestExecutionBusinessModel 實現，和 run robot 有關的 ====================

    def prepare_execution(self, config: ExecutionConfiguration) -> bool:
        """準備執行環境"""
        try:
            # 檢查是否有正在執行的任務
            if self.isRunning:
                self._logger.warning("Another execution is already running")
                return False
            # 創建輸出目錄
            os.makedirs(config.output_directory, exist_ok=True)

            return True

        except Exception as e:
            self._logger.error(f"Failed to prepare execution: {e}")
            return False

    async def start_execution(self, config: ExecutionConfiguration) -> str:
        """開始執行測試（映射原有的 run_command）"""
        try:
            # 檢查當前狀態是否為 IDLE
            if self._current_execution_state != ExecutionState.IDLE:
                raise ValueError(f"Cannot start execution in {self._current_execution_state.value} state")

            # 轉換到準備狀態
            self._set_execution_state(ExecutionState.PREPARING)

            # 準備執行
            if not self.prepare_execution(config):
                self._set_execution_state(ExecutionState.FAILED)
                raise ValueError("Failed to prepare execution")

            # 轉換為原有格式
            testcase_dict = self._convert_items_to_legacy_format()

            # 第一階段：生成 user composition JSON
            user_json_success, user_json_msg, user_json_path = \
                self._generate_user_composition_internal(testcase_dict, config.test_name)

            if not user_json_success:
                self._set_execution_state(ExecutionState.FAILED)
                raise ValueError(f"Failed to generate user composition: {user_json_msg}")

            # 檢查是否在準備過程中被停止
            if self._current_execution_state == ExecutionState.STOPPING:
                self._set_execution_state(ExecutionState.CANCELLED)
                return "cancelled"

            # 第二階段：從 JSON 生成 robot file
            robot_success, robot_msg, robot_result = \
                self._generate_robot_from_json_internal(user_json_path)

            if not robot_success:
                self._set_execution_state(ExecutionState.FAILED)
                raise ValueError(f"Failed to generate robot file: {robot_msg}")

            robot_path, mapping_path = robot_result

            # 再次檢查是否被停止
            if self._current_execution_state == ExecutionState.STOPPING:
                self._set_execution_state(ExecutionState.CANCELLED)
                return "cancelled"

            # 第三階段：轉換到執行狀態
            self._set_execution_state(ExecutionState.RUNNING)

            # 在線程中執行
            await self._execute_robot_in_thread(robot_path, mapping_path, config)

            return "success"

        except Exception as e:
            self._logger.error(f"Failed to start execution: {e}")
            # 只有在非 STOPPING 狀態才設為 FAILED
            if self._current_execution_state != ExecutionState.STOPPING:
                self._set_execution_state(ExecutionState.FAILED)
            raise

    async def stop_execution(self, force: bool = False) -> bool:
        """停止執行 - 完整實現"""
        try:
            # 檢查當前狀態是否可以停止
            if self._current_execution_state not in [ExecutionState.PREPARING, ExecutionState.RUNNING]:
                self._logger.warning(f"Cannot stop execution in {self._current_execution_state.value} state")
                return False

            self._logger.info(f"Stopping execution (force={force})")

            # 轉換到停止中狀態
            self._set_execution_state(ExecutionState.STOPPING)

            stop_success = True

            # === 第一階段：通知 Worker 停止 ===
            if self.worker:
                try:
                    self._logger.info("Requesting worker to stop...")
                    # 通過 Qt 信號安全調用 Worker 的停止方法
                    QMetaObject.invokeMethod(
                        self.worker,
                        "stop_work",
                        Qt.ConnectionType.QueuedConnection
                    )

                    # 等待一段時間讓 Worker 自己停止
                    if not force:
                        import asyncio
                        await asyncio.sleep(2.0)  # 給 Worker 2 秒時間自己停止

                except Exception as e:
                    self._logger.error(f"Failed to request worker stop: {e}")
                    stop_success = False

            # === 第二階段：處理線程 ===
            if self.thread and self.thread.isRunning():
                try:
                    self._logger.info("Stopping thread...")

                    if force:
                        # 強制模式：直接終止
                        self.thread.terminate()
                        if not self.thread.wait(3000):  # 等待3秒
                            self._logger.error("Failed to terminate thread")
                            stop_success = False
                    else:
                        # 優雅模式：先 quit，再 terminate
                        self.thread.quit()
                        if not self.thread.wait(5000):  # 等待5秒
                            self._logger.warning("Thread quit timeout, forcing termination")
                            self.thread.terminate()
                            if not self.thread.wait(3000):  # 再等待3秒
                                self._logger.error("Failed to force terminate thread")
                                stop_success = False

                except Exception as e:
                    self._logger.error(f"Failed to stop thread: {e}")
                    stop_success = False

            # === 第三階段：清理資源 ===
            try:
                # 清理 worker 和 thread 引用
                if self.worker:
                    # Worker 會在 thread 結束時自動 deleteLater
                    self.worker = None

                if self.thread:
                    # Thread 會在結束時自動 deleteLater
                    self.thread = None

                self._logger.info("Resources cleaned up")

            except Exception as e:
                self._logger.error(f"Failed to cleanup resources: {e}")

            # === 第四階段：設置最終狀態 ===
            if stop_success:
                self._set_execution_state(ExecutionState.CANCELLED)
                self._logger.info("Execution stopped successfully")
                return True
            else:
                self._set_execution_state(ExecutionState.FAILED)
                self._logger.error("Failed to stop execution")
                return False

        except Exception as e:
            self._logger.error(f"Exception during stop execution: {e}")
            self._set_execution_state(ExecutionState.FAILED)
            return False

    def generate_testcase(self, name_text, category, priority, description) -> str:
        testcase_dict = self._convert_items_to_legacy_format()
        self.generate_command( testcase_dict, name_text, category, priority, description)

    def import_testcase(self, file_path):
        pass

    async def _execute_robot_in_thread(self, robot_path: str,
                                   mapping_path: str, config: ExecutionConfiguration):
        """在 QThread 中執行 Robot Framework（保持原有邏輯）"""
        try:
            project_root = self._get_project_root()
            lib_path = os.path.join(project_root, "Lib")
            output_dir = config.output_directory

            # 創建 worker
            self.worker = RobotTestWorker(
                robot_path, project_root, lib_path, output_dir, mapping_path
            )

            # 連接信號
            self.worker.progress.connect(
                self._handle_worker_progress, Qt.ConnectionType.DirectConnection
            )
            self.worker.finished.connect(
                self._handle_worker_finished,
                Qt.ConnectionType.DirectConnection
            )

            # 如果 worker 有 error 信號，連接錯誤處理
            if hasattr(self.worker, 'error'):
                self.worker.error.connect(self._handle_worker_error)

            # 創建線程
            self.thread = QThread()
            self.worker.moveToThread(self.thread)

            # 連接線程信號
            self.thread.started.connect(self.worker.start_work)
            self.thread.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.worker.finished.connect(self.thread.quit)

            # 啟動線程
            self.thread.start()

        except Exception as e:
            self._logger.error(f"Failed to execute robot in thread: {e}")
            self._set_execution_state(ExecutionState.FAILED)
            raise


    def _set_execution_state(self, new_state: ExecutionState) -> None:
        """統一的執行狀態設置方法 - 唯一修改狀態的入口"""
        old_state = self._current_execution_state

        if old_state == new_state:
            return  # 狀態沒有變化，不需要通知

        # 定義合法的狀態轉換（根據狀態機圖）
        valid_transitions = {
            ExecutionState.IDLE: [ExecutionState.PREPARING],
            ExecutionState.PREPARING: [ExecutionState.RUNNING, ExecutionState.FAILED, ExecutionState.STOPPING],
            ExecutionState.RUNNING: [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.STOPPING],
            ExecutionState.STOPPING: [ExecutionState.CANCELLED, ExecutionState.FAILED],
            ExecutionState.COMPLETED: [ExecutionState.IDLE],
            ExecutionState.FAILED: [ExecutionState.IDLE],
            ExecutionState.CANCELLED: [ExecutionState.IDLE]
        }

        # 檢查轉換是否合法
        if new_state not in valid_transitions.get(old_state, []):
            self._logger.warning(f"Invalid state transition: {old_state.value} → {new_state.value}")
            return

        # 更新狀態
        self._current_execution_state = new_state

        # 同步 isRunning（保持兼容性）
        self.isRunning = new_state in [ExecutionState.RUNNING]

        # 記錄日誌
        self._logger.info(f"Execution state changed: {old_state.value} → {new_state.value}")

        # 發出信號通知
        self.execution_state_changed.emit(old_state, new_state)

        # 自動重置到 IDLE（對於終態）

        if new_state in [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED]:
            self._safe_set_idle()

    def _safe_set_idle(self):
        """安全地將狀態重置為 IDLE - 使用 QMetaObject"""
        try:
            # 使用 QMetaObject.invokeMethod 在主線程的事件隊列中執行
            QMetaObject.invokeMethod(
                self,
                "_reset_to_idle_slot",
                Qt.ConnectionType.QueuedConnection
            )

        except Exception as e:
            self._logger.error(f"Failed to schedule IDLE reset: {e}")

    @Slot()
    def _reset_to_idle_slot(self):
        """重置狀態到 IDLE 的 Slot"""
        try:
            self._logger.info("[QMetaObject] Attempting to change to IDLE")

            # 檢查當前狀態是否為終態
            if self._current_execution_state in [ExecutionState.COMPLETED, ExecutionState.FAILED,
                                                 ExecutionState.CANCELLED]:
                # 直接修改狀態，避免遞迴調用 _set_execution_state
                old_state = self._current_execution_state
                self._current_execution_state = ExecutionState.IDLE
                self.isRunning = False

                self._logger.info(f"Execution state changed: {old_state.value} → idle")
                self.execution_state_changed.emit(old_state, ExecutionState.IDLE)
            else:
                self._logger.warning(f"Cannot reset to IDLE from {self._current_execution_state.value}")

        except Exception as e:
            self._logger.error(f"Failed to reset to IDLE: {e}")

    def __del__(self):
        print("[DEBUG] Self destroyed before timer triggered")
    # endregion

    # region 根據 UI 介面字卡設定，建立對應的 json  路徑 : data/robot/user/user_composition_test_name.json
    def _generate_user_composition_internal(self, test_cases: Dict, name_text: str):
        """內部方法：生成 user composition（原 generate_user_composition）"""
        try:
            name_text = self._sanitize_filename( name_text )
            project_root = self._get_project_root()
            user_dir = os.path.join(project_root, "data", "robot", "user")
            os.makedirs(user_dir, exist_ok=True)

            composition = self._build_user_composition(test_cases, name_text)

            filename = f"user_{name_text}.json"
            json_path = os.path.join(user_dir, filename)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(composition, f, indent=4, ensure_ascii=False)

            return True, f"User composition generated: {json_path}", json_path

        except Exception as e:
            return False, f"Error generating user composition: {e}", ""

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理檔名，移除或替換不能出現在檔名中的字符

        Args:
            filename: 原始檔名

        Returns:
            str: 清理後的安全檔名
        """
        import re

        if not filename:
            return "untitled"

        # 1. 替換不允許的字符為下劃線
        # Windows 和 Unix 系統都不允許的字符: < > : " | ? * \ /
        forbidden_chars = r'[<>:"|?*\\/]'
        clean_name = re.sub(forbidden_chars, '_', filename)

        # 2. 替換空格為下劃線
        clean_name = clean_name.replace(' ', '_')

        # 3. 移除控制字符 (ASCII 0-31)
        clean_name = re.sub(r'[\x00-\x1f]', '', clean_name)

        # 4. 替換多個連續的下劃線為單個下劃線
        clean_name = re.sub(r'_+', '_', clean_name)

        # 5. 移除開頭和結尾的下劃線和點號
        clean_name = clean_name.strip('_.')

        # 6. 檢查是否為 Windows 保留名稱 (不區分大小寫)
        windows_reserved = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        if clean_name.upper() in windows_reserved:
            clean_name = f"_{clean_name}"

        # 7. 確保檔名不為空，且長度合理 (Windows 限制為 255 字符，但我們設為 100 以保險)
        if not clean_name:
            clean_name = "untitled"
        elif len(clean_name) > 100:
            clean_name = clean_name[:100].rstrip('_.')

        return clean_name

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
                testcase = self._build_individual_keyword(key, test)

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

    def _build_individual_keyword(self, key, test):
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

    # endregion

    # region 根據生成的 json 轉譯成 .robot 檔案, 路徑 : data/robot/run/generated_test.robot
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

    """建立 keyword 映射關係 路徑 : data/robot/run/generated_test_mapping.json """
    def _build_keyword_mapping(self, nested_testcases, composition):

        mapping = {
            'testcase_to_keyword': {},  # testcase_id -> keyword_name
            'keyword_to_testcase': {},  # keyword_name -> testcase_info
            'nested_structure': {}  # 完整的嵌套結構
        }

        # 處理嵌套的 testcases
        for testcase_id, testcase_data in nested_testcases.items():
            keyword_name = testcase_data['keyword_name']

            mapping['testcase_to_keyword'][testcase_id] = keyword_name
            mapping['keyword_to_testcase'][keyword_name] = {
                'testcase_id': testcase_id,
                'testcase_name': f"[Testcase] {testcase_data['testcase_name']}",
                'description': testcase_data['description']
            }

        # 建立嵌套結構映射
        for testcase in composition.get('individual_testcases', []):
            if testcase.get('type') == 'testcase':
                test_id = testcase.get('test_id')
                mapping['nested_structure'][test_id] = self._map_testcase_structure(
                    testcase.get('steps', []), nested_testcases
                )

        return mapping
    def _map_testcase_structure(self, steps, nested_testcases):
        """遞迴映射 testcase 結構"""
        mapped_steps = []

        for step in steps:
            if step.get('step_type') == 'testcase':
                testcase_id = step.get('testcase_id')
                if testcase_id in nested_testcases:
                    mapped_steps.append({
                        'type': 'nested_testcase',
                        'original_testcase_id': testcase_id,
                        'generated_keyword_name': nested_testcases[testcase_id]['keyword_name'],
                        'testcase_name': f"[Testcase] {step.get('testcase_name')}",
                        'inner_steps': self._map_testcase_structure(step.get('steps', []), nested_testcases)
                    })
            elif step.get('step_type') == 'keyword':
                mapped_steps.append({
                    'type': 'keyword',
                    'keyword_name': step.get('keyword_name'),
                    'keyword_category': step.get('keyword_category')
                })

        return mapped_steps


    """從 composition 生成 Robot Framework 內容 - 支援嵌套 testcase 轉 keyword"""
    def _generate_robot_content_from_composition(self, composition):
        robot_content = []

        # 生成 Settings 區段
        robot_content.extend(self._generate_settings_from_composition(composition))
        robot_content.append("")

        # 生成 Variables 區段
        robot_content.extend(self._generate_variables_from_composition(composition))
        robot_content.append("")

        # 收集所有嵌套的 testcases 並生成 keywords
        nested_testcases = self._collect_nested_testcases(composition)

        # 生成 Test Cases 區段
        robot_content.append("*** Test Cases ***")
        robot_content.extend(self._generate_testcase_from_composition(composition, nested_testcases))

        # 如果有嵌套的 testcases，生成 Keywords 區段
        if nested_testcases:
            robot_content.append("")
            robot_content.append("*** Keywords ***")
            robot_content.extend(self._generate_keywords_from_nested_testcases(nested_testcases))

        return '\n'.join(robot_content)
    def _generate_settings_from_composition(self, composition):
        """從 composition 生成 Settings 區段"""
        content = ["*** Settings ***"]

        settings = composition.get('selected_settings', {})
        content.append(f"Documentation    {settings.get('documentation', 'Generated Test')}")

        # 添加 libraries
        for lib in settings.get('libraries', []):
            content.append(f"Library    {lib['library_name']}")

        return content
    def _generate_variables_from_composition(self, composition):
        """從 composition 生成 Variables 區段"""
        content = ["*** Variables ***"]

        for var in composition.get('selected_variables', []):
            content.append(f"${{{var['name']}}}    {var['value']}")

        return content
    def _collect_nested_testcases(self, composition):
        """收集所有嵌套的 testcases，準備轉換為 keywords"""
        nested_testcases = {}

        def collect_from_steps(steps, collected_testcases):
            """遞迴收集步驟中的 testcase"""
            for step in steps:
                if step.get('step_type') == 'testcase':
                    testcase_id = step.get('testcase_id')
                    testcase_name = step.get('testcase_name', 'Unknown')

                    # 生成唯一的 keyword 名稱
                    keyword_name = self._generate_keyword_name(testcase_name, testcase_id)

                    collected_testcases[testcase_id] = {
                        'keyword_name': keyword_name,
                        'testcase_name': testcase_name,
                        'testcase_id': testcase_id,
                        'description': step.get('description', ''),
                        'steps': step.get('steps', [])
                    }

                    # 遞迴收集內部的 testcase
                    collect_from_steps(step.get('steps', []), collected_testcases)

        # 從所有 individual_testcases 開始收集
        for testcase in composition.get('individual_testcases', []):
            if testcase.get('type') == 'testcase':
                collect_from_steps(testcase.get('steps', []), nested_testcases)

        return nested_testcases
    def _generate_keyword_name(self, testcase_name, testcase_id):
        """生成唯一的 keyword 名稱"""
        # 清理 testcase_name，移除特殊字符
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', testcase_name)  # 支援中文
        return f"Execute_Testcase_{safe_name}_{testcase_id}"
    def _generate_testcase_from_composition(self, composition, nested_testcases):
        """從 composition 生成 Test Cases 內容 - 支援 testcase 轉 keyword"""
        content = []

        # 處理每個獨立的 test case
        for testcase in composition.get('individual_testcases', []):
            if testcase['type'] == 'keyword':
                content.extend(self._generate_keyword_testcase(testcase))
            elif testcase['type'] == 'testcase':
                content.extend(self._generate_testcase_testcase_with_keywords(testcase, nested_testcases))

        return content
    def _generate_keywords_from_nested_testcases(self, nested_testcases):
        """從嵌套的 testcases 生成 Keywords 區段"""
        content = []

        for testcase_data in nested_testcases.values():
            keyword_name = testcase_data['keyword_name']
            description = testcase_data['description']
            steps = testcase_data['steps']

            # Keyword 名稱
            content.append(keyword_name)

            # Documentation

            # Documentation
            if description:
                description = description.replace('\n', ' ')
                content.append(f"    [Documentation]    {description}")

            # 處理步驟
            for step in steps:
                step_content = self._process_step_for_keyword(step, nested_testcases)
                content.extend(step_content)

            content.append("")  # 添加空行分隔

        return content
    def _generate_testcase_testcase_with_keywords(self, testcase, nested_testcases):
        """生成 testcase 類型的 test case - 支援 keyword 調用"""
        content = []

        # Test case 名稱
        content.append(testcase['test_name'])

        # Tags
        content.append(f"    [Tags]    auto-generated    {testcase['priority']}")

        # Documentation
        if testcase['description']:
            description = testcase['description']
            description = description.replace('\n', ' ')
            content.append(f"    [Documentation]    {description}")

        # 處理步驟 - 使用新的處理方法
        for step in testcase.get('steps', []):
            step_content = self._process_step_for_keyword(step, nested_testcases)
            content.extend(step_content)

        content.append("")  # 添加空行分隔
        return content
    def _process_step_for_keyword(self, step, nested_testcases):
        """處理 keyword 內的步驟，支援嵌套 testcase 調用"""
        content = []
        indent = "    "  # 固定使用 4 個空格縮排

        step_type = step.get('step_type', 'keyword')

        if step_type == 'keyword':
            # 處理 keyword 類型
            action = step.get('keyword_name', '')
            params = step.get('parameters', {})

            if params:
                param_str = '    '.join(f"{k}={v}" for k, v in params.items())
                content.append(f"{indent}{action}    {param_str}")
            else:
                content.append(f"{indent}{action}")

        elif step_type == 'testcase':
            # 處理嵌套的 testcase - 調用對應的 keyword
            testcase_id = step.get('testcase_id')
            if testcase_id in nested_testcases:
                keyword_name = nested_testcases[testcase_id]['keyword_name']
                content.append(f"{indent}{keyword_name}")
            else:
                # 備用方案：如果找不到對應的 keyword，使用註解
                testcase_name = step.get('testcase_name', 'Unknown Testcase')
                content.append(f"{indent}# ERROR: Missing keyword for testcase: {testcase_name}")

        else:
            # 處理其他類型或向下兼容舊格式
            step_name = step.get('step_name', step.get('action', step.get('name', 'Unknown Step')))
            content.append(f"{indent}{step_name}")

        return content
    def _generate_keyword_testcase(self, testcase):
        """生成 keyword 類型的 test case"""
        content = []

        # Test case 名稱
        content.append(testcase['test_name'])

        # Tags
        content.append(f"    [Tags]    auto-generated    {testcase['priority']}")

        # Documentation
        if testcase['description']:
            description = testcase['description']
            description = description.replace('\n', ' ')
            content.append(f"    [Documentation]    {description}")

        # Keyword 呼叫
        keyword_name = testcase['keyword_name']
        parameters = testcase.get('parameters', {})

        if parameters:
            param_list = []
            for param_name, param_value in parameters.items():
                param_list.append(f"{param_name}={param_value}")
            content.append(f"    {keyword_name}    {'    '.join(param_list)}")
        else:
            content.append(f"    {keyword_name}")

        content.append("")  # 添加空行分隔
        return content

    # endregion

    #region export cmd

    def generate_command(self, testcase, name_text, category, priority, description):
        """生成測試指令並保存為 JSON 檔案 (保留原有功能)"""
        # print("Click Generate Command")
        # 使用新的 generate_user_composition 方法
        success, msg, path = self._generate_user_composition_internal(testcase, name_text)

        if success:
            self.generate_cards_from_json(path, category, priority, description)

        else:
            print(f"Error: {msg}")

    def generate_cards_from_json(self, user_composition_path, category, priority, description):
        """從 user composition JSON 生成 testcase card"""
        import time
        from datetime import datetime

        try:
            # 讀取 user composition
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            with open(user_composition_path, 'r', encoding='utf-8') as f:
                composition = json.load(f)

            # 提取基本資訊
            meta = composition.get('meta', {})
            test_name = meta.get('test_name', 'Unnamed_Test')

            # 生成唯一的 testcase ID
            testcase_id = f"user_testcase_{int(time.time())}"

            # 轉換 individual_testcases 為 steps 格式
            steps = []
            dependencies = {
                "libraries": set(),
                "keywords": set()
            }

            for item in composition.get('individual_testcases', []):
                if item.get('type') == 'keyword':
                    # 處理 keyword 類型
                    step = {
                        "step_type": "keyword",
                        "keyword_id": item.get('test_id'),
                        "keyword_name": item.get('keyword_name'),
                        "keyword_category": item.get('keyword_category'),
                        "parameters": item.get('parameters', {}),
                        "description": item.get('description', '')
                    }
                    steps.append(step)

                    # 收集依賴
                    if keyword_category := item.get('keyword_category'):
                        dependencies["libraries"].add(keyword_category)
                    if keyword_name := item.get('keyword_name'):
                        dependencies["keywords"].add(keyword_name)

                elif item.get('type') == 'testcase':
                    # 處理 testcase 類型 - 保持 testcase 結構，不展開
                    testcase_name = item.get('testcase_name', 'Unknown Testcase')
                    testcase_steps = item.get('steps', [])

                    # 收集這個 testcase 內步驟的依賴
                    self._collect_testcase_dependencies(testcase_steps, dependencies)

                    # 創建 testcase 類型的步驟
                    testcase_step = {
                        "step_type": "testcase",
                        "testcase_id": item.get('test_id'),
                        "testcase_name": testcase_name,
                        "description": item.get('description', ''),
                        "priority": item.get('priority', 'normal'),
                        "steps": testcase_steps  # 保留完整的 steps 陣列
                    }
                    steps.append(testcase_step)

            # 計算預估時間（每個步驟約2分鐘）
            estimated_time = max(1, len(steps) * 2)

            # 建立 testcase card 格式
            testcase_card = {
                testcase_id: {
                    "data": {
                        "config": {
                            "type": "testcase",
                            "name": test_name,
                            "description": description,
                            "category": category,
                            "priority": priority,
                            "estimated_time": f"{estimated_time}min",
                            "created_by": meta.get('created_by', 'user'),
                            "created_at": meta.get('created_at', datetime.now().isoformat()),
                            "steps": steps,
                            "dependencies": {
                                "libraries": list(dependencies["libraries"]),
                                "keywords": list(dependencies["keywords"])
                            },
                            "metadata": {
                                "source_composition": os.path.basename(user_composition_path),
                                "total_steps": len(steps)
                            }
                        }
                    }
                }
            }

            # 確定保存路徑
            cards_dir = os.path.join(project_root, "data", "robot", "cards")
            os.makedirs(cards_dir, exist_ok=True)

            user_testcases_path = os.path.join(cards_dir, f"{category}-test-case.json")

            # 讀取現有的 user testcases（如果存在）
            existing_testcases = {}
            if os.path.exists(user_testcases_path):
                try:
                    with open(user_testcases_path, 'r', encoding='utf-8') as f:
                        existing_testcases = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    print("Warning: 無法讀取現有的 user_testcases.json，將創建新檔案")
                    existing_testcases = {}

            # 合併新的 testcase
            existing_testcases.update(testcase_card)

            # 保存更新後的檔案
            with open(user_testcases_path, 'w', encoding='utf-8') as f:
                json.dump(existing_testcases, f, indent=4, ensure_ascii=False)

            success_msg = f"Testcase '{test_name}' 已保存到 cards (ID: {testcase_id})"
            # print(success_msg)

            return True, success_msg, testcase_id

        except FileNotFoundError:
            error_msg = f"找不到檔案: {user_composition_path}"
            print(f"Error: {error_msg}")
            return False, error_msg, None

        except json.JSONDecodeError as e:
            error_msg = f"JSON 格式錯誤: {e}"
            print(f"Error: {error_msg}")
            return False, error_msg, None

        except Exception as e:
            error_msg = f"生成 testcase card 時發生錯誤: {e}"
            print(f"Error: {error_msg}")
            return False, error_msg, None

    def _collect_testcase_dependencies(self, testcase_steps, dependencies):
        """收集 testcase 內步驟的依賴資訊"""
        for step in testcase_steps:
            if not isinstance(step, dict):
                continue

            step_type = step.get('step_type', step.get('type', 'unknown'))

            if step_type == 'keyword':
                # 收集 keyword 的依賴
                if keyword_category := step.get('keyword_category'):
                    dependencies["libraries"].add(keyword_category)
                if keyword_name := step.get('keyword_name'):
                    dependencies["keywords"].add(keyword_name)

            elif step_type == 'testcase':
                # 如果有嵌套的 testcase，遞歸收集依賴
                nested_steps = step.get('steps', [])
                if nested_steps:
                    self._collect_testcase_dependencies(nested_steps, dependencies)

    #endregion

    def _get_project_root(self):
        """獲取專案根目錄"""
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_id_from_testName(self, data: str) -> str:
        """
        從 testname 取得 id :
        testname : Execute TestCase - Test HMI Assist Level Button click [id]1578378060608
        id : 1578378060608
        """
        try:
            if "[id]" in data:
                id_start = data.find("[id]") + len("[id]")
                id_value = data[id_start:]
                return id_value.split()[0].strip()
            return ""
        except Exception as e:
            self._logger.error(f"Error extracting ID: {e}")
            return ""

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
            # 檢查是否在執行狀態
            if self._current_execution_state != ExecutionState.RUNNING:
                self._logger.warning(f"Received progress in {self._current_execution_state.value} state")
                return

            test_name = message.get('data', {}).get('test_name', '')
            self.test_id = self._get_id_from_testName(test_name)
            self.test_progress.emit(message, self.test_id)

        except Exception as e:
            self._logger.error(f"Error handling progress: {e}")

    @Slot(bool)
    def _handle_worker_finished(self, success: bool):
        """處理 worker 完成"""
        try:
            # 根據當前狀態和結果決定目標狀態
            if self._current_execution_state == ExecutionState.STOPPING:
                # 被使用者停止
                self._set_execution_state(ExecutionState.CANCELLED)
            elif success:
                # 正常完成
                self._set_execution_state(ExecutionState.COMPLETED)
            else:
                # 執行失敗
                self._set_execution_state(ExecutionState.FAILED)

            # 發出完成信號
            self.test_finished.emit(success)

            self._logger.info(f"Worker finished with {'success' if success else 'failure'}")

        except Exception as e:
            self._logger.error(f"Error handling worker finished: {e}")
            self._set_execution_state(ExecutionState.FAILED)

    @Slot(str)
    def _handle_worker_error(self, error_message: str):
        """處理 worker 錯誤"""
        self._logger.error(f"Worker error: {error_message}")

        # 只有在非 STOPPING 狀態才設為 FAILED
        if self._current_execution_state != ExecutionState.STOPPING:
            self._set_execution_state(ExecutionState.FAILED)

    def get_execution_state(self) -> ExecutionState:
        """獲取當前執行狀態"""
        return self._current_execution_state

    def can_start_execution(self) -> bool:
        """檢查是否可以開始執行"""
        return self._current_execution_state == ExecutionState.IDLE

    def can_stop_execution(self) -> bool:
        """檢查是否可以停止執行"""
        return self._current_execution_state in [ExecutionState.PREPARING, ExecutionState.RUNNING]




