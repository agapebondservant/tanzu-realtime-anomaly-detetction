import pika
import time
import datetime
import logging
import traceback
import threading
import json
from datetime import datetime, timedelta
import pytz
from app.main.python.connection import publisher
from utils import utils


class PostCollector(publisher.Publisher):

    def on_channel_open(self, _channel):
        """Called when our channel has opened"""
        if self.data is not None:
            super().on_channel_open(_channel)

            self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', json.dumps(self.data),
                                       pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=pika.DeliveryMode.Persistent,
                                                            timestamp=self.data[0]))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None,
                 post=None,
                 sentiment='neutral'):
        super(PostCollector, self).__init__(host, data, exchange, routing_key)
        self.data = [utils.datetime_as_offset(utils.get_current_datetime()),
                     utils.next_sequence_id(),
                     sentiment, 0.6771, None, 0.0, "American", None,
                     "johnydoe", None, 0,
                     post,
                     None, "Washington, DC", None]
        logging.info(f"In post collector: data = {self.data}")
