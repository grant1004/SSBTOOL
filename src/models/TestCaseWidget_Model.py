# TestCaseWidget_Model.py
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TestStep:
    step_id: int
    name: str
    action: str
    params: dict
    expected: str


@dataclass
class TestCase:
    id: str
    name: str
    description: str
    priority: str
    estimated_time: int
    setup: dict
    steps: List[TestStep]


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

                # 載入測試案例
                test_cases = []
                for case in data.get('test_cases', []):
                    steps = [
                        TestStep(
                            step_id=step.get('step_id'),
                            name=step.get('name', ''),
                            action=step.get('action', ''),
                            params=step.get('params', {}),
                            expected=step.get('expected', '')
                        ) for step in case.get('steps', [])
                    ]

                    test_case = TestCase(
                        id=case.get('id', ''),
                        name=case.get('name', ''),
                        description=case.get('description', ''),
                        setup=case.get('setup', {}),
                        priority=case.get('priority', 'normal'),
                        estimated_time=case.get('estimated_time', 1),
                        steps=steps,
                    )
                    test_cases.append(test_case)

                self.test_cases[category] = test_cases
                return [self._convert_to_dict(case) for case in test_cases]

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
               any(search_text in step.action.lower() for step in case.steps)
        ]

        return [self._convert_to_dict(case) for case in filtered_cases]

    def _convert_to_dict(self, test_case: TestCase) -> dict:
        """將 TestCase 對象轉換為字典"""
        return {
            'id': test_case.id,
            'name': test_case.name,
            'description': test_case.description,
            'setup': test_case.setup,
            'estimated_time': test_case.estimated_time,
            'steps': [
                {
                    'step_id': step.step_id,
                    'name': step.name,
                    'action': step.action,
                    'params': step.params,
                    'expected': step.expected
                } for step in test_case.steps
            ],
            'priority': test_case.priority
        }