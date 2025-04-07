# src/utils/container.py
class Container:
    _instances = {}

    @classmethod
    def reset(cls):
        cls._instances = {}

    @classmethod
    def get_run_widget_model(cls):
        from src.models import RunWidget_Model
        if 'run_widget_model' not in cls._instances:
            cls._instances['run_widget_model'] = RunWidget_Model()
        return cls._instances['run_widget_model']

    @classmethod
    def get_run_widget_controller(cls):
        from src.controllers import RunWidgetController
        if 'run_widget_controller' not in cls._instances:
            cls._instances['run_widget_controller'] = RunWidgetController()
        return cls._instances['run_widget_controller']