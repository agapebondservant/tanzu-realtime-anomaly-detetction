def simulate_firehose_data(self, data):
    # while True:
    lag_adjustment = pytz.utc.localize(datetime.now()) - data.index.min() + timedelta(minutes=1)
    new_data = data.copy()
    new_data.set_index(new_data.index + lag_adjustment, inplace=True)
    for i, row in new_data.iterrows():
        msg = row.to_json(orient='records')
        self.channel.basic_publish('rabbitanalytics4-stream-exchange', 'anomaly.all', msg,
                                   pika.BasicProperties(content_type='text/plain',
                                                        delivery_mode=pika.DeliveryMode.Persistent,
                                                        timestamp=int(i.timestamp())))
