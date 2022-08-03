# PRODUCER
import pika
import time
import datetime
import logging
import traceback

# Create a global channel variable to hold our channel object in
publisher_channel = None

#####################
# Step #2
#####################


def on_connected(connection):
    """Called when we are fully connected to RabbitMQ"""
    # Open a channel
    logging.info("In on_connected")
    connection.channel(on_open_callback=on_channel_open)

#####################
# Step #3
#####################


def on_channel_open(new_channel):
    """Called when our channel has opened"""
    global publisher_channel
    publisher_channel = new_channel
    t_end = time.time() + 10
    logging.info(t_end)
    while time.time() < t_end:
        msg = f'Have another message{time.time()}'
        logging.info(msg)
        publisher_channel.basic_publish('rabbitanalytics1-stream-exchange','anomalyall',msg,pika.BasicProperties(content_type='text/plain',delivery_mode=pika.DeliveryMode.Persistent))

#####################
# Step #4
#####################


def on_queue_declared(frame):
    """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
    publisher_channel.basic_consume('rabbitanalytics1-stream', handle_delivery)

#####################
# Step #5
#####################


def handle_delivery(channel, method, header, body):
    """Called when we receive a message from RabbitMQ"""
    logging.info(f"Received a message!...{body}")


def on_closed(connection, error):
    logging.error(error)
    logging.error(connection)


def on_connection_error(connection, error):
    logging.error(f'Error while attempting to connect...{error} {connection}')


# Step #1: Connect to RabbitMQ using the default parameters
def init_connection(host=None):
    parameters = pika.ConnectionParameters(host=host,credentials=pika.PlainCredentials('data-user', 'data-password'))
    publisher_connection = pika.SelectConnection(parameters, on_open_callback=on_connected, on_close_callback=on_closed)
    publisher_connection.add_on_open_error_callback(on_connection_error)

    try:
        # Loop so we can communicate with RabbitMQ
        publisher_connection.ioloop.start()
    except KeyboardInterrupt:
        # Gracefully close the connection
        publisher_connection.close()
        # Loop until we're fully closed, will stop on its own
        publisher_connection.ioloop.start()


#init_connection('rabbitanalytics1.streamlit.svc.cluster.local')