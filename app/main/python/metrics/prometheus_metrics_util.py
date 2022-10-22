import mlmetrics


def send_arima_mae(mae):
    mlmetrics.exporter.prepare_gauge('anomaly_mae', 'ARIMA Model Median Absolute Error', [], mae)
