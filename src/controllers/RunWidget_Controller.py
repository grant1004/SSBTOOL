# controllers/window_controller.py
from PySide6.QtCore import QObject, Slot, Signal, Property
from src.utils import singleton, Container

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
        self.model.test_finished.connect(self.view.update_test_status)

    def RunCommand(self):
        testcase = self.view.test_cases
        Name_text = self.view.get_name_text()
        self.view.reset_test()
        return self.model.run_command( testcase, Name_text )

    def GenerateCommand(self):
        return self.model.generate_command()

    def ReportCommand(self):
        return self.model.report_command()

    def ImportCommand(self):
        return self.model.import_command()

