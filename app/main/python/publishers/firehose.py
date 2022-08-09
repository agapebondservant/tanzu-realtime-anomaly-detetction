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


class Firehose(publisher.Publisher):

    def on_channel_open(self, _channel):
        """Called when our channel has opened"""
        super().on_channel_open(_channel)

        if self.data is not None:
            orientation = 'records' if any(self.data.index.duplicated()) else 'index'
            for i in self.data.index:
                msg = self.data.loc[i].to_json(orient=orientation)
                self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', msg,
                                           pika.BasicProperties(content_type='text/plain',
                                                                delivery_mode=pika.DeliveryMode.Persistent,
                                                                timestamp=int(i.timestamp())))
            self.publish_random_data(self.data)

    def publish_random_data(self, data):
        # while True:
        orientation = 'records' if any(self.data.index.duplicated()) else 'index'
        lag_adjustment = pytz.utc.localize(datetime.now()) - data.index.min()
        new_data = data.copy()
        new_data.set_index(new_data.index + lag_adjustment, inplace=True)
        for i in new_data.index:
            msg = new_data.loc[i].to_json(orient=orientation)
            self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', msg,
                                       pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=pika.DeliveryMode.Persistent))

            # Publish notification to topic exchange that new data was published
            self.channel.basic_publish('rabbitanalytics4-exchange', 'anomaly.datapublished', msg,
                                       pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=pika.DeliveryMode.Persistent))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None):
        super(Firehose, self).__init__(host, data, exchange, routing_key)
