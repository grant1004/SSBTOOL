# controllers/RunWidget_Controller.py - 更新版本
from PySide6.QtCore import QObject, Slot, Signal, Property
from src.utils import singleton, Container
from src.ui.components import ExportDialog


@singleton
class RunWidgetController(QObject):
    def __init__(self):
        super().__init__()
        self.model = Container.get_run_widget_model()
        self.view = None
        # 連接 model 信號到 view 的更新方法

    def set_view(self, view):
        # 提供方法來設置 view
        self.view = view
        self.model.test_progress.connect(self.view.update_progress)
        self.model.test_finished.connect(self.view.test_finished)

    def RunCommand(self):
        testcase = self.view.test_cases
        Name_text = self.view.get_name_text()
        self.view.reset_test()
        return self.model.run_command(testcase, Name_text)

    def GenerateCommand(self):
        """顯示 Export 對話框並處理 generate command"""
        # 導入對話框（延遲導入避免循環依賴）

        # 獲取主視窗和主題管理器
        main_window = self._get_main_window()
        theme_manager = getattr(main_window, 'theme_manager', None) if main_window else None

        # 顯示對話框
        export_data = ExportDialog.show_export_dialog(theme_manager, main_window)

        if export_data:
            # 用戶確認了，執行 generate command
            testcase = self.view.test_cases
            name_text = export_data['name']
            category = export_data['category']
            priority = export_data['priority']
            description = export_data['description']

            print(f"Exporting test case: {name_text}")
            print(f"Category: {category}, Priority: {priority}")
            print(f"Description: {export_data['description']}")

            return self.model.generate_command(testcase, name_text, category, priority, description)
        else:
            # 用戶取消了
            print("Export cancelled by user")
            return None

    def _get_main_window(self):
        """獲取主視窗"""
        if not self.view:
            return None

        # 向上遍歷查找主視窗
        parent = self.view.parent()
        while parent:
            if hasattr(parent, 'theme_manager'):
                return parent
            parent = parent.parent()
        return None

    def ReportCommand(self):
        return self.model.report_command()

    def ImportCommand(self):
        return self.model.import_command()