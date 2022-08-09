import pika
import time
import datetime
import logging
import traceback
import threading
import json
from datetime import datetime, timedelta
import pytz
from app.main.python.connection import subscriber


class FirehoseMonitor(subscriber.Subscriber):
    def __init__(self,
                 host,
                 process_delivery_callback,
                 queue,
                 queue_arguments,
                 consumer_arguments,
                 offset,
                 prefetch_count,
                 conn_retry_count):
        super(FirehoseMonitor, self).__init__(host, process_delivery_callback, queue,
                                              queue_arguments, consumer_arguments, offset, prefetch_count,
                                              conn_retry_count)

    def process_delivery(self, header, body):
        logging.info(f"Received a message!...{json.loads(body)}")
