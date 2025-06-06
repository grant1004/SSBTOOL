# src/utils/KeywordParser.py - 修正版本
import inspect
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from robot.api.deco import keyword


@dataclass
class ArgumentInfo:
    """參數信息數據結構"""
    name: str
    type: str
    description: str
    value: str
    default: Optional[str] = None
    options: Optional[List[str]] = None
    example: Optional[str] = None


@dataclass
class KeywordInfo:
    """關鍵字數據結構"""
    name: str
    description: str
    category: str
    arguments: List[ArgumentInfo]
    returns: str
    library_name: str
    priority: str = 'normal'


class KeywordParser:
    """Robot Framework 關鍵字解析器 - 修正版本"""

    def __init__(self):
        self.keywords_by_category: Dict[str, Dict[str, KeywordInfo]] = {}

    def parse_library(self, library_instance: Any, category: str) -> List[KeywordInfo]:
        """解析庫實例中的所有關鍵字"""
        if category not in self.keywords_by_category:
            self.keywords_by_category[category] = {}

        keywords = []

        for name, member in inspect.getmembers(library_instance):
            if name.startswith('_'):
                continue

            if hasattr(member, 'robot_name'):
                try:
                    doc = inspect.getdoc(member) or ''
                    description, args_doc, returns_doc = self._parse_docstring(doc)

                    signature = inspect.signature(member)

                    arguments = []
                    for param_name, param in signature.parameters.items():
                        if param_name == 'self':
                            continue

                        param_type = (param.annotation.__name__
                                      if param.annotation != inspect.Parameter.empty
                                      else 'any')

                        default = None
                        if param.default != inspect.Parameter.empty:
                            default = str(param.default)

                        # 從文檔中獲取參數詳細信息
                        param_info = args_doc.get(param_name, {})
                        param_desc = param_info.get('description', '')
                        param_options = param_info.get('options', [])
                        param_example = param_info.get('example', '')

                        # 🔧 修正：確保有選項時不會被設為 None
                        final_options = param_options if param_options else None

                        arguments.append(ArgumentInfo(
                            name=param_name,
                            type=param_type,
                            description=param_desc,
                            default=default,
                            value=default or "",
                            options=final_options,
                            example=param_example if param_example else None
                        ))

                    keyword_info = KeywordInfo(
                        name=name,
                        description=description,
                        category=category,
                        arguments=arguments,
                        returns=returns_doc,
                        library_name=library_instance.__class__.__name__,
                        priority=self._determine_priority(name, description)
                    )

                    keywords.append(keyword_info)
                    self.keywords_by_category[category][name] = keyword_info

                except Exception as e:
                    print(f"Error parsing keyword {name}: {e}")
                    import traceback
                    traceback.print_exc()  # 📝 添加詳細錯誤信息

        return keywords

    def _parse_docstring(self, docstring: str) -> tuple[str, dict, str]:
        """解析文檔字符串 - 改進版本"""
        lines = docstring.split('\n')
        description = []
        args_doc = {}
        returns_doc = ''

        mode = 'description'
        current_arg = None
        current_arg_info = {}

        # print(f"🔍 開始解析文檔字串：")  # 📝 調試信息

        for i, line in enumerate(lines):
            original_line = line
            line_stripped = line.strip()

            # print(f"Line {i}: '{original_line}' -> 模式: {mode}")  # 📝 調試信息

            if not line_stripped:
                continue

            # 檢測區段切換
            if line_stripped.lower().startswith('args:') or line_stripped.lower().startswith('arguments:'):
                mode = 'args'
                # print(f"切換到 args 模式")  # 📝 調試信息
                continue
            elif line_stripped.lower().startswith('returns:'):
                mode = 'returns'
                # 保存最後一個參數
                if current_arg and current_arg_info:
                    args_doc[current_arg] = current_arg_info.copy()
                    # print(f"保存參數: {current_arg} -> {current_arg_info}")  # 📝 調試信息
                continue

            if mode == 'description':
                description.append(line_stripped)

            elif mode == 'args':
                # 🔧 改進的縮排檢測
                indent_level = len(original_line) - len(original_line.lstrip())

                # 如果是參數行（通常縮排 4 個空格，且包含冒號）
                if indent_level <= 4 and ':' in line_stripped and not line_stripped.startswith(
                        'options:') and not line_stripped.startswith('default:') and not line_stripped.startswith(
                        'description:') and not line_stripped.startswith('example:'):
                    # 保存前一個參數的信息
                    if current_arg and current_arg_info:
                        args_doc[current_arg] = current_arg_info.copy()
                        # print(f"保存參數: {current_arg} -> {current_arg_info}")  # 📝 調試信息

                    # 開始新參數
                    parts = line_stripped.split(':', 1)
                    if len(parts) > 0:
                        current_arg = parts[0].strip()
                        current_arg_info = {
                            'description': parts[1].strip() if len(parts) > 1 else '',
                            'options': [],
                            'example': '',
                            'default': ''
                        }
                        # print(f"開始新參數: {current_arg}")  # 📝 調試信息

                elif indent_level > 4 and current_arg:  # 參數的詳細信息（縮排更多）
                    self._parse_arg_detail_line(line_stripped, current_arg_info)
                    # print(f"解析參數詳情: {line_stripped} -> {current_arg_info}")  # 📝 調試信息

            elif mode == 'returns':
                returns_doc = line_stripped

        # 🔧 確保保存最後一個參數
        if current_arg and current_arg_info:
            args_doc[current_arg] = current_arg_info.copy()
            # print(f"保存最後參數: {current_arg} -> {current_arg_info}")  # 📝 調試信息

        # print(f"🎯 最終解析結果: args_doc = {args_doc}")  # 📝 調試信息

        return (
            ' '.join(description),
            args_doc,
            returns_doc
        )

    def _parse_arg_detail_line(self, line: str, arg_info: dict):
        """解析參數詳細信息行 - 改進版本"""
        line = line.strip()

        if line.startswith('options:'):
            options_str = line.replace('options:', '').strip()
            # print(f"🔧 解析選項: '{options_str}'")  # 📝 調試信息

            if '|' in options_str:
                options = [opt.strip() for opt in options_str.split('|') if opt.strip()]
            else:
                options = [opt.strip() for opt in options_str.split(',') if opt.strip()]

            arg_info['options'] = options
            # print(f"✅ 設置選項: {options}")  # 📝 調試信息

        elif line.startswith('default:'):
            default_value = line.replace('default:', '').strip()
            arg_info['default'] = default_value
            # print(f"✅ 設置默認值: {default_value}")  # 📝 調試信息

        elif line.startswith('example:'):
            example_value = line.replace('example:', '').strip()
            arg_info['example'] = example_value
            # print(f"✅ 設置示例: {example_value}")  # 📝 調試信息

        elif line.startswith('description:'):
            desc_value = line.replace('description:', '').strip()
            arg_info['description'] = desc_value
            # print(f"✅ 設置描述: {desc_value}")  # 📝 調試信息

        else:
            # 如果沒有明確的前綴，假設是描述的一部分
            if arg_info['description']:
                arg_info['description'] += ' ' + line
            else:
                arg_info['description'] = line
            # print(f"📝 追加描述: {line}")  # 📝 調試信息

    def get_keywords_for_category(self, category: str) -> List[Dict[str, Any]]:
        """獲取特定類別的所有關鍵字的卡片配置"""
        if category not in self.keywords_by_category:
            return []

        return [self.convert_to_card_config(kw)
                for kw in self.keywords_by_category[category].values()]

    def convert_to_card_config(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """將關鍵字數據轉換為 KeywordCard 配置格式"""
        arguments_config = []
        for arg in keyword_info.arguments:
            arg_config = {
                'name': arg.name,
                'type': arg.type,
                'description': arg.description,
                'default': arg.default,
                'value': arg.value or arg.default or ""
            }

            # 🔧 確保選項信息正確添加
            if arg.options and len(arg.options) > 0:
                arg_config['options'] = arg.options
                # print(f"📦 添加選項到配置: {arg.name} -> {arg.options}")  # 📝 調試信息

            if arg.example:
                arg_config['example'] = arg.example

            arguments_config.append(arg_config)

        config = {
            'id': keyword_info.name,
            'name': keyword_info.name,
            'category': keyword_info.category,
            'description': keyword_info.description,
            'arguments': arguments_config,
            'returns': keyword_info.returns,
            'priority': keyword_info.priority
        }

        # print(f"🎯 最終卡片配置: {config}")  # 📝 調試信息
        return config

    def _determine_priority(self, name: str, description: str) -> str:
        """決定關鍵字優先級"""
        name_lower = name.lower()

        if any(word in name_lower for word in ['connect', 'init', 'setup', 'reset']):
            return 'required'
        elif any(word in name_lower for word in ['check', 'verify', 'test', 'measure']):
            return 'normal'
        else:
            return 'optional'

    def clear_category(self, category: str):
        """清除特定類別的所有關鍵字"""
        if category in self.keywords_by_category:
            self.keywords_by_category[category].clear()

# # test_keyword_parser.py - 測試腳本
# import sys
# import os
#
# # 添加項目路徑
# project_root = os.path.dirname(os.path.abspath(__file__))
# if project_root not in sys.path:
#     sys.path.append(project_root)
#
# from Lib.HMILibrary import HMILibrary
#
#
# def test_keyword_parsing():
#     """測試關鍵字解析"""
#     print("🚀 開始測試 KeywordParser...")
#
#     # 創建解析器和庫實例
#     parser = KeywordParser()
#     hmi_lib = HMILibrary()
#
#     print("\n📊 解析 HMI Library...")
#     keywords = parser.parse_library(hmi_lib, "hmi")
#
#     print(f"\n✅ 解析完成，找到 {len(keywords)} 個關鍵字")
#
#     # 查找 button_click 關鍵字
#     button_click_kw = None
#     for kw in keywords:
#         if kw.name == "button_click":
#             button_click_kw = kw
#             break
#
#     if button_click_kw:
#         print(f"\n🎯 找到 button_click 關鍵字:")
#         print(f"  名稱: {button_click_kw.name}")
#         print(f"  描述: {button_click_kw.description}")
#         print(f"  參數數量: {len(button_click_kw.arguments)}")
#
#         for i, arg in enumerate(button_click_kw.arguments):
#             print(f"\n  參數 {i + 1}: {arg.name}")
#             print(f"    類型: {arg.type}")
#             print(f"    描述: {arg.description}")
#             print(f"    默認值: {arg.default}")
#             print(f"    選項: {arg.options}")  # 🔍 重點檢查這裡
#             print(f"    示例: {arg.example}")
#
#     # 轉換為卡片配置格式
#     print(f"\n🔄 轉換為卡片配置格式...")
#     if button_click_kw:
#         card_config = parser.convert_to_card_config(button_click_kw)
#         print(f"\n📦 卡片配置:")
#         print(f"  ID: {card_config['id']}")
#         print(f"  名稱: {card_config['name']}")
#         print(f"  類別: {card_config['category']}")
#         print(f"  描述: {card_config['description']}")
#
#         print(f"\n  參數配置:")
#         for i, arg_config in enumerate(card_config['arguments']):
#             print(f"    參數 {i + 1}: {arg_config['name']}")
#             print(f"      類型: {arg_config['type']}")
#             print(f"      描述: {arg_config['description']}")
#             print(f"      默認值: {arg_config['default']}")
#             print(f"      選項: {arg_config.get('options', 'None')}")  # 🔍 重點檢查這裡
#             print(f"      示例: {arg_config.get('example', 'None')}")
#
#     print(f"\n🎉 測試完成！")
#
#
# if __name__ == "__main__":
#     test_keyword_parsing()