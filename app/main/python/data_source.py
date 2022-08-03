
import joblib
import logging
import numpy as np
import pandas as pd
import feature_store
from datetime import datetime, timedelta
from app.main.python import csv_data, mq_data, firehose_publisher


def get_data_source_mode():
    return 'csv'


def get_data(data=None, offset_from_end=None):
    mode = get_data_source_mode()
    if mode == 'csv':
        return csv_data.get_data(data, offset_from_end)
    if mode == 'mq':
        return mq_data.get_data(data, offset_from_end)


def get_arima_model_results():
    arima_model_results = feature_store.load_artifact('anomaly_arima_model_results')
    return arima_model_results
