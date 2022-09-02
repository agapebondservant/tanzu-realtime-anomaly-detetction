# Sample Usage

```
import connection_utils
from rabbitmq_consumer import RabbitMQConsumer
from rabbitmq_producer import RabbitMQProducer

# Producer code:
producer = RabbitMQProducer(host='my-host-address',
    data=['abc','123'],
    exchange='my-exchange',
    routing_key='my.routing.key')
@send_method(producer)
def on_send(self, _channel):
    """ Publishes data """
    super().on_channel_open(_channel) # Must include this line!!!
    self.channel.basic_publish(self.exchange, self.routing_key, json.dumps(self.data),
                               pika.BasicProperties(content_type='text/plain',
                                                    delivery_mode=pika.DeliveryMode.Persistent,
                                                    timestamp=int(self.data.publish_dt.timestamp()))
producer.start()
      
# Consumer code:
consumer = RabbitMQConsumer(host='my-host-address',
    queue='my-queue-name',
    queue_arguments={'x-queue-type': 'stream'},
    consumer_arguments={'offset':16000000})
@receive_method(consumer)
def on_receive(self, header, body):
    """ Consumes data """
    print(f"Message received! {body}")
consumer.start()
```