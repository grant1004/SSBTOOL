from robot.api.deco import library, keyword
import sys
import os
from .BaseLibrary import BaseRobotLibrary

# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
# 將該路徑加入到 Python 的模組搜尋路徑中
if current_dir not in sys.path:
    sys.path.append(current_dir)

import time


@library
class HMILibrary(BaseRobotLibrary):
    """HMI Testing Library"""

    def __init__(self):
        super().__init__()

    @keyword
    def click_button(self, button_id: str, delay: float = 0.5):
        """
        Simulate clicking a button on HMI.

        Args:
            button_id: The ID of the button to click
            delay: Delay time in seconds before clicking (default: 0.5)

        Returns:
            bool: True if click successful, False otherwise
        """
        time.sleep(delay)
        return True


