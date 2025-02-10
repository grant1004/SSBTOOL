# controllers/window_controller.py
from PySide6.QtCore import QObject, Slot, Signal, Property

class RunWidgetController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

    def RunCommand(self):
        return self.model.run_command()

    def GenerateCommand(self):
        return self.model.generate_command()

    def ReportCommand(self):
        return self.model.report_command()

    def ImportCommand(self):
        return self.model.import_command()

    @Slot()  # 對於無參數的函數使用 @Slot()
    def addTestSuite(self):
        print("Add Test Suite clicked")

    @Slot()  # 對於有參數的函數指定參數類型
    def addTest(self):
        print(f"Add Test to suite")

    @Slot(str)
    def deleteTestSuite(self, suite_name):
        print(f"Delete suite: {suite_name}")