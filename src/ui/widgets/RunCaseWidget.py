import uuid
from pickle import FALSE

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
        self._test_items: Dict[str, TestItem] = {}
        self._ui_widgets: Dict[str, QWidget] = {}
        self._ui_states: Dict[str, Any] = {}

        # 執行時間追蹤
        # self._start_time: Optional[datetime.datetime] = None
        # self._timer = QTimer()
        # self._timer.timeout.connect(self._update_execution_time)

        self._setup_ui()
        self._setup_connections()

        # 添加接收計數器
        self._received_counter = 0
        self._received_messages = []
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

        # 創建並存儲按鈕引用
        self.buttons = {}

        # 控制區域
        self._setup_control_area()

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
        # self.time_label = QLabel("準備就緒")
        # self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.time_label.setStyleSheet("""
        #     QLabel {
        #         font-weight: bold;
        #         color: #666;
        #         font-size: 12px;
        #         padding: 8px;
        #         background-color: rgba(0, 0, 0, 0.05);
        #         border-radius: 4px;
        #     }
        # """)
        # self.time_label.setMinimumWidth(150)

        # 佈局組裝
        control_layout.addWidget(self.run_button_group)
        control_layout.addStretch()
        # control_layout.addWidget(self.time_label)
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
                                       QPushButton:pressed {
                                           background-color: #50c6281f;        
                                       }
                                       QPushButton:disabled {
                                           background-color: #70cccccc;
                                           color: #666666;
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
                                       QPushButton:pressed {
                                           background-color: #709d8c0b;
                                       }
                                       QPushButton:disabled {
                                           background-color: #70cccccc;
                                           color: #666666;
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
                                       QPushButton:pressed {
                                           background-color: #70145bbf;
                                       }
                                       QPushButton:disabled {
                                           background-color: #70cccccc;
                                           color: #666666;
                                       }
                                   """)


        return button

    # endregion

    #region ==================== IExecutionView 接口實現 ====================

    def update_progress( self, message: dict, test_id ):
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

        panel = self._ui_widgets[test_id]
        panel.update_status(message)
        self._update_ui()

    def execution_state_changed(self, old_state: ExecutionState, new_state: ExecutionState):
        """ 根據狀態變化，設定 button Enable/Disable """
        if new_state == ExecutionState.IDLE:
            for btn_type, btn_obj in self.buttons.items() :
                if ( btn_type == "stop" ):
                    btn_obj.setEnabled(False)
                else :
                    btn_obj.setEnabled(True)
            print(f"[RunCaseWidget] execution_state_changed: {old_state} -> {new_state}")

        else:
            for btn_type, btn_obj in self.buttons.items() :
                if (btn_type == "stop"):
                    btn_obj.setEnabled(True)
                else:
                    btn_obj.setEnabled(False)
            print(f"[RunCaseWidget] execution_state_changed: {old_state} -> {new_state}")


    # endregion

    # region ==================== ICompositionView 接口實現 ====================

    def add_test_item_ui(self, item: TestItem, insert_index: Optional[int] = None) -> None:
        """
        添加測試項目 UI - 支援指定位置插入

        Args:
            item: 測試項目
            insert_index: 插入位置索引（None表示插入到末尾）
        """
        # 如果是第一個項目，隱藏空狀態標籤
        if len(self._test_items) == 0:
            self.empty_label.setVisible(False)

        # 創建項目UI
        if item.type == TestItemType.TEST_CASE:
            widget = CollapsibleProgressPanel(item.config, self.content_widget)
        else:  # KEYWORD
            widget = BaseKeywordProgressCard(item.config, self.content_widget)

        # 連接信號
        widget.delete_requested.connect(
            lambda: self.on_test_item_delete_requested(item.id)
        )
        widget.move_up_requested.connect(
            lambda: self.on_test_item_move_requested(item.id, "up")
        )
        widget.move_down_requested.connect(
            lambda: self.on_test_item_move_requested(item.id, "down")
        )

        # 設置右鍵選單
        self._setup_item_context_menu(widget, item.id)

        # 根據 insert_index 決定插入位置
        if insert_index is not None and insert_index < self.content_layout.count() - 1:
            # 插入到指定位置（在空狀態標籤之前）
            self.content_layout.insertWidget(insert_index, widget)
        else:
            # 插入到末尾（在空狀態標籤之前）
            self.content_layout.insertWidget(self.content_layout.count() - 1, widget)

        # 保存引用
        self._test_items[item.id] = item
        self._ui_widgets[item.id] = widget

        self.scroll_area.ensureWidgetVisible(widget)
        self._logger.info(f"Added test item UI: {item.name} ({item.type.value}) at index {insert_index}")

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

    def clear_all_test_items_ui(self) -> None:
        """
        清空所有測試項目的 UI（由 Controller 調用）
        """
        try:
            # 1. 移除所有 widgets
            for item_id, widget in list(self._ui_widgets.items()):
                self.content_layout.removeWidget(widget)
                widget.hide()
                widget.deleteLater()

            # 2. 清空引用
            self._ui_widgets.clear()
            self._test_items.clear()

            # 3. 顯示空狀態
            self.empty_label.setVisible(True)

            self._logger.info("All test items cleared from UI")

        except Exception as e:
            self._logger.error(f"Error clearing test items UI: {e}")


    # endregion

    # region ==================== IControlView 接口實現 ====================

    def enable_run_controls(self) -> None:
        """啟用運行控制"""
        for btn_key, config in self.buttons_config.items():
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

    # endregion

    # region ==================== IExecutionViewEvents 接口實現 ====================

    def on_run_requested(self) -> None:
        """當請求運行時觸發"""
        self.emit_user_action("start_execution", {"test_items": list(self._test_items.values())})

    def on_stop_requested(self) -> None:
        """當請求停止時觸發"""
        if self.ask_user_confirmation("確定要停止當前執行嗎？", "確認停止"):
            self.emit_user_action("stop_execution")

    def on_generate_requested(self, config: Dict[str, Any]) -> None:
        """當請求生成時觸發"""
        self.emit_user_action("generate_test_file", config)

    def on_import_requested(self) -> None:
        """當請求導入時觸發"""
        self.emit_user_action("import_test_composition")

    def on_report_requested(self) -> None:
        """當請求報告時觸發"""
        self.emit_user_action("generate_execution_report")

    # endregion

    # region==================== ICompositionViewEvents 接口實現 ====================

    def on_test_item_dropped(self, item_data: Dict[str, Any],
                             item_type: TestItemType,
                             insert_index: Optional[int] = None) -> None:
        """
        當測試項目被拖放時觸發 - 支援指定位置插入

        Args:
            item_data: 項目數據
            item_type: 項目類型
            insert_index: 插入位置索引（None表示插入到末尾）
        """
        # 生成穩定的唯一 ID
        item_id = str(uuid.uuid4())

        # 創建標準的 TestItem 數據結構
        test_item = TestItem(
            id=item_id,
            type=item_type,
            name=item_data.get('name', ''),
            config=item_data.get('config', item_data),
            status=TestItemStatus.WAITING,
            progress=0
        )

        self.emit_user_action("add_test_item", {
            "item_data": {
                "test_item": test_item,
                "test_data": item_data
            },
            "item_type": item_type,
            "insert_index": insert_index  # 新增位置參數
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
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖動事件 - 添加位置指示"""
        if (event.mimeData().hasFormat('application/x-testcase') or
                event.mimeData().hasFormat('application/x-keyword')):

            # 計算插入位置並顯示視覺提示
            insert_index = self._calculate_drop_position(event.pos())
            self._show_drop_indicator(insert_index)

            event.acceptProposedAction()
        else:
            self._hide_drop_indicator()
            event.ignore()

    def dropEvent(self, event):
        """放下事件 - 支援位置插入"""
        mime_data = event.mimeData()

        # 隱藏位置指示器
        self._hide_drop_indicator()

        try:
            # 計算插入位置
            insert_index = self._calculate_drop_position(event.pos())

            if mime_data.hasFormat('application/x-testcase'):
                data = json.loads(mime_data.data('application/x-testcase').data().decode())
                self.on_test_item_dropped(data, TestItemType.TEST_CASE, insert_index)

            elif mime_data.hasFormat('application/x-keyword'):
                data = json.loads(mime_data.data('application/x-keyword').data().decode())
                self.on_test_item_dropped(data, TestItemType.KEYWORD, insert_index)

        except Exception as e:
            self._logger.error(f"Error handling drop event: {e}")
            self.show_error_message(f"處理拖放數據時發生錯誤: {str(e)}")

    def _calculate_drop_position(self, drop_pos):
        """
        計算拖放位置對應的插入索引

        Args:
            drop_pos: QPoint - 拖放位置座標

        Returns:
            int - 插入索引（0為最前面，len(items)為最後面）
        """
        # 將座標轉換為 content_widget 的本地座標
        local_pos = self.content_widget.mapFromParent(drop_pos)
        drop_y = local_pos.y()

        # 如果沒有任何項目，插入到第一個位置
        if len(self._ui_widgets) == 0:
            return 0

        # 獲取所有 widget 的位置信息
        widget_positions = []
        layout = self.content_layout

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() and item.widget() in self._ui_widgets.values():
                widget = item.widget()
                widget_rect = widget.geometry()
                widget_positions.append({
                    'index': i,
                    'widget': widget,
                    'top': widget_rect.top(),
                    'bottom': widget_rect.bottom(),
                    'center': widget_rect.top() + widget_rect.height() // 2
                })

        # 按位置排序
        widget_positions.sort(key=lambda x: x['top'])

        # 找到插入位置
        for i, widget_info in enumerate(widget_positions):
            if drop_y < widget_info['center']:
                return i  # 插入到這個 widget 之前

        # 如果drop位置在所有widget之後，插入到最後
        return len(widget_positions)

    def _show_drop_indicator(self, insert_index):
        """
        顯示拖放位置指示器

        Args:
            insert_index: int - 插入位置索引
        """
        # 移除之前的指示器
        self._hide_drop_indicator()

        # 創建拖放指示器
        if not hasattr(self, '_drop_indicator'):
            self._drop_indicator = QFrame(self.content_widget)
            self._drop_indicator.setFixedHeight(3)
            self._drop_indicator.setStyleSheet("""
                QFrame {
                    background-color: #4CAF50;
                    border-radius: 1px;
                    margin: 2px 10px;
                }
            """)

        # 插入指示器到指定位置
        self.content_layout.insertWidget(insert_index, self._drop_indicator)
        self._drop_indicator.show()

    def _hide_drop_indicator(self):
        """隱藏拖放位置指示器"""
        if hasattr(self, '_drop_indicator') and self._drop_indicator:
            self.content_layout.removeWidget(self._drop_indicator)
            self._drop_indicator.hide()

    def dragLeaveEvent(self, event):
        """拖動離開事件"""
        self._hide_drop_indicator()
        super().dragLeaveEvent(event)

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

    def _handle_user_action(self, action_name: str, action_data: Any):
        """處理用戶操作信號"""
        self._logger.debug(f"User action: {action_name} with data: {action_data}")

    # endregion


    def get_test_items(self) -> List[TestItem]:
        """獲取所有測試項目"""
        return list(self._test_items.values())
    def _update_ui(self):
        self.update()
        self.repaint()


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

