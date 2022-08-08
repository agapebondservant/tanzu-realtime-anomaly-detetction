import pika
import time
import datetime
import logging
import traceback
import threading
import json
from app.main.python.connection import connection


class Publisher(connection.Connection):

    def on_channel_open(self, new_channel):
        """Called when our channel has opened"""
        self.channel = new_channel
        # self.channel.add_on_close_callback(lambda ch, err: self.on_channel_closed(ch, err))
        logging.info(f"data type: {type(self.data)} {self.data}")

        if self.data is not None:
            orientation = 'records' if any(self.data.index.duplicated()) else 'index'
            for i in self.data.index:
                msg = self.data.loc[i].to_json(orient=orientation)
                # logging.info(f'Have another message: {msg}')
                self.channel.basic_publish(self.exchange, self.routing_key, json.dumps(msg),
                                           pika.BasicProperties(content_type='text/plain',
                                                                delivery_mode=pika.DeliveryMode.Persistent))

    def send_data(self, data_to_send):
        logging.info('In send_data...')
        self.data = data_to_send
        if self._connection is not None:
            self.on_connected(self._connection)

    def __init__(self,
                 host=None,
                 data=None,
                 exchange='rabbitanalytics1-stream-exchange',
                 routing_key='anomalyall'):
        super(Publisher, self).__init__()
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.channel = None
        self.conn_retry_count = 0
        self.data = data
        self.exchange = exchange
        self.routing_key = routing_key
        self._connection = None
