# PRODUCER
import pika
import time
import datetime
import logging
import traceback
from app.main.python import csv_data
import threading
import json

base_connection = None


class FireHosePublisher(threading.Thread):

    #####################
    # Step #2
    #####################

    def on_connected(self, conn):
        """Called when we are fully connected to RabbitMQ"""
        # Open a channel
        logging.info("In on_connected")
        base_connection = conn
        base_connection.channel(on_open_callback=lambda ch: self.callback(self, ch))

    #####################
    # Step #3
    #####################

    def load_stream_data(self, new_channel):
        """Called when our channel has opened"""
        self.channel = new_channel
        df = csv_data.get_data()
        logging.info(df)
        for i in df.index:
            # msg = df.loc[i].to_json("row{}.json".format(i), orient="records")
            msg = df.loc[i].to_json(orient="records")
            # logging.info(f'Have another message: {msg}')
            self.channel.basic_publish('rabbitanalytics1-stream-exchange', 'anomalyall', json.dumps(msg),
                                       pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=pika.DeliveryMode.Persistent))

    def on_closed(self, connection, error):
        logging.error(error)
        logging.error(connection)

    def on_connection_error(self, connection, error):
        logging.error(f'Error while attempting to connect...{error} {connection}')

    #####################
    # Domain Methods
    #####################
    def run(self):
        base_connection = pika.SelectConnection(self.parameters,
                                                on_open_callback=lambda conn: self.on_connected(conn),
                                                on_close_callback=lambda conn, err: self.on_closed(conn, err))
        base_connection.add_on_open_error_callback(self.on_connection_error)

        try:
            # Loop so we can communicate with RabbitMQ
            # exit if number of connection retries exceeds a threshold
            self.conn_retry_count = self.conn_retry_count + 1
            if self.conn_retry_count > 10:
                raise KeyboardInterrupt
            base_connection.ioloop.start()
        except KeyboardInterrupt:
            # Gracefully close the connection
            base_connection.close()
            # Loop until we're fully closed, will stop on its own
            base_connection.ioloop.start()

    # Step #1: Connect to RabbitMQ using the default parameters

    def __init__(self, host=None, callback=load_stream_data):
        super(FireHosePublisher, self).__init__()
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.channel = None
        self.callback = callback
        self.conn_retry_count = 0
