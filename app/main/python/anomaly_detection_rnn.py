########################
# Imports
########################
import ray
import os

ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ),
                      'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import pandas as pd
import numpy as np
import logging
from statsmodels.tsa.seasonal import seasonal_decompose
from pylab import rcParams
from datetime import datetime
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from statsmodels.tsa.statespace.tools import diff
from statsmodels.tsa.stattools import acovf, acf, pacf, pacf_yw, pacf_ols
from pandas.plotting import lag_plot
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf, month_plot, quarter_plot
from statsmodels.tsa.stattools import adfuller
from statsmodels.tools.eval_measures import mse, rmse, meanabs, aic, bic
from pmdarima import auto_arima
from statsmodels.tsa.seasonal import seasonal_decompose
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from statsmodels.tsa.arima.model import ARIMA
from statistics import median, mean
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import pytz
import warnings
import scipy.stats as st
import math
import seaborn as sns
from pylab import rcParams
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
import re
import pytz
import math
import json
from app.main.python import feature_store, data_source, config, anomaly_detection
from app.main.python.utils import utils
from app.main.python.metrics import prometheus_metrics_util
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, SimpleRNN, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from mlmetrics import exporter


########################################################################################################################
# ANOMALY DETECTION
########################################################################################################################


########################
# Ingest Data
########################
def ingest_data():
    return anomaly_detection.ingest_data()


#######################################
# Set Global Values
#######################################
def initialize_input_features(data_freq, sliding_window_size, rnn_order):
    return anomaly_detection.initialize_input_features(data_freq, sliding_window_size, rnn_order)


#######################################
# Generate and Save EDA Artifacts
#######################################
def generate_and_save_eda_metrics(df):
    return anomaly_detection.generate_and_save_eda_metrics(df)


#############################
# Filter Data
#############################
def filter_data(df, head=True, num_rows_head=None, num_rows_tail=None):
    return anomaly_detection.filter_data(df, head, num_rows_head, num_rows_tail)


#############################
# Prepare Data
#############################

def prepare_data(df, sample_frequency, extvars):
    return anomaly_detection.prepare_data(df, sample_frequency, extvars)


#######################################
# Perform data cleansing
#######################################
def cleanse_data(df):
    return anomaly_detection.cleanse_data(df)


#######################################
# Perform feature extraction via resampling
#######################################
def extract_features(df, sample_frequency='10min', extvars={}, is_partial_data=False):
    return anomaly_detection.extract_features(df, sample_frequency, extvars, is_partial_data)


#######################################
# Perform Data Standardization
#######################################
def standardize_data(buffers, extvars):
    return anomaly_detection.standardize_data(buffers, extvars)


#######################################
# Initialize Data Buffers
#######################################
def get_filtered_data_sets(df, sample_frequency, extvars):
    return anomaly_detection.get_filtered_data_sets(df, sample_frequency, extvars)


#######################################
# Generate and Save ADF Results
#######################################
def generate_and_save_adf_results(actual_negative_sentiments):
    logging.info("Generate and save Dickey-Fuller test results...")
    adfuller_results = adfuller(actual_negative_sentiments['sentiment_normalized'])
    feature_store.save_artifact(adfuller_results, 'adf_results')
    return adfuller_results


#######################################
# Check for stationarity
#######################################
def check_stationarity(adfuller_results):
    logging.info("Check for stationarity...")
    return adfuller_results[1] < 0.05


#######################################
# Generate and Save Stationary Results
#######################################
def generate_and_save_stationarity_results(actual_negative_sentiments, sliding_window_size):
    logging.info("Save stationarity plot results...")
    plot_acf(actual_negative_sentiments['sentiment'], lags=20)
    plt.savefig("anomaly_acf.png", bbox_inches='tight')
    plot_pacf(actual_negative_sentiments['sentiment_normalized'])
    plt.savefig("anomaly_pacf.png", bbox_inches='tight')
    seasonal_decompose(actual_negative_sentiments['sentiment'], model='additive', period=sliding_window_size).plot()
    plt.savefig("anomaly_seasonal_decompose.png", bbox_inches='tight')


#######################################
# Plot Positive/Negative Trends
#####################################
def plot_positive_negative_trends(total_sentiments, actual_positive_sentiments, actual_negative_sentiments,
                                  timeframe='day'):
    logging.info("Plotting positive/negative trends...")
    # Set start_date, end_date
    end_date = utils.get_current_datetime()
    start_date = end_date - timedelta(hours=get_time_lags(timeframe))
    marker_date = feature_store.load_offset('original_datetime')

    fig, ax = plt.subplots(figsize=(12, 5))

    fig.suptitle(f"Trending over the past {timeframe}")
    ax.set_xlim([start_date, end_date])
    ax.plot(actual_positive_sentiments['sentiment'],
            label="Positive Tweets", color="orange")
    ax.plot(actual_negative_sentiments['sentiment'],
            label="Negative Tweets", color="red")
    ax.hlines(actual_positive_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='orange')
    ax.hlines(actual_negative_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='red')
    ax.set_ylabel('Number of posts', fontsize=14)
    ax.axvspan(marker_date, end_date, alpha=0.5, color='gray')
    ax.legend()

    return fig


#######################################
# Build RNN model
#######################################
def build_model(actual_negative_sentiments, sliding_window_size=144, data_freq=10, rebuild=False):
    logging.info("Build RNN model...")

    generator = feature_store.load_artifact('anomaly_timeseries')

    if rebuild is True:
        # Build a Timeseries Generator
        generator = build_timeseries_generator(actual_negative_sentiments['sentiment_normalized'], sliding_window_size)

    feature_store.save_artifact(generator, 'anomaly_timeseries')

    return generator


##############################################################################
# Build a Timeseries generator for the RNN Model
##############################################################################
def build_timeseries_generator(actual_negative_sentiments, training_window_size, sliding_window_size):
    # The training data
    actual_negative_sentiments_train = actual_negative_sentiments.iloc[:training_window_size].dropna()

    logging.info(f"Size of training set: {len(actual_negative_sentiments_train)}")

    # number of outputs per batch
    batch_length = sliding_window_size

    # Number of batches per training cycle
    timeseries_batch_size = 1

    # Standardize the data
    standard_scaler_rnn = StandardScaler()

    standard_scaler_rnn.fit(actual_negative_sentiments_train[['sentiment']])

    feature_store.save_artifact(standard_scaler_rnn, 'scaler_rnn_train')

    scaled_train = standard_scaler_rnn.transform(actual_negative_sentiments_train[['sentiment']])

    # Build the generator
    generator = TimeseriesGenerator(scaled_train,
                                    scaled_train,
                                    length=batch_length,
                                    batch_size=timeseries_batch_size)

    return generator


#######################################
# Train/Validate RNN Model To Generate Results
#######################################
def train_model(training_window_size, stepwise_fit, actual_negative_sentiments, sliding_window_size=144, rebuild=False,
                data_freq=10):
    logging.info(f"Train RNN model...")

    # generate batch_length - number of outputs per batch; generator batch size; number of features
    batch_length, timeseries_batch_size, num_features, num_weights = sliding_window_size, 1, 1, 150

    logging.info(f"Using batch_length={batch_length}, training_window_size={training_window_size}")

    # set up model
    rnn_model = Sequential()

    rnn_model.add(SimpleRNN(num_weights, input_shape=(batch_length, num_features)))

    rnn_model.add(Dense(1))

    rnn_model.compile(optimizer='adam', loss='mae')

    rnn_model.summary()

    # get the training generator
    generator = build_timeseries_generator(actual_negative_sentiments, training_window_size, sliding_window_size)

    # set up Early Stopping
    early_stop = EarlyStopping(monitor='val_loss', patience=2)

    standard_scaler_rnn = feature_store.load_artifact('scaler_rnn_train')

    logging.info(f"Standard scaler: {standard_scaler_rnn}")

    # set the test data
    actual_negative_sentiments_train = actual_negative_sentiments.iloc[:training_window_size].dropna()
    actual_negative_sentiments_test = actual_negative_sentiments.iloc[
                                      training_window_size:].dropna() if rebuild else utils.get_next_rolling_window(
        actual_negative_sentiments, sliding_window_size)

    scaled_test = standard_scaler_rnn.transform(actual_negative_sentiments_test[['sentiment']])

    # build the validation batch generator
    validation_generator = TimeseriesGenerator(scaled_test,
                                               scaled_test,
                                               length=batch_length,
                                               batch_size=timeseries_batch_size)

    # fit the model
    rnn_model.fit_generator(generator, epochs=40, validation_data=validation_generator, callbacks=[early_stop])

    # generate losses visualization
    fig, ax = plt.subplots(figsize=(15, 6))
    fig.suptitle("RNN Losses", fontsize=16)
    losses = pd.DataFrame(rnn_model.history.history)
    ax.plot(pd.DataFrame(losses['loss']), label="Loss")
    ax.plot(pd.DataFrame(losses['val_loss']), label="Validation Loss")
    ax.legend(loc='best')
    plt.savefig("anomaly_rnn_losses.png", bbox_inches='tight')

    # save the model
    feature_store.save_artifact(rnn_model, 'anomaly_rnn_model')

    return generate_forecasts_from_timeseries_generator(rnn_model,
                                                        sliding_window_size,
                                                        standard_scaler_rnn,
                                                        actual_negative_sentiments_train,
                                                        actual_negative_sentiments_test)


#######################################
# Load RNN model
#######################################
def load_model():
    logging.info("Loading RNN model...")
    return feature_store.load_artifact('anomaly_rnn_model')


#######################################
# Test RNN Model
#######################################
def test_rnn_model(sliding_window_size, total_forecast_size, stepwise_fit, actual_negative_sentiments):
    logging.info('Testing RNN model...')

    return generate_forecasts(sliding_window_size, total_forecast_size, stepwise_fit,
                              actual_negative_sentiments)


#######################################
# Detect Anomalies
#######################################
def detect_anomalies(predictions, window_size, actual_negative_sentiments):
    logging.info('Detecting anomalies...')

    z_score = st.norm.ppf(.95)  # 95% confidence interval
    mae_scale_factor = 0.67449  # MAE is 0.67449 * std

    predictions = predictions.iloc[-int(window_size):]

    df_total = actual_negative_sentiments['sentiment'].iloc[:int(window_size)].iloc[-len(predictions):]
    logging.info(f"anomalies for...{df_total} {predictions}...sizes: {len(df_total)} , {len(predictions)}")
    mae = median_absolute_error(df_total, predictions)

    model_rnn_results_full = \
        pd.DataFrame({'fittedvalues': predictions, 'median_values': predictions.rolling(4).median().fillna(0)},
                     index=predictions.index)
    model_rnn_results_full['threshold'] = model_rnn_results_full['median_values'] + (
            z_score / mae_scale_factor) * mae
    model_rnn_results_full['anomaly'] = 0

    model_rnn_results_full['actualvalues'] = df_total
    model_rnn_results_full['actualvalues'].fillna(0, inplace=True)

    model_rnn_results_full.loc[
        model_rnn_results_full['actualvalues'] > model_rnn_results_full['threshold'], 'anomaly'] = 1

    print(f"Anomaly distribution: \n{model_rnn_results_full['anomaly'].value_counts()}")

    # TODO: Publish anomaly summary to queue
    feature_store.save_artifact(actual_negative_sentiments, 'actual_negative_sentiments')
    publish_trend_stats(actual_negative_sentiments)

    return model_rnn_results_full


#######################################
# Plot Trend with Anomalies
#######################################
def plot_trend_with_anomalies(total_negative_sentiments, model_rnn_results_full, model_rnn_forecasts,
                              sliding_window_size,
                              stepwise_fit,
                              extvars,
                              timeframe='hour',
                              data_freq=10):
    logging.info("Plot trend with anomalies...")

    standard_scalar = extvars['anomaly_negative_standard_scalar']
    inverse_scaled = pd.DataFrame(
        model_rnn_results_full[['actualvalues', 'fittedvalues']],
        columns=['actualvalues', 'fittedvalues'],
        index=model_rnn_results_full.index)

    logging.info(f"Inverse scaled values: {inverse_scaled}")

    fitted_values_actual = inverse_scaled['actualvalues']
    fitted_values_predicted = inverse_scaled['fittedvalues']
    fitted_values_forecasted = pd.DataFrame(standard_scalar.inverse_transform(pd.DataFrame(model_rnn_forecasts)),
                                            columns=['forecastvalues'],
                                            index=model_rnn_forecasts.index)['forecastvalues'] if len(
        model_rnn_forecasts) else None

    mae_error = median_absolute_error(fitted_values_predicted, fitted_values_actual)
    feature_store.save_artifact(mae_error, 'anomaly_mae_error')

    # Set start_date, end_date
    target = model_rnn_forecasts if len(model_rnn_forecasts) else fitted_values_actual
    end_date = utils.get_current_datetime()
    logging.info(f"end date is {end_date} {target}")
    start_date = end_date - timedelta(hours=get_time_lags(timeframe))
    marker_date_end = end_date if fitted_values_forecasted is not None else None
    marker_date_start = max(end_date - timedelta(minutes=data_freq * len(target)), utils.get_max_index(target)) if fitted_values_forecasted is not None else None

    # TODO: Publish metrics to queue
    exporter.prepare_histogram('anomaly_mae_error',
                               'Anomaly MAE Error',
                               {'scdf_run_tag': 'v1.0', 'scdf_run_step': 'plot_anomalies'}, mae_error)

    # Plot curves
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim([start_date, end_date])
    ax.plot(fitted_values_actual, label="Actual", color='blue')
    ax.plot(fitted_values_predicted, label=f"RNN Predictions", color='orange')
    ax.plot(fitted_values_forecasted, label='Forecasted', color='green',
            linewidth=2) if fitted_values_forecasted is not None else True
    ax.plot(fitted_values_actual.loc[model_rnn_results_full['anomaly'] == 1],
            marker='o', linestyle='None', color='red', label="Anomalies")
    ax.axvspan(marker_date_start, marker_date_end, alpha=0.5,
               color='green') if fitted_values_forecasted is not None else True

    # Include plots for test data if applicable
    test_data = total_negative_sentiments[['sentiment_normalized']].iloc[int(sliding_window_size):]
    if len(test_data):
        fitted_values_actual_test = pd.DataFrame(standard_scalar.inverse_transform(test_data),
                                                 columns=['testvalues'],
                                                 index=test_data.index)['testvalues']
        ax.plot(fitted_values_actual_test, label="Test", color="yellow")

    ax.legend()
    fig.suptitle(f"RNN Model: \n Median Absolute Error (MAE): {mae_error}", fontsize=16)

    return fig


#######################################
# Generate RNN Forecasts
#######################################
def generate_forecasts(sliding_window_size, total_forecast_size, stepwise_fit, actual_negative_sentiments,
                       rebuild=False,
                       total_training_window=1440,
                       data_freq=10):
    logging.info("Generate RNN predictions...")

    # The dataset to forecast with
    if rebuild:
        num_shifts = total_training_window + total_forecast_size - len(actual_negative_sentiments)
        actual_negative_sentiments_train = actual_negative_sentiments.iloc[:int(total_training_window)]
        actual_negative_sentiments_test = actual_negative_sentiments.iloc[int(total_training_window):]
        actual_negative_sentiments_test = utils.get_next_rolling_window(actual_negative_sentiments_test,
                                                                        num_shifts) if num_shifts else actual_negative_sentiments_test
    else:
        actual_negative_sentiments_train = actual_negative_sentiments
        actual_negative_sentiments_test = utils.get_next_rolling_window(actual_negative_sentiments, sliding_window_size)

    # Load the model
    rnn_model = feature_store.load_artifact('anomaly_rnn_model')

    standard_scaler_rnn = feature_store.load_artifact('scaler_rnn_train')

    return generate_forecasts_from_timeseries_generator(rnn_model,
                                                        sliding_window_size,
                                                        standard_scaler_rnn,
                                                        actual_negative_sentiments_train,
                                                        actual_negative_sentiments_test)


#######################################
# Generate RNN Forecasts from Timeseries Generator
#######################################
def generate_forecasts_from_timeseries_generator(rnn_model, sliding_window_size, standard_scaler,
                                                 actual_negative_sentiments_train, actual_negative_sentiments_test):
    scaled_train = standard_scaler.transform(actual_negative_sentiments_train[['sentiment']])

    scaled_test = standard_scaler.transform(actual_negative_sentiments_test[['sentiment']])

    num_predictions, num_features, batch_length = len(scaled_test), 1, sliding_window_size

    eval_batch = scaled_train[-batch_length:].reshape(1, batch_length, num_features)

    scaled_predictions = []

    for i in np.arange(num_predictions):
        scaled_prediction = rnn_model.predict(eval_batch)

        eval_batch = np.append(eval_batch[:, 1:, :], [scaled_prediction], axis=1)

        scaled_predictions.append(scaled_prediction)

    predictions = standard_scaler.inverse_transform(np.reshape(scaled_predictions, (num_predictions, 1)))

    rnn_predictions = pd.concat([get_prior_forecasts(),
                                 pd.Series(predictions.reshape(-1),
                                           index=actual_negative_sentiments_test.index)]).iloc[-num_predictions:]

    rnn_predictions = rnn_predictions.reindex(actual_negative_sentiments_test.index)

    print(f"rnn predictions : {rnn_predictions}")

    # Store predictions
    feature_store.save_artifact(rnn_predictions, 'anomaly_rnn_forecasts')

    return rnn_predictions


#######################################
# Get any prior forecasts
#######################################
def get_prior_forecasts():
    forecasts = feature_store.load_artifact('anomaly_rnn_forecasts')
    if forecasts is None:
        forecasts = pd.Series([])
    return forecasts


##############################################
# Get latest predictions from prior forecasts
##############################################

def get_predictions_before_or_at(dt):
    forecasts = feature_store.load_artifact('anomaly_rnn_forecasts')
    logging.info(f"forecasts is {dt} {forecasts}")
    if forecasts is None:
        return pd.Series([])
    return forecasts[forecasts.index <= dt]


##############################################
# Get latest forecasts
##############################################

def get_forecasts_after(dt):
    forecasts = feature_store.load_artifact('anomaly_rnn_forecasts')
    if forecasts is None:
        return pd.Series([])
    return forecasts[forecasts.index > dt]


##############################################
# Compute a feasible train-test split percentage
##############################################
def get_train_test_split_percent(actual_negative_sentiments, total_forecast_window_size):
    return 1 - (int(total_forecast_window_size) / len(actual_negative_sentiments))


#######################################
# Convert timeframe flag to number of time lags
#######################################
def get_time_lags(timeframe='day'):
    logging.info(f"Get time lag for {timeframe}...")
    time_lags = {'hour': 1, 'day': 24, 'week': 168}
    return time_lags[timeframe]


#######################################
# Generate and publish stats
#######################################


def publish_trend_stats(actual_negative_sentiments=None):
    if actual_negative_sentiments is None:
        actual_negative_sentiments = feature_store.load_artifact('actual_negative_sentiments')

    sample_frequencies = ['1min', '10min', '60min']

    stats = []

    old_summary = feature_store.load_artifact('anomaly_summary')
    if old_summary is None:
        old_summary = pd.DataFrame()

    for sample_frequency in sample_frequencies:
        num_negative_in_past, sample_frequency_num = 0, int(re.findall(r'\d+', sample_frequency)[0])

        last_recorded_time = actual_negative_sentiments.index[-1]
        offset_time = last_recorded_time - timedelta(minutes=sample_frequency_num)

        num_negative_in_past = actual_negative_sentiments.loc[actual_negative_sentiments.index >= offset_time][
            'sentiment'].sum()
        logging.info(f"Number of negative posts in past {sample_frequency_num} minutes: {num_negative_in_past}")

        stats.append(num_negative_in_past)

    new_summary = {sample_frequencies[i]: [stats[i]] for i in range(len(sample_frequencies))}
    new_summary['anomaly_found'] = [False]  # TODO: Set to True if new anomaly is found
    new_summary = pd.DataFrame.from_dict(new_summary)

    summary = pd.concat([old_summary, new_summary])
    logging.info(f"New Summary: {new_summary}")

    feature_store.save_artifact(summary, 'anomaly_summary')

    # Publish to queue
    # config.stats_publisher.send_data(new_summary)

    return new_summary


#######################################
# Retrieve generated stats
#######################################


def get_trend_stats():
    return feature_store.load_artifact('anomaly_summary')


def process_stats(head, body):
    logging.info('In process_stats...')
    logging.info(f'{json.loads(body)} {head}')


#######################################
# Get utility variables
# (data normalizers, etc)
#######################################
def get_utility_vars():
    return {
        'anomaly_positive_standard_scalar': StandardScaler(),
        'anomaly_neutral_standard_scalar': StandardScaler(),
        'anomaly_negative_standard_scalar': StandardScaler(),
    }
