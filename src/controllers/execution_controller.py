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
        self.register_model("execution_business_model", execution_business_model)
        self.execution_business_model = execution_business_model

        # 視圖管理
        self._run_case_views: List[IExecutionView] = []
        self._composition_views: List[ICompositionView] = []
        self._control_views: List[IControlView] = []

    #region IExecutionController
    def register_view(self, view) -> None:
        """註冊測試案例視圖"""
        registered_as = []

        # 檢查並註冊執行視圖介面
        if isinstance(view, IExecutionView):
            if view not in self._run_case_views:
                self._run_case_views.append(view)
                registered_as.append("IExecutionView")

        # 檢查並註冊組合視圖介面
        if isinstance(view, ICompositionView):
            if view not in self._composition_views:
                self._composition_views.append(view)
                registered_as.append("ICompositionView")

        # 檢查並註冊控制視圖介面
        if isinstance(view, IControlView):
            if view not in self._control_views:
                self._control_views.append(view)
                registered_as.append("IControlView")


        if registered_as:
            interfaces_str = ", ".join(registered_as)
            self._logger.info(f"Registered {type(view).__name__} as: {interfaces_str}")
        else:
            self._logger.warning(f"No recognized interfaces found for {type(view).__name__}")


    async def handle_run_request(self) -> None:
        pass

    async def handle_pause_request(self) -> None:
        pass

    async def handle_resume_request(self) -> None:
        pass

    async def handle_stop_request(self) -> None:
        pass

    def handle_test_item_added(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        pass

    def handle_test_item_removed(self, item_id: str) -> None:
        pass

    def handle_test_item_moved(self, item_id: str, direction: str) -> None:
        pass

    async def handle_generate_request(self, export_config: Dict[str, Any]) -> None:
        pass

    async def handle_import_request(self) -> None:
        pass

    async def handle_report_request(self) -> None:
        pass

    def get_current_execution_status(self) -> Dict[str, Any]:
        pass

    def register_execution_view(self, view: 'IExecutionView') -> None:
        pass

    #endregion
