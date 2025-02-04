# controllers/window_controller.py
class RunWidgetController:
    def __init__(self, model, view):
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