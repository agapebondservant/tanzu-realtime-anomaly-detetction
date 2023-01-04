import json
from datetime import datetime
import pytz
import re
import ray
import os
import mlflow
ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ), 'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import pandas as pd
import logging
import traceback
from app.main.python import feature_store, config
from collections import defaultdict
import sys

################################################
# Command Line Utils
#
################################################


def get_cmd_arg(name):
    d = defaultdict(list)
    for cmd_args in sys.argv[1:]:
        cmd_arg = cmd_args.split('=')
        if len(cmd_arg) == 2:
            d[cmd_arg[0].lstrip('-')].append(cmd_arg[1])

    if name in d:
        return d[name][0]
    else:
        logging.info('Unknown command line arg requested: {}'.format(name))

################################################
# Environment Variable Utils
#
################################################


def get_env_var(name):
    if name in os.environ:
        value = os.environ[name]
        return int(value) if re.match("\d+$", value) else value
    else:
        logging.info('Unknown environment variable requested: {}'.format(name))


def set_env_var(name, value):
    if value:
        os.environ[name] = value

################################################
# Dataframe Utils
#
################################################


def dataframe_record_as_json_string(row, date_index, orientation):
    msg = json.loads(row.to_json(orient=orientation))
    msg.insert(0, datetime.strftime(date_index, '%Y-%m-%d %H:%M:%S%z'))
    msg = json.dumps(msg)
    return msg


def get_current_datetime():
    return pytz.utc.localize(datetime.now())


def get_max_index(df):
    if df is None:
        return None
    return df.index.max()


def get_min_index(df):
    if df is None:
        return None
    return df.index.min()


def filter_rows_by_head_or_tail(df, head=True, num_rows_in_head=None, num_rows_in_tail=None):
    if (num_rows_in_head is not None) != (num_rows_in_tail is not None):
        raise ValueError(
            f"Exactly one of num_rows_head({num_rows_in_head}) and num_rows_tail({num_rows_in_tail}) must be passed, not both")
    if num_rows_in_head is not None:
        return df[:num_rows_in_head] if head else df[num_rows_in_head:]
    else:
        return df[:-num_rows_in_tail] if head else df[-num_rows_in_tail:]


def append_json_list_to_dataframe(df, json_records):
    df_data = json_records[1:]
    df_index = epoch_as_datetime(json_records[0])
    df_columns = df.columns

    if 'sentiment' in list(df_columns):
        sentiment_idx = list(df_columns).index('airline_sentiment')
        df_data += [{'positive': 1, 'negative': -1, 'neutral': 0}.get(df_data[sentiment_idx])]

    df2 = pd.DataFrame(
        data={df.columns[col]: df_data[col] for col in range(len(df_columns))},
        index=[df_index])

    return pd.concat([df, df2])


def datetime_as_utc(dt):
    return pytz.utc.localize(dt)


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


sequence_id = 569587140490866700


def next_sequence_id():
    global sequence_id
    sequence_id += 1
    return sequence_id


def get_next_rolling_window(current_dataset, num_shifts):
    if not len(current_dataset):
        logging.error("Error: Cannot get the next rolling window for an empty dataset")
    else:
        new_dataset = pd.concat([current_dataset[num_shifts % len(current_dataset):], current_dataset[:num_shifts % len(current_dataset)]])
        new_dataset.index = current_dataset.index + (current_dataset.index.freq * num_shifts)
        return new_dataset


################################################
# MLFlow Utils
#
################################################
def get_current_run_id():
    last_active_run = mlflow.last_active_run()
    return last_active_run.info.run_id if last_active_run else None


def get_parent_run_id():
    last_active_run = mlflow.last_active_run()
    logging.debug(f"Current run id is...{get_current_run_id()}\nParent run id is...{last_active_run.data.tags.get('mlflow.parentRunId')}")
    return (last_active_run.data.tags.get("mlflow.parentRunId") or get_current_run_id()) if last_active_run else None


def prepare_mlflow_experiment():
    current_experiment_name = get_env_var('CURRENT_EXPERIMENT')
    current_experiment = mlflow.get_experiment_by_name(current_experiment_name)
    current_experiment_id = current_experiment.experiment_id if current_experiment and current_experiment.lifecycle_stage == 'active' else mlflow.create_experiment(
        current_experiment_name)
    mlflow_tags = {'step': get_env_var('CURRENT_APP') or '', 'run_tag': get_env_var('RUN_TAG') or ''}
    set_env_var("MLFLOW_CURRENT_TAGS", json.dumps(mlflow_tags))
    set_env_var("MLFLOW_EXPERIMENT_ID", current_experiment_id)
    logging.info(
        f"Launching experiment...experiment name={current_experiment_name}, experiment id={current_experiment_id}, tags={mlflow_tags}")


def prepare_mlflow_run(active_run):
    mlflow.set_tags(json.loads(get_env_var("MLFLOW_CURRENT_TAGS")))
    set_env_var('MLFLOW_RUN_ID', active_run.info.run_id)
