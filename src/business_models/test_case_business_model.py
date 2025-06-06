# src/business_models/test_case_business_model.py
"""
測試案例業務模型 - 純新架構實現

職責：
1. 管理測試案例的載入、搜索、驗證
2. 管理關鍵字的解析和緩存
3. 提供統一的業務規則驗證
4. 處理測試案例依賴關係
5. 支持多種數據源和格式
"""

import os
import json
import time
from typing import Dict, Optional, List, Callable, Any, Union
from dataclasses import asdict
from pathlib import Path
from PySide6.QtCore import QObject, Signal

# 導入接口
from src.interfaces.test_case_interface import (
    ITestCaseBusinessModel, IKeywordParsingModel,
    TestCaseCategory, TestCasePriority, TestCaseInfo, KeywordInfo,
    SearchCriteria, TestCaseMode
)

# 導入 MVC 基類
from src.mvc_framework.base_model import BaseBusinessModel

# 導入現有工具類
from src.utils.KeywordParser import KeywordParser
from src.utils.LibraryLoader import LibraryLoader


class TestCaseBusinessModel(BaseBusinessModel, ITestCaseBusinessModel, IKeywordParsingModel):
    """
    測試案例業務模型實現

    特點：
    - 統一的測試案例和關鍵字管理
    - 智能緩存機制
    - 多種搜索和過濾功能
    - 完整的業務規則驗證
    - 支持熱重載和增量更新
    """

    # 業務信號
    test_cases_loaded = Signal(TestCaseCategory, int)  # category, count
    keywords_loaded = Signal(TestCaseCategory, int)  # category, count
    search_completed = Signal(str, int)  # search_text, results_count
    category_refreshed = Signal(TestCaseCategory)
    validation_failed = Signal(str, list)  # item_id, errors

    def __init__(self):
        super().__init__()

        # 數據存儲
        self._test_cases_cache: Dict[TestCaseCategory, List[TestCaseInfo]] = {}
        self._keywords_cache: Dict[TestCaseCategory, List[KeywordInfo]] = {}
        self._test_case_by_id: Dict[str, TestCaseInfo] = {}
        self._keyword_by_id: Dict[str, KeywordInfo] = {}

        # 依賴關係緩存
        self._dependencies_cache: Dict[str, Dict[str, List[str]]] = {}

        # 配置和工具
        self._library_loader = LibraryLoader()
        self._keyword_parser = KeywordParser()

        # 業務配置
        self._data_directory = self._get_data_directory()
        self._supported_categories = list(TestCaseCategory)
        self._cache_ttl = 300  # 5分鐘緩存過期時間
        self._auto_refresh_enabled = True

        # 緩存管理
        self._cache_timestamps: Dict[str, float] = {}
        self._loading_states: Dict[TestCaseCategory, bool] = {}

        # 設置業務規則
        self._setup_validation_rules()

        self.log_operation("test_case_business_model_initialized", True, "測試案例業務模型初始化完成")

    # ==================== ITestCaseBusinessModel 接口實現 ====================

    def load_test_cases(self, category: TestCaseCategory) -> List[TestCaseInfo]:
        """載入指定分類的測試案例"""
        operation_name = f"load_test_cases_{category.value}"
        self.operation_started.emit(operation_name)

        try:
            # 1. 檢查緩存
            cached_result = self._get_cached_test_cases(category)
            if cached_result is not None:
                self.log_operation(operation_name, True, f"從緩存獲取 {len(cached_result)} 個測試案例")
                self.operation_completed.emit(operation_name, True)
                return cached_result

            # 2. 標記載入狀態
            self._loading_states[category] = True

            # 3. 從文件系統載入
            test_cases = self._load_test_cases_from_file(category)

            # 4. 轉換為業務對象
            test_case_infos = []
            for case_id, info in test_cases.items():
                try:
                    case_data = info['data']['config']
                    test_case_info = self._convert_to_test_case_info( case_id, case_data, category)
                    if self.validate_test_case(test_case_info):
                        test_case_infos.append(test_case_info)
                        self._test_case_by_id[test_case_info.id] = test_case_info
                    else:
                        self._logger.warning(f"Invalid test case: {test_case_info.id}")
                except Exception as e:
                    self._logger.error(f"Error converting test case: {e}")

            # 5. 緩存結果
            self._cache_test_cases(category, test_case_infos)

            # 6. 發送事件
            self.test_cases_loaded.emit(category, len(test_case_infos))
            self.data_changed.emit("test_cases_loaded", {
                'category': category,
                'count': len(test_case_infos)
            })

            self.log_operation(operation_name, True, f"載入 {len(test_case_infos)} 個測試案例")
            self.operation_completed.emit(operation_name, True)

            return test_case_infos

        except Exception as e:
            error_msg = f"載入測試案例失敗: {str(e)}"
            self.log_operation(operation_name, False, error_msg)
            self.error_occurred.emit("LOAD_TEST_CASES_FAILED", error_msg)
            self.operation_completed.emit(operation_name, False)
            return []

        finally:
            self._loading_states[category] = False

    def load_keywords(self, category: TestCaseCategory) -> List[KeywordInfo]:
        """載入指定分類的關鍵字"""
        operation_name = f"load_keywords_{category.value}"
        self.operation_started.emit(operation_name)

        try:
            # 1. 檢查緩存
            cached_result = self._get_cached_keywords(category)
            if cached_result is not None:
                self.log_operation(operation_name, True, f"從緩存獲取 {len(cached_result)} 個關鍵字")
                self.operation_completed.emit(operation_name, True)
                return cached_result

            # 2. 標記載入狀態
            self._loading_states[category] = True

            # 3. 通過庫載入器獲取庫實例
            library_instance = self._library_loader.get_library(category.value)
            if library_instance is None:
                self._logger.warning(f"No library found for category: {category.value}")
                self.operation_completed.emit(operation_name, True)
                return []

            # 4. 解析關鍵字
            self._keyword_parser.clear_category(category.value)
            parsed_keywords = self._keyword_parser.parse_library(library_instance, category.value)

            # 5. 轉換為業務對象
            keyword_infos = []
            for parsed_kw in parsed_keywords:
                try:
                    keyword_info = self._convert_to_keyword_info(parsed_kw, category)
                    keyword_infos.append(keyword_info)
                    self._keyword_by_id[keyword_info.id] = keyword_info
                except Exception as e:
                    self._logger.error(f"Error converting keyword: {e}")

            # 6. 緩存結果
            self._cache_keywords(category, keyword_infos)

            # 7. 發送事件
            self.keywords_loaded.emit(category, len(keyword_infos))
            self.data_changed.emit("keywords_loaded", {
                'category': category,
                'count': len(keyword_infos)
            })

            self.log_operation(operation_name, True, f"載入 {len(keyword_infos)} 個關鍵字")
            self.operation_completed.emit(operation_name, True)

            return keyword_infos

        except Exception as e:
            error_msg = f"載入關鍵字失敗: {str(e)}"
            self.log_operation(operation_name, False, error_msg)
            self.error_occurred.emit("LOAD_KEYWORDS_FAILED", error_msg)
            self.operation_completed.emit(operation_name, False)
            return []

        finally:
            self._loading_states[category] = False

    def search_test_cases(self, criteria: SearchCriteria) -> List[TestCaseInfo]:
        """搜索測試案例"""
        operation_name = "search_test_cases"
        self.operation_started.emit(operation_name)

        try:
            # 1. 確定搜索範圍
            categories_to_search = [criteria.category] if criteria.category else self._supported_categories

            # 2. 收集所有相關測試案例
            all_test_cases = []
            for category in categories_to_search:
                test_cases = self._get_or_load_test_cases(category)
                all_test_cases.extend(test_cases)

            # 3. 應用搜索條件
            filtered_results = self._apply_test_case_search_filters(all_test_cases, criteria)

            # 4. 發送事件
            self.search_completed.emit(criteria.keyword, len(filtered_results))
            self.data_changed.emit("search_completed", {
                'criteria': criteria,
                'results_count': len(filtered_results)
            })

            self.log_operation(operation_name, True, f"搜索到 {len(filtered_results)} 個測試案例")
            self.operation_completed.emit(operation_name, True)

            return filtered_results

        except Exception as e:
            error_msg = f"搜索測試案例失敗: {str(e)}"
            self.log_operation(operation_name, False, error_msg)
            self.error_occurred.emit("SEARCH_TEST_CASES_FAILED", error_msg)
            self.operation_completed.emit(operation_name, False)
            return []

    def search_keywords(self, criteria: SearchCriteria) -> List[KeywordInfo]:
        """搜索關鍵字"""
        operation_name = "search_keywords"
        self.operation_started.emit(operation_name)

        try:
            # 1. 確定搜索範圍
            categories_to_search = [criteria.category] if criteria.category else self._supported_categories

            # 2. 收集所有相關關鍵字
            all_keywords = []
            for category in categories_to_search:
                keywords = self._get_or_load_keywords(category)
                all_keywords.extend(keywords)

            # 3. 應用搜索條件
            filtered_results = self._apply_keyword_search_filters(all_keywords, criteria)

            # 4. 發送事件
            self.search_completed.emit(criteria.keyword, len(filtered_results))

            self.log_operation(operation_name, True, f"搜索到 {len(filtered_results)} 個關鍵字")
            self.operation_completed.emit(operation_name, True)

            return filtered_results

        except Exception as e:
            error_msg = f"搜索關鍵字失敗: {str(e)}"
            self.log_operation(operation_name, False, error_msg)
            self.error_occurred.emit("SEARCH_KEYWORDS_FAILED", error_msg)
            self.operation_completed.emit(operation_name, False)
            return []

    def get_test_case_by_id(self, test_case_id: str) -> Optional[TestCaseInfo]:
        """根據 ID 獲取測試案例"""
        return self._test_case_by_id.get(test_case_id)

    def get_keyword_by_id(self, keyword_id: str) -> Optional[KeywordInfo]:
        """根據 ID 獲取關鍵字"""
        return self._keyword_by_id.get(keyword_id)

    def validate_test_case(self, test_case: TestCaseInfo) -> bool:
        """驗證測試案例有效性"""
        try:
            errors = []

            # 基本字段驗證
            if not test_case.id or not test_case.id.strip():
                errors.append("測試案例 ID 不能為空")

            if not test_case.name or not test_case.name.strip():
                errors.append("測試案例名稱不能為空")

            if test_case.estimated_time < 0:
                errors.append("預估時間不能為負數")

            # 步驟驗證
            if not test_case.steps:
                errors.append("測試案例必須包含至少一個步驟")

            for i, step in enumerate(test_case.steps):
                if not isinstance(step, dict):
                    errors.append(f"步驟 {i+1} 格式無效")
                elif ( step.get('step_type') == "keyword" and
                       not step.get('name') and
                       not step.get('keyword_name') ):
                    errors.append(f"步驟 {i+1} 缺少名稱或關鍵字名稱")

            # 依賴驗證
            dependencies = test_case.dependencies
            if 'libraries' in dependencies:
                for lib in dependencies['libraries']:
                    if not isinstance(lib, str) or not lib.strip():
                        errors.append(f"庫依賴格式無效: {lib}")

            if errors:
                self.validation_failed.emit(test_case.id, errors)
                return False

            return True

        except Exception as e:
            self._logger.error(f"Validation error for test case {test_case.id}: {e}")
            return False

    def get_categories(self) -> List[TestCaseCategory]:
        """獲取所有可用分類"""
        return self._supported_categories.copy()

    def get_test_case_dependencies(self, test_case_id: str) -> Dict[str, List[str]]:
        """獲取測試案例依賴關係"""
        if test_case_id in self._dependencies_cache:
            return self._dependencies_cache[test_case_id].copy()

        test_case = self.get_test_case_by_id(test_case_id)
        if not test_case:
            return {}

        dependencies = test_case.dependencies.copy()
        self._dependencies_cache[test_case_id] = dependencies
        return dependencies

    def refresh_test_cases(self, category: Optional[TestCaseCategory] = None) -> bool:
        """刷新測試案例數據"""
        operation_name = f"refresh_test_cases_{category.value if category else 'all'}"
        self.operation_started.emit(operation_name)

        try:
            categories_to_refresh = [category] if category else self._supported_categories

            for cat in categories_to_refresh:
                # 清除緩存
                self._clear_category_cache(cat)

                # 重新載入
                self.load_test_cases(cat)
                self.load_keywords(cat)

                # 發送刷新事件
                self.category_refreshed.emit(cat)

            self.log_operation(operation_name, True, "測試案例數據刷新完成")
            self.operation_completed.emit(operation_name, True)
            return True

        except Exception as e:
            error_msg = f"刷新測試案例失敗: {str(e)}"
            self.log_operation(operation_name, False, error_msg)
            self.error_occurred.emit("REFRESH_FAILED", error_msg)
            self.operation_completed.emit(operation_name, False)
            return False

    # ==================== IKeywordParsingModel 接口實現 ====================

    def parse_library(self, library_instance: Any, category: TestCaseCategory) -> List[KeywordInfo]:
        """解析 Robot Framework 庫"""
        try:
            parsed_keywords = self._keyword_parser.parse_library(library_instance, category.value)
            keyword_infos = []

            for parsed_kw in parsed_keywords:
                keyword_info = self._convert_to_keyword_info(parsed_kw, category)
                keyword_infos.append(keyword_info)

            return keyword_infos

        except Exception as e:
            self._logger.error(f"Error parsing library for {category.value}: {e}")
            return []

    def get_keywords_for_category(self, category: TestCaseCategory) -> List[Dict[str, Any]]:
        """獲取指定分類的關鍵字配置"""
        keywords = self._get_or_load_keywords(category)
        return [self._convert_keyword_to_config(kw) for kw in keywords]

    def clear_category(self, category: TestCaseCategory) -> None:
        """清除指定分類的關鍵字緩存"""
        self._keyword_parser.clear_category(category.value)
        self._clear_category_cache(category)

    # ==================== 私有輔助方法 ====================

    def _get_data_directory(self) -> Path:
        """獲取數據目錄"""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data" / "robot" / "cards"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def _load_test_cases_from_file(self, category: TestCaseCategory) -> Union[List[dict], dict]:
        """從文件載入測試案例"""
        file_path = self._data_directory / f"{category.value}-test-case.json"

        if not file_path.exists():
            self._logger.warning(f"Test case file not found: {file_path}")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

                # 處理不同的文件格式
                if isinstance(data, dict):
                    # 新格式：{"testcase_id": {"data": {"config": {...}}}}
                    return data
                else:
                    self._logger.error(f"Unsupported file format: {file_path}")
                    return []

        except Exception as e:
            self._logger.error(f"Error loading test cases from {file_path}: {e}")
            return []

    def _convert_to_test_case_info(self, case_id: str, case_data: dict, category: TestCaseCategory) -> TestCaseInfo:
        """轉換字典數據為 TestCaseInfo 對象"""
        return TestCaseInfo(
            id=case_id,
            name=case_data.get('name', ''),
            description=case_data.get('description', ''),
            category=category,
            priority=TestCasePriority(case_data.get('priority', 'normal')),
            estimated_time=self._parse_estimated_time(case_data.get('estimated_time', 0)),  # 使用解析方法
            steps=case_data.get('steps', []),
            dependencies=case_data.get('dependencies', {}),
            metadata=case_data.get('metadata', {})
        )

    def _parse_estimated_time(self, time_value) -> int:
        """
        解析預估時間，支持多種格式

        Args:
            time_value: 時間值，可以是字串（如 "4min", "1h"）或數字

        Returns:
            int: 時間（分鐘）
        """
        if isinstance(time_value, int):
            return max(0, time_value)

        if isinstance(time_value, (float)):
            return max(0, int(time_value))

        if isinstance(time_value, str):
            time_str = time_value.strip().lower()

            # 如果是純數字字串
            if time_str.isdigit():
                return max(0, int(time_str))

            # 解析帶單位的時間
            import re

            # 匹配 "數字+單位" 格式
            match = re.match(r'^(\d+(?:\.\d+)?)\s*(min|minute|minutes|h|hour|hours|s|sec|second|seconds)?$', time_str)
            if match:
                number = float(match.group(1))
                unit = match.group(2) or 'min'  # 預設為分鐘

                # 轉換為分鐘
                if unit in ['min', 'minute', 'minutes']:
                    return max(0, int(number))
                elif unit in ['h', 'hour', 'hours']:
                    return max(0, int(number * 60))
                elif unit in ['s', 'sec', 'second', 'seconds']:
                    return max(0, int(number / 60))

            # 如果解析失敗，記錄警告並返回默認值
            self._logger.warning(f"Unable to parse estimated_time: '{time_value}', using default 0")
            return 0

        # 其他類型返回默認值
        self._logger.warning(f"Invalid estimated_time type: {type(time_value)}, using default 0")
        return 0

    def _convert_to_keyword_info(self, parsed_kw, category: TestCaseCategory) -> KeywordInfo:
        """轉換解析的關鍵字為 KeywordInfo 對象"""
        return KeywordInfo(
            id=parsed_kw.name,
            name=parsed_kw.name,
            description=parsed_kw.description,
            category=category,
            arguments=[asdict(arg) for arg in parsed_kw.arguments],
            returns=parsed_kw.returns,
            estimated_time=self._estimate_keyword_time(parsed_kw),
            library_name=parsed_kw.library_name,
            priority=TestCasePriority(parsed_kw.priority)
        )

    def _convert_keyword_to_config(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """轉換關鍵字信息為配置字典"""
        return {
            'id': keyword_info.id,
            'name': keyword_info.name,
            'category': keyword_info.category.value,
            'description': keyword_info.description,
            'arguments': keyword_info.arguments,
            'returns': keyword_info.returns,
            'priority': keyword_info.priority.value
        }

    def _estimate_keyword_time(self, parsed_kw) -> int:
        """估算關鍵字執行時間（秒）"""
        # 簡單的啟發式估算
        base_time = 1  # 基礎時間 1 秒
        arg_time = len(parsed_kw.arguments) * 0.5  # 每個參數增加 0.5 秒

        # 根據關鍵字名稱和類型調整
        name_lower = parsed_kw.name.lower()
        if any(word in name_lower for word in ['wait', 'sleep', 'delay']):
            return 5  # 等待類關鍵字通常較長
        elif any(word in name_lower for word in ['check', 'verify', 'assert']):
            return 2  # 驗證類關鍵字通常較快
        elif any(word in name_lower for word in ['send', 'receive', 'connect']):
            return 3  # 通信類關鍵字中等時間

        return int(base_time + arg_time)

    def _get_cached_test_cases(self, category: TestCaseCategory) -> Optional[List[TestCaseInfo]]:
        """獲取緩存的測試案例"""
        cache_key = f"test_cases_{category.value}"

        if not self._is_cache_valid(cache_key):
            return None

        return self._test_cases_cache.get(category)

    def _get_cached_keywords(self, category: TestCaseCategory) -> Optional[List[KeywordInfo]]:
        """獲取緩存的關鍵字"""
        cache_key = f"keywords_{category.value}"

        if not self._is_cache_valid(cache_key):
            return None

        return self._keywords_cache.get(category)

    def _cache_test_cases(self, category: TestCaseCategory, test_cases: List[TestCaseInfo]) -> None:
        """緩存測試案例"""
        self._test_cases_cache[category] = test_cases
        cache_key = f"test_cases_{category.value}"
        self._cache_timestamps[cache_key] = time.time()

    def _cache_keywords(self, category: TestCaseCategory, keywords: List[KeywordInfo]) -> None:
        """緩存關鍵字"""
        self._keywords_cache[category] = keywords
        cache_key = f"keywords_{category.value}"
        self._cache_timestamps[cache_key] = time.time()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """檢查緩存是否有效"""
        if cache_key not in self._cache_timestamps:
            return False

        age = time.time() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl

    def _clear_category_cache(self, category: TestCaseCategory) -> None:
        """清除特定分類的緩存"""
        self._test_cases_cache.pop(category, None)
        self._keywords_cache.pop(category, None)

        cache_keys = [f"test_cases_{category.value}", f"keywords_{category.value}"]
        for key in cache_keys:
            self._cache_timestamps.pop(key, None)

        # 清除 ID 映射中的相關項目
        to_remove_tc = [tc_id for tc_id, tc in self._test_case_by_id.items() if tc.category == category]
        to_remove_kw = [kw_id for kw_id, kw in self._keyword_by_id.items() if kw.category == category]

        for tc_id in to_remove_tc:
            self._test_case_by_id.pop(tc_id, None)

        for kw_id in to_remove_kw:
            self._keyword_by_id.pop(kw_id, None)

    def _get_or_load_test_cases(self, category: TestCaseCategory) -> List[TestCaseInfo]:
        """獲取或載入測試案例"""
        cached = self._get_cached_test_cases(category)
        if cached is not None:
            return cached
        return self.load_test_cases(category)

    def _get_or_load_keywords(self, category: TestCaseCategory) -> List[KeywordInfo]:
        """獲取或載入關鍵字"""
        cached = self._get_cached_keywords(category)
        if cached is not None:
            return cached
        return self.load_keywords(category)

    def _apply_test_case_search_filters(self, test_cases: List[TestCaseInfo], criteria: SearchCriteria) -> List[TestCaseInfo]:
        """應用測試案例搜索過濾條件"""
        results = test_cases

        # 關鍵字過濾
        if criteria.keyword:
            keyword_lower = criteria.keyword.lower()
            results = [
                tc for tc in results
                if (keyword_lower in tc.name.lower() or
                    keyword_lower in tc.description.lower() or
                    any(keyword_lower in str(step.get('name', '')).lower()
                        for step in tc.steps))
            ]

        # 優先級過濾
        if criteria.priority:
            results = [tc for tc in results if tc.priority == criteria.priority]

        return results

    def _apply_keyword_search_filters(self, keywords: List[KeywordInfo], criteria: SearchCriteria) -> List[KeywordInfo]:
        """應用關鍵字搜索過濾條件"""
        results = keywords

        # 關鍵字過濾
        if criteria.keyword:
            keyword_lower = criteria.keyword.lower()
            results = [
                kw for kw in results
                if (keyword_lower in kw.name.lower() or
                    keyword_lower in kw.description.lower())
            ]

        # 優先級過濾
        if criteria.priority:
            results = [kw for kw in results if kw.priority == criteria.priority]

        return results

    def _setup_validation_rules(self) -> None:
        """設置業務驗證規則"""
        self.add_validation_rule(
            "test_case_id",
            lambda x: isinstance(x, str) and len(x.strip()) > 0,
            "測試案例 ID 不能為空"
        )

        self.add_validation_rule(
            "test_case_name",
            lambda x: isinstance(x, str) and len(x.strip()) > 0,
            "測試案例名稱不能為空"
        )

        self.add_validation_rule(
            "estimated_time",
            lambda x: isinstance(x, (int, float)) and x >= 0,
            "預估時間必須為非負數"
        )

    # ==================== 高級功能方法 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        stats = {
            'categories': len(self._supported_categories),
            'test_cases_by_category': {},
            'keywords_by_category': {},
            'total_test_cases': len(self._test_case_by_id),
            'total_keywords': len(self._keyword_by_id),
            'cache_hit_ratio': self._calculate_cache_hit_ratio(),
            'loading_states': self._loading_states.copy()
        }

        for category in self._supported_categories:
            tc_count = len(self._test_cases_cache.get(category, []))
            kw_count = len(self._keywords_cache.get(category, []))
            stats['test_cases_by_category'][category.value] = tc_count
            stats['keywords_by_category'][category.value] = kw_count

        return stats

    def get_loading_state(self, category: TestCaseCategory) -> bool:
        """獲取分類的載入狀態"""
        return self._loading_states.get(category, False)

    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """設置緩存過期時間"""
        self._cache_ttl = max(60, ttl_seconds)  # 最少 1 分鐘

    def enable_auto_refresh(self, enabled: bool) -> None:
        """啟用/禁用自動刷新"""
        self._auto_refresh_enabled = enabled

    def export_test_cases(self, category: TestCaseCategory, file_path: str) -> bool:
        """導出測試案例到文件"""
        try:
            test_cases = self._get_or_load_test_cases(category)
            export_data = [asdict(tc) for tc in test_cases]

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, ensure_ascii=False, indent=2)

            self.log_operation("export_test_cases", True, f"導出 {len(test_cases)} 個測試案例到 {file_path}")
            return True

        except Exception as e:
            self.log_operation("export_test_cases", False, f"導出失敗: {str(e)}")
            return False

    def _calculate_cache_hit_ratio(self) -> float:
        """計算緩存命中率"""
        # 這是一個簡化的實現，實際應用中可能需要更詳細的統計
        total_requests = len(self._cache_timestamps)
        if total_requests == 0:
            return 0.0

        valid_caches = sum(1 for key in self._cache_timestamps.keys() if self._is_cache_valid(key))
        return valid_caches / total_requests

    def clear_all_caches(self) -> None:
        """清除所有緩存"""
        self._test_cases_cache.clear()
        self._keywords_cache.clear()
        self._test_case_by_id.clear()
        self._keyword_by_id.clear()
        self._dependencies_cache.clear()
        self._cache_timestamps.clear()

    def stop(self) -> None:
        """停止業務模型"""
        try:
            # 清理緩存
            self.clear_all_caches()

            # 清理觀察者
            self.clear_cache()

            self.log_operation("test_case_business_model_stopped", True, "測試案例業務模型已停止")

        except Exception as e:
            self._logger.error(f"Error stopping test case business model: {e}")



# ==================== 工廠方法 ====================

class TestCaseBusinessModelFactory:
    """測試案例業務模型工廠"""

    @staticmethod
    def create_model() -> TestCaseBusinessModel:
        """創建測試案例業務模型實例"""
        return TestCaseBusinessModel()

    @staticmethod
    def create_model_with_config(config: Dict[str, Any]) -> TestCaseBusinessModel:
        """根據配置創建測試案例業務模型實例"""
        model = TestCaseBusinessModel()

        # 應用配置
        if 'cache_ttl' in config:
            model.set_cache_ttl(config['cache_ttl'])

        if 'auto_refresh' in config:
            model.enable_auto_refresh(config['auto_refresh'])

        return model