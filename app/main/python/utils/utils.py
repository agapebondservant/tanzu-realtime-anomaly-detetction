import json
from datetime import datetime
import pytz
import pandas as pd
import logging
import traceback
import functools
from app.main.python import feature_store, config
import streamlit as st
import threading


def dataframe_record_as_json_string(row, date_index, orientation):
    msg = json.loads(row.to_json(orient=orientation))
    msg.insert(0, datetime.strftime(date_index, '%Y-%m-%d %H:%M:%S%z'))
    msg = json.dumps(msg)
    return msg


def get_current_datetime():
    return pytz.utc.localize(datetime.now())


def append_json_list_to_dataframe(df, json_record):
    df_data = json_record[1:]
    df_index = json_record[0]
    df_columns = df.columns

    # num_columns_to_append = len(df.columns) - len(json_record[1:])
    # df_data += [None]*num_columns_to_append

    if 'sentiment' in list(df_columns):
        sentiment_idx = list(df_columns).index('airline_sentiment')
        df_data += [{'positive': 1, 'negative': -1, 'neutral': 0}.get(df_data[sentiment_idx])]

    df2 = pd.DataFrame(
        data={df.columns[col]: df_data[col] for col in range(len(df_columns))},
        index=[df_index])
    pd.to_datetime(df2.index, format='%Y-%m-%d %H:%M:%S%z', utc=True, errors='coerce')

    return pd.concat([df, df2])


def index_as_datetime(data):
    return pd.to_datetime(data.index, format='%Y-%m-%d %H:%M:%S%z', utc=True, errors='coerce')


def datetime_as_offset(dt):
    return int(dt.timestamp())


def epoch_as_datetime(epoch_time):
    return datetime.utcfromtimestamp(epoch_time).replace(tzinfo=pytz.utc)


def store_global_offset(dt):
    offset = datetime_as_offset(dt)
    logging.info(f"saving original offset...{offset}")

    # save offset to global store
    feature_store.save_offset(offset, 'original')
    feature_store.save_offset(dt, 'original_datetime')

    # update all relevant consumers to read from the original offset
    monitors = [config.firehose_monitor]
    for monitor in monitors:
        monitor.read_data(offset)


def exception_handler(args):
    logging.error(f'caught {args.exc_type} with value {args.exc_value} in thread {args.thread}\n')
    logging.error(traceback.format_exc())


def use_interrupt(func):
    def wrapper(*args):
        st.session_state.dashboard_global_event.set()
        func(*args)
        st.session_state.dashboard_global_event.clear()
    return wrapper
