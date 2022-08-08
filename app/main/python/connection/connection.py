import pika
import time
import datetime
import logging
import traceback
import threading
import json


class Connection(threading.Thread):

    def on_connected(self, conn):
        """Called when we are fully connected to RabbitMQ"""
        # Open a channel
        logging.info(f"In on_connected: {conn}")
        self._connection = conn
        self._connection.channel(on_open_callback=lambda ch: self.on_channel_open(ch))

    def on_channel_open(self):
        pass

    def on_connection_close(self, conn, error):
        logging.error(error)
        logging.error(conn)

    def on_connection_error(self, conn, error):
        try:
            logging.error(f'Error while attempting to connect...{conn} {error}')
            self.connect(self._connection)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    def init_connection(self):
        conn = pika.SelectConnection(self.parameters,
                                     on_open_callback=lambda con: self.on_connected(con),
                                     on_close_callback=lambda con, err: self.on_connection_close(con, err))
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

    # Connect to RabbitMQ using the default parameters
    def run(self):
        self._connection = self.init_connection()
        self.connect(self._connection)

    # Initialize class
    def __init__(self,
                 host=None):
        super(Connection, self).__init__()
        self._connection = None
        self.conn_retry_count = 0
