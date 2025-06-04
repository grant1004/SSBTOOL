import sys
import os
import time
from robot.api.deco import library, keyword
from src.utils import CANPacketGenerator
from .BaseLibrary import BaseRobotLibrary
# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
# 將該路徑加入到 Python 的模組搜尋路徑中
if current_dir not in sys.path:
    sys.path.append(current_dir)


@library(scope='GLOBAL')  # 確保整個測試過程使用同一個實例
class BatteryLibrary(BaseRobotLibrary):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'


    def __init__(self):
        super().__init__()


    def close(self):
        """明確的清理方法，在所有測試完成後調用"""
        super().close()

