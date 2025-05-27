# TestCaseWidget_Controller.py
from src.utils import *

class TestCaseWidgetController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.current_category = "common"
        self.current_mode = "test_cases"
        self.keyword_parser = KeywordParser()

    def initialize(self):
        """初始化數據"""
        self.load_category_data(self.current_category)

    def handle_category_change(self, category: str):
        """處理類別變更"""
        self.current_category = category
        if self.current_mode == "test_cases":
            self.load_category_data(category)
        else:
            self.view.keyword_group.clear_cards()
            self.load_keyword_data(category)

    def handle_search(self, search_text: str):
        """處理搜索"""
        if self.current_mode == "test_cases":
            filtered_data = self.model.filter_test_cases(self.current_category, search_text)
            self.view.test_case_group.load_from_data({'test_cases': filtered_data})
        else:
            self.view.keyword_group.filter_cards(search_text)

    def handle_mode_switch(self, mode: str):
        """處理模式切換"""
        self.current_mode = mode
        self.view.switch_mode(mode)

        if mode == "test_cases":
            self.load_category_data(self.current_category)
        else:
            self.load_keyword_data(self.current_category)

    def load_category_data(self, category: str):
        """加載測試案例數據"""
        data = self.model.load_category_data(category)
        self.view.test_case_group.load_from_data(data)

    def load_keyword_data(self, category: str):
        """加載關鍵字數據"""
        try:
            library_loader = LibraryLoader()
            library = library_loader.get_library(category)

            if library is None:
                print(f"No library found for category: {category}")
                return

            self.keyword_parser.clear_category(category)
            self.keyword_parser.parse_library(library, category)
            card_configs = self.keyword_parser.get_keywords_for_category(category)
            self.view.keyword_group.load_from_data(card_configs)

        except Exception as e:
            print(f"Error loading keywords: {e}")