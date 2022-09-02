import pika
from rabbitmq.connection import publisher
from app.main.python.utils import utils


class Firehose(publisher.Publisher):

    def send_messages(self, _channel):
        """Called when our channel has opened"""

        if self.data is not None:
            for i, row in self.data.iterrows():
                msg = utils.dataframe_record_as_json_string(row, i, 'records')
                self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', msg,
                                           pika.BasicProperties(content_type='text/plain',
                                                                delivery_mode=pika.DeliveryMode.Persistent,
                                                                timestamp=utils.datetime_as_offset(i)))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange=None,
                 routing_key=None):
        super(Firehose, self).__init__(host=host, data=data, exchange=exchange, routing_key=routing_key,
                                       send_callback=Firehose.send_messages)
