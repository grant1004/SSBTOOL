from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from enum import Enum
from src.utils import get_icon_path, Utils


class TestStatus(Enum):
    WAITING = "waiting"  # 等待執行
    RUNNING = "running"  # 執行中
    PASSED = "passed"  # 通過
    FAILED = "failed"  # 失敗
    NOT_RUN = "not_run"  # 未執行


class EnhancedKeywordItem:
    """增強的關鍵字項目包裝器"""

    def __init__(self, keyword_data, parent=None):
        self.keyword_data = keyword_data
        self.status = TestStatus.WAITING
        self.progress = 0
        self.widget = self._create_widget(parent)

    def _create_widget(self, parent):
        """創建關鍵字項目 Widget"""
        item_widget = QWidget(parent)
        item_widget.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border: none;
                border-radius: 4px;
                margin: 1px 0;
            }
        """)

        main_layout = QVBoxLayout(item_widget)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)

        # 第一行：關鍵字名稱和狀態
        first_row_widget = QWidget()
        first_row = QHBoxLayout(first_row_widget)
        first_row.setContentsMargins(0, 0, 0, 0)
        first_row.setSpacing(8)

        # 狀態指示燈
        self.status_light = QLabel()
        self.status_light.setFixedSize(8, 8)
        self.status_light.setStyleSheet("""
            background-color: #E0E0E0;
            border-radius: 4px;
        """)

        # 關鍵字名稱
        keyword_name = self.keyword_data.get('name', self.keyword_data.get('action', 'Unknown'))
        self.keyword_label = QLabel(keyword_name)
        self.keyword_label.setStyleSheet("""
            color: #333333;
            font-size:14px;
            font-weight: 600;
        """)

        # 狀態文本
        self.status_label = QLabel("WAITING")
        self.status_label.setFixedWidth(70)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #999999;
            font-size: 12px;
            font-weight: bold;
            background-color: #F8F9FA;
            padding: 2px 6px;
            border-radius: 3px;
        """)

        first_row.addWidget(self.status_light)
        first_row.addWidget(self.keyword_label, 1)
        first_row.addWidget(self.status_label)

        # 第二行：參數信息（如果有）
        params = self.keyword_data.get('params', {})
        self.params_widget = None
        if params:
            self.params_widget = self._create_params_widget(params)

        # 第三行：進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # 添加到主布局
        main_layout.addWidget(first_row_widget)
        if self.params_widget:
            main_layout.addWidget(self.params_widget)
        main_layout.addWidget(self.progress_bar)

        return item_widget

    def _create_params_widget(self, params):
        """創建參數顯示 Widget"""
        params_widget = QWidget()
        params_layout = QHBoxLayout(params_widget)
        params_layout.setContentsMargins(12, 0, 0, 0)  # 縮排對齊狀態燈
        params_layout.setSpacing(4)

        params_label = QLabel("參數:")
        params_label.setStyleSheet("color: #666666; font-size: 12px; font-weight: 500;")
        params_layout.addWidget(params_label)

        # 顯示參數
        for key, value in params.items():
            param_text = f"{key}={value}"
            param_chip = QLabel(param_text)
            param_chip.setStyleSheet("""
                background-color: #E8F4FD;
                color: #1565C0;
                padding: 1px 6px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: 500;
            """)
            params_layout.addWidget(param_chip)

        params_layout.addStretch()
        return params_widget

    def update_status(self, status, progress=None):
        """更新狀態和進度"""
        self.status = status

        # 狀態顏色映射
        colors = {
            TestStatus.WAITING: "#E0E0E0",  # 灰色
            TestStatus.RUNNING: "#2196F3",  # 藍色
            TestStatus.PASSED: "#4CAF50",  # 綠色
            TestStatus.FAILED: "#F44336",  # 紅色
            TestStatus.NOT_RUN: "#FF9800"  # 橙色
        }

        # 更新狀態指示燈
        self.status_light.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 4px;
        """)

        # 更新狀態文本
        status_text = {
            TestStatus.WAITING: "WAITING",
            TestStatus.RUNNING: "RUNNING",
            TestStatus.PASSED: "PASSED",
            TestStatus.FAILED: "FAILED",
            TestStatus.NOT_RUN: "NOT RUN"
        }
        self.status_label.setText(status_text[status])

        # 更新狀態文本顏色
        text_colors = {
            TestStatus.WAITING: "#999999",
            TestStatus.RUNNING: "#2196F3",
            TestStatus.PASSED: "#4CAF50",
            TestStatus.FAILED: "#F44336",
            TestStatus.NOT_RUN: "#FF9800"
        }
        self.status_label.setStyleSheet(f"""
            color: {text_colors[status]};
            font-size: 10px;
            font-weight: bold;
            background-color: #F8F9FA;
            padding: 2px 6px;
            border-radius: 3px;
        """)

        # 更新進度條
        if progress is not None:
            self.progress = progress
            self.progress_bar.setValue(progress)

            # 根據狀態更新進度條顏色
            chunk_color = colors[status]
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 2px;
                }}
            """)


class CollapsibleProgressPanel(QFrame):
    """可展開的進度面板 - 完整重構版本"""

    # 信號定義
    delete_requested = Signal(QObject)  # 刪除請求信號
    move_up_requested = Signal(QObject)  # 向上移動請求信號
    move_down_requested = Signal(QObject)  # 向下移動請求信號

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)

        self.setObjectName("CollapsibleProgressPanel")
        self.config = config
        self.is_expanded = False

        self.keywords = self._convert_steps_format(config.get('steps', []))

        self.keyword_mapping = self._build_keyword_mapping()

        self.keyword_items = []
        self.current_keyword_index = -1

        # 執行狀態追蹤
        self.completed_count = 0  # 已完成數量 (PASS + FAIL + NOT_RUN)
        self.passed_count = 0  # 通過數量
        self.failed_count = 0  # 失敗數量
        self.not_run_count = 0  # 未執行數量
        self.total_count = len(self.keywords)

        # 設置樣式
        self.setStyleSheet("""
            #CollapsibleProgressPanel {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin: 4px 4px 0px 4px;  
            }
        """)

        self._setup_ui()

        # 允許右鍵選單
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    # region ==================== UI ====================
    def _setup_ui(self):
        """設置 UI"""
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(6)

        # 創建增強的標題欄
        self.header = self._create_enhanced_header()

        # 整體進度條
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(4)
        self.overall_progress.setRange(0, self.total_count)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                background-color: #F0F0F0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # 關鍵字列表容器
        self.keywords_container = QWidget()
        self.keywords_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.keywords_layout = QVBoxLayout(self.keywords_container)
        self.keywords_layout.setContentsMargins(0, 0, 0, 0)
        self.keywords_layout.setSpacing(2)

        # 創建所有關鍵字項
        for keyword in self.keywords:
            item = EnhancedKeywordItem(keyword, self)
            self.keyword_items.append(item)
            self.keywords_layout.addWidget(item.widget)

        # 添加到主布局
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.overall_progress)
        self.main_layout.addWidget(self.keywords_container)

        # 初始設置
        self.keywords_container.hide()
        self._update_expand_icon()
        self._update_progress_info()

    def _create_enhanced_header(self):
        """創建增強的標題欄"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border-radius: 4px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 4, 6, 4)
        header_layout.setSpacing(8)

        # 狀態指示燈
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(10, 10)
        self.status_indicator.setStyleSheet("""
            background-color: #FFC107;
            border-radius: 5px;
        """)

        # 標題
        self.title_label = QLabel(self.config.get('name', ''))
        self.title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333333;
        """)

        # 進度信息標籤
        self.progress_info_label = QLabel("0/0")
        self.progress_info_label.setStyleSheet("""
            font-size: 11px;
            color: #666666;
            background-color: #E9ECEF;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
        """)

        # 預估時間
        estimated_time = self.config.get('estimated_time', '0min')
        self.time_label = QLabel(estimated_time)
        self.time_label.setStyleSheet("""
            font-size: 11px;
            color: #666666;
            background-color: #E9ECEF;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 600;
        """)

        # 展開/收起按鈕
        self.expand_button = QPushButton()
        self.expand_button.setFixedSize(20, 20)
        self.expand_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 3px;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.expand_button.clicked.connect(self.toggle_expand)

        # 添加到布局
        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.progress_info_label)
        header_layout.addWidget(self.time_label)
        header_layout.addWidget(self.expand_button)

        return header

    #endregion

    # region ==================== 資料映射建立、初始化 ====================
    def _build_keyword_mapping(self):
        """建立 Robot keyword 名稱到 UI index 的順序映射 - 使用 list 結構"""
        mapping = []

        for index, step in enumerate(self.keywords):
            step_type = step.get('step_type', 'unknown')
            unique_id = step.get('unique_id')

            if not unique_id:
                continue

            if step_type == 'keyword':
                # keyword 類型的映射
                keyword_name = step.get('keyword_name', '')

                # 建立可能的 Robot Framework keyword 名稱
                possible_names = [
                    keyword_name
                ]

                # 為每個可能的名稱創建映射項目
                for robot_name in possible_names:
                    mapping.append({
                        'robot_keyword': robot_name,
                        'index': index,
                        'unique_id': unique_id,
                        'type': 'keyword',
                        'display_name': keyword_name,
                        'completed': False  # 執行狀態標記
                    })

            elif step_type == 'testcase':
                # testcase 類型的映射
                testcase_name = step.get('testcase_name', '')

                # Robot Framework 生成的 keyword 名稱格式
                safe_name = self._convert_to_robot_name(testcase_name)
                generated_keyword = f"Execute_Testcase_{safe_name}_{unique_id}"

                mapping.append({
                    'robot_keyword': generated_keyword,
                    'index': index,
                    'unique_id': unique_id,
                    'type': 'testcase',
                    'display_name': f"[Testcase] {testcase_name}",
                    'completed': False  # 執行狀態標記
                })

        print(f"[CollapsibleProgressPanel] Built keyword mapping (list structure):")
        for i, item in enumerate(mapping):
            print(
                f"  [{i}] '{item['robot_keyword']}' -> index {item['index']} (ID: {item['unique_id']}, completed: {item['completed']})")

        return mapping

    def _convert_to_robot_name(self, keyword_name):
        """將 keyword 名稱轉換為 Robot Framework 安全格式"""
        import re
        # 清理名稱，移除特殊字符，保留中文
        safe_name = re.sub(r'[^a-zA-Z0-9_. \u4e00-\u9fff]', '_', str(keyword_name))
        return safe_name if safe_name else 'Unknown'

    def _convert_from_robot_name(self, robot_keyword):
        """將 Robot Framework 名稱格式轉換為 keyword mapping 中的名稱"""
        import re
        # 移除前綴，例如 'Lib.CommonLibrary.' 或其他庫名稱
        base_name = re.sub(r'^Lib\.[a-zA-Z]+Library\.', '', robot_keyword)
        # 將名稱轉換為小寫並用下劃線連接單詞
        mapped_name = re.sub(r'[^\w\u4e00-\u9fff]+', '_', base_name).lower()
        return mapped_name

    def _convert_steps_format(self, steps):
        """直接使用新格式，不進行格式轉換，為每個 step 添加唯一標識"""
        converted_steps = []

        for i, step in enumerate(steps):
            if isinstance(step, dict):
                # 直接使用新格式，只添加必要的 UI 顯示欄位
                step_copy = step.copy()

                step_type = step.get('step_type', 'unknown')

                if step_type == 'keyword':
                    # keyword 類型
                    step_copy['name'] = step.get('keyword_name', 'Unknown Keyword')
                    step_copy['unique_id'] = step.get('keyword_id')
                    step_copy['params'] = step.get('parameters', {})

                elif step_type == 'testcase':
                    # testcase 類型 - 這裡是關鍵，保持為獨立項目
                    testcase_name = step.get('testcase_name', 'Unknown Testcase')
                    step_copy['name'] = f"[Testcase] {testcase_name}"
                    step_copy['unique_id'] = step.get('testcase_id')
                    step_copy['params'] = {}  # testcase 通常沒有 params

                else:
                    # 其他類型
                    step_copy['name'] = step.get('name', f'Step {i + 1}')
                    step_copy['unique_id'] = step.get('step_id', f'step_{i}')
                    step_copy['params'] = step.get('params', {})

                # 添加用於顯示的 action 欄位（向下兼容）
                if 'action' not in step_copy:
                    step_copy['action'] = step_copy['name']

                converted_steps.append(step_copy)

        return converted_steps

    #endregion

    #region ==================== 狀態更新方法 ====================

    def update_status(self, message: dict):
        """更新執行狀態 - 基於完整 message"""
        try:
            msg_type = message.get('type', '')
            data = message.get('data', {})

            print(f"[CollapsibleProgressPanel] Received {msg_type}: {data}")

            if msg_type == 'test_start':
                self._handle_test_start(data)
            elif msg_type == 'keyword_start':
                self._handle_keyword_start(data)
            elif msg_type == 'keyword_end':
                self._handle_keyword_end(data)
            elif msg_type == 'log':
                self._handle_log(data)
            elif msg_type == 'test_end':
                self._handle_test_end(data)
            else:
                print(f"[CollapsibleProgressPanel] Unknown message type: {msg_type}")

        except Exception as e:
            print(f"[CollapsibleProgressPanel] Error updating status: {e}")

    def _handle_test_start(self, data):
        """處理測試開始"""
        test_name = data.get('test_name', '')
        print(f"[CollapsibleProgressPanel] Test started: {test_name}")
        self.reset_status()
        self.update_overall_status(TestStatus.RUNNING)

    def _handle_keyword_start(self, data):
        """處理關鍵字開始"""
        keyword_name = data.get('original_keyword_name', '')
        print(f"[CollapsibleProgressPanel] Keyword started: {keyword_name}")
        # 找到對應的關鍵字項目
        item_index = self._find_keyword_item_index(keyword_name, mark_completed=False)

        if item_index == -1 :
            keyword_name = self._convert_from_robot_name(keyword_name)
            print(f"[CollapsibleProgressPanel] Keyword started: {keyword_name}")
            # 找到對應的關鍵字項目
            item_index = self._find_keyword_item_index(keyword_name, mark_completed=False)

        if item_index >= 0:
            self.current_keyword_index = item_index
            self.keyword_items[item_index].update_status(TestStatus.RUNNING)

            # 如果是第一個關鍵字，更新整體狀態
            if item_index == 0:
                self.update_overall_status(TestStatus.RUNNING)

    def _handle_keyword_end(self, data):
        """處理關鍵字結束"""
        keyword_name = data.get('original_keyword_name', '')
        robot_status = data.get('status', 'UNKNOWN')
        error_message = data.get('message', '')

        print(f"[CollapsibleProgressPanel] Keyword ended: {self._convert_to_robot_name(keyword_name)} - {robot_status}")

        # 找到對應的關鍵字項目
        item_index = self._find_keyword_item_index(keyword_name, mark_completed=True)

        if item_index == -1 :
            keyword_name = self._convert_from_robot_name(keyword_name)
            print(f"[CollapsibleProgressPanel] Change Keyword name: {keyword_name}")
            # 找到對應的關鍵字項目
            item_index = self._find_keyword_item_index(keyword_name, mark_completed=True)

        if item_index >= 0:
            # 映射 Robot Framework 狀態到我們的狀態
            if robot_status == 'PASS':
                status = TestStatus.PASSED
                progress = 100
                self.passed_count += 1
                self.completed_count += 1
            elif robot_status == 'FAIL':
                status = TestStatus.FAILED
                progress = 100
                self.failed_count += 1
                self.completed_count += 1
            elif robot_status == 'NOT RUN':
                status = TestStatus.NOT_RUN
                progress = 100  # NOT RUN 也算完成，進度條設為100%
                self.not_run_count += 1
                self.completed_count += 1  # NOT RUN 也算作已完成
            else:
                status = TestStatus.WAITING
                progress = 0
                print(f"[CollapsibleProgressPanel] Unknown robot status: {robot_status}")

            print(
                f"[CollapsibleProgressPanel] Updated counts - Passed: {self.passed_count}, Failed: {self.failed_count}, Not Run: {self.not_run_count}, Completed: {self.completed_count}/{self.total_count}")

            # 更新關鍵字項目狀態
            self.keyword_items[item_index].update_status(status, progress)

            # 更新整體進度
            self._update_overall_progress()

            # 檢查是否需要更新整體狀態
            self._check_overall_completion()

    def _handle_log(self, data):
        """處理日誌訊息"""
        level = data.get('level', '')
        message = data.get('message', '')
        keyword_name = data.get('keyword_name', '')

        if level in ['ERROR', 'FAIL']:
            print(f"[CollapsibleProgressPanel] Error log: {message}")
            # 這裡可以考慮在對應的關鍵字項目中顯示錯誤信息

    def _handle_test_end(self, data):
        """處理測試結束"""
        test_status = data.get('status', '')
        error_message = data.get('message', '')

        print(f"[CollapsibleProgressPanel] Test ended: {test_status}")

        if test_status == 'PASS':
            self.update_overall_status(TestStatus.PASSED)
        elif test_status == 'FAIL':
            self.update_overall_status(TestStatus.FAILED)

    def _find_keyword_item_index(self, robot_keyword_name, mark_completed=False):
        """找到對應的 KeywordProgressItem 索引 - 使用 list 順序查找

        Args:
            robot_keyword_name: Robot Framework 傳入的 keyword 名稱
            mark_completed: 是否標記為已完成 (在 keyword_end 時設為 True)
        """


        # 1. 精確匹配：完整的 robot keyword 名稱
        for mapping_item in self.keyword_mapping:
            if mapping_item['robot_keyword'] == robot_keyword_name:
                if mapping_item['completed']:
                    continue
                index = mapping_item['index']
                unique_id = mapping_item['unique_id']

                # 只在 keyword_end 時標記為已完成
                if mark_completed:
                    mapping_item['completed'] = True
                print( f"[CollapsibleProgressPanel] Found by exact match: {robot_keyword_name} -> index {index} (ID: {unique_id})")
                return index

        # 2. ID 精確匹配：從 Robot keyword 名稱提取 ID
        extracted_id = self._extract_id_from_robot_keyword(robot_keyword_name)
        if extracted_id:
            for mapping_item in self.keyword_mapping:
                if mapping_item['unique_id'] == extracted_id:
                    # 如果已完成且不是要標記完成，跳過
                    if mapping_item['completed'] and not mark_completed:
                        continue

                    index = mapping_item['index']

                    # 只在 keyword_end 時標記為已完成
                    if mark_completed:
                        mapping_item['completed'] = True
                        print(f"[CollapsibleProgressPanel] Marked as completed: index {index}")

                    print(
                        f"[CollapsibleProgressPanel] Found by ID match: {robot_keyword_name} -> ID {extracted_id} -> index {index}")
                    return index

        # 3. 模糊匹配：顯示名稱相似的項目
        for mapping_item in self.keyword_mapping:
            # 如果已完成且不是要標記完成，跳過
            if mapping_item['completed']:
                continue

            display_name = mapping_item['display_name']
            robot_keyword = mapping_item['robot_keyword']

            # 檢查名稱相似度
            if (self._is_similar_keyword(robot_keyword_name, display_name) or
                    self._is_similar_keyword(robot_keyword_name, robot_keyword)):

                index = mapping_item['index']
                unique_id = mapping_item['unique_id']

                # 只在 keyword_end 時標記為已完成
                if mark_completed:
                    mapping_item['completed'] = True
                    print(f"[CollapsibleProgressPanel] Marked as completed: index {index}")

                print(
                    f"[CollapsibleProgressPanel] Found by fuzzy match: {robot_keyword_name} -> '{display_name}' -> index {index} (ID: {unique_id})")
                return index

        print(f"[CollapsibleProgressPanel] Could not find keyword: {robot_keyword_name}")
        print(f"[CollapsibleProgressPanel] Available mappings:")
        for i, item in enumerate(self.keyword_mapping):
            print(
                f"  [{i}] '{item['robot_keyword']}' -> index {item['index']} (ID: {item['unique_id']}, completed: {item['completed']})")

        return -1

    def _extract_id_from_robot_keyword(self, robot_keyword_name):
        """從 Robot keyword 名稱中提取唯一 ID"""
        try:
            import re

            # 匹配格式：Execute_Testcase_NAME_ID
            match = re.search(r'Execute_Testcase_.*_(\d+)$', robot_keyword_name)
            if match:
                return int(match.group(1))

            # 匹配末尾的數字 ID
            match = re.search(r'_(\d+)$', robot_keyword_name)
            if match:
                return int(match.group(1))

            # 匹配任何數字序列
            match = re.search(r'(\d+)', robot_keyword_name)
            if match:
                return int(match.group(1))

        except (ValueError, AttributeError) as e:
            print(f"[CollapsibleProgressPanel] Error extracting ID from {robot_keyword_name}: {e}")

        return None

    def _is_similar_keyword(self, robot_keyword_name, target_name):
        """檢查兩個 keyword 名稱是否相似"""
        # 轉換為小寫進行比較
        robot_clean = robot_keyword_name.lower()
        target_clean = target_name.lower()

        # 移除常見的前綴後綴
        robot_clean = robot_clean.replace('execute_testcase_', '').replace('[testcase]', '').strip()
        target_clean = target_clean.replace('execute_testcase_', '').replace('[testcase]', '').strip()

        # 檢查包含關係
        return robot_clean in target_clean or target_clean in robot_clean

    def _update_overall_progress(self):
        """更新整體進度條"""
        if self.total_count > 0:
            self.overall_progress.setValue(self.completed_count)
            self._update_progress_info()

            # 更新進度條顏色 - 根據不同狀態組合
            if self.failed_count > 0:
                # 有失敗的，使用紅色
                chunk_color = "#F44336"
            elif self.not_run_count > 0 and self.passed_count > 0:
                # 有通過也有未執行的，使用黃色
                chunk_color = "#FF9800"
            elif self.not_run_count > 0 and self.passed_count == 0:
                # 只有未執行的，使用橙色
                chunk_color = "#FF9800"
            elif self.passed_count > 0:
                # 只有通過的，使用綠色
                chunk_color = "#4CAF50"
            else:
                # 其他情況，使用藍色
                chunk_color = "#2196F3"

            self.overall_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 2px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 2px;
                }}
            """)

    def _check_overall_completion(self):
        """檢查整體完成狀態"""
        if self.completed_count >= self.total_count:
            # 所有步驟都完成了，根據不同情況設置狀態
            if self.failed_count > 0:
                # 有失敗的步驟
                self.update_overall_status(TestStatus.FAILED)
            elif self.not_run_count > 0 and self.passed_count > 0:
                # 有通過也有未執行的
                self.update_overall_status(TestStatus.NOT_RUN)
            elif self.not_run_count > 0 and self.passed_count == 0:
                # 只有未執行的
                self.update_overall_status(TestStatus.NOT_RUN)
            elif self.passed_count > 0:
                # 只有通過的
                self.update_overall_status(TestStatus.PASSED)
            else:
                # 其他情況
                self.update_overall_status(TestStatus.WAITING)

    def update_overall_status(self, status: TestStatus):
        """更新整體狀態"""
        colors = {
            TestStatus.WAITING: "#FFC107",
            TestStatus.RUNNING: "#2196F3",
            TestStatus.PASSED: "#4CAF50",
            TestStatus.FAILED: "#F44336",
            TestStatus.NOT_RUN: "#FF9800"
        }

        self.status_indicator.setStyleSheet(f"""
            background-color: {colors[status]};
            border-radius: 5px;
        """)

    def reset_status(self):
        """重置所有關鍵字的狀態和進度"""
        print(f"[CollapsibleProgressPanel] Resetting status")

        # 重置所有計數器
        self.completed_count = 0
        self.passed_count = 0
        self.failed_count = 0
        self.not_run_count = 0
        self.current_keyword_index = -1

        # 重置映射中的完成狀態
        for mapping_item in self.keyword_mapping:
            mapping_item['completed'] = False

        # 重置所有關鍵字項目
        for item in self.keyword_items:
            item.update_status(TestStatus.WAITING, 0)

        # 重置整體進度
        self.overall_progress.setValue(0)
        self.update_overall_status(TestStatus.WAITING)
        self._update_progress_info()

    def _update_progress_info(self):
        """更新進度信息顯示"""
        if hasattr(self, 'progress_info_label'):
            # 顯示總進度 (已完成/總數)
            base_info = f"{self.completed_count}/{self.total_count}"

            # 添加詳細狀態計數（如果有的話）
            details = []
            if self.passed_count > 0:
                details.append(f"✓{self.passed_count}")
            if self.failed_count > 0:
                details.append(f"✗{self.failed_count}")
            if self.not_run_count > 0:
                details.append(f"◦{self.not_run_count}")

            if details:
                detail_info = " (" + " ".join(details) + ")"
                self.progress_info_label.setText(base_info + detail_info)
            else:
                self.progress_info_label.setText(base_info)

    #endregion

    # region ==================== 滑鼠事件 ====================
    def mousePressEvent(self, event):
        """處理整個面板的點擊事件"""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self.header.geometry().contains(event.pos()):
                self.toggle_expand()

    def show_context_menu(self, position):
        """顯示右鍵選單"""
        context_menu = QMenu(self)

        # 新增選單項目
        delete_action = context_menu.addAction("刪除")
        move_up_action = context_menu.addAction("向上移動")
        move_down_action = context_menu.addAction("向下移動")

        # 設置圖標
        try:
            delete_icon = QIcon(get_icon_path("delete.svg"))
            delete_action.setIcon(Utils.change_icon_color(delete_icon, "#000000"))

            upward_icon = QIcon(get_icon_path("arrow_drop_up.svg"))
            move_up_action.setIcon(Utils.change_icon_color(upward_icon, "#000000"))

            downward_icon = QIcon(get_icon_path("arrow_drop_down.svg"))
            move_down_action.setIcon(Utils.change_icon_color(downward_icon, "#000000"))
        except ImportError:
            pass

        # 獲取所選操作
        action = context_menu.exec_(self.mapToGlobal(position))

        # 處理所選操作
        if action == delete_action:
            self.delete_requested.emit(self)
        elif action == move_up_action:
            self.move_up_requested.emit(self)
        elif action == move_down_action:
            self.move_down_requested.emit(self)

    def toggle_expand(self):
        """切換展開/收起狀態"""
        self.is_expanded = not self.is_expanded

        # 更新前先確保所有的尺寸更新已經完成
        QApplication.processEvents()

        if self.is_expanded:
            self.keywords_container.show()
        else:
            self.keywords_container.hide()

        # 更新布局
        self.updateGeometry()
        self.adjustSize()

        # 找到 ScrollArea 父組件
        scroll_area = None
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scroll_area = parent
                break
            parent = parent.parent()

        # 如果找到了 ScrollArea，更新它
        if scroll_area:
            scroll_area.viewport().update()

        self._update_expand_icon()

    def _update_expand_icon(self):
        """更新展開/收起圖標"""
        icon_name = "navigate_up.svg" if self.is_expanded else "navigate_down.svg"
        icon = QIcon(get_icon_path(icon_name))
        colored_icon = Utils.change_icon_color(icon, "#666666")
        self.expand_button.setIcon(colored_icon)
        self.expand_button.setIconSize(QSize(12, 12))
    #endregion

