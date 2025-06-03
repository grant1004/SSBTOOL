# src/interfaces/test_case_interfaces.py
"""
測試案例管理相關接口定義
定義測試案例的載入、管理、搜索、分類等功能的責任邊界
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from dataclasses import dataclass


class TestCaseCategory(Enum):
    """測試案例分類"""
    COMMON = "common"
    BATTERY = "battery"
    HMI = "hmi"
    MOTOR = "motor"
    CONTROLLER = "controller"


class TestCasePriority(Enum):
    """測試案例優先級"""
    REQUIRED = "required"
    NORMAL = "normal"
    OPTIONAL = "optional"


class TestCaseMode(Enum):
    """測試案例模式"""
    TEST_CASES = "test_cases"
    KEYWORDS = "keywords"


@dataclass
class TestCaseInfo:
    """測試案例信息數據類"""
    id: str
    name: str
    description: str
    category: TestCaseCategory
    priority: TestCasePriority
    estimated_time: int  # 分鐘
    steps: List[Dict[str, Any]]
    dependencies: Dict[str, List[str]]
    metadata: Dict[str, Any]


@dataclass
class KeywordInfo:
    """關鍵字信息數據類"""
    id: str
    name: str
    description: str
    category: TestCaseCategory
    arguments: List[Dict[str, Any]]
    returns: str
    estimated_time: int  # 分鐘
    library_name: str
    priority: TestCasePriority


@dataclass
class SearchCriteria:
    """搜索條件"""
    keyword: str = ""
    category: Optional[TestCaseCategory] = None
    priority: Optional[TestCasePriority] = None
    mode: Optional[TestCaseMode] = None


# ==================== Model 層接口 ====================

class ITestCaseBusinessModel(ABC):
    """測試案例業務模型接口"""

    @abstractmethod
    def load_test_cases(self, category: TestCaseCategory) -> List[TestCaseInfo]:
        """
        載入指定分類的測試案例

        Args:
            category: 測試案例分類

        Returns:
            List[TestCaseInfo]: 測試案例列表

        Business Rules:
        - 載入前需驗證分類有效性
        - 支持緩存機制
        - 處理載入失敗情況
        """
        pass

    @abstractmethod
    def load_keywords(self, category: TestCaseCategory) -> List[KeywordInfo]:
        """載入指定分類的關鍵字"""
        pass

    @abstractmethod
    def search_test_cases(self, criteria: SearchCriteria) -> List[TestCaseInfo]:
        """搜索測試案例"""
        pass

    @abstractmethod
    def search_keywords(self, criteria: SearchCriteria) -> List[KeywordInfo]:
        """搜索關鍵字"""
        pass

    @abstractmethod
    def get_test_case_by_id(self, test_case_id: str) -> Optional[TestCaseInfo]:
        """根據 ID 獲取測試案例"""
        pass

    @abstractmethod
    def get_keyword_by_id(self, keyword_id: str) -> Optional[KeywordInfo]:
        """根據 ID 獲取關鍵字"""
        pass

    @abstractmethod
    def validate_test_case(self, test_case: TestCaseInfo) -> bool:
        """驗證測試案例有效性"""
        pass

    @abstractmethod
    def get_categories(self) -> List[TestCaseCategory]:
        """獲取所有可用分類"""
        pass

    @abstractmethod
    def get_test_case_dependencies(self, test_case_id: str) -> Dict[str, List[str]]:
        """獲取測試案例依賴關係"""
        pass

    @abstractmethod
    def refresh_test_cases(self, category: Optional[TestCaseCategory] = None) -> bool:
        """刷新測試案例數據"""
        pass


class IKeywordParsingModel(ABC):
    """關鍵字解析模型接口"""

    @abstractmethod
    def parse_library(self, library_instance: Any, category: TestCaseCategory) -> List[KeywordInfo]:
        """解析 Robot Framework 庫"""
        pass

    @abstractmethod
    def get_keywords_for_category(self, category: TestCaseCategory) -> List[Dict[str, Any]]:
        """獲取指定分類的關鍵字配置"""
        pass

    @abstractmethod
    def clear_category(self, category: TestCaseCategory) -> None:
        """清除指定分類的關鍵字緩存"""
        pass


# ==================== Controller 層接口 ====================

class ITestCaseController(ABC):
    """測試案例控制器接口"""

    @abstractmethod
    def register_view(self, view: 'ITestCaseView') -> None:
        """註冊測試案例視圖"""
        pass

    @abstractmethod
    def unregister_view(self, view: 'ITestCaseView') -> None:
        """取消註冊測試案例視圖"""
        pass

    @abstractmethod
    def handle_category_change(self, category: TestCaseCategory) -> None:
        """
        處理分類變更請求

        Coordination Responsibilities:
        - 協調數據載入
        - 管理視圖狀態切換
        - 處理載入錯誤
        - 更新相關 UI 組件
        """
        pass

    @abstractmethod
    def handle_mode_switch(self, mode: TestCaseMode) -> None:
        """處理模式切換（測試案例 vs 關鍵字）"""
        pass

    @abstractmethod
    def handle_search_request(self, search_text: str) -> None:
        """處理搜索請求"""
        pass

    @abstractmethod
    def handle_test_case_selection(self, test_case_id: str) -> None:
        """處理測試案例選擇"""
        pass

    @abstractmethod
    def handle_keyword_selection(self, keyword_id: str) -> None:
        """處理關鍵字選擇"""
        pass

    @abstractmethod
    def handle_refresh_request(self) -> None:
        """處理刷新請求"""
        pass

    @abstractmethod
    def get_current_state(self) -> Dict[str, Any]:
        """獲取當前狀態（用於狀態恢復）"""
        pass


# ==================== View 層接口 ====================

class ITestCaseView(ABC):
    """測試案例視圖接口"""

    @abstractmethod
    def display_test_cases(self, test_cases: List[TestCaseInfo]) -> None:
        """顯示測試案例列表"""
        pass

    @abstractmethod
    def display_keywords(self, keywords: List[KeywordInfo]) -> None:
        """顯示關鍵字列表"""
        pass

    @abstractmethod
    def update_category_selection(self, category: TestCaseCategory) -> None:
        """更新分類選擇"""
        pass

    @abstractmethod
    def update_mode_selection(self, mode: TestCaseMode) -> None:
        """更新模式選擇"""
        pass

    @abstractmethod
    def show_loading_state(self, is_loading: bool) -> None:
        """顯示載入狀態"""
        pass

    @abstractmethod
    def show_error_message(self, error_message: str) -> None:
        """顯示錯誤信息"""
        pass

    @abstractmethod
    def show_empty_state(self, message: str) -> None:
        """顯示空狀態"""
        pass

    @abstractmethod
    def highlight_search_results(self, search_text: str) -> None:
        """高亮搜索結果"""
        pass

    @abstractmethod
    def clear_search_highlight(self) -> None:
        """清除搜索高亮"""
        pass

    @abstractmethod
    def enable_controls(self) -> None:
        """啟用控制項"""
        pass

    @abstractmethod
    def disable_controls(self) -> None:
        """禁用控制項"""
        pass


class ITestCaseViewEvents(ABC):
    """測試案例視圖事件接口"""

    @abstractmethod
    def on_category_changed(self, category: TestCaseCategory) -> None:
        """當分類變更時觸發"""
        pass

    @abstractmethod
    def on_mode_switched(self, mode: TestCaseMode) -> None:
        """當模式切換時觸發"""
        pass

    @abstractmethod
    def on_search_text_changed(self, search_text: str) -> None:
        """當搜索文本變更時觸發"""
        pass

    @abstractmethod
    def on_test_case_selected(self, test_case_id: str) -> None:
        """當測試案例被選擇時觸發"""
        pass

    @abstractmethod
    def on_keyword_selected(self, keyword_id: str) -> None:
        """當關鍵字被選擇時觸發"""
        pass

    @abstractmethod
    def on_refresh_requested(self) -> None:
        """當請求刷新時觸發"""
        pass


# ==================== 搜索和過濾接口 ====================

class ITestCaseFilter(ABC):
    """測試案例過濾器接口"""

    @abstractmethod
    def set_filter_criteria(self, criteria: SearchCriteria) -> None:
        """設置過濾條件"""
        pass

    @abstractmethod
    def apply_filter(self, items: List[Union[TestCaseInfo, KeywordInfo]]) -> List[Union[TestCaseInfo, KeywordInfo]]:
        """應用過濾條件"""
        pass

    @abstractmethod
    def clear_filter(self) -> None:
        """清除過濾條件"""
        pass


class ITestCaseSearch(ABC):
    """測試案例搜索接口"""

    @abstractmethod
    def search(self, query: str, items: List[Union[TestCaseInfo, KeywordInfo]]) -> List[
        Union[TestCaseInfo, KeywordInfo]]:
        """執行搜索"""
        pass

    @abstractmethod
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """獲取搜索建議"""
        pass


# ==================== 數據載入接口 ====================

class ITestCaseDataLoader(ABC):
    """測試案例數據載入器接口"""

    @abstractmethod
    def load_from_file(self, file_path: str) -> List[TestCaseInfo]:
        """從文件載入測試案例"""
        pass

    @abstractmethod
    def load_from_directory(self, directory_path: str) -> Dict[TestCaseCategory, List[TestCaseInfo]]:
        """從目錄載入測試案例"""
        pass

    @abstractmethod
    def save_to_file(self, test_cases: List[TestCaseInfo], file_path: str) -> bool:
        """保存測試案例到文件"""
        pass


class ILibraryLoader(ABC):
    """庫載入器接口"""

    @abstractmethod
    def get_library(self, category: TestCaseCategory) -> Optional[Any]:
        """獲取指定分類的庫實例"""
        pass

    @abstractmethod
    def reload_library(self, category: TestCaseCategory) -> bool:
        """重新載入庫"""
        pass


# ==================== 事件數據類 ====================

class TestCaseCategoryChangedEvent:
    """測試案例分類變更事件"""

    def __init__(self, old_category: TestCaseCategory, new_category: TestCaseCategory):
        self.old_category = old_category
        self.new_category = new_category


class TestCaseModeChangedEvent:
    """測試案例模式變更事件"""

    def __init__(self, old_mode: TestCaseMode, new_mode: TestCaseMode):
        self.old_mode = old_mode
        self.new_mode = new_mode


class TestCaseSearchEvent:
    """測試案例搜索事件"""

    def __init__(self, search_text: str, results_count: int):
        self.search_text = search_text
        self.results_count = results_count


class TestCaseSelectionEvent:
    """測試案例選擇事件"""

    def __init__(self, item_id: str, item_type: str, item_data: Union[TestCaseInfo, KeywordInfo]):
        self.item_id = item_id
        self.item_type = item_type  # "test_case" or "keyword"
        self.item_data = item_data


# ==================== 配置接口 ====================

class ITestCaseConfiguration(ABC):
    """測試案例配置接口"""

    @abstractmethod
    def get_default_category(self) -> TestCaseCategory:
        """獲取默認分類"""
        pass

    @abstractmethod
    def get_default_mode(self) -> TestCaseMode:
        """獲取默認模式"""
        pass

    @abstractmethod
    def get_categories_config(self) -> Dict[TestCaseCategory, Dict[str, Any]]:
        """獲取分類配置"""
        pass

    @abstractmethod
    def get_search_config(self) -> Dict[str, Any]:
        """獲取搜索配置"""
        pass


# ==================== 使用範例 ====================

"""
使用範例：

# Model 實現
class TestCaseBusinessModel(ITestCaseBusinessModel):
    def load_test_cases(self, category: TestCaseCategory) -> List[TestCaseInfo]:
        # 實現從文件系統載入測試案例
        pass

# Controller 實現
class TestCaseController(ITestCaseController):
    def __init__(self, model: ITestCaseBusinessModel):
        self.model = model
        self.views = []
        self.current_category = TestCaseCategory.COMMON
        self.current_mode = TestCaseMode.TEST_CASES

    def handle_category_change(self, category: TestCaseCategory):
        # 協調數據載入和視圖更新
        pass

# View 實現
class TestCaseWidget(QWidget, ITestCaseView, ITestCaseViewEvents):
    def display_test_cases(self, test_cases: List[TestCaseInfo]):
        # 更新 UI 顯示
        pass

    def on_category_changed(self, category: TestCaseCategory):
        # 發送到 Controller
        pass

設計重點：
1. 數據和 UI 分離：TestCaseInfo 是純數據，不包含 UI 邏輯
2. 職責清晰：Model 管理數據，Controller 協調，View 顯示
3. 事件驅動：通過事件實現鬆耦合通信
4. 可擴展性：易於添加新的分類和功能
"""