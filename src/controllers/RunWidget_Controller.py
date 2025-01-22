# controllers/window_controller.py
class RunWidgetController:
    def __init__(self, main_window):
        self.main_window = main_window

    def RunCommand(self):
        print( "Click Run Command")

    def GenerateCommand(self):
        print( "Click Generate Command")

    def ReportCommand(self):
        print( "Click Report Command")