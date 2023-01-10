from app.main.python import csv_data_source, feature_store


def get_data(begin_offset=None, end_offset=None):
    return csv_data_source.get_data(begin_offset, end_offset)


def get_arima_model_results():
    arima_model_results = feature_store.load_artifact('anomaly_arima_model_results', distributed=False)
    return arima_model_results
