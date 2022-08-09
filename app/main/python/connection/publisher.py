import pika
import time
import datetime
import logging
import traceback
import threading
import json
from app.main.python.connection import connection


class Publisher(connection.Connection):

    def send_data(self, data_to_send):
        logging.info('In send_data...')
        self.data = data_to_send
        if self._connection is not None:
            self.on_connected(self._connection)

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None):
        super(Publisher, self).__init__()
        self.host = host
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.channel = None
        self.conn_retry_count = 0
        self.data = data
        self.exchange = exchange
        self.routing_key = routing_key
        self._connection = None
