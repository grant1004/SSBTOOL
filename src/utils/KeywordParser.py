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
    options: Optional[List[str]] = None  # 新增：參數選項列表
    example: Optional[str] = None  # 新增：參數示例


@dataclass
class KeywordInfo:
    """關鍵字數據結構"""
    name: str  # 關鍵字名稱
    description: str  # 關鍵字描述
    category: str  # 所屬類別
    arguments: List[ArgumentInfo]  # 參數列表
    returns: str  # 返回值描述
    library_name: str  # 所屬庫名稱
    priority: str = 'normal'  # 優先級


class KeywordParser:
    """Robot Framework 關鍵字解析器"""

    def __init__(self):
        self.keywords_by_category: Dict[str, Dict[str, KeywordInfo]] = {}

    def parse_library(self, library_instance: Any, category: str) -> List[KeywordInfo]:
        """解析庫實例中的所有關鍵字

        Args:
            library_instance: 要解析的 Library 實例
            category: 關鍵字類別（例如：'battery', 'common' 等）

        Returns:
            List[KeywordInfo]: 解析出的關鍵字資訊列表
        """
        if category not in self.keywords_by_category:
            self.keywords_by_category[category] = {}

        keywords = []

        for name, member in inspect.getmembers(library_instance):
            # 跳過私有方法
            if name.startswith('_'):
                continue

            # 只檢查有 @keyword 裝飾器的方法
            if hasattr(member, 'robot_name'):
                try:
                    # 解析文檔字符串
                    doc = inspect.getdoc(member) or ''
                    description, args_doc, returns_doc = self._parse_docstring(doc)

                    # 獲取方法簽名
                    signature = inspect.signature(member)

                    # 解析參數
                    arguments = []
                    for param_name, param in signature.parameters.items():
                        if param_name == 'self':
                            continue

                        # 獲取參數類型
                        param_type = (param.annotation.__name__
                                      if param.annotation != inspect.Parameter.empty
                                      else 'any')

                        # 獲取默認值
                        default = None
                        if param.default != inspect.Parameter.empty:
                            default = str(param.default)

                        # 從文檔中獲取參數詳細信息
                        param_info = args_doc.get(param_name, {})
                        param_desc = param_info.get('description', '')
                        param_options = param_info.get('options', [])
                        param_example = param_info.get('example', '')

                        arguments.append(ArgumentInfo(
                            name=param_name,
                            type=param_type,
                            description=param_desc,
                            default=default,
                            value=default,
                            options=param_options if param_options else None,
                            example=param_example if param_example else None
                        ))

                    # 創建關鍵字信息
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

        return keywords

    def _parse_docstring(self, docstring: str) -> tuple[str, dict, str]:
        """解析文檔字符串，提取描述、參數文檔和返回值文檔"""
        lines = docstring.split('\n')
        description = []
        args_doc = {}
        returns_doc = ''

        mode = 'description'
        current_arg = None
        current_arg_info = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.lower().startswith('args:') or line.lower().startswith('arguments:'):
                mode = 'args'
                continue
            elif line.lower().startswith('returns:'):
                mode = 'returns'
                continue

            if mode == 'description':
                description.append(line)
            elif mode == 'args':
                if line.startswith('    '):  # 縮排行，是參數的詳細信息
                    if current_arg and line.strip():
                        # 解析參數的詳細屬性
                        self._parse_arg_detail_line(line.strip(), current_arg_info)
                else:  # 新參數
                    # 保存前一個參數的信息
                    if current_arg and current_arg_info:
                        args_doc[current_arg] = current_arg_info.copy()

                    # 開始新參數
                    parts = line.split(':')
                    if len(parts) > 0:
                        current_arg = parts[0].strip()
                        current_arg_info = {
                            'description': parts[1].strip() if len(parts) > 1 else '',
                            'options': [],
                            'example': '',
                            'default': ''
                        }
            elif mode == 'returns':
                returns_doc = line.strip()

        # 保存最後一個參數的信息
        if current_arg and current_arg_info:
            args_doc[current_arg] = current_arg_info

        return (
            ' '.join(description),
            args_doc,
            returns_doc
        )

    def _parse_arg_detail_line(self, line: str, arg_info: dict):
        """解析參數詳細信息行"""
        line = line.strip()

        if line.startswith('options:'):
            # 解析選項，支持用 | 或 , 分隔
            options_str = line.replace('options:', '').strip()
            if '|' in options_str:
                options = [opt.strip() for opt in options_str.split('|') if opt.strip()]
            else:
                options = [opt.strip() for opt in options_str.split(',') if opt.strip()]
            arg_info['options'] = options

        elif line.startswith('default:'):
            # 解析默認值
            default_value = line.replace('default:', '').strip()
            arg_info['default'] = default_value

        elif line.startswith('example:'):
            # 解析示例
            example_value = line.replace('example:', '').strip()
            arg_info['example'] = example_value

        elif line.startswith('description:'):
            # 解析描述
            desc_value = line.replace('description:', '').strip()
            arg_info['description'] = desc_value

        elif not any(line.startswith(prefix) for prefix in ['options:', 'default:', 'example:', 'description:']):
            # 如果沒有明確的前綴，假設是描述的一部分
            if arg_info['description']:
                arg_info['description'] += ' ' + line
            else:
                arg_info['description'] = line

    def get_keywords_for_category(self, category: str) -> List[Dict[str, Any]]:
        """獲取特定類別的所有關鍵字的卡片配置"""
        if category not in self.keywords_by_category:
            return []

        return [self.convert_to_card_config(kw)
                for kw in self.keywords_by_category[category].values()]

    def convert_to_card_config(self, keyword_info: KeywordInfo) -> Dict[str, Any]:
        """將關鍵字數據轉換為 KeywordCard 配置格式"""
        # 轉換參數信息，包含選項
        arguments_config = []
        for arg in keyword_info.arguments:
            arg_config = {
                'name': arg.name,
                'type': arg.type,
                'description': arg.description,
                'default': arg.default,
                'value': arg.value
            }

            # 添加選項信息
            if arg.options:
                arg_config['options'] = arg.options

            # 添加示例信息
            if arg.example:
                arg_config['example'] = arg.example

            arguments_config.append(arg_config)

        return {
            'id': keyword_info.name,
            'name': keyword_info.name,
            'category': keyword_info.category,
            'description': keyword_info.description,
            'arguments': arguments_config,
            'returns': keyword_info.returns,
            'priority': keyword_info.priority
        }

    def _determine_priority(self, name: str, description: str) -> str:
        """決定關鍵字優先級"""
        name_lower = name.lower()
        desc_lower = description.lower()

        # 必要的系統操作關鍵字
        if any(word in name_lower for word in ['connect', 'init', 'setup', 'reset']):
            return 'required'

        # 一般測試關鍵字
        elif any(word in name_lower for word in ['check', 'verify', 'test', 'measure']):
            return 'normal'

        # 其他輔助關鍵字
        else:
            return 'optional'

    def clear_category(self, category: str):
        """清除特定類別的所有關鍵字"""
        if category in self.keywords_by_category:
            self.keywords_by_category[category].clear()