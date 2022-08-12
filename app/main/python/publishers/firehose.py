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


class Firehose(publisher.Publisher):

    def on_channel_open(self, _channel):
        """Called when our channel has opened"""
        super().on_channel_open(_channel)

        if self.data is not None:
            for i, row in self.data.iterrows():
                msg = utils.dataframe_record_as_json_string(row, i, 'records')
                self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', msg,
                                           pika.BasicProperties(content_type='text/plain',
                                                                delivery_mode=pika.DeliveryMode.Persistent,
                                                                timestamp=utils.datetime_as_offset(i)))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None):
        super(Firehose, self).__init__(host, data, exchange, routing_key)
