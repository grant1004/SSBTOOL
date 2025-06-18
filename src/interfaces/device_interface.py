# src/interfaces/device_interfaces.py
"""
設備管理相關接口定義
這些接口定義了設備管理系統中各組件的責任邊界
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from PySide6.QtCore import QObject, Signal
from enum import Enum


class DeviceType(Enum):
    """設備類型枚舉"""
    USB = "USB"
    LOADER = "LOADER"
    POWER = "POWER"


class DeviceStatus(Enum):
    """設備狀態枚舉"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    BUSY = "busy"


class DeviceConnectionResult:
    """設備連接結果"""

    def __init__(self, success: bool, message: str = "", error_code: Optional[str] = None):
        self.success = success
        self.message = message
        self.error_code = error_code


# ==================== Model 層接口 ====================

class IDeviceBusinessModel(ABC):
    """設備業務模型接口 - 定義純業務邏輯"""

    @abstractmethod
    async def connect_device(self, device_type: DeviceType, com_port: str) -> DeviceConnectionResult:
        """
        連接設備 - 核心業務邏輯

        Args:
            device_type: 要連接的設備類型

        Returns:
            DeviceConnectionResult: 連接結果

        Business Rules:
        - 同類型設備同時只能連接一個
        - 連接前需檢查前置條件
        - 連接失敗需清理資源
        """
        pass

    @abstractmethod
    async def disconnect_device(self, device_type: DeviceType) -> DeviceConnectionResult:
        """斷開設備連接"""
        pass

    @abstractmethod
    def get_device_status(self, device_type: DeviceType) -> DeviceStatus:
        """獲取設備當前狀態"""
        pass

    @abstractmethod
    def get_all_device_status(self) -> Dict[DeviceType, DeviceStatus]:
        """獲取所有設備狀態"""
        pass

    @abstractmethod
    def is_device_available(self, device_type: DeviceType) -> bool:
        """檢查設備是否可用（業務規則檢查）"""
        pass

    @abstractmethod
    def can_perform_operation(self, device_type: DeviceType, operation: str) -> bool:
        """檢查是否可以執行特定操作（業務規則驗證）"""
        pass

    @abstractmethod
    def get_device_info(self, device_type: DeviceType) -> Optional[Dict[str, Any]]:
        """獲取設備詳細信息"""
        pass

    @abstractmethod
    def register_status_observer(self, callback: Callable[[DeviceType, DeviceStatus], None]):
        """註冊設備狀態變更觀察者"""
        pass

    @abstractmethod
    def unregister_status_observer(self, callback: Callable[[DeviceType, DeviceStatus], None]):
        """取消註冊設備狀態變更觀察者"""
        pass


# ==================== Controller 層接口 ====================

class IDeviceController(ABC):
    """設備控制器接口 - 定義協調邏輯"""

    @abstractmethod
    def register_view(self, view: 'IDeviceView') -> None:
        """註冊設備視圖"""
        pass

    @abstractmethod
    def unregister_view(self, view: 'IDeviceView') -> None:
        """取消註冊設備視圖"""
        pass

    @abstractmethod
    async def handle_connect_request(self, device_type: DeviceType) -> None:
        """
        處理設備連接請求 - 協調邏輯

        Coordination Responsibilities:
        - 前置條件檢查和用戶確認
        - 協調 Model 執行業務邏輯
        - 管理 UI 狀態更新
        - 處理錯誤和異常情況
        - 跨組件狀態同步
        """
        pass

    @abstractmethod
    async def handle_disconnect_request(self, device_type: DeviceType) -> None:
        """處理設備斷開請求"""
        pass

    @abstractmethod
    def handle_status_query(self, device_type: Optional[DeviceType] = None) -> Dict[DeviceType, DeviceStatus]:
        """處理狀態查詢請求"""
        pass

    @abstractmethod
    def handle_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """處理設備錯誤"""
        pass

    @abstractmethod
    def refresh_device_status(self) -> None:
        """刷新所有設備狀態"""
        pass

    @abstractmethod
    def set_device_configuration(self, device_type: DeviceType, config: Dict[str, Any]) -> bool:
        """設置設備配置"""
        pass


# ==================== View 層接口 ====================

class IDeviceView(ABC):
    """設備視圖接口 - 定義 UI 更新契約"""

    @abstractmethod
    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """
        更新設備狀態顯示

        Args:
            device_type: 設備類型
            status: 新的設備狀態
        """
        pass

    @abstractmethod
    def show_connection_progress(self, device_type: DeviceType, progress: int) -> None:
        """
        顯示連接進度

        Args:
            device_type: 設備類型
            progress: 進度百分比 (0-100)
        """
        pass

    @abstractmethod
    def show_connection_success(self, device_type: DeviceType) -> None:
        """顯示連接成功提示"""
        pass

    @abstractmethod
    def show_connection_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示連接錯誤"""
        pass

    @abstractmethod
    def show_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示設備運行錯誤"""
        pass

    @abstractmethod
    def enable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """啟用設備控制項"""
        pass

    @abstractmethod
    def disable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """禁用設備控制項"""
        pass

    @abstractmethod
    def update_device_info(self, device_type: DeviceType, info: Dict[str, Any]) -> None:
        """更新設備詳細信息顯示"""
        pass

    @abstractmethod
    def request_user_confirmation(self, message: str) -> bool:
        """請求用戶確認（同步方法）"""
        pass

    @abstractmethod
    async def request_user_confirmation_async(self, message: str) -> bool:
        """請求用戶確認（異步方法）"""
        pass


# ==================== View Event 接口 ====================

class IDeviceViewEvents(ABC):
    """設備視圖事件接口 - 定義 View 發出的事件"""

    @abstractmethod
    def on_connect_requested(self, device_type: DeviceType) -> None:
        """當用戶請求連接設備時觸發"""
        pass

    @abstractmethod
    def on_disconnect_requested(self, device_type: DeviceType) -> None:
        """當用戶請求斷開設備時觸發"""
        pass

    @abstractmethod
    def on_refresh_requested(self) -> None:
        """當用戶請求刷新狀態時觸發"""
        pass

    @abstractmethod
    def on_device_settings_requested(self, device_type: DeviceType) -> None:
        """當用戶請求設備設置時觸發"""
        pass


# ==================== 事件數據類 ====================

class DeviceStatusChangedEvent:
    """設備狀態變更事件"""

    def __init__(self, device_type: DeviceType, old_status: DeviceStatus, new_status: DeviceStatus):
        self.device_type = device_type
        self.old_status = old_status
        self.new_status = new_status
        self.timestamp = None  # 可以添加時間戳


class DeviceErrorEvent:
    """設備錯誤事件"""

    def __init__(self, device_type: DeviceType, error_code: str, error_message: str):
        self.device_type = device_type
        self.error_code = error_code
        self.error_message = error_message
        self.timestamp = None


class DeviceConnectionEvent:
    """設備連接事件"""

    def __init__(self, device_type: DeviceType, event_type: str, success: bool = True, message: str = ""):
        self.device_type = device_type
        self.event_type = event_type  # "connecting", "connected", "disconnecting", "disconnected"
        self.success = success
        self.message = message
        self.timestamp = None


# ==================== 配置接口 ====================

class IDeviceConfiguration(ABC):
    """設備配置接口"""

    @abstractmethod
    def get_device_config(self, device_type: DeviceType) -> Dict[str, Any]:
        """獲取設備配置"""
        pass

    @abstractmethod
    def set_device_config(self, device_type: DeviceType, config: Dict[str, Any]) -> bool:
        """設置設備配置"""
        pass

    @abstractmethod
    def get_default_config(self, device_type: DeviceType) -> Dict[str, Any]:
        """獲取設備默認配置"""
        pass

    @abstractmethod
    def validate_config(self, device_type: DeviceType, config: Dict[str, Any]) -> bool:
        """驗證設備配置是否有效"""
        pass


# ==================== 工廠接口 ====================

class IDeviceFactory(ABC):
    """設備工廠接口 - 用於創建設備實例"""

    @abstractmethod
    def create_device_model(self) -> IDeviceBusinessModel:
        """創建設備業務模型"""
        pass

    @abstractmethod
    def create_device_controller(self, model: IDeviceBusinessModel) -> IDeviceController:
        """創建設備控制器"""
        pass

    @abstractmethod
    def create_device_view(self, parent=None) -> IDeviceView:
        """創建設備視圖"""
        pass


# ==================== 使用範例和說明 ====================

"""
使用範例：

# Model 實現
class DeviceBusinessModel(IDeviceBusinessModel):
    async def connect_device(self, device_type: DeviceType) -> DeviceConnectionResult:
        # 實現具體的業務邏輯
        pass

# Controller 實現  
class DeviceController(IDeviceController):
    def __init__(self, model: IDeviceBusinessModel):
        self.model = model
        self.views = []

    async def handle_connect_request(self, device_type: DeviceType):
        # 實現協調邏輯
        pass

# View 實現
class TopWidget(QWidget, IDeviceView, IDeviceViewEvents):
    def update_device_status(self, device_type: DeviceType, status: DeviceStatus):
        # 實現 UI 更新
        pass

    def on_connect_requested(self, device_type: DeviceType):
        # 發送到 Controller
        pass

設計原則：
1. 接口分離：每個接口職責單一
2. 依賴倒置：高層模塊不依賴低層模塊
3. 開閉原則：對擴展開放，對修改關閉
4. 里氏替換：子類可以替換父類
"""