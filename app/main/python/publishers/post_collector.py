import pika
import logging
import json
from rabbitmq.connection import publisher
from app.main.python.utils import utils


class PostCollector(publisher.Publisher):

    def send_messages(self, _channel):
        """Called when our channel has opened"""
        if self.data is not None:

            self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', json.dumps(self.data),
                                       pika.BasicProperties(content_type='text/plain',
                                                            delivery_mode=pika.DeliveryMode.Persistent,
                                                            timestamp=self.data[0]))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None,
                 post=None,
                 sentiment='neutral'):
        super(PostCollector, self).__init__(host=host, data=data, exchange=exchange, routing_key=routing_key,
                                            send_callback=PostCollector.send_messages)
        self.data = [utils.datetime_as_offset(utils.get_current_datetime()),
                     utils.next_sequence_id(),
                     sentiment, 0.6771, None, 0.0, "American", None,
                     "johnydoe", None, 0,
                     post,
                     None, "Washington, DC", None]
