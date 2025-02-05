import inspect
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from robot.api.deco import keyword


@dataclass
class KeywordInfo:
    """關鍵字數據結構"""
    name: str  # 關鍵字名稱
    description: str  # 關鍵字描述
    arguments: List[str]  # 參數列表
    library_name: str  # 所屬庫名稱
    category: str  # 所屬類別


class KeywordParser:
    """Robot Framework 關鍵字解析器"""

    def __init__(self):
        # 用字典來存儲不同類別的關鍵字
        self.keywords_by_category: Dict[str, Dict[str, KeywordInfo]] = {}

    def parse_library(self, library_instance: Any, category: str) -> List[KeywordInfo]:
        """解析庫實例中的所有關鍵字"""
        # 確保類別存在
        if category not in self.keywords_by_category:
            self.keywords_by_category[category] = {}

        keywords = []

        # 獲取所有帶有 @keyword 裝飾器的方法
        for name, member in inspect.getmembers(library_instance):
            if name.startswith('_'):  # 跳過私有方法
                continue

            if hasattr(member, 'robot_name') or inspect.ismethod(member):
                try:
                    # 獲取方法的參數
                    signature = inspect.signature(member)
                    params = [
                        param.name for param in signature.parameters.values()
                        if param.name != 'self'
                    ]

                    # 獲取文檔字符串
                    doc = inspect.getdoc(member) or ''

                    # 創建關鍵字數據
                    keyword_info = KeywordInfo(
                        name=name,
                        description=doc,
                        arguments=params,
                        library_name=library_instance.__class__.__name__,
                        category=category
                    )

                    keywords.append(keyword_info)
                    self.keywords_by_category[category][name] = keyword_info

                except Exception as e:
                    print(f"Error parsing keyword {name}: {e}")

        return keywords

    def get_keywords_for_category(self, category: str) -> List[Dict[str, Any]]:
        """獲取特定類別的所有關鍵字的卡片配置"""
        if category not in self.keywords_by_category:
            return []

        return [self.convert_to_card_config(kw) for kw in self.keywords_by_category[category].values()]

    def convert_to_card_config(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """將關鍵字數據轉換為 BaseCard 配置格式"""
        return {
            'id': keyword_info.name,
            'title': keyword_info.name,
            'info': keyword_info.description,
            'estimated_time': 0,
            'keywords': keyword_info.arguments,
            'priority': self._determine_priority(keyword_info)
        }

    def _determine_priority(self, keyword_info: KeywordInfo) -> str:
        """根據關鍵字特徵決定優先級"""
        name_lower = keyword_info.name.lower()
        if 'connect' in name_lower or 'init' in name_lower or 'reset' in name_lower:
            return 'required'
        elif 'measure' in name_lower or 'test' in name_lower:
            return 'standard'
        else:
            return 'optional'

    def clear_category(self, category: str):
        """清除特定類別的所有關鍵字"""
        if category in self.keywords_by_category:
            self.keywords_by_category[category].clear()