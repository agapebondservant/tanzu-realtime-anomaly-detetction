import threading
from app.main.python import feature_store


class MonitorThread(threading.Timer):
    def __init__(self,
                 interval=30,
                 monitor: threading.Thread = None,
                 monitor_args=None,
                 offset=None,
                 offset_name='firehose_monitor'):
        super(MonitorThread, self).__init__(interval, monitor.start, monitor_args)
        self.offset = offset
        self.offset_name = offset_name
        feature_store.save_offset(self.offset, self.offset_name)

