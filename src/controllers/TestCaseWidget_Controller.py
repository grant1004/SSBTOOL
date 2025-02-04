# TestCaseWidget_Controller.py
class TestCaseWidgetController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.current_category = "battery"

    def initialize(self):
        """初始化數據"""
        self.load_category_data(self.current_category)

    def handle_category_change(self, category: str):
        """處理類別變更"""
        self.current_category = category
        self.load_category_data(category)

    def handle_search(self, search_text: str):
        """處理搜索"""
        filtered_data = self.model.filter_test_cases(self.current_category, search_text)
        self.view.test_case_group.load_from_data(filtered_data)

    def handle_mode_switch(self, mode: str):
        """處理模式切換"""
        # 實現模式切換邏輯
        self.load_category_data(self.current_category)

    def load_category_data(self, category: str):
        """加載類別數據"""
        data = self.model.load_category_data(category)
        self.view.test_case_group.load_from_data(data)