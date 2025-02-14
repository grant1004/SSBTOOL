from PySide6.QtCore import Signal, QObject
from src.utils.singleton import singleton
from robot import run
from src.worker import RobotTestWorker
import os

@singleton
class RunWidget_Model(QObject):

    test_progress = Signal(str)  # 測試進度信號
    test_finished = Signal(bool)  # 測試完成信號

    def __init__(self):
        super().__init__()
        self.worker = None

    def run_command(self, testcase, name_text ):
        # print("Click Run Command")
        if ( len( testcase ) == 0 ):
            print( "No test case selected")
        else :
            generate, msg, path = self.generate_robot_file(testcase,name_text)
            print( msg )
            if generate:
                project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                lib_path = os.path.join(project_root, "Lib")
                output_dir = os.path.join(project_root, "data", "robot")

                # 創建並設置 worker
                self.worker = RobotTestWorker(path, project_root, lib_path, output_dir)
                self.worker.progress.connect(self.handle_progress)
                self.worker.finished.connect(self.handle_finished)

                # 開始執行
                self.worker.start()

    def handle_progress(self, message):
        """處理測試進度更新"""
        self.test_progress.emit(message)
        # print(message)  # 你可以改為更新 UI 上的進度顯示

    def handle_finished(self, success):
        """處理測試完成"""
        self.test_finished.emit(success)
        self.worker = None

    def generate_command(self):
        print( "Click Generate Command")

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
            # print( test )
            if category := test.get('data', {}).get('config', {}).get('category'):
                libraries.add(category)

            # 從 setup 中的 library 屬性抓取庫
            if libraries_in_setup := test.get('data', {}).get('config', {}).get('setup', {}).get('library'):
                # print( f"libraries_in_setup: {libraries_in_setup}" )
                libraries.update(libraries_in_setup)
            else :
                print( "no libraries_in_setup" )


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
        for test in test_cases.values():
            config = test.get('data', {}).get('config', {})
            if 'category' in config:
                # 是 keyword
                robot_content.extend(self._generate_content_keyword(test))
            else:
                # 是 test case
                robot_content.extend(self._generate_content_testcase(test))

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

    def _generate_content_testcase(self, test):
        """生成測試案例內容"""
        content = []
        config = test.get('data', {}).get('config', {})

        # 測試案例名稱
        content.append(config.get('name', 'Unnamed Test'))

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

    def _generate_content_keyword(self, test):
        """生成關鍵字內容"""
        content = []
        config = test.get('data', {}).get('config', {})

        # 生成唯一的測試案例名稱
        test_name = f"Execute Keyword - {config.get('name', 'Unknown')}"
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

