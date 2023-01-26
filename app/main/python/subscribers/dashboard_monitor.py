import logging
from rabbitmq.connection import subscriber
from app.main.python.ui import dashboard_widgets


class DashboardMonitor(subscriber.Subscriber):

    def receive_messages(self, header, body):
        logging.info("Refreshing dashboard................................")
        dashboard_widgets.render_trends_dashboard('day')

    def __init__(self,
                 host=None,
                 queue='rabbitanalytics4-dashboard',
                 queue_arguments={},
                 consumer_arguments={},
                 offset=0,
                 prefetch_count=1000,
                 conn_retry_count=0):
        super(DashboardMonitor, self).__init__(host=host, queue=queue,
                                               queue_arguments=queue_arguments, consumer_arguments=consumer_arguments,
                                               offset=offset, prefetch_count=prefetch_count,
                                               conn_retry_count=conn_retry_count,
                                               receive_callback=DashboardMonitor.receive_messages,
                                               passive=True)

        self.buffer_length = 0
