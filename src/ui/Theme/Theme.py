class Theme:
    # 定義主題顏色
    PRIMARY_COLOR = "#FFA726"
    BACKGROUND_COLOR = "#1E1E1E"
    SECONDARY_BACKGROUND = "#2D2D2D"
    BORDER_COLOR = "#404040"
    TEXT_COLOR = "#E0E0E0"
    SECONDARY_TEXT = "#808080"

    # 生成全局樣式表
    @classmethod
    def get_style_sheet(cls):
        return f"""
        /* 全局變數 */
        * {{
            background-color: {cls.BACKGROUND_COLOR};
            color: {cls.TEXT_COLOR};
        }}

        QMainWindow {{
            background-color: {cls.BACKGROUND_COLOR};
        }}

        /* 按鈕樣式 */
        QPushButton {{
            background-color: {cls.PRIMARY_COLOR};
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            color: {cls.BACKGROUND_COLOR};
        }}

        QPushButton:hover {{
            background-color: {cls.PRIMARY_COLOR}CC;  /* 80% 透明度 */
        }}

        /* 標籤頁樣式 */
        QTabWidget::pane {{
            border: 1px solid {cls.BORDER_COLOR};
            background-color: {cls.SECONDARY_BACKGROUND};
        }}

        QTabBar::tab {{
            background-color: {cls.SECONDARY_BACKGROUND};
            color: {cls.SECONDARY_TEXT};
            padding: 8px 16px;
            border: none;
        }}

        QTabBar::tab:selected {{
            color: {cls.PRIMARY_COLOR};
            border-bottom: 2px solid {cls.PRIMARY_COLOR};
        }}

        /* 列表樣式 */
        QListWidget {{
            background-color: {cls.SECONDARY_BACKGROUND};
            border: 1px solid {cls.BORDER_COLOR};
            border-radius: 4px;
        }}

        QListWidget::item {{
            padding: 8px;
        }}

        QListWidget::item:selected {{
            background-color: {cls.PRIMARY_COLOR}33;  /* 20% 透明度 */
            color: {cls.PRIMARY_COLOR};
        }}
        """
