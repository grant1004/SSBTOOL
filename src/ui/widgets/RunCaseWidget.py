from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from numpy import long

from src.utils import Container
from src.ui.components.base import CollapsibleProgressPanel, BaseKeywordProgressCard
import json

import datetime
from typing import Dict, Any

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
        test_name = message.get('data', {}).get('test_name', '')
        key_word = message.get('data', {}).get('keyword_name', '')
        # 記錄接收的訊息
        message_record = {
            'counter': self._received_counter,
            'test_name': test_name,
            'keyword': key_word,
            'type': msg_type,
            'test_id': test_id,
            'timestamp': QDateTime.currentDateTime().toString(),
            'message' : message
        }
        self._received_messages.append(message_record)

        panel = self.test_cases[test_id]['panel']
        panel.update_status(message)
        self._update_ui()

    def reset_test(self):
        for panel in self.test_cases.values():
            panel['panel'].reset_status()

    def test_finished(self, success : bool ) :
        for msg in self._received_messages :
            # print( msg['message'] )
            formatted = PrettyMessageFormatter.format_message(msg)
            print(formatted)
        self._received_messages.clear()

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

class PrettyMessageFormatter:
    """漂亮的消息格式化器"""

    # 🎨 消息類型顏色和符號
    TYPE_STYLES = {
        'test_start': {'emoji': '🚀', 'color': '\033[92m', 'label': 'TEST_START'},  # 綠色
        'test_end': {'emoji': '🏁', 'color': '\033[94m', 'label': 'TEST_END'},  # 藍色
        'keyword_start': {'emoji': '▶️', 'color': '\033[93m', 'label': 'KW_START'},  # 黃色
        'keyword_end': {'emoji': '✅', 'color': '\033[95m', 'label': 'KW_END'},  # 紫色
        'log': {'emoji': '📝', 'color': '\033[96m', 'label': 'LOG'},  # 青色
        'error': {'emoji': '❌', 'color': '\033[91m', 'label': 'ERROR'},  # 紅色
        'unknown': {'emoji': '❓', 'color': '\033[90m', 'label': 'UNKNOWN'},  # 灰色
    }

    # 🎨 狀態顏色
    STATUS_COLORS = {
        'PASS': '\033[92m',  # 綠色
        'FAIL': '\033[91m',  # 紅色
        'RUNNING': '\033[93m',  # 黃色
        'SKIP': '\033[90m',  # 灰色
    }

    # 重置顏色
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def format_message(cls, msg: Dict[str, Any], compact: bool = False) -> str:
        """
        格式化消息為漂亮的輸出

        Args:
            msg: 消息字典
            compact: 是否使用緊湊格式
        """
        if compact:
            return cls._format_compact(msg)
        else:
            return cls._format_detailed(msg)

    @classmethod
    def _format_detailed(cls, msg: Dict[str, Any]) -> str:
        """詳細格式化"""

        # 獲取基本信息
        counter = msg.get('counter', '?')
        msg_type = msg.get('type', 'unknown')
        keyword = msg.get('keyword', '')
        test_name = msg.get('test_name', '')
        test_id = msg.get('test_id', '')
        timestamp = msg.get('timestamp', '')
        status = msg.get('status', '')

        # 獲取樣式
        style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
        emoji = style['emoji']
        color = style['color']
        label = style['label']

        # 格式化時間戳
        formatted_time = cls._format_timestamp(timestamp)

        # 🔥 使用完整的測試名稱（不截斷）
        full_test_name = test_name

        # 格式化狀態
        formatted_status = cls._format_status(status)

        # 構建輸出
        lines = []

        # 主要信息行
        header = f"{color}{cls.BOLD}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"

        if keyword:
            header += f" │ 🔧 {cls.BOLD}{keyword}{cls.RESET}"

        if formatted_status:
            header += f" │ {formatted_status}"

        lines.append(header)

        # 詳細信息行
        if test_id:
            lines.append(f"    📋 Test ID: {cls.BOLD}{test_id}{cls.RESET}")

        # 🔥 顯示完整測試名稱
        if full_test_name:
            lines.append(f"    📝 Test: {full_test_name}")

        # 🔥 如果有keyword，單獨顯示一行
        if keyword:
            lines.append(f"    🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}")

        if formatted_time:
            lines.append(f"    ⏰ Time: {formatted_time}")

        # 分隔線（可選）
        if counter and int(str(counter)) % 5 == 0:
            lines.append(f"    {'-' * 100}")

        return '\n'.join(lines)

    @classmethod
    def _format_compact(cls, msg: Dict[str, Any]) -> str:
        """緊湊格式化 - 顯示完整信息"""

        counter = msg.get('counter', '?')
        msg_type = msg.get('type', 'unknown')
        keyword = msg.get('keyword', '')
        test_name = msg.get('test_name', '')
        test_id = msg.get('test_id', '')
        status = msg.get('status', '')
        timestamp = msg.get('timestamp', '')

        # 獲取樣式
        style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
        emoji = style['emoji']
        color = style['color']
        label = style['label']

        # 格式化狀態
        status_str = f" [{cls._format_status(status, short=True)}]" if status else ""

        # 格式化時間
        time_str = cls._format_timestamp(timestamp)
        time_display = f" ⏰{time_str}" if time_str else ""

        # 🔥 構建完整的輸出行
        lines = []

        # 主要信息行
        main_line = (f"{color}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"
                     f" │ 🆔{test_id}{status_str}{time_display}")
        lines.append(main_line)

        # 🔥 如果有keyword，顯示keyword行
        if keyword:
            keyword_line = f"     🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}"
            lines.append(keyword_line)

        # 🔥 如果有完整測試名稱，顯示測試名稱行
        if test_name:
            test_line = f"     📝 Test: {test_name}"
            lines.append(test_line)

        return '\n'.join(lines)

    @classmethod
    def _format_timestamp(cls, timestamp: Any) -> str:
        """格式化時間戳"""
        if not timestamp:
            return ""

        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%H:%M:%S.%f")[:-3]  # 保留毫秒
            elif isinstance(timestamp, str):
                return timestamp
            else:
                return str(timestamp)
        except:
            return str(timestamp)

    @classmethod
    def _format_status(cls, status: str, short: bool = False) -> str:
        """格式化狀態"""
        if not status:
            return ""

        status_upper = status.upper()
        color = cls.STATUS_COLORS.get(status_upper, '')

        if short:
            status_map = {'RUNNING': 'RUN', 'PASS': 'OK', 'FAIL': 'ERR'}
            display_status = status_map.get(status_upper, status_upper[:3])
        else:
            display_status = status_upper

        return f"{color}{display_status}{cls.RESET}" if color else display_status

    @classmethod
    def _truncate_test_name(cls, test_name: str, max_length: int = None) -> str:
        """
        🔥 修改：現在返回完整的測試名稱，不進行截斷
        保留此函數以維護向後兼容性
        """
        return test_name if test_name else ""
