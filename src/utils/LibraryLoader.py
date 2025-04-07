from importlib import import_module
from typing import Dict, Type, Optional
import sys, os


class LibraryLoader:
    """Library 動態加載器"""

    # Library 映射配置
    LIBRARY_MAPPING = {
        'common': ( 'Lib.CommonLibrary', 'CommonLibrary'),
        'battery': ('Lib.BatteryLibrary','BatteryLibrary'),
        'hmi': ('Lib.HMILibrary','HMILibrary'),
        'motor':('Lib.MotorLibrary','MotorLibrary'),
        'controller': ('Lib.ControllerLibrary','ControllerLibrary')
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

            # 嘗試直接導入（適用於已編譯模式）
            try:
                module = import_module(module_path)
            except ImportError:
                # 如果直接導入失敗，嘗試通過路徑載入（適用於文件系統模式）
                if getattr(sys, 'frozen', False):
                    # 打包環境
                    base_dir = os.path.dirname(sys.executable)
                    lib_path = os.path.join(base_dir, "Lib")
                    if lib_path not in sys.path:
                        sys.path.insert(0, lib_path)

                # 再次嘗試導入
                module = import_module(module_path)

            # 獲取類
            library_class = getattr(module, class_name)

            # 創建實例
            library_instance = library_class()

            # 儲存實例
            self.loaded_libraries[category] = library_instance

            return library_instance

        except Exception as e:
            raise Exception(f"Error creating library instance for category '{category}': {e}")