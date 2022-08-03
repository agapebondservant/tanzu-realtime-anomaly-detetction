# PRODUCER
import pika
import time
import datetime
import logging
import traceback
from app.main.python import csv_data
import threading


class FireHosePublisher(threading.Thread):
    # Step #1: Connect to RabbitMQ using the default parameters

    def __init__(self, host=None):
        threading.Thread.__init__(self)
        self.parameters = pika.ConnectionParameters(host=host,
                                               credentials=pika.PlainCredentials('data-user', 'data-password'))

    # Create a global channel variable to hold our channel object in
    # publisher_channel = None

    #####################
    # Step #2
    #####################

    def on_connected(self, connection):
        """Called when we are fully connected to RabbitMQ"""
        # Open a channel
        logging.info("In on_connected")
        connection.channel(on_open_callback=self.on_channel_open)

    #####################
    # Step #3
    #####################

    def on_channel_open(self, new_channel):
        """Called when our channel has opened"""
        #global publisher_channel
        self.publisher_channel = new_channel
        df = csv_data.get_data()
        for i in df.index:
            msg = df.loc[i].to_json("row{}.json".format(i), orient="records")
            msg = f'Have another message: {msg}'
            self.publisher_channel.basic_publish('rabbitanalytics1-stream-exchange', 'anomalyall', msg,
                                                 pika.BasicProperties(content_type='text/plain',
                                                                      delivery_mode=pika.DeliveryMode.Persistent))

    #####################
    # Step #4
    #####################

    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        self.publisher_channel.basic_consume('rabbitanalytics1-stream', self.handle_delivery)

    #####################
    # Step #5
    #####################

    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ"""
        logging.info(f"Received a message!...{body}")

    def on_closed(self, connection, error):
        logging.error(error)
        logging.error(connection)

    def on_connection_error(self, connection, error):
        logging.error(f'Error while attempting to connect...{error} {connection}')

    #####################
    # Domain Methods
    #####################
    def run(self):
        self.publisher_connection = pika.SelectConnection(self.parameters, on_open_callback=self.on_connected,
                                                          on_close_callback=self.on_closed)
        self.publisher_connection.add_on_open_error_callback(self.on_connection_error)

        try:
            # Loop so we can communicate with RabbitMQ
            self.publisher_connection.ioloop.start()
        except KeyboardInterrupt:
            # Gracefully close the connection
            self.publisher_connection.close()
            # Loop until we're fully closed, will stop on its own
            self.publisher_connection.ioloop.start()
