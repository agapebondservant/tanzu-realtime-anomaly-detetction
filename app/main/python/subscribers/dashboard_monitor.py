import pika
import time
import datetime
import logging
import traceback
import threading
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
from app.main.python.connection import subscriber
from app.main.python.publishers import notifier
from app.main.python import csv_data, feature_store, config
from app.main.python.utils import utils
from app.main.python import dashboard_widgets


class DashboardMonitor(subscriber.Subscriber):
    def __init__(self,
                 host=None,
                 process_delivery_callback=None,
                 queue='rabbitanalytics4-dashboard',
                 queue_arguments={},
                 consumer_arguments={},
                 offset=0,
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(DashboardMonitor, self).__init__(host, process_delivery_callback, queue,
                                               queue_arguments, consumer_arguments, offset, prefetch_count,
                                               conn_retry_count)

    def process_delivery(self, header, body):
        logging.info("Refreshing dashboard................................")
        dashboard_widgets.render_trends_dashboard('day')
