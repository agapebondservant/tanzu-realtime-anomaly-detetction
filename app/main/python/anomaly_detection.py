########################
# Imports
########################
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
from app.main.python import feature_store, data_source


########################################################################################################################
# ANOMALY DETECTION
########################################################################################################################


########################
# Ingest Data
########################
def ingest_data():
    logging.info('Ingest data...')
    # TODO: retrieve from Rabbit Stream-backed queue
    return data_source.get_data()


#######################################
# Set Global Values
#######################################
def initialize_input_features(data_freq, sliding_window_size, arima_order):
    logging.info("Initializing input features...")
    input_features = {
        'data_freq': data_freq,
        'sliding_window_size': sliding_window_size,
        'arima_order': arima_order
    }
    feature_store.save_artifact(input_features, "anomaly_detection_input_features")
    return input_features


#######################################
# Generate and Save EDA Artifacts
#######################################
def generate_and_save_eda_metrics(df):
    logging.info("Generating and saving EDA metrics...")
    data_summary = df.groupby('airline_sentiment').resample('1d').count()[['tweet_id']]
    data_summary = data_summary.unstack(0)
    data_summary['total'] = data_summary.sum(axis=1)
    feature_store.save_artifact(data_summary, "anomaly_detection_eda")
    return data_summary


#############################
# Filter Data
#############################
def filter_data(df, window):
    logging.info("Filtering by retrieving only required subset of data...")
    return df[window:]


#############################
# Prepare Data
#############################

def prepare_data(df, sample_frequency, extvars):
    logging.info("Preparing data...")
    data_buffers = extract_features(df, sample_frequency, extvars)
    return data_buffers


#######################################
# Perform feature extraction via resampling
#######################################
def extract_features(df, sample_frequency, extvars):
    logging.info("Performing feature extraction...")

    df['sentiment'] = df['airline_sentiment'].map({'positive': 1, 'neutral': 0, 'negative': -1})

    return save_data_buffers(df, sample_frequency, extvars)


#######################################
# Perform Data Standardization
#######################################
def standardize_data(buffers, extvars):
    logging.info("Performing data standardization...")

    actual_positive_sentiments, actual_negative_sentiments, actual_neutral_sentiments = \
        buffers['actual_positive_sentiments'], \
        buffers['actual_negative_sentiments'], \
        buffers['actual_neutral_sentiments']

    buffers['actual_positive_sentiments'][['sentiment_normalized']] = \
        extvars['anomaly_positive_standard_scalar'].fit_transform(actual_positive_sentiments[['sentiment']])
    buffers['actual_negative_sentiments'][['sentiment_normalized']] = \
        extvars['anomaly_negative_standard_scalar'].fit_transform(actual_negative_sentiments[['sentiment']])
    buffers['actual_negative_sentiments'][['sentiment_normalized']] = \
        extvars['anomaly_neutral_standard_scalar'].fit_transform(actual_neutral_sentiments[['sentiment']])

    return buffers


#######################################
# Initialize Data Buffers
#######################################
def save_data_buffers(df, sample_frequency, extvars):
    logging.info("Generate and save data buffers to use for stream processing...")

    data_buffers = {
        'total_sentiments': df,
        'actual_positive_sentiments': df[df['sentiment'] == 1].resample(f'{sample_frequency}').count(),
        'actual_negative_sentiments': df[df['sentiment'] == -1].resample(f'{sample_frequency}').count(),
        'actual_neutral_sentiments': df[df['sentiment'] == 0].resample(f'{sample_frequency}').count()
    }

    data_buffers = standardize_data(data_buffers, extvars)

    feature_store.save_artifact(data_buffers, 'anomaly_detection_buffers')
    return data_buffers


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
    start_date, end_date = total_sentiments['sentiment'].index.max(), total_sentiments[
        'sentiment'].index.max() - timedelta(
        hours=get_time_lags(timeframe))

    fig, ax = plt.subplots(figsize=(12, 5))

    fig.suptitle(f"Trending over the past {timeframe}")
    ax.set_xlim([start_date, end_date])
    ax.plot(actual_positive_sentiments['sentiment'],
            label="Positive Tweets", color="blue")
    ax.plot(actual_negative_sentiments['sentiment'],
            label="Negative Tweets", color="orange")
    ax.hlines(actual_positive_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='blue')
    ax.hlines(actual_negative_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='orange')
    ax.set_ylabel('Number of tweets', fontsize=14)
    ax.legend()

    return fig


#######################################
# Perform Auto ARIMA Search
#######################################
def run_auto_arima(actual_negative_sentiments, retrain):
    logging.info("Running auto_arima...")
    stepwise_fit = feature_store.load_artifact('anomaly_auto_arima')

    if retrain is True:
        stepwise_fit = auto_arima(actual_negative_sentiments['sentiment_normalized'], start_p=0, start_q=0, max_p=6,
                                  max_q=6,
                                  seasonal=False, trace=True)

    feature_store.save_artifact(stepwise_fit, 'anomaly_auto_arima')
    print(f"feature store results is null: {stepwise_fit is None}")
    return stepwise_fit


#######################################
# Build ARIMA Model Results
#######################################
def build_arima_model(training_window_size, stepwise_fit, actual_negative_sentiments):
    logging.info(f"Build ARIMA model with params (p,d,q) = {stepwise_fit.order}...")
    actual_negative_sentiments_train = actual_negative_sentiments.iloc[-int(training_window_size):]

    model_arima_order = stepwise_fit.order

    model_arima = ARIMA(actual_negative_sentiments_train['sentiment_normalized'], order=model_arima_order)

    feature_store.save_artifact(model_arima, 'anomaly_arima_model')

    model_arima_results = model_arima.fit()  # fit the model

    feature_store.save_artifact(model_arima_results, 'anomaly_arima_model_results')

    return model_arima_results


#######################################
# Test ARIMA Model
#######################################
def test_arima_model(sliding_window_size, total_forecast_size, stepwise_fit, actual_negative_sentiments):
    logging.info('Testing ARIMA model...')

    return generate_arima_predictions(sliding_window_size, total_forecast_size, stepwise_fit,
                                      actual_negative_sentiments)


#######################################
# Detect Anomalies
#######################################
def detect_anomalies(predictions, forecast_window_size, actual_negative_sentiments):
    logging.info('Detecting anomalies...')

    z_score = st.norm.ppf(.95)  # 95% confidence interval
    mae_scale_factor = 0.67449  # MAE is 0.67449 * std

    predictions = predictions.iloc[-int(forecast_window_size):]

    df_total = actual_negative_sentiments['sentiment_normalized']
    mae = median_absolute_error(df_total.iloc[-int(forecast_window_size):], predictions)

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
    publish_trend_stats(actual_negative_sentiments)

    return model_arima_results_full


#######################################
# Plot Trend with Anomalies
#######################################
def plot_trend_with_anomalies(model_arima_results_full, sliding_window_size, stepwise_fit, extvars,
                              timeframe='hour'):
    logging.info("Plot trend with anomalies...")
    start_date, end_date = \
        model_arima_results_full.actualvalues.index[-1] - timedelta(hours=get_time_lags(timeframe)), \
        model_arima_results_full.actualvalues.index[-1]

    standard_scalar = extvars['anomaly_negative_standard_scalar']
    inverse_scaled = pd.DataFrame(
        standard_scalar.inverse_transform(model_arima_results_full[['actualvalues', 'fittedvalues']]),
        columns=['actualvalues', 'fittedvalues'],
        index=model_arima_results_full.index)

    logging.info(f"Inverse scaled values: {inverse_scaled}")

    fitted_values_predicted = inverse_scaled['actualvalues']
    fitted_values_actual = inverse_scaled['fittedvalues']

    mae_error = median_absolute_error(fitted_values_predicted, fitted_values_actual)
    feature_store.save_artifact(mae_error, 'anomaly_mae_error')

    # Plot curves
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim([start_date, end_date])
    ax.plot(fitted_values_actual, label="Actual", color='blue')
    ax.plot(fitted_values_predicted, color='orange', label=f"ARIMA {stepwise_fit.order} Predictions")
    ax.hlines(median(fitted_values_actual), xmin=start_date, xmax=end_date, linestyles='--',
              colors='blue')
    ax.plot(fitted_values_actual[-int(sliding_window_size):].loc[model_arima_results_full['anomaly'] == 1],
            marker='o', linestyle='None', color='red', label="Anomalies"
            )
    ax.legend()
    fig.suptitle(f"ARIMA Model: \n Median Absolute Error (MAE): {mae_error}", fontsize=16)

    return fig


#######################################
# Generate ARIMA Predictions
#######################################
def generate_arima_predictions(sliding_window_size, total_forecast_size, stepwise_fit, actual_negative_sentiments):
    logging.info("Generate ARIMA predictions...")
    # The dataset to forecast with
    df = actual_negative_sentiments.iloc[:-int(total_forecast_size)]

    # The number of forecasts per sliding window will be the number of AR lags, as ARIMA can't forecast beyond that
    num_lags = stepwise_fit.order[0]

    # The number of sliding windows will be ( total forecast size / num_lags )
    num_sliding_windows = total_forecast_size / num_lags

    # Initialize the start & end indexes
    end_idx = len(df) - num_lags

    # Get any prior ARIMA predictions
    predictions = get_prior_arima_predictions()

    for idx in np.arange(num_sliding_windows):
        # Compute the start & end indexes
        end_idx = end_idx + num_lags
        start_idx = end_idx - sliding_window_size
        logging.info(f'DEBUG: {start_idx} {end_idx} {end_idx - start_idx} {len(df)} {len(actual_negative_sentiments)}')
        tmp_data = actual_negative_sentiments[int(start_idx):int(end_idx)]
        tmp_arima = ARIMA(tmp_data['sentiment_normalized'], order=stepwise_fit.order)
        tmp_model_arima_results = tmp_arima.fit()
        pred = tmp_model_arima_results.forecast(steps=num_lags, typ="levels").rename('forecasted')
        predictions = predictions.append(pred)

    # Save predictions
    # latest_predictions = predictions[predictions.index > actual_negative_sentiments.index[-1]]
    feature_store.save_artifact(predictions, 'anomaly_arima_predictions')

    # Return predictions
    return predictions


#######################################
# Get any prior predictions
#######################################

def get_prior_arima_predictions():
    return feature_store.load_artifact('anomaly_arima_predictions') or pd.getSeries([])


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


def publish_trend_stats(actual_negative_sentiments):
    sample_frequencies = ['1min', '10min', '60min']

    stats = []

    for sample_frequency in sample_frequencies:
        num_negative_in_past, sample_frequency_num = 0, int(re.findall(r'\d+', sample_frequency)[0])

        last_recorded_time = actual_negative_sentiments.index[-1]
        offset_time = last_recorded_time - timedelta(minutes=sample_frequency_num)

        num_negative_in_past = actual_negative_sentiments.loc[actual_negative_sentiments.index >= offset_time]['sentiment'].sum()
        print(f"Number of negative posts in past {sample_frequency_num} minutes: {num_negative_in_past}")

        stats.append(num_negative_in_past)

    summary = {sample_frequencies[i]: stats[i] for i in range(len(sample_frequencies))}
    summary['anomaly_found'] = False # TODO: Set to True if new anomaly is found
    feature_store.save_artifact(summary, 'anomaly_summary')

    return summary


#######################################
# Retrieve generated stats
#######################################


def get_trend_stats():
    return feature_store.load_artifact('anomaly_summary')
