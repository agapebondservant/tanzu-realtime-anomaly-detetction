import joblib
import logging
import numpy as np
import pandas as pd
import feature_store
from datetime import datetime, timedelta
import pytz


def get_data(old_data=None, offset=None):
    csv_data_source_path = 'app/data/airlinetweets.csv'
    new_data = pd.read_csv(csv_data_source_path, parse_dates=['tweet_created'],
                           index_col=['tweet_created']).sort_index()

    # Adjust timestamps to align with today's date for demo purposes
    lag_adjustment = pytz.utc.localize(datetime.now()) - new_data.index.max()
    new_data.set_index(new_data.index + lag_adjustment, inplace=True)

    if old_data is None:
        return new_data

    if offset is not None:
        # Fetch new rows starting from after the last offset
        new_data = new_data[new_data.index > offset]

    # compute the amount of history that has been captured
    history = new_data.index[0] - new_data.index[-1]

    # Drop all overflow records from the dataset, i.e.
    # records with timestamps that are earlier than the permitted history window
    return pd.concat([old_data.index > (old_data.index[0] - history)], new_data)
