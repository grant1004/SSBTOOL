# src/interfaces/execution_interfaces.py
"""
測試執行管理相關接口定義
定義測試執行、進度管理、結果處理等功能的責任邊界
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class ExecutionState(Enum):
    """執行狀態"""
    IDLE = "idle"
    PREPARING = "preparing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestItemType(Enum):
    """測試項目類型"""
    TEST_CASE = "test_case"
    KEYWORD = "keyword"


class TestItemStatus(Enum):
    """測試項目狀態"""
    WAITING = "waiting"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"


@dataclass
class TestItem:
    """測試項目數據類"""
    id: str
    type: TestItemType
    name: str
    config: Dict[str, Any]
    status: TestItemStatus = TestItemStatus.WAITING
    progress: int = 0
    error_message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_data: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionProgress:
    """執行進度數據類"""
    total_items: int
    completed_items: int
    current_item_index: int
    current_item: Optional[TestItem]
    overall_progress: int  # 0-100
    estimated_remaining_time: Optional[float] = None  # 秒
    elapsed_time: float = 0.0  # 秒


@dataclass
class ExecutionResult:
    """執行結果數據類"""
    execution_id: str
    test_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float  # 秒
    state: ExecutionState
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    success_rate: float  # 0.0-1.0
    test_items: List[TestItem]
    error_summary: List[str]
    report_path: Optional[str] = None


@dataclass
class ExecutionConfiguration:
    """執行配置數據類"""
    test_name: str
    test_items: List[TestItem]
    execution_mode: str = "sequential"  # sequential, parallel
    timeout: int = 300  # 秒
    retry_count: int = 0
    continue_on_failure: bool = True
    generate_report: bool = True
    output_directory: str = ""
    variables: Dict[str, Any] = None


# ==================== Model 層接口 ====================

class ITestExecutionBusinessModel(ABC):
    """測試執行業務模型接口"""

    @abstractmethod
    def prepare_execution(self, config: ExecutionConfiguration) -> bool:
        """
        準備執行環境

        Args:
            config: 執行配置

        Returns:
            bool: 準備是否成功

        Business Rules:
        - 驗證執行前置條件
        - 檢查依賴關係
        - 準備執行環境
        - 驗證測試項目有效性
        """
        pass

    @abstractmethod
    async def start_execution(self, config: ExecutionConfiguration) -> str:
        """
        開始執行測試

        Args:
            config: 執行配置

        Returns:
            str: 執行 ID
        """
        pass

    @abstractmethod
    async def pause_execution(self, execution_id: str) -> bool:
        """暫停執行"""
        pass

    @abstractmethod
    async def resume_execution(self, execution_id: str) -> bool:
        """恢復執行"""
        pass

    @abstractmethod
    async def stop_execution(self, execution_id: str, force: bool = False) -> bool:
        """停止執行"""
        pass

    @abstractmethod
    def get_execution_state(self, execution_id: str) -> ExecutionState:
        """獲取執行狀態"""
        pass

    @abstractmethod
    def get_execution_progress(self, execution_id: str) -> Optional[ExecutionProgress]:
        """獲取執行進度"""
        pass

    @abstractmethod
    def get_execution_result(self, execution_id: str) -> Optional[ExecutionResult]:
        """獲取執行結果"""
        pass

    @abstractmethod
    def validate_execution_prerequisites(self, config: ExecutionConfiguration) -> List[str]:
        """驗證執行前置條件，返回錯誤列表"""
        pass

    @abstractmethod
    def estimate_execution_time(self, config: ExecutionConfiguration) -> float:
        """估算執行時間（秒）"""
        pass

    @abstractmethod
    def get_active_executions(self) -> List[str]:
        """獲取活躍的執行 ID 列表"""
        pass

    @abstractmethod
    def register_progress_observer(self, callback: Callable[[str, ExecutionProgress], None]) -> None:
        """註冊進度觀察者"""
        pass

    @abstractmethod
    def register_result_observer(self, callback: Callable[[str, ExecutionResult], None]) -> None:
        """註冊結果觀察者"""
        pass


class ITestCompositionModel(ABC):
    """測試組合模型接口 - 管理測試項目的組合和排序"""

    @abstractmethod
    def add_test_item(self, item: TestItem) -> bool:
        """添加測試項目"""
        pass

    @abstractmethod
    def remove_test_item(self, item_id: str) -> bool:
        """移除測試項目"""
        pass

    @abstractmethod
    def move_test_item(self, item_id: str, new_position: int) -> bool:
        """移動測試項目位置"""
        pass

    @abstractmethod
    def get_test_items(self) -> List[TestItem]:
        """獲取所有測試項目"""
        pass

    @abstractmethod
    def clear_test_items(self) -> None:
        """清除所有測試項目"""
        pass

    @abstractmethod
    def validate_composition(self) -> List[str]:
        """驗證測試組合，返回錯誤列表"""
        pass

    @abstractmethod
    def generate_execution_config(self, test_name: str) -> ExecutionConfiguration:
        """生成執行配置"""
        pass


class IReportGenerationModel(ABC):
    """報告生成模型接口"""

    @abstractmethod
    async def generate_report(self, result: ExecutionResult, format: str = "html") -> str:
        """
        生成測試報告

        Args:
            result: 執行結果
            format: 報告格式 (html, pdf, json)

        Returns:
            str: 報告文件路徑
        """
        pass

    @abstractmethod
    def get_available_formats(self) -> List[str]:
        """獲取可用的報告格式"""
        pass

    @abstractmethod
    def validate_report_config(self, config: Dict[str, Any]) -> bool:
        """驗證報告配置"""
        pass


# ==================== Controller 層接口 ====================

class IExecutionController(ABC):
    """執行控制器接口"""

    @abstractmethod
    def register_view(self, view: 'IExecutionView') -> None:
        pass

    @abstractmethod
    async def handle_run_request(self) -> None:
        """
        處理運行請求

        Coordination Responsibilities:
        - 收集測試項目和配置
        - 驗證執行條件（設備狀態、依賴等）
        - 協調執行準備
        - 啟動執行並管理狀態
        - 處理執行過程中的協調
        """
        pass

    @abstractmethod
    async def handle_stop_request(self) -> None:
        """處理停止請求"""
        pass

    @abstractmethod
    def handle_test_item_added(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        """處理測試項目添加"""
        pass

    @abstractmethod
    def handle_test_item_removed(self, item_id: str) -> None:
        """處理測試項目移除"""
        pass

    @abstractmethod
    def handle_test_item_moved(self, item_id: str, direction: str) -> None:
        """處理測試項目移動"""
        pass

    @abstractmethod
    def handle_test_item_clear(self, item_id: str, direction: str) -> None:
        """刪除所有項目"""
        pass

    @abstractmethod
    async def handle_generate_request(self, export_config: Dict[str, Any]) -> None:
        """處理生成/導出請求"""
        pass

    @abstractmethod
    async def handle_import_request(self) -> None:
        """處理導入請求"""
        pass

    @abstractmethod
    async def handle_report_request(self) -> None:
        """處理報告生成請求"""
        pass

    @abstractmethod
    def get_current_execution_status(self) -> Dict[str, Any]:
        """獲取當前執行狀態"""
        pass


# ==================== View 層接口 ====================

class IExecutionView(ABC):
    """執行視圖接口 - 顯示執行狀態和進度"""

    @abstractmethod
    def update_execution_state(self, state: ExecutionState) -> None:
        """更新執行狀態"""
        pass

    @abstractmethod
    def update_execution_progress(self, progress: ExecutionProgress) -> None:
        """更新執行進度"""
        pass

    @abstractmethod
    def update_test_item_status(self, item_id: str, status: TestItemStatus, progress: int = 0, error: str = "") -> None:
        """更新測試項目狀態"""
        pass

    @abstractmethod
    def show_execution_result(self, result: ExecutionResult) -> None:
        """顯示執行結果"""
        pass

    @abstractmethod
    def reset_execution_display(self) -> None:
        """重置執行顯示"""
        pass


class ICompositionView(ABC):
    """組合視圖接口 - 管理測試項目的組合"""

    @abstractmethod
    def add_test_item_ui(self, item: TestItem) -> None:
        """添加測試項目 UI"""
        pass

    @abstractmethod
    def remove_test_item_ui(self, item_id: str) -> None:
        """移除測試項目 UI"""
        pass

    @abstractmethod
    def update_test_item_order(self, ordered_item_ids: List[str]) -> None:
        """更新測試項目順序"""
        pass

    @abstractmethod
    def highlight_current_item(self, item_id: Optional[str]) -> None:
        """高亮當前執行項目"""
        pass

    @abstractmethod
    def enable_composition_editing(self) -> None:
        """啟用組合編輯"""
        pass

    @abstractmethod
    def disable_composition_editing(self) -> None:
        """禁用組合編輯"""
        pass

    @abstractmethod
    def show_composition_validation_errors(self, errors: List[str]) -> None:
        """顯示組合驗證錯誤"""
        pass


class IControlView(ABC):
    """控制視圖接口 - 執行控制按鈕等"""

    @abstractmethod
    def enable_run_controls(self) -> None:
        """啟用運行控制"""
        pass

    @abstractmethod
    def disable_run_controls(self) -> None:
        """禁用運行控制"""
        pass

    @abstractmethod
    def update_control_state(self, state: ExecutionState) -> None:
        """根據執行狀態更新控制項"""
        pass

    @abstractmethod
    def show_execution_time(self, elapsed_time: float, estimated_remaining: Optional[float] = None) -> None:
        """顯示執行時間"""
        pass


# ==================== View Event 接口 ====================

class IExecutionViewEvents(ABC):
    """執行視圖事件接口"""

    @abstractmethod
    def on_run_requested(self) -> None:
        """當請求運行時觸發"""
        pass

    @abstractmethod
    def on_stop_requested(self) -> None:
        """當請求停止時觸發"""
        pass

    @abstractmethod
    def on_generate_requested(self, config: Dict[str, Any]) -> None:
        """當請求生成時觸發"""
        pass

    @abstractmethod
    def on_import_requested(self) -> None:
        """當請求導入時觸發"""
        pass

    @abstractmethod
    def on_report_requested(self) -> None:
        """當請求報告時觸發"""
        pass


class ICompositionViewEvents(ABC):
    """組合視圖事件接口"""

    @abstractmethod
    def on_test_item_dropped(self, item_data: Dict[str, Any], item_type: TestItemType) -> None:
        """當測試項目被拖放時觸發"""
        pass

    @abstractmethod
    def on_test_item_delete_requested(self, item_id: str) -> None:
        """當請求刪除測試項目時觸發"""
        pass

    @abstractmethod
    def on_test_item_move_requested(self, item_id: str, direction: str) -> None:
        """當請求移動測試項目時觸發"""
        pass

    @abstractmethod
    def on_composition_cleared(self) -> None:
        """當組合被清空時觸發"""
        pass


# ==================== 專門的執行引擎接口 ====================

class ITestExecutionEngine(ABC):
    """測試執行引擎接口 - 實際執行測試的底層引擎"""

    @abstractmethod
    async def execute_test_configuration(self, config: ExecutionConfiguration) -> ExecutionResult:
        """執行測試配置"""
        pass

    @abstractmethod
    def supports_execution_mode(self, mode: str) -> bool:
        """檢查是否支持指定的執行模式"""
        pass

    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """獲取引擎信息"""
        pass


class IProgressReporter(ABC):
    """進度報告器接口"""

    @abstractmethod
    def report_progress(self, execution_id: str, progress: ExecutionProgress) -> None:
        """報告進度更新"""
        pass

    @abstractmethod
    def report_item_status(self, execution_id: str, item_id: str, status: TestItemStatus) -> None:
        """報告項目狀態更新"""
        pass

    @abstractmethod
    def report_execution_complete(self, execution_id: str, result: ExecutionResult) -> None:
        """報告執行完成"""
        pass


# ==================== 事件數據類 ====================

class ExecutionStateChangedEvent:
    """執行狀態變更事件"""

    def __init__(self, execution_id: str, old_state: ExecutionState, new_state: ExecutionState):
        self.execution_id = execution_id
        self.old_state = old_state
        self.new_state = new_state
        self.timestamp = datetime.now()


class ExecutionProgressEvent:
    """執行進度事件"""

    def __init__(self, execution_id: str, progress: ExecutionProgress):
        self.execution_id = execution_id
        self.progress = progress
        self.timestamp = datetime.now()


class TestItemStatusEvent:
    """測試項目狀態事件"""

    def __init__(self, execution_id: str, item_id: str, old_status: TestItemStatus, new_status: TestItemStatus):
        self.execution_id = execution_id
        self.item_id = item_id
        self.old_status = old_status
        self.new_status = new_status
        self.timestamp = datetime.now()


class CompositionChangedEvent:
    """組合變更事件"""

    def __init__(self, change_type: str, item_id: str, item_data: Optional[TestItem] = None):
        self.change_type = change_type  # "added", "removed", "moved"
        self.item_id = item_id
        self.item_data = item_data
        self.timestamp = datetime.now()
