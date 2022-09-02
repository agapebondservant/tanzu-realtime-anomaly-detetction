import pika
from rabbitmq.connection import publisher


class Notifier(publisher.Publisher):

    def send_messages(self, _channel):
        """Called when our channel has opened"""

        # Publish notification to topic exchange that new data was published
        self.channel.basic_publish(self.exchange, self.routing_key, self.data,
                                   pika.BasicProperties(content_type='text/plain',
                                                        delivery_mode=pika.DeliveryMode.Persistent))

    def __init__(self,
                 host=None,
                 data=None,
                 exchange='rabbitanalytics4-exchange',
                 routing_key='anomaly.datapublished'):
        super(Notifier, self).__init__(host=host, data=data, exchange=exchange, routing_key=routing_key,
                                       send_callback=Notifier.send_messages)
