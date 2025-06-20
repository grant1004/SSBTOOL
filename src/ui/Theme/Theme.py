from enum import Enum
from typing import Dict

from PySide6.QtCore import QObject, Signal


class ThemeType(Enum):
    DEFAULT = "default"
    INDUSTRIAL = "industrial"


class Theme:
    class Default:
        # Primary Colors
        PRIMARY = "#006C4D"
        PRIMARY_LIGHT = "#4CAF50"
        PRIMARY_DARK = "#005C41"

        # Background Colors
        BACKGROUND = "#DBE5DF"
        SURFACE = "#F5F5F5"
        SURFACE_VARIANT = "#FAFAFA"

        # Border Colors
        BORDER = "#000000"
        BORDER_LIGHT = "#EEEEEE"

        # Text Colors
        LINEEDIT_BACKGROUND = "#FFFFFF"
        TEXT_PRIMARY = "#333333"
        TEXT_SECONDARY = "#666666"
        TEXT_DISABLED = "#999999"
        TEXT_ON_PRIMARY = "#FFFFFF"

        # Status Colors
        SUCCESS = "#4CAF50"
        ERROR = "#F44336"
        WARNING = "#FFC107"
        OFFLINE = "#FF4444"

        # Overlay Colors
        OVERLAY = "rgba(0, 0, 0, 0.1)"
        HOVER = "rgba(0, 0, 0, 0.05)"

    class Industrial:
        # Primary Colors
        PRIMARY = "#FFA726"
        PRIMARY_LIGHT = "#FFB74D"
        PRIMARY_DARK = "#F57C00"

        # Background Colors
        BACKGROUND = "#1E1E1E"
        SURFACE = "#2D2D2D"
        SURFACE_VARIANT = "#323232"

        # Border Colors
        BORDER = "#000000"
        BORDER_LIGHT = "#505050"

        # Text Colors
        LINEEDIT_BACKGROUND = "#2D2D2D"
        TEXT_PRIMARY = "#E0E0E0"
        TEXT_SECONDARY = "#808080"
        TEXT_DISABLED = "#666666"
        TEXT_ON_PRIMARY = "#1E1E1E"

        # Status Colors
        SUCCESS = "#4CAF50"
        ERROR = "#F44336"
        WARNING = "#FFC107"
        OFFLINE = "#FF4444"

        # Overlay Colors
        OVERLAY = "rgba(255, 255, 255, 0.05)"
        HOVER = "rgba(255, 255, 255, 0.1)"


class ThemeManager(QObject):
    theme_changed = Signal()  # 添加信號

    def __init__(self):
        super().__init__()
        self._current_theme = ThemeType.DEFAULT
        self._themes = {
            ThemeType.DEFAULT: Theme.Default,
            ThemeType.INDUSTRIAL: Theme.Industrial
        }

    @property
    def current_theme(self) -> ThemeType:
        return self._current_theme

    # ThemeManager.py
    def switch_theme(self):
        # 直接在內部判斷並切換
        self._current_theme = ThemeType.DEFAULT if self._current_theme == ThemeType.INDUSTRIAL else ThemeType.INDUSTRIAL
        self._update_app_style()
        self.theme_changed.emit()  # 發送信號

    def get_style_sheet(self) -> str:
        theme = self._themes[self._current_theme]
        return f"""
        /* Global Styles */
        QWidget {{
            background-color: {theme.SURFACE};
            color: {theme.TEXT_PRIMARY};
            border-radius: 4px;
            margin: 0;
            padding: 0;
        }}
        
        QlineEdit {{
            background-color: {theme.LINEEDIT_BACKGROUND};}}

        QLabel {{
            background-color: Transparent;
            color: {theme.TEXT_PRIMARY};
        }}
        

        /* MainWindow */
        QMainWindow {{
            background-color: {theme.BACKGROUND};
            margin: 0;
            padding: 0;
        }}

        #central-widget {{
            background-color: {theme.BACKGROUND};
            margin: 0;
            padding: 0;
        }}

        /* MenuBar */
        QMenuBar {{
            background-color: {theme.SURFACE};
            border-bottom: 1px solid {theme.BORDER};
        }}

        /* StatusBar */
        QStatusBar {{
            background-color: {theme.PRIMARY};
            color: {theme.TEXT_ON_PRIMARY};
        }}

        /* Base Buttons */
        QPushButton {{
            background-color: #2D2D2D60;
            color: {theme.TEXT_ON_PRIMARY};
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
        }}

        QPushButton:hover {{
            background-color: #2D2D2DFF;
        }}

        QPushButton:pressed {{
            background-color: #5F5F5F;
        }}

        QPushButton:disabled {{
            background-color: {theme.TEXT_DISABLED};
            color: {theme.SURFACE};
        }}

        /* Base Tab */
        QTabWidget::pane {{
            border: 1px solid {theme.BORDER};
            background-color: {theme.SURFACE};
        }}

        QTabBar::tab {{
            background-color: {theme.SURFACE};
            color: {theme.TEXT_SECONDARY};
            padding: 8px 16px;
            border: none;
            border-bottom: 2px solid transparent;
        }}

        QTabBar::tab:selected {{
            color: {theme.PRIMARY};
            border-bottom: 2px solid {theme.PRIMARY};
        }}

        /* Base Card */
        #base-card {{
            background-color: {theme.SURFACE};
            border: 1px solid {theme.BORDER_LIGHT};
            border-radius: 8px;
            margin: 4px;
            padding: 12px;
        }}

        #base-card:hover {{
            border-color: {theme.PRIMARY};
            background-color: {theme.SURFACE_VARIANT};
        }}

        #base-card QLabel {{
            color: {theme.TEXT_PRIMARY};
        }}

        #base-card .title {{
            font-size: 14px;
            font-weight: bold;
            color: {theme.TEXT_PRIMARY};
        }}

        #base-card .description {{
            font-size: 12px;
            color: {theme.TEXT_SECONDARY};
        }}

        #base-card .keyword-tag {{
            background-color: {theme.PRIMARY}20;
            color: {theme.PRIMARY};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 11px;
        }}

        /* Search Bar */
        #search-container {{
            background-color: {theme.SURFACE_VARIANT};
            border: 1px solid {theme.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
        }}

        #search-container QLineEdit {{
            background-color: transparent;
            border: none;
            color: {theme.TEXT_PRIMARY};
            font-size: 14px;
        }}

        #search-container QLineEdit::placeholder {{
            color: {theme.TEXT_DISABLED};
        }}

        /* Switch Button */
        #switch-button {{
            background-color: {theme.SURFACE_VARIANT};
            border-radius: 20px;
            padding: 4px;
        }}

        #switch-button QPushButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border-radius: 16px;
            padding: 6px 12px;
        }}

        #switch-button QPushButton:checked {{
            background-color: {theme.PRIMARY};
            color: {theme.TEXT_ON_PRIMARY};
        }}

        /* Component Status Button */
        #component-status {{
            background-color: {theme.SURFACE_VARIANT};
            border-radius: 15px;
            padding: 4px 12px;
        }}

        #component-status .status-indicator {{
            width: 10px;
            height: 10px;
            border-radius: 5px;
        }}

        #component-status .status-indicator.online {{
            background-color: {theme.SUCCESS};
        }}

        #component-status .status-indicator.offline {{
            background-color: {theme.ERROR};
        }}

        /* Tabs Group */
        #tabs-container {{
            background-color: transparent;
        }}

        #tabs-container QPushButton {{
            text-align: left;
            padding: 12px;
            margin: 2px 0;
            border-radius: 4px;
            color: {theme.TEXT_SECONDARY};
        }}

        #tabs-container QPushButton:checked {{
            background-color: {theme.PRIMARY};
            color: {theme.TEXT_ON_PRIMARY};
        }}

        #tabs-container QPushButton:hover:!checked {{
            background-color: {theme.HOVER};
        }}

        /* ScrollArea and ScrollBar */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}

        QScrollBar:vertical {{
            background-color: {theme.SURFACE};
            width: 8px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {theme.BORDER};
            border-radius: 4px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {theme.PRIMARY};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}

        /* Test Case Priority Indicators */
        .priority-required {{
            background-color: {theme.ERROR}40;
            color: {theme.ERROR};
        }}

        .priority-standard {{
            background-color: {theme.PRIMARY}40;
            color: {theme.PRIMARY};
        }}

        .priority-optional {{
            background-color: {theme.WARNING}40;
            color: {theme.WARNING};
        }}

        /* List Widget Updates */
        QListWidget {{
            background-color: {theme.SURFACE};
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
        }}

        QListWidget::item {{
            padding: 8px;
            border-radius: 4px;
        }}

        QListWidget::item:selected {{
            background-color: {theme.OVERLAY};
            color: {theme.PRIMARY};
        }}

        QListWidget::item:hover {{
            background-color: {theme.HOVER};
        }}

        /* Line Edit Updates */
        QLineEdit {{
            background-color: {theme.SURFACE};
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
            padding: 8px;
        }}

        QLineEdit:focus {{
            border-color: {theme.PRIMARY};
        }}

        /* ComboBox Updates */
        QComboBox {{
            background-color: {theme.SURFACE};
            border: 1px solid {theme.BORDER};
            border-radius: 4px;
            padding: 8px;
        }}
        
        """

    def _update_app_style(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(self.get_style_sheet())

