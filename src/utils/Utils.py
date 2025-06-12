from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import datetime
from typing import Dict, Any


def change_icon_color(icon, color):
    px = icon.pixmap(16, 16)

    painter = QPainter(px)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(px.rect(), QColor(color))
    painter.end()

    return QIcon(px)


def setup_click_animation(button: QPushButton) -> QPushButton:
   anim = QPropertyAnimation(button, b"geometry")
   anim.setDuration(100)

   def on_pressed():
       geo = button.geometry()
       anim.setStartValue(geo)
       anim.setEndValue(QRect(geo.x() + 2, geo.y() + 2,
                            geo.width() - 4, geo.height() - 4))
       anim.start()

   def on_released():
       geo = button.geometry()
       anim.setStartValue(geo)
       anim.setEndValue(QRect(geo.x() - 2, geo.y() - 2,
                            geo.width() + 4, geo.height() + 4))
       anim.start()

   button.pressed.connect(on_pressed)
   button.released.connect(on_released)
   return button


class PrettyMessageFormatter:
    """漂亮的消息格式化器"""

    # 🎨 消息類型顏色和符號
    TYPE_STYLES = {
        'test_start': {'emoji': '🚀', 'color': '\033[92m', 'label': 'TEST_START'},  # 綠色
        'test_end': {'emoji': '🏁', 'color': '\033[94m', 'label': 'TEST_END'},  # 藍色
        'keyword_start': {'emoji': '▶️', 'color': '\033[93m', 'label': 'KW_START'},  # 黃色
        'keyword_end': {'emoji': '✅', 'color': '\033[95m', 'label': 'KW_END'},  # 紫色
        'log': {'emoji': '📝', 'color': '\033[96m', 'label': 'LOG'},  # 青色
        'error': {'emoji': '❌', 'color': '\033[91m', 'label': 'ERROR'},  # 紅色
        'unknown': {'emoji': '❓', 'color': '\033[90m', 'label': 'UNKNOWN'},  # 灰色
    }

    # 🎨 狀態顏色
    STATUS_COLORS = {
        'PASS': '\033[92m',  # 綠色
        'FAIL': '\033[91m',  # 紅色
        'RUNNING': '\033[93m',  # 黃色
        'SKIP': '\033[90m',  # 灰色
    }

    # 重置顏色
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def format_message(cls, msg: Dict[str, Any], compact: bool = False) -> str:
        """
        格式化消息為漂亮的輸出

        Args:
            msg: 消息字典
            compact: 是否使用緊湊格式
        """
        if compact:
            return cls._format_compact(msg)
        else:
            return cls._format_detailed(msg)

    @classmethod
    def _format_detailed(cls, msg: Dict[str, Any]) -> str:
        """詳細格式化"""

        # 獲取基本信息
        counter = msg.get('counter', '?')
        msg_type = msg.get('type', 'unknown')
        keyword = msg.get('keyword', '')
        test_name = msg.get('test_name', '')
        test_id = msg.get('test_id', '')
        timestamp = msg.get('timestamp', '')
        status = msg.get('status', '')

        # 獲取樣式
        style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
        emoji = style['emoji']
        color = style['color']
        label = style['label']

        # 格式化時間戳
        formatted_time = cls._format_timestamp(timestamp)

        # 🔥 使用完整的測試名稱（不截斷）
        full_test_name = test_name

        # 格式化狀態
        formatted_status = cls._format_status(status)

        # 構建輸出
        lines = []

        # 主要信息行
        header = f"{color}{cls.BOLD}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"

        if keyword:
            header += f" │ 🔧 {cls.BOLD}{keyword}{cls.RESET}"

        if formatted_status:
            header += f" │ {formatted_status}"

        lines.append(header)

        # 詳細信息行
        if test_id:
            lines.append(f"    📋 Test ID: {cls.BOLD}{test_id}{cls.RESET}")

        # 🔥 顯示完整測試名稱
        if full_test_name:
            lines.append(f"    📝 Test: {full_test_name}")

        # 🔥 如果有keyword，單獨顯示一行
        if keyword:
            lines.append(f"    🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}")

        if formatted_time:
            lines.append(f"    ⏰ Time: {formatted_time}")

        # 分隔線（可選）
        if counter and int(str(counter)) % 5 == 0:
            lines.append(f"    {'-' * 100}")

        return '\n'.join(lines)

    @classmethod
    def _format_compact(cls, msg: Dict[str, Any]) -> str:
        """緊湊格式化 - 顯示完整信息"""

        counter = msg.get('counter', '?')
        msg_type = msg.get('type', 'unknown')
        keyword = msg.get('keyword', '')
        test_name = msg.get('test_name', '')
        test_id = msg.get('test_id', '')
        status = msg.get('status', '')
        timestamp = msg.get('timestamp', '')

        # 獲取樣式
        style = cls.TYPE_STYLES.get(msg_type, cls.TYPE_STYLES['unknown'])
        emoji = style['emoji']
        color = style['color']
        label = style['label']

        # 格式化狀態
        status_str = f" [{cls._format_status(status, short=True)}]" if status else ""

        # 格式化時間
        time_str = cls._format_timestamp(timestamp)
        time_display = f" ⏰{time_str}" if time_str else ""

        # 🔥 構建完整的輸出行
        lines = []

        # 主要信息行
        main_line = (f"{color}#{counter:>3}{cls.RESET} {emoji} {color}{label:<12}{cls.RESET}"
                     f" │ 🆔{test_id}{status_str}{time_display}")
        lines.append(main_line)

        # 🔥 如果有keyword，顯示keyword行
        if keyword:
            keyword_line = f"     🔧 Keyword: {cls.BOLD}{keyword}{cls.RESET}"
            lines.append(keyword_line)

        # 🔥 如果有完整測試名稱，顯示測試名稱行
        if test_name:
            test_line = f"     📝 Test: {test_name}"
            lines.append(test_line)

        return '\n'.join(lines)

    @classmethod
    def _format_timestamp(cls, timestamp: Any) -> str:
        """格式化時間戳"""
        if not timestamp:
            return ""

        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.datetime.fromtimestamp(timestamp)
                return dt.strftime("%H:%M:%S.%f")[:-3]  # 保留毫秒
            elif isinstance(timestamp, str):
                return timestamp
            else:
                return str(timestamp)
        except:
            return str(timestamp)

    @classmethod
    def _format_status(cls, status: str, short: bool = False) -> str:
        """格式化狀態"""
        if not status:
            return ""

        status_upper = status.upper()
        color = cls.STATUS_COLORS.get(status_upper, '')

        if short:
            status_map = {'RUNNING': 'RUN', 'PASS': 'OK', 'FAIL': 'ERR'}
            display_status = status_map.get(status_upper, status_upper[:3])
        else:
            display_status = status_upper

        return f"{color}{display_status}{cls.RESET}" if color else display_status

    @classmethod
    def _truncate_test_name(cls, test_name: str, max_length: int = None) -> str:
        """
        🔥 修改：現在返回完整的測試名稱，不進行截斷
        保留此函數以維護向後兼容性
        """
        return test_name if test_name else ""
