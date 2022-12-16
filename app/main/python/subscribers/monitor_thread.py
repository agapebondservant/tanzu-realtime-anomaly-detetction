import threading
# from streamlit.scriptrunner.script_run_context import get_script_run_ctx, add_script_run_ctx
from streamlit.runtime.scriptrunner import add_script_run_ctx
from app.main.python.utils import utils


threading.excepthook = utils.exception_handler


class MonitorThread(threading.Thread):
    def __init__(self,
                 interval=30,
                 monitor: threading.Thread = None,
                 monitor_args=()):
        super(MonitorThread, self).__init__(target=self.repeat, args=monitor_args)
        self.interval = interval
        self.monitor = monitor
        self.monitor_args = monitor_args
        add_script_run_ctx(self)
