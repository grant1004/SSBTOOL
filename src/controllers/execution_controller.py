import asyncio
from typing import Dict, List, Optional, Any, Set
from PySide6.QtCore import QObject, Signal, QTimer, Qt

from src.business_models.execution_business_model import TestExecutionBusinessModel
# 導入接口
from src.interfaces.execution_interface import (
    IExecutionController, ITestExecutionBusinessModel, ITestCompositionModel, IReportGenerationModel,
    TestItem, ExecutionResult, ExecutionConfiguration, TestItemType, IExecutionView, ICompositionView,
    IControlView, ExecutionState
)

# 導入 MVC 基類
from src.mvc_framework.base_controller import BaseController
from src.mvc_framework.event_bus import event_bus


class ExecutionController(BaseController, IExecutionController):



    def __init__(self, execution_business_model: TestExecutionBusinessModel):
        super().__init__()
        # 註冊業務模型
        self._run_case_views = None
        self._composition_views = None
        self._control_views = None

        self.register_model("execution_business_model", execution_business_model)
        self.execution_business_model = execution_business_model


    #region BaseController
    def register_view(self, view) -> None:
        """註冊測試案例視圖"""
        registered_as = []

        # 檢查並註冊執行視圖介面
        if isinstance(view, IExecutionView):
            self._run_case_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("IExecutionView")

        # 檢查並註冊組合視圖介面
        if isinstance(view, ICompositionView):
            self._composition_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("ICompositionView")

        # 檢查並註冊控制視圖介面
        if isinstance(view, IControlView):
            self._control_views = view
            if view not in self._device_views:
                self._device_views.append(view)
                registered_as.append("IControlView")

        view.user_action.connect(self.handle_user_action)
        self.execution_business_model.test_progress.connect(
            self._run_case_views.update_progress, Qt.ConnectionType.QueuedConnection
        )
        if registered_as:
            interfaces_str = ", ".join(registered_as)
            self._logger.info(f"Registered {type(view).__name__} as: {interfaces_str}")
        else:
            self._logger.warning(f"No recognized interfaces found for {type(view).__name__}")

    def _get_action_handler_map(self) -> Dict[str, callable]:
        """
        🔑 關鍵：將用戶操作映射到 IExecutionController 接口方法
        """
        return {
            # 執行相關操作 -> IExecutionController 方法
            "start_execution": self.handle_run_request,
            "stop_execution": self.handle_stop_request,

            # 組合相關操作 -> IExecutionController 方法
            "add_test_item": self.handle_test_item_added,
            "remove_test_item": self.handle_test_item_removed,
            "move_test_item": self.handle_test_item_moved,
            "clear_test_composition": self.handle_test_item_clear,

            # 文件操作 -> IExecutionController 方法
            "generate_test_file": self.handle_generate_request,
            "import_test_composition": self.handle_import_request,
            "generate_execution_report": self.handle_report_request,
        }


    #endregion

    #region 組合相關操作

    def handle_test_item_added(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        """
        處理測試項目添加

        這裡的 item_data 包含：
        - test_item: TestItem 實例
        - item_data: 原始數據
        - item_type: 項目類型
        """
        test_item = item_data.get('test_item')
        success = self.execution_business_model.add_test_item(test_item)

        if success:
            # 3. 通知 View 更新 UI（如果需要)
            if self._composition_views:
                self._composition_views.add_test_item_ui(test_item)

            self._logger.info(f"Test item added: {test_item.id}")

        else:
            self._logger.error(f"Failed to add test item: {test_item.id}")

    def handle_test_item_removed(self, item_id: str) -> None:
        success = self.execution_business_model.remove_test_item(item_id)

        if success:
            # 3. 通知 View 更新 UI（如果需要)
            if self._composition_views:
                self._composition_views.remove_test_item_ui(item_id)

            self._logger.info(f"Test item remove: {item_id}")

        else:
            self._logger.error(f"Failed to remove test item: {item_id}")

    def handle_test_item_moved(self, item_id: str, direction: str) -> None:
        """
        處理測試項目移動請求

        協調流程：
        1. 獲取當前順序
        2. 計算新位置
        3. 更新 Model
        4. 通知 View 更新顯示
        """
        try:
            # 1. 從 Model 獲取當前項目順序
            current_order = self.execution_business_model.get_item_order()

            if item_id not in current_order:
                self._logger.error(f"Item {item_id} not found in current order")
                return

            # 2. 計算新位置
            current_index = current_order.index(item_id)
            new_index = self._calculate_new_position(current_index, direction, len(current_order))

            if new_index == current_index:
                self._logger.info("Item already at boundary, cannot move")
                return

            # 3. 在 Model 中更新位置
            success = self.execution_business_model.move_test_item(item_id, new_index)

            if success:
                # 4. 獲取更新後的順序
                new_order = self.execution_business_model.get_item_order()

                # 5. 通知所有 View 更新顯示
                if self._composition_views:
                    self._composition_views.update_test_item_order(new_order)

                # 6. 發送狀態變更信號
                self.state_changed.emit("item_order", new_order)

                self._logger.info(f"Moved item {item_id} from {current_index} to {new_index}")
            else:
                self._logger.error(f"Failed to move item {item_id}")

        except Exception as e:
            self._logger.error(f"Error handling item move: {e}")

    def _calculate_new_position(self, current_index: int, direction: str, total_items: int) -> int:
        """計算移動後的新位置"""
        if direction == "up" and current_index > 0:
            return current_index - 1
        elif direction == "down" and current_index < total_items - 1:
            return current_index + 1
        else:
            return current_index  # 不能移動

    def handle_test_item_clear(self) -> None:
        """
        處理清空所有測試項目的請求

        注意：修正了接口定義，清空操作不需要 item_id 和 direction 參數

        協調流程：
        1. 檢查當前狀態（是否正在執行）
        2. 獲取當前項目列表（用於日誌或撤銷）
        3. 清空 Model 中的數據
        4. 通知所有 View 更新
        5. 記錄操作歷史
        """
        try:
            # 1. 檢查執行狀態
            current_state = self.get_current_execution_status()
            if current_state == ExecutionState.RUNNING:
                self._logger.warning("Cannot clear items while execution is running")
                return

            # 2. 獲取當前項目（用於記錄）
            current_items = self.execution_business_model.get_test_items()
            items_count = len(current_items)

            if items_count == 0:
                self._logger.info("No items to clear")
                return

            # 3. 記錄將要清空的項目（可用於撤銷功能）
            cleared_items_data = self._create_items_snapshot(current_items)

            # 4. 在 Model 中清空數據
            self.execution_business_model.clear_test_items()

            # 5. 通知所有 View 更新
            if self._composition_views:
                self._composition_views.clear_all_test_items_ui()

            if self._run_case_views:
                self._run_case_views.reset_execution_display()

            # 6. 發送狀態變更信號
            self.state_changed.emit("test_items", [])

            # 7. 記錄操作歷史（可用於撤銷）
            self._record_operation_history({
                "operation": "clear_all",
                "items_count": items_count,
                "cleared_items": cleared_items_data,
                "timestamp": self._get_timestamp_qt()
            })

            # 8. 顯示操作結果
            self.operation_completed.emit("clear_test_composition", True)

            self._logger.info(f"Cleared {items_count} test items")

        except Exception as e:
            self._logger.error(f"Error clearing test items: {e}")
            self.operation_completed.emit("clear_test_composition", False)
            # self._handle_error("clear_items_failed", str(e))

    def _record_operation_history(self, operation_data: Dict[str, Any]):
        """記錄操作歷史"""
        # 實現操作歷史記錄，可用於撤銷功能
        if not hasattr(self, '_operation_history'):
            self._operation_history = []

        self._operation_history.append(operation_data)

        # 限制歷史記錄數量
        if len(self._operation_history) > 50:
            self._operation_history.pop(0)

    def _create_items_snapshot(self, items: List[TestItem]) -> List[Dict[str, Any]]:
        """創建項目快照（用於撤銷或歷史記錄）"""
        return [
            {
                "id": item.id,
                "type": item.type.value,
                "name": item.name,
                "config": item.config.copy(),
                "status": item.status.value
            }
            for item in items
        ]

    def _get_timestamp_qt(self) -> str:
        """使用 Qt 格式的時間戳"""
        from PySide6.QtCore import QDateTime
        return QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")

    def handle_undo_clear(self) -> None:
        """撤銷清空操作 """
        if not hasattr(self, '_operation_history') or not self._operation_history:
            return

        last_operation = self._operation_history[-1]
        if last_operation.get("operation") == "clear_all":
            cleared_items = last_operation.get("cleared_items", [])

            # 恢復項目
            for item_data in cleared_items:
                self.handle_test_item_added(item_data, TestItemType(item_data["type"]))

            self._operation_history.pop()
            self._logger.info("Undo clear operation completed")

    # endregion

    # region execution request

    async def handle_run_request(self) -> None:
        print( "Received run request")
        exe_config = self.execution_business_model.generate_execution_config("Untitled")
        await self.execution_business_model.start_execution(exe_config)

    async def handle_stop_request(self) -> None:
        print("Received stop request")

    async def handle_generate_request(self, export_config: Dict[str, Any]) -> None:
        print("Received handle_generate_request")

    async def handle_import_request(self) -> None:
        print("Received handle_import_request")

    async def handle_report_request(self) -> None:
        print("Received handle_report_request")

    #endregion

    def get_current_execution_status(self) -> ExecutionState:
        return self._run_case_views.get_current_execution_state()


