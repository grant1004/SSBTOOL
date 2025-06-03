# src/mvc_framework/base_view.py
"""
MVC 框架基礎 View 類
提供通用的視圖功能
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Signal, QTimer, QObject
import logging
from .metaclass_utils import QObjectABCMeta


class BaseView(QWidget, metaclass=QObjectABCMeta):
    """視圖基類"""

    # 通用信號
    user_action = Signal(str, object)  # (action_name, action_data)
    view_ready = Signal()
    view_destroyed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._controllers = {}
        self._state = {}
        self._validation_errors = []
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_deferred_updates)
        self._deferred_updates = []

    def register_controller(self, name: str, controller: QObject) -> None:
        """註冊控制器"""
        self._controllers[name] = controller

    def get_controller(self, name: str) -> Optional[QObject]:
        """獲取控制器"""
        return self._controllers.get(name)

    def emit_user_action(self, action_name: str, action_data: Any = None) -> None:
        """發出用戶操作信號"""
        self.user_action.emit(action_name, action_data)
        self._logger.debug(f"User action emitted: {action_name}")

    def show_message(self, message: str, title: str = "信息", message_type: str = "info") -> None:
        """顯示消息框"""
        if message_type == "error":
            QMessageBox.critical(self, title, message)
        elif message_type == "warning":
            QMessageBox.warning(self, title, message)
        elif message_type == "question":
            return QMessageBox.question(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def show_error_message(self, error_message: str) -> None:
        """顯示錯誤消息"""
        self.show_message(error_message, "錯誤", "error")

    def show_success_message(self, success_message: str) -> None:
        """顯示成功消息"""
        self.show_message(success_message, "成功", "info")

    def show_warning_message(self, warning_message: str) -> None:
        """顯示警告消息"""
        self.show_message(warning_message, "警告", "warning")

    def ask_user_confirmation(self, question: str, title: str = "確認") -> bool:
        """詢問用戶確認"""
        result = QMessageBox.question(self, title, question,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return result == QMessageBox.StandardButton.Yes

    def set_view_state(self, key: str, value: Any) -> None:
        """設置視圖狀態"""
        self._state[key] = value

    def get_view_state(self, key: str, default: Any = None) -> Any:
        """獲取視圖狀態"""
        return self._state.get(key, default)

    def add_validation_error(self, error: str) -> None:
        """添加驗證錯誤"""
        if error not in self._validation_errors:
            self._validation_errors.append(error)

    def clear_validation_errors(self) -> None:
        """清除驗證錯誤"""
        self._validation_errors.clear()

    def get_validation_errors(self) -> list:
        """獲取驗證錯誤"""
        return self._validation_errors.copy()

    def show_validation_errors(self) -> None:
        """顯示驗證錯誤"""
        if self._validation_errors:
            error_text = "\n".join(self._validation_errors)
            self.show_error_message(f"驗證錯誤:\n{error_text}")

    def defer_update(self, update_func: Callable, delay_ms: int = 100) -> None:
        """延遲更新（避免頻繁更新）"""
        self._deferred_updates.append(update_func)
        self._update_timer.start(delay_ms)

    def _perform_deferred_updates(self) -> None:
        """執行延遲的更新"""
        for update_func in self._deferred_updates:
            try:
                update_func()
            except Exception as e:
                self._logger.error(f"Deferred update failed: {e}")
        self._deferred_updates.clear()

    def enable_controls(self) -> None:
        """啟用控制項 - 子類可覆蓋"""
        self.setEnabled(True)

    def disable_controls(self) -> None:
        """禁用控制項 - 子類可覆蓋"""
        self.setEnabled(False)

    def show_loading_state(self, is_loading: bool, message: str = "載入中...") -> None:
        """顯示載入狀態 - 子類可覆蓋"""
        if is_loading:
            self.disable_controls()
        else:
            self.enable_controls()

    def closeEvent(self, event):
        """視圖關閉事件"""
        self.view_destroyed.emit()
        super().closeEvent(event)

    def showEvent(self, event):
        """視圖顯示事件"""
        self.view_ready.emit()
        super().showEvent(event)