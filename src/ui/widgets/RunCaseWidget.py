# from PySide6.QtWidgets import *
# from PySide6.QtCore import *
# from PySide6.QtGui import *
# from numpy import long
#
# from src.utils import Container
# from src.ui.components.base import CollapsibleProgressPanel, BaseKeywordProgressCard
# import json
#
# import datetime
# from typing import Dict, Any
#
# class RunCaseWidget(QWidget):
#     update_ui = Signal()
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setAcceptDrops(True)
#         self.controller = Container.get_run_widget_controller()
#         self.controller.set_view(self)
#         self.theme_manager = self.parent().theme_manager
#         self._setup_shadow()
#         self.setContentsMargins(4, 8, 8, 4)
#         self._setup_ui()
#
#         self.test_cases = {}
#         self.update_ui.connect(self._update_ui)
#
#         # 添加接收計數器
#         self._received_counter = 0
#         self._received_messages = []
#
#     def _setup_ui(self):
#         self.main_layout = QGridLayout(self)
#         self.main_layout.setContentsMargins(0, 0, 0, 0)
#         self.main_layout.setSpacing(0)
#
#         # 創建頂部輸入框
#         # self.Name_LineEdit = QLabel()
#         # self.Name_LineEdit.setFont(QFont("Arial", 30, QFont.Weight.Bold))
#         # self.Name_LineEdit.setText("Working Area.")
#         # self.Name_LineEdit.setFixedHeight(40)
#
#         # 創建滾動區域
#         self.scroll_area = QScrollArea()
#         self.scroll_area.setWidgetResizable(True)
#         self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
#         self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
#
#         # 創建內容容器
#         self.content_widget = QWidget()
#         self.content_layout = QVBoxLayout(self.content_widget)
#         self.content_layout.setContentsMargins(0, 0, 0, 0)  # 移除內容容器的邊距
#         self.content_layout.setSpacing(0)
#         self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
#
#         # 設置滾動區域的內容
#         self.scroll_area.setWidget(self.content_widget)
#
#         # 設置列（column）的比例
#         # self.main_layout.setColumnStretch(0, 15)
#         # self.main_layout.setColumnStretch(1, 2)
#
#         # 設置列（row）的比例
#         # self.main_layout.setRowStretch(0, 1)
#         # self.main_layout.setRowStretch(1, 15)
#
#         # 添加到主布局  row column rowspan columnspan
#         self.main_layout.addWidget(self.scroll_area)  # 使用-1讓容器填充所有剩餘行
#         # self.main_layout.addWidget(self.Name_LineEdit, 0, 0, 1, 1, Qt.AlignmentFlag.AlignTop)
#
#     def _setup_shadow(self):
#         self.shadow = QGraphicsDropShadowEffect(self)
#         self.shadow.setColor(QColor(0, 0, 0, 60))
#         self.shadow.setBlurRadius(15)
#         self.shadow.setOffset(0, 2)
#         self.setGraphicsEffect(self.shadow)
#         self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
#
#     def dragEnterEvent(self, event):
#         if event.mimeData().hasFormat('application/x-testcase') or event.mimeData().hasFormat('application/x-keyword'):
#             event.acceptProposedAction()
#
#     def dragMoveEvent(self, event):
#         event.acceptProposedAction()
#
#     def dropEvent(self, event):
#         mime_data = event.mimeData()
#         """
#             x-testcase :
#                 {'id': 'TEST_001',
#                  'name': 'Test Case 001, Test Case 001',
#                  'description': '測試功能A的運作情況',
#                  'setup': {
#                     'preconditions': ['預先條件1', '預先條件2']},
#                     'estimated_time': 300,
#                     'steps': [{'step_id': 1, 'name': '步驟1', 'action': '執行動作1', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果1'}, {'step_id': 2, 'name': '步驟2', 'action': '執行動作2', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果2'}, {'step_id': 3, 'name': '步驟3', 'action': '執行動作3', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果3'}, {'step_id': 4, 'name': '步驟4', 'action': '執行動作4', 'params': {'param1': '值3'}, 'expected': '預期結果4'}],
#                     'priority': 'required'
#                     }
#
#             x-keyword :
#             {'id': 'send_can_message',
#              'config': {
#                 'id': 'send_can_message',
#                 'name': 'send_can_message',
#                 'category': 'battery',
#                 'description': '發送 CAN 訊息',
#                 'arguments': [
#                     {'name': 'can_id', 'type': 'any', 'description': '', 'default': None, 'value': '401'},
#                     {'name': 'payload', 'type': 'any', 'description': '', 'default': None, 'value': '00'},
#                     {'name': 'node', 'type': 'any', 'description': '', 'default': '1', 'value': '1'},
#                     {'name': 'can_type', 'type': 'any', 'description': '', 'default': '0', 'value': '0'}],
#                 'returns': '',
#                 'priority': 'optional'}
#             }
#
#
#
#
#         """
#         if mime_data.hasFormat('application/x-testcase'):
#             data = mime_data.data('application/x-testcase')
#             data_type = 'testcase'
#         elif mime_data.hasFormat('application/x-keyword'):
#             data = mime_data.data('application/x-keyword')
#             data_type = 'keyword'
#             # print( data )
#         else:
#             return
#
#
#
#         case_data = json.loads(str(data, encoding='utf-8'))
#         # print( "Drop data : " + str(case_data) )
#         self.add_item(case_data, data_type)
#         event.acceptProposedAction()
#
#     def add_item(self, case_data, data_type):
#         """
#         根據不同類型創建不同的面板
#
#         Args:
#             case_data: 拖放的數據
#             data_type: 'testcase' 或 'keyword'
#         """
#         if data_type == 'testcase':
#             # 創建測試案例面板
#             panel = CollapsibleProgressPanel(case_data['config'], parent=self)
#             # 連接右鍵選單信號
#             panel.delete_requested.connect(self.handle_delete_item)
#             panel.move_up_requested.connect(self.handle_move_up_item)
#             panel.move_down_requested.connect(self.handle_move_down_item)
#         else:
#             # 創建關鍵字面板
#             panel = BaseKeywordProgressCard(case_data['config'], parent=self)
#             # 連接右鍵選單信號
#             panel.delete_requested.connect(self.handle_delete_item)
#             panel.move_up_requested.connect(self.handle_move_up_item)
#             panel.move_down_requested.connect(self.handle_move_down_item)
#
#
#         self.content_layout.addWidget(panel)
#
#         panel_id = id(panel)
#
#         self.test_cases[panel_id] = {
#             'panel': panel,
#             'data': case_data,  # json
#             'type': data_type  # testcase keyword
#         }
#
#         # 確保新添加的面板可見
#         self.scroll_area.ensureWidgetVisible(panel)
#
#     def _update_ui(self):
#         self.update()
#         self.repaint()
#
#     def get_name_text(self):
#         return "Untitled"
#         # if (self.Name_LineEdit.text() == ""):
#         #     return "Untitled"
#         # else:
#         #     return self.Name_LineEdit.text()
#
#     def update_progress(self, message: dict, test_id: long):
#         """更新進度顯示 - 增強接收追蹤版本"""
#         self._received_counter += 1
#         msg_type = message.get('type', 'unknown')
#         test_name = message.get('data', {}).get('test_name', '')
#         key_word = message.get('data', {}).get('keyword_name', '')
#         # 記錄接收的訊息
#         message_record = {
#             'counter': self._received_counter,
#             'test_name': test_name,
#             'keyword': key_word,
#             'type': msg_type,
#             'test_id': test_id,
#             'timestamp': QDateTime.currentDateTime().toString(),
#             'message' : message
#         }
#         self._received_messages.append(message_record)
#
#         panel = self.test_cases[test_id]['panel']
#         panel.update_status(message)
#         self._update_ui()
#
#     def reset_test(self):
#         for panel in self.test_cases.values():
#             panel['panel'].reset_status()
#
#     def test_finished(self, success : bool ) :
#         for msg in self._received_messages :
#             # print( msg['message'] )
#             formatted = PrettyMessageFormatter.format_message(msg)
#             print(formatted)
#         self._received_messages.clear()
#
#     # 新增處理右鍵選單動作的方法
#     def handle_delete_item(self, panel):
#         """處理刪除項目"""
#         # 找到對應的panel_id
#         panel_id = id(panel)
#
#         if panel_id in self.test_cases:
#             # 從布局中移除
#             self.content_layout.removeWidget(panel)
#             # 隱藏和刪除panel
#             panel.hide()
#             panel.deleteLater()
#             # 從字典中移除
#             del self.test_cases[panel_id]
#             # 更新UI
#             self._update_ui()
#
#     def handle_move_up_item(self, panel):
#         """處理向上移動項目"""
#         # 找到當前項目在佈局中的索引
#         index = self.content_layout.indexOf(panel)
#
#         # 檢查是否可以上移（不是第一個）
#         if index > 0:
#             # 從佈局中移除
#             self.content_layout.removeWidget(panel)
#             # 在新位置添加
#             self.content_layout.insertWidget(index - 1, panel)
#             # 重新構建 test_cases 字典以保持正確順序
#             self._rebuild_test_cases_order()
#             # 更新UI
#             self._update_ui()
#
#     def handle_move_down_item(self, panel):
#         """處理向下移動項目"""
#         # 找到當前項目在佈局中的索引
#         index = self.content_layout.indexOf(panel)
#
#         # 檢查是否可以下移（不是最後一個）
#         if index < self.content_layout.count() - 1:
#             # 從佈局中移除
#             self.content_layout.removeWidget(panel)
#             # 在新位置添加
#             self.content_layout.insertWidget(index + 1, panel)
#             # 重新構建 test_cases 字典以保持正確順序
#             self._rebuild_test_cases_order()
#             # 更新UI
#             self._update_ui()
#
#     def _rebuild_test_cases_order(self):
#         """重新構建 test_cases 字典以反映當前布局順序"""
#         # 備份當前的 test_cases 數據
#         old_test_cases = self.test_cases.copy()
#         # 清空當前字典
#         self.test_cases.clear()
#
#         # 按照布局順序重新構建字典
#         for i in range(self.content_layout.count()):
#             widget = self.content_layout.itemAt(i).widget()
#             if widget:  # 確保 widget 存在
#                 panel_id = id(widget)
#                 # 如果在舊字典中找到對應數據，則添加到新字典
#                 if panel_id in old_test_cases:
#                     self.test_cases[panel_id] = old_test_cases[panel_id]
#
#     def get_test_cases_in_order(self):
#         """獲取按照當前布局順序排列的測試用例列表"""
#         ordered_cases = []
#         for i in range(self.content_layout.count()):
#             widget = self.content_layout.itemAt(i).widget()
#             if widget:
#                 panel_id = id(widget)
#                 if panel_id in self.test_cases:
#                     ordered_cases.append(self.test_cases[panel_id])
#         return ordered_cases
#
# class PrettyMessageFormatter:
#     """漂亮的消息格式化器"""
#
#     # 🎨 消息類型顏色和符號
#     TYPE_STYLES = {
#         'test_start': {'emoji': '🚀', 'color': '\033[92m', 'label': 'TEST_START'},  # 綠色
#         'test_end': {'emoji': '🏁', 'color': '\033[94m', 'label': 'TEST_END'},  # 藍色
#         'keyword_start': {'emoji': '▶️', 'color': '\033[93m', 'label': 'KW_START'},  # 黃色
#         'keyword_end': {'emoji': '✅', 'color': '\033[95m', 'label': 'KW_END'},  # 紫色
#         'log': {'emoji': '📝', 'color': '\033[96m', 'label': 'LOG'},  # 青色
#         'error': {'emoji': '❌', 'color': '\033[91m', 'label': 'ERROR'},  # 紅色
#         'unknown': {'emoji': '❓', 'color': '\033[90m', 'label': 'UNKNOWN'},  # 灰色
#     }
#
#     # 🎨 狀態顏色
#     STATUS_COLORS = {
#         'PASS': '\033[92m',  # 綠色
#         'FAIL': '\033[91m',  # 紅色
#         'RUNNING': '\033[93m',  # 黃色
#         'SKIP': '\033[90m',  # 灰色
#     }
#
#     # 重置顏色
#     RESET = '\033[0m'
#     BOLD = '\033[1m'
#
#     @classmethod
#     def format_message(cls, msg: Dict[str, Any], compact: bool = False) -> str:
#         """
#         格式化消息為漂亮的輸出
#
#         Args:
#             msg: 消息字典
#             compact: 是否使用緊湊格式
#         """
#         if compact:
#             return cls._format_compact(msg)
#         else:
#             return cls._format_detailed(msg)
#
#     @classmethod
#     def _format_detailed(cls, msg: Dict[str, Any]) -> str:
#         """詳細格式化"""
#
#         # 獲取基本信息
#         counter = msg.get('counter', '?')
#         msg_type = msg.get('type', 'unknown')
#         keyword = msg.get('keyword', '')
#         test_name = msg.get('test_name', '')
#         test_id = msg.get('test_id', '')
#         timestamp = msg.get('timestamp', '')
#         status = msg.get('status', '')
#
#         # 獲取樣式
#         style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
#         emoji = style['emoji']
#         color = style['color']
#         label = style['label']
#
#         # 格式化時間戳
#         formatted_time = cls._format_timestamp(timestamp)
#
#         # 🔥 使用完整的測試名稱（不截斷）
#         full_test_name = test_name
#
#         # 格式化狀態
#         formatted_status = cls._format_status(status)
#
#         # 構建輸出
#         lines = []
#
#         # 主要信息行
#         header = f"{color}{cls.BOLD}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"
#
#         if keyword:
#             header += f" │ 🔧 {cls.BOLD}{keyword}{cls.RESET}"
#
#         if formatted_status:
#             header += f" │ {formatted_status}"
#
#         lines.append(header)
#
#         # 詳細信息行
#         if test_id:
#             lines.append(f"    📋 Test ID: {cls.BOLD}{test_id}{cls.RESET}")
#
#         # 🔥 顯示完整測試名稱
#         if full_test_name:
#             lines.append(f"    📝 Test: {full_test_name}")
#
#         # 🔥 如果有keyword，單獨顯示一行
#         if keyword:
#             lines.append(f"    🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}")
#
#         if formatted_time:
#             lines.append(f"    ⏰ Time: {formatted_time}")
#
#         # 分隔線（可選）
#         if counter and int(str(counter)) % 5 == 0:
#             lines.append(f"    {'-' * 100}")
#
#         return '\n'.join(lines)
#
#     @classmethod
#     def _format_compact(cls, msg: Dict[str, Any]) -> str:
#         """緊湊格式化 - 顯示完整信息"""
#
#         counter = msg.get('counter', '?')
#         msg_type = msg.get('type', 'unknown')
#         keyword = msg.get('keyword', '')
#         test_name = msg.get('test_name', '')
#         test_id = msg.get('test_id', '')
#         status = msg.get('status', '')
#         timestamp = msg.get('timestamp', '')
#
#         # 獲取樣式
#         style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
#         emoji = style['emoji']
#         color = style['color']
#         label = style['label']
#
#         # 格式化狀態
#         status_str = f" [{cls._format_status(status, short=True)}]" if status else ""
#
#         # 格式化時間
#         time_str = cls._format_timestamp(timestamp)
#         time_display = f" ⏰{time_str}" if time_str else ""
#
#         # 🔥 構建完整的輸出行
#         lines = []
#
#         # 主要信息行
#         main_line = (f"{color}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"
#                      f" │ 🆔{test_id}{status_str}{time_display}")
#         lines.append(main_line)
#
#         # 🔥 如果有keyword，顯示keyword行
#         if keyword:
#             keyword_line = f"     🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}"
#             lines.append(keyword_line)
#
#         # 🔥 如果有完整測試名稱，顯示測試名稱行
#         if test_name:
#             test_line = f"     📝 Test: {test_name}"
#             lines.append(test_line)
#
#         return '\n'.join(lines)
#
#     @classmethod
#     def _format_timestamp(cls, timestamp: Any) -> str:
#         """格式化時間戳"""
#         if not timestamp:
#             return ""
#
#         try:
#             if isinstance(timestamp, (int, float)):
#                 dt = datetime.datetime.fromtimestamp(timestamp)
#                 return dt.strftime("%H:%M:%S.%f")[:-3]  # 保留毫秒
#             elif isinstance(timestamp, str):
#                 return timestamp
#             else:
#                 return str(timestamp)
#         except:
#             return str(timestamp)
#
#     @classmethod
#     def _format_status(cls, status: str, short: bool = False) -> str:
#         """格式化狀態"""
#         if not status:
#             return ""
#
#         status_upper = status.upper()
#         color = cls.STATUS_COLORS.get(status_upper, '')
#
#         if short:
#             status_map = {'RUNNING': 'RUN', 'PASS': 'OK', 'FAIL': 'ERR'}
#             display_status = status_map.get(status_upper, status_upper[:3])
#         else:
#             display_status = status_upper
#
#         return f"{color}{display_status}{cls.RESET}" if color else display_status
#
#     @classmethod
#     def _truncate_test_name(cls, test_name: str, max_length: int = None) -> str:
#         """
#         🔥 修改：現在返回完整的測試名稱，不進行截斷
#         保留此函數以維護向後兼容性
#         """
#         return test_name if test_name else ""


# src/ui/widgets/RunCaseWidget.py

"""
重構的 RunCaseWidget - 實現執行、組合和控制視圖接口
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from typing import Dict, List, Optional, Any
import json
import datetime

from src.controllers.execution_controller import ExecutionController
from src.mvc_framework.base_view import BaseView
from src.interfaces.execution_interface import (
    IExecutionView, ICompositionView, IControlView,
    IExecutionViewEvents, ICompositionViewEvents,
    ExecutionState, ExecutionProgress, TestItemStatus,
    ExecutionResult, TestItem, TestItemType
)
from src.ui.components.base import CollapsibleProgressPanel, BaseKeywordProgressCard
from src.utils import get_icon_path, Utils


class RunCaseWidget(BaseView, IExecutionView, ICompositionView, IControlView,
                    IExecutionViewEvents, ICompositionViewEvents):
    """
    重構的運行案例小部件
    實現所有執行相關的視圖接口和事件接口
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._execution_controller: Optional[ExecutionController] = None

        # 狀態管理
        self._current_execution_state = ExecutionState.IDLE
        self._current_execution_id: Optional[str] = None
        self._test_items: Dict[str, TestItem] = {}
        self._ui_widgets: Dict[str, QWidget] = {}
        self._current_highlighted_item: Optional[str] = None

        # 執行時間追蹤
        self._start_time: Optional[datetime.datetime] = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_execution_time)

        self._setup_ui()
        self._setup_connections()
        self._logger.info("TestCaseWidget initialized with MVC architecture")

    def _setup_connections(self):
        """設置信號連接"""
        # 連接基礎視圖的信號
        self.user_action.connect(self._handle_user_action)

    def register_controller(self, name: str, controller: ExecutionController) -> None:
        super().register_controller(name, controller)
        self._execution_controller = controller
        if controller:
            controller.register_view(self)
            self._logger.info("Execution controller set and view registered")

    # region ==================== build UI ====================

    def _setup_ui(self):
        """設置用戶界面"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)

        # 控制區域
        self._setup_control_area()

        # 分隔線
        # separator = QFrame()
        # separator.setFrameShape(QFrame.Shape.HLine)
        # separator.setFrameShadow(QFrame.Shadow.Sunken)
        # separator.setStyleSheet("background-color: #90006C4D;")
        # self.main_layout.addWidget(separator)

        # 執行結果區域
        # self._setup_execution_area()

        # 測試項目組合區域
        self._setup_composition_area()


    def _setup_control_area(self):
        """設置控制區域"""
        # 初始化按鈕配置
        self.button_config()

        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(8)
        control_layout.setContentsMargins(8, 8, 8, 8)

        # 創建並存儲按鈕引用
        self.buttons = {}

        # 運行控制按鈕組
        self.run_button_group = QWidget()
        run_layout = QHBoxLayout(self.run_button_group)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.setSpacing(8)

        for button_key, value in self.buttons_config.items():
            button = self._create_button(button_key, self.buttons_config[button_key])
            self.buttons[button_key] = button
            run_layout.addWidget(button)
            # 設置初始狀態
            if button_key in ["stop"]:
                button.setEnabled(False)

        # 時間顯示標籤
        self.time_label = QLabel("準備就緒")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                font-weight: bold; 
                color: #666;
                font-size: 12px;
                padding: 8px;
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 4px;
            }
        """)
        self.time_label.setMinimumWidth(150)

        # 佈局組裝
        control_layout.addWidget(self.run_button_group)
        control_layout.addStretch()
        control_layout.addWidget(self.time_label)
        self.main_layout.addWidget(control_frame)

    def _setup_composition_area(self):
        """設置組合區域"""
        # 組合標題
        # composition_label = QLabel("測試組合")
        # composition_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 4px; background-color: transparent;")
        # self.main_layout.addWidget(composition_label)

        # 滾動區域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setMinimumHeight(200)

        # 內容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(2)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 空狀態提示
        self.empty_label = QLabel("拖放測試案例或關鍵字到此處")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-style: italic; padding: 20px; font-size: 20px;")
        self.content_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area, 1)

    def _setup_execution_area(self):
        """設置執行結果區域"""
        # 進度條
        self.progress_frame = QFrame()
        self.progress_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        progress_layout = QVBoxLayout(self.progress_frame)

        self.progress_label = QLabel("執行進度")
        self.progress_label.setStyleSheet("font-weight: bold;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        self.main_layout.addWidget(self.progress_frame)

    def button_config(self):
        # 按鈕配置
        self.buttons_config = {
            "run": {
                "icon": get_icon_path("play_circle"),
                "slot": self.on_run_requested,
                "tooltip": "Run Robot framework",
                "text": "Run"
            },
            "stop": {
                "icon": get_icon_path("cancel"),
                "slot": self.on_stop_requested,
                "tooltip": "Stop Robot framework",
                "text": "Stop"
            },
            "export": {  # 調整按鈕順序以符合設計
                "icon": get_icon_path("file_download"),
                "slot": self._on_generate_clicked,
                "tooltip": "Generate Robot file",
                "text": "Export"  # 添加按鈕文字
            },
            "import": {
                "icon": get_icon_path("file import template"),
                "slot": self.on_import_requested,
                "tooltip": "Load existing Robot file",
                "text": "Import"
            },
            "report": {
                "icon": get_icon_path("picture_as_pdf"),
                "slot": self.on_report_requested,
                "tooltip": "Get Report file (PDF)",
                "text": "Report"
            },
            "clear": {
                "icon": get_icon_path("delete"),
                "slot": self._on_clear_clicked,
                "tooltip": "Clear test case",
                "text": "Clear"
            }
        }

    def _create_button(self, key: str, config: dict) -> QPushButton:
        """創建按鈕的通用方法"""
        button = QPushButton(config["text"])

        # 設置圖標
        if config.get("icon"):
            icon = QIcon(config["icon"])
            colored_icon = Utils.change_icon_color(icon, "#000000")
            button.setIcon(colored_icon)

        # 設置提示文字
        if config.get("tooltip"):
            button.setToolTip(config["tooltip"])

        # 連接信號
        if config.get("slot"):
            button.clicked.connect(config["slot"])

        # 設置對象名稱以便後續引用
        button.setObjectName(f"{key}_button")


        # 設置按鈕樣式
        button.setMinimumHeight(35)
        button.setMinimumWidth(80)

        # 應用不同的樣式主題
        if key == "run":
            # 執行控制按鈕樣式
            button.setStyleSheet("""
                                       QPushButton {
                                           background-color: #704CAF50;
                                           color: #000000;
                                           border: none;
                                           border-radius: 6px;
                                           padding: 8px 16px;
                                           font-weight: bold;
                                       }
                                       QPushButton:hover {
                                           background-color: #7045a049;
                                       }
                                       QPushButton:pressed {
                                           background-color: #703d8b40;
                                       }
                                       QPushButton:disabled {
                                           background-color: #70cccccc;
                                           color: #666666;
                                       }
                                   """)
        elif key == "stop":
            # 停止按鈕特殊樣式
            button.setStyleSheet("""
                                       QPushButton {
                                           background-color: #70f44336;
                                           color: #000000;
                                           border: none;
                                           border-radius: 6px;
                                           padding: 8px 16px;
                                           font-weight: bold;
                                       }
                                       QPushButton:hover {
                                           background-color: #50da190b;
                                       }
                                   """)
        elif key == "clear":
            # 停止按鈕特殊樣式
            button.setStyleSheet("""
                                       QPushButton {
                                           background-color: #70FDB813;
                                           color: #000000;
                                           border: none;
                                           border-radius: 6px;
                                           padding: 8px 16px;
                                           font-weight: bold;
                                       }
                                       QPushButton:hover {
                                           background-color: #70F2AA02;
                                       }
                                   """)
        else:
            # 其他按鈕樣式
            button.setStyleSheet("""
                                       QPushButton {
                                           background-color: #702196F3;
                                           color: #000000;
                                           border: none;
                                           border-radius: 6px;
                                           padding: 8px 16px;
                                       }
                                       QPushButton:hover {
                                           background-color: #701976D2;
                                       }
                                   """)


        return button

    # endregion

    #region ==================== IExecutionView 接口實現 ====================

    def update_execution_state(self, state: ExecutionState) -> None:
        """更新執行狀態"""
        old_state = self._current_execution_state
        self._current_execution_state = state

        self._logger.info(f"Execution state changed: {old_state.value} -> {state.value}")

        # 更新控制項狀態
        self.update_control_state(state)

        # 更新狀態顯示
        status_messages = {
            ExecutionState.IDLE: "準備就緒",
            ExecutionState.PREPARING: "準備中...",
            ExecutionState.RUNNING: "執行中...",
            ExecutionState.PAUSED: "已暫停",
            ExecutionState.STOPPING: "停止中...",
            ExecutionState.COMPLETED: "執行完成",
            ExecutionState.FAILED: "執行失敗",
            ExecutionState.CANCELLED: "已取消"
        }

        self.status_label.setText(status_messages.get(state, "未知狀態"))

        # 管理計時器
        if state == ExecutionState.RUNNING:
            if not self._start_time:
                self._start_time = datetime.datetime.now()
            self._timer.start(1000)  # 每秒更新一次
        elif state in [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED]:
            self._timer.stop()
        elif state == ExecutionState.PAUSED:
            self._timer.stop()

    def update_execution_progress(self, progress: ExecutionProgress) -> None:
        """更新執行進度"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(progress.total_items)
        self.progress_bar.setValue(progress.completed_items)

        # 更新進度文字
        progress_text = f"進度: {progress.completed_items}/{progress.total_items} ({progress.overall_progress}%)"

        if progress.current_item:
            progress_text += f" - 當前: {progress.current_item.name}"
            # 高亮當前執行項目
            self.highlight_current_item(progress.current_item.id)

        if progress.estimated_remaining_time:
            remaining_min = int(progress.estimated_remaining_time // 60)
            remaining_sec = int(progress.estimated_remaining_time % 60)
            progress_text += f" - 預計剩餘: {remaining_min:02d}:{remaining_sec:02d}"

        self.progress_label.setText(progress_text)

    def update_test_item_status(self, item_id: str, status: TestItemStatus,
                                progress: int = 0, error: str = "") -> None:
        """更新測試項目狀態"""
        if item_id in self._ui_widgets:
            widget = self._ui_widgets[item_id]

            # 更新UI顯示
            if hasattr(widget, 'update_status'):
                widget.update_status(status, progress, error)

            # 更新數據模型
            if item_id in self._test_items:
                item = self._test_items[item_id]
                item.status = status
                item.progress = progress
                item.error_message = error

        self._logger.debug(f"Test item {item_id} status updated to {status.value}")

    def show_execution_result(self, result: ExecutionResult) -> None:
        """顯示執行結果"""
        # 更新所有項目的最終狀態
        for item in result.test_items:
            self.update_test_item_status(item.id, item.status, 100, item.error_message)

        # 顯示執行摘要
        summary = (f"執行完成！\n"
                   f"總數: {result.total_tests}, "
                   f"通過: {result.passed_tests}, "
                   f"失敗: {result.failed_tests}, "
                   f"跳過: {result.skipped_tests}\n"
                   f"成功率: {result.success_rate:.1%}, "
                   f"耗時: {result.total_duration:.1f}秒")

        if result.state == ExecutionState.COMPLETED:
            self.show_success_message(summary)
        else:
            error_summary = "\n".join(result.error_summary) if result.error_summary else "未知錯誤"
            self.show_error_message(f"執行失敗!\n{summary}\n\n錯誤:\n{error_summary}")

    def reset_execution_display(self) -> None:
        """重置執行顯示"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("執行進度")
        self.status_label.setText("")
        self.time_label.setText("準備就緒")

        # 重置所有項目狀態
        for widget in self._ui_widgets.values():
            if hasattr(widget, 'reset_status'):
                widget.reset_status()

        # 清除高亮
        self.highlight_current_item(None)

        # 重置時間追蹤
        self._start_time = None
        self._timer.stop()

        self._logger.info("Execution display reset")
    # endregion

    # region ==================== ICompositionView 接口實現 ====================

    def add_test_item_ui(self, item: TestItem) -> None:
        """添加測試項目 UI"""
        # 如果是第一個項目，隱藏空狀態標籤
        if len(self._test_items) == 0:
            self.empty_label.setVisible(False)

        # 創建項目UI
        if item.type == TestItemType.TEST_CASE:
            widget = CollapsibleProgressPanel(item.config, self.content_widget)
        else:  # KEYWORD
            widget = BaseKeywordProgressCard(item.config, self.content_widget)

        # 設置右鍵選單
        self._setup_item_context_menu(widget, item.id)

        # 添加到佈局
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)

        # 保存引用
        self._test_items[item.id] = item
        self._ui_widgets[item.id] = widget

        self._logger.info(f"Added test item UI: {item.name} ({item.type.value})")

    def remove_test_item_ui(self, item_id: str) -> None:
        """移除測試項目 UI"""
        if item_id in self._ui_widgets:
            widget = self._ui_widgets[item_id]

            # 從佈局移除
            self.content_layout.removeWidget(widget)
            widget.hide()
            widget.deleteLater()

            # 清理引用
            del self._ui_widgets[item_id]
            del self._test_items[item_id]

            # 如果沒有項目了，顯示空狀態
            if len(self._test_items) == 0:
                self.empty_label.setVisible(True)

            self._logger.info(f"Removed test item UI: {item_id}")

    def update_test_item_order(self, ordered_item_ids: List[str]) -> None:
        """更新測試項目順序"""
        # 暫時移除所有項目（但不刪除）
        widgets_to_reorder = {}
        for item_id in ordered_item_ids:
            if item_id in self._ui_widgets:
                widget = self._ui_widgets[item_id]
                self.content_layout.removeWidget(widget)
                widgets_to_reorder[item_id] = widget

        # 按新順序重新添加
        for item_id in ordered_item_ids:
            if item_id in widgets_to_reorder:
                self.content_layout.insertWidget(
                    self.content_layout.count() - 1,  # 在空狀態標籤之前
                    widgets_to_reorder[item_id]
                )

        self._logger.info(f"Updated test item order: {ordered_item_ids}")

    def highlight_current_item(self, item_id: Optional[str]) -> None:
        """高亮當前執行項目"""
        # 清除之前的高亮
        if self._current_highlighted_item and self._current_highlighted_item in self._ui_widgets:
            old_widget = self._ui_widgets[self._current_highlighted_item]
            if hasattr(old_widget, 'set_highlighted'):
                old_widget.set_highlighted(False)

        # 設置新的高亮
        if item_id and item_id in self._ui_widgets:
            widget = self._ui_widgets[item_id]
            if hasattr(widget, 'set_highlighted'):
                widget.set_highlighted(True)

            # 滾動到當前項目
            self.scroll_area.ensureWidgetVisible(widget)

        self._current_highlighted_item = item_id

    def enable_composition_editing(self) -> None:
        """啟用組合編輯"""
        self.setAcceptDrops(True)
        self.buttons['clear'].setEnabled(True)

        # 啟用所有項目的編輯功能
        for widget in self._ui_widgets.values():
            if hasattr(widget, 'set_editable'):
                widget.set_editable(True)

    def disable_composition_editing(self) -> None:
        """禁用組合編輯"""
        self.setAcceptDrops(False)
        self.buttons['clear'].setEnabled(False)

        # 禁用所有項目的編輯功能
        for widget in self._ui_widgets.values():
            if hasattr(widget, 'set_editable'):
                widget.set_editable(False)

    def show_composition_validation_errors(self, errors: List[str]) -> None:
        """顯示組合驗證錯誤"""
        if errors:
            error_text = "組合驗證錯誤:\n" + "\n".join(f"• {error}" for error in errors)
            self.show_error_message(error_text)

    # endregion

    # region ==================== IControlView 接口實現 ====================

    def enable_run_controls(self) -> None:
        """啟用運行控制"""
        control = ["run", "export", "import"]
        for btn_key, config in self.buttons_config.items():
            if btn_key in control:
                self.buttons[btn_key].setEnabled(True)

    def disable_run_controls(self) -> None:
        """禁用運行控制"""
        for btn_key, config in self.buttons_config.items():
                self.buttons[btn_key].setEnabled(False)

    def update_control_state(self, state: ExecutionState) -> None:
        """根據執行狀態更新控制項"""
        if state == ExecutionState.IDLE:
            self.buttons["run"].setEnabled(len(self._test_items) > 0)
            self.buttons["stop"].setEnabled(False)
            self.enable_composition_editing()

        elif state == ExecutionState.RUNNING:
            self.buttons["run"].setEnabled(False)
            self.buttons["stop"].setEnabled(True)
            self.disable_composition_editing()

        elif state in [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED]:
            self.buttons["run"].setEnabled(len(self._test_items) > 0)
            self.buttons["stop"].setEnabled(False)
            self.enable_composition_editing()
            self.buttons["report"].setEnabled(True)

    def show_execution_time(self, elapsed_time: float,
                            estimated_remaining: Optional[float] = None) -> None:
        """顯示執行時間"""
        elapsed_min = int(elapsed_time // 60)
        elapsed_sec = int(elapsed_time % 60)
        time_text = f"已用時間: {elapsed_min:02d}:{elapsed_sec:02d}"

        if estimated_remaining:
            remaining_min = int(estimated_remaining // 60)
            remaining_sec = int(estimated_remaining % 60)
            time_text += f" | 預計剩餘: {remaining_min:02d}:{remaining_sec:02d}"

        self.time_label.setText(time_text)

    # endregion

    # region ==================== IExecutionViewEvents 接口實現 ====================

    def on_run_requested(self) -> None:
        """當請求運行時觸發"""
        if self._current_execution_state == ExecutionState.PAUSED:
            self.emit_user_action("resume_execution")
        else:
            self.emit_user_action("start_execution", {"test_items": list(self._test_items.values())})

    def on_pause_requested(self) -> None:
        """當請求暫停時觸發"""
        self.emit_user_action("pause_execution", {"execution_id": self._current_execution_id})

    def on_resume_requested(self) -> None:
        """當請求恢復時觸發"""
        self.emit_user_action("resume_execution", {"execution_id": self._current_execution_id})

    def on_stop_requested(self) -> None:
        """當請求停止時觸發"""
        if self.ask_user_confirmation("確定要停止當前執行嗎？", "確認停止"):
            self.emit_user_action("stop_execution", {"execution_id": self._current_execution_id})

    def on_generate_requested(self, config: Dict[str, Any]) -> None:
        """當請求生成時觸發"""
        self.emit_user_action("generate_test_file", config)

    def on_import_requested(self) -> None:
        """當請求導入時觸發"""
        self.emit_user_action("import_test_composition")

    def on_report_requested(self) -> None:
        """當請求報告時觸發"""
        self.emit_user_action("generate_execution_report", {"execution_id": self._current_execution_id})

    # endregion

    # region==================== ICompositionViewEvents 接口實現 ====================

    def on_test_item_dropped(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        """當測試項目被拖放時觸發"""
        self.emit_user_action("add_test_item", {
            "item_data": item_data,
            "item_type": item_type
        })

    def on_test_item_delete_requested(self, item_id: str) -> None:
        """當請求刪除測試項目時觸發"""
        if self.ask_user_confirmation("確定要刪除此測試項目嗎？", "確認刪除"):
            self.emit_user_action("remove_test_item", {"item_id": item_id})

    def on_test_item_move_requested(self, item_id: str, direction: str) -> None:
        """當請求移動測試項目時觸發"""
        self.emit_user_action("move_test_item", {
            "item_id": item_id,
            "direction": direction
        })

    def on_composition_cleared(self) -> None:
        """當組合被清空時觸發"""
        self.emit_user_action("clear_test_composition")

    # endregion

    # region ==================== 拖放事件處理 ====================

    def dragEnterEvent(self, event):
        """拖入事件"""
        if (event.mimeData().hasFormat('application/x-testcase') or
                event.mimeData().hasFormat('application/x-keyword')):
            if self._current_execution_state in [ExecutionState.IDLE, ExecutionState.COMPLETED,
                                                 ExecutionState.FAILED, ExecutionState.CANCELLED]:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖動事件"""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """放下事件"""
        mime_data = event.mimeData()

        try:
            if mime_data.hasFormat('application/x-testcase'):
                data = json.loads(mime_data.data('application/x-testcase').data().decode())
                self.on_test_item_dropped(data, TestItemType.TEST_CASE)

            elif mime_data.hasFormat('application/x-keyword'):
                data = json.loads(mime_data.data('application/x-keyword').data().decode())
                self.on_test_item_dropped(data, TestItemType.KEYWORD)

        except Exception as e:
            self._logger.error(f"Error handling drop event: {e}")
            self.show_error_message(f"處理拖放數據時發生錯誤: {str(e)}")

    # endregion

    # region ==================== 私有方法 ====================

    def _on_generate_clicked(self):
        """生成按鈕點擊處理"""
        # 可以在這裡打開配置對話框，然後調用 on_generate_requested
        config = {
            "format": "robot",
            "include_setup": True,
            "include_teardown": True,
            "test_name": f"Generated_Test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        self.on_generate_requested(config)

    def _on_clear_clicked(self):
        """清空按鈕點擊處理"""
        if len(self._test_items) > 0:
            if self.ask_user_confirmation("確定要清空所有測試項目嗎？", "確認清空"):
                self.on_composition_cleared()

    def _setup_item_context_menu(self, widget: QWidget, item_id: str):
        """設置項目右鍵選單"""

        def show_context_menu(pos):
            menu = QMenu(self)

            delete_action = menu.addAction("刪除")
            delete_action.triggered.connect(lambda: self.on_test_item_delete_requested(item_id))

            menu.addSeparator()

            move_up_action = menu.addAction("向上移動")
            move_up_action.triggered.connect(lambda: self.on_test_item_move_requested(item_id, "up"))

            move_down_action = menu.addAction("向下移動")
            move_down_action.triggered.connect(lambda: self.on_test_item_move_requested(item_id, "down"))

            menu.exec(widget.mapToGlobal(pos))

        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(show_context_menu)

    def _update_execution_time(self):
        """更新執行時間顯示"""
        if self._start_time and self._current_execution_state == ExecutionState.RUNNING:
            elapsed = (datetime.datetime.now() - self._start_time).total_seconds()
            self.show_execution_time(elapsed)

    def _handle_user_action(self, action_name: str, action_data: Any):
        """處理用戶操作信號"""
        self._logger.debug(f"User action: {action_name} with data: {action_data}")

    # endregion

    # region ==================== 公共方法 ====================

    def set_execution_id(self, execution_id: str):
        """設置當前執行ID"""
        self._current_execution_id = execution_id

    def get_test_items(self) -> List[TestItem]:
        """獲取所有測試項目"""
        return list(self._test_items.values())

    def get_current_execution_state(self) -> ExecutionState:
        """獲取當前執行狀態"""
        return self._current_execution_state
    # endregion