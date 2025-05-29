from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from numpy import long

from src.utils import Container
from src.ui.components.base import CollapsibleProgressPanel, BaseKeywordProgressCard
import json

import datetime
from typing import Dict, Any


class PrettyProgressPrinter:
    """漂亮的測試進度顯示器"""

    # ANSI 顏色代碼
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'GRAY': '\033[90m'
    }

    # 圖標
    ICONS = {
        'test_start': '🚀',
        'test_end': '✅',
        'keyword_start': '⚡',
        'keyword_end': '📝',
        'log': '📋',
        'running': '🔄',
        'pass': '✅',
        'fail': '❌',
        'error': '⚠️',
        'info': 'ℹ️'
    }

    def __init__(self, show_timestamp=True, use_colors=True, use_icons=True):
        self.show_timestamp = show_timestamp
        self.use_colors = use_colors
        self.use_icons = use_icons
        self.indent_level = 0

    def _colorize(self, text: str, color: str) -> str:
        """為文字添加顏色"""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['RESET']}"

    def _get_icon(self, icon_key: str) -> str:
        """獲取圖標"""
        if not self.use_icons:
            return ""
        return self.ICONS.get(icon_key, "") + " "

    def _get_timestamp(self) -> str:
        """獲取時間戳"""
        if not self.show_timestamp:
            return ""
        return f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "

    def _get_indent(self) -> str:
        """獲取縮排"""
        return "  " * self.indent_level

    def _format_test_start(self, data: Dict[str, Any]) -> str:
        """格式化測試開始訊息"""
        test_name = data.get('test_name', 'Unknown Test')
        icon = self._get_icon('test_start')
        timestamp = self._get_timestamp()
        indent = self._get_indent()

        header = "=" * 60
        title = f"{icon}開始測試: {test_name}"

        return (f"\n{self._colorize(header, 'CYAN')}\n"
                f"{timestamp}{indent}{self._colorize(title, 'CYAN')}\n"
                f"{self._colorize(header, 'CYAN')}")

    def _format_test_end(self, data: Dict[str, Any]) -> str:
        """格式化測試結束訊息"""
        test_name = data.get('test_name', 'Unknown Test')
        status = data.get('status', 'UNKNOWN')
        message = data.get('message', '')

        if status == 'PASS':
            icon = self._get_icon('pass')
            color = 'GREEN'
            status_text = "測試通過"
        elif status == 'FAIL':
            icon = self._get_icon('fail')
            color = 'RED'
            status_text = "測試失敗"
        else:
            icon = self._get_icon('test_end')
            color = 'YELLOW'
            status_text = f"測試結束 ({status})"

        timestamp = self._get_timestamp()
        indent = self._get_indent()

        result = (f"{timestamp}{indent}{icon}{self._colorize(status_text, color)}: "
                  f"{self._colorize(test_name, 'WHITE')}")

        if message:
            result += f"\n{timestamp}{indent}  {self._colorize('訊息:', 'GRAY')} {self._colorize(message, color)}"

        footer = "=" * 60
        result += f"\n{self._colorize(footer, 'GRAY')}\n"

        return result

    def _format_keyword_start(self, data: Dict[str, Any]) -> str:
        """格式化關鍵字開始訊息"""
        keyword_name = data.get('keyword_name', 'Unknown Keyword')
        icon = self._get_icon('keyword_start')
        timestamp = self._get_timestamp()
        indent = self._get_indent()

        return (f"{timestamp}{indent}{icon}{self._colorize('執行關鍵字:', 'BLUE')} "
                f"{self._colorize(keyword_name, 'WHITE')}")

    def _format_keyword_end(self, data: Dict[str, Any]) -> str:
        """格式化關鍵字結束訊息"""
        keyword_name = data.get('keyword_name', 'Unknown Keyword')
        status = data.get('status', 'UNKNOWN')
        message = data.get('message', '')

        if status == 'PASS':
            icon = self._get_icon('pass')
            color = 'GREEN'
            status_text = "完成"
        elif status == 'FAIL':
            icon = self._get_icon('fail')
            color = 'RED'
            status_text = "失敗"
        else:
            icon = self._get_icon('keyword_end')
            color = 'YELLOW'
            status_text = status

        timestamp = self._get_timestamp()
        indent = self._get_indent()

        result = (f"{timestamp}{indent}{icon}{self._colorize(f'關鍵字{status_text}:', color)} "
                  f"{self._colorize(keyword_name, 'DIM')}")

        if message:
            result += f"\n{timestamp}{indent}  {self._colorize('→', 'GRAY')} {self._colorize(message, color)}"

        return result

    def _format_log(self, data: Dict[str, Any]) -> str:
        """格式化日誌訊息"""
        level = data.get('level', 'INFO')
        message = data.get('message', '')
        keyword_name = data.get('keyword_name', '')

        if level == 'FAIL':
            icon = self._get_icon('fail')
            color = 'RED'
            level_text = "錯誤"
        elif level == 'ERROR':
            icon = self._get_icon('error')
            color = 'RED'
            level_text = "錯誤"
        elif level == 'WARN':
            icon = self._get_icon('error')
            color = 'YELLOW'
            level_text = "警告"
        else:
            icon = self._get_icon('info')
            color = 'CYAN'
            level_text = "資訊"

        timestamp = self._get_timestamp()
        indent = self._get_indent()

        result = f"{timestamp}{indent}{icon}{self._colorize(f'[{level_text}]', color)} {self._colorize(message, color)}"

        if keyword_name:
            result += f"\n{timestamp}{indent}  {self._colorize('來源:', 'GRAY')} {self._colorize(keyword_name, 'DIM')}"

        return result

    def update_progress(self, message: Dict[str, Any], test_id: int = None):
        """更新進度顯示"""
        try:
            msg_type = message.get('type', 'unknown')
            data = message.get('data', {})

            # 根據訊息類型調整縮排
            if msg_type == 'test_start':
                self.indent_level = 0
            elif msg_type in ['keyword_start', 'log']:
                self.indent_level = 1
            elif msg_type == 'keyword_end':
                self.indent_level = 1
            elif msg_type == 'test_end':
                self.indent_level = 1

            # 格式化不同類型的訊息
            if msg_type == 'test_start':
                formatted_msg = self._format_test_start(data)
            elif msg_type == 'test_end':
                formatted_msg = self._format_test_end(data)
            elif msg_type == 'keyword_start':
                formatted_msg = self._format_keyword_start(data)
            elif msg_type == 'keyword_end':
                formatted_msg = self._format_keyword_end(data)
            elif msg_type == 'log':
                formatted_msg = self._format_log(data)
            else:
                # 未知類型，使用簡單格式
                timestamp = self._get_timestamp()
                indent = self._get_indent()
                formatted_msg = f"{timestamp}{indent}{self._colorize('[未知]', 'GRAY')} {str(message)}"

            print(formatted_msg)

        except Exception as e:
            # 如果格式化失敗，回退到原始輸出
            print(f"{self._colorize('[錯誤]', 'RED')} 格式化失敗: {e}")
            print(f"> {str(message)}")


class RunCaseWidget(QWidget):
    update_ui = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.controller = Container.get_run_widget_controller()
        self.controller.set_view(self)
        self.theme_manager = self.parent().theme_manager
        self._setup_shadow()
        self.setContentsMargins(4, 8, 8, 4)
        self._setup_ui()

        self.test_cases = {}
        self.update_ui.connect(self._update_ui)

        # 添加接收計數器
        self._received_counter = 0
        self._received_messages = []

    def _setup_ui(self):
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 創建頂部輸入框
        # self.Name_LineEdit = QLabel()
        # self.Name_LineEdit.setFont(QFont("Arial", 30, QFont.Weight.Bold))
        # self.Name_LineEdit.setText("Working Area.")
        # self.Name_LineEdit.setFixedHeight(40)

        # 創建滾動區域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 創建內容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)  # 移除內容容器的邊距
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 設置滾動區域的內容
        self.scroll_area.setWidget(self.content_widget)

        # 設置列（column）的比例
        # self.main_layout.setColumnStretch(0, 15)
        # self.main_layout.setColumnStretch(1, 2)

        # 設置列（row）的比例
        # self.main_layout.setRowStretch(0, 1)
        # self.main_layout.setRowStretch(1, 15)

        # 添加到主布局  row column rowspan columnspan
        self.main_layout.addWidget(self.scroll_area)  # 使用-1讓容器填充所有剩餘行
        # self.main_layout.addWidget(self.Name_LineEdit, 0, 0, 1, 1, Qt.AlignmentFlag.AlignTop)

    def _setup_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-testcase') or event.mimeData().hasFormat('application/x-keyword'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        """
            x-testcase : 
                {'id': 'TEST_001', 
                 'name': 'Test Case 001, Test Case 001', 
                 'description': '測試功能A的運作情況', 
                 'setup': {
                    'preconditions': ['預先條件1', '預先條件2']}, 
                    'estimated_time': 300, 
                    'steps': [{'step_id': 1, 'name': '步驟1', 'action': '執行動作1', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果1'}, {'step_id': 2, 'name': '步驟2', 'action': '執行動作2', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果2'}, {'step_id': 3, 'name': '步驟3', 'action': '執行動作3', 'params': {'param1': '值1', 'param2': '值2'}, 'expected': '預期結果3'}, {'step_id': 4, 'name': '步驟4', 'action': '執行動作4', 'params': {'param1': '值3'}, 'expected': '預期結果4'}], 
                    'priority': 'required'
                    }

            x-keyword :
            {'id': 'send_can_message', 
             'config': {
                'id': 'send_can_message', 
                'name': 'send_can_message', 
                'category': 'battery', 
                'description': '發送 CAN 訊息', 
                'arguments': [
                    {'name': 'can_id', 'type': 'any', 'description': '', 'default': None, 'value': '401'}, 
                    {'name': 'payload', 'type': 'any', 'description': '', 'default': None, 'value': '00'}, 
                    {'name': 'node', 'type': 'any', 'description': '', 'default': '1', 'value': '1'}, 
                    {'name': 'can_type', 'type': 'any', 'description': '', 'default': '0', 'value': '0'}], 
                'returns': '', 
                'priority': 'optional'}
            }




        """
        if mime_data.hasFormat('application/x-testcase'):
            data = mime_data.data('application/x-testcase')
            data_type = 'testcase'
        elif mime_data.hasFormat('application/x-keyword'):
            data = mime_data.data('application/x-keyword')
            data_type = 'keyword'
            # print( data )
        else:
            return



        case_data = json.loads(str(data, encoding='utf-8'))
        # print( "Drop data : " + str(case_data) )
        self.add_item(case_data, data_type)
        event.acceptProposedAction()

    def add_item(self, case_data, data_type):
        """
        根據不同類型創建不同的面板

        Args:
            case_data: 拖放的數據
            data_type: 'testcase' 或 'keyword'
        """
        if data_type == 'testcase':
            # 創建測試案例面板
            panel = CollapsibleProgressPanel(case_data['config'], parent=self)
            # 連接右鍵選單信號
            panel.delete_requested.connect(self.handle_delete_item)
            panel.move_up_requested.connect(self.handle_move_up_item)
            panel.move_down_requested.connect(self.handle_move_down_item)
        else:
            # 創建關鍵字面板
            panel = BaseKeywordProgressCard(case_data['config'], parent=self)
            # 連接右鍵選單信號
            panel.delete_requested.connect(self.handle_delete_item)
            panel.move_up_requested.connect(self.handle_move_up_item)
            panel.move_down_requested.connect(self.handle_move_down_item)


        self.content_layout.addWidget(panel)

        panel_id = id(panel)

        self.test_cases[panel_id] = {
            'panel': panel,
            'data': case_data,  # json
            'type': data_type  # testcase keyword
        }

        # 確保新添加的面板可見
        self.scroll_area.ensureWidgetVisible(panel)

    def _update_ui(self):
        self.update()
        self.repaint()

    def get_name_text(self):
        return "Untitled"
        # if (self.Name_LineEdit.text() == ""):
        #     return "Untitled"
        # else:
        #     return self.Name_LineEdit.text()

    def update_progress(self, message: dict, test_id: long):
        """更新進度顯示 - 增強接收追蹤版本"""
        self._received_counter += 1
        msg_type = message.get('type', 'unknown')
        #
        # print(f"[UI] 🔥 #{self._received_counter} Received: {msg_type} for test_id: {test_id}")
        #
        # 記錄接收的訊息
        message_record = {
            'counter': self._received_counter,
            'type': msg_type,
            'test_id': test_id,
            'timestamp': QDateTime.currentDateTime().toString()
        }
        self._received_messages.append(message_record)

        panel = self.test_cases[test_id]['panel']
        panel.update_status(message)
        self._update_ui()


    def reset_test(self):
        for panel in self.test_cases.values():
            panel['panel'].reset_status()

    def test_finished(self, result: bool):
        print(f"[UI] 📋 Received messages history ({ self._received_counter }): {[m['type'] for m in self._received_messages]}")

    # 新增處理右鍵選單動作的方法
    def handle_delete_item(self, panel):
        """處理刪除項目"""
        # 找到對應的panel_id
        panel_id = id(panel)

        if panel_id in self.test_cases:
            # 從布局中移除
            self.content_layout.removeWidget(panel)
            # 隱藏和刪除panel
            panel.hide()
            panel.deleteLater()
            # 從字典中移除
            del self.test_cases[panel_id]
            # 更新UI
            self._update_ui()

    def handle_move_up_item(self, panel):
        """處理向上移動項目"""
        # 找到當前項目在佈局中的索引
        index = self.content_layout.indexOf(panel)

        # 檢查是否可以上移（不是第一個）
        if index > 0:
            # 從佈局中移除
            self.content_layout.removeWidget(panel)
            # 在新位置添加
            self.content_layout.insertWidget(index - 1, panel)
            # 重新構建 test_cases 字典以保持正確順序
            self._rebuild_test_cases_order()
            # 更新UI
            self._update_ui()

    def handle_move_down_item(self, panel):
        """處理向下移動項目"""
        # 找到當前項目在佈局中的索引
        index = self.content_layout.indexOf(panel)

        # 檢查是否可以下移（不是最後一個）
        if index < self.content_layout.count() - 1:
            # 從佈局中移除
            self.content_layout.removeWidget(panel)
            # 在新位置添加
            self.content_layout.insertWidget(index + 1, panel)
            # 重新構建 test_cases 字典以保持正確順序
            self._rebuild_test_cases_order()
            # 更新UI
            self._update_ui()

    def _rebuild_test_cases_order(self):
        """重新構建 test_cases 字典以反映當前布局順序"""
        # 備份當前的 test_cases 數據
        old_test_cases = self.test_cases.copy()
        # 清空當前字典
        self.test_cases.clear()

        # 按照布局順序重新構建字典
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget:  # 確保 widget 存在
                panel_id = id(widget)
                # 如果在舊字典中找到對應數據，則添加到新字典
                if panel_id in old_test_cases:
                    self.test_cases[panel_id] = old_test_cases[panel_id]

    def get_test_cases_in_order(self):
        """獲取按照當前布局順序排列的測試用例列表"""
        ordered_cases = []
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                panel_id = id(widget)
                if panel_id in self.test_cases:
                    ordered_cases.append(self.test_cases[panel_id])
        return ordered_cases