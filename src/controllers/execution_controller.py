import asyncio
from typing import Dict, List, Optional, Any, Set
from PySide6.QtCore import QObject, Signal, QTimer

from src.business_models.execution_business_model import TestExecutionBusinessModel
# 導入接口
from src.interfaces.execution_interface import (
    IExecutionController, ITestExecutionBusinessModel, ITestCompositionModel, IReportGenerationModel,
    TestItem, ExecutionResult, ExecutionConfiguration, TestItemType, IExecutionView, ICompositionView,
    IControlView
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
            if view not in self._device_views:
                self._run_case_views = view
                self._device_views.append(view)
                registered_as.append("IExecutionView")

        # 檢查並註冊組合視圖介面
        if isinstance(view, ICompositionView):
            if view not in self._device_views:
                self._composition_views = view
                self._device_views.append(view)
                registered_as.append("ICompositionView")

        # 檢查並註冊控制視圖介面
        if isinstance(view, IControlView):
            if view not in self._device_views:
                self._control_views = view
                self._device_views.append(view)
                registered_as.append("IControlView")


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

    #region IExecutionController
    async def handle_run_request(self) -> None:
        pass

    async def handle_stop_request(self) -> None:
        pass

    def handle_test_item_added(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        pass

    def handle_test_item_removed(self, item_id: str) -> None:
        pass

    def handle_test_item_moved(self, item_id: str, direction: str) -> None:
        pass

    def handle_test_item_clear(self, item_id: str, direction: str) -> None:
        pass
    async def handle_generate_request(self, export_config: Dict[str, Any]) -> None:
        pass

    async def handle_import_request(self) -> None:
        pass

    async def handle_report_request(self) -> None:
        pass

    def get_current_execution_status(self) -> Dict[str, Any]:
        pass

    #endregion
