from importlib import import_module
from typing import Dict, Type, Optional


class LibraryLoader:
    """Library 動態加載器"""

    # Library 映射配置
    LIBRARY_MAPPING = {
        'common': ('Lib.CANMonitorLibrary', 'CommonLibrary'),
        'battery': ('Lib.CANMonitorLibrary', 'BatteryLibrary'),
        'hmi': ('Lib.CANMonitorLibrary', 'HMILibrary'),
        'motor': ('Lib.CANMonitorLibrary', 'MotorLibrary'),
        'controller': ('Lib.CANMonitorLibrary', 'ControllerLibrary')
    }

    def __init__(self):
        self.loaded_libraries: Dict[str, object] = {}

    def get_library(self, category: str) -> Optional[object]:
        """獲取指定分類的 Library 實例"""
        # 檢查是否已經載入
        if category in self.loaded_libraries:
            return self.loaded_libraries[category]

        # 檢查是否支持該分類
        if category not in self.LIBRARY_MAPPING:
            raise ValueError(f"Unsupported library category: {category}")

        try:
            # 獲取模組和類名
            module_path, class_name = self.LIBRARY_MAPPING[category]

            # 動態導入模組
            module = import_module(module_path)

            # 獲取類
            library_class = getattr(module, class_name)

            # 創建實例
            library_instance = library_class()

            # 儲存實例
            self.loaded_libraries[category] = library_instance

            return library_instance

        except ImportError as e:
            raise ImportError(f"Failed to import library for category '{category}': {e}")
        except AttributeError as e:
            raise AttributeError(f"Failed to find library class for category '{category}': {e}")
        except Exception as e:
            raise Exception(f"Error creating library instance for category '{category}': {e}")
