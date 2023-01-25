import ray
import os

ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ),
                      'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import pandas as pd
from app.main.python import feature_store
from app.main.python.utils import utils

data_columns = None


def get_data(begin_offset=None, end_offset=None, new_data=None):
    data = get_cached_data()

    if data is None:
        csv_data_source_path = 'app/data/airlinetweets.csv'
        data = pd.read_csv(csv_data_source_path, parse_dates=['tweet_created'],
                           index_col=['tweet_created']).sort_index()

        # Adjust timestamps to align with today's date for demo purposes
        current_dt = utils.get_current_datetime()
        lag_adjustment = current_dt - data.index.max()
        data.set_index(data.index + lag_adjustment, inplace=True)

        # Temporary: Get only the last 7 days
        # (based on the state of the data in the csv file)
        # data = data[data.index > (current_dt - timedelta(days=7))]

        # Store the last published date as the offset
        last_published_date = current_dt
        utils.store_global_offset(last_published_date)
    else:
        data.index = utils.index_as_datetime(data)

    if new_data is not None:
        data = pd.concat([data, new_data])

    if begin_offset is not None:
        # Fetch new rows starting from after the begin offset
        data = data[data.index > begin_offset]

    if end_offset is not None:
        # New rows should come before the end offset
        data = data[data.index < end_offset]

    # Store to feature store
    feature_store.save_artifact(data, '_data', distributed=False)

    return data


def get_cached_data():
    return feature_store.load_artifact('_data', distributed=False)


def add_data(new_data):
    return get_data(new_data=new_data)


def get_data_schema():
    global data_columns
    if data_columns is None:
        csv_data_source_path = 'app/data/airlinetweets.csv'
        data_columns = pd.read_csv(csv_data_source_path, parse_dates=['tweet_created'],
                                   index_col=['tweet_created']).columns
    return data_columns
