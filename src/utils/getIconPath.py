import os
def get_icon_path(icon_name):
    """獲取圖標的完整路徑"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(project_root, "src", "assets", "Icons", icon_name)