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


class FirehoseMonitor(subscriber.Subscriber):
    def __init__(self,
                 host=None,
                 process_delivery_callback=None,
                 queue='rabbitanalytics4-stream',
                 queue_arguments={'x-queue-type': 'stream'},
                 consumer_arguments={},
                 offset=None,
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(FirehoseMonitor, self).__init__(host, process_delivery_callback, queue,
                                              queue_arguments, consumer_arguments, offset, prefetch_count,
                                              conn_retry_count)
        self.new_data = None

    def process_delivery(self, header, body):
        # Only start making updates to the dataset when the publisher is ready
        if header.timestamp > feature_store.load_offset('original'):
            # Get existing data
            old_data = csv_data.get_data()
            if old_data is None or old_data.empty:
                return

            # track new data
            if self.new_data is None:
                self.new_data = pd.DataFrame(data=[], columns=old_data.columns)
            self.new_data = utils.append_json_list_to_dataframe(self.new_data, json.loads(body))

            # Append new data to the dataset
            data = pd.concat([old_data, self.new_data])

            # update the feature store
            feature_store.save_artifact(data, '_data')

            logging.debug(f"new data looks like this: {data}")

            # Reset new_data
            self.new_data = None

            # publish a notification
            logging.info("sending message to notifier...")
            notify_publisher = notifier.Notifier(host=config.host, data=config.data_published_msg)
            notify_publisher.start()
