# src/ui/components/ExportDialog.py
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class ExportDialog(QDialog):
    """Export 測試案例對話框"""

    # 預設的分類選項，可以輕鬆擴充
    DEFAULT_CATEGORIES = [
        "common",
        "battery",
        "hmi",
        "motor",
        "controller"
    ]

    # 優先級選項和對應顏色
    PRIORITY_OPTIONS = [
        {"name": "required", "text": "Required", "color": "#FF3D00"},
        {"name": "normal", "text": "Normal", "color": "#0099FF"},
        {"name": "optional", "text": "Optional", "color": "#4CAF50"}
    ]

    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.result_data = None
        self.priority_buttons = {}
        self.priority_button_group = QButtonGroup(self)

        self._setup_ui()
        self._setup_connections()
        # self._apply_default_style()
        self._apply_theme()

        # 設置預設值
        self._set_default_values()

    def _setup_ui(self):
        """設置 UI"""
        self.setWindowTitle("Export Configuration")
        self.setFixedSize(600, 550)  # 再增加一點高度以確保所有內容都能顯示
        self.setModal(True)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20,20,20,20)  # 增加左右邊距
        main_layout.setSpacing(0)  # 增加間距

        # 標題
        title_label = QLabel("📄 Export Test Case Configuration")
        title_label.setObjectName("dialog-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 表單區域
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(10,10,10,10)

        # Test Case Name
        name_section = self._create_form_section("Test Case Name")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter test case name...")
        self.name_input.setFixedHeight(44)  # 增加高度
        self.name_input.setMinimumWidth(400)  # 設定最小寬度
        name_section.layout().addWidget(self.name_input)
        form_layout.addWidget(name_section)

        # Category
        category_section = self._create_form_section("Category")
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.DEFAULT_CATEGORIES)
        self.category_combo.setFixedHeight(44)  # 增加高度
        self.category_combo.setMinimumWidth(400)  # 設定最小寬度
        category_section.layout().addWidget(self.category_combo)
        form_layout.addWidget(category_section)

        # Description
        description_section = self._create_form_section("Description")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter description (optional)...")
        self.description_input.setFixedHeight(100)  # 增加高度
        self.description_input.setMinimumWidth(400)  # 設定最小寬度
        description_section.layout().addWidget(self.description_input)
        form_layout.addWidget(description_section)

        # Priority - 使用 Radio Button
        priority_container = QWidget()
        priority_layout = QHBoxLayout(priority_container)
        priority_layout.setContentsMargins(0, 0, 0, 0)
        priority_layout.setSpacing(20)  # 增加按鈕間距

        for i, priority in enumerate(self.PRIORITY_OPTIONS):
            radio_btn = QRadioButton(priority["text"])
            radio_btn.setFixedHeight(40)  # 增加高度
            radio_btn.setMinimumWidth(100)  # 設定最小寬度
            radio_btn.setObjectName(f"priority-{priority['name']}")
            radio_btn.toggled.connect(lambda checked, p=priority: self._on_priority_changed(checked, p))

            self.priority_buttons[priority["name"]] = radio_btn
            self.priority_button_group.addButton(radio_btn, i)
            priority_layout.addWidget(radio_btn)

        priority_layout.addStretch()
        form_layout.addWidget(priority_container, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(form_widget)

        # 按鈕區域
        button_widget = QWidget()
        button_widget.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_widget)

        # 取消按鈕
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedHeight(44)  # 增加高度
        self.cancel_button.setMinimumWidth(120)  # 設定最小寬度
        self.cancel_button.setObjectName("cancel-button")
        self.cancel_button.setStyleSheet("background-color: transparent;")

        # 確認按鈕
        self.confirm_button = QPushButton("Export")
        self.confirm_button.setFixedHeight(44)  # 增加高度
        self.confirm_button.setMinimumWidth(120)  # 設定最小寬度
        self.confirm_button.setObjectName("confirm-button")
        self.confirm_button.setStyleSheet("background-color: #006C4D;")
        self.confirm_button.setDefault(True)  # 設為預設按鈕

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)

        main_layout.addWidget(button_widget, alignment=Qt.AlignmentFlag.AlignCenter)

    def _create_form_section(self, title):
        """創建表單區段"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # 調整標籤和輸入框間的間距

        # 標籤
        label = QLabel(title)
        label.setObjectName("form-label")
        layout.addWidget(label)

        return section

    def _setup_connections(self):
        """設置信號連接"""
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self._on_confirm)

        # Enter 鍵確認
        self.name_input.returnPressed.connect(self._on_confirm)

    def _set_default_values(self):
        """設置預設值"""
        self.name_input.setText("Untitled")
        self.category_combo.setCurrentText("common")
        # 設置預設優先級為 normal
        self.priority_buttons["normal"].setChecked(True)
        self._update_priority_style("normal")

    def _on_priority_changed(self, checked, priority_data):
        """處理優先級 Radio Button 變化"""
        if checked:
            self._update_priority_style(priority_data["name"])

    def _update_priority_style(self, selected_priority):
        """更新優先級按鈕樣式"""
        for priority in self.PRIORITY_OPTIONS:
            button = self.priority_buttons[priority["name"]]
            if priority["name"] == selected_priority:
                # 選中狀態 - 使用對應顏色背景
                button.setStyleSheet(f"""
                    QRadioButton {{
                        background-color: {priority["color"]};
                        color: white;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 600;
                        font-size: 14px;
                        min-width: 80px;
                    }}
                    QRadioButton::indicator {{
                        width: 0px;
                        height: 0px;
                    }}
                """)
            else:
                # 未選中狀態 - 透明背景，使用對應顏色邊框
                if self.theme_manager:
                    current_theme = self.theme_manager._themes[self.theme_manager._current_theme]
                    text_color = current_theme.TEXT_PRIMARY
                    bg_color = current_theme.SURFACE
                else:
                    text_color = "#333333"
                    bg_color = "#FFFFFF"

                button.setStyleSheet(f"""
                    QRadioButton {{
                        background-color: {bg_color};
                        color: {text_color};
                        border: 2px solid {priority["color"]};
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 500;
                        font-size: 14px;
                        min-width: 80px;
                    }}
                    QRadioButton:hover {{
                        background-color: {self._get_alpha_color(priority["color"], "4C")};
                    }}
                    QRadioButton::indicator {{
                        width: 0px;
                        height: 0px;
                    }}
                """)

    def _get_alpha_color(self, hex_color, alpha_hex):
        """將十六進制顏色添加透明度 (Qt 格式: #AARRGGBB)"""
        color_without_hash = hex_color[1:] if hex_color.startswith('#') else hex_color
        return f"#{alpha_hex}{color_without_hash}"


    def _on_confirm(self):
        """確認按鈕處理"""
        # 獲取選中的優先級
        selected_priority = "normal"  # 預設值
        for priority_name, button in self.priority_buttons.items():
            if button.isChecked():
                selected_priority = priority_name
                break

        # 收集表單數據
        self.result_data = {
            'name': self.name_input.text().strip() or "Untitled",
            'category': self.category_combo.currentText().strip() or "common",
            'description': self.description_input.toPlainText().strip(),
            'priority': selected_priority
        }

        self.accept()

    def get_export_data(self):
        """獲取 export 數據"""
        return self.result_data

    def _apply_theme(self):
        """應用主題樣式"""
        if not self.theme_manager:
            self._apply_default_style()
            return

        current_theme = self.theme_manager._themes[self.theme_manager._current_theme]

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {current_theme.BACKGROUND};
                color: {current_theme.TEXT_PRIMARY};
            }}

            #dialog-title {{
                font-size: 22px;
                font-weight: bold;
                color: {current_theme.PRIMARY};
                padding: 16px 0;
                letter-spacing: 0.5px;
            }}

            #form-label {{
                color: {current_theme.TEXT_PRIMARY};
                font-size: 15px;
                font-weight: 600;
                margin-bottom: 8px;
                padding-left: 2px;
            }}

            QLineEdit {{
                background-color: {current_theme.LINEEDIT_BACKGROUND};
                border: 1px solid {current_theme.BORDER};
                border-radius: 6px;
                padding: 0px 14px;
                font-size: 14px;
                color: {current_theme.TEXT_PRIMARY};
            }}

            QLineEdit:focus {{
                border-color: {current_theme.PRIMARY};
                border-width: 2px;
            }}

            QTextEdit {{
                background-color: {current_theme.LINEEDIT_BACKGROUND};
                border: 1px solid {current_theme.BORDER};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 14px;
                color: {current_theme.TEXT_PRIMARY};
            }}

            QTextEdit:focus {{
                border-color: {current_theme.PRIMARY};
                border-width: 2px;
            }}

            QComboBox {{
                background-color: {current_theme.LINEEDIT_BACKGROUND};
                border: 1px solid {current_theme.BORDER};
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 14px;
                color: {current_theme.TEXT_PRIMARY};
            }}

            QComboBox:focus {{
                border-color: {current_theme.PRIMARY};
                border-width: 2px;
            }}

            QComboBox::drop-down {{
                border: none;
                width: 25px;
            }}

            QComboBox::down-arrow {{
                width: 14px;
                height: 14px;
                margin-right: 10px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {current_theme.SURFACE};
                border: 1px solid {current_theme.BORDER};
                selection-background-color: {current_theme.PRIMARY};
                selection-color: {current_theme.TEXT_ON_PRIMARY};
                padding: 4px;
            }}
            

            #cancel-button {{
                background-color: #FFFFFF;
                color: #222222;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}

            #cancel-button:hover {{
                background-color: #F8F9FA;
                color: #333333;
                border-color: #006C4D;
            }}

            #confirm-button {{
                background-color: {current_theme.PRIMARY};
                color: {current_theme.TEXT_ON_PRIMARY};
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}

            #confirm-button:hover {{
                background-color: {current_theme.PRIMARY_DARK};
            }}

            #confirm-button:pressed {{
                background-color: {current_theme.PRIMARY_DARK};
            }}
            
        """)

    def _apply_default_style(self):
        """應用預設樣式（當沒有主題管理器時）"""
        self.setStyleSheet("""
            QDialog {
                background-color: #F5F5F5;
                color: #333333;
            }

            #dialog-title {
                font-size: 22px;
                font-weight: bold;
                color: #006C4D;
                padding: 16px 0;
                letter-spacing: 0.5px;
            }

            #form-label {
                color: #333333;
                font-size: 15px;
                font-weight: 600;
                margin-bottom: 8px;
                padding-left: 2px;
            }

            QLineEdit, QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 14px;
                color: #333333;
            }

            QLineEdit:focus, QTextEdit:focus {
                border-color: #006C4D;
                border-width: 2px;
            }

            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 14px;
                color: #333333;
            }

            QComboBox:focus {
                border-color: #006C4D;
                border-width: 2px;
            }

            #cancel-button {
                background-color: #FFFFFF;
                color: #666666;
                border: 2px solid #DDDDDD;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }

            #cancel-button:hover {
                background-color: #F8F9FA;
                color: #333333;
                border-color: #006C4D;
            }

            #confirm-button {
                background-color: #006C4D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }

            #confirm-button:hover {
                background-color: #005C41;
            }
        """)

    @staticmethod
    def show_export_dialog(theme_manager=None, parent=None):
        """靜態方法：顯示 export 對話框並返回結果"""
        dialog = ExportDialog(theme_manager, parent)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_export_data()
        else:
            return None