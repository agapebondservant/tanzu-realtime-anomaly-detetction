import joblib
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pytz
from app.main.python import feature_store, config
from app.main.python.subscribers.firehose_monitor import FirehoseMonitor
from app.main.python.utils import utils
import threading
import json


def get_data(begin_offset=None, end_offset=None):
    data = get_cached_data()

    if data is None:
        csv_data_source_path = 'app/data/airlinetweets.csv'
        data = pd.read_csv(csv_data_source_path, parse_dates=['tweet_created'],
                           index_col=['tweet_created']).sort_index()
        # Adjust timestamps to align with today's date for demo purposes
        lag_adjustment = utils.get_current_datetime() - data.index.max()
        data.set_index(data.index + lag_adjustment, inplace=True)

        logging.info(f"original offset...{utils.datetime_as_offset(data.index.max())}")
        feature_store.save_offset('original', utils.datetime_as_offset(data.index.max()))
    else:
        data.index = utils.index_as_datetime(data)

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
