########################
# Imports
########################
import pandas as pd
import numpy as np
import logging
import warnings
import traceback
from pylab import rcParams
from app.main.python import sentiment_analysis, anomaly_detection

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
def sentiment_analysis_training_pipeline(source):
    logging.info("Starting Sentiment Analysis Training Pipeline.......................")

    try:
        # Ingest Data
        df = sentiment_analysis.ingest_data(source)

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


def anomaly_detection_training_pipeline(source, sample_frequency, reporting_timeframe):
    logging.info("Starting Anomaly Detection Pipeline.......................")

    # Input features
    data_freq, sliding_window_size, total_forecast_window = 10, 144, 1440

    try:
        # Ingest Data
        df = anomaly_detection.ingest_data(source)

        # Store input values
        anomaly_detection.initialize_input_features(data_freq, sliding_window_size, total_forecast_window)

        # Perform feature extraction
        buffers = anomaly_detection.extract_features(df, sample_frequency=sample_frequency)

        # Save EDA artifacts
        anomaly_detection.generate_and_save_eda_metrics(df)

        # Perform ADF test
        adf_results = anomaly_detection.generate_and_save_adf_results(buffers['actual_negative_sentiments'])
        anomaly_detection.generate_and_save_stationarity_results(buffers['actual_negative_sentiments'],
                                                                 sliding_window_size)

        # Check for stationarity
        logging.info(f'Stationarity : {anomaly_detection.check_stationarity(adf_results)}')
        logging.info(f'P-value : {adf_results[1]}')

        # Plot positive/negative trends
        fig = anomaly_detection.plot_positive_negative_trends(buffers['total_sentiments'],
                                                              buffers['actual_positive_sentiments'],
                                                              buffers['actual_negative_sentiments'],
                                                              timeframe=reporting_timeframe)

        return fig

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
