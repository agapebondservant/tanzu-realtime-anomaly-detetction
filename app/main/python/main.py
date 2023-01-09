########################
# Imports
########################
import streamlit as st
import logging
import warnings
import traceback
from app.main.python import sentiment_analysis, anomaly_detection, data_source, feature_store, feature_store_remote
from sklearn.preprocessing import StandardScaler
from app.main.python.publishers.firehose import Firehose
from app.main.python.publishers.post_collector import PostCollector
from app.main.python.subscribers.dashboard_monitor import DashboardMonitor
from app.main.python import config, csv_data
from app.main.python.utils import utils
from app.main.python.subscribers.firehose_monitor import FirehoseMonitor
from app.main.python.settings import settings
import mlflow
from datetime import datetime
import os

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

        with mlflow.start_run(run_id=utils.get_current_run_id(), run_name=datetime.now().strftime("%Y-%m-%d-%H%M"),
                              nested=True):

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

            feature_store.save_artifact(True, 'sentiment_analysis_is_trained')

            logging.info("Sentiment Analysis Pipeline execution complete.")
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def sentiment_analysis_inference_pipeline():
    try:
        if len(st.session_state['sentiment_post']) != 0:
            st.session_state['sentiment'] = sentiment_analysis.predict(st.session_state['sentiment_post'])
            post_collector = PostCollector(host=config.host,
                                           post=st.session_state['sentiment_post'],
                                           sentiment=st.session_state['sentiment'])
            post_collector.start()
        return st.session_state['sentiment']
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
        df = settings.anomaly_detection.ingest_data()

        # Store input values
        settings.anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

        # Prepare data by performing feature extraction
        buffers = settings.anomaly_detection.prepare_data(df, sample_frequency, extvars)

        # Plot positive/negative trends
        fig = settings.anomaly_detection.plot_positive_negative_trends(buffers['total_sentiments'],
                                                                       buffers['actual_positive_sentiments'],
                                                                       buffers['actual_negative_sentiments'],
                                                                       timeframe=reporting_timeframe)

        return fig

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


# TODO: Use external pipeline like Argo Workflow/Airflow/Spring Cloud Data Flow
def anomaly_detection_needs_training():
    return feature_store.load_artifact('anomaly_detection_is_trained') is None


# TODO: Use external pipeline like Argo Workflow/Airflow/Spring Cloud Data Flow
def sentiment_analysis_needs_training():
    logging.info(f"Needs training ... {feature_store.load_artifact('sentiment_analysis_is_trained') is None}")
    return feature_store.load_artifact('sentiment_analysis_is_trained') is None


def anomaly_detection_training_pipeline(sample_frequency, reporting_timeframe, rebuild=False):
    with mlflow.start_run(run_id=utils.get_current_run_id(), run_name=datetime.now().strftime("%Y-%m-%d-%H%M"),
                          nested=True):
        logging.info("Starting Anomaly Detection Training Pipeline.......................")

        # Input features
        data_freq, sliding_window_size, estimated_seasonality_hours, arima_order, training_percent = 10, 144, 24, None, 0.73  # 0.80
        logging.info(
            f"Params: data_freq={data_freq}, sliding_window_size={sliding_window_size}, training_percent={training_percent}")

        # Other required variables

        extvars = settings.anomaly_detection.get_utility_vars()

        # Set up metrics

        try:
            # Ingest Data
            df = settings.anomaly_detection.ingest_data()

            # Store input values
            settings.anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

            # Prepare data by performing feature extraction
            buffers = settings.anomaly_detection.prepare_data(df, sample_frequency, extvars)

            # Determine the training window
            num_future_predictions = 2
            if rebuild:
                total_training_window = int(training_percent * len(buffers['actual_negative_sentiments']))
                total_forecast_window = len(
                    buffers['actual_negative_sentiments']) - total_training_window + num_future_predictions
            else:
                total_training_window = len(buffers['actual_negative_sentiments'])
                total_forecast_window = num_future_predictions

            # Save EDA artifacts
            settings.anomaly_detection.generate_and_save_eda_metrics(df)

            # Perform ADF test
            adf_results = settings.anomaly_detection.generate_and_save_adf_results(
                buffers['actual_negative_sentiments'])
            settings.anomaly_detection.generate_and_save_stationarity_results(buffers['actual_negative_sentiments'],
                                                                              estimated_seasonality_hours)

            # Check for stationarity
            logging.info(f'Stationarity : {settings.anomaly_detection.check_stationarity(adf_results)}')
            logging.info(f'P-value : {adf_results[1]}')

            # Build a predictive model (or reuse existing one if this is not rebuild mode)
            stepwise_fit = settings.anomaly_detection.build_model(buffers['actual_negative_sentiments'], rebuild)

            # Perform training
            model_results = settings.anomaly_detection.train_model(total_training_window, stepwise_fit,
                                                                   buffers['actual_negative_sentiments'],
                                                                   rebuild=rebuild,
                                                                   data_freq=data_freq)

            # Perform forecasting
            model_forecasts = settings.anomaly_detection.generate_forecasts(sliding_window_size,
                                                                            total_forecast_window,
                                                                            stepwise_fit,
                                                                            buffers[
                                                                                'actual_negative_sentiments'],
                                                                            rebuild,
                                                                            total_training_window=total_training_window)

            # Detect anomalies
            model_results_full = settings.anomaly_detection.detect_anomalies(model_results,  # fittedvalues,
                                                                             total_training_window,
                                                                             buffers['actual_negative_sentiments'])

            # Plot anomalies
            fig = settings.anomaly_detection.plot_trend_with_anomalies(buffers['actual_negative_sentiments'],
                                                                       model_results_full,
                                                                       model_forecasts,
                                                                       total_training_window,
                                                                       stepwise_fit,
                                                                       extvars,
                                                                       reporting_timeframe,
                                                                       data_freq=data_freq)

            # TEMPORARY: Set a flag indicating that training was done
            feature_store.save_artifact(True, 'anomaly_detection_is_trained')

            return fig

        except Exception as e:
            logging.error('Could not complete execution - error occurred: ', exc_info=True)
            traceback.print_exc()


def anomaly_detection_inference_pipeline(sample_frequency, reporting_timeframe):
    logging.info("Starting Anomaly Detection Inference Pipeline.......................")

    # Input features
    data_freq, sliding_window_size, total_forecast_window, total_training_window, arima_order = 10, 144, 2, 1440, None

    # Other required variables
    extvars = settings.anomaly_detection.get_utility_vars()

    try:
        # Ingest Data
        data = settings.anomaly_detection.ingest_data()

        # Filter Data to return a total incremental training window of size total_training_window
        # data = anomaly_detection.filter_data(data, total_training_window)

        # Store input values
        settings.anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)

        # Prepare Data
        buffers = settings.anomaly_detection.prepare_data(data, sample_frequency, extvars)

        # Retrieve stepwise_fit (used by ARIMA model only)
        stepwise_fit = feature_store_remote.load_artifact('anomaly_auto_arima', remote=False)

        # Retrieve training results
        model_results = settings.anomaly_detection.get_prior_forecasts()

        # Last Published Date
        last_published_date = utils.get_max_index(buffers['actual_negative_sentiments'])

        # Get latest predictions
        model_predictions = settings.anomaly_detection.get_predictions_before_or_at(last_published_date)

        # Get latest forecasts
        model_forecasts = settings.anomaly_detection.get_forecasts_after(last_published_date)

        # Detect anomalies
        model_results_full = settings.anomaly_detection.detect_anomalies(
            model_predictions,
            total_training_window,
            buffers['actual_negative_sentiments'])

        # Plot anomalies
        fig = settings.anomaly_detection.plot_trend_with_anomalies(buffers['actual_negative_sentiments'],
                                                                   model_results_full,
                                                                   model_forecasts,
                                                                   total_training_window,
                                                                   stepwise_fit,
                                                                   extvars,
                                                                   reporting_timeframe)

        return fig

    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


def anomaly_detection_stats(sample_frequency):
    logging.info("Running Anomaly Detection stats.......................")
    try:
        # Initialize realtime data filter if necessary
        # if config.publisher is None:
        #    config.publisher = Publisher(host=config.host)
        #    config.publisher.start()

        # Generate stats
        stats = settings.anomaly_detection.get_trend_stats()
        return stats
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Initialize MQ connections
#############################
def initialize():
    logging.info(f"in initialize...{utils.get_cmd_arg('model_name')} {config.firehose} {config.dashboard_monitor}")
    if config.firehose_monitor is None or config.firehose is None or config.dashboard_monitor is None:
        mlflow.end_run()
        run_name = datetime.now().strftime("%Y-%m-%d-%H%M")
        with mlflow.start_run(run_name=run_name) as active_run:
            os.environ['MLFLOW_RUN_ID'] = active_run.info.run_id
            os.environ['MLFLOW_RUN_NAME'] = run_name
            mlflow.set_tags({'runlevel': 'root'})

            # if config.firehose_monitor is None:
            config.firehose_monitor = FirehoseMonitor(host=config.host)
            config.firehose_monitor.start()

            # if config.firehose is None:
            config.firehose = Firehose(host=config.host, data=csv_data.get_data())
            config.firehose.start()

            # if config.dashboard_monitor is None:
            config.dashboard_monitor = DashboardMonitor(host=config.host, queue=config.dashboard_queue)
            config.dashboard_monitor.start()

    # if config.dashboard_notifier_thread is None:
    #    config.dashboard_notifier_thread = MonitorThread(interval=config.dashboard_refresh_interval,
    #                                                     monitor=notifier.Notifier(host=config.host, data=config.data_published_msg))
    #    config.dashboard_notifier_thread.start()


initialize()
