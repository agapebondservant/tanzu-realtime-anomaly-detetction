import threading

host = 'rabbitanalytics4.streamlit.svc.cluster.local'

dashboard_monitor = None

firehose = None
firehose_monitor = None
firehose_monitor_thread = None

dashboard_refresh_interval = 30
dashboard_refresh_window_size_in_minutes = 60
dashboard_queue = 'rabbitanalytics4-dashboard'

data_published_msg = 'DATA_PUBLISHED'
data_refresh_msg = 'DATA_REFRESH'
