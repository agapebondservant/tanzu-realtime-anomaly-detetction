# PRODUCER
import pika
import time
import datetime
import logging
import traceback
import threading
import json


class FireHosePublisher(threading.Thread):

    #####################
    # Step #2
    #####################

    def on_connected(self, conn):
        """Called when we are fully connected to RabbitMQ"""
        # Open a channel
        logging.info(f"In on_connected: {conn} {self.data}")
        self._connection = conn
        if self.data is not None:
            self._connection.channel(on_open_callback=lambda ch: self.load_stream_data(ch))

    #####################
    # Step #3
    #####################

    def load_stream_data(self, new_channel):
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

    def on_closed(self, connection, error):
        logging.error(error)
        logging.error(connection)

    def on_connection_error(self, connection, error):
        logging.error(f'Error while attempting to connect...{error} {connection}')

    def on_channel_closed(self, channel, error):
        try:
            logging.error(f'Error while attempting to connect...{error} {channel}')
            try:
                self._connection.close() if self._connection.is_closing or self._connection.is_closed else True
                time.sleep(1)
            except Exception as e:
                pass

            # reconnect
            self._connection = self.init_connection()
            self.connect(self._connection)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    #####################
    # Domain Methods
    #####################
    def run(self):
        self._connection = self.init_connection()
        self.connect(self._connection)

    def send_data(self, data_to_send):
        logging.info('In send_data...')
        self.data = data_to_send
        if self._connection is not None:
            self.on_connected(self._connection)

    def init_connection(self):
        conn = pika.SelectConnection(self.parameters,
                                                on_open_callback=lambda conn: self.on_connected(conn),
                                                on_close_callback=lambda conn, err: self.on_closed(conn, err))
        conn.add_on_open_error_callback(self.on_connection_error)
        return conn

    def connect(self, conn):
        try:
            # Loop so we can communicate with RabbitMQ
            # exit if number of connection retries exceeds a threshold
            self.conn_retry_count = self.conn_retry_count + 1
            if self.conn_retry_count > 10:
                raise KeyboardInterrupt
            self._connection.ioloop.start()
        except KeyboardInterrupt:
            # Gracefully close the connection
            self._connection.close()
            # Loop until we're fully closed, will stop on its own
            self._connection.ioloop.start()

    # Step #1: Connect to RabbitMQ using the default parameters

    def __init__(self,
                 host=None,
                 data=None,
                 exchange='rabbitanalytics1-stream-exchange',
                 routing_key='anomalyall'):
        super(FireHosePublisher, self).__init__()
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.channel = None
        self.conn_retry_count = 0
        self.data = data
        self.exchange = exchange
        self.routing_key = routing_key
        self._connection = None
