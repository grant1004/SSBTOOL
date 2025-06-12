# src/ui/widgets/TopWidget.py - 改良版本，添加背景和更好的排版
"""
TopWidget 改良版本
添加漸層背景、更好的佈局和現代化設計
"""

import asyncio
from typing import Dict, Any, Optional

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# 導入 MVC 架構
from src.interfaces.device_interface import IDeviceView, IDeviceViewEvents, DeviceType, DeviceStatus
from src.mvc_framework.base_view import BaseView
from src.controllers.device_controller import DeviceController

# 導入新的狀態按鈕
from src.ui.components.StatusButton import ComponentStatusButton
from src.ui.components.SwitchThemeButton import SwitchThemeButton


class TopWidget(BaseView, IDeviceView, IDeviceViewEvents):
    """
    改良版 TopWidget
    具有漸層背景、更好的佈局和現代化設計
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._device_controller: Optional[DeviceController] = None

        # 設備配置
        self.devices = {
            DeviceType.USB: {'icon': 'parts_cable', 'name': 'USB'},
            DeviceType.POWER: {'icon': 'show_chart', 'name': 'Power'},
            DeviceType.LOADER: {'icon': 'parts_charger', 'name': 'Loader'}
        }

        self.status_buttons: Dict[DeviceType, ComponentStatusButton] = {}

        # 獲取主題管理器
        self.theme_manager = self._get_theme_manager()

        self.setup_ui()
        self._logger.info("TopWidget initialized with improved design and background")

    def set_device_controller(self, controller: DeviceController) -> None:
        """設置設備控制器"""
        self._device_controller = controller
        if controller:
            controller.register_view(self)
        self._logger.info("Device controller set and view registered")

    #region ==================== UI 設置 ====================

    def setup_ui(self):
        """設置 UI"""
        self.setFixedHeight(72)  # 增加高度以容納更豐富的設計
        self.setContentsMargins(0, 0, 0, 0)

        # 設置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 創建內容容器
        content_container = QWidget()
        content_container.setObjectName("top-widget-container")
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(24, 16, 24, 16)  # 增加內邊距

        # 左側：標題區域
        title_section = self._create_title_section()
        content_layout.addWidget(title_section, alignment=Qt.AlignmentFlag.AlignLeft)

        # 中間：設備狀態區域
        device_section = self._create_device_section()
        content_layout.addWidget(device_section, alignment=Qt.AlignmentFlag.AlignLeft)

        # 右側：控制區域
        # control_section = self._create_control_section()
        # content_layout.addWidget(control_section)

        main_layout.addWidget(content_container)

        # 設置樣式
        self._setup_styles()
        self._setup_shadow()

    def _create_title_section(self):
        """創建標題區域"""
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        # 主標題
        title_label = QLabel("SSB Tool")
        title_label.setObjectName("main-title")
        title_layout.addWidget(title_label)

        # 副標題
        subtitle_label = QLabel("Device Management")
        subtitle_label.setObjectName("subtitle")
        title_layout.addWidget(subtitle_label)

        title_layout.addStretch()
        return title_widget

    def _create_device_section(self):
        """創建設備狀態區域"""
        device_widget = QWidget()
        device_widget.setObjectName("device-section")
        device_layout = QHBoxLayout(device_widget)
        device_layout.setContentsMargins(16, 0, 16, 0)

        # 創建設備按鈕
        for device_type, config in self.devices.items():
            button = ComponentStatusButton(config['name'], config['icon'], self.main_window)
            button.setFixedSize(200, 40)  # 統一按鈕大小
            self.status_buttons[device_type] = button

            # 連接事件
            button.clicked.connect(lambda checked, dt=device_type: self._handle_device_click(dt))
            button.status_changed.connect(lambda old, new, dt=device_type:
                                          self._on_status_changed(dt, old, new))

            device_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)

        return device_widget

    def _create_control_section(self):
        """創建控制區域"""
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(12)

        # 刷新按鈕
        refresh_button = QPushButton("刷新")
        refresh_button.setObjectName("control-button")
        refresh_button.setFixedSize(80, 36)
        refresh_button.clicked.connect(self.on_refresh_requested)
        control_layout.addWidget(refresh_button)

        # 主題切換按鈕
        if self.theme_manager:
            theme_button = SwitchThemeButton(self.theme_manager, self)
            control_layout.addWidget(theme_button)

        # 設置按鈕（可選）
        settings_button = QPushButton("設置")
        settings_button.setObjectName("control-button")
        settings_button.setFixedSize(80, 36)
        settings_button.clicked.connect(self._open_settings)
        control_layout.addWidget(settings_button)

        control_layout.addStretch()
        return control_widget

    def _setup_styles(self):
        """設置樣式"""
        if self.theme_manager:
            current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

            # 根據主題設置樣式
            if self.theme_manager.current_theme.value == "industrial":
                self._apply_dark_theme_styles(current_theme)
            else:
                self._apply_light_theme_styles(current_theme)
        else:
            self._apply_default_styles()

    def _apply_light_theme_styles(self, theme):
        """應用淺色主題樣式"""
        self.setStyleSheet(f"""
            TopWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {theme.PRIMARY}, 
                    stop:0.3 {theme.PRIMARY_LIGHT}, 
                    stop:1 {theme.BACKGROUND});
                border-bottom: 2px solid {theme.BORDER};
            }}
            
            #TitleSection {{
                background: transparent;
            }} 

            #top-widget-container {{
                background: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}

            #main-title {{
                font-size: 24px;
                font-weight: bold;
                color: {theme.PRIMARY};
                letter-spacing: 1px;
            }}

            #subtitle {{
                font-size: 12px;
                color: {theme.TEXT_SECONDARY};
                font-weight: 500;
            }}

            #section-label {{
                font-size: 14px;
                font-weight: 600;
                color: {theme.TEXT_PRIMARY};
                padding: 0 8px;
            }}

            #device-section {{
                background: transparent;
            }}

            #separator {{
                color: {theme.BORDER};
                background-color: {theme.BORDER};
            }}

            #control-button {{
                background-color: {theme.SURFACE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid #000000;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }}

            #control-button:hover {{
                background-color: {theme.PRIMARY};
                color: {theme.TEXT_ON_PRIMARY};
                border-color: {theme.PRIMARY};
            }}

            #control-button:pressed {{
                background-color: {theme.PRIMARY_DARK};
            }}
        """)

    def _apply_dark_theme_styles(self, theme):
        """應用深色主題樣式"""
        self.setStyleSheet(f"""
            TopWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2C2C2C, 
                    stop:0.3 #3D3D3D, 
                    stop:1 {theme.BACKGROUND});
                border-bottom: 2px solid {theme.BORDER};
            }}
            
            #TitleSection {{
                background: transparent;
            }} 

            #top-widget-container {{
                background: rgba(45, 45, 45, 0.95);
                border: 1px solid rgba(255, 167, 38, 0.3);
            }}

            #main-title {{
                font-size: 24px;
                font-weight: bold;
                color: {theme.PRIMARY};
                letter-spacing: 1px;
            }}

            #subtitle {{
                font-size: 12px;
                color: {theme.TEXT_SECONDARY};
                font-weight: 500;
            }}

            #section-label {{
                font-size: 14px;
                font-weight: 600;
                color: {theme.TEXT_PRIMARY};
                padding: 0 8px;
            }}

            #device-section {{
                background: rgba(50, 50, 50, 0.8);
                border-radius: 8px;
                border: 1px solid {theme.BORDER};
            }}

            #separator {{
                color: {theme.BORDER};
                background-color: {theme.BORDER};
            }}

            #control-button {{
                background-color: {theme.SURFACE};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid #000000;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }}

            #control-button:hover {{
                background-color: {theme.PRIMARY};
                color: {theme.TEXT_ON_PRIMARY};
                border-color: {theme.PRIMARY};
            }}

            #control-button:pressed {{
                background-color: {theme.PRIMARY_DARK};
            }}
        """)

    def _apply_default_styles(self):
        """應用預設樣式（無主題管理器時）"""
        self.setStyleSheet("""
            TopWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #006C4D, 
                    stop:0.3 #4CAF50, 
                    stop:1 #DBE5DF);
                border-bottom: 2px solid #DDDDDD;
            }
            
            #TitleSection {{
                background: transparent;
            }} 
            
            #top-widget-container {
                background: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }

            #main-title {
                font-size: 24px;
                font-weight: bold;
                color: #006C4D;
                letter-spacing: 1px;
            }

            #subtitle {
                font-size: 12px;
                color: #666666;
                font-weight: 500;
            }

            #section-label {
                font-size: 14px;
                font-weight: 600;
                color: #333333;
                padding: 0 8px;
            }

            #device-section {
                background: rgba(248, 249, 250, 0.8);
                border-radius: 8px;
                border: 1px solid #EEEEEE;
            }

            #separator {
                color: #DDDDDD;
                background-color: #DDDDDD;
            }

            #control-button {
                background-color: #F5F5F5;
                color: #333333;
                border: 1px solid #000000;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }

            #control-button:hover {
                background-color: #006C4D;
                color: #FFFFFF;
                border-color: #006C4D;
            }

            #control-button:pressed {
                background-color: #005C41;
            }
        """)

    def _setup_shadow(self):
        """設置陰影效果"""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _get_theme_manager(self):
        """獲取主題管理器"""
        parent = self.main_window
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent.theme_manager
            parent = parent.parent() if hasattr(parent, 'parent') else None
        return None
    #endregion

    #region ==================== 事件處理 ====================

    def _handle_device_click(self, device_type: DeviceType):
        """處理設備點擊"""
        if not self._device_controller:
            self._logger.error("No device controller available")
            return

        current_status = self.status_buttons[device_type].current_status
        self._logger.info(f"Device {device_type.value} status: {current_status.value}")

        if current_status == DeviceStatus.DISCONNECTED or current_status == DeviceStatus.ERROR:
            asyncio.create_task(self._device_controller.handle_connect_request(device_type))
        elif current_status == DeviceStatus.CONNECTED:
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))

    def _on_status_changed(self, device_type: DeviceType, old_status: DeviceStatus, new_status: DeviceStatus):
        """狀態變更回調"""
        self._logger.debug(f"Device {device_type.value} status: {old_status.value} -> {new_status.value}")

    def _open_settings(self):
        """開啟設置對話框"""
        self.emit_user_action("settings_requested", None)
    #endregion

    #region ==================== IDeviceView 接口實現 ====================

    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態顯示"""
        self._logger.debug(f"Updating {device_type.value} to {status.value}")

        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(status)
        else:
            self._logger.warning(f"No button found for device: {device_type.value}")

    def show_connection_progress(self, device_type: DeviceType, progress: int) -> None:
        """顯示連接進度"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].set_connection_progress(progress)

    def show_connection_success(self, device_type: DeviceType) -> None:
        """顯示連接成功"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.CONNECTED)

        device_name = self.devices[device_type]['name']
        self.show_success_message(f"{device_name} 連接成功")

    def show_connection_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示連接錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        self.show_error_message(f"{device_name} 連接失敗: {error_message}")

    def show_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示設備錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        self.show_error_message(f"{device_name} 錯誤: {error_message}")

    def enable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """啟用設備控制項"""
        if device_type is None:
            for button in self.status_buttons.values():
                button.setEnabled(True)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(True)

    def disable_device_controls(self, device_type: Optional[DeviceType] = None) -> None:
        """禁用設備控制項"""
        if device_type is None:
            for button in self.status_buttons.values():
                button.setEnabled(False)
        elif device_type in self.status_buttons:
            self.status_buttons[device_type].setEnabled(False)

    def update_device_info(self, device_type: DeviceType, info: Dict[str, Any]) -> None:
        """更新設備詳細信息"""
        if device_type in self.status_buttons:
            device_name = self.devices[device_type]['name']
            tooltip = f"{device_name}\n狀態: {info.get('status', 'Unknown')}"

            if 'connection_time' in info:
                tooltip += f"\n連接時間: {info['connection_time']:.1f}s"

            self.status_buttons[device_type].setToolTip(tooltip)

    def request_user_confirmation(self, message: str) -> bool:
        """請求用戶確認"""
        return self.ask_user_confirmation(message, "設備操作確認")

    async def request_user_confirmation_async(self, message: str) -> bool:
        """異步請求用戶確認"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.request_user_confirmation, message
        )

    # endregion

    #region ==================== IDeviceViewEvents 接口實現 ====================

    def on_connect_requested(self, device_type: DeviceType) -> None:
        """連接請求"""
        if self._device_controller:
            asyncio.create_task(self._device_controller.handle_connect_request(device_type))

    def on_disconnect_requested(self, device_type: DeviceType) -> None:
        """斷開請求"""
        if self._device_controller:
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))

    def on_refresh_requested(self) -> None:
        """刷新請求"""
        if self._device_controller:
            self._device_controller.refresh_device_status()

    def on_device_settings_requested(self, device_type: DeviceType) -> None:
        """設備設置請求"""
        self.emit_user_action("device_settings_requested", device_type)

    # endregion

    #region ==================== 主題更新 ====================

    def update_theme(self):
        """更新主題（當主題變更時調用）"""
        self._setup_styles()

    # endregion

    #region ==================== 便利方法 ====================

    def get_all_device_status(self) -> Dict[DeviceType, DeviceStatus]:
        """獲取所有設備狀態"""
        return {dt: btn.current_status for dt, btn in self.status_buttons.items()}

    def set_all_disconnected(self) -> None:
        """設置所有設備為斷開狀態"""
        for button in self.status_buttons.values():
            button.update_status(DeviceStatus.DISCONNECTED)

    def get_connection_summary(self) -> Dict[str, int]:
        """獲取連接摘要"""
        summary = {'total': 0, 'connected': 0, 'error': 0, 'connecting': 0}

        for button in self.status_buttons.values():
            summary['total'] += 1
            status = button.current_status

            if status == DeviceStatus.CONNECTED:
                summary['connected'] += 1
            elif status == DeviceStatus.ERROR:
                summary['error'] += 1
            elif status == DeviceStatus.CONNECTING:
                summary['connecting'] += 1

        return summary

    # endregion