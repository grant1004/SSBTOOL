# BaseLibrary.py - 重構版本，完全使用新 MVC 架構

import asyncio
from typing import Optional, TYPE_CHECKING

# 使用 TYPE_CHECKING 避免循環導入
if TYPE_CHECKING:
    from src.business_models.device_business_model import DeviceBusinessModel


class BaseRobotLibrary:
    """
    Robot Framework 測試庫的基礎類別
    提供共享的事件循環管理和設備業務模型訪問
    """

    _shared_loop: Optional[asyncio.AbstractEventLoop] = None

    def __init__(self):
        """初始化基礎庫"""
        # 首先初始化日志前綴
        self._logger_prefix = self.__class__.__name__

        # 獲取設備業務模型
        self._device_business_model = self._get_device_business_model()

        self._log_info("Base library initialized")

    def _get_device_business_model(self) -> Optional['DeviceBusinessModel']:
        """獲取設備業務模型實例"""
        try:
            # 延遲導入，避免循環依賴
            from src.business_models.device_business_model import DeviceBusinessModel
            # 方法1：通過全局變量直接獲取（推薦）
            import __main__
            if hasattr(__main__, 'device_business_model'):
                model = __main__.device_business_model
                self._log_info("Device business model obtained from global variable")
                return model

            # 方法2：通過應用協調器獲取
            if hasattr(__main__, 'app_coordinator'):
                coordinator = __main__.app_coordinator
                model = coordinator.get_service("device_business_model")
                if model:
                    self._log_info("Device business model obtained from app coordinator")
                    return model

            # 方法3：創建新實例（fallback）
            self._log_warning("Creating new DeviceBusinessModel instance as fallback")
            return DeviceBusinessModel()

        except Exception as e:
            self._log_error(f"Failed to get device business model: {e}")
            return None

    @property
    def device_model(self) -> Optional['DeviceBusinessModel']:
        """獲取設備業務模型"""
        if self._device_business_model is None:
            self._device_business_model = self._get_device_business_model()
        return self._device_business_model

    @classmethod
    def get_shared_loop(cls) -> asyncio.AbstractEventLoop:
        """獲取共享的事件循環"""
        if cls._shared_loop is None or cls._shared_loop.is_closed():
            try:
                # 嘗試獲取現有的事件循環
                cls._shared_loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果當前線程沒有循環，創建一個新的
                cls._shared_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(cls._shared_loop)
        return cls._shared_loop

    @classmethod
    def close_shared_loop(cls):
        """關閉共享的事件循環"""
        if cls._shared_loop and not cls._shared_loop.is_closed():
            cls._shared_loop.close()
            cls._shared_loop = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """獲取事件循環（優先使用共享循環）"""
        return self.get_shared_loop()

    def _run_async(self, coro):
        """運行異步函數的安全方法"""
        try:
            loop = self._get_loop()
            if loop.is_running():
                # 如果循環正在運行，創建任務
                return asyncio.create_task(coro)
            else:
                # 如果循環未運行，直接運行
                return loop.run_until_complete(coro)
        except Exception as e:
            self._log_error(f"Error running async function: {e}")
            raise

    def _log_info(self, message: str):
        """記錄信息日志"""
        prefix = getattr(self, '_logger_prefix', self.__class__.__name__)
        print(f"ℹ️  [{prefix}] {message}")

    def _log_warning(self, message: str):
        """記錄警告日志"""
        prefix = getattr(self, '_logger_prefix', self.__class__.__name__)
        print(f"⚠️  [{prefix}] {message}")

    def _log_error(self, message: str):
        """記錄錯誤日志"""
        prefix = getattr(self, '_logger_prefix', self.__class__.__name__)
        print(f"❌ [{prefix}] {message}")

    def _log_success(self, message: str):
        """記錄成功日志"""
        prefix = getattr(self, '_logger_prefix', self.__class__.__name__)
        print(f"✅ [{prefix}] {message}")

    def _validate_device_model(self):
        """驗證設備業務模型是否可用"""
        if not self.device_model:
            raise RuntimeError("設備業務模型不可用，請確保應用程序正確初始化")

    def close(self):
        """清理資源"""
        try:
            self._log_info("Starting cleanup...")

            loop = self._get_loop()

            # 取得所有待處理的任務
            if hasattr(asyncio, 'all_tasks'):
                pending = asyncio.all_tasks(loop)
            else:
                pending = asyncio.Task.all_tasks(loop)

            # 取消所有待處理的任務
            cancelled_count = 0
            for task in pending:
                if not task.done():
                    task.cancel()
                    cancelled_count += 1

            if cancelled_count > 0:
                self._log_info(f"Cancelled {cancelled_count} pending tasks")

            # 等待任務完成
            if pending:
                try:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                except Exception as e:
                    self._log_warning(f"Some tasks failed during cleanup: {e}")

            self._log_success("Cleanup completed")

        except Exception as e:
            self._log_error(f"Error during cleanup: {e}")
        finally:
            # 重置設備業務模型引用
            self._device_business_model = None