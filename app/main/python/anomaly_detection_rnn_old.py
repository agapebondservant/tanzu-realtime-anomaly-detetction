########################
# Imports
########################
import ray
import os
ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ), 'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
import modin.pandas as pd
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
import re
import json
from app.main.python import feature_store, data_source, config, anomaly_detection
from app.main.python.utils import utils
from app.main.python.metrics import prometheus_metrics_util
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, SimpleRNN, Dropout
from tensorflow.keras.callbacks import EarlyStopping


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
def initialize_input_features(data_freq, sliding_window_size, arima_order):
    return anomaly_detection.initialize_input_features(data_freq, sliding_window_size, arima_order)


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


##############################################################################
# Build RNN model
##############################################################################
def build_rnn_model(actual_negative_sentiments, rebuild):
    logging.info("Build RNN model...")

    generator = feature_store.load_artifact('anomaly_timeseries')

    if rebuild is True:
        # Build a Timeseries Generator
        generator = build_timeseries_generator(actual_negative_sentiments['sentiment_normalized'])

    feature_store.save_artifact(generator, 'anomaly_timeseries')

    return generator


##############################################################################
# Build a Timeseries generator for the RNN Model
##############################################################################
def build_timeseries_generator(actual_negative_sentiments, sample_frequency='10min'):
    test_period = 1440  # (we assume a daily sample rate)

    total_test_window = int(test_period * 2 / sample_frequency)

    # The size of the sliding window
    sliding_window_size = int(test_period / sample_frequency)

    # The training data
    actual_negative_sentiments_train = actual_negative_sentiments.iloc[:-total_test_window].dropna()

    # number of outputs per batch
    batch_length = int(test_period / sample_frequency)

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


##############################################################################
# Train and Validate RNN Model To Generate Results
##############################################################################
def train_rnn_model(actual_negative_sentiments, test_period=1440, sample_frequency='10min', num_features=1):
    logging.info(f"Train RNN model...")

    # generate batch_length - number of outputs per batch
    batch_length = int(test_period / sample_frequency)

    # set the test window
    total_test_window = int(test_period * 2 / sample_frequency)

    # set the generator batch size
    timeseries_batch_size = 1

    # set up model
    rnn_model = Sequential()
    rnn_model.add(SimpleRNN(150, input_shape=(batch_length, num_features)))
    rnn_model.add(Dense(1))
    rnn_model.compile(optimizer='adam', loss='mae')
    rnn_model.summary()

    # set up Early Stopping
    early_stop = EarlyStopping(monitor='val_loss', patience=2)
    standard_scaler_rnn = feature_store.load_artifact('scaler_rnn_train')

    # set the test data
    actual_negative_sentiments_test = actual_negative_sentiments.iloc[-total_test_window:].dropna()

    scaled_test = standard_scaler_rnn.transform(actual_negative_sentiments_test[['sentiment']])

    # get the training generator
    generator = build_timeseries_generator(actual_negative_sentiments, test_period)

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


#######################################
# Test RNN Model
#######################################
def test_rnn_model(sliding_window_size, total_forecast_size, stepwise_fit, actual_negative_sentiments):
    logging.info('Testing RNN model...')

    return generate_rnn_forecasts(sliding_window_size, total_forecast_size, stepwise_fit,
                                  actual_negative_sentiments)


#######################################
# Detect Anomalies
#######################################
def detect_anomalies(predictions, window_size, actual_negative_sentiments):
    logging.info('Detecting anomalies...')

    z_score = st.norm.ppf(.95)  # 95% confidence interval
    mae_scale_factor = 0.67449  # MAE is 0.67449 * std

    predictions = predictions.iloc[:int(window_size)]

    df_total = actual_negative_sentiments['sentiment_normalized'].iloc[:int(window_size)]
    # mae = median_absolute_error(df_total.iloc[-int(window_size):], predictions)
    logging.info(f"anomalies for...{df_total} {predictions}")
    mae = median_absolute_error(df_total, predictions)

    model_arima_results_full = \
        pd.DataFrame({'fittedvalues': predictions, 'median_values': predictions.rolling(4).median().fillna(0)},
                     index=predictions.index)
    model_arima_results_full['threshold'] = model_arima_results_full['median_values'] + (
            z_score / mae_scale_factor) * mae
    model_arima_results_full['anomaly'] = 0

    model_arima_results_full['actualvalues'] = df_total
    model_arima_results_full['actualvalues'].fillna(0, inplace=True)

    model_arima_results_full.loc[
        model_arima_results_full['actualvalues'] > model_arima_results_full['threshold'], 'anomaly'] = 1

    print(f"Anomaly distribution: \n{model_arima_results_full['anomaly'].value_counts()}")

    # TODO: Publish anomaly summary to queue
    feature_store.save_artifact(actual_negative_sentiments, 'actual_negative_sentiments')
    publish_trend_stats(actual_negative_sentiments)

    return model_arima_results_full


#######################################
# Plot Trend with Anomalies
#######################################
def plot_trend_with_anomalies(total_negative_sentiments, model_rnn_results_full, model_rnn_forecasts,
                              sliding_window_size,
                              extvars,
                              timeframe='hour'):
    logging.info("Plot trend with anomalies...")

    # Set start_date, end_date
    end_date = utils.get_max_index(model_rnn_forecasts)
    logging.info(f"end date is {end_date} {model_rnn_forecasts}")
    start_date = end_date - timedelta(hours=get_time_lags(timeframe))
    marker_date_start = utils.get_min_index(model_rnn_forecasts)
    marker_date_end = utils.get_max_index(model_rnn_forecasts)

    standard_scalar = extvars['anomaly_negative_standard_scalar']
    inverse_scaled = pd.DataFrame(model_rnn_results_full[['actualvalues', 'fittedvalues']],
                                  columns=['actualvalues', 'fittedvalues'],
                                  index=model_rnn_results_full.index)

    logging.info(f"Inverse scaled values: {inverse_scaled}")

    fitted_values_actual = inverse_scaled['actualvalues']
    fitted_values_predicted = inverse_scaled['fittedvalues']
    fitted_values_forecasted = pd.DataFrame(pd.DataFrame(model_rnn_forecasts),
                                            columns=['forecastvalues'],
                                            index=model_rnn_forecasts.index)['forecastvalues']

    mae_error = median_absolute_error(fitted_values_predicted, fitted_values_actual)
    feature_store.save_artifact(mae_error, 'anomaly_mae_error')

    # TODO: Publish metrics to queue/log MAE metric
    # prometheus_metrics_util.send_arima_mae(mae_error)

    # Plot curves
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim([start_date, end_date])
    ax.plot(fitted_values_actual, label="Actual", color='blue')
    ax.plot(fitted_values_predicted, label=f"RNN Predictions", color='orange')
    ax.plot(fitted_values_forecasted, label='Forecasted', color='green', linewidth=2)
    ax.plot(fitted_values_actual.loc[model_rnn_results_full['anomaly'] == 1],
            marker='o', linestyle='None', color='red', label="Anomalies")
    ax.axvspan(marker_date_start, marker_date_end, alpha=0.5, color='green')

    ax.legend()
    fig.suptitle(f"RNN Model: \n Median Absolute Error (MAE): {mae_error}", fontsize=16)

    return fig


#######################################
# Generate RNN Forecasts
#######################################
def generate_rnn_forecasts(rnn_model,
                           actual_negative_sentiments_test,
                           scaled_test,
                           scaled_train,
                           standard_scaler_rnn,
                           batch_length,
                           num_features=1):
    logging.info("Generating RNN predictions...")

    num_predictions = len(scaled_test)
    eval_batch = scaled_train[-batch_length:].reshape(1, batch_length, num_features)
    scaled_predictions = []

    for i in np.arange(num_predictions):
        scaled_prediction = rnn_model.predict(eval_batch)
        eval_batch = np.append(eval_batch[:, 1:, :], [scaled_prediction], axis=1)
        scaled_predictions.append(scaled_prediction)

    predictions = standard_scaler_rnn.inverse_transform(np.reshape(scaled_predictions, (num_predictions, 1)))
    rnn_predictions = pd.concat([pd.Series(), pd.Series(predictions.reshape(-1))])[
                      -len(actual_negative_sentiments_test):]
    rnn_predictions.reindex(actual_negative_sentiments_test.index)

    # Store predictions
    feature_store.save_artifact(rnn_predictions, 'anomaly_rnn_forecasts')
    return rnn_predictions


#######################################
# Get any prior forecasts
#######################################

def get_prior_rnn_forecasts():
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
    return anomaly_detection.publish_trend_stats(actual_negative_sentiments)


#######################################
# Retrieve generated stats
#######################################


def get_trend_stats():
    return anomaly_detection.get_trend_stats()


def process_stats(head, body):
    anomaly_detection.process_stats(head, body)


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
