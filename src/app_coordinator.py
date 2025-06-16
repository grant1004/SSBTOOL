# src/app_coordinator.py
"""
應用程式協調器
負責組裝和管理整個應用程式的 MVC 架構
"""

import sys
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal
import logging

from src.business_models.device_business_model import DeviceBusinessModel
from src.business_models.execution_business_model import TestExecutionBusinessModel
from src.business_models.test_case_business_model import TestCaseBusinessModelFactory
from src.controllers.execution_controller import ExecutionController
from src.controllers.device_controller import DeviceController
from src.controllers.test_case_controller import TestCaseController
# 導入框架基礎類
from src.mvc_framework.dependency_container import DependencyContainer
from src.mvc_framework.event_bus import event_bus


# 導入現有組件（在重構過程中會逐步替換）
from src.ui.main_window import MainWindow
from src.ui.Theme import ThemeManager


class ApplicationCoordinator(QObject):
    """
    應用程式協調器

    職責：
    1. 組裝 MVC 架構
    2. 管理組件依賴關係
    3. 協調跨模組通信
    4. 管理應用程式生命週期
    """

    # 應用程式級別信號
    application_started = Signal()
    application_shutdown = Signal()

    def __init__(self):
        super().__init__()
        self.container = DependencyContainer()
        self.main_window: Optional[MainWindow] = None
        self.theme_manager: Optional[ThemeManager] = None
        self._logger = logging.getLogger(self.__class__.__name__)
        # 初始化標誌
        self._is_initialized = False
        self._is_running = False

    def initialize(self) -> bool:
        """
        初始化應用程式

        Returns:
            bool: 初始化是否成功
        """
        try:
            self._logger.info("Starting application initialization...")
            # 階段 1: 設置基礎設施
            self._setup_logging()
            self._setup_theme_system()

            # 階段 2: 註冊核心服務
            self._register_core_services()

            # 階段 3: 創建業務模型
            self._create_business_models()

            # 階段 4: 創建控制器
            self._create_controllers()

            # 階段 5: 創建視圖
            self._create_views()

            # 階段 6: 連接組件
            self._wire_components()

            # 階段 7: 最終設置
            self._setup_event_handlers()

            self._is_initialized = True
            self._logger.info("Application initialization completed successfully")
            return True

        except Exception as e:
            self._logger.error(f"Application initialization failed: {e}")
            return False

    def start(self) -> MainWindow:
        """
        啟動應用程式

        Returns:
            MainWindow: 主視窗實例
        """
        if not self._is_initialized:
            raise RuntimeError("Application not initialized. Call initialize() first.")

        try:
            self._logger.info("Starting application...")

            # 顯示主視窗
            self.main_window.show()

            # 發送啟動信號
            self.application_started.emit()
            event_bus.publish("application_started")

            self._is_running = True
            self._logger.info("Application started successfully")

            return self.main_window

        except Exception as e:
            self._logger.error(f"Failed to start application: {e}")
            raise

    def shutdown(self) -> None:
        """關閉應用程式"""
        try:
            self._logger.info("Shutting down application...")

            # 發送關閉信號
            self.application_shutdown.emit()
            event_bus.publish("application_shutdown")

            # 清理資源
            self._cleanup_resources()

            self._is_running = False
            self._logger.info("Application shutdown completed")

        except Exception as e:
            self._logger.error(f"Error during application shutdown: {e}")

    def get_service(self, service_name: str) -> Any:
        """獲取服務"""
        return self.container.get(service_name)

    def get_main_window(self) -> MainWindow:
        """獲取主視窗"""
        return self.main_window

    def get_theme_manager(self) -> ThemeManager:
        """獲取主題管理器"""
        return self.theme_manager

    # ==================== 私有初始化方法 ====================

    def _setup_logging(self) -> None:
        """設置日誌系統"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                # 可以添加文件處理器
                # logging.FileHandler('app.log')
            ]
        )
        self._logger.info("Logging system initialized")
        # logging.disable(logging.CRITICAL)

    def _setup_theme_system(self) -> None:
        """設置主題系統"""
        self.theme_manager = ThemeManager()
        self.container.register_instance("theme_manager", self.theme_manager)
        self._logger.info("Theme system initialized")

    def _register_core_services(self) -> None:
        """註冊核心服務"""
        # 註冊事件總線
        self.container.register_instance("event_bus", event_bus)

        # 註冊應用協調器自身
        self.container.register_instance("app_coordinator", self)

        # 註冊配置管理器（如果有的話）
        # self.container.register_singleton("config_manager", lambda: ConfigManager())

        self._logger.info("Core services registered")

    def _create_business_models(self) -> None:
        """創建業務模型"""
        # 在重構過程中，這裡會逐步添加新的業務模型

        # 設備業務模型（將來實現）
        self.container.register_singleton(
            "device_business_model",
            lambda: DeviceBusinessModel()
        )

        # 測試案例業務模型（將來實現）
        self.container.register_singleton(
            "test_case_business_model",
            lambda: TestCaseBusinessModelFactory.create_model()
        )

        # 測試執行業務模型（將來實現）
        self.container.register_singleton(
            "test_execution_business_model",
            lambda: TestExecutionBusinessModel()
        )

        self._logger.info("Business models created")

    def _create_controllers(self) -> None:
        """創建控制器"""
        # 在重構過程中，這裡會逐步添加新的控制器

        # 設備控制器（將來實現）
        self.container.register_singleton(
            "device_controller",
            lambda: DeviceController(
                self.container.get_required("device_business_model")
            )
        )

        # 測試案例控制器（將來實現）
        self.container.register_singleton(
            "test_case_controller",
            lambda: TestCaseController(
                self.container.get_required("test_case_business_model")
            )
        )

        # 測試執行控制器（將來實現）
        self.container.register_singleton(
            "execution_controller",
            lambda: ExecutionController(
                self.container.get_required("test_execution_business_model")
            )
        )

        self._logger.info("Controllers created")

    def _create_views(self) -> None:
        """創建視圖 - 純粹創建，不設置控制器依賴"""
        # 創建主視窗（傳入基本依賴如主題管理器）
        self.main_window = MainWindow()
        self.container.register_instance("main_window", self.main_window)

        # 子組件在 MainWindow 的 init_ui 中創建，也是純粹創建
        # 這裡可以直接獲取引用
        self.container.register_instance("top_widget", self.main_window.top_widget)
        self.container.register_instance("test_case_widget", self.main_window.test_case_widget)
        self.container.register_instance("run_case_widget", self.main_window.run_case_widget)
        # self.container.register_instance("run_widget", self.main_window.run_widget)

        self._logger.info("Views created (without controller dependencies)")

    def _wire_components(self) -> None:
        """連接組件 - 這裡是重點！設置所有的依賴關係"""
        self._logger.info("Starting component wiring...")

        #region  TopWidget 用來管理 device 連接
        self._logger.info("----------------- Wiring TopWidget start ----------------------------------")
        device_controller = self.container.get_required("device_controller")
        top_widget = self.container.get_required("top_widget")
        top_widget.register_controller("device_controller", device_controller)

        #endregion

        #region TestCase
        self._logger.info("----------------- Wiring TestCase start ----------------------------------")
        test_case_controller = self.container.get_required("test_case_controller")
        test_case_widget = self.container.get_required("test_case_widget")
        test_case_widget.register_controller("test_case_controller", test_case_controller)

        #endregion

        # region Execution Case
        self._logger.info("----------------- Wiring Execution Case start ----------------------------------")
        execution_controller = self.container.get_required("execution_controller")
        run_case_widget = self.container.get_required("run_case_widget")
        run_case_widget.register_controller( "execution_controller", execution_controller)

        # endregion

        self._logger.info("Component wiring completed")

    def _setup_event_handlers(self) -> None:
        """設置事件處理器"""
        # 設置全局事件處理
        event_bus.subscribe("application_error", self._on_application_error)
        event_bus.subscribe("theme_changed", self._on_theme_changed)

        # 設置主視窗關閉事件
        if self.main_window:
            self.main_window.closeEvent = self._on_main_window_close

        self._logger.info("Event handlers set up")

    def _cleanup_resources(self) -> None:
        """清理資源"""
        try:
            # 停止所有業務模型
            device_model = self.container.get("device_business_model")
            if device_model and hasattr(device_model, 'stop'):
                device_model.stop()

            # 清理容器
            self.container.clear()

            # 清理事件總線
            event_bus.clear_all_subscriptions()

        except Exception as e:
            self._logger.error(f"Error during resource cleanup: {e}")

    # ==================== 事件處理方法 ====================

    def _on_application_error(self, error_data: Dict[str, Any]) -> None:
        """處理應用程式錯誤"""
        error_message = error_data.get('message', 'Unknown error')
        self._logger.error(f"Application error: {error_message}")

        # 可以在這裡添加錯誤報告機制
        if self.main_window:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.main_window,
                "應用程式錯誤",
                f"發生錯誤: {error_message}"
            )

    def _on_theme_changed(self, theme_data: Any) -> None:
        """處理主題變更"""
        self._logger.info("Theme changed, updating all components")
        # 主題變更邏輯（如果需要的話）

    def _on_main_window_close(self, event) -> None:
        """處理主視窗關閉事件"""
        self.shutdown()
        event.accept()


class ApplicationFactory:
    """
    應用程式工廠
    提供不同配置的應用程式創建方法
    """

    @staticmethod
    def create_production_app() -> ApplicationCoordinator:
        """創建生產環境應用程式"""
        coordinator = ApplicationCoordinator()
        return coordinator

    @staticmethod
    def create_development_app() -> ApplicationCoordinator:
        """創建開發環境應用程式"""
        coordinator = ApplicationCoordinator()
        # 可以添加開發環境特有的配置
        return coordinator

    @staticmethod
    def create_test_app() -> ApplicationCoordinator:
        """創建測試環境應用程式"""
        coordinator = ApplicationCoordinator()
        # 可以添加測試環境特有的配置
        return coordinator


# ==================== 應用程式啟動入口 ====================
"""
def main():
   
    app = QApplication(sys.argv)

    try:
        # 創建應用協調器
        coordinator = ApplicationFactory.create_production_app()

        # 初始化應用程式
        if not coordinator.initialize():
            sys.exit(1)

        # 啟動應用程式
        main_window = coordinator.start()

        # 運行事件循環
        result = app.exec()

        # 清理
        coordinator.shutdown()

        return result

    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
"""

# ==================== 重構進度追蹤 ====================
"""
重構進度追蹤：

Phase 1: 基礎架構 ✅
- [✅] 接口定義完成
- [✅] MVC 基類完成  
- [✅] 應用協調器骨架完成
- [🔄] 準備開始 Phase 2

Phase 2: 設備管理重構 (下一步)
- [ ] 創建 DeviceBusinessModel
- [ ] 重構 DeviceController
- [ ] 適配 TopWidget
- [ ] 測試設備管理功能

使用說明：
1. 這個協調器目前是骨架，在重構過程中會逐步填充
2. 現有功能通過 MainWindow 保持運行
3. 新的 MVC 組件會逐步註冊到容器中
4. 重構完成後，所有組件都通過協調器管理

啟動方式：
python -m src.app_coordinator

或者在 main.py 中：
from src.app_coordinator import ApplicationFactory

coordinator = ApplicationFactory.create_production_app()
coordinator.initialize()
main_window = coordinator.start()
"""