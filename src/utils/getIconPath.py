import os
import sys

def get_icon_path(icon_name):
    """獲取圖標的完整路徑"""
    # 判斷是打包環境還是開發環境
    if getattr(sys, 'frozen', False):
        # 打包環境
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, "src", "assets", "Icons", icon_name)
    else:
        # 開發環境
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, "src", "assets", "Icons", icon_name)