
from PySide6.QtCore import Signal, QObject, Slot, Qt, QThread
from numpy import long
import json

from src.Container import singleton
from src.worker import RobotTestWorker
import os

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
        if len(testcase) == 0:
            print("No test case selected")
            return

        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

        self.isRunning = True
        self.now_TestCase = testcase
        generate, msg, path = self.generate_robot_file(testcase, name_text)
        # print(msg)

        if generate:
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            lib_path = os.path.join(project_root, "Lib")
            output_dir = os.path.join(project_root, "data", "robot")

            # 創建並設置新的 worker thread 用來執行 .robot
            self.worker = RobotTestWorker(path, project_root, lib_path, output_dir)
            self.worker.progress.connect(self.handle_progress, Qt.ConnectionType.QueuedConnection)
            self.worker.finished.connect(self.handle_finished, Qt.ConnectionType.QueuedConnection)

            self.thread = QThread()
            self.thread.started.connect( self.worker.run )

            self.worker.moveToThread(self.thread)

            self.thread.start()

    @Slot(dict)  # 明確標記為槽函數
    def handle_progress(self, message):
        """處理測試進度更新"""
        # print( "handle_progress" )
        # print( message )
        self.test_id = int(self._get_id_from_testName(message.get('data', "No data in progress message.").get('test_name')))
        self.test_progress.emit(message, self.test_id)

    @Slot(dict)  # 明確標記為槽函數
    def handle_finished(self, success):
        """處理測試完成"""
        # print( "handle_finished" )
        if self.test_id is not None :
            self.test_finished.emit(success)
        self.worker = None

    def generate_command(self, testcase, name_text):
        """生成測試指令並保存為 JSON 檔案
        Args:
            testcase (dict): 測試案例字典
            name_text (str): 測試名稱
        """
        print("Click Generate Command")
        if len(testcase) == 0:
            print("No test case selected")
            return

        # 建立基本結構
        command = {
            "testName": name_text,
            "testcases": []
        }

        # 添加測試案例
        for key, test in testcase.items():
            test_data = test.get('data', {})
            if test_data:  # 確保有資料才添加
                command["testcases"].append(test_data)

        # 生成檔案名稱 (使用測試名稱)
        filename = f"{name_text}.json"

        # 寫入 JSON 檔案
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(command, f, indent=4, ensure_ascii=False)
            print(f"Successfully generated {filename}")
        except Exception as e:
            print(f"Error generating JSON file: {str(e)}")

    def report_command(self):
        print( "Click Report Command")

    def import_command(self):
        print( "Click Import Command")


    # generate .robot
    def generate_robot_file(self, test_cases, name_text):
        """生成 Robot Framework 測試文件"""
        if not test_cases:
            return False, "No test case selected", ""

        try:
            robot_content = self._generate_robot_content(test_cases, name_text)

            # 使用專案根目錄的相對路徑
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            robot_dir = os.path.join(project_root, "data", "robot")

            # 確保目錄存在
            os.makedirs(robot_dir, exist_ok=True)

            # 生成檔案路徑
            robot_file_path = os.path.join(robot_dir, "generated_test.robot")

            # 寫入文件
            with open(robot_file_path, 'w', encoding='utf-8') as f:
                f.write(robot_content)

            return True, f"Robot file generated successfully: {robot_file_path}", robot_file_path

        except Exception as e:
            return False, f"Error generating robot file: {e}", ""

    def _generate_robot_content(self, test_cases, name_text):
        """生成完整的 Robot 文件內容"""
        robot_content = []
        libraries = set()

        # 收集所有使用到的庫
        for test in test_cases.values():
            # 從 config 類別中抓取庫
            # print( test.get('panel') )
            if category := test.get('data', {}).get('config', {}).get('category'):
                libraries.add(category)

            # 從 setup 中的 library 屬性抓取庫
            if libraries_in_setup := test.get('data', {}).get('config', {}).get('setup', {}).get('library'):
                # print( f"libraries_in_setup: {libraries_in_setup}" )
                libraries.update(libraries_in_setup)
            # else :
                # print( "no libraries_in_setup" )


        # print( f"Libraries: {libraries}" )
        # 生成 Settings 區段
        robot_content.extend(self._generate_settings(libraries, name_text))
        robot_content.append("")

        # 生成 Variables 區段
        robot_content.extend(self._generate_variables())
        robot_content.append("")

        # 生成 Test Cases 區段
        robot_content.append("*** Test Cases ***")

        # 處理每個測試項目
        for key, test in test_cases.items():
            config = test.get('data', {}).get('config', {})
            if 'category' in config:
                # 是 keyword
                robot_content.extend(self._generate_content_keyword(key,test))
            else:
                # 是 test case
                robot_content.extend(self._generate_content_testcase(key,test))

        return '\n'.join(robot_content)

    def _generate_settings(self, libraries, name_text):
        """生成 Settings 區段，自動包含所有需要的 Library"""
        content = ["*** Settings ***"]
        content.append(f"Documentation    {name_text}")

        # 將庫名和文件對應起來
        library_files = {
            'common': 'CommonLibrary',
            'battery': 'BatteryLibrary',
            'hmi': 'HMILibrary',
            'motor': 'MotorLibrary',
            'controller': 'ControllerLibrary'
        }

        # 為每個需要的庫添加 Library 聲明
        for category in sorted(libraries):
            # 使用 lower() 進行大小寫不敏感的查找
            library_name = library_files.get(category.lower())
            if library_name:
                content.append(f"Library    Lib.{library_name}")

        content.append("")  # 添加空行
        return content

    def _generate_variables(self):
        """生成 Variables 區段"""
        return [
            "*** Variables ***",
            "${TIMEOUT}    30s"
        ]

    def _generate_content_testcase(self, key, test):
        """生成測試案例內容"""
        content = []
        config = test.get('data', {}).get('config', {})

        # 測試案例名稱
        testName = f"{config.get('name', 'Unknown')} [id]{key}"
        content.append(testName)

        # Tags
        content.append(f"    [Tags]    {config.get('priority', 'normal')}")

        # Documentation
        doc_lines = [config.get('description', '')]
        if preconditions := config.get('setup', {}).get('preconditions', []):
            doc_lines.extend(['', 'Preconditions:'])
            for precond in preconditions:
                doc_lines.append(f"- {precond}")

        content.append(f"    [Documentation]    {doc_lines[0]}")
        for line in doc_lines[1:]:
            content.append(f"    ...    {line}")

        # Steps
        for step in config.get('steps', []):
            action = step.get('action', '')
            params = step.get('params', {})
            param_str = '    '.join(f"{k}=${{{v}}}" for k, v in params.items())

            if param_str:
                content.append(f"    {action}    {param_str}")
            else:
                content.append(f"    {action}")

        content.append("")  # 添加空行分隔
        return content

    def _generate_content_keyword(self, key, test):
        """生成關鍵字內容"""
        content = []
        config = test.get('data', {}).get('config', {})

        # 生成唯一的測試案例名稱
        test_name = f"Execute Keyword - {config.get('name', 'Unknown')} [id]{key}"
        content.append(test_name)
        content.append(f"    [Tags]    auto-generated    {config.get('priority', 'normal')}")

        if description := config.get('description'):
            content.append(f"    [Documentation]    {description}")

        # 取得 keyword 名稱和參數
        keyword_name = config.get('name', '')
        arguments = config.get('arguments', [])

        # 生成 keyword 呼叫
        if not arguments:
            content.append(f"    {keyword_name}")
        else:
            param_values = []
            for arg in arguments:
                arg_name = arg.get('name', '')
                # print( arg )
                default_value = arg.get('value')

                if default_value is not None:
                    if ( arg.get('type') == 'str' ):
                        param_values.append(f"{arg_name}=\"{default_value}\"")
                    else :
                        param_values.append(f"{arg_name}={default_value}")
                else:
                    param_values.append(f"{arg_name}=None")

            content.append(f"    {keyword_name}    {('    ').join(param_values)}")

        content.append("")  # 添加空行分隔
        return content

    def _get_id_from_testName(self, data: str) -> str:
        """
        從測試名稱中提取 ID

        Args:
            data (str): 測試名稱字符串，格式如 "Execute Keyword - send_can_message [id]2972073797632"

        Returns:
            str: 提取出的 ID，如果沒找到則返回空字符串
        """
        try:
            # 使用 split 分割字符串，找到包含 [id] 的部分
            if "[id]" in data:
                # 找到 [id] 的位置並截取後面的數字
                id_start = data.find("[id]") + len("[id]")
                id_value = data[id_start:]

                # 如果 ID 後面還有其他文字，只取數字部分
                # 使用 strip() 去除可能的空格
                return id_value.split()[0].strip()
            return ""

        except Exception as e:
            print(f"Error extracting ID: {e}")
            return ""