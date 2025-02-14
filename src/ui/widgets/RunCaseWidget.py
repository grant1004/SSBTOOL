from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from src.utils import Container
from src.ui.components.base import CollapsibleProgressPanel, BaseKeywordProgressCard
import json


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
        self.update_ui.connect( self._update_ui )


    def _setup_ui(self):
        self.main_layout = QGridLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 創建頂部輸入框
        self.Name_LineEdit = QLineEdit()
        self.Name_LineEdit.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.Name_LineEdit.setPlaceholderText("Enter Test Case Name")
        self.Name_LineEdit.setFixedHeight(40)

        # 創建容器widget來包含scroll area並設置padding
        # self.scroll_container = QWidget()
        # scroll_container_layout = QVBoxLayout(self.scroll_container)
        # scroll_container_layout.setContentsMargins(0, 28, 0, 0)  # 頂部25的padding
        # scroll_container_layout.setSpacing(0)

        # 創建滾動區域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 創建內容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0,0,0,0)  # 移除內容容器的邊距
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 設置滾動區域的內容
        self.scroll_area.setWidget(self.content_widget)

        # 將scroll area添加到容器中
        # scroll_container_layout.addWidget(self.scroll_area)

        # 設置列（column）的比例
        self.main_layout.setColumnStretch(0, 15)
        self.main_layout.setColumnStretch(1, 2)

        # 設置列（row）的比例
        self.main_layout.setRowStretch(0, 1)
        self.main_layout.setRowStretch(1, 15)

        # 添加到主布局  row column rowspan columnspan
        self.main_layout.addWidget(self.scroll_area, 1, 0, -1, 2)  # 使用-1讓容器填充所有剩餘行
        self.main_layout.addWidget(self.Name_LineEdit, 0, 0, 1, 1, Qt.AlignmentFlag.AlignTop)

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
                    {'id': 'BMS_MCU_Reset', 
                     'name': 'BMS_MCU_Reset', 
                     'category': 'common', 
                     'description': '', 
                     'arguments': [], 
                     'returns': '', 
                     'priority': 'required'
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
        else:
            # 創建關鍵字面板
            panel = BaseKeywordProgressCard(case_data['config'], parent=self)

        # 添加到內容布局
        self.content_layout.addWidget(panel)
        panel_id = id(panel)
        # print( panel_id )
        # 保存引用
        self.test_cases[panel_id]= {
            'panel': panel,
            'data': case_data, # json
            'type': data_type  # testcase keyword
        }

        # 確保新添加的面板可見
        self.scroll_area.ensureWidgetVisible(panel)

    def _update_ui(self):
        self.update()
        self.repaint()

    def get_name_text(self):
        if ( self.Name_LineEdit.text() == "" ):
            return "Untitled"
        else:
            return self.Name_LineEdit.text()

    def update_progress(self, message_str):
        """更新進度顯示"""
        try:
            import ast

            message = ast.literal_eval(message_str)

            test_name = message['data']['test_name']
            msg_type = message['type']
            if msg_type == 'testcase':
                panel_id = message['panel_id']
                panel = self.test_cases[panel_id]['panel']
                panel.update_progress(message)
            elif msg_type == 'keyword':
                panel_id = message['panel_id']
                panel = self.test_cases[panel_id]['panel']
                panel.update_progress(message)

        except Exception as e:
            print(f"Error parsing message: {e}")


    def update_test_status(self, success):
        """更新測試狀態"""
