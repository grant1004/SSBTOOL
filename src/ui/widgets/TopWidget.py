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


class ComPortInputDialog(QDialog):
    """COM PORT 輸入對話框"""

    def __init__(self, device_name: str, default_port: str = "", parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self.com_port = default_port
        self.setup_ui()

    def setup_ui(self):
        """設置對話框 UI"""
        self.setWindowTitle(f"{self.device_name} - COM PORT 設定")
        self.setFixedSize(400, 200)
        self.setModal(True)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 標題
        title_label = QLabel(f"請輸入 {self.device_name} 的 COM PORT:")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # COM PORT 輸入區域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        com_label = QLabel("COM PORT:")
        com_label.setFont(QFont("Microsoft YaHei", 10))
        input_layout.addWidget(com_label)

        self.com_port_input = QLineEdit()
        self.com_port_input.setPlaceholderText("例如: COM32")
        self.com_port_input.setText(self.com_port)
        self.com_port_input.setFont(QFont("Consolas", 11))
        self.com_port_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 11px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                background-color: #f9f9f9;
            }
        """)
        input_layout.addWidget(self.com_port_input)

        layout.addLayout(input_layout)

        # 按鈕區域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # 取消按鈕
        cancel_button = QPushButton("取消")
        cancel_button.setFixedSize(100, 40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 6px;
                color: #333;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #bbb;
            }
            QPushButton:pressed {
                background-color: #ddd;
            }
        """)
        cancel_button.clicked.connect(self.reject)

        # 確認按鈕
        confirm_button = QPushButton("確認連接")
        confirm_button.setFixedSize(100, 40)
        confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        confirm_button.clicked.connect(self.accept)
        confirm_button.setDefault(True)

        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)

        # 設置焦點到輸入框
        self.com_port_input.setFocus()

        # 連接 Enter 鍵事件
        self.com_port_input.returnPressed.connect(self.accept)

    def get_com_port(self) -> str:
        """取得輸入的 COM PORT"""
        return self.com_port_input.text().strip().upper()

    def accept(self):
        """確認按鈕點擊處理"""
        port = self.get_com_port()
        if not port:
            QMessageBox.warning(self, "輸入錯誤", "請輸入有效的 COM PORT!")
            return

        if not port.startswith("COM"):
            # 自動加上 COM 前綴
            if port.isdigit():
                port = f"COM{port}"
            else:
                QMessageBox.warning(self, "格式錯誤", "COM PORT 格式應為 'COMxx' 或數字!")
                return

        self.com_port = port
        super().accept()


class TopWidget(BaseView, IDeviceView, IDeviceViewEvents):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self._device_controller: Optional[DeviceController] = None

        # 設備配置 - 包含預設 COM PORT
        self.devices = {
            DeviceType.USB: {'icon': 'parts_cable', 'name': 'USB', 'default_port': 'COM19'},
            DeviceType.POWER: {'icon': 'show_chart', 'name': 'Power', 'default_port': 'COM32'},
            DeviceType.LOADER: {'icon': 'parts_charger', 'name': 'Loader', 'default_port': 'COM37'}
        }

        self.status_buttons: Dict[DeviceType, ComponentStatusButton] = {}

        # 儲存各設備的 COM PORT 設定
        self.device_com_ports: Dict[DeviceType, str] = {}

        # 獲取主題管理器
        self.theme_manager = self._get_theme_manager()

        self.setup_ui()
        self._logger.info("TopWidget initialized with COM PORT input support")

    def register_controller(self, name: str, controller: DeviceController) -> None:
        super().register_controller(name, controller)
        self._device_controller = controller
        if controller:
            controller.register_view(self)
            self._logger.info("Device controller set and view registered")

    # region ==================== UI 設置 ====================

    def setup_ui(self):
        """設置 UI"""
        self.setFixedHeight(72)  # 增加高度以容納更豐富的設計
        self.setContentsMargins(0, 0, 0, 0)

        # 設置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 創建內容容器
        content_container = QWidget()
        content_container.setObjectName("top-widget-container")
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(24, 16, 24, 16)  # 增加內邊距
        content_layout.setSpacing(100)
        # 左側：標題區域
        title_section = self._create_title_section()
        title_section.setObjectName("title-section")
        title_section.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        content_layout.addWidget(title_section, 0)  # 拉伸因子為0

        # 中間：設備狀態區域
        device_section = self._create_device_section()
        device_section.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        content_layout.addWidget(device_section, 0)  # 拉伸因子為0

        content_layout.addStretch(1)

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

        return title_widget

    def _create_device_section(self):
        """創建設備狀態區域"""
        device_widget = QWidget()
        device_widget.setObjectName("device-section")
        device_layout = QHBoxLayout(device_widget)
        device_layout.setContentsMargins(0, 0, 0, 0)
        # 調試：檢查設備數據
        print(f"設備數量: {len(self.devices) if hasattr(self, 'devices') else 0}")
        # 創建設備按鈕
        for device_type, config in self.devices.items():
            button = ComponentStatusButton(config['name'], config['icon'], self.main_window)
            button.setFixedSize(200, 40)  # 統一按鈕大小
            self.status_buttons[device_type] = button

            # 設置預設 COM PORT
            self.device_com_ports[device_type] = config['default_port']

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
            theme_button = SwitchThemeButton(self.theme_manager, self.main_window)
            theme_button.setFixedSize(36, 36)
            control_layout.addWidget(theme_button)

        return control_widget

    def _setup_styles(self):
        """設置樣式"""
        self.setStyleSheet("""
            #top-widget-container {
                background: #F5F5F5;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            #main-title {
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 18px;
                font-weight: bold;
                color: #2E7D32;
                margin: 0;
            }

            #subtitle {
                font-family: 'Microsoft YaHei', sans-serif;
                font-size: 11px;
                color: #666666;
                margin: 0;
            }

            #device-section {
                background: transparent;
                padding: 0 16px;
            }

            #control-button {
                background-color: #4CAF50;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }

            #control-button:hover {
                background-color: #45a049;
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

    # endregion

    # region ==================== COM PORT 對話框處理 ====================

    def _show_com_port_dialog(self, device_type: DeviceType) -> Optional[str]:
        """顯示 COM PORT 輸入對話框"""
        device_config = self.devices[device_type]
        current_port = self.device_com_ports.get(device_type, device_config['default_port'])

        dialog = ComPortInputDialog(
            device_name=device_config['name'],
            default_port=current_port,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_port = dialog.get_com_port()
            self.device_com_ports[device_type] = new_port
            self._logger.info(f"User set {device_type.value} COM PORT to: {new_port}")
            return new_port
        else:
            self._logger.info(f"User cancelled COM PORT input for {device_type.value}")
            return None

    # endregion

    # region ==================== 事件處理 ====================

    def _handle_device_click(self, device_type: DeviceType):
        """處理設備點擊 - 新增 COM PORT 輸入"""
        if not self._device_controller:
            self._logger.error("No device controller available")
            return

        current_status = self.status_buttons[device_type].current_status
        self._logger.info(f"Device {device_type.value} status: {current_status.value}")

        if current_status == DeviceStatus.DISCONNECTED or current_status == DeviceStatus.ERROR:
            # 連接前先顯示 COM PORT 輸入對話框
            if device_type == DeviceType.USB:
                asyncio.create_task(self._device_controller.handle_connect_request(device_type, None))
            else :
                com_port = self._show_com_port_dialog(device_type)
                self.set_device_com_port( device_type, com_port )
                if com_port:
                    # 將 COM PORT 資訊傳遞給控制器
                    asyncio.create_task(self._device_controller.handle_connect_request(device_type, com_port))
                else:
                    self._logger.info(f"Connection cancelled for {device_type.value}")

        elif current_status == DeviceStatus.CONNECTED:
            asyncio.create_task(self._device_controller.handle_disconnect_request(device_type))

    def _on_status_changed(self, device_type: DeviceType, old_status: DeviceStatus, new_status: DeviceStatus):
        """狀態變更回調"""
        self._logger.debug(f"Device {device_type.value} status: {old_status.value} -> {new_status.value}")

    def _open_settings(self):
        """開啟設置對話框"""
        self.emit_user_action("settings_requested", None)

    # endregion

    # region ==================== IDeviceView 接口實現 ====================

    def update_device_status(self, device_type: DeviceType, status: DeviceStatus) -> None:
        """更新設備狀態顯示"""
        self._logger.debug(f"Updating {device_type.value} to {status.value}")

        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(status)

            # 更新按鈕提示資訊，包含 COM PORT
            if device_type in self.device_com_ports:
                device_name = self.devices[device_type]['name']
                com_port = self.device_com_ports[device_type]
                tooltip = f"{device_name}\nCOM PORT: {com_port}\n狀態: {status.value}"
                self.status_buttons[device_type].setToolTip(tooltip)
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
        com_port = self.device_com_ports.get(device_type, "Unknown")
        self.show_success_message(f"{device_name} ({com_port}) 連接成功")

    def show_connection_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示連接錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        com_port = self.device_com_ports.get(device_type, "Unknown")
        self.show_error_message(f"{device_name} ({com_port}) 連接失敗: {error_message}")

    def show_device_error(self, device_type: DeviceType, error_message: str) -> None:
        """顯示設備錯誤"""
        if device_type in self.status_buttons:
            self.status_buttons[device_type].update_status(DeviceStatus.ERROR)

        device_name = self.devices[device_type]['name']
        com_port = self.device_com_ports.get(device_type, "Unknown")
        self.show_error_message(f"{device_name} ({com_port}) 錯誤: {error_message}")

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
            com_port = self.device_com_ports.get(device_type, "Unknown")
            tooltip = f"{device_name}\nCOM PORT: {com_port}\n狀態: {info.get('status', 'Unknown')}"

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

    # region ==================== IDeviceViewEvents 接口實現 ====================

    def on_connect_requested(self, device_type: DeviceType) -> None:
        """連接請求 - 已修改為透過 _handle_device_click 處理"""
        # 這個方法現在由 _handle_device_click 取代，因為我們需要先獲取 COM PORT
        pass

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

    # region ==================== 主題更新 ====================

    def update_theme(self):
        """更新主題（當主題變更時調用）"""
        self._setup_styles()

    # endregion

    # region ==================== 便利方法 ====================

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

    def get_device_com_port(self, device_type: DeviceType) -> str:
        """獲取設備的 COM PORT"""
        return self.device_com_ports.get(device_type, self.devices[device_type]['default_port'])

    def set_device_com_port(self, device_type: DeviceType, com_port: str) -> None:
        """設置設備的 COM PORT"""
        self.device_com_ports[device_type] = com_port
        self._logger.info(f"Set {device_type.value} COM PORT to: {com_port}")

    # endregion