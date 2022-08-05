# CONSUMER
# Needs cleanup!

import pika
import logging
import time
import traceback
import threading
import json

base_connection = None


class FireHoseSubscriber(threading.Thread):

    # Step 2

    def on_connected(self, conn):
        logging.info("In on_connected...")
        """Called when we are fully connected to RabbitMQ"""
        # Open a channel
        base_connection = conn
        base_connection.channel(on_open_callback=lambda ch: self.on_channel_open(ch))

    # Step #3

    def on_channel_open(self, new_channel):
        """Called when our channel has opened"""
        logging.info("In on_channel_open...")
        self.channel = new_channel
        self.channel.add_on_close_callback(lambda ch, err: self.on_channel_closed(ch, err))
        self.channel.queue_declare(queue=self.queue, durable=True,
                                   callback=lambda frame: self.on_queue_declared(frame),
                                   passive=True,
                                   arguments=self.queue_arguments)

    # Step #4

    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        logging.info("In on_queue_declared...")
        try:
            if not frame:
                logging.info("Queue should be predeclared")
            self.channel.basic_qos(prefetch_count=self.prefetch_count)
            self.channel.basic_consume(self.queue,
                                       on_message_callback=lambda ch, m, h, body: self.callback(self, ch, m, h, body),
                                       arguments=self.consumer_arguments,
                                       consumer_tag='firehose')
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    # Step #5

    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ"""
        logging.info(f"Received a message!...{json.loads(body)}")
        try:
            self.channel = channel
            self.channel.basic_ack(method.delivery_tag, False)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)

    def on_connection_error(self, conn, error):
        try:
            logging.error(f'Error while attempting to connect...{conn} {error}')
            self.connect(base_connection)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    def on_channel_closed(self, channel, error):
        try:
            logging.error(f'Error while attempting to connect...{error} {channel}')
            try:
                base_connection.close()
                time.sleep(1)
            except Exception as e:
                pass
            self.connect(base_connection)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    def connect(self, conn):
        try:
            # exit if number of connection retries exceeds a threshold
            self.conn_retry_count = self.conn_retry_count + 1
            if self.conn_retry_count > 10:
                raise KeyboardInterrupt
            # Loop so we can communicate with RabbitMQ
            conn.ioloop.start() if conn is not None else True
        except KeyboardInterrupt:
            logging.error('Keyboard Interrupt: ', exc_info=True)
            traceback.print_exc()
            # Gracefully close the connection
            conn.close()
            # Loop until we're fully closed, will stop on its own
            conn.ioloop.start()

    def init_connection(self):
        base_connection = pika.SelectConnection(self.parameters, on_open_callback=lambda conn: self.on_connected(conn))
        base_connection.add_on_open_error_callback(lambda conn, err: self.on_connection_error(conn, err))
        self.connect(base_connection)

    # Step #1: Connect to RabbitMQ using the default parameters
    def run(self):
        self.init_connection()

    # Step #0: Initialize class
    def __init__(self,
                 host=None,
                 callback=handle_delivery,
                 queue='rabbitanalytics1-stream',
                 queue_arguments={'x-queue-type': 'stream'},
                 consumer_arguments={'x-stream-offset': 0},
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(FireHoseSubscriber, self).__init__()
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.host = host
        self.callback = callback or self.handle_delivery
        self.queue = queue
        self.queue_arguments = queue_arguments
        self.consumer_arguments = consumer_arguments
        self.prefetch_count = prefetch_count
        self.conn_retry_count = conn_retry_count
        self.channel = None
