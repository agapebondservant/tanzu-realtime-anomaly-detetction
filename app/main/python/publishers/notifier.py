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


class Notifier(publisher.Publisher):

    def on_channel_open(self, _channel):
        """Called when our channel has opened"""
        super().on_channel_open(_channel)

        # Publish notification to topic exchange that new data was published
        self.channel.basic_publish(self.exchange, self.routing_key, self.data,
                                   pika.BasicProperties(content_type='text/plain',
                                                        delivery_mode=pika.DeliveryMode.Persistent))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange='rabbitanalytics4-exchange',
                 routing_key='anomaly.datapublished'):
        super(Notifier, self).__init__(host, data, exchange, routing_key)
