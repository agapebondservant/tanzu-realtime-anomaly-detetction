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
                 prefetch_count=100,
                 conn_retry_count=0):
        super(FirehoseMonitor, self).__init__(host, process_delivery_callback, queue,
                                              queue_arguments, consumer_arguments, offset, prefetch_count,
                                              conn_retry_count)
        self.new_data = None
        self.offset = feature_store.load_offset('firehose_monitor') or feature_store.load_offset('original') or 0

    def process_delivery(self, header, body):
        # Only make updates to the dataset when a processing offset has been initialized
        logging.info(f"in process_delivery: the current offset is {self.offset}")
        if self.offset > 0:
            # Get existing data
            old_data = csv_data.get_data()
            if old_data is None or old_data.empty:
                return

            # track new data
            if self.new_data is None:
                self.new_data = pd.DataFrame(data=[], columns=old_data.columns)
            self.new_data = utils.append_json_list_to_dataframe(self.new_data, json.loads(body))

            # if len(self.new_data) >= self.prefetch_count:
            # Drop all overflow records from the dataset
            data = pd.concat([old_data[len(self.new_data):], self.new_data])
            # data.index = utils.index_as_datetime(data)

            # update the feature store
            feature_store.save_artifact(data, '_data')

            # Save the new offset
            self.offset = utils.datetime_as_offset(data.index.max())
            # int(data.index.max().timestamp())
            feature_store.save_offset('firehose_monitor', self.offset)

        # publish a notification
        logging.info("sending message to notifier...")
        notify_publisher = notifier.Notifier(host=config.host, data=config.data_published_msg)
        notify_publisher.start()

        # Reset new_data
        self.new_data = None
