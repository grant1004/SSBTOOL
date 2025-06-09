from datetime import datetime
from PySide6.QtCore import Signal, QObject, Slot, Qt, QThread
from numpy import long
import json
import os
import time

from src.Container import singleton
from src.worker import RobotTestWorker


@singleton
class RunWidget_Model(QObject):
    test_progress = Signal(dict, long)  # 測試進度信號, test id
    test_finished = Signal(bool)  # 測試完成信號, test id

    def __init__(self):
        super().__init__()
        self.thread = None
        self.test_id = None
        self.now_TestCase = None
        self.isRunning = None
        self.worker = None

    def run_command(self, testcase, name_text):
        """執行測試流程：testcase → user JSON → robot file → 執行"""
        if len(testcase) == 0:
            print("No test case selected")
            return

        self.isRunning = True
        self.now_TestCase = testcase

        # 第一階段：生成 user composition JSON
        user_json_success, user_json_msg, user_json_path = self.generate_user_composition(testcase, name_text)
        if not user_json_success:
            print(f"Failed to generate user composition: {user_json_msg}")
            return

        # 第二階段：從 JSON 生成 robot file
        robot_success, robot_msg, robot_result = self.generate_robot_from_json(user_json_path)
        if not robot_success:
            print(f"Failed to generate robot file: {robot_msg}")
            return

        robot_path, mapping_path = robot_result  # **解包映射路徑**

        # 第三階段：執行 robot file
        if robot_success:
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            lib_path = os.path.join(project_root, "Lib")
            output_dir = os.path.join(project_root, "report")

            # 創建並設置新的 worker thread 用來執行 .robot
            self.worker = RobotTestWorker(robot_path, project_root, lib_path, output_dir, mapping_path)

            # 連接信號
            self.worker.progress.connect(self.handle_progress, Qt.ConnectionType.DirectConnection)
            self.worker.finished.connect(self.handle_finished, Qt.ConnectionType.DirectConnection)

            # 創建新的線程
            self.thread = QThread()

            # 將 worker 移動到線程
            self.worker.moveToThread(self.thread)

            # *** 修正：連接線程啟動信號到 worker 的槽函數，而不是手動調用 run() ***
            self.thread.started.connect(self.worker.start_work)

            # 添加線程完成處理
            def on_thread_finished():
                # print(f"[THREAD] Robot test execution thread finished\n")
                self.isRunning = False

            self.thread.finished.connect(on_thread_finished)

            # *** 修正：當 worker 完成時，退出線程 ***
            self.worker.finished.connect(self.thread.quit)

            # *** 修正：當線程退出時，清理資源 ***
            self.thread.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # 啟動線程
            # print(f"[MAIN] Starting Robot test execution...")
            self.thread.start()

    def generate_user_composition(self, test_cases, name_text):
        """第一階段：將 testcase 資料轉換為 user composition JSON"""
        try:
            # 建立專案根目錄路徑
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            user_dir = os.path.join(project_root, "data", "robot", "user")
            os.makedirs(user_dir, exist_ok=True)

            # 分析 test_cases 來建立 composition
            composition = self._build_user_composition(test_cases, name_text)

            # 生成檔案路徑
            filename = f"user_{name_text}.json"
            json_path = os.path.join(user_dir, filename)

            # 寫入 JSON 檔案
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(composition, f, indent=4, ensure_ascii=False)

            return True, f"User composition generated: {json_path}", json_path

        except Exception as e:
            return False, f"Error generating user composition: {e}", ""

    def _build_user_composition(self, test_cases, name_text):
        """建立 user composition 結構"""
        libraries = set()
        individual_testcases = []

        # 分析所有 test cases 收集資訊
        for key, test in test_cases.items():
            config = test.get('data', {}).get('config', {})
            # print( "Config : " + str(config) )

            # 收集 libraries - 原有邏輯
            if category := config.get('category'):
                libraries.add(category)

            if libraries_in_setup := config.get('setup', {}).get('library'):
                libraries.update(libraries_in_setup)

            # 🔥 新增：收集 steps 中每個 keyword 的 keyword_category
            steps = config.get('steps', [])
            self._collect_libraries_from_steps(steps, libraries)

            # 建立獨立的 test case（每個 keyword 一個 test case）
            casetype = config.get('type', '')
            if casetype == "testcase":
                # 這是一個 testcase，建立獨立的 test case
                testcase = self._build_individual_testcase(key, test)
            else:
                # 這是一個 keyword，建立獨立的 test case
                testcase = self._build_individual_keyword_testcase(key, test)

            if testcase:
                individual_testcases.append(testcase)

        # 建立 user composition 結構
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

    def generate_robot_from_json(self, json_path):
        """第二階段：從 user composition JSON 生成 Robot Framework 檔案"""
        try:
            # 讀取 user composition

            with open(json_path, 'r', encoding='utf-8') as f:
                composition = json.load(f)

            print(f"user composition: {composition}")
            # 收集嵌套 testcases
            nested_testcases = self._collect_nested_testcases(composition)

            # **新增：生成映射關係**
            keyword_mapping = self._build_keyword_mapping(nested_testcases, composition)

            # 生成 robot 內容
            robot_content = self._generate_robot_content_from_composition(composition)

            # 建立輸出路徑
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            robot_dir = os.path.join(project_root, "data", "robot", "run")
            os.makedirs(robot_dir, exist_ok=True)

            # 生成檔案路徑
            output_filename = composition.get('runtime_config', {}).get('output_filename', 'generated_test.robot')
            robot_file_path = os.path.join(robot_dir, output_filename)

            # **新增：保存映射關係**
            mapping_file_path = robot_file_path.replace('.robot', '_mapping.json')
            with open(mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(keyword_mapping, f, indent=4, ensure_ascii=False)

            # 寫入檔案
            with open(robot_file_path, 'w', encoding='utf-8') as f:
                f.write(robot_content)

            return True, f"Robot file generated: {robot_file_path}", (robot_file_path, mapping_file_path)

        except Exception as e:
            return False, f"Error generating robot file from JSON: {e}", ""

    def _build_keyword_mapping(self, nested_testcases, composition):
        """建立 keyword 映射關係"""
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

    def _generate_robot_content_from_composition(self, composition):
        """從 composition 生成 Robot Framework 內容 - 支援嵌套 testcase 轉 keyword"""
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
            if description:
                content.append(f"    [Documentation]    {description}")

            # 處理步驟
            for step in steps:
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

    def _process_step_flat(self, step):
        """扁平化處理步驟，所有步驟都使用相同縮排層級"""
        content = []
        indent = "    "  # 固定使用 4 個空格縮排

        step_type = step.get('step_type', 'keyword')

        if step_type == 'keyword':
            # 處理 keyword 類型
            action = step.get('keyword_name', '')
            params = step.get('parameters', {})

            if params:
                param_str = '    '.join(f"{k}=${{{v}}}" for k, v in params.items())
                content.append(f"{indent}{action}    {param_str}")
            else:
                content.append(f"{indent}{action}")

        elif step_type == 'testcase':
            # 處理 testcase 類型 - 扁平化展開其內部步驟
            testcase_name = step.get('testcase_name', 'Unknown Testcase')

            # 添加註解說明這是一個嵌套的 testcase
            content.append(f"{indent}# === Begin Testcase: {testcase_name} ===")

            # 如果有描述，也加入註解
            if description := step.get('description'):
                content.append(f"{indent}# Description: {description}")

            # 遞迴處理內部步驟，但保持相同縮排層級
            for inner_step in step.get('steps', []):
                inner_content = self._process_step_flat(inner_step)
                content.extend(inner_content)

            # 添加結束註解
            content.append(f"{indent}# === End Testcase: {testcase_name} ===")

        else:
            # 處理其他類型或向下兼容舊格式
            step_name = step.get('step_name', step.get('action', step.get('name', 'Unknown Step')))

            # 如果有參數，處理參數
            params = step.get('parameters', step.get('params', {}))
            if params:
                param_str = '    '.join(f"{k}=${{{v}}}" for k, v in params.items())
                content.append(f"{indent}{step_name}    {param_str}")
            else:
                content.append(f"{indent}{step_name}")

        return content

    @Slot(dict)
    def handle_progress(self, message):
        # print(f"[MODEL] 🔥 Received: {message['type']}")
        try:
            test_name = message.get('data', {}).get('test_name', '')
            print(f"[MODEL] 🔍 Extracting ID from: {test_name}")

            self.test_id = int(self._get_id_from_testName(test_name))
            print(f"[MODEL] ✅ Extracted test_id: {self.test_id}")

            # print(f"[MODEL] 📤 Emitting to UI...")
            self.test_progress.emit(message, self.test_id)
            # print(f"[MODEL] ✅ Emitted to UI successfully")

        except Exception as e:
            print(f"[MODEL] ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    @Slot(dict)
    def handle_finished(self, success):
        """處理測試完成 - 改進版本"""
        try:
            # print(f"[FINISHED] Test completed with success: {success}")  # 新增：調試信息
            if self.test_id is not None:
                self.test_finished.emit(success)
            else:
                print(f"[FINISHED] Warning: test_id is None")

            # 清理 worker 引用
            self.worker = None
            self.isRunning = False

        except Exception as e:
            print(f"[FINISHED] Error handling finished: {e}")

    def generate_command(self, testcase, name_text, category, priority, description):
        """生成測試指令並保存為 JSON 檔案 (保留原有功能)"""
        # print("Click Generate Command")
        # 使用新的 generate_user_composition 方法
        success, msg, path = self.generate_user_composition(testcase, name_text)

        if success:
            # print(f"Successfully generated user composition: {path}")
            success2, msg2, path2 = self.generate_cards_from_json(path,category, priority, description)

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

    def get_user_testcases(self):
        """讀取所有使用者創建的 testcases"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cards_dir = os.path.join(project_root, "data", "robot", "cards")
            user_testcases_path = os.path.join(cards_dir, "user_testcases.json")

            if not os.path.exists(user_testcases_path):
                return {}

            with open(user_testcases_path, 'r', encoding='utf-8') as f:
                user_testcases = json.load(f)

            # print(f"載入了 {len(user_testcases)} 個使用者 testcases")
            return user_testcases

        except Exception as e:
            print(f"讀取 user testcases 時發生錯誤: {e}")
            return {}

    def delete_user_testcase(self, testcase_id):
        """刪除指定的使用者 testcase"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cards_dir = os.path.join(project_root, "data", "robot", "cards")
            user_testcases_path = os.path.join(cards_dir, "user_testcases.json")

            if not os.path.exists(user_testcases_path):
                return False, "user_testcases.json 不存在"

            with open(user_testcases_path, 'r', encoding='utf-8') as f:
                user_testcases = json.load(f)

            if testcase_id not in user_testcases:
                return False, f"找不到 testcase ID: {testcase_id}"

            # 獲取要刪除的 testcase 名稱
            testcase_name = user_testcases[testcase_id].get('data', {}).get('config', {}).get('name', testcase_id)

            # 刪除 testcase
            del user_testcases[testcase_id]

            # 保存更新後的檔案
            with open(user_testcases_path, 'w', encoding='utf-8') as f:
                json.dump(user_testcases, f, indent=4, ensure_ascii=False)

            success_msg = f"已刪除 testcase: {testcase_name}"
            # print(success_msg)
            return True, success_msg

        except Exception as e:
            error_msg = f"刪除 testcase 時發生錯誤: {e}"
            print(f"Error: {error_msg}")
            return False, error_msg

    def list_user_testcases_summary(self):
        """獲取使用者 testcases 的摘要資訊"""
        user_testcases = self.get_user_testcases()

        summary = []
        for testcase_id, testcase_data in user_testcases.items():
            config = testcase_data.get('data', {}).get('config', {})

            summary.append({
                "id": testcase_id,
                "name": config.get('name', 'Unknown'),
                "description": config.get('description', ''),
                "created_at": config.get('created_at', ''),
                "step_count": len(config.get('steps', [])),
                "libraries": config.get('dependencies', {}).get('libraries', [])
            })

        return summary

    def report_command(self):
        print("Click Report Command")

    def import_command(self):
        print("Click Import Command")

    def _get_id_from_testName(self, data: str) -> str:
        """從測試名稱中提取 ID"""
        try:
            if "[id]" in data:
                id_start = data.find("[id]") + len("[id]")
                id_value = data[id_start:]
                return id_value.split()[0].strip()
            return ""
        except Exception as e:
            print(f"Error extracting ID: {e}")
            return ""