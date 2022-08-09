import joblib
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
from app.main.python import feature_store, config
import threading


def get_data(begin_offset=None, end_offset=None):
    data = get_cached_data()

    if data is None:
        csv_data_source_path = 'app/data/airlinetweets.csv'
        data = pd.read_csv(csv_data_source_path, parse_dates=['tweet_created'],
                           index_col=['tweet_created']).sort_index()
        # Adjust timestamps to align with today's date for demo purposes
        lag_adjustment = pytz.utc.localize(datetime.now()) - data.index.max()
        data.set_index(data.index + lag_adjustment, inplace=True)

    if begin_offset is None and end_offset is None:
        return data

    if begin_offset is not None:
        # Fetch new rows starting from after the begin offset
        data = data[data.index > begin_offset]

    if end_offset is not None:
        # New rows should come before the end offset
        data = data[data.index < end_offset]

    # Store to feature store
    feature_store.save_artifact(data, '_data')

    return data


def get_cached_data():
    return feature_store.load_artifact('_data')


def launch_refresh_data_listener(end_offset=None):
    # every [config.dashboard_refresh_interval] seconds,
    # consume [config.dashboard_refresh_window_size_in_minutes] minutes of data from the stream
    while True:
        task = threading.Timer(config.dashboard_refresh_interval, refresh_data, args=end_offset)
        task.start()


def refresh_data(end_offset=None):
    # Get existing data
    old_data = get_data()

    # compute the amount of history that has been captured
    history = old_data.index[0] - old_data.index[-1]

    # Drop all overflow records from the dataset, i.e.
    # records with timestamps that are earlier than the permitted history window
    data = pd.concat([old_data.index > (old_data.index[0] - history)], old_data)
