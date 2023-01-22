import json
from datetime import datetime
import pytz
import re
import ray
import os
import mlflow
from mlflow import MlflowClient
from mlflow.models import MetricThreshold

ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ),
                      'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import pandas as pd
import logging
import traceback
from app.main.python import feature_store, config
from collections import defaultdict
import sys
import joblib
from multiprocessing import Process, Lock
from filelock import FileLock, Timeout

mutex = Lock()
file_locks = {}


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
# Thread/Concurrency Utils
#
################################################

def synchronize(target=None, args=(), kwargs={}):
    with mutex:
        p = Process(target=target, args=args, kwargs=kwargs)
        p.start()


def synchronize_file_write(file=None, file_path=None):
    try:
        global file_locks
        key = file_path.replace(os.sep, '_')
        lock = file_locks.get(key) or FileLock(f"{file_path}.lock")
        with lock:
            with open(file_path, "wb") as file_handle:
                joblib.dump(file, file_handle)
    except Exception as e:
        logging.info(f'Synchronized file write to {file} at file_path {file_path} failed - error occurred: ',
                     exc_info=True)


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


def append_json_list_to_dataframe(df, json_records, index_col=0):
    df_data = json_records[1:]
    df_index = epoch_as_datetime(json_records[index_col])
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
        new_dataset = pd.concat(
            [current_dataset[num_shifts % len(current_dataset):], current_dataset[:num_shifts % len(current_dataset)]])
        new_dataset.index = current_dataset.index + (current_dataset.index.freq * num_shifts)
        return new_dataset


################################################
# MLFlow Utils
#
################################################
def get_current_run_id():
    last_active_run = mlflow.last_active_run()
    return last_active_run.info.run_id if last_active_run else None


def get_root_run_id(experiment_names=['Default']):
    runs = mlflow.search_runs(experiment_names=experiment_names, filter_string="tags.runlevel='root'", max_results=1,
                              output_format='list')
    logging.debug(f"Parent run is...{runs}")
    return runs[0].info.run_id if len(runs) else None


def mlflow_log_model(parent_run_id, model, flavor, **kwargs):
    logging.info(f"In log_model...run id = {parent_run_id}")
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

    getattr(mlflow, flavor).log_model(model, **kwargs)

    logging.info("Logging was successful.")


def mlflow_load_model(parent_run_id, flavor, model_uri=None, **kwargs):
    try:
        logging.info(f"In load_model...run id = {parent_run_id}")
        mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

        model = getattr(mlflow, flavor).load_model(model_uri)
        logging.info("Model loaded.")

        return model
    except Exception as e:
        logging.info(f'Could not complete execution for load_model - {model_uri}- error occurred: ', exc_info=True)


def mlflow_log_dict(parent_run_id, dataframe=None, dict_name=None):
    logging.info(f"In log_dict...run id = {parent_run_id}")
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

    dataframe.index = dataframe.index.astype('str')
    MlflowClient().log_dict(parent_run_id, dataframe.to_dict(), dict_name)

    logging.info("Logging was successful.")


def mlflow_log_metric(parent_run_id, **kwargs):
    logging.info(f"In log_metric...run id = {parent_run_id}")
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

    MlflowClient().log_metric(parent_run_id, **kwargs)

    logging.info("Logging was successful.")


def mlflow_log_artifact(parent_run_id, artifact, local_path, **kwargs):
    logging.info(f"In log_artifact...run id = {parent_run_id}, local_path")
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

    with open(local_path, "wb") as artifact_handle:
        joblib.dump(artifact, artifact_handle)
    # synchronize_file_write(file=artifact, file_path=local_path)
    MlflowClient().log_artifact(parent_run_id, local_path, **kwargs)
    logging.info("Logging was successful.")


def mlflow_load_artifact(parent_run_id, artifact_name, **kwargs):
    try:
        logging.info(f"In load_artifact...run id = {parent_run_id}, {kwargs}")
        mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

        artifact_list = MlflowClient().list_artifacts(parent_run_id)
        artifact_match = next((artifact for artifact in artifact_list if artifact.path == artifact_name), None)
        artifact = None

        if artifact_match:
            download_path = mlflow.artifacts.download_artifacts(**kwargs)
            logging.info(f"Artifact downloaded to...{download_path}")
            with open(f"{download_path}", "rb") as artifact_handle:
                artifact = joblib.load(artifact_handle)
        else:
            logging.info(f"Artifact {artifact_name} cannot be loaded (has not yet been saved).")

        return artifact
    except Exception as e:
        logging.info(f'Could not complete execution for load_artifact - {kwargs}- error occurred: ', exc_info=True)


def mlflow_log_text(parent_run_id, **kwargs):
    logging.info(f"In log_text...run id = {parent_run_id}, {kwargs}")
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

    MlflowClient().log_text(parent_run_id, **kwargs)

    logging.info("Logging was successful.")


def mlflow_load_text(parent_run_id, **kwargs):
    try:
        logging.info(f"In load_text...{kwargs}")
        mlflow.set_tags({'mlflow.parentRunId': parent_run_id})

        text = mlflow.artifacts.load_text(**kwargs)
        logging.info(f"Text...{text}")

        return text
    except Exception as e:
        logging.info(f'Could not complete execution for load_text - {kwargs}- error occurred: ', exc_info=True)


def get_dataframe_from_dict(parent_run_id=None, artifact_name=None):
    if parent_run_id and artifact_name:
        pd.DataFrame.from_dict(mlflow.artifacts.load_dict(f"runs:/{parent_run_id}/{artifact_name}"))
    else:
        logging.error(
            f"Could not load dict with empty parent_run_id or artifact_name (run_id={parent_run_id}, artifact_name={artifact_name}")


def mlflow_generate_autolog_metrics(flavor=None):
    getattr(mlflow, flavor).autolog(log_models=False) if flavor is not None else mlflow.autolog(log_models=False)


def mlflow_evaluate_models(parent_run_id, flavor, baseline_model=None, candidate_model=None, data=None,
                           version=None):
    mlflow.set_tags({'mlflow.parentRunId': parent_run_id})
    logging.info(f"In evaluate_models...run id = {parent_run_id}")
    try:
        client = MlflowClient()

        mlflow.evaluate(
            candidate_model.model_uri,
            data,
            targets="target",
            model_type="regressor",
            validation_thresholds={
                "r2_score": MetricThreshold(
                    threshold=0.5,
                    min_absolute_change=0.05,
                    min_relative_change=0.05,
                    higher_is_better=True
                ),
            },
            baseline_model=baseline_model.model_uri,
        )

        logging.info("Candidate model passed evaluation; promoting to Staging...")

        client.transition_model_version_stage(
            name="baseline_model",
            version=version,
            stage="Staging"
        )

        logging.info("Candidate model promoted successfully.")

        logging.info("Updating baseline model...")
        mlflow_log_model(candidate_model,
                         parent_run_id,
                         registered_model_name='baseline_model',
                         await_registration_for=None)

        logging.info("Evaluation complete.")
        return True
    except BaseException as e:
        logging.error(
            "Candidate model training failed to satisfy configured thresholds...could not promote. Retaining baseline model.")
