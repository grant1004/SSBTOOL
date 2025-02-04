# TestCaseWidget_Model.py
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TestCase:
    id: str
    name: str
    description: str
    estimated_time: int
    keywords: List[str]
    priority: str


class TestCaseWidget_Model:
    def __init__(self):
        self.test_cases: Dict[str, List[TestCase]] = {}

    def load_category_data(self, category: str) -> List[dict]:
        """加載特定類別的測試案例"""
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            json_path = os.path.join(project_root, "data", f"{category}-test-case.json")

            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.test_cases[category] = [
                    TestCase(
                        id=case.get('id', ''),
                        name=case.get('name', ''),
                        description=case.get('description', ''),
                        estimated_time=case.get('estimated_time', 0),
                        keywords=case.get('keywords', []),
                        priority=case.get('priority', 'medium')
                    ) for case in data
                ]

                return self._convert_to_dict(self.test_cases[category])
        except Exception as e:
            print(f"Error loading test cases for {category}: {e}")
            return []

    def filter_test_cases(self, category: str, search_text: str) -> List[dict]:
        """過濾測試案例"""
        if category not in self.test_cases:
            return []

        search_text = search_text.lower()
        filtered_cases = [
            case for case in self.test_cases[category]
            if search_text in case.name.lower() or
               search_text in case.description.lower() or
               any(search_text in keyword.lower() for keyword in case.keywords)
        ]

        return self._convert_to_dict(filtered_cases)

    def _convert_to_dict(self, test_cases: List[TestCase]) -> List[dict]:
        """將 TestCase 對象轉換為字典"""
        return [{
            'id': case.id,
            'name': case.name,
            'description': case.description,
            'estimated_time': case.estimated_time,
            'keywords': case.keywords,
            'priority': case.priority
        } for case in test_cases]

