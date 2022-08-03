# CONSUMER
# Needs cleanup!

import pika
import logging
import time
import traceback

# Create a global channel variable to hold our channel object in
subscriber_channel = None

# Initialize other variables
prefetch_count = 1000


# Step #2


def on_connected(subscriber_connection):
    logging.info("In on_connected...")
    """Called when we are fully connected to RabbitMQ"""
    # Open a channel
    subscriber_connection.channel(on_open_callback=on_channel_open)


# Step #3


def on_channel_open(new_channel):
    """Called when our channel has opened"""
    logging.info("In on_channel_open...")
    global subscriber_channel
    subscriber_channel = new_channel
    subscriber_channel.add_on_close_callback(on_channel_closed)
    subscriber_channel.queue_declare(queue="rabbitanalytics1-stream", durable=True, callback=on_queue_declared, passive=True,
                          arguments={'x-queue-type': 'stream'})


# Step #4


def on_queue_declared(frame):
    """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
    logging.info("In on_queue_declared...")
    try:
        if not frame:
            logging.info("Queue should be predeclared")
        subscriber_channel.basic_qos(prefetch_count=prefetch_count)
        subscriber_channel.basic_consume('rabbitanalytics1-stream', on_message_callback=handle_delivery,
                              arguments={'x-stream-offset': 10000}, consumer_tag='firehose')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


# Step #5


def handle_delivery(subscriber_channel, method, header, body):
    """Called when we receive a message from RabbitMQ"""
    logging.info(f"Received a message!...{body}")
    try:
        subscriber_channel.basic_ack(method.delivery_tag, False)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)


def on_connection_error(subscriber_connection, error):
    try:
        logging.error(f'Error while attempting to connect...{subscriber_connection} {error}')
        parameters = pika.ConnectionParameters(host='rabbitanalytics1.data-samples-w03-s001.svc.cluster.local',
                                               credentials=pika.PlainCredentials('data-user', 'data-password'))
        subscriber_connection = pika.SelectConnection(parameters, on_open_callback=on_connected)
        subscriber_connection.add_on_open_error_callback(on_connection_error)
        reloop(subscriber_connection)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def on_channel_closed(subscriber_channel, error):
    try:
        logging.error(f'Error while attempting to connect...{error} {subscriber_channel}')
        parameters = pika.ConnectionParameters(host='rabbitanalytics1.data-samples-w03-s001.svc.cluster.local',
                                               credentials=pika.PlainCredentials('data-user', 'data-password'))
        global subscriber_connection
        if subscriber_connection is not None:
            subscriber_connection.close()
            time.sleep(1)
        subscriber_connection = pika.SelectConnection(parameters, on_open_callback=on_connected)
        subscriber_connection.add_on_open_error_callback(on_connection_error)
        reloop(subscriber_connection)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def reloop(subscriber_connection):
    try:
        # Loop so we can communicate with RabbitMQ
        subscriber_connection.ioloop.start()
    except KeyboardInterrupt:
        logging.error('Keyboard Interrupt: ', exc_info=True)
        traceback.print_exc()
        # Gracefully close the subscriber_connection
        subscriber_connection.close()
        # Loop until we're fully closed, will stop on its own
        subscriber_connection.ioloop.start()


# Step #1: Connect to RabbitMQ using the default parameters

def init_connection(host=None):
    parameters = pika.ConnectionParameters(host=host,
                                           credentials=pika.PlainCredentials('data-user', 'data-password'))
    subscriber_connection = pika.SelectConnection(parameters, on_open_callback=on_connected)
    subscriber_connection.add_on_open_error_callback(on_connection_error)
    try:
        # Loop so we can communicate with RabbitMQ
        subscriber_connection.ioloop.start()
    except KeyboardInterrupt as e:
        logging.error('Keyboard Interrupt: ', exc_info=True)
        traceback.print_exc()
        # Gracefully close the subscriber_connection
        subscriber_connection.close()
        # Loop until we're fully closed, will stop on its own
        subscriber_connection.ioloop.start()

