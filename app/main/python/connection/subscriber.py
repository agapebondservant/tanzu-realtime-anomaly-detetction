import pika
import time
import datetime
import logging
import traceback
import threading
import json
from app.main.python.connection import connection


class Subscriber(connection.Connection):

    def read_data(self, offset=0):
        if self.queue_arguments.get('x-queue-type') == 'stream':
            self.consumer_arguments['x-stream-offset'] = offset
        if self._connection is not None:
            self.on_connected(self, self._connection)

    def on_channel_open(self, new_channel):
        """Called when our channel has opened"""
        logging.info("In on_channel_open...")
        self.channel = new_channel
        self.channel.add_on_close_callback(lambda ch, err: self.on_channel_closed(ch, err))
        self.channel.queue_declare(queue=self.queue, durable=True,
                                   callback=lambda frame: self.on_queue_declared(frame),
                                   passive=True,
                                   arguments=self.queue_arguments)

    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        logging.info("In on_queue_declared...")
        try:
            if not frame:
                logging.info("Queue should be predeclared")
            self.channel.basic_qos(prefetch_count=self.prefetch_count)
            self.channel.basic_consume(self.queue,
                                       on_message_callback=lambda ch, m, h, body: self.handle_delivery(ch, m, h, body),
                                       arguments=self.consumer_arguments)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()

    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ"""
        try:
            self.process_delivery_callback(header, body)
            self.channel = channel
            self.channel.basic_ack(method.delivery_tag, False)
        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)

    def process_delivery(self, header, body):
        logging.info(f"Received a message!...{json.loads(body)}")

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

    def __init__(self,
                 host=None,
                 process_delivery_callback=None,
                 queue='rabbitanalytics1-stream',
                 queue_arguments={'x-queue-type': 'stream'},
                 consumer_arguments={},
                 offset=0,
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(Subscriber, self).__init__()
        self.parameters = pika.ConnectionParameters(host=host,
                                                    credentials=pika.PlainCredentials('data-user', 'data-password'))
        self.host = host
        self.process_delivery_callback = process_delivery_callback or self.process_delivery
        self.queue = queue
        self.queue_arguments = queue_arguments
        self.consumer_arguments = consumer_arguments
        self.offset = offset
        self.consumer_arguments['x-stream-offset'] = offset
        self.prefetch_count = prefetch_count
        self.conn_retry_count = conn_retry_count
        self.channel = None
        self._connection = None