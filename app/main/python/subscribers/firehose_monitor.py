import logging
import json
import os
import ray
ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ), 'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import pandas as pd
from rabbitmq.connection import subscriber
from app.main.python.publishers import notifier
from app.main.python import csv_data_source, feature_store, config
from app.main.python.utils import utils


class FirehoseMonitor(subscriber.Subscriber):
    def __init__(self,
                 host=None,
                 queue='rabbitanalytics4-stream',
                 queue_arguments={'x-queue-type': 'stream'},
                 consumer_arguments={},
                 offset=None,
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(FirehoseMonitor, self).__init__(host=host, queue=queue,
                                              queue_arguments=queue_arguments, consumer_arguments=consumer_arguments,
                                              offset=offset, prefetch_count=prefetch_count,
                                              conn_retry_count=conn_retry_count,
                                              receive_callback=FirehoseMonitor.receive_messages)
        self.new_data = None

    def receive_messages(self, header, body):
        # Only start making updates to the dataset when the publisher is ready
        if header.timestamp > feature_store.load_offset('original', distributed=False):

            # track new data
            if self.new_data is None:
                self.new_data = pd.DataFrame(data=[], columns=csv_data_source.get_data_schema())
            self.new_data = utils.append_json_list_to_dataframe(self.new_data, json.loads(body))

            # update the feature store by appending the new data to the existing dataset
            csv_data_source.add_data(self.new_data)

            # Reset new_data
            self.new_data = None

            # publish a notification
            logging.info("sending message to notifier...")
            notify_publisher = notifier.Notifier(host=config.host, data=config.data_published_msg)
            notify_publisher.start()
