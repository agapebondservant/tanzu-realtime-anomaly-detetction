########################
# Imports
########################
import pandas as pd
import numpy as np
import logging
import warnings
import traceback
from pylab import rcParams
from datetime import datetime, timedelta
from app.main.python import sentiment_analysis, anomaly_detection, data_source, feature_store
from sklearn.preprocessing import StandardScaler

########################
# Set-up
########################
warnings.filterwarnings('ignore')


#############################
# Sentiment Analysis Inference Pipeline
#############################


def sentiment_analysis_inference_pipeline(text):
    logging.info("Starting Sentiment Analysis Inference Pipeline.......................")
    try:
        sentiment_analysis.predict(text)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Sentiment Analysis Training Pipeline
#############################
def sentiment_analysis_training_pipeline():
    logging.info("Starting Sentiment Analysis Training Pipeline.......................")

    try:
        # Ingest Data
        df = sentiment_analysis.ingest_data()

        # Prepare Data
        df = sentiment_analysis.prepare_data(df)

        # Perform Test-Train Split
        df_train, df_test = sentiment_analysis.train_test_split(df)

        # Perform tf-idf vectorization
        x_train, x_test, y_train, y_test, vectorizer = sentiment_analysis.vectorization(df_train, df_test)

        # Generate model
        model = sentiment_analysis.train(x_train, x_test, y_train, y_test)

        # Store metrics
        sentiment_analysis.generate_and_save_metrics(x_train, x_test, y_train, y_test, model)

        # Save model
        sentiment_analysis.save_model(model)

        # Save vectorizer
        sentiment_analysis.save_vectorizer(vectorizer)

        logging.info("Sentiment Analysis Pipeline execution complete.")
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def sentiment_analysis_inference_pipeline(text):
    try:
        return sentiment_analysis.predict(text)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def anomaly_detection_show_trends(sample_frequency, reporting_timeframe):
    logging.info("Starting Anomaly Detection Show Trends Pipeline.......................")

    # Input features
    data_freq, sliding_window_size, total_forecast_window, total_training_window, arima_order = 10, 144, 144, None, None

    # Other required variables

    extvars = {
        'anomaly_positive_standard_scalar': StandardScaler(),
        'anomaly_neutral_standard_scalar': StandardScaler(),
        'anomaly_negative_standard_scalar': StandardScaler(),
    }

    try:
        # Ingest Data
        df = anomaly_detection.ingest_data()

        # Store input values
        anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

        # Prepare data by performing feature extraction
        buffers = anomaly_detection.prepare_data(df, sample_frequency, extvars)

        # Plot positive/negative trends
        fig = anomaly_detection.plot_positive_negative_trends(buffers['total_sentiments'],
                                                              buffers['actual_positive_sentiments'],
                                                              buffers['actual_negative_sentiments'],
                                                              timeframe=reporting_timeframe)

        return fig

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def anomaly_detection_training_pipeline(sample_frequency, reporting_timeframe, retrain=False):
    logging.info("Starting Anomaly Detection Training Pipeline.......................")

    # Input features
    data_freq, sliding_window_size, total_forecast_window, estimated_seasonality_hours, arima_order = 10, 144, 144, 24, None

    # Other required variables

    extvars = {
        'anomaly_positive_standard_scalar': StandardScaler(),
        'anomaly_neutral_standard_scalar': StandardScaler(),
        'anomaly_negative_standard_scalar': StandardScaler(),
    }

    try:
        # Ingest Data
        df = anomaly_detection.ingest_data()

        # Store input values
        anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

        # Prepare data by performing feature extraction
        buffers = anomaly_detection.prepare_data(df, sample_frequency, extvars)
        total_training_window = len(buffers['actual_negative_sentiments']) - total_forecast_window

        # Save EDA artifacts
        anomaly_detection.generate_and_save_eda_metrics(df)

        # Perform ADF test
        adf_results = anomaly_detection.generate_and_save_adf_results(buffers['actual_negative_sentiments'])
        anomaly_detection.generate_and_save_stationarity_results(buffers['actual_negative_sentiments'],
                                                                 estimated_seasonality_hours)

        # Check for stationarity
        logging.info(f'Stationarity : {anomaly_detection.check_stationarity(adf_results)}')
        logging.info(f'P-value : {adf_results[1]}')

        # Generate an ARIMA model
        stepwise_fit = anomaly_detection.run_auto_arima(buffers['actual_negative_sentiments'], retrain)

        # Perform training
        model_arima_results = anomaly_detection.build_arima_model(total_training_window, stepwise_fit, buffers['actual_negative_sentiments'])

        # Detect anomalies
        model_arima_results_full = anomaly_detection.detect_anomalies(model_arima_results.fittedvalues,
                                                                      total_training_window,
                                                                      buffers['actual_negative_sentiments'])

        # Plot anomalies
        fig = anomaly_detection.plot_trend_with_anomalies(model_arima_results_full,
                                                          total_training_window,
                                                          stepwise_fit,
                                                          extvars,
                                                          reporting_timeframe)

        return fig

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def anomaly_detection_inference_pipeline(sample_frequency, reporting_timeframe):
    logging.info("Starting Anomaly Detection Inference Pipeline.......................")

    # Input features
    data_freq, sliding_window_size, total_forecast_window, total_training_window, arima_order = 10, 144, 3, 1440, None

    try:
        # Ingest Data
        data = anomaly_detection.ingest_data()

        # Filter Data to return a total incremental training window of size total_training_window
        data = anomaly_detection.filter_data(data, total_training_window)

        # Store input values
        anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

        # Prepare Data
        buffers = anomaly_detection.prepare_data(data, sample_frequency)

        # Retrieve auto-arima results
        auto_arima_results = feature_store.load_artifact('anomaly_auto_arima')

        # Generate predictions
        predictions = anomaly_detection.generate_arima_predictions(sliding_window_size,
                                                                   total_forecast_window,
                                                                   auto_arima_results,
                                                                   buffers['actual_negative_sentiments'])

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def anomaly_detection_stats(sample_frequency):
    logging.info("Running Anomaly Detection stats.......................")
    try:
        # Generate stats
        stats = anomaly_detection.get_trend_stats()
        return stats
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
